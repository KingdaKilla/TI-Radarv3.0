# =============================================================================
# TI-Radar — Embedding-Service Dockerfile (CPU-basiert)
# =============================================================================
# Fuer GPU-Beschleunigung: EMBEDDING_DEVICE=cuda setzen und
# Base-Image auf nvidia/cuda:12.4.1-runtime-ubuntu22.04 wechseln.
# =============================================================================

# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

# Shared domain
COPY packages/shared/ /app/shared/
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python -e /app/shared/

# Service dependencies
COPY services/embedding-svc/pyproject.toml /app/service/pyproject.toml
RUN uv pip install --python /app/.venv/bin/python -r /app/service/pyproject.toml

# Service source
COPY services/embedding-svc/src/ /app/src/

# --- Stage 2: Runtime ---
FROM python:3.12-slim AS runtime

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -r svc && useradd -r -g svc -d /app -s /sbin/nologin svc

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/shared /app/shared
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.cache/huggingface

# HF/Transformers-Cache-Dir vorbereiten (svc:svc-Ownership, damit
# HuggingFace-Downloads beim ersten Start funktionieren - auch wenn
# ein leeres Named-Volume hierhin gemountet wird).
RUN mkdir -p /app/.cache/huggingface && chown -R svc:svc /app/.cache

EXPOSE 50080 9100

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=30s \
    CMD python -c "import grpc; ch = grpc.insecure_channel('localhost:50080'); grpc.channel_ready_future(ch).result(timeout=3)" \
    || exit 1

USER svc

CMD ["python", "-m", "src.server"]
