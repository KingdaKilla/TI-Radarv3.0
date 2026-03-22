# =============================================================================
# Dockerfile — Orchestrator Service (TI-Radar v2)
# =============================================================================
# Multi-Stage Build:
#   1. Builder: Dependencies installieren (Caching-Layer)
#   2. Runtime: Minimales Image mit nur den noetigsten Paketen
#
# Ausfuehren:
#   docker build -t orchestrator-svc .
#   docker run -p 8000:8000 orchestrator-svc
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — Dependencies installieren
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# System-Dependencies fuer grpcio (Kompilierung)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Nur pyproject.toml kopieren fuer besseres Docker-Layer-Caching
# (Build-Context ist Projekt-Root, daher voller Pfad)
COPY services/orchestrator-svc/pyproject.toml .

# Dependencies in ein virtuelles Environment installieren
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# ---------------------------------------------------------------------------
# Stage 2: Runtime — Minimales Production-Image
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Sicherheit: Nicht als root ausfuehren
RUN groupadd -r appuser && useradd -r -g appuser -s /sbin/nologin appuser

# Laufzeit-Dependencies fuer asyncpg (libpq)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        && rm -rf /var/lib/apt/lists/*

# Virtuelle Umgebung aus Builder-Stage kopieren
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Anwendungscode kopieren (Build-Context = Projekt-Root)
COPY services/orchestrator-svc/src/ src/

# Shared Domain-Paket (Modelle, Metriken)
COPY packages/shared/ shared/
RUN pip install --no-cache-dir -e shared/

# Berechtigungen setzen
RUN chown -R appuser:appuser /app

USER appuser

# Konfigurierbare Umgebungsvariablen (Defaults fuer Container)
ENV HOST=0.0.0.0 \
    PORT=8000 \
    LOG_LEVEL=INFO \
    DEBUG=false

# Health Check: flacher Health-Endpoint ohne gRPC-Pruefung
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Port exponieren
EXPOSE 8000

# Uvicorn mit Factory-Pattern starten
CMD ["uvicorn", "src.main:create_app", \
     "--factory", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info", \
     "--access-log"]
