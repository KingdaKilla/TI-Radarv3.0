#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== TI-Radar Start ==="

# .env prüfen
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "FEHLER: .env nicht gefunden. Bitte zuerst setup.sh ausführen."
    exit 1
fi

source "$PROJECT_ROOT/.env"

# DB-Pfad prüfen
if [ -z "${TI_RADAR_DB_PATH:-}" ]; then
    echo "FEHLER: TI_RADAR_DB_PATH nicht gesetzt in .env"
    exit 1
fi

if [ ! -d "$TI_RADAR_DB_PATH" ]; then
    echo "FEHLER: Datenbank-Verzeichnis nicht gefunden: $TI_RADAR_DB_PATH"
    echo "Ist das externe Laufwerk angeschlossen?"
    exit 1
fi

# Services starten
cd "$PROJECT_ROOT"
docker compose --env-file .env -f deploy/docker-compose.yml up -d

echo ""
echo "=== Services gestartet ==="
echo "Frontend:    http://localhost:3000"
echo "API:         http://localhost:8000"
echo "API Docs:    http://localhost:8000/docs"
echo ""
echo "Logs:   docker compose --env-file .env -f deploy/docker-compose.yml logs -f"
echo "Stop:   docker compose --env-file .env -f deploy/docker-compose.yml down"
