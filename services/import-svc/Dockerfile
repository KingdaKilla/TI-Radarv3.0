# =============================================================================
# Dockerfile — TI-Radar v2 Import Service
# =============================================================================
# Multi-Stage Build: uv fuer schnelle Dependency-Installation,
# python:3.12-slim als Runtime-Image.
#
# Verwendung:
#   docker build -t import-svc .
#   docker run -p 8030:8030 --env-file .env import-svc
# =============================================================================

# --- Stage 1: Builder (uv + Dependencies) ---
FROM python:3.12-slim AS builder

# uv installieren (schnellster Python Package Manager)
RUN pip install --no-cache-dir uv

WORKDIR /app

# Shared-Paket kopieren und installieren
COPY packages/shared/ /app/shared/

# Dependencies zuerst kopieren (Docker Layer Caching)
COPY services/import-svc/pyproject.toml ./

# Virtual Environment erstellen und Dependencies installieren
RUN uv venv /app/.venv \
    && uv pip install --python /app/.venv/bin/python -r pyproject.toml \
    && uv pip install --python /app/.venv/bin/python /app/shared/

# Quellcode kopieren
COPY services/import-svc/src/ ./src/

# --- Stage 2: Runtime (schlankes Image) ---
FROM python:3.12-slim AS runtime

# lxml benoetigt libxml2 und libxslt zur Laufzeit
RUN apt-get update \
    && apt-get install -y --no-install-recommends libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

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

# Bulk-Datenverzeichnis anlegen
RUN mkdir -p /data/bulk/EPO /data/bulk/CORDIS && chown -R svc:svc /data

# FastAPI HTTP Port
EXPOSE 8030

# Health Check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8030/healthz')" \
    || exit 1

# User wechseln
USER svc

# Server starten (Factory-Pattern)
CMD ["uvicorn", "src.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8030"]
