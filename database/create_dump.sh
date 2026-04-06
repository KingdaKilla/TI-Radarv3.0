#!/usr/bin/env bash
# =============================================================================
# TI-Radar: Sauberer PostgreSQL Full-Dump (Schema + Daten)
# Ziel: D:\ti_radar_full_dump_2026-04-05.backup
# =============================================================================
set -euo pipefail

CONTAINER="ti-radar-db"
DB_NAME="ti_radar"
DB_USER="tip_admin"
DATE=$(date +%Y-%m-%d)
DUMP_FILE="/tmp/ti_radar_full_dump_${DATE}.backup"
LOCAL_DUMP="/d/ti_radar_full_dump_${DATE}.backup"

echo "=== TI-Radar Full Dump ==="
echo "Container: $CONTAINER"
echo "Datenbank: $DB_NAME"
echo "Ziel:      $LOCAL_DUMP"
echo ""

# 1. Pruefen ob Container laeuft
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "FEHLER: Container '$CONTAINER' laeuft nicht."
    echo "Starte mit: cd deploy && docker compose up -d db"
    exit 1
fi

# 2. Aktuelle Tabellengroessen anzeigen
echo "--- Aktuelle Tabellengroessen (Top 20) ---"
docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT schemaname || '.' || relname AS tabelle,
           pg_size_pretty(pg_total_relation_size(schemaname || '.' || relname)) AS groesse,
           n_live_tup AS zeilen
    FROM pg_stat_user_tables
    WHERE n_live_tup > 0
    ORDER BY pg_total_relation_size(schemaname || '.' || relname) DESC
    LIMIT 20;
"

# 3. Materialized Views aktualisieren
echo ""
echo "--- Materialized Views aktualisieren ---"
docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT cross_schema.refresh_all_views();
" 2>/dev/null || echo "(refresh_all_views nicht verfuegbar, uebersprungen)"

# 4. VACUUM ANALYZE
echo ""
echo "--- VACUUM ANALYZE (optimiert Dump) ---"
docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "VACUUM ANALYZE;"

# 5. pg_dump
echo ""
echo "--- pg_dump starten (Schema + Daten, komprimiert) ---"
echo "    Dies kann bei 150+ Mio Patenten laenger dauern..."
docker exec "$CONTAINER" pg_dump \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=custom \
    --compress=6 \
    --verbose \
    --no-owner \
    --no-privileges \
    --file="$DUMP_FILE" \
    2>&1 | tail -5

# 6. Dump aus Container kopieren
echo ""
echo "--- Kopiere Dump aus Container nach D:\\ ---"
docker cp "${CONTAINER}:${DUMP_FILE}" "$LOCAL_DUMP"

# 7. Aufraeumen im Container
docker exec "$CONTAINER" rm -f "$DUMP_FILE"

# 8. Ergebnis
DUMP_SIZE=$(ls -lh "$LOCAL_DUMP" | awk '{print $5}')
echo ""
echo "========================================="
echo " Dump erfolgreich erstellt"
echo "========================================="
echo " Datei:   $LOCAL_DUMP"
echo " Groesse: $DUMP_SIZE"
echo " Datum:   $DATE"
echo ""
echo " Restore-Befehl:"
echo "   pg_restore -U tip_admin -d ti_radar \\"
echo "     --clean --if-exists --create \\"
echo "     --jobs=4 --verbose \\"
echo "     $LOCAL_DUMP"
echo "========================================="
