"""FastAPI Application Factory fuer den Export-Service.

Erstellt und konfiguriert die FastAPI-Anwendung mit:
- Lifespan-Management (asyncpg Pool + httpx.AsyncClient)
- CORS-Middleware
- Export-Router fuer CSV, JSON und Excel-Exports
- Health-Endpoint
- Strukturiertes Logging via structlog
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

import asyncpg
import httpx
import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import Settings
from src.db_schema import ensure_schema as _ensure_schema
from src.router_export import router as export_router

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Structlog konfigurieren
# ---------------------------------------------------------------------------


def _configure_structlog(settings: Settings) -> None:
    """Konfiguriert structlog fuer strukturiertes JSON-Logging.

    Entwicklungsmodus: farbige Console-Ausgabe (human-readable).
    Produktion: JSON-Lines fuer Log-Aggregatoren (ELK, Loki).
    """
    is_dev = settings.debug

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_dev:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _mask_dsn(dsn: str) -> str:
    """Maskiert das Passwort in einem DSN-String fuer sichere Ausgabe."""
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", dsn)


# ---------------------------------------------------------------------------
# Lifespan: asyncpg Pool + httpx.AsyncClient
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Verwaltet den Lebenszyklus von DB-Pool und HTTP-Client.

    Startup:
      1. asyncpg Connection-Pool zur PostgreSQL-Datenbank aufbauen
      2. export_schema erstellen falls nicht vorhanden
      3. httpx.AsyncClient fuer Orchestrator-Aufrufe erstellen

    Shutdown:
      1. HTTP-Client schliessen
      2. DB-Pool schliessen
    """
    settings = Settings()

    logger.info(
        "export_svc_startup",
        host=settings.host,
        port=settings.port,
        orchestrator_url=settings.orchestrator_url,
        cache_ttl_hours=settings.cache_ttl_hours,
    )

    # --- asyncpg Connection-Pool ---
    app.state.db_pool = None
    try:
        pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
            command_timeout=15.0,
        )
        app.state.db_pool = pool
        logger.info("db_pool_erstellt", dsn=_mask_dsn(settings.database_url))
    except Exception as exc:
        logger.warning(
            "db_pool_fehler",
            error=str(exc),
            hint="Export-Caching nicht verfuegbar — Orchestrator-Fallback aktiv",
        )

    # Schema und Tabellen erstellen (nur wenn Pool vorhanden)
    if app.state.db_pool is not None:
        try:
            await _ensure_schema(app.state.db_pool)
        except Exception as exc:
            logger.warning(
                "export_schema_fehler",
                error=str(exc),
                hint="Schema/Tabellen nicht erstellt — Caching evtl. eingeschraenkt",
            )

    # --- httpx.AsyncClient fuer Orchestrator ---
    client = httpx.AsyncClient(
        base_url=settings.orchestrator_url,
        timeout=httpx.Timeout(60.0, connect=10.0),
        headers={"Accept": "application/json"},
    )
    app.state.http_client = client

    # --- Settings im App-State speichern ---
    app.state.settings = settings

    logger.info("export_svc_bereit", version="2.0.0")

    yield

    # --- Shutdown ---
    logger.info("export_svc_shutdown_gestartet")

    await client.aclose()
    logger.info("http_client_geschlossen")

    if app.state.db_pool is not None:
        await app.state.db_pool.close()
        logger.info("db_pool_geschlossen")

    logger.info("export_svc_shutdown_abgeschlossen")


# Schema-Bootstrap-Logik liegt in src/db_schema.py (read-first, vermeidet DB-Log-Spam)
# und wird oben als _ensure_schema importiert.


# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Erstellt und konfiguriert die FastAPI-Anwendung.

    Wird als Factory-Funktion aufgerufen:
    uvicorn src.main:create_app --factory --port 8020
    """
    settings = Settings()
    _configure_structlog(settings)

    app = FastAPI(
        title="TI-Radar Export Service",
        description=(
            "Technology Intelligence Radar v2 — Export-Service fuer "
            "CSV, JSON, Excel, PDF und Batch-Export von Analyseergebnissen. "
            "Cached Orchestrator-Responses und fuehrt Export-Log."
        ),
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- CORS-Middleware ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
    )

    # --- Router registrieren ---
    app.include_router(export_router)

    # --- Health-Endpoint ---
    @app.get("/health", tags=["Health"])
    async def health() -> dict[str, str | bool]:
        """Einfacher Health-Check fuer Load-Balancer und Kubernetes."""
        db_ok = app.state.db_pool is not None
        return {
            "status": "healthy" if db_ok else "degraded",
            "service": "export-svc",
            "version": "2.0.0",
            "database": db_ok,
            "timestamp": datetime.now().isoformat(),
        }

    return app


# ---------------------------------------------------------------------------
# Direkter Start (Entwicklung)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    settings = Settings()
    uvicorn.run(
        "src.main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
