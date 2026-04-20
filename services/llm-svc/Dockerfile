# =============================================================================
# Dockerfile — LLM Analysis Service
# =============================================================================
# Multi-Stage Build: uv fuer schnelle Dependency-Installation,
# python:3.12-slim als Runtime-Image.
#
# Kein DB-Zugriff — dieser Service ruft ausschliesslich externe LLM-APIs auf.
#
# Verwendung:
#   docker build -t llm-svc .
#   docker run -p 50070:50070 --env-file .env llm-svc
# =============================================================================

# --- Stage 1: Builder (uv + Dependencies) ---
FROM python:3.12-slim AS builder

# uv installieren (schnellster Python Package Manager)
RUN pip install --no-cache-dir uv

WORKDIR /app

# Dependencies zuerst kopieren (Docker Layer Caching)
COPY services/llm-svc/pyproject.toml ./

# Virtual Environment erstellen und Dependencies installieren
RUN uv venv /app/.venv \
    && uv pip install --python /app/.venv/bin/python -r pyproject.toml

# Quellcode kopieren
COPY services/llm-svc/src/ ./src/

# Shared gRPC Stubs
COPY packages/shared/ /app/shared/
RUN uv pip install --python /app/.venv/bin/python -e /app/shared/

# --- Stage 2: Runtime (schlankes Image) ---
FROM python:3.12-slim AS runtime

# Sicherheit: Non-Root User
RUN groupadd -r svc && useradd -r -g svc -d /app -s /sbin/nologin svc

WORKDIR /app

# Virtual Environment aus Builder kopieren
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/shared /app/shared

# PATH setzen (venv aktivieren)
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# gRPC Port
EXPOSE 50070

# Prometheus Metrics Port
EXPOSE 9099

# Health Check (gRPC Health Checking Protocol)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=15s \
    CMD python -c "import grpc; ch = grpc.insecure_channel('localhost:50070'); grpc.channel_ready_future(ch).result(timeout=3)" \
    || exit 1

# User wechseln
USER svc

# Server starten
CMD ["python", "-m", "src.server"]
