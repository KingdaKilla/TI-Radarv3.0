"""gRPC Server fuer den LLM Analysis Service.

Startet den async gRPC-Server mit:
- LlmAnalysisServicer (textuelle KI-Analyse)
- Health-Check-Service (gRPC Health Checking Protocol)
- Reflection (fuer grpcurl / grpc-cli Debugging)
- Graceful Shutdown bei SIGTERM/SIGINT

Verwendung:
    python -m src.server
"""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import Any

import structlog
from prometheus_client import Counter, Histogram, start_http_server

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
    from shared.generated.python import llm_pb2
    from shared.generated.python import llm_pb2_grpc
except ImportError:
    llm_pb2 = None  # type: ignore[assignment]
    llm_pb2_grpc = None  # type: ignore[assignment]

from src.config import Settings
from src.service import LlmAnalysisServicer

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
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)


async def serve() -> None:
    """Hauptfunktion: gRPC-Server starten und auf Shutdown warten."""
    settings = Settings()

    # --- Prometheus Metrics HTTP-Server ---
    metrics_port = settings.metrics_port
    start_http_server(metrics_port)
    logger.info("prometheus_metrics_gestartet", port=metrics_port)

    # --- Pruefe ob gRPC verfuegbar ---
    if grpc_aio is None:
        logger.error("grpc_nicht_installiert", hinweis="pip install grpcio grpcio-tools")
        sys.exit(1)

    # --- gRPC Server erstellen ---
    server = grpc_aio.server(
        options=[
            ("grpc.max_send_message_length", 10 * 1024 * 1024),   # 10 MB
            ("grpc.max_receive_message_length", 10 * 1024 * 1024),
            ("grpc.keepalive_time_ms", 300_000),
            ("grpc.keepalive_timeout_ms", 10_000),
            ("grpc.http2.min_recv_ping_interval_without_data_ms", 60_000),
        ],
    )

    # --- LLM Analysis Servicer registrieren ---
    servicer = LlmAnalysisServicer(settings=settings)
    if llm_pb2_grpc is not None:
        llm_pb2_grpc.add_LlmAnalysisServiceServicer_to_server(servicer, server)
        logger.info("servicer_registriert", service="LlmAnalysisService")
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
                "tip.llm.LlmAnalysisService",
                health_pb2.HealthCheckResponse.SERVING,
            )
            health_servicer.set(
                "",  # Gesamtstatus
                health_pb2.HealthCheckResponse.SERVING,
            )
        logger.info("health_check_registriert")

    # --- Reflection (fuer grpcurl Debugging) ---
    if reflection is not None and llm_pb2 is not None:
        service_names = (
            llm_pb2.DESCRIPTOR.services_by_name["LlmAnalysisService"].full_name,
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
    logger.info("server_gestoppt")


if __name__ == "__main__":
    asyncio.run(serve())
