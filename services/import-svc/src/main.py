"""FastAPI Application Factory fuer den Import Service.

Erstellt und konfiguriert die FastAPI-Anwendung mit:
- Lifespan-Management (asyncpg Connection-Pool)
- CORS-Middleware (konfigurierbar via CORS_ORIGINS)
- Import-Router (EPO + CORDIS Bulk-Import)
- Health-Endpoint
- Strukturiertes Logging via structlog
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import logging

import asyncpg
import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import Settings
from src.router_import import router as import_router

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Structlog konfigurieren (einmalig beim Import)
# ---------------------------------------------------------------------------


def _configure_structlog(*, debug: bool = False) -> None:
    """Konfiguriert structlog fuer strukturiertes JSON-Logging.

    Entwicklungsmodus: farbige Console-Ausgabe (human-readable).
    Produktion: JSON-Lines fuer Log-Aggregatoren (ELK, Loki).
    """
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if debug:
        # Farbige Console-Ausgabe im Entwicklungsmodus
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # JSON-Lines fuer Produktion
        processors.append(structlog.processors.JSONRenderer())

    # Python stdlib-Logging konfigurieren (Handler + Level)
    logging.basicConfig(format="%(message)s", stream=__import__("sys").stdout, level=logging.DEBUG)
    logging.getLogger().setLevel(logging.DEBUG)

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
    import re

    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", dsn)


# ---------------------------------------------------------------------------
# Lifespan: asyncpg Pool Lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Verwaltet den Lebenszyklus des asyncpg Connection-Pools.

    Startup:
      1. asyncpg Connection-Pool zur PostgreSQL-Datenbank aufbauen
      2. Konfiguration loggen

    Shutdown:
      1. Connection-Pool graceful schliessen
    """
    settings = Settings()

    # --- Startup ---
    logger.info(
        "import_svc_startup",
        bulk_data_dir=settings.bulk_data_dir,
        batch_size=settings.batch_size,
        max_workers=settings.max_workers,
        debug=settings.debug,
    )

    # asyncpg Connection-Pool aufbauen
    app.state.db_pool = None
    try:
        pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=settings.max_workers + 2,
            command_timeout=300.0,  # Bulk-Imports brauchen laengere Timeouts
        )
        app.state.db_pool = pool
        logger.info("db_pool_erstellt", dsn=_mask_dsn(settings.database_url))
    except Exception as exc:
        logger.error(
            "db_pool_fehler",
            error=str(exc),
            hint="Import-Endpoints nicht verfuegbar ohne Datenbankverbindung",
        )

    # Settings in app.state speichern fuer Router-Zugriff
    app.state.settings = settings

    logger.info("import_svc_bereit", version="2.0.0")

    yield

    # --- Shutdown ---
    logger.info("import_svc_shutdown_gestartet")

    if app.state.db_pool is not None:
        await app.state.db_pool.close()
        logger.info("db_pool_geschlossen")

    logger.info("import_svc_shutdown_abgeschlossen")


# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Erstellt und konfiguriert die FastAPI-Anwendung.

    Wird als Factory-Funktion aufgerufen:
    uvicorn src.main:create_app --factory --host 0.0.0.0 --port 8030
    """
    settings = Settings()
    _configure_structlog(debug=settings.debug)

    app = FastAPI(
        title="TI-Radar Import Service",
        description=(
            "Technology Intelligence Radar v2 — Bulk-Datenimport von "
            "EPO-Patenten und CORDIS-EU-Forschungsprojekten in PostgreSQL 17. "
            "Verwendet asyncpg COPY-Protokoll fuer maximalen Durchsatz."
        ),
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- Middleware ---

    # CORS (Frontend-Zugriff erlauben)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
    )

    # --- Router registrieren ---
    app.include_router(import_router)

    # --- Health Endpoint ---
    @app.get("/healthz", tags=["Health"])
    async def healthz() -> JSONResponse:
        """Liveness-Probe fuer Kubernetes/Docker."""
        db_ok = app.state.db_pool is not None and not app.state.db_pool._closed
        return JSONResponse(
            status_code=200 if db_ok else 503,
            content={
                "status": "healthy" if db_ok else "degraded",
                "service": "import-svc",
                "version": "2.0.0",
                "database": "connected" if db_ok else "disconnected",
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
        )

    return app


# ---------------------------------------------------------------------------
# Direkter Start (Entwicklung)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _settings = Settings()
    uvicorn.run(
        "src.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=8030,
        reload=_settings.debug,
        log_level=_settings.log_level.lower(),
    )
