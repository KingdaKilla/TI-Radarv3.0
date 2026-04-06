#!/usr/bin/env bash
# ============================================================================
# create_split_dump.sh
# Granularer Split-Dump: Per Schema + Patent-Dekaden
# ============================================================================
#
# Aufruf:
#   ./database/create_split_dump.sh              # Dump nach D:\
#   ./database/create_split_dump.sh /pfad/ziel   # Dump in anderes Verzeichnis
#
# Ergebnis:
#   D:\ti_radar_dump_YYYY-MM-DD/
#   ├── 00_schema_only.sql
#   ├── patent_schema/  (Dekaden-Split fuer patents, patent_cpc, patent_applicants)
#   ├── cordis_schema.backup
#   ├── research_schema.backup
#   ├── entity_schema.backup
#   ├── export_schema.backup
#   └── cross_schema.backup
#
# ============================================================================

set -euo pipefail

CONTAINER="ti-radar-db"
DB_USER="tip_admin"
DB_NAME="ti_radar"
DATE=$(date +%Y-%m-%d)

# Zielverzeichnis (lokal, ausserhalb des Containers)
BASE_DIR="${1:-/d}/ti_radar_dump_${DATE}"
PATENT_DIR="${BASE_DIR}/patent_schema"

# Temporaeres Verzeichnis im Container
C_BASE="/tmp/dump_split"
C_PATENT="${C_BASE}/patent_schema"

echo "============================================"
echo "TI-Radar Granularer Split-Dump"
echo "Ziel: ${BASE_DIR}"
echo "Datum: ${DATE}"
echo "============================================"

# -------------------------------------------------
# Pruefen ob Container laeuft
# -------------------------------------------------
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "FEHLER: Container '$CONTAINER' laeuft nicht."
    exit 1
fi

# -------------------------------------------------
# Verzeichnisse vorbereiten
# -------------------------------------------------
echo ""
echo "[1/6] Verzeichnisse vorbereiten..."
docker exec "$CONTAINER" mkdir -p "$C_PATENT"
mkdir -p "$PATENT_DIR"

# -------------------------------------------------
# Schema-Only Dump (DDL)
# -------------------------------------------------
echo ""
echo "[2/6] Schema-Only Dump (DDL)..."
docker exec "$CONTAINER" pg_dump \
    -U "$DB_USER" -d "$DB_NAME" \
    --schema-only \
    --no-owner --no-privileges \
    -f "${C_BASE}/00_schema_only.sql"
echo "   -> 00_schema_only.sql"

# -------------------------------------------------
# Patent-Schema: Dekaden-Split
# -------------------------------------------------
echo ""
echo "[3/6] Patent-Schema: Dekaden-Split..."

# Hilfsfunktion: Dumpt eine oder mehrere Partitionen in eine Datei
dump_partitions() {
    local label="$1"
    local outfile="$2"
    shift 2
    # Restliche Argumente sind -t Flags
    echo "   -> ${label}..."
    docker exec "$CONTAINER" pg_dump \
        -U "$DB_USER" -d "$DB_NAME" \
        --data-only --format=custom --compress=6 \
        --no-owner --no-privileges \
        "$@" \
        -f "${C_PATENT}/${outfile}"
}

# --- patents (Haupttabelle) ---
dump_partitions "patents_pre1980" "patents_pre1980.backup" \
    -t patent_schema.patents_pre1980

dump_partitions "patents_1980s" "patents_1980s.backup" \
    -t patent_schema.patents_1980s

dump_partitions "patents_1990s" "patents_1990s.backup" \
    -t patent_schema.patents_1990s

dump_partitions "patents_2000s" "patents_2000s.backup" \
    -t 'patent_schema.patents_200[0-9]'

dump_partitions "patents_2010s" "patents_2010s.backup" \
    -t 'patent_schema.patents_201[0-9]'

dump_partitions "patents_2020s" "patents_2020s.backup" \
    -t 'patent_schema.patents_202[0-9]' \
    -t patent_schema.patents_2030 \
    -t patent_schema.patents_future

# --- patent_cpc (co-partitioniert) ---
dump_partitions "patent_cpc_pre1980" "patent_cpc_pre1980.backup" \
    -t patent_schema.patent_cpc_pre1980

dump_partitions "patent_cpc_1980s" "patent_cpc_1980s.backup" \
    -t patent_schema.patent_cpc_1980s

dump_partitions "patent_cpc_1990s" "patent_cpc_1990s.backup" \
    -t patent_schema.patent_cpc_1990s

dump_partitions "patent_cpc_2000s" "patent_cpc_2000s.backup" \
    -t 'patent_schema.patent_cpc_200[0-9]'

dump_partitions "patent_cpc_2010s" "patent_cpc_2010s.backup" \
    -t 'patent_schema.patent_cpc_201[0-9]'

dump_partitions "patent_cpc_2020s" "patent_cpc_2020s.backup" \
    -t 'patent_schema.patent_cpc_202[0-9]' \
    -t patent_schema.patent_cpc_2030 \
    -t patent_schema.patent_cpc_future

# --- patent_applicants (co-partitioniert) ---
dump_partitions "patent_applicants_pre1980" "patent_applicants_pre1980.backup" \
    -t patent_schema.patent_applicants_pre1980

dump_partitions "patent_applicants_1980s" "patent_applicants_1980s.backup" \
    -t patent_schema.patent_applicants_1980s

dump_partitions "patent_applicants_1990s" "patent_applicants_1990s.backup" \
    -t patent_schema.patent_applicants_1990s

dump_partitions "patent_applicants_2000s" "patent_applicants_2000s.backup" \
    -t 'patent_schema.patent_applicants_200[0-9]'

dump_partitions "patent_applicants_2010s" "patent_applicants_2010s.backup" \
    -t 'patent_schema.patent_applicants_201[0-9]'

dump_partitions "patent_applicants_2020s" "patent_applicants_2020s.backup" \
    -t 'patent_schema.patent_applicants_202[0-9]' \
    -t patent_schema.patent_applicants_2030 \
    -t patent_schema.patent_applicants_future

# --- Restliche Patent-Tabellen (nicht partitioniert) ---
dump_partitions "applicants" "applicants.backup" \
    -t patent_schema.applicants

dump_partitions "cpc_descriptions" "cpc_descriptions.backup" \
    -t patent_schema.cpc_descriptions

dump_partitions "patent_citations" "patent_citations.backup" \
    -t patent_schema.patent_citations

dump_partitions "import_metadata" "import_metadata.backup" \
    -t patent_schema.import_metadata

dump_partitions "enrichment_progress" "enrichment_progress.backup" \
    -t patent_schema.enrichment_progress

# -------------------------------------------------
# Nicht-Patent-Schemas (je ein Dump)
# -------------------------------------------------
echo ""
echo "[4/6] Schema-Dumps (cordis, research, entity, export, cross)..."

for schema in cordis_schema research_schema entity_schema export_schema cross_schema; do
    echo "   -> ${schema}..."
    docker exec "$CONTAINER" pg_dump \
        -U "$DB_USER" -d "$DB_NAME" \
        --data-only --format=custom --compress=6 \
        --no-owner --no-privileges \
        -n "$schema" \
        -f "${C_BASE}/${schema}.backup"
done

# -------------------------------------------------
# Aus Container kopieren
# -------------------------------------------------
echo ""
echo "[5/6] Dateien aus Container kopieren..."
docker cp "${CONTAINER}:${C_BASE}/00_schema_only.sql" "${BASE_DIR}/00_schema_only.sql"

# Patent-Schema Dateien
for f in $(docker exec "$CONTAINER" ls "$C_PATENT"); do
    docker cp "${CONTAINER}:${C_PATENT}/${f}" "${PATENT_DIR}/${f}"
done

# Schema-Dumps
for schema in cordis_schema research_schema entity_schema export_schema cross_schema; do
    docker cp "${CONTAINER}:${C_BASE}/${schema}.backup" "${BASE_DIR}/${schema}.backup"
done

# Aufraeumen im Container
docker exec "$CONTAINER" rm -rf "$C_BASE"

# -------------------------------------------------
# Verifizierung
# -------------------------------------------------
echo ""
echo "[6/6] Verifizierung..."
echo ""
echo "============================================"
echo "Dump-Dateien:"
echo "============================================"

total_size=0
while IFS= read -r file; do
    size=$(stat --format="%s" "$file" 2>/dev/null || stat -f "%z" "$file" 2>/dev/null || echo "0")
    human=$(numfmt --to=iec "$size" 2>/dev/null || echo "${size} B")
    name="${file#${BASE_DIR}/}"
    printf "  %-45s %10s\n" "$name" "$human"
    total_size=$((total_size + size))
done < <(find "$BASE_DIR" -type f | sort)

echo "--------------------------------------------"
total_human=$(numfmt --to=iec "$total_size" 2>/dev/null || echo "${total_size} B")
printf "  %-45s %10s\n" "GESAMT" "$total_human"

echo ""
echo "============================================"
echo "Split-Dump abgeschlossen!"
echo "============================================"
echo ""
echo "Restore-Beispiele:"
echo ""
echo "  # Komplettes Schema restaurieren:"
echo "  psql -U tip_admin -d ti_radar -f ${BASE_DIR}/00_schema_only.sql"
echo ""
echo "  # Nur CORDIS-Daten:"
echo "  pg_restore -U tip_admin -d ti_radar --data-only --disable-triggers \\"
echo "      ${BASE_DIR}/cordis_schema.backup"
echo ""
echo "  # Nur Patente 2020er-Dekade:"
echo "  pg_restore -U tip_admin -d ti_radar --data-only --disable-triggers \\"
echo "      ${BASE_DIR}/patent_schema/patents_2020s.backup"
echo "============================================"
