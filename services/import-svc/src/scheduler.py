"""Import-Scheduler fuer Bulk-Imports und API-Delta-Updates.

Nutzt APScheduler (AsyncIOScheduler), um zwei Job-Typen auszufuehren:
1. Woechentlicher Bulk-Import (EPO DOCDB, CORDIS, EuroSciVoc) — initiale Datenbasis
2. Taeglicher API-Delta-Update (EPO OPS, CORDIS REST API) — aktuelle Daten

API-Daten ueberschreiben Bulk-Daten (ON CONFLICT DO UPDATE).
Bulk = initiales Setup. APIs = primaere laufende Datenquelle.

Standard-Schedules:
- Bulk: Sonntag 02:00 UTC (IMPORT_SCHEDULE)
- Delta: Taeglich 03:00 UTC (API_DELTA_SCHEDULE)
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = structlog.get_logger(__name__)

# Letztes Scheduler-Ergebnis (fuer Status-Endpoint)
_last_run: dict[str, Any] = {}


def create_scheduler(
    app: Any,
    cron_expression: str = "0 2 * * 0",
    timezone_str: str = "UTC",
) -> AsyncIOScheduler:
    """Scheduler erstellen und Job registrieren.

    Args:
        app: FastAPI-Instanz (fuer Zugriff auf db_pool und settings).
        cron_expression: Cron-Ausdruck (5-Felder: Minute Stunde Tag Monat Wochentag).
        timezone_str: Zeitzone fuer den Cron-Trigger.

    Returns:
        Konfigurierter AsyncIOScheduler (noch nicht gestartet).
    """
    scheduler = AsyncIOScheduler(timezone=timezone_str)

    # Cron-Felder parsen
    parts = cron_expression.strip().split()
    if len(parts) != 5:
        logger.error(
            "scheduler_ungueltig_cron",
            expression=cron_expression,
            hint="Erwartet 5 Felder: Minute Stunde Tag Monat Wochentag",
        )
        return scheduler

    trigger = CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
        timezone=timezone_str,
    )

    scheduler.add_job(
        weekly_import_job,
        trigger=trigger,
        args=[app],
        id="weekly_bulk_import",
        name="Woechentlicher Bulk-Import (EuroSciVoc + CORDIS + EPO)",
        replace_existing=True,
    )

    # --- Taeglicher API-Delta-Update ---
    settings = getattr(app, "state", None)
    delta_cron = "0 3 * * *"
    if settings and hasattr(settings, "settings"):
        delta_cron = getattr(settings.settings, "api_delta_schedule", delta_cron)

    delta_parts = delta_cron.strip().split()
    if len(delta_parts) == 5:
        delta_trigger = CronTrigger(
            minute=delta_parts[0],
            hour=delta_parts[1],
            day=delta_parts[2],
            month=delta_parts[3],
            day_of_week=delta_parts[4],
            timezone=timezone_str,
        )
        scheduler.add_job(
            daily_api_delta_job,
            trigger=delta_trigger,
            args=[app],
            id="daily_api_delta",
            name="Taeglicher API-Delta-Update (EPO OPS + CORDIS)",
            replace_existing=True,
            misfire_grace_time=3600,
            max_instances=1,
        )
        logger.info("scheduler_delta_konfiguriert", schedule=delta_cron)

    logger.info(
        "scheduler_konfiguriert",
        bulk_schedule=cron_expression,
        delta_schedule=delta_cron,
        timezone=timezone_str,
    )

    return scheduler


async def weekly_import_job(app: Any) -> None:
    """Woechentlicher Import-Job: EuroSciVoc -> CORDIS -> EPO.

    Reihenfolge: EuroSciVoc (schnellstes) zuerst, EPO (langsamstes) zuletzt.
    Ueberspringt eine Quelle wenn deren Import bereits laeuft (manuell getriggert).
    """
    global _last_run

    from src.router_import import (
        ImportStatus,
        _run_cordis_import,
        _run_epo_import,
        _run_euroscivoc_import,
        _state,
    )

    pool = getattr(app.state, "db_pool", None)
    settings = getattr(app.state, "settings", None)

    if pool is None or settings is None:
        logger.error("scheduler_job_abgebrochen", grund="Kein DB-Pool oder Settings")
        return

    t0 = time.monotonic()
    started_at = datetime.now(tz=timezone.utc).isoformat()
    results: dict[str, str] = {}

    logger.info("scheduler_job_gestartet")

    # 1. EuroSciVoc
    try:
        await _run_euroscivoc_import(pool, settings)
        results["euroscivoc"] = "ok"
        logger.info("scheduler_euroscivoc_ok")
    except Exception as exc:
        results["euroscivoc"] = f"fehler: {exc}"
        logger.error("scheduler_euroscivoc_fehler", error=str(exc))

    # 2. CORDIS
    if _state.cordis_status == ImportStatus.RUNNING:
        results["cordis"] = "uebersprungen (laeuft bereits)"
        logger.warning("scheduler_cordis_uebersprungen")
    else:
        _state.cordis_status = ImportStatus.RUNNING
        _state.cordis_started_at = datetime.now(tz=timezone.utc).isoformat()
        _state.cordis_result = {}
        try:
            await _run_cordis_import(pool, settings)
            results["cordis"] = "ok"
            logger.info("scheduler_cordis_ok")
        except Exception as exc:
            _state.cordis_status = ImportStatus.FAILED
            _state.cordis_result = {"error": str(exc)}
            results["cordis"] = f"fehler: {exc}"
            logger.error("scheduler_cordis_fehler", error=str(exc))

    # 3. EPO (laeuft als Background-Task, kann Stunden dauern)
    if _state.epo_status == ImportStatus.RUNNING:
        results["epo"] = "uebersprungen (laeuft bereits)"
        logger.warning("scheduler_epo_uebersprungen")
    else:
        _state.epo_status = ImportStatus.RUNNING
        _state.epo_started_at = datetime.now(tz=timezone.utc).isoformat()
        _state.epo_result = {}
        try:
            await _run_epo_import(pool, settings)
            results["epo"] = "ok"
            logger.info("scheduler_epo_ok")
        except Exception as exc:
            _state.epo_status = ImportStatus.FAILED
            _state.epo_result = {"error": str(exc)}
            results["epo"] = f"fehler: {exc}"
            logger.error("scheduler_epo_fehler", error=str(exc))

    # 4. Junction-Derivation (patent_cpc, patent_applicants, applicants).
    # Wird immer nach EPO ausgefuehrt — auch bei uebersprungenem Import —
    # damit manuelle Imports sicher abgedeckt sind. Idempotent durch
    # ON CONFLICT DO NOTHING; bei Full-Scan auf 156 M Patents kann das
    # 30-90 Minuten dauern. Siehe services/import-svc/src/importers/junction_deriver.py.
    try:
        from src.importers.junction_deriver import derive_junctions

        junction_stats = await derive_junctions(pool)
        results["junction_derivation"] = "ok"
        logger.info("scheduler_junction_derivation_ok", stats=junction_stats)
    except Exception as exc:
        results["junction_derivation"] = f"fehler: {exc}"
        logger.error("scheduler_junction_derivation_fehler", error=str(exc))

    duration_s = round(time.monotonic() - t0, 1)

    _last_run = {
        "started_at": started_at,
        "duration_seconds": duration_s,
        "results": results,
    }

    logger.info(
        "scheduler_job_abgeschlossen",
        dauer_sekunden=duration_s,
        ergebnisse=results,
    )


async def daily_api_delta_job(app: Any) -> None:
    """Taeglicher Delta-Update: Holt aktuelle Daten via EPO OPS + CORDIS API.

    Fragt die zuletzt gesuchten Technologien erneut ab (aus den Cache-Tabellen).
    API-Daten ueberschreiben bestehende Bulk-Eintraege (ON CONFLICT DO UPDATE).
    """
    global _last_run

    pool = getattr(app.state, "db_pool", None)
    settings = getattr(app.state, "settings", None)

    if pool is None or settings is None:
        logger.error("delta_job_abgebrochen", grund="Kein DB-Pool oder Settings")
        return

    t0 = time.monotonic()
    started_at = datetime.now(tz=timezone.utc).isoformat()
    results: dict[str, str] = {}
    end_year = datetime.now().year
    start_year = end_year - max(settings.api_delta_lookback_days // 365, 1)

    logger.info("delta_job_gestartet", lookback_days=settings.api_delta_lookback_days)

    # EPO OPS Delta
    if settings.epo_ops_enabled and settings.epo_ops_consumer_key:
        try:
            from src.importers.epo_ops_adapter import EpoOpsAdapter

            epo = EpoOpsAdapter(
                consumer_key=settings.epo_ops_consumer_key,
                consumer_secret=settings.epo_ops_consumer_secret,
                timeout=settings.epo_ops_timeout_s,
                rate_limit_rpm=settings.epo_ops_rate_limit_rpm,
                pool=pool,
            )
            top_techs = await pool.fetch(
                "SELECT DISTINCT technology FROM patent_schema.epo_ops_cache "
                "ORDER BY fetched_at DESC LIMIT 50"
            )
            for row in top_techs:
                await epo.search_patents(
                    row["technology"], start_year=start_year, end_year=end_year,
                )
            results["epo_ops"] = f"ok ({len(top_techs)} Technologien)"
            logger.info("delta_epo_ops_ok", technologies=len(top_techs))
        except Exception as exc:
            results["epo_ops"] = f"fehler: {exc}"
            logger.error("delta_epo_ops_fehler", error=str(exc))
    else:
        results["epo_ops"] = "deaktiviert"

    # CORDIS Delta
    if settings.cordis_api_enabled:
        try:
            from src.importers.cordis_api_adapter import CordisApiAdapter

            cordis = CordisApiAdapter(
                timeout=settings.cordis_api_timeout_s,
                rate_limit_rpm=settings.cordis_api_rate_limit_rpm,
                pool=pool,
            )
            top_techs = await pool.fetch(
                "SELECT DISTINCT technology FROM cordis_schema.cordis_api_cache "
                "ORDER BY fetched_at DESC LIMIT 50"
            )
            for row in top_techs:
                await cordis.search_projects(row["technology"])
            results["cordis_api"] = f"ok ({len(top_techs)} Technologien)"
            logger.info("delta_cordis_api_ok", technologies=len(top_techs))
        except Exception as exc:
            results["cordis_api"] = f"fehler: {exc}"
            logger.error("delta_cordis_api_fehler", error=str(exc))
    else:
        results["cordis_api"] = "deaktiviert"

    duration_s = round(time.monotonic() - t0, 1)

    _last_run = {
        "type": "api_delta",
        "started_at": started_at,
        "duration_seconds": duration_s,
        "results": results,
    }

    logger.info("delta_job_abgeschlossen", dauer_sekunden=duration_s, ergebnisse=results)


def get_schedule_status(scheduler: AsyncIOScheduler | None) -> dict[str, Any]:
    """Aktuellen Scheduler-Status fuer den Status-Endpoint zurueckgeben."""
    if scheduler is None:
        return {"enabled": False}

    bulk_job = scheduler.get_job("weekly_bulk_import")
    delta_job = scheduler.get_job("daily_api_delta")

    bulk_next = None
    if bulk_job and bulk_job.next_run_time:
        bulk_next = bulk_job.next_run_time.isoformat()

    delta_next = None
    if delta_job and delta_job.next_run_time:
        delta_next = delta_job.next_run_time.isoformat()

    return {
        "enabled": scheduler.running,
        "bulk_next_run": bulk_next,
        "delta_next_run": delta_next,
        "last_run": _last_run or None,
    }
