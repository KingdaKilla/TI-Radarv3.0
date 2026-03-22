#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== TI-Radar Setup ==="

# 1. Docker prüfen
if ! command -v docker &>/dev/null; then
    echo "FEHLER: Docker ist nicht installiert."
    echo "Download: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker compose version &>/dev/null; then
    echo "FEHLER: Docker Compose Plugin nicht gefunden."
    exit 1
fi

echo "[OK] Docker gefunden: $(docker --version)"

# 2. .env erstellen falls nicht vorhanden
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo "[INFO] .env aus .env.example erstellt. Bitte Werte eintragen!"
    echo ""
    echo "Mindestens folgende Werte müssen gesetzt werden:"
    echo "  - POSTGRES_PASSWORD"
    echo "  - TI_RADAR_DB_PATH (z.B. D:/ti-radar-db)"
    echo ""
    read -p "Möchten Sie die .env jetzt bearbeiten? [j/N] " answer
    if [[ "$answer" =~ ^[jJyY]$ ]]; then
        ${EDITOR:-nano} "$PROJECT_ROOT/.env"
    fi
fi

# 3. TI_RADAR_DB_PATH prüfen
source "$PROJECT_ROOT/.env"
if [ -z "${TI_RADAR_DB_PATH:-}" ]; then
    echo "FEHLER: TI_RADAR_DB_PATH ist nicht gesetzt in .env"
    exit 1
fi

if [ ! -d "$TI_RADAR_DB_PATH" ]; then
    echo "[INFO] Erstelle Datenbank-Verzeichnis: $TI_RADAR_DB_PATH"
    mkdir -p "$TI_RADAR_DB_PATH"
fi
echo "[OK] Datenbank-Verzeichnis: $TI_RADAR_DB_PATH"

# 4. Proto-Stubs generieren
echo "[...] Generiere Protobuf-Stubs..."
if pip show grpcio-tools &>/dev/null 2>&1; then
    bash "$PROJECT_ROOT/scripts/generate_protos.sh"
    echo "[OK] Proto-Stubs generiert"
else
    echo "[WARN] grpcio-tools nicht installiert — Proto-Stubs werden beim Docker-Build generiert"
fi

# 5. Docker-Images bauen
echo "[...] Baue Docker-Images (kann beim ersten Mal mehrere Minuten dauern)..."
cd "$PROJECT_ROOT"
docker compose --env-file .env -f deploy/docker-compose.yml build

echo ""
echo "=== Setup abgeschlossen ==="
echo "Starten mit: bash scripts/start.sh"
