-- ============================================================================
-- restore_dump.sql
-- Vollstaendiges Restore-Skript fuer ti_radar_dump.backup
-- auf einem Server, wo die DB bereits existiert
-- ============================================================================
--
-- Ausfuehrung:
--   docker exec ti-radar-db psql -U tip_admin -d ti_radar -f /tmp/restore_dump.sql
--
-- Danach:
--   docker exec ti-radar-db pg_restore -U tip_admin -d ti_radar \
--       --data-only --disable-triggers --jobs=4 /tmp/dump.backup
--
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. ALLE Tabellen leeren (Reihenfolge beachtet Foreign Keys)
-- ============================================================================

-- --- Patent Schema ---
TRUNCATE patent_schema.patent_citations;
TRUNCATE patent_schema.epo_ops_cache;
TRUNCATE patent_schema.patent_cpc CASCADE;
TRUNCATE patent_schema.patent_applicants CASCADE;
TRUNCATE patent_schema.applicants CASCADE;
TRUNCATE patent_schema.patents CASCADE;
TRUNCATE patent_schema.cpc_descriptions;
TRUNCATE patent_schema.import_metadata;
TRUNCATE patent_schema.enrichment_progress;

-- --- CORDIS Schema ---
TRUNCATE cordis_schema.project_euroscivoc;
TRUNCATE cordis_schema.publications CASCADE;
TRUNCATE cordis_schema.organizations CASCADE;
TRUNCATE cordis_schema.projects CASCADE;
TRUNCATE cordis_schema.euroscivoc CASCADE;
TRUNCATE cordis_schema.import_metadata;
TRUNCATE cordis_schema.cordis_api_cache;

-- --- Research Schema ---
TRUNCATE research_schema.paper_authors;
TRUNCATE research_schema.papers CASCADE;
TRUNCATE research_schema.authors CASCADE;
TRUNCATE research_schema.query_cache;
TRUNCATE research_schema.openaire_cache;
TRUNCATE research_schema.openaire_publications;

-- --- Entity Schema ---
TRUNCATE entity_schema.actor_source_mappings;
TRUNCATE entity_schema.unified_actors CASCADE;
TRUNCATE entity_schema.resolution_runs;
TRUNCATE entity_schema.gleif_cache;

-- --- Export Schema ---
TRUNCATE export_schema.export_log, export_schema.report_templates, export_schema.analysis_cache;

-- --- Cross Schema (Tabellen, NICHT Materialized Views) ---
TRUNCATE cross_schema.document_chunks;
TRUNCATE cross_schema.etl_checkpoints;
TRUNCATE cross_schema.etl_run_log;
TRUNCATE cross_schema.import_log;

-- --- Public ---
TRUNCATE public.alembic_version;


-- ============================================================================
-- 2. Vektor-Dimensionen an Dump anpassen (nur noetig wenn Dump andere Dims hat)
--    Schema definiert vector(384). Nur document_chunks verwendet vector(1024)
--    im Dump, alle anderen Embedding-Spalten sind bereits 384.
-- ============================================================================

ALTER TABLE cross_schema.document_chunks
    ALTER COLUMN embedding TYPE vector(1024);


-- ============================================================================
-- 3. Identity/Serial Sequenzen zuruecksetzen
--    Damit neue IDs nicht mit vorhandenen Dump-IDs kollidieren
-- ============================================================================

-- patent_schema
ALTER TABLE patent_schema.patents ALTER COLUMN id RESTART;
ALTER TABLE patent_schema.applicants ALTER COLUMN id RESTART;
ALTER TABLE patent_schema.import_metadata ALTER COLUMN id RESTART;

-- cordis_schema
ALTER TABLE cordis_schema.organizations ALTER COLUMN id RESTART;
ALTER TABLE cordis_schema.publications ALTER COLUMN id RESTART;
ALTER TABLE cordis_schema.euroscivoc ALTER COLUMN id RESTART;
ALTER TABLE cordis_schema.import_metadata ALTER COLUMN id RESTART;

-- research_schema
ALTER TABLE research_schema.papers ALTER COLUMN id RESTART;
ALTER TABLE research_schema.authors ALTER COLUMN id RESTART;
ALTER TABLE research_schema.query_cache ALTER COLUMN id RESTART;
ALTER TABLE research_schema.openaire_cache ALTER COLUMN id RESTART;
ALTER TABLE research_schema.openaire_publications ALTER COLUMN id RESTART;

-- entity_schema
ALTER TABLE entity_schema.actor_source_mappings ALTER COLUMN id RESTART;
ALTER TABLE entity_schema.resolution_runs ALTER COLUMN id RESTART;

-- cross_schema
ALTER TABLE cross_schema.document_chunks ALTER COLUMN id RESTART;
ALTER TABLE cross_schema.etl_run_log ALTER COLUMN id RESTART;

-- export_schema
ALTER TABLE export_schema.analysis_cache ALTER COLUMN id RESTART;
ALTER TABLE export_schema.report_templates ALTER COLUMN id RESTART;
ALTER TABLE export_schema.export_log ALTER COLUMN id RESTART;

COMMIT;

-- ============================================================================
-- Fertig! Jetzt pg_restore ausfuehren:
--
--   docker exec ti-radar-db pg_restore -U tip_admin -d ti_radar \
--       --data-only --disable-triggers --jobs=4 /tmp/dump.backup
--
-- Danach Materialized Views aktualisieren:
--
--   docker exec ti-radar-db psql -U tip_admin -d ti_radar \
--       -c "REFRESH MATERIALIZED VIEW cross_schema.mv_patent_counts_by_cpc_year;
--           REFRESH MATERIALIZED VIEW cross_schema.mv_cpc_cooccurrence;
--           REFRESH MATERIALIZED VIEW cross_schema.mv_yearly_tech_counts;
--           REFRESH MATERIALIZED VIEW cross_schema.mv_top_applicants;
--           REFRESH MATERIALIZED VIEW cross_schema.mv_patent_country_distribution;
--           REFRESH MATERIALIZED VIEW cross_schema.mv_project_counts_by_year;
--           REFRESH MATERIALIZED VIEW cross_schema.mv_cordis_country_pairs;
--           REFRESH MATERIALIZED VIEW cross_schema.mv_top_cordis_orgs;
--           REFRESH MATERIALIZED VIEW cross_schema.mv_funding_by_instrument;"
--
-- Und PostgreSQL Performance-Settings zuruecksetzen:
--
--   docker exec ti-radar-db psql -U tip_admin -d ti_radar -c "
--       ALTER SYSTEM RESET max_wal_size;
--       ALTER SYSTEM RESET wal_level;
--       ALTER SYSTEM RESET fsync;
--       ALTER SYSTEM RESET full_page_writes;
--       ALTER SYSTEM RESET synchronous_commit;
--       ALTER SYSTEM RESET autovacuum;
--       ALTER SYSTEM RESET archive_mode;
--       ALTER SYSTEM RESET max_wal_senders;"
--
--   docker compose restart db
--
-- ============================================================================
