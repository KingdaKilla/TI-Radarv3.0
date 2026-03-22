"""gRPC Server fuer den UC-C Publication Analytics Service."""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import Any

import asyncpg
import structlog
from prometheus_client import Counter, Gauge, Histogram, start_http_server

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
    from shared.generated.python import uc_c_publications_pb2
    from shared.generated.python import uc_c_publications_pb2_grpc
except ImportError:
    uc_c_publications_pb2 = None  # type: ignore[assignment]
    uc_c_publications_pb2_grpc = None  # type: ignore[assignment]

from src.config import Settings
from src.service import PublicationAnalyticsServicer

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars, structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(), structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0), context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(), cache_logger_on_first_use=True,
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
    """PostgreSQL Connection Pool erstellen."""
    logger.info("db_pool_erstellen", url=settings.database_url.split("@")[-1])
    pool: asyncpg.Pool = await asyncpg.create_pool(
        dsn=settings.database_url, min_size=settings.db_min_connections,
        max_size=settings.db_max_connections, command_timeout=settings.db_query_timeout_s,
    )
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

    if grpc_aio is None:
        logger.error("grpc_nicht_installiert")
        sys.exit(1)

    pool = await create_db_pool(settings)
    server = grpc_aio.server(options=[
        ("grpc.max_send_message_length", 50 * 1024 * 1024),
        ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ("grpc.keepalive_time_ms", 300_000), ("grpc.keepalive_timeout_ms", 10_000),
        ("grpc.http2.min_recv_ping_interval_without_data_ms", 60_000),
    ])

    servicer = PublicationAnalyticsServicer(pool=pool, settings=settings)
    if uc_c_publications_pb2_grpc is not None:
        uc_c_publications_pb2_grpc.add_PublicationAnalyticsServiceServicer_to_server(servicer, server)
        logger.info("servicer_registriert", service="PublicationAnalyticsService")
    else:
        logger.warning("stubs_nicht_verfuegbar")

    if grpc_health is not None and health_pb2_grpc is not None:
        health_servicer = grpc_health.HealthServicer()
        health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
        if health_pb2 is not None:
            health_servicer.set("tip.uc_c_publications.PublicationAnalyticsService", health_pb2.HealthCheckResponse.SERVING)
            health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)

    if reflection is not None and uc_c_publications_pb2 is not None:
        service_names = (
            uc_c_publications_pb2.DESCRIPTOR.services_by_name["PublicationAnalyticsService"].full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(service_names, server)

    listen_addr = f"{settings.service_host}:{settings.service_port}"
    server.add_insecure_port(listen_addr)
    await server.start()
    logger.info("server_gestartet", adresse=listen_addr)

    shutdown_event = asyncio.Event()
    def _signal_handler(*_args: Any) -> None:
        logger.info("shutdown_signal_empfangen")
        shutdown_event.set()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            signal.signal(sig, _signal_handler)

    await shutdown_event.wait()
    logger.info("graceful_shutdown", grace_period_s=10)
    if health_pb2 is not None and grpc_health is not None:
        health_servicer.set("", health_pb2.HealthCheckResponse.NOT_SERVING)
    await server.stop(grace=10)
    await pool.close()
    logger.info("server_gestoppt")


if __name__ == "__main__":
    asyncio.run(serve())
