"""Export-Endpoints fuer CSV, JSON, Excel, PDF und Batch-Export.

Stellt REST-Endpoints bereit, um Analyseergebnisse in verschiedenen
Formaten herunterzuladen. Ergebnisse werden in export_schema.analysis_cache
gecacht und bei Bedarf frisch vom Orchestrator geholt.

Endpoints:
  POST /api/v1/export/csv   — CSV-Download (StreamingResponse)
  POST /api/v1/export/json  — JSON-Download
  POST /api/v1/export/xlsx  — Excel-Download (StreamingResponse)
  POST /api/v1/export/pdf   — PDF-Report-Download (StreamingResponse)
  POST /api/v1/export/batch — ZIP-Batch-Export (mehrere Technologien)
  GET  /api/v1/export/history — Export-Log abfragen
  DELETE /api/v1/export/cache — Abgelaufene Cache-Eintraege loeschen
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
import hmac
import io
import json
import os
import time
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg
import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Security
from fastapi.responses import JSONResponse, StreamingResponse
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

from src.config import Settings
from src.exporters.csv_exporter import export_csv
from src.exporters.excel_exporter import export_excel
from src.exporters.pdf_exporter import generate_pdf

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/export", tags=["Export"])


# ---------------------------------------------------------------------------
# Request- / Response-Modelle
# ---------------------------------------------------------------------------


class ExportRequest(BaseModel):
    """Anfrage fuer einen Datenexport.

    Definiert die Parameter fuer die Analyse, deren Ergebnisse
    exportiert werden sollen. Entspricht im Wesentlichen den
    Parametern des Orchestrator RadarRequest.
    """

    technology: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Technologie-Suchbegriff (z.B. 'solid-state batteries')",
    )
    start_year: int = Field(
        default=2015,
        ge=1990,
        le=2030,
        description="Startjahr des Analysezeitraums",
    )
    end_year: int = Field(
        default=2025,
        ge=1990,
        le=2030,
        description="Endjahr des Analysezeitraums",
    )
    use_cases: list[str] = Field(
        default_factory=list,
        description="Selektive UC-Auswahl (leer = alle 12 UCs)",
    )
    european_only: bool = Field(
        default=False,
        description="Nur EU-27 + assoziierte Laender beruecksichtigen",
    )


class ExportHistoryEntry(BaseModel):
    """Ein Eintrag im Export-Log."""

    id: int
    technology: str
    export_format: str
    use_cases: list[str]
    row_count: int
    file_size_bytes: int
    duration_ms: int
    created_at: str
    client_ip: str
    request_id: str


class CachePurgeResult(BaseModel):
    """Ergebnis der Cache-Bereinigung."""

    deleted_count: int
    message: str


class WebhookCreate(BaseModel):
    """Registrierung eines Webhooks fuer Event-Benachrichtigungen.

    Implementiert das Event-Hub-Pattern (Pub/Sub): Der Client registriert
    eine Callback-URL und wird bei relevanten Events automatisch per
    HTTP POST benachrichtigt.
    """

    callback_url: str = Field(
        ...,
        description="URL, an die Event-Payloads per HTTP POST gesendet werden",
    )
    events: list[str] = Field(
        ...,
        min_length=1,
        description="Event-Typen zum Abonnieren: export.completed, export.failed, cache.purged",
    )
    secret: str = Field(
        default="",
        description="Optionaler HMAC-Secret fuer Payload-Signierung (X-Webhook-Signature)",
    )


class WebhookResponse(BaseModel):
    """Bestaetigung einer Webhook-Registrierung."""

    id: str
    callback_url: str
    events: list[str]
    created_at: str


class BatchExportRequest(BaseModel):
    """Anfrage fuer einen Batch-Export (mehrere Technologien als ZIP).

    Generiert fuer jede Technologie eine separate CSV-Datei und
    buendelt diese in einem ZIP-Archiv.
    """

    technologies: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Liste von Technologien (max. 20 pro Batch)",
    )
    start_year: int = Field(
        default=2015,
        ge=1990,
        le=2030,
        description="Startjahr des Analysezeitraums",
    )
    end_year: int = Field(
        default=2025,
        ge=1990,
        le=2030,
        description="Endjahr des Analysezeitraums",
    )
    use_cases: list[str] = Field(
        default_factory=list,
        description="Selektive UC-Auswahl (leer = alle 12 UCs)",
    )
    european_only: bool = Field(
        default=False,
        description="Nur EU-27 + assoziierte Laender beruecksichtigen",
    )


# ---------------------------------------------------------------------------
# Hilfsfunktionen: Cache-Verwaltung
# ---------------------------------------------------------------------------


def _build_cache_key(req: ExportRequest) -> str:
    """Erzeugt einen deterministischen Cache-Key aus den Request-Parametern.

    Verwendet SHA-256 ueber die normalisierten Parameter, damit
    identische Anfragen denselben Cache-Eintrag treffen.
    """
    normalized = {
        "technology": req.technology.strip().lower(),
        "start_year": req.start_year,
        "end_year": req.end_year,
        "use_cases": sorted(req.use_cases),
        "european_only": req.european_only,
    }
    raw = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


async def _get_cached_result(
    pool: asyncpg.Pool,
    cache_key: str,
) -> dict[str, Any] | None:
    """Sucht ein gueltiges (nicht abgelaufenes) Cache-Ergebnis.

    Returns:
        Das gecachte RadarResponse-JSON oder None falls kein Treffer.
    """
    row = await pool.fetchrow(
        """
        SELECT result_json
        FROM export_schema.analysis_cache
        WHERE cache_key = $1
          AND expires_at > NOW()
        ORDER BY created_at DESC
        LIMIT 1
        """,
        cache_key,
    )
    if row is not None:
        logger.info("cache_treffer", cache_key=cache_key[:12])
        return json.loads(row["result_json"]) if isinstance(row["result_json"], str) else row["result_json"]
    return None


async def _store_cache_result(
    pool: asyncpg.Pool,
    cache_key: str,
    req: ExportRequest,
    result: dict[str, Any],
    ttl_hours: int,
) -> None:
    """Speichert ein Analyseergebnis im Cache.

    Verwendet INSERT ... ON CONFLICT DO UPDATE, damit bei erneutem
    Aufruf mit denselben Parametern der Cache aktualisiert wird.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    result_json = json.dumps(result, ensure_ascii=False, default=str)

    await pool.execute(
        """
        INSERT INTO export_schema.analysis_cache
            (cache_key, technology, start_year, end_year, european_only,
             use_cases, result_json, expires_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
        ON CONFLICT (cache_key) DO UPDATE SET
            result_json = EXCLUDED.result_json,
            created_at = NOW(),
            expires_at = EXCLUDED.expires_at
        """,
        cache_key,
        req.technology,
        req.start_year,
        req.end_year,
        req.european_only,
        req.use_cases,
        result_json,
        expires_at,
    )
    logger.info("cache_gespeichert", cache_key=cache_key[:12], ttl_hours=ttl_hours)


async def _log_export(
    pool: asyncpg.Pool,
    technology: str,
    export_format: str,
    use_cases: list[str],
    row_count: int,
    file_size_bytes: int,
    duration_ms: int,
    client_ip: str,
    request_id: str,
) -> None:
    """Schreibt einen Eintrag ins Export-Log (Audit-Trail)."""
    try:
        await pool.execute(
            """
            INSERT INTO export_schema.export_log
                (technology, export_format, use_cases, row_count,
                 file_size_bytes, duration_ms, client_ip, request_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            technology,
            export_format,
            use_cases,
            row_count,
            file_size_bytes,
            duration_ms,
            client_ip,
            request_id,
        )
    except Exception as exc:
        # Export-Log-Fehler sind nicht kritisch — nur loggen
        logger.warning("export_log_fehler", error=str(exc))


# ---------------------------------------------------------------------------
# Hilfsfunktion: Daten vom Orchestrator holen (oder aus Cache)
# ---------------------------------------------------------------------------


async def _get_analysis_data(
    request: Request,
    req: ExportRequest,
) -> dict[str, Any]:
    """Holt Analyseergebnisse — zuerst aus Cache, dann vom Orchestrator.

    1. Cache-Lookup in export_schema.analysis_cache
    2. Falls kein Treffer: POST /api/v1/radar am Orchestrator
    3. Ergebnis im Cache speichern

    Raises:
        HTTPException: Bei Orchestrator-Fehlern oder Timeout.
    """
    pool: asyncpg.Pool | None = request.app.state.db_pool
    client: httpx.AsyncClient = request.app.state.http_client
    settings: Settings = request.app.state.settings

    cache_key = _build_cache_key(req)

    # 1. Cache pruefen
    if pool is not None:
        try:
            cached = await _get_cached_result(pool, cache_key)
            if cached is not None:
                return cached
        except Exception as exc:
            logger.warning("cache_lookup_fehler", error=str(exc))

    # 2. Frische Daten vom Orchestrator holen
    logger.info(
        "orchestrator_anfrage",
        technology=req.technology,
        start_year=req.start_year,
        end_year=req.end_year,
        use_cases=req.use_cases,
    )

    years = req.end_year - req.start_year
    orchestrator_payload = {
        "technology": req.technology,
        "years": max(years, 3),
        "european_only": req.european_only,
        "use_cases": req.use_cases,
    }

    try:
        resp = await client.post("/api/v1/radar", json=orchestrator_payload)
        resp.raise_for_status()
        result = resp.json()
    except httpx.TimeoutException:
        logger.error("orchestrator_timeout", technology=req.technology)
        raise HTTPException(
            status_code=504,
            detail="Orchestrator-Service Timeout — bitte spaeter erneut versuchen",
        )
    except httpx.HTTPStatusError as exc:
        logger.error(
            "orchestrator_http_fehler",
            status=exc.response.status_code,
            detail=exc.response.text[:500],
        )
        raise HTTPException(
            status_code=502,
            detail=f"Orchestrator-Fehler: HTTP {exc.response.status_code}",
        )
    except httpx.HTTPError as exc:
        logger.error("orchestrator_verbindungsfehler", error=str(exc))
        raise HTTPException(
            status_code=502,
            detail="Orchestrator-Service nicht erreichbar",
        )

    # 3. Ergebnis cachen
    if pool is not None:
        try:
            await _store_cache_result(pool, cache_key, req, result, settings.cache_ttl_hours)
        except Exception as exc:
            logger.warning("cache_store_fehler", error=str(exc))

    return result


# ---------------------------------------------------------------------------
# POST /api/v1/export/csv
# ---------------------------------------------------------------------------


@router.post("/csv", summary="CSV-Export der Analyseergebnisse", dependencies=[Depends(require_admin_key)])
async def export_csv_endpoint(
    req: ExportRequest,
    request: Request,
) -> StreamingResponse:
    """Exportiert Analyseergebnisse als CSV-Datei.

    Generiert eine CSV-Datei mit einer Sektion pro Use-Case.
    Jeder UC hat spezifische Spaltenkoepfe (z.B. UC1: year, patent_count, ...).
    """
    t0 = time.monotonic()

    # Daten holen (Cache oder Orchestrator)
    data = await _get_analysis_data(request, req)

    # Relevante Use-Cases bestimmen
    uc_list = req.use_cases if req.use_cases else _all_uc_names()

    # CSV generieren
    csv_bytes = await export_csv(data, uc_list)

    duration_ms = int((time.monotonic() - t0) * 1000)

    # Export-Log schreiben
    pool: asyncpg.Pool | None = request.app.state.db_pool
    if pool is not None:
        client_ip = request.client.host if request.client else ""
        await _log_export(
            pool=pool,
            technology=req.technology,
            export_format="csv",
            use_cases=uc_list,
            row_count=csv_bytes.count(b"\n"),
            file_size_bytes=len(csv_bytes),
            duration_ms=duration_ms,
            client_ip=client_ip,
            request_id="",
        )

    logger.info(
        "csv_export_abgeschlossen",
        technology=req.technology,
        size_bytes=len(csv_bytes),
        duration_ms=duration_ms,
    )

    # Dateiname mit Technologie und Zeitstempel
    safe_tech = req.technology.replace(" ", "_").replace("/", "-")[:50]
    filename = f"ti-radar_{safe_tech}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(csv_bytes)),
        },
    )


# ---------------------------------------------------------------------------
# POST /api/v1/export/json
# ---------------------------------------------------------------------------


@router.post("/json", summary="JSON-Export der Analyseergebnisse", dependencies=[Depends(require_admin_key)])
async def export_json_endpoint(
    req: ExportRequest,
    request: Request,
) -> JSONResponse:
    """Exportiert Analyseergebnisse als JSON.

    Gibt das vollstaendige RadarResponse-JSON zurueck, optional
    gefiltert auf bestimmte Use-Cases.
    """
    t0 = time.monotonic()

    # Daten holen (Cache oder Orchestrator)
    data = await _get_analysis_data(request, req)

    # Optional: Nur angeforderte UCs zurueckgeben
    if req.use_cases:
        uc_panel_map = _uc_to_panel_map()
        filtered: dict[str, Any] = {
            "technology": data.get("technology", req.technology),
            "analysis_period": data.get("analysis_period", f"{req.start_year}-{req.end_year}"),
        }
        for uc_name in req.use_cases:
            panel_key = uc_panel_map.get(uc_name, uc_name)
            filtered[panel_key] = data.get(panel_key, {})
        # Metadaten beibehalten
        for meta_key in ("uc_errors", "explainability", "total_processing_time_ms",
                         "successful_uc_count", "total_uc_count", "timestamp"):
            if meta_key in data:
                filtered[meta_key] = data[meta_key]
        export_data = filtered
    else:
        export_data = data

    duration_ms = int((time.monotonic() - t0) * 1000)
    result_bytes = json.dumps(export_data, ensure_ascii=False, indent=2, default=str).encode()

    # Export-Log schreiben
    pool: asyncpg.Pool | None = request.app.state.db_pool
    if pool is not None:
        client_ip = request.client.host if request.client else ""
        await _log_export(
            pool=pool,
            technology=req.technology,
            export_format="json",
            use_cases=req.use_cases if req.use_cases else _all_uc_names(),
            row_count=0,
            file_size_bytes=len(result_bytes),
            duration_ms=duration_ms,
            client_ip=client_ip,
            request_id="",
        )

    logger.info(
        "json_export_abgeschlossen",
        technology=req.technology,
        size_bytes=len(result_bytes),
        duration_ms=duration_ms,
    )

    safe_tech = req.technology.replace(" ", "_").replace("/", "-")[:50]
    filename = f"ti-radar_{safe_tech}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ---------------------------------------------------------------------------
# POST /api/v1/export/xlsx
# ---------------------------------------------------------------------------


@router.post("/xlsx", summary="Excel-Export der Analyseergebnisse", dependencies=[Depends(require_admin_key)])
async def export_xlsx_endpoint(
    req: ExportRequest,
    request: Request,
) -> StreamingResponse:
    """Exportiert Analyseergebnisse als Excel-Datei (.xlsx).

    Erstellt ein Workbook mit einem Tabellenblatt pro Use-Case.
    Header-Zeilen sind fett und hellblau hinterlegt, Geldwerte
    erhalten ein Zahlenformat.
    """
    t0 = time.monotonic()

    # Daten holen (Cache oder Orchestrator)
    data = await _get_analysis_data(request, req)

    # Relevante Use-Cases bestimmen
    uc_list = req.use_cases if req.use_cases else _all_uc_names()

    # Excel generieren
    xlsx_bytes = await export_excel(data, uc_list)

    duration_ms = int((time.monotonic() - t0) * 1000)

    # Export-Log schreiben
    pool: asyncpg.Pool | None = request.app.state.db_pool
    if pool is not None:
        client_ip = request.client.host if request.client else ""
        await _log_export(
            pool=pool,
            technology=req.technology,
            export_format="xlsx",
            use_cases=uc_list,
            row_count=0,
            file_size_bytes=len(xlsx_bytes),
            duration_ms=duration_ms,
            client_ip=client_ip,
            request_id="",
        )

    logger.info(
        "xlsx_export_abgeschlossen",
        technology=req.technology,
        size_bytes=len(xlsx_bytes),
        duration_ms=duration_ms,
    )

    safe_tech = req.technology.replace(" ", "_").replace("/", "-")[:50]
    filename = f"ti-radar_{safe_tech}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return StreamingResponse(
        iter([xlsx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(xlsx_bytes)),
        },
    )


# ---------------------------------------------------------------------------
# POST /api/v1/export/pdf
# ---------------------------------------------------------------------------


@router.post("/pdf", summary="PDF-Report der Analyseergebnisse", dependencies=[Depends(require_admin_key)])
async def export_pdf_endpoint(
    req: ExportRequest,
    request: Request,
) -> StreamingResponse:
    """Exportiert Analyseergebnisse als professionellen PDF-Report.

    Generiert ein A4-Querformat-Dokument mit Titelseite,
    Inhaltsverzeichnis, einer Sektion pro Use-Case (inkl. Datentabellen)
    und einem Anhang mit Methodik und Datenquellen.
    """
    t0 = time.monotonic()

    # Daten holen (Cache oder Orchestrator)
    data = await _get_analysis_data(request, req)

    # Relevante Use-Cases bestimmen
    uc_list = req.use_cases if req.use_cases else _all_uc_names()

    # PDF generieren
    pdf_bytes = await generate_pdf(req.technology, data, uc_list)

    duration_ms = int((time.monotonic() - t0) * 1000)

    # Export-Log schreiben
    pool: asyncpg.Pool | None = request.app.state.db_pool
    if pool is not None:
        client_ip = request.client.host if request.client else ""
        await _log_export(
            pool=pool,
            technology=req.technology,
            export_format="pdf",
            use_cases=uc_list,
            row_count=0,
            file_size_bytes=len(pdf_bytes),
            duration_ms=duration_ms,
            client_ip=client_ip,
            request_id="",
        )

    logger.info(
        "pdf_export_abgeschlossen",
        technology=req.technology,
        size_bytes=len(pdf_bytes),
        duration_ms=duration_ms,
    )

    safe_tech = req.technology.replace(" ", "_").replace("/", "-")[:50]
    filename = f"ti-radar_{safe_tech}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


# ---------------------------------------------------------------------------
# POST /api/v1/export/batch
# ---------------------------------------------------------------------------


@router.post("/batch", summary="Batch-Export als ZIP-Archiv", dependencies=[Depends(require_admin_key)])
async def export_batch_endpoint(
    req: BatchExportRequest,
    request: Request,
) -> StreamingResponse:
    """Exportiert Analyseergebnisse fuer mehrere Technologien als ZIP.

    Generiert pro Technologie eine separate CSV-Datei und buendelt
    alle Dateien in einem ZIP-Archiv. Fehlgeschlagene Technologien
    werden uebersprungen und im Log dokumentiert.
    """
    t0 = time.monotonic()

    uc_list = req.use_cases if req.use_cases else _all_uc_names()
    zip_buffer = io.BytesIO()
    files_added = 0
    errors: list[str] = []

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for technology in req.technologies:
            # ExportRequest fuer jede einzelne Technologie erstellen
            single_req = ExportRequest(
                technology=technology,
                start_year=req.start_year,
                end_year=req.end_year,
                use_cases=req.use_cases,
                european_only=req.european_only,
            )

            try:
                data = await _get_analysis_data(request, single_req)
                csv_bytes = await export_csv(data, uc_list)

                # Dateiname im ZIP (sicher und eindeutig)
                safe_tech = technology.replace(" ", "_").replace("/", "-")[:50]
                csv_filename = f"{safe_tech}.csv"
                zf.writestr(csv_filename, csv_bytes)
                files_added += 1

                logger.info("batch_csv_erstellt", technology=technology, size=len(csv_bytes))

            except HTTPException as exc:
                # Orchestrator-Fehler — Technologie ueberspringen, nicht abbrechen
                errors.append(f"{technology}: HTTP {exc.status_code} — {exc.detail}")
                logger.warning(
                    "batch_technologie_uebersprungen",
                    technology=technology,
                    error=exc.detail,
                )
            except Exception as exc:
                errors.append(f"{technology}: {type(exc).__name__} — {str(exc)[:200]}")
                logger.warning(
                    "batch_technologie_fehler",
                    technology=technology,
                    error=str(exc),
                )

        # Fehlerprotokoll als separate Datei im ZIP (falls Fehler auftraten)
        if errors:
            error_text = "Batch-Export Fehlerprotokoll\n"
            error_text += "=" * 40 + "\n\n"
            for err in errors:
                error_text += f"- {err}\n"
            zf.writestr("_fehler.txt", error_text.encode("utf-8"))

    if files_added == 0:
        raise HTTPException(
            status_code=502,
            detail="Batch-Export fehlgeschlagen — keine Technologie konnte exportiert werden",
        )

    zip_bytes = zip_buffer.getvalue()
    duration_ms = int((time.monotonic() - t0) * 1000)

    # Export-Log schreiben
    pool: asyncpg.Pool | None = request.app.state.db_pool
    if pool is not None:
        client_ip = request.client.host if request.client else ""
        await _log_export(
            pool=pool,
            technology=", ".join(req.technologies[:5]),
            export_format="batch_zip",
            use_cases=uc_list,
            row_count=files_added,
            file_size_bytes=len(zip_bytes),
            duration_ms=duration_ms,
            client_ip=client_ip,
            request_id="",
        )

    logger.info(
        "batch_export_abgeschlossen",
        technologies=len(req.technologies),
        files_added=files_added,
        errors=len(errors),
        size_bytes=len(zip_bytes),
        duration_ms=duration_ms,
    )

    filename = f"ti-radar_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    return StreamingResponse(
        iter([zip_bytes]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(zip_bytes)),
        },
    )


# ---------------------------------------------------------------------------
# GET /api/v1/export/history
# ---------------------------------------------------------------------------


@router.get(
    "/history",
    response_model=list[ExportHistoryEntry],
    summary="Export-Historie abfragen",
)
async def export_history(
    request: Request,
    response: Response,
    limit: int = 50,
    offset: int = 0,
) -> list[ExportHistoryEntry]:
    """Gibt die letzten Export-Log-Eintraege zurueck (paginiert).

    Nuetzlich fuer Audit-Trails und Nutzungsstatistiken.
    Der Response-Header ``X-Total-Count`` enthaelt die Gesamtanzahl aller
    Eintraege, unabhaengig von offset/limit.
    """
    pool: asyncpg.Pool | None = request.app.state.db_pool
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="Datenbank nicht verfuegbar — Export-Historie kann nicht abgefragt werden",
        )

    clamped_limit = min(limit, 500)

    total_count, rows = await asyncio.gather(
        pool.fetchval("SELECT COUNT(*) FROM export_schema.export_log"),
        pool.fetch(
            """
            SELECT id, technology, export_format, use_cases, row_count,
                   file_size_bytes, duration_ms, created_at, client_ip, request_id
            FROM export_schema.export_log
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            clamped_limit,
            offset,
        ),
    )

    response.headers["X-Total-Count"] = str(total_count or 0)

    return [
        ExportHistoryEntry(
            id=row["id"],
            technology=row["technology"],
            export_format=row["export_format"],
            use_cases=list(row["use_cases"]) if row["use_cases"] else [],
            row_count=row["row_count"],
            file_size_bytes=row["file_size_bytes"],
            duration_ms=row["duration_ms"],
            created_at=row["created_at"].isoformat() if row["created_at"] else "",
            client_ip=row["client_ip"] or "",
            request_id=row["request_id"] or "",
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# DELETE /api/v1/export/cache
# ---------------------------------------------------------------------------


@router.delete(
    "/cache",
    response_model=CachePurgeResult,
    summary="Abgelaufene Cache-Eintraege loeschen",
    dependencies=[Depends(require_admin_key)],
)
async def purge_expired_cache(request: Request) -> CachePurgeResult:
    """Loescht alle abgelaufenen Eintraege aus export_schema.analysis_cache.

    Kann manuell oder per Cron-Job aufgerufen werden, um Speicherplatz
    in der Datenbank freizugeben.
    """
    pool: asyncpg.Pool | None = request.app.state.db_pool
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="Datenbank nicht verfuegbar — Cache kann nicht bereinigt werden",
        )

    result = await pool.execute(
        """
        DELETE FROM export_schema.analysis_cache
        WHERE expires_at < NOW()
        """
    )

    # asyncpg gibt z.B. "DELETE 5" zurueck
    deleted_count = 0
    if result and result.startswith("DELETE"):
        parts = result.split()
        if len(parts) >= 2:
            try:
                deleted_count = int(parts[1])
            except ValueError:
                pass

    logger.info("cache_bereinigt", deleted_count=deleted_count)

    result = CachePurgeResult(
        deleted_count=deleted_count,
        message=f"{deleted_count} abgelaufene Cache-Eintraege geloescht",
    )

    # Webhook-Benachrichtigung (Event-Hub Pattern)
    await notify_webhooks("cache.purged", {
        "event": "cache.purged",
        "deleted_count": deleted_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return result


# ---------------------------------------------------------------------------
# POST /api/v1/export/webhooks  +  DELETE /api/v1/export/webhooks/{id}
# ---------------------------------------------------------------------------

# In-Memory Webhook-Registry (MVP — fuer Produktion: Datenbank-Tabelle)
_webhook_registry: dict[str, dict[str, Any]] = {}

VALID_WEBHOOK_EVENTS = frozenset({
    "export.completed",
    "export.failed",
    "cache.purged",
})


@router.post(
    "/webhooks",
    response_model=WebhookResponse,
    status_code=201,
    summary="Webhook registrieren (Event-Hub Pattern)",
)
async def register_webhook(webhook: WebhookCreate) -> WebhookResponse:
    """Registriert einen Webhook fuer Event-Benachrichtigungen.

    Der Client gibt eine Callback-URL und eine Liste von Event-Typen an.
    Bei jedem relevanten Event sendet der Export-Service einen HTTP POST
    mit dem Event-Payload an die Callback-URL.

    Gueltige Event-Typen: ``export.completed``, ``export.failed``, ``cache.purged``
    """
    invalid = set(webhook.events) - VALID_WEBHOOK_EVENTS
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Ungueltige Event-Typen: {', '.join(sorted(invalid))}. "
                   f"Gueltig: {', '.join(sorted(VALID_WEBHOOK_EVENTS))}",
        )

    webhook_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()

    _webhook_registry[webhook_id] = {
        "callback_url": webhook.callback_url,
        "events": webhook.events,
        "secret": webhook.secret,
        "created_at": now,
    }

    logger.info(
        "webhook_registriert",
        webhook_id=webhook_id,
        callback_url=webhook.callback_url,
        events=webhook.events,
    )

    return WebhookResponse(
        id=webhook_id,
        callback_url=webhook.callback_url,
        events=webhook.events,
        created_at=now,
    )


@router.delete(
    "/webhooks/{webhook_id}",
    status_code=204,
    summary="Webhook abmelden",
)
async def unregister_webhook(webhook_id: str) -> None:
    """Entfernt eine bestehende Webhook-Registrierung."""
    if webhook_id not in _webhook_registry:
        raise HTTPException(status_code=404, detail="Webhook nicht gefunden")

    del _webhook_registry[webhook_id]
    logger.info("webhook_abgemeldet", webhook_id=webhook_id)


@router.get(
    "/webhooks",
    response_model=list[WebhookResponse],
    summary="Registrierte Webhooks auflisten",
)
async def list_webhooks() -> list[WebhookResponse]:
    """Gibt alle registrierten Webhooks zurueck."""
    return [
        WebhookResponse(
            id=wh_id,
            callback_url=wh["callback_url"],
            events=wh["events"],
            created_at=wh["created_at"],
        )
        for wh_id, wh in _webhook_registry.items()
    ]


async def notify_webhooks(event_type: str, payload: dict[str, Any]) -> None:
    """Benachrichtigt alle registrierten Webhooks fuer einen Event-Typ.

    Wird intern aufgerufen nach Export-Abschluss oder Cache-Bereinigung.
    Fehler bei der Zustellung werden geloggt, blockieren aber nicht.
    """
    for wh_id, wh in _webhook_registry.items():
        if event_type not in wh["events"]:
            continue
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {"Content-Type": "application/json"}
                if wh.get("secret"):
                    sig = hashlib.sha256(
                        (wh["secret"] + json.dumps(payload, sort_keys=True)).encode()
                    ).hexdigest()
                    headers["X-Webhook-Signature"] = sig
                await client.post(wh["callback_url"], json=payload, headers=headers)
                logger.info("webhook_zugestellt", webhook_id=wh_id, event=event_type)
        except Exception as exc:
            logger.warning(
                "webhook_zustellung_fehlgeschlagen",
                webhook_id=wh_id,
                event=event_type,
                error=str(exc),
            )


# ---------------------------------------------------------------------------
# Hilfsfunktionen: UC-Mapping
# ---------------------------------------------------------------------------


def _all_uc_names() -> list[str]:
    """Gibt alle 12 UC-Bezeichnungen zurueck."""
    return [
        "landscape", "maturity", "competitive", "funding",
        "cpc_flow", "geographic", "research_impact", "temporal",
        "tech_cluster", "actor_type", "patent_grant", "euroscivoc",
    ]


def _uc_to_panel_map() -> dict[str, str]:
    """Mapping von UC-Name auf Panel-Key im RadarResponse.

    In der aktuellen Implementierung sind UC-Name und Panel-Key
    identisch, aber dieses Mapping ermoeglicht zukuenftige Aenderungen.
    """
    names = _all_uc_names()
    return {name: name for name in names}
