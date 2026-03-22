# =============================================================================
# Dockerfile — UC1 Landscape Service
# =============================================================================
# Multi-Stage Build: uv fuer schnelle Dependency-Installation,
# python:3.12-slim als Runtime-Image.
#
# Verwendung:
#   docker build -t landscape-svc .
#   docker run -p 50051:50051 --env-file .env landscape-svc
# =============================================================================

# --- Stage 1: Builder (uv + Dependencies) ---
FROM python:3.12-slim AS builder

# uv aus offiziellem Image kopieren (schnellster Python Package Manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies zuerst kopieren (Docker Layer Caching)
COPY pyproject.toml ./

# Virtual Environment erstellen und Dependencies installieren
RUN uv venv /app/.venv \
    && uv pip install --python /app/.venv/bin/python -r pyproject.toml

# Quellcode kopieren
COPY src/ ./src/

# --- Stage 2: Runtime (schlankes Image) ---
FROM python:3.12-slim AS runtime

# Sicherheit: Non-Root User
RUN groupadd -r svc && useradd -r -g svc -d /app -s /sbin/nologin svc

WORKDIR /app

# Virtual Environment aus Builder kopieren
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# PATH setzen (venv aktivieren)
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# gRPC Port
EXPOSE 50051

# Prometheus Metrics Port
EXPOSE 9090

# Health Check (gRPC Health Checking Protocol)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import grpc; ch = grpc.insecure_channel('localhost:50051'); grpc.channel_ready_future(ch).result(timeout=3)" \
    || exit 1

# User wechseln
USER svc

# Server starten
CMD ["python", "-m", "src.server"]
