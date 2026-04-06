"""Import-Router — Endpoints fuer EPO- und CORDIS-Bulk-Import.

Stellt vier Endpoints bereit:
  POST /api/v1/import/epo          — EPO-Patent-Bulk-Import starten
  POST /api/v1/import/cordis       — CORDIS-Projekt-Bulk-Import starten
  GET  /api/v1/import/status       — Aktuellen Import-Status abfragen
  POST /api/v1/import/refresh-views — Materialisierte Views aktualisieren
"""

from __future__ import annotations

import asyncio
import hmac
import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Admin-Key Authentication
# ---------------------------------------------------------------------------

_ADMIN_KEY_HEADER = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def require_admin_key(key: str | None = Security(_ADMIN_KEY_HEADER)) -> None:
    """Validate the X-Admin-Key header against TI_RADAR_ADMIN_KEY env var.

    In MVP mode (no key configured) the check is skipped so local development
    requires no configuration change.  In any deployed environment the env var
    MUST be set to a strong random secret.
    """
    expected = os.getenv("TI_RADAR_ADMIN_KEY", "")
    if not expected:
        return  # MVP mode — no key configured
    if not key or not hmac.compare_digest(key, expected):
        raise HTTPException(status_code=401, detail="Admin key required")

from src.importers.cordis_importer import ImportResult as CordisResult
from src.importers.cordis_importer import import_cordis_bulk
from src.importers.epo_enrichment import EnrichmentResult
from src.importers.epo_enrichment import enrich_epo_patents
from src.importers.epo_importer import ImportResult as EpoResult
from src.importers.epo_importer import import_epo_bulk
from src.importers.euroscivoc_importer import ImportResult as EuroscivocResult
from src.importers.euroscivoc_importer import import_euroscivoc_bulk

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/import", tags=["Import"])


# ---------------------------------------------------------------------------
# Materialisierte Views: Automatischer Refresh nach Import
# ---------------------------------------------------------------------------

# Patent-bezogene MVs (nach EPO-Import)
_PATENT_VIEWS = [
    "cross_schema.mv_patent_counts_by_cpc_year",
    "cross_schema.mv_cpc_cooccurrence",
    "cross_schema.mv_yearly_tech_counts",
    "cross_schema.mv_top_applicants",
    "cross_schema.mv_patent_country_distribution",
]

# CORDIS-bezogene MVs (nach CORDIS-Import)
_CORDIS_VIEWS = [
    "cross_schema.mv_project_counts_by_year",
    "cross_schema.mv_cordis_country_pairs",
    "cross_schema.mv_top_cordis_orgs",
    "cross_schema.mv_funding_by_instrument",
]

# Alle 9 MVs
_ALL_VIEWS = _PATENT_VIEWS + _CORDIS_VIEWS

# Allowlist aller erlaubten materialisierten Views (verhindert SQL-Injection)
_ALLOWED_VIEWS: frozenset = frozenset(_PATENT_VIEWS + _CORDIS_VIEWS + _ALL_VIEWS)


async def _refresh_materialized_views(
    pool: Any,
    views: list[str] | None = None,
    source: str = "unbekannt",
) -> float:
    """Materialisierte Views concurrent refreshen.

    Verwendet REFRESH MATERIALIZED VIEW CONCURRENTLY, das keine Lese-Sperren
    setzt (erfordert UNIQUE INDEX auf jeder MV — in 002_schema.sql vorhanden).

    Args:
        pool: asyncpg Connection-Pool.
        views: Liste der zu refreshenden Views. None = alle 9 MVs.
        source: Quellenangabe fuer Log-Meldungen (z.B. 'epo', 'cordis').

    Returns:
        Dauer des gesamten Refresh in Sekunden.
    """
    target_views = views or _ALL_VIEWS
    start_time = time.monotonic()

    logger.info(
        "mv_refresh_gestartet",
        quelle=source,
        anzahl_views=len(target_views),
    )

    async with pool.acquire() as conn:
        for view in target_views:
            if view not in _ALLOWED_VIEWS:
                raise ValueError(f"View not in allowlist: {view!r}")
            view_start = time.monotonic()
            try:
                await conn.execute(
                    f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}"
                )
                view_duration = round(time.monotonic() - view_start, 2)
                logger.info(
                    "mv_refresh_view_abgeschlossen",
                    view=view,
                    dauer_sekunden=view_duration,
                )
            except Exception as exc:
                logger.error(
                    "mv_refresh_view_fehler",
                    view=view,
                    error=str(exc),
                )

    total_duration = round(time.monotonic() - start_time, 2)
    logger.info(
        "mv_refresh_abgeschlossen",
        quelle=source,
        dauer_sekunden=total_duration,
        anzahl_views=len(target_views),
    )
    return total_duration


# ---------------------------------------------------------------------------
# Pydantic-Modelle fuer Request/Response
# ---------------------------------------------------------------------------


class ImportStatus(str, Enum):
    """Moegliche Status eines Import-Vorgangs."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ImportResponse(BaseModel):
    """Antwort-Modell fuer Import-Endpoints.

    Attribute:
        status: Aktueller Status des Imports.
        source: Datenquelle (EPO, CORDIS).
        message: Statusmeldung.
        files_processed: Anzahl verarbeiteter Dateien.
        records_imported: Anzahl importierter Datensaetze.
        records_skipped: Anzahl uebersprungener Datensaetze.
        errors: Liste von Fehlermeldungen (max. 50).
        duration_seconds: Bisherige Laufzeit in Sekunden.
        details: Zusaetzliche Details.
        started_at: Startzeitpunkt (ISO 8601).
    """

    status: ImportStatus
    source: str
    message: str
    files_processed: int = 0
    records_imported: int = 0
    records_skipped: int = 0
    errors: list[str] = Field(default_factory=list, max_length=50)
    duration_seconds: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)
    started_at: str | None = None


class StatusResponse(BaseModel):
    """Antwort-Modell fuer den Status-Endpoint.

    Attribute:
        epo: Status des EPO-Imports.
        cordis: Status des CORDIS-Imports.
    """

    epo: ImportResponse
    cordis: ImportResponse


class RefreshResponse(BaseModel):
    """Antwort-Modell fuer View-Refresh.

    Attribute:
        status: Ergebnisstatus.
        message: Statusmeldung.
        duration_seconds: Laufzeit in Sekunden.
    """

    status: str
    message: str
    duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Globaler Import-Status (In-Memory, pro Instanz)
# ---------------------------------------------------------------------------


class _ImportState:
    """Interner Status-Tracker fuer laufende Imports.

    Hinweis: In-Memory, nicht persistent. Bei Neustart geht der Status
    verloren. Fuer Produktionsbetrieb sollte Redis/DB verwendet werden.
    """

    def __init__(self) -> None:
        self.epo_status: ImportStatus = ImportStatus.IDLE
        self.epo_result: dict[str, Any] = {}
        self.epo_started_at: str | None = None
        # Live-Fortschritt fuer EPO (wird vom Background-Task aktualisiert)
        self.epo_files_done: int = 0
        self.epo_records_done: int = 0
        self.epo_current_file: str = ""

        self.cordis_status: ImportStatus = ImportStatus.IDLE
        self.cordis_result: dict[str, Any] = {}
        self.cordis_started_at: str | None = None


_state = _ImportState()


# ---------------------------------------------------------------------------
# EPO Import Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/epo",
    response_model=ImportResponse,
    summary="EPO-Patent-Bulk-Import starten",
    description=(
        "Liest alle XML-Dateien aus dem konfigurierten EPO-Verzeichnis, "
        "parst DOCDB-Patent-Daten und laedt sie batchweise ueber das "
        "asyncpg COPY-Protokoll in patent_schema.patents."
    ),
    dependencies=[Depends(require_admin_key)],
)
async def start_epo_import(request: Request) -> ImportResponse:
    """EPO-Bulk-Import starten.

    Liest XML-Dateien aus bulk_data_dir/EPO/ und importiert
    Patent-Daten in patent_schema.patents + patent_schema.patent_cpc.
    """
    # Pruefen ob bereits ein Import laeuft
    if _state.epo_status == ImportStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail="EPO-Import laeuft bereits. Bitte warten oder Status pruefen.",
        )

    # Datenbank-Pool und Settings aus app.state holen
    pool = request.app.state.db_pool
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="Datenbankverbindung nicht verfuegbar.",
        )

    settings = request.app.state.settings

    # Import-Status setzen
    _state.epo_status = ImportStatus.RUNNING
    _state.epo_started_at = datetime.now(tz=timezone.utc).isoformat()
    _state.epo_result = {}

    logger.info("epo_import_angefordert", bulk_data_dir=settings.bulk_data_dir)

    # Import als Background-Task starten (195 GB kann Stunden dauern)
    asyncio.create_task(_run_epo_import(pool, settings))

    return ImportResponse(
        status=ImportStatus.RUNNING,
        source="EPO",
        message="EPO-Import gestartet. Status ueber GET /api/v1/import/status abrufbar.",
        started_at=_state.epo_started_at,
    )


async def _run_epo_import(pool: Any, settings: Any) -> None:
    """EPO-Import als Background-Task ausfuehren mit Progress-Tracking."""
    def _progress_cb(files_done: int, records_done: int, current_file: str) -> None:
        _state.epo_files_done = files_done
        _state.epo_records_done = records_done
        _state.epo_current_file = current_file

    try:
        result: EpoResult = await import_epo_bulk(
            pool=pool,
            data_dir=settings.bulk_data_dir,
            batch_size=settings.batch_size,
            progress_cb=_progress_cb,
        )

        _state.epo_result = asdict(result)

        if result.errors:
            _state.epo_status = ImportStatus.COMPLETED
        else:
            _state.epo_status = ImportStatus.COMPLETED

        logger.info(
            "epo_import_ergebnis",
            status=_state.epo_status.value,
            records=result.records_imported,
            files=result.files_processed,
            duration=result.duration_seconds,
        )

        # Automatischer MV-Refresh nach erfolgreichem EPO-Import
        if result.records_imported > 0:
            try:
                refresh_duration = await _refresh_materialized_views(
                    pool, views=_PATENT_VIEWS, source="epo",
                )
                _state.epo_result["mv_refresh_duration"] = refresh_duration
            except Exception as refresh_exc:
                logger.error(
                    "epo_mv_refresh_fehlgeschlagen",
                    error=str(refresh_exc),
                )

    except Exception as exc:
        _state.epo_status = ImportStatus.FAILED
        _state.epo_result = {"error": str(exc)}
        logger.error("epo_import_fehlgeschlagen", error=str(exc))


# ---------------------------------------------------------------------------
# CORDIS Import Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/cordis",
    response_model=ImportResponse,
    summary="CORDIS-Projekt-Bulk-Import starten",
    description=(
        "Liest Projekte- und Organisationen-CSVs aus dem konfigurierten "
        "CORDIS-Verzeichnis und laedt sie batchweise in "
        "cordis_schema.projects + cordis_schema.organizations."
    ),
    dependencies=[Depends(require_admin_key)],
)
async def start_cordis_import(request: Request) -> ImportResponse:
    """CORDIS-Bulk-Import starten.

    Liest CSV-Dateien aus bulk_data_dir/CORDIS/ und importiert
    Projekte + Organisationen in cordis_schema.
    """
    # Pruefen ob bereits ein Import laeuft
    if _state.cordis_status == ImportStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail="CORDIS-Import laeuft bereits. Bitte warten oder Status pruefen.",
        )

    # Datenbank-Pool und Settings aus app.state holen
    pool = request.app.state.db_pool
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="Datenbankverbindung nicht verfuegbar.",
        )

    settings = request.app.state.settings

    # Import-Status setzen
    _state.cordis_status = ImportStatus.RUNNING
    _state.cordis_started_at = datetime.now(tz=timezone.utc).isoformat()
    _state.cordis_result = {}

    logger.info("cordis_import_angefordert", bulk_data_dir=settings.bulk_data_dir)

    try:
        response = await _run_cordis_import(pool, settings)
        return response

    except Exception as exc:
        _state.cordis_status = ImportStatus.FAILED
        _state.cordis_result = {"error": str(exc)}
        logger.error("cordis_import_fehlgeschlagen", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail="Import fehlgeschlagen. Siehe Server-Logs.",
        ) from exc


async def _run_cordis_import(pool: Any, settings: Any) -> ImportResponse:
    """CORDIS-Import als standalone Funktion (aufrufbar von Endpoint und Scheduler)."""
    result: CordisResult = await import_cordis_bulk(
        pool=pool,
        data_dir=settings.bulk_data_dir,
        batch_size=settings.batch_size,
    )

    _state.cordis_result = asdict(result)

    if result.errors:
        _state.cordis_status = ImportStatus.COMPLETED
        message = (
            f"CORDIS-Import abgeschlossen mit {len(result.errors)} Warnungen. "
            f"{result.records_imported} Datensaetze importiert."
        )
    else:
        _state.cordis_status = ImportStatus.COMPLETED
        message = (
            f"CORDIS-Import erfolgreich. {result.records_imported} Datensaetze "
            f"aus {result.files_processed} Dateien importiert."
        )

    logger.info("cordis_import_ergebnis", status=_state.cordis_status.value)

    mv_refresh_duration = 0.0
    if result.records_imported > 0:
        try:
            mv_refresh_duration = await _refresh_materialized_views(
                pool, views=_CORDIS_VIEWS, source="cordis",
            )
        except Exception as refresh_exc:
            logger.error(
                "cordis_mv_refresh_fehlgeschlagen",
                error=str(refresh_exc),
            )

    details = result.details.copy()
    if mv_refresh_duration > 0:
        details["mv_refresh_duration"] = mv_refresh_duration

    return ImportResponse(
        status=_state.cordis_status,
        source="CORDIS",
        message=message,
        files_processed=result.files_processed,
        records_imported=result.records_imported,
        records_skipped=result.records_skipped,
        errors=result.errors[:50],
        duration_seconds=result.duration_seconds,
        details=details,
        started_at=_state.cordis_started_at,
    )


# ---------------------------------------------------------------------------
# EuroSciVoc Import Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/euroscivoc",
    response_model=ImportResponse,
    summary="EuroSciVoc-Taxonomie-Import starten",
    description=(
        "Liest EuroSciVoc-Daten aus den CORDIS-Projekt-ZIPs (euroSciVoc.json) "
        "und importiert Taxonomie + Projekt-Zuordnungen in cordis_schema."
    ),
    dependencies=[Depends(require_admin_key)],
)
async def start_euroscivoc_import(request: Request) -> ImportResponse:
    """EuroSciVoc-Import aus CORDIS-Bulk-ZIPs starten.

    Liest euroSciVoc.json aus cordis-*projects-json.zip und importiert
    die hierarchische Taxonomie sowie Projekt-Zuordnungen.
    """
    pool = request.app.state.db_pool
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="Datenbankverbindung nicht verfuegbar.",
        )

    settings = request.app.state.settings

    logger.info("euroscivoc_import_angefordert", bulk_data_dir=settings.bulk_data_dir)

    try:
        return await _run_euroscivoc_import(pool, settings)

    except Exception as exc:
        logger.error("euroscivoc_import_fehlgeschlagen", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail="Import fehlgeschlagen. Siehe Server-Logs.",
        ) from exc


async def _run_euroscivoc_import(pool: Any, settings: Any) -> ImportResponse:
    """EuroSciVoc-Import als standalone Funktion (aufrufbar von Endpoint und Scheduler)."""
    result: EuroscivocResult = await import_euroscivoc_bulk(
        pool=pool,
        data_dir=settings.bulk_data_dir,
        batch_size=settings.batch_size,
    )

    status = ImportStatus.COMPLETED
    if result.errors:
        message = (
            f"EuroSciVoc-Import abgeschlossen mit {len(result.errors)} Warnungen. "
            f"{result.records_imported} Datensaetze importiert."
        )
    else:
        message = (
            f"EuroSciVoc-Import erfolgreich. {result.records_imported} Datensaetze "
            f"aus {result.files_processed} ZIPs importiert."
        )

    logger.info("euroscivoc_import_ergebnis", status=status.value)

    return ImportResponse(
        status=status,
        source="EUROSCIVOC",
        message=message,
        files_processed=result.files_processed,
        records_imported=result.records_imported,
        records_skipped=result.records_skipped,
        errors=result.errors[:50],
        duration_seconds=result.duration_seconds,
        details=result.details,
    )


# ---------------------------------------------------------------------------
# Status Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Import-Status abfragen",
    description="Gibt den aktuellen Status beider Import-Vorgaenge zurueck.",
)
async def get_import_status() -> StatusResponse:
    """Aktuellen Import-Status fuer EPO und CORDIS zurueckgeben."""
    epo_result = _state.epo_result
    cordis_result = _state.cordis_result

    # Fuer EPO: Live-Fortschritt anzeigen wenn Import laeuft
    epo_files = epo_result.get("files_processed", 0)
    epo_records = epo_result.get("records_imported", 0)
    epo_details: dict[str, Any] = {}
    if _state.epo_status == ImportStatus.RUNNING:
        epo_files = _state.epo_files_done
        epo_records = _state.epo_records_done
        if _state.epo_current_file:
            epo_details["current_file"] = _state.epo_current_file
        if _state.epo_started_at:
            elapsed = (datetime.now(tz=timezone.utc) - datetime.fromisoformat(_state.epo_started_at)).total_seconds()
            epo_details["elapsed_seconds"] = round(elapsed, 1)

    return StatusResponse(
        epo=ImportResponse(
            status=_state.epo_status,
            source="EPO",
            message=_status_message("EPO", _state.epo_status),
            files_processed=epo_files,
            records_imported=epo_records,
            records_skipped=epo_result.get("records_skipped", 0),
            errors=epo_result.get("errors", [])[:50],
            duration_seconds=epo_result.get("duration_seconds", 0.0),
            details=epo_details,
            started_at=_state.epo_started_at,
        ),
        cordis=ImportResponse(
            status=_state.cordis_status,
            source="CORDIS",
            message=_status_message("CORDIS", _state.cordis_status),
            files_processed=cordis_result.get("files_processed", 0),
            records_imported=cordis_result.get("records_imported", 0),
            records_skipped=cordis_result.get("records_skipped", 0),
            errors=cordis_result.get("errors", [])[:50],
            duration_seconds=cordis_result.get("duration_seconds", 0.0),
            details=cordis_result.get("details", {}),
            started_at=_state.cordis_started_at,
        ),
    )


def _status_message(source: str, status: ImportStatus) -> str:
    """Lesbare Statusmeldung generieren."""
    messages = {
        ImportStatus.IDLE: f"{source}-Import wurde noch nicht gestartet.",
        ImportStatus.RUNNING: f"{source}-Import laeuft...",
        ImportStatus.COMPLETED: f"{source}-Import abgeschlossen.",
        ImportStatus.FAILED: f"{source}-Import fehlgeschlagen.",
    }
    return messages.get(status, f"{source}-Import: unbekannter Status.")


# ---------------------------------------------------------------------------
# EPO Enrichment Endpoint (CPC-Codes + Laender nachladen)
# ---------------------------------------------------------------------------


@router.post(
    "/enrich-epo",
    response_model=ImportResponse,
    summary="EPO-Patente um CPC-Codes und Laender anreichern",
    description=(
        "Liest die EPO-DOCDB-XML-Archive erneut und aktualisiert bestehende "
        "Patent-Eintraege mit korrekt extrahierten CPC-Codes und Applicant-Countries."
    ),
    dependencies=[Depends(require_admin_key)],
)
async def start_epo_enrichment(request: Request) -> ImportResponse:
    """EPO-Enrichment starten.

    Liest die gleichen ZIP-Archive wie der Import, extrahiert aber nur
    CPC-Codes und Laender und aktualisiert bestehende Zeilen.
    """
    pool = request.app.state.db_pool
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="Datenbankverbindung nicht verfuegbar.",
        )

    settings = request.app.state.settings
    logger.info("epo_enrichment_angefordert", bulk_data_dir=settings.bulk_data_dir)

    # Als Background-Task starten
    asyncio.create_task(_run_epo_enrichment(pool, settings))

    return ImportResponse(
        status=ImportStatus.RUNNING,
        source="EPO-Enrichment",
        message="EPO-Enrichment gestartet. Status ueber GET /api/v1/import/status abrufbar.",
    )


async def _run_epo_enrichment(pool: Any, settings: Any) -> None:
    """EPO-Enrichment als Background-Task ausfuehren."""
    try:
        result: EnrichmentResult = await enrich_epo_patents(
            pool=pool,
            data_dir=settings.bulk_data_dir,
            batch_size=settings.batch_size,
        )
        logger.info(
            "epo_enrichment_ergebnis",
            aktualisiert=result.records_updated,
            dateien=result.files_processed,
            dauer=result.duration_seconds,
        )
    except Exception as exc:
        logger.error("epo_enrichment_fehlgeschlagen", error=str(exc))


# ---------------------------------------------------------------------------
# Materialisierte Views aktualisieren
# ---------------------------------------------------------------------------


@router.post(
    "/refresh-views",
    response_model=RefreshResponse,
    summary="Materialisierte Views aktualisieren",
    description=(
        "Ruft cross_schema.refresh_all_views() auf, um alle materialisierten "
        "Views nach einem Datenimport zu aktualisieren."
    ),
    dependencies=[Depends(require_admin_key)],
)
async def refresh_views(request: Request) -> RefreshResponse:
    """Alle materialisierten Views in cross_schema aktualisieren.

    Sollte nach einem erfolgreichen EPO- oder CORDIS-Import aufgerufen
    werden, um die View-Daten auf den neuesten Stand zu bringen.
    """
    pool = request.app.state.db_pool
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="Datenbankverbindung nicht verfuegbar.",
        )

    logger.info("view_refresh_gestartet")
    start_time = time.monotonic()

    try:
        async with pool.acquire() as conn:
            await conn.execute("SELECT cross_schema.refresh_all_views()")

        duration = round(time.monotonic() - start_time, 2)
        logger.info("view_refresh_abgeschlossen", dauer_sekunden=duration)

        return RefreshResponse(
            status="success",
            message="Alle materialisierten Views erfolgreich aktualisiert.",
            duration_seconds=duration,
        )

    except Exception as exc:
        duration = round(time.monotonic() - start_time, 2)
        logger.error("view_refresh_fehler", error=str(exc), dauer_sekunden=duration)
        raise HTTPException(
            status_code=500,
            detail="Import fehlgeschlagen. Siehe Server-Logs.",
        ) from exc


# ---------------------------------------------------------------------------
# API Delta-Update (EPO OPS + CORDIS REST API)
# ---------------------------------------------------------------------------


@router.post(
    "/api-delta",
    summary="API-basierte Delta-Updates manuell ausloesen",
    description=(
        "Startet einen API-Delta-Update im Hintergrund. EPO OPS und CORDIS REST APIs "
        "werden fuer die zuletzt gesuchten Technologien abgefragt. API-Daten ueberschreiben "
        "bestehende Bulk-Eintraege (ON CONFLICT DO UPDATE)."
    ),
    dependencies=[Depends(require_admin_key)],
)
async def trigger_api_delta(request: Request) -> dict[str, str]:
    """Manueller Trigger fuer API-basierte Delta-Updates."""
    import asyncio

    from src.scheduler import daily_api_delta_job

    asyncio.create_task(daily_api_delta_job(request.app))
    return {
        "status": "Delta-Update gestartet",
        "message": "EPO OPS + CORDIS API Updates laufen im Hintergrund",
    }


# ---------------------------------------------------------------------------
# Scheduler-Status Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/schedule",
    summary="Import-Schedule-Status abfragen",
    description="Gibt den aktuellen Scheduler-Status, naechste Ausfuehrung und letztes Ergebnis zurueck.",
)
async def get_schedule_status_endpoint(request: Request) -> dict[str, Any]:
    """Scheduler-Status zurueckgeben."""
    from src.scheduler import get_schedule_status

    scheduler = getattr(request.app.state, "scheduler", None)
    return get_schedule_status(scheduler)
