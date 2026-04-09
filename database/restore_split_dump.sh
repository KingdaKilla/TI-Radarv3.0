#!/usr/bin/env bash
# ============================================================================
# restore_split_dump.sh
# Restore eines Split-Dumps (erstellt von create_split_dump.sh)
# ============================================================================
#
# Aufruf:
#   ./database/restore_split_dump.sh /pfad/zum/dump-verzeichnis
#
# Environment-Variablen (optional):
#
#   COMPOSE_FILE=deploy/docker-compose.server.yml
#     Compose-File fuer den "docker compose up -d db" Aufruf in Phase [1/9].
#     Default: deploy/docker-compose.yml (lokal).
#     Auf dem Server: COMPOSE_FILE=deploy/docker-compose.server.yml setzen.
#
#   DELETE_DUMPS_AFTER_RESTORE=1
#     Loescht jede .backup-Datei auf dem HOST sofort nach ihrem erfolgreichen
#     pg_restore, um Plattenplatz zu sparen. WICHTIG: pg_restore Exit-Code wird
#     streng geprueft — bei rc > 1 (fatal error) wird NICHT geloescht und das
#     Skript bricht ab. Warnings (rc==1, z.B. "already exists") gelten als OK.
#     00_schema_only.sql und dump.sha256 bleiben IMMER erhalten.
#     DIESE OPTION IST DESTRUKTIV — danach ist kein Restart ohne erneuten
#     Transfer moeglich.
#
# Erwartet:
#   /pfad/zum/dump-verzeichnis/
#   ├── 00_schema_only.sql
#   ├── patent_schema/
#   │   ├── patents_pre1980.backup ... patents_2020s.backup
#   │   ├── patent_cpc_pre1980.backup ... patent_cpc_2020s.backup
#   │   ├── patent_applicants_pre1980.backup ... patent_applicants_2020s.backup
#   │   ├── applicants.backup, cpc_descriptions.backup, ...
#   ├── cordis_schema.backup
#   ├── research_schema.backup
#   ├── entity_schema.backup
#   ├── export_schema.backup
#   └── cross_schema.backup
#
# ============================================================================

set -euo pipefail

DUMP_DIR="${1:?Bitte Dump-Verzeichnis angeben: ./restore_split_dump.sh /pfad/zum/dump}"
CONTAINER="ti-radar-db"
DB_USER="tip_admin"
DB_NAME="ti_radar"
COMPOSE_FILE="${COMPOSE_FILE:-deploy/docker-compose.yml}"
DELETE_DUMPS_AFTER_RESTORE="${DELETE_DUMPS_AFTER_RESTORE:-0}"

# Farben fuer Terminal-Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "============================================"
echo "TI-Radar Split-Dump Restore"
echo "Dump-Dir: ${DUMP_DIR}"
echo "Compose:  ${COMPOSE_FILE}"
if [ "$DELETE_DUMPS_AFTER_RESTORE" = "1" ]; then
    echo -e "${YELLOW}WARNUNG: DELETE_DUMPS_AFTER_RESTORE=1 aktiv${NC}"
    echo -e "${YELLOW}  -> Jede .backup-Datei wird nach erfolgreichem Restore GELOESCHT${NC}"
    echo -e "${YELLOW}  -> Nach Abbruch / Fehler ist kein Restart ohne erneuten Transfer moeglich${NC}"
fi
echo "============================================"

# -------------------------------------------------
# Validierung: Dump-Verzeichnis pruefen
# -------------------------------------------------
if [ ! -f "${DUMP_DIR}/00_schema_only.sql" ]; then
    echo -e "${RED}FEHLER: ${DUMP_DIR}/00_schema_only.sql nicht gefunden.${NC}"
    echo "Bitte Pfad zu einem Split-Dump-Verzeichnis angeben."
    exit 1
fi

if [ ! -d "${DUMP_DIR}/patent_schema" ]; then
    echo -e "${RED}FEHLER: ${DUMP_DIR}/patent_schema/ nicht gefunden.${NC}"
    exit 1
fi

# Hilfsfunktion: Backup-Datei in Container kopieren, restaurieren,
# strenge Exit-Code-Pruefung und optionales Loeschen nach Erfolg.
#
# pg_restore Exit-Codes:
#   0  -> vollstaendiger Erfolg
#   1  -> Warnings (z.B. Item bereits vorhanden, skip) - akzeptabel
#   >1 -> fatal error - hier wird das Skript abgebrochen
restore_backup() {
    local label="$1"
    local backup_file="$2"

    if [ ! -f "$backup_file" ]; then
        echo -e "   ${YELLOW}SKIP: $(basename "$backup_file") nicht vorhanden${NC}"
        return 0
    fi

    local file_size
    file_size=$(du -h "$backup_file" 2>/dev/null | cut -f1)
    echo -n "   -> ${label} (${file_size})... "

    docker cp "$backup_file" "${CONTAINER}:/tmp/restore_part.backup"

    # pg_restore Output in Variable fangen, Exit-Code explizit capturen
    # (set -e darf hier nicht zuschlagen)
    local pg_output=""
    local rc=0
    pg_output=$(docker exec "$CONTAINER" pg_restore \
        -U "$DB_USER" -d "$DB_NAME" \
        --data-only --disable-triggers \
        /tmp/restore_part.backup 2>&1) || rc=$?

    # Container-Kopie immer aufraeumen (Platz im Container-Temp)
    docker exec "$CONTAINER" rm -f /tmp/restore_part.backup || true

    if [ "$rc" -eq 0 ] || [ "$rc" -eq 1 ]; then
        # Erfolg (rc=0) oder akzeptable Warnings (rc=1)
        if [ "$rc" -eq 1 ]; then
            echo -e "${GREEN}OK${NC} ${YELLOW}(mit Warnings)${NC}"
        else
            echo -e "${GREEN}OK${NC}"
        fi

        # Optional: Dump-Datei auf HOST loeschen, um Platz zu sparen
        if [ "$DELETE_DUMPS_AFTER_RESTORE" = "1" ]; then
            if rm -f "$backup_file"; then
                echo -e "      ${YELLOW}-> Host-Dump geloescht (${file_size} frei)${NC}"
            else
                echo -e "      ${RED}-> Loeschen von $backup_file fehlgeschlagen${NC}"
            fi
        fi
        return 0
    else
        # Fataler Fehler: NICHT loeschen, Skript abbrechen
        echo -e "${RED}FAIL (pg_restore rc=$rc)${NC}"
        echo "   --- pg_restore output (letzte 20 Zeilen) ---"
        echo "$pg_output" | tail -20 | sed 's/^/     /'
        echo "   ---"
        echo -e "   ${RED}Abbruch. Host-Dump $backup_file bleibt fuer Retry erhalten.${NC}"
        return "$rc"
    fi
}

# -------------------------------------------------
# [1/9] DB-Container starten
# -------------------------------------------------
echo ""
echo "[1/9] DB-Container starten..."
docker compose -f "$COMPOSE_FILE" up -d db
sleep 5

# Warten bis ready
for i in $(seq 1 30); do
    if docker exec "$CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
        echo "   -> PostgreSQL bereit."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo -e "${RED}FEHLER: PostgreSQL nicht bereit nach 30 Versuchen.${NC}"
        exit 1
    fi
    sleep 2
done

# -------------------------------------------------
# [2/8] Performance-Tuning fuer schnellen Import
# -------------------------------------------------
echo ""
echo "[2/9] PostgreSQL Performance-Tuning fuer Import..."
docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
    ALTER SYSTEM SET max_wal_size = '10GB';
    ALTER SYSTEM SET wal_level = 'minimal';
    ALTER SYSTEM SET fsync = off;
    ALTER SYSTEM SET full_page_writes = off;
    ALTER SYSTEM SET synchronous_commit = off;
    ALTER SYSTEM SET autovacuum = off;
    ALTER SYSTEM SET archive_mode = off;
    ALTER SYSTEM SET max_wal_senders = 0;
"

echo "   -> Container neustarten..."
docker compose -f "$COMPOSE_FILE" restart db
sleep 5

# -------------------------------------------------
# [3/8] Tabellen leeren + Sequenzen zuruecksetzen
# -------------------------------------------------
echo ""
echo "[3/9] Tabellen leeren, Sequenzen zuruecksetzen..."

# restore_dump.sql ist im Image unter /opt/restore/ eingebacken
if docker exec "$CONTAINER" test -f /opt/restore/restore_dump.sql; then
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -f /opt/restore/restore_dump.sql
else
    # Fallback: aus Host-Dateisystem
    docker cp "database/sql/restore_dump.sql" "${CONTAINER}:/tmp/restore_dump.sql"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -f /tmp/restore_dump.sql
    docker exec "$CONTAINER" rm -f /tmp/restore_dump.sql
fi

# -------------------------------------------------
# [4/8] Nicht-Patent-Schemas restaurieren
# -------------------------------------------------
echo ""
echo "[4/9] Nicht-Patent-Schemas restaurieren..."

restore_backup "cordis_schema"   "${DUMP_DIR}/cordis_schema.backup"
restore_backup "research_schema" "${DUMP_DIR}/research_schema.backup"
restore_backup "entity_schema"   "${DUMP_DIR}/entity_schema.backup"
restore_backup "export_schema"   "${DUMP_DIR}/export_schema.backup"
restore_backup "cross_schema"    "${DUMP_DIR}/cross_schema.backup"

# -------------------------------------------------
# [5/8] Patent-Schema: Nicht-partitionierte Tabellen
# -------------------------------------------------
echo ""
echo "[5/9] Patent-Schema: Referenztabellen..."

restore_backup "applicants"          "${DUMP_DIR}/patent_schema/applicants.backup"
restore_backup "cpc_descriptions"    "${DUMP_DIR}/patent_schema/cpc_descriptions.backup"
restore_backup "patent_citations"    "${DUMP_DIR}/patent_schema/patent_citations.backup"
restore_backup "import_metadata"     "${DUMP_DIR}/patent_schema/import_metadata.backup"
restore_backup "enrichment_progress" "${DUMP_DIR}/patent_schema/enrichment_progress.backup"

# -------------------------------------------------
# [6/8] Patent-Schema: Dekaden-Partitionen
# -------------------------------------------------
echo ""
echo "[6/9] Patent-Dekaden restaurieren (das dauert am laengsten)..."

DECADES=("pre1980" "1980s" "1990s" "2000s" "2010s" "2020s")

for decade in "${DECADES[@]}"; do
    echo ""
    echo "   === Dekade: ${decade} ==="
    restore_backup "patents_${decade}"            "${DUMP_DIR}/patent_schema/patents_${decade}.backup"
    restore_backup "patent_cpc_${decade}"          "${DUMP_DIR}/patent_schema/patent_cpc_${decade}.backup"
    restore_backup "patent_applicants_${decade}"   "${DUMP_DIR}/patent_schema/patent_applicants_${decade}.backup"
done

# -------------------------------------------------
# [7/9] Junction-Tabellen aus denormalisierten Patent-Daten ableiten
# -------------------------------------------------
# Die Dumps enthalten patent_cpc_*.backup und patent_applicants_*.backup,
# aber diese sind in der aktuellen Prod-DB leer (nur Header, 1-4 KB).
# Die Junctions werden daher aus patents.cpc_codes und patents.applicant_names
# (denormalisierte Felder, die der EPO-Importer direkt befuellt) abgeleitet.
# Idempotent durch ON CONFLICT DO NOTHING — bei zukuenftigen Dumps mit bereits
# gefuellten Junction-Partitionen ist der Effekt ein No-op.
echo ""
echo "[7/9] Junction-Tabellen ableiten (patent_cpc, patent_applicants, applicants)..."

# Drei Fundstellen in dieser Reihenfolge:
#   1. Host-Dateisystem (Repo-Checkout) - fuer lokale Entwicklung
#   2. Im DB-Image eingebacken unter /opt/restore/ - fuer Server-Deployment
#      wo das Repo evtl. nicht vollstaendig vorhanden ist
#   3. Skip mit Warnung
if [ -f "database/sql/seed_junctions_production.sql" ]; then
    docker cp "database/sql/seed_junctions_production.sql" \
        "${CONTAINER}:/tmp/seed_junctions_production.sql"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" \
        -f /tmp/seed_junctions_production.sql
    docker exec "$CONTAINER" rm -f /tmp/seed_junctions_production.sql
    echo -e "   ${GREEN}Junction-Ableitung abgeschlossen (vom Host).${NC}"
elif docker exec "$CONTAINER" test -f /opt/restore/seed_junctions_production.sql 2>/dev/null; then
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" \
        -f /opt/restore/seed_junctions_production.sql
    echo -e "   ${GREEN}Junction-Ableitung abgeschlossen (aus Image).${NC}"
else
    echo -e "   ${YELLOW}SKIP: seed_junctions_production.sql nicht gefunden.${NC}"
    echo -e "   ${YELLOW}UC1/UC3/UC5/UC8-Services haben dann keine Junction-Daten.${NC}"
fi

# -------------------------------------------------
# [8/9] Materialized Views aktualisieren
# -------------------------------------------------
echo ""
echo "[8/9] Materialized Views aktualisieren..."

# Bevorzugt via refresh_cross_schema_mvs.sql (setzt statement_timeout=0 und
# nutzt CONCURRENTLY). Fallback: inline non-concurrent refresh.
if [ -f "database/sql/refresh_cross_schema_mvs.sql" ]; then
    docker cp "database/sql/refresh_cross_schema_mvs.sql" \
        "${CONTAINER}:/tmp/refresh_cross_schema_mvs.sql"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" \
        -f /tmp/refresh_cross_schema_mvs.sql
    docker exec "$CONTAINER" rm -f /tmp/refresh_cross_schema_mvs.sql
elif docker exec "$CONTAINER" test -f /opt/restore/refresh_cross_schema_mvs.sql 2>/dev/null; then
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" \
        -f /opt/restore/refresh_cross_schema_mvs.sql
else
    echo -e "   ${YELLOW}Fallback: inline MV-Refresh ohne statement_timeout=0${NC}"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
        SET statement_timeout = 0;
        REFRESH MATERIALIZED VIEW cross_schema.mv_patent_counts_by_cpc_year;
        REFRESH MATERIALIZED VIEW cross_schema.mv_cpc_cooccurrence;
        REFRESH MATERIALIZED VIEW cross_schema.mv_yearly_tech_counts;
        REFRESH MATERIALIZED VIEW cross_schema.mv_top_applicants;
        REFRESH MATERIALIZED VIEW cross_schema.mv_patent_country_distribution;
        REFRESH MATERIALIZED VIEW cross_schema.mv_project_counts_by_year;
        REFRESH MATERIALIZED VIEW cross_schema.mv_cordis_country_pairs;
        REFRESH MATERIALIZED VIEW cross_schema.mv_top_cordis_orgs;
        REFRESH MATERIALIZED VIEW cross_schema.mv_funding_by_instrument;
    "
fi

# -------------------------------------------------
# [9/9] Performance-Settings zuruecksetzen
# -------------------------------------------------
echo ""
echo "[9/9] PostgreSQL Performance-Settings zuruecksetzen..."
docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
    ALTER SYSTEM RESET max_wal_size;
    ALTER SYSTEM RESET wal_level;
    ALTER SYSTEM RESET fsync;
    ALTER SYSTEM RESET full_page_writes;
    ALTER SYSTEM RESET synchronous_commit;
    ALTER SYSTEM RESET autovacuum;
    ALTER SYSTEM RESET archive_mode;
    ALTER SYSTEM RESET max_wal_senders;
"

docker compose -f "$COMPOSE_FILE" restart db
sleep 5

# Alembic-Version setzen
echo ""
echo "Alembic-Version setzen..."
docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
    DELETE FROM public.alembic_version;
    INSERT INTO public.alembic_version (version_num) VALUES ('001_consolidated');
"

# -------------------------------------------------
# Verifizierung
# -------------------------------------------------
echo ""
echo "============================================"
echo "Verifizierung: Zeilenanzahl pro Tabelle"
echo "============================================"
docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT 'patent_schema.patents' AS tabelle, COUNT(*) AS zeilen FROM patent_schema.patents
    UNION ALL SELECT 'patent_schema.applicants', COUNT(*) FROM patent_schema.applicants
    UNION ALL SELECT 'patent_schema.patent_applicants', COUNT(*) FROM patent_schema.patent_applicants
    UNION ALL SELECT 'patent_schema.patent_cpc', COUNT(*) FROM patent_schema.patent_cpc
    UNION ALL SELECT 'patent_schema.patent_citations', COUNT(*) FROM patent_schema.patent_citations
    UNION ALL SELECT 'cordis_schema.projects', COUNT(*) FROM cordis_schema.projects
    UNION ALL SELECT 'cordis_schema.organizations', COUNT(*) FROM cordis_schema.organizations
    UNION ALL SELECT 'cordis_schema.publications', COUNT(*) FROM cordis_schema.publications
    UNION ALL SELECT 'cordis_schema.euroscivoc', COUNT(*) FROM cordis_schema.euroscivoc
    UNION ALL SELECT 'entity_schema.unified_actors', COUNT(*) FROM entity_schema.unified_actors
    UNION ALL SELECT 'cross_schema.import_log', COUNT(*) FROM cross_schema.import_log
    UNION ALL SELECT 'research_schema.papers', COUNT(*) FROM research_schema.papers
    ORDER BY tabelle;
"

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Split-Dump Restore abgeschlossen!${NC}"
echo -e "${GREEN}============================================${NC}"
