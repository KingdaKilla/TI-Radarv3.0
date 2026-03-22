"""Middleware fuer Request-ID-Propagation, Rate Limiting, Logging und Metriken.

Jeder eingehende HTTP-Request erhaelt eine eindeutige Request-ID,
die in den strukturierten Logs und in der gRPC-Metadata an die
UC-Services weitergegeben wird (Distributed Tracing).

Rate Limiting: Einfacher In-Memory-Limiter (Sliding Window pro IP).
Fuer MVP ausreichend — bei Skalierung auf Redis/Valkey umsteigen.
"""

from __future__ import annotations

import asyncio
import re
import time
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable

import structlog
from fastapi import HTTPException, Request, Response
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Request-ID Header-Name (X-Request-ID ist De-facto-Standard)
# ---------------------------------------------------------------------------
REQUEST_ID_HEADER = "X-Request-ID"

# Erlaubtes Format fuer X-Request-ID: alphanumerisch + Bindestrich, 1-64 Zeichen
_REQUEST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-]{1,64}$")

# ---------------------------------------------------------------------------
# Prometheus-Metriken
# ---------------------------------------------------------------------------

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Gesamtzahl eingehender HTTP-Requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Dauer eingehender HTTP-Requests in Sekunden",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

GRPC_CALLS_TOTAL = Counter(
    "grpc_calls_total",
    "Gesamtzahl ausgehender gRPC-Aufrufe an UC-Services",
    ["uc_service", "status"],
)

GRPC_CALL_DURATION_SECONDS = Histogram(
    "grpc_call_duration_seconds",
    "Dauer ausgehender gRPC-Aufrufe in Sekunden",
    ["uc_service"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 20.0, 30.0],
)

RADAR_REQUESTS_TOTAL = Counter(
    "radar_requests_total",
    "Gesamtzahl der Radar-Analyse-Requests",
    ["status"],
)

UC_DEGRADATION_TOTAL = Counter(
    "uc_degradation_total",
    "Anzahl der Graceful-Degradation-Events (UC-Fehler/Timeouts)",
    ["uc_service", "error_type"],
)


# ---------------------------------------------------------------------------
# Request-ID-Middleware
# ---------------------------------------------------------------------------

class RequestIdMiddleware(BaseHTTPMiddleware):
    """Fuegt jedem Request eine eindeutige Request-ID hinzu.

    - Liest vorhandene X-Request-ID aus dem Header (z.B. von API-Gateway)
    - Generiert eine neue UUID v4 falls kein Header vorhanden
    - Setzt die Request-ID in den Response-Header
    - Bindet die Request-ID an den structlog-Context fuer alle Logeintraege
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Request-ID aus Header lesen, Wert validieren oder neu generieren
        request_id = request.headers.get(REQUEST_ID_HEADER, "")
        if not request_id or not _REQUEST_ID_PATTERN.match(request_id):
            request_id = str(uuid.uuid4())

        # In Request-State speichern (fuer Router-Zugriff)
        request.state.request_id = request_id

        # Strukturiertes Logging: Request-ID an Context binden
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Timing + Request-Logging
        t0 = time.monotonic()
        method = request.method
        path = request.url.path

        logger.info(
            "http_request_start",
            method=method,
            path=path,
            client=request.client.host if request.client else "unknown",
        )

        # Request durchreichen
        response = await call_next(request)

        # Dauer berechnen
        duration = time.monotonic() - t0
        status_code = response.status_code

        # Response-Header setzen
        response.headers[REQUEST_ID_HEADER] = request_id

        # Prometheus-Metriken aktualisieren
        # Endpoint normalisieren (Query-Parameter entfernen)
        endpoint = path
        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code),
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)

        # Abschluss-Log
        logger.info(
            "http_request_end",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=int(duration * 1000),
        )

        return response


# ---------------------------------------------------------------------------
# Hilfsfunktionen fuer gRPC-Metriken (von Routern aufgerufen)
# ---------------------------------------------------------------------------


def record_grpc_call(
    uc_service: str,
    status: str,
    duration_seconds: float,
) -> None:
    """Zeichnet Metriken fuer einen gRPC-Aufruf auf.

    Args:
        uc_service: Name des UC-Service (z.B. "landscape").
        status: Ergebnis ("success", "timeout", "error", "unavailable").
        duration_seconds: Dauer des Aufrufs in Sekunden.
    """
    GRPC_CALLS_TOTAL.labels(uc_service=uc_service, status=status).inc()
    GRPC_CALL_DURATION_SECONDS.labels(uc_service=uc_service).observe(duration_seconds)

    if status != "success":
        UC_DEGRADATION_TOTAL.labels(
            uc_service=uc_service,
            error_type=status,
        ).inc()


def record_radar_request(status: str) -> None:
    """Zeichnet eine Radar-Anfrage als Metrik auf."""
    RADAR_REQUESTS_TOTAL.labels(status=status).inc()


# ---------------------------------------------------------------------------
# Rate-Limit-Middleware (Sliding Window, In-Memory)
# ---------------------------------------------------------------------------

# Prometheus-Metrik fuer Rate-Limit-Verletzungen
RATE_LIMIT_EXCEEDED_TOTAL = Counter(
    "rate_limit_exceeded_total",
    "Anzahl der abgelehnten Requests wegen Rate-Limit-Ueberschreitung",
    ["client_ip"],
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Einfacher In-Memory Rate-Limiter (Sliding Window pro Client-IP).

    Standard: 100 Requests pro Minute. Konfigurierbar via Konstruktor.
    Fuer MVP ausreichend — bei horizontaler Skalierung (mehrere Replicas)
    auf Redis/Valkey-basierten Limiter umsteigen.

    Health-Check-Endpunkte (/healthz, /readyz, /metrics) sind vom
    Rate Limiting ausgenommen, damit Kubernetes-Probes nicht blockiert werden.
    """

    # Endpunkte, die vom Rate Limiting ausgenommen sind
    EXEMPT_PATHS: frozenset[str] = frozenset({
        "/healthz",
        "/readyz",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    })

    def __init__(
        self,
        app: object,
        max_requests: int = 100,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._MAX_TRACKED_IPS = 10_000

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Health-Checks und Docs vom Rate Limiting ausnehmen
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        async with self._lock:
            # Evict oldest entry if IP tracking table is full
            if len(self._requests) >= self._MAX_TRACKED_IPS:
                oldest_ip = min(
                    self._requests,
                    key=lambda ip: self._requests[ip][-1] if self._requests[ip] else 0,
                )
                del self._requests[oldest_ip]

            # Alte Requests ausserhalb des Zeitfensters aufräumen
            window_start = now - self.window_seconds
            self._requests[client_ip] = [
                t for t in self._requests[client_ip]
                if t > window_start
            ]

            if len(self._requests[client_ip]) >= self.max_requests:
                RATE_LIMIT_EXCEEDED_TOTAL.labels(client_ip=client_ip).inc()
                logger.warning(
                    "rate_limit_ueberschritten",
                    client_ip=client_ip,
                    max_requests=self.max_requests,
                    window_seconds=self.window_seconds,
                )
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"Rate Limit erreicht: max. {self.max_requests} "
                        f"Anfragen pro {self.window_seconds} Sekunden"
                    ),
                )

            self._requests[client_ip].append(now)

        return await call_next(request)
