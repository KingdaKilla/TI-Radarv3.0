"""FastAPI Application Factory fuer den Orchestrator Service.

Erstellt und konfiguriert die FastAPI-Anwendung mit:
- CORS-Middleware (konfigurierbar via CORS_ORIGINS)
- Request-ID-Middleware (X-Request-ID Propagation)
- Lifespan-Management (gRPC-Channel-Pool + DB-Pool)
- Strukturiertes Logging via structlog
- Prometheus-Metriken
- Drei Router: Radar, Health/Metrics, Suggestions
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import Settings
from src.grpc_clients import GrpcChannelManager
from src.middleware import RateLimitMiddleware, RequestIdMiddleware
from src.router_health import router as health_router
from src.router_radar import router as radar_router
from src.router_suggestions import router as suggestions_router

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Structlog konfigurieren (einmalig beim Import)
# ---------------------------------------------------------------------------


def _configure_structlog() -> None:
    """Konfiguriert structlog fuer strukturiertes JSON-Logging.

    Entwicklungsmodus: farbige Console-Ausgabe (human-readable).
    Produktion: JSON-Lines fuer Log-Aggregatoren (ELK, Loki).
    """
    settings = Settings()
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
        # Farbige Console-Ausgabe im Entwicklungsmodus
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # JSON-Lines fuer Produktion
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ---------------------------------------------------------------------------
# Lifespan: gRPC-Channels + DB-Pool Lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Verwaltet den Lebenszyklus von gRPC-Channels und DB-Pool.

    Startup:
      1. gRPC Channel-Pool initialisieren (lazy Channels zu 12 UC-Services)
      2. asyncpg Connection-Pool zur PostgreSQL-Datenbank aufbauen
      3. Konfiguration loggen

    Shutdown:
      1. Alle gRPC-Channels graceful schliessen
      2. DB-Pool schliessen
    """
    settings = Settings()

    # --- Startup ---
    logger.info(
        "orchestrator_startup",
        host=settings.host,
        port=settings.port,
        cors_origins=settings.cors_origin_list,
        debug=settings.debug,
    )

    # gRPC Channel-Manager initialisieren
    channel_manager = GrpcChannelManager(settings)
    app.state.grpc_channels = channel_manager

    uc_configs = settings.get_uc_configs()
    for uc_name, config in uc_configs.items():
        logger.info(
            "uc_service_konfiguriert",
            uc=uc_name,
            address=config.address,
            timeout=config.timeout,
        )

    # asyncpg Connection-Pool aufbauen
    app.state.db_pool = None
    try:
        import asyncpg

        pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
            command_timeout=10.0,
        )
        app.state.db_pool = pool
        logger.info("db_pool_erstellt", dsn=_mask_dsn(settings.database_url))
    except ImportError:
        logger.warning("asyncpg_nicht_installiert", hint="pip install asyncpg")
    except Exception as exc:
        logger.warning(
            "db_pool_fehler",
            error=str(exc),
            hint="Suggestions-Endpoint nicht verfuegbar",
        )

    logger.info("orchestrator_bereit", version="3.0.0")

    yield

    # --- Shutdown ---
    logger.info("orchestrator_shutdown_gestartet")

    # gRPC-Channels schliessen
    await channel_manager.close()

    # DB-Pool schliessen
    if app.state.db_pool is not None:
        await app.state.db_pool.close()
        logger.info("db_pool_geschlossen")

    logger.info("orchestrator_shutdown_abgeschlossen")


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _mask_dsn(dsn: str) -> str:
    """Maskiert das Passwort in einem DSN-String fuer sichere Ausgabe."""
    # postgresql://user:PASSWORD@host:port/db -> postgresql://user:***@host:port/db
    import re

    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", dsn)


# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Erstellt und konfiguriert die FastAPI-Anwendung.

    Wird als Factory-Funktion aufgerufen:
    uvicorn src.main:create_app --factory --port 8000
    """
    _configure_structlog()
    settings = Settings()

    _debug = os.getenv("DEBUG", "").lower() == "true"

    app = FastAPI(
        title="TI-Radar Orchestrator",
        description=(
            "Technology Intelligence Radar v3 — API-Gateway mit gRPC-Fan-Out "
            "zu 13 UC-Microservices. Implementiert Graceful Degradation, "
            "Per-UC-Timeouts und Prometheus-Metriken."
        ),
        version="3.0.0",
        lifespan=lifespan,
        docs_url="/docs" if _debug else None,
        redoc_url="/redoc" if _debug else None,
        openapi_url="/openapi.json" if _debug else None,
    )

    # --- Middleware (Reihenfolge: aussen -> innen) ---

    # 1. CORS (muss vor Request-ID sein, damit Preflight-Requests durchkommen)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # 2. Rate Limiting (100 Requests/Minute pro IP, Health-Checks ausgenommen)
    app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

    # 3. Request-ID + strukturiertes Logging + Metriken
    app.add_middleware(RequestIdMiddleware)

    # --- Router registrieren ---
    app.include_router(radar_router)
    app.include_router(health_router)
    app.include_router(suggestions_router)

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
