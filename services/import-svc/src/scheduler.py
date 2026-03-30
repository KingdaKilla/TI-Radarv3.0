"""Woechentlicher Import-Scheduler fuer EPO, CORDIS und EuroSciVoc.

Nutzt APScheduler (AsyncIOScheduler), um Bulk-Imports regelmaessig
auszufuehren. Der Scheduler laeuft innerhalb des FastAPI-Prozesses
und wird ueber den Lifespan-Kontext gesteuert.

Standard-Schedule: Sonntag 02:00 UTC (konfigurierbar via IMPORT_SCHEDULE).
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

    logger.info(
        "scheduler_konfiguriert",
        schedule=cron_expression,
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


def get_schedule_status(scheduler: AsyncIOScheduler | None) -> dict[str, Any]:
    """Aktuellen Scheduler-Status fuer den Status-Endpoint zurueckgeben."""
    if scheduler is None:
        return {"enabled": False}

    job = scheduler.get_job("weekly_bulk_import")
    next_run = None
    if job and job.next_run_time:
        next_run = job.next_run_time.isoformat()

    return {
        "enabled": scheduler.running,
        "next_run": next_run,
        "last_run": _last_run or None,
    }
