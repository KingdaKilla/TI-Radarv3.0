# =============================================================================
# Dockerfile — Export Service (TI-Radar v2)
# =============================================================================
# Multi-Stage Build mit uv fuer schnelle Dependency-Installation:
#   1. Builder: Dependencies installieren (Caching-Layer)
#   2. Runtime: Minimales Image mit nur den noetigsten Paketen
#
# Ausfuehren:
#   docker build -t export-svc .
#   docker run -p 8020:8020 export-svc
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — Dependencies mit uv installieren
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# uv fuer schnelle Dependency-Installation
RUN pip install --no-cache-dir uv

WORKDIR /app

# Nur pyproject.toml kopieren fuer besseres Docker-Layer-Caching
# (Build-Context ist Projekt-Root, daher voller Pfad)
COPY services/export-svc/pyproject.toml .

# Virtuelles Environment erstellen und Dependencies installieren
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache .

# Shared-Paket kopieren und installieren
COPY packages/shared/ /app/shared/
RUN . /opt/venv/bin/activate && \
    uv pip install --no-cache /app/shared/

# ---------------------------------------------------------------------------
# Stage 2: Runtime — Minimales Production-Image
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Sicherheit: Nicht als root ausfuehren
RUN groupadd -r appuser && useradd -r -g appuser -s /sbin/nologin appuser

# Laufzeit-Dependencies: libpq (asyncpg) + WeasyPrint (PDF-Export)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        libglib2.0-0 libpango-1.0-0 libpangoft2-1.0-0 \
        libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev \
        libcairo2 fonts-dejavu-core \
        && rm -rf /var/lib/apt/lists/*

# Virtuelle Umgebung aus Builder-Stage kopieren
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Shared-Paket kopieren (fuer Domain-Modelle)
COPY --from=builder /app/shared/ shared/

# Anwendungscode kopieren (Build-Context = Projekt-Root)
COPY services/export-svc/src/ src/

# Berechtigungen setzen
RUN chown -R appuser:appuser /app

USER appuser

# Konfigurierbare Umgebungsvariablen (Defaults fuer Container)
# HINWEIS: appuser hat kein Home-Verzeichnis (useradd -r ohne -m).
# Matplotlib + Fontconfig brauchen writable Cache-Pfade —
# deshalb werden sie nach /tmp umgeleitet (von appuser beschreibbar).
ENV HOST=0.0.0.0 \
    PORT=8020 \
    LOG_LEVEL=INFO \
    MPLCONFIGDIR=/tmp/matplotlib \
    XDG_CACHE_HOME=/tmp/.cache \
    FONTCONFIG_PATH=/etc/fonts

# Health Check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8020/health')" || exit 1

# Port exponieren
EXPOSE 8020

# Uvicorn mit Factory-Pattern starten
CMD ["uvicorn", "src.main:create_app", \
     "--factory", \
     "--host", "0.0.0.0", \
     "--port", "8020", \
     "--workers", "1", \
     "--log-level", "info", \
     "--access-log"]
