"""gRPC Server fuer den UC2 Maturity Service.

Startet den async gRPC-Server mit:
- MaturityServicer (UC2 S-Curve Analyse)
- Health-Check-Service (gRPC Health Checking Protocol)
- Reflection (fuer grpcurl / grpc-cli Debugging)
- PostgreSQL Connection Pool (asyncpg)
- Graceful Shutdown bei SIGTERM/SIGINT

Verwendung:
    python -m src.server
"""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import Any

import asyncpg
import structlog
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# --- gRPC-Imports (try/except, da Stubs noch nicht generiert) ---
try:
    import grpc
    from grpc import aio as grpc_aio
    from grpc_health.v1 import health as grpc_health
    from grpc_health.v1 import health_pb2
    from grpc_health.v1 import health_pb2_grpc
    from grpc_reflection.v1alpha import reflection
except ImportError as _grpc_err:
    grpc = None  # type: ignore[assignment]
    grpc_aio = None  # type: ignore[assignment]
    grpc_health = None  # type: ignore[assignment]
    health_pb2 = None  # type: ignore[assignment]
    health_pb2_grpc = None  # type: ignore[assignment]
    reflection = None  # type: ignore[assignment]

try:
    from shared.generated.python import uc2_maturity_pb2
    from shared.generated.python import uc2_maturity_pb2_grpc
except ImportError:
    uc2_maturity_pb2 = None  # type: ignore[assignment]
    uc2_maturity_pb2_grpc = None  # type: ignore[assignment]

from src.config import Settings
from src.service import MaturityServicer

# Structlog konfigurieren
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# --- Prometheus Metriken ---
GRPC_REQUEST_COUNT = Counter(
    "grpc_requests_total",
    "Anzahl gRPC-Requests",
    ["service", "method", "status"],
)
GRPC_REQUEST_DURATION = Histogram(
    "grpc_request_duration_seconds",
    "Dauer der gRPC-Requests in Sekunden",
    ["service", "method"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)
DB_POOL_SIZE = Gauge(
    "db_pool_size",
    "Aktuelle DB Connection Pool Groesse",
    ["service"],
)


async def create_db_pool(settings: Settings) -> asyncpg.Pool:
    """PostgreSQL Connection Pool erstellen.

    Verwendet asyncpg fuer hochperformanten async Zugriff.
    Pool-Groesse wird ueber Settings konfiguriert.
    """
    logger.info(
        "db_pool_erstellen",
        url=settings.database_url.split("@")[-1],  # Passwort nicht loggen
        min_size=settings.db_min_connections,
        max_size=settings.db_max_connections,
    )
    pool: asyncpg.Pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=settings.db_min_connections,
        max_size=settings.db_max_connections,
        command_timeout=settings.db_query_timeout_s,
    )
    # Verbindung testen
    async with pool.acquire() as conn:
        version = await conn.fetchval("SELECT version()")
        logger.info("db_verbunden", pg_version=version)
    return pool


async def serve() -> None:
    """Hauptfunktion: gRPC-Server starten und auf Shutdown warten."""
    settings = Settings()

    # --- Prometheus Metrics HTTP-Server (Port 9090) ---
    start_http_server(9090)
    logger.info("prometheus_metrics_gestartet", port=9090)

    # --- Pruefe ob gRPC verfuegbar ---
    if grpc_aio is None:
        logger.error("grpc_nicht_installiert", hinweis="pip install grpcio grpcio-tools")
        sys.exit(1)

    # --- PostgreSQL Pool ---
    pool = await create_db_pool(settings)

    # --- gRPC Server erstellen ---
    server = grpc_aio.server(
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),   # 50 MB
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
            ("grpc.keepalive_time_ms", 300_000),
            ("grpc.keepalive_timeout_ms", 10_000),
            ("grpc.http2.min_recv_ping_interval_without_data_ms", 60_000),
        ],
    )

    # --- Maturity Servicer registrieren ---
    servicer = MaturityServicer(pool=pool, settings=settings)
    if uc2_maturity_pb2_grpc is not None:
        uc2_maturity_pb2_grpc.add_MaturityServiceServicer_to_server(servicer, server)
        logger.info("servicer_registriert", service="MaturityService")
    else:
        logger.warning(
            "stubs_nicht_verfuegbar",
            hinweis="gRPC-Stubs noch nicht generiert — Service startet ohne RPC-Registrierung",
        )

    # --- Health Check Service ---
    if grpc_health is not None and health_pb2_grpc is not None:
        health_servicer = grpc_health.HealthServicer()
        health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
        # Service als SERVING markieren
        if health_pb2 is not None:
            health_servicer.set(
                "tip.uc2.MaturityService",
                health_pb2.HealthCheckResponse.SERVING,
            )
            health_servicer.set(
                "",  # Gesamtstatus
                health_pb2.HealthCheckResponse.SERVING,
            )
        logger.info("health_check_registriert")

    # --- Reflection (fuer grpcurl Debugging) ---
    if reflection is not None and uc2_maturity_pb2 is not None:
        service_names = (
            uc2_maturity_pb2.DESCRIPTOR.services_by_name["MaturityService"].full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(service_names, server)
        logger.info("reflection_aktiviert", services=service_names)

    # --- Port binden und starten ---
    listen_addr = f"{settings.service_host}:{settings.service_port}"
    server.add_insecure_port(listen_addr)
    await server.start()
    logger.info("server_gestartet", adresse=listen_addr)

    # --- Graceful Shutdown ---
    shutdown_event = asyncio.Event()

    def _signal_handler(*_args: Any) -> None:
        """SIGTERM/SIGINT Handler — setzt Shutdown-Event."""
        logger.info("shutdown_signal_empfangen")
        shutdown_event.set()

    # Signal-Handler nur wenn Hauptthread (nicht in Tests)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows: signal.signal als Fallback
            signal.signal(sig, _signal_handler)

    # Warten auf Shutdown-Signal
    await shutdown_event.wait()

    # Graceful Shutdown: 10s Grace Period
    logger.info("graceful_shutdown", grace_period_s=10)
    if health_pb2 is not None and grpc_health is not None:
        health_servicer.set(
            "",
            health_pb2.HealthCheckResponse.NOT_SERVING,
        )
    await server.stop(grace=10)

    # DB-Pool schliessen
    await pool.close()
    logger.info("server_gestoppt")


if __name__ == "__main__":
    asyncio.run(serve())
