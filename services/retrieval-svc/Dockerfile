# =============================================================================
# Dockerfile — Retrieval Service
# =============================================================================
# Semantische Suche ueber pgvector fuer RAG-Pipeline.
# Hybrid Search (Dense + Sparse) + Cross-Encoder Reranking.
# =============================================================================

# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY services/retrieval-svc/pyproject.toml ./

RUN uv venv /app/.venv \
    && uv pip install --python /app/.venv/bin/python -r pyproject.toml

COPY services/retrieval-svc/src/ ./src/

# Shared gRPC Stubs
COPY packages/shared/ /app/shared/
RUN uv pip install --python /app/.venv/bin/python -e /app/shared/

# --- Stage 2: Runtime ---
FROM python:3.12-slim AS runtime

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd -r svc && useradd -r -g svc -d /app -s /sbin/nologin svc

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/shared /app/shared

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.cache/huggingface

# HF/Transformers-Cache-Dir vorbereiten (svc:svc-Ownership, damit
# CrossEncoder-Reranker-Downloads beim ersten Start funktionieren -
# auch wenn ein leeres Named-Volume hierhin gemountet wird).
RUN mkdir -p /app/.cache/huggingface && chown -R svc:svc /app/.cache

EXPOSE 50081
EXPOSE 9098

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=15s \
    CMD python -c "import grpc; ch = grpc.insecure_channel('localhost:50081'); grpc.channel_ready_future(ch).result(timeout=3)" \
    || exit 1

USER svc

CMD ["python", "-m", "src.server"]
