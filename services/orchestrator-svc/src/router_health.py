"""Health- und Metrics-Endpoints fuer den Orchestrator.

GET /health — Aggregierter Health-Check ueber alle UC-Services.
GET /metrics — Prometheus-Metriken im OpenMetrics-Format.

Der Health-Endpoint unterstuetzt zwei Modi:
- Shallow (Standard): Nur der Orchestrator selbst wird geprueft.
- Deep (?deep=true): Alle 13 UC-Service-Channels werden auf
  Konnektivitaet geprueft (dauert bis zu 3s).
"""

from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, Query, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.grpc_clients import GrpcChannelManager
from src.schemas import HealthResponse, ServiceHealthStatus

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Health"])


# ---------------------------------------------------------------------------
# UC-Name zu Anzeigename-Mapping
# ---------------------------------------------------------------------------
UC_DISPLAY_NAMES: dict[str, str] = {
    "landscape": "landscape-svc (UC1)",
    "maturity": "maturity-svc (UC2)",
    "competitive": "competitive-svc (UC3)",
    "funding": "funding-svc (UC4)",
    "cpc_flow": "cpc-flow-svc (UC5)",
    "geographic": "geographic-svc (UC6)",
    "research_impact": "research-impact-svc (UC7)",
    "temporal": "temporal-svc (UC8)",
    "tech_cluster": "tech-cluster-svc (UC9)",
    "actor_type": "actor-type-svc (UC11)",
    "patent_grant": "patent-grant-svc (UC12)",
    "euroscivoc": "euroscivoc-svc (UC10)",
}


@router.get("/health", response_model=HealthResponse)
async def health_check(
    request: Request,
    deep: bool = Query(
        default=False,
        description="Deep Health Check: Konnektivitaet zu allen UC-Services pruefen",
    ),
) -> HealthResponse:
    """Service Health Check mit optionalem Deep-Check der UC-Services.

    Shallow (Standard): Prueft nur, ob der Orchestrator selbst laeuft.
    Deep (?deep=true): Prueft zusaetzlich die gRPC-Konnektivitaet zu
    allen 12 UC-Services und gibt pro Service Latenz + Status zurueck.
    """
    channel_manager: GrpcChannelManager = request.app.state.grpc_channels
    services: list[ServiceHealthStatus] = []
    overall_healthy = True

    # Datenbank-Konnektivitaet pruefen
    db_healthy = False
    db_pool = getattr(request.app.state, "db_pool", None)
    if db_pool is not None:
        try:
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_healthy = True
        except Exception as exc:
            logger.warning("health_db_fehler", error=str(exc))

    if deep:
        # Alle UC-Service-Channels parallel pruefen
        health_results = await channel_manager.check_all_health()

        for uc_name, (healthy, latency_ms, error) in health_results.items():
            services.append(ServiceHealthStatus(
                service_name=UC_DISPLAY_NAMES.get(uc_name, uc_name),
                use_case=uc_name,
                healthy=healthy,
                latency_ms=latency_ms,
                error=error,
            ))
            if not healthy:
                overall_healthy = False

        logger.info(
            "health_deep_check",
            healthy=overall_healthy,
            services_checked=len(services),
            services_healthy=sum(1 for s in services if s.healthy),
            db_healthy=db_healthy,
        )
    else:
        # Shallow: Orchestrator laeuft -> healthy
        logger.debug("health_shallow_check", healthy=True, db_healthy=db_healthy)

    return HealthResponse(
        healthy=overall_healthy,
        services=services,
        version="2.0.0",
        timestamp=datetime.now().isoformat(),
        database_healthy=db_healthy,
    )


# ---------------------------------------------------------------------------
# Prometheus Metrics Endpoint
# ---------------------------------------------------------------------------


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics() -> Response:
    """Prometheus-Metriken im OpenMetrics/text-Format.

    Exponiert automatisch alle registrierten Prometheus-Counter,
    Histogramme und Gauges aus der middleware.py.
    """
    metrics_output = generate_latest()
    return Response(
        content=metrics_output,
        media_type=CONTENT_TYPE_LATEST,
    )
