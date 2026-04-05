#!/usr/bin/env bash
# ============================================================================
# restore_on_server.sh
# Vollstaendiges Restore der ti_radar_dump.backup auf dem Zielserver
# ============================================================================
#
# Aufruf von AUSSERHALB des Containers:
#   ./restore_on_server.sh /pfad/zur/dump.backup
#
# Oder von INNERHALB des Containers (SQL ist bereits eingebacken):
#   docker exec ti-radar-db psql -U tip_admin -d ti_radar \
#       -f /opt/restore/restore_dump.sql
#
# ============================================================================

set -euo pipefail

DUMP_PATH="${1:?Bitte Dump-Pfad angeben: ./restore_on_server.sh /pfad/zur/dump.backup}"
CONTAINER="ti-radar-db"
DB_USER="tip_admin"
DB_NAME="ti_radar"

echo "============================================"
echo "TI-Radar Dump Restore"
echo "Dump: $DUMP_PATH"
echo "============================================"

# -------------------------------------------------
# Schritt 1: DB-Container starten (falls nicht laeuft)
# -------------------------------------------------
echo ""
echo "[1/7] DB-Container starten..."
docker compose up -d db
sleep 5

# -------------------------------------------------
# Schritt 2: Performance-Tuning fuer schnellen Import
# -------------------------------------------------
echo ""
echo "[2/7] PostgreSQL Performance-Tuning fuer Import..."
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
docker compose restart db
sleep 5

# -------------------------------------------------
# Schritt 3: Dump-Datei in Container kopieren
# -------------------------------------------------
echo ""
echo "[3/7] Dump in Container kopieren (kann dauern bei grossen Dateien)..."
docker cp "$DUMP_PATH" "$CONTAINER":/tmp/dump.backup

# -------------------------------------------------
# Schritt 4: Tabellen leeren + Vektordimensionen anpassen
#            (SQL ist im Image unter /opt/restore/ eingebacken)
# -------------------------------------------------
echo ""
echo "[4/7] Tabellen leeren, Sequenzen zuruecksetzen, Vektor-Dimensionen anpassen..."
docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -f /opt/restore/restore_dump.sql

# -------------------------------------------------
# Schritt 5: pg_restore ausfuehren
# -------------------------------------------------
echo ""
echo "[5/7] pg_restore starten (--data-only --disable-triggers --jobs=4)..."
echo "   -> Das dauert bei 74 GB mehrere Stunden!"
docker exec "$CONTAINER" pg_restore \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --data-only \
    --disable-triggers \
    --jobs=4 \
    /tmp/dump.backup || echo "   -> pg_restore beendet (einige Warnungen sind normal)"

# -------------------------------------------------
# Schritt 6: Materialized Views aktualisieren
# -------------------------------------------------
echo ""
echo "[6/7] Materialized Views aktualisieren..."
docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
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

# -------------------------------------------------
# Schritt 7: Performance-Settings zuruecksetzen
# -------------------------------------------------
echo ""
echo "[7/7] PostgreSQL Performance-Settings zuruecksetzen..."
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

docker compose restart db
sleep 5

# Aufraeumen
echo ""
echo "Dump-Datei im Container aufraeumen..."
docker exec "$CONTAINER" rm -f /tmp/dump.backup

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
    UNION ALL SELECT 'entity_schema.actor_source_mappings', COUNT(*) FROM entity_schema.actor_source_mappings
    UNION ALL SELECT 'cross_schema.document_chunks', COUNT(*) FROM cross_schema.document_chunks
    UNION ALL SELECT 'research_schema.papers', COUNT(*) FROM research_schema.papers
    ORDER BY tabelle;
"

echo ""
echo "============================================"
echo "Restore abgeschlossen!"
echo "============================================"
