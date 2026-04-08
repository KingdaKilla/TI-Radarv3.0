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

# ----------------------------------------------------------------------------
# Git-Bash auf Windows: POSIX->Windows Pfad-Konvertierung deaktivieren.
# Ohne das wandelt Git Bash z.B. /tmp/dump_split/x in einen Windows-Pfad
# /C:/Users/.../tmp/dump_split/x um, BEVOR docker.exe das Argument bekommt.
# Resultat: pg_dump im Container schreibt eine "Geister-Datei" mit ":" und
# "/" im Namen, und docker cp findet sie nicht. Wir wollen, dass POSIX-Pfade
# 1:1 an docker.exe und damit an den Container weitergereicht werden.
# Auf Linux/macOS hat das keine Wirkung.
# ----------------------------------------------------------------------------
export MSYS_NO_PATHCONV=1

CONTAINER="ti-radar-db"
DB_USER="tip_admin"
DB_NAME="ti_radar"
DATE=$(date +%Y-%m-%d)

# Zielverzeichnis (lokal, ausserhalb des Containers)
BASE_DIR="${1:-/d}/ti_radar_dump_${DATE}"
PATENT_DIR="${BASE_DIR}/patent_schema"

# Windows-Style-Pfade fuer 'docker cp' (docker.exe versteht /d/ nicht).
# cygpath -m liefert "D:/..." statt "D:\...".
# Wenn cygpath fehlt (Linux/macOS), bleibt der Pfad unveraendert.
if command -v cygpath >/dev/null 2>&1; then
    WIN_BASE_DIR=$(cygpath -m "$BASE_DIR")
    WIN_PATENT_DIR=$(cygpath -m "$PATENT_DIR")
else
    WIN_BASE_DIR="$BASE_DIR"
    WIN_PATENT_DIR="$PATENT_DIR"
fi

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
echo "[1/5] Verzeichnisse vorbereiten..."
docker exec "$CONTAINER" mkdir -p "$C_PATENT"
mkdir -p "$PATENT_DIR"

# -------------------------------------------------
# Schema-Only Dump (DDL)
# -------------------------------------------------
echo ""
echo "[2/5] Schema-Only Dump (DDL)..."
docker exec "$CONTAINER" pg_dump \
    -U "$DB_USER" -d "$DB_NAME" \
    --schema-only \
    --no-owner --no-privileges \
    -f "${C_BASE}/00_schema_only.sql"
# Sofort nach D: kopieren und im Container loeschen
docker cp "${CONTAINER}:${C_BASE}/00_schema_only.sql" "${WIN_BASE_DIR}/00_schema_only.sql"
docker exec "$CONTAINER" rm -f "${C_BASE}/00_schema_only.sql"
echo "   -> 00_schema_only.sql"

# -------------------------------------------------
# Patent-Schema: Dekaden-Split
# -------------------------------------------------
echo ""
echo "[3/5] Patent-Schema: Dekaden-Split..."

# Hilfsfunktion: Dumpt eine oder mehrere Partitionen in eine Datei
# und kopiert die Datei sofort aus dem Container nach D:, damit der
# Container-Tempspace (in der Docker-VHDX auf C:) nie ueber eine Datei
# hinaus waechst.
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
    # Sofort nach D: kopieren und im Container loeschen
    docker cp "${CONTAINER}:${C_PATENT}/${outfile}" "${WIN_PATENT_DIR}/${outfile}"
    docker exec "$CONTAINER" rm -f "${C_PATENT}/${outfile}"
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
echo "[4/5] Schema-Dumps (cordis, research, entity, export, cross)..."

for schema in cordis_schema research_schema entity_schema export_schema cross_schema; do
    echo "   -> ${schema}..."
    docker exec "$CONTAINER" pg_dump \
        -U "$DB_USER" -d "$DB_NAME" \
        --data-only --format=custom --compress=6 \
        --no-owner --no-privileges \
        -n "$schema" \
        -f "${C_BASE}/${schema}.backup"
    # Sofort nach D: kopieren und im Container loeschen
    docker cp "${CONTAINER}:${C_BASE}/${schema}.backup" "${WIN_BASE_DIR}/${schema}.backup"
    docker exec "$CONTAINER" rm -f "${C_BASE}/${schema}.backup"
done

# -------------------------------------------------
# Container-Tempspace aufraeumen
# -------------------------------------------------
# Hinweis: Dateien wurden bereits direkt nach jedem pg_dump nach D: kopiert
# und einzeln im Container geloescht (siehe dump_partitions() und Schema-Loop).
# Hier nur noch das leere Temp-Verzeichnis entfernen.
docker exec "$CONTAINER" rm -rf "$C_BASE"

# -------------------------------------------------
# Verifizierung
# -------------------------------------------------
echo ""
echo "[5/5] Verifizierung..."
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
