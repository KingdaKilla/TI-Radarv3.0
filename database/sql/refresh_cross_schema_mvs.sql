-- ============================================================================
-- refresh_cross_schema_mvs.sql
--
-- Aktualisiert alle 9 Materialized Views im cross_schema.
--
-- WICHTIG: DIESE DATEI DARF NICHT IN EINER TRANSAKTION LAUFEN.
--   `REFRESH MATERIALIZED VIEW CONCURRENTLY` verbietet PostgreSQL innerhalb
--   BEGIN..COMMIT ("cannot run inside a transaction block"). psql-autocommit
--   behandelt jedes Statement als eigene implizite Transaktion — das passt.
--
-- CONCURRENTLY:
--   Alle 9 MVs haben einen UNIQUE Index (verifiziert via pg_index.indisunique),
--   also ist CONCURRENTLY unterstuetzt. Der alte MV-Inhalt bleibt waehrend
--   des Refresh lesbar, was wichtig ist wenn UC-Services parallel queryen.
--
-- HINWEIS zu Junction-Fill:
--   Die aktuellen MV-Definitionen lesen direkt aus patents.cpc_codes und
--   patents.applicant_names (denormalisiert). Das bedeutet: ein Junction-
--   Fill aus seed_junctions_production.sql AENDERT diese MVs NICHT, weil
--   sie die Junction-Tabellen gar nicht benutzen. Dieser Refresh ist trotzdem
--   sinnvoll nach einem VOLLEN DATEN-RESTORE (Stale-Detection).
--
-- Aufruf:
--   docker cp database/sql/refresh_cross_schema_mvs.sql \
--     ti-radar-db:/tmp/refresh_cross_schema_mvs.sql
--   docker exec ti-radar-db psql -U tip_admin -d ti_radar \
--     -f /tmp/refresh_cross_schema_mvs.sql
--
-- ============================================================================

\echo ''
\echo '=== TI-Radar: cross_schema Materialized Views refreshen ==='
\echo ''
\timing on

-- Defense in depth
\set ON_ERROR_STOP on

-- statement_timeout deaktivieren: die teuren MVs (mv_patent_counts_by_cpc_year,
-- mv_cpc_cooccurrence, mv_yearly_tech_counts, mv_top_applicants) ueberschreiten
-- das Production-Default (10 min), weil sie aus patents.cpc_codes denormalisiert
-- lesen und auf 156 M Patents aggregieren. REFRESH CONCURRENTLY macht zusaetzlich
-- einen FULL JOIN mit dem alten Stand, was die Zeit verdoppelt.
SET statement_timeout = 0;
SET lock_timeout = 0;

\echo '[1/9] mv_patent_counts_by_cpc_year...'
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_patent_counts_by_cpc_year;

\echo '[2/9] mv_cpc_cooccurrence...'
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_cpc_cooccurrence;

\echo '[3/9] mv_yearly_tech_counts...'
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_yearly_tech_counts;

\echo '[4/9] mv_top_applicants...'
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_top_applicants;

\echo '[5/9] mv_patent_country_distribution...'
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_patent_country_distribution;

\echo '[6/9] mv_project_counts_by_year...'
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_project_counts_by_year;

\echo '[7/9] mv_cordis_country_pairs...'
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_cordis_country_pairs;

\echo '[8/9] mv_top_cordis_orgs...'
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_top_cordis_orgs;

\echo '[9/9] mv_funding_by_instrument...'
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_funding_by_instrument;

-- Session-Settings zuruecksetzen
RESET statement_timeout;
RESET lock_timeout;

\echo ''
\echo '--- Row-Counts nach Refresh ---'
SELECT 'mv_patent_counts_by_cpc_year'   AS mv, COUNT(*) AS zeilen FROM cross_schema.mv_patent_counts_by_cpc_year
UNION ALL SELECT 'mv_cpc_cooccurrence',            COUNT(*) FROM cross_schema.mv_cpc_cooccurrence
UNION ALL SELECT 'mv_yearly_tech_counts',          COUNT(*) FROM cross_schema.mv_yearly_tech_counts
UNION ALL SELECT 'mv_top_applicants',              COUNT(*) FROM cross_schema.mv_top_applicants
UNION ALL SELECT 'mv_patent_country_distribution', COUNT(*) FROM cross_schema.mv_patent_country_distribution
UNION ALL SELECT 'mv_project_counts_by_year',      COUNT(*) FROM cross_schema.mv_project_counts_by_year
UNION ALL SELECT 'mv_cordis_country_pairs',        COUNT(*) FROM cross_schema.mv_cordis_country_pairs
UNION ALL SELECT 'mv_top_cordis_orgs',             COUNT(*) FROM cross_schema.mv_top_cordis_orgs
UNION ALL SELECT 'mv_funding_by_instrument',       COUNT(*) FROM cross_schema.mv_funding_by_instrument;

\echo ''
\echo '=== Materialized View Refresh abgeschlossen ==='
\echo ''
