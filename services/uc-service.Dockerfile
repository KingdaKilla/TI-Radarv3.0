# =============================================================================
# TI-Radar v2 — UC-Service Dockerfile (Multi-Stage Template)
# =============================================================================
# Parametrisierter Build fuer alle UC-Services (UC1-UC9, UCB, UCD, UCE).
# SERVICE_DIR gibt an, welcher Service gebaut wird.
#
# Verwendung:
#   docker build --build-arg SERVICE_DIR=services/maturity-svc \
#                -f services/uc-service.Dockerfile -t maturity-svc .
# =============================================================================

# --- Stage 1: Builder (uv + Dependencies) ---
FROM python:3.12-slim AS builder

# Systemabhaengigkeiten fuer asyncpg + scipy Kompilierung + uv
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev gcc g++ && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir uv

WORKDIR /app

# Build-Argument: welcher Service-Ordner
ARG SERVICE_DIR=services/landscape-svc

# Shared Domain-Logik installieren (als Package)
COPY packages/shared/ /app/shared/
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python -e /app/shared/

# Service-Dependencies installieren
COPY ${SERVICE_DIR}/pyproject.toml /app/service/pyproject.toml
RUN uv pip install --python /app/.venv/bin/python -r /app/service/pyproject.toml 2>/dev/null || \
    uv pip install --python /app/.venv/bin/python \
        grpcio>=1.60 grpcio-tools>=1.60 grpcio-health-checking>=1.60 \
        grpcio-reflection>=1.60 "protobuf>=6.31" asyncpg>=0.29 structlog>=24.0 \
        pydantic-settings>=2.0 httpx>=0.27 prometheus-client>=0.20

# Service-Quellcode kopieren
COPY ${SERVICE_DIR}/src/ /app/src/

# --- Stage 2: Runtime (schlankes Image) ---
FROM python:3.12-slim AS runtime

# Sicherheit: Non-Root User
RUN groupadd -r svc && useradd -r -g svc -d /app -s /sbin/nologin svc

# Laufzeit-Dependencies (libpq fuer asyncpg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Virtual Environment + Code aus Builder kopieren
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/shared /app/shared
COPY --from=builder /app/src /app/src

# PATH setzen (venv aktivieren)
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# gRPC Port + Prometheus Metrics Port
EXPOSE 50051
EXPOSE 9090

# Health Check (gRPC Health Checking Protocol)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=15s \
    CMD python -c "import grpc; ch = grpc.insecure_channel('localhost:50051'); grpc.channel_ready_future(ch).result(timeout=3)" \
    || exit 1

# User wechseln
USER svc

# gRPC Server starten
CMD ["python", "-m", "src.server"]
