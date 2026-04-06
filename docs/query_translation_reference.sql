-- ============================================================================
-- 004_query_translation.sql
-- SQLite to PostgreSQL query translation reference
-- ============================================================================
-- Maps every query pattern from mvp_v1.0 repositories to its PostgreSQL
-- equivalent. These serve as the specification for the new asyncpg-based
-- repository implementations.
--
-- HINWEIS: Diese Datei enthaelt NUR Kommentare als Referenz-Dokumentation.
-- Keine ausfuehrbaren SQL-Statements, da die referenzierten Tabellen erst
-- nach dem Daten-Import existieren / befuellt sind.
-- ============================================================================


-- ============================================================================
-- PATENT REPOSITORY TRANSLATIONS
-- ============================================================================

-- ---------------------------------------------------------------------------
-- search_by_technology (was: FTS5 MATCH on patents_fts)
-- ---------------------------------------------------------------------------
-- SQLite:
--   SELECT p.* FROM patents_fts fts
--   JOIN patents p ON p.id = fts.rowid
--   WHERE patents_fts MATCH '"lithium ion"'
--   AND p.publication_date >= '2020-01-01'
--   LIMIT 10000
--
-- PostgreSQL:
-- SELECT p.publication_number, p.country, p.title,
--        p.publication_date, p.applicant_names, p.applicant_countries,
--        p.cpc_codes, p.family_id
-- FROM patent_schema.patents p
-- WHERE p.search_vector @@ ti_websearch_tsquery('lithium ion')
--   AND p.publication_date >= '2020-01-01'::DATE
-- ORDER BY ts_rank_cd(p.search_vector, ti_websearch_tsquery('lithium ion')) DESC
-- LIMIT 10000;


-- ---------------------------------------------------------------------------
-- count_by_year (was: SUBSTR + GROUP BY)
-- ---------------------------------------------------------------------------
-- SQLite:
--   SELECT SUBSTR(p.publication_date, 1, 4) AS year, COUNT(*) AS count
--   FROM patents_fts fts JOIN patents p ON p.id = fts.rowid
--   WHERE patents_fts MATCH ? AND SUBSTR(publication_date, 1, 4) >= '2015'
--   GROUP BY year ORDER BY year
--
-- PostgreSQL (leverages partition pruning on publication_year):
-- SELECT p.publication_year AS year,
--        COUNT(*) AS count
-- FROM patent_schema.patents p
-- WHERE p.search_vector @@ ti_plainto_tsquery('lithium ion')
--   AND p.publication_year >= 2015
--   AND p.publication_year <= 2025
-- GROUP BY p.publication_year
-- ORDER BY p.publication_year;


-- ---------------------------------------------------------------------------
-- count_by_country (was: p.country GROUP BY)
-- ---------------------------------------------------------------------------
-- PostgreSQL (unchanged logic, proper DATE comparison):
-- SELECT p.country, COUNT(*) AS count
-- FROM patent_schema.patents p
-- WHERE p.search_vector @@ ti_plainto_tsquery('lithium ion')
--   AND p.publication_date >= '2015-01-01'::DATE
-- GROUP BY p.country
-- ORDER BY count DESC
-- LIMIT 20;


-- ---------------------------------------------------------------------------
-- count_by_applicant_country (was: LIKE on CSV text)
-- ---------------------------------------------------------------------------
-- SQLite:
--   SELECT p.applicant_countries FROM patents_fts fts
--   JOIN patents p ... -- then Python splits CSV and counts
--
-- PostgreSQL (no Python post-processing needed, GIN-indexed):
-- SELECT country, COUNT(*) AS count
-- FROM (
--     SELECT unnest(p.applicant_countries) AS country
--     FROM patent_schema.patents p
--     WHERE p.search_vector @@ ti_plainto_tsquery('lithium ion')
--       AND p.publication_year BETWEEN 2015 AND 2025
--       AND p.applicant_countries IS NOT NULL
-- ) sub
-- WHERE length(country) = 2
-- GROUP BY country
-- ORDER BY count DESC
-- LIMIT 30;


-- ---------------------------------------------------------------------------
-- top_applicants (normalized, was: JOIN patent_applicants + applicants)
-- ---------------------------------------------------------------------------
-- PostgreSQL (uses unnest on applicant_names array):
-- SELECT applicant_name, COUNT(*) AS count
-- FROM patent_schema.patents p,
--      LATERAL unnest(p.applicant_names) AS a(applicant_name)
-- WHERE p.search_vector @@ ti_plainto_tsquery('lithium ion')
--   AND p.publication_year BETWEEN 2015 AND 2025
--   AND p.applicant_names IS NOT NULL
-- GROUP BY applicant_name
-- ORDER BY count DESC
-- LIMIT 20;


-- ---------------------------------------------------------------------------
-- co_applicants (was: self-join on patent_applicants)
-- ---------------------------------------------------------------------------
-- SELECT a1.applicant_name AS actor_a,
--        a2.applicant_name AS actor_b,
--        COUNT(*) AS co_count
-- FROM patent_schema.patents p,
--      LATERAL unnest(p.applicant_names) WITH ORDINALITY AS a1(applicant_name, ord1),
--      LATERAL unnest(p.applicant_names) WITH ORDINALITY AS a2(applicant_name, ord2)
-- WHERE p.search_vector @@ ti_plainto_tsquery('lithium ion')
--   AND p.publication_year BETWEEN 2015 AND 2025
--   AND array_length(p.applicant_names, 1) >= 2
--   AND a1.ord1 < a2.ord2
-- GROUP BY a1.applicant_name, a2.applicant_name
-- ORDER BY co_count DESC
-- LIMIT 200;


-- ---------------------------------------------------------------------------
-- suggest_titles (was: FTS5 prefix match '"prefix"*')
-- ---------------------------------------------------------------------------
-- SQLite:
--   WHERE patents_fts MATCH '"quantum"*' LIMIT 500
--
-- PostgreSQL: pg_trgm similarity for typo-tolerant autocomplete
-- SELECT DISTINCT p.title
-- FROM patent_schema.patents p
-- WHERE p.title % 'quantum comp'
--   AND p.title ILIKE 'quantum comp%'
-- ORDER BY similarity(p.title, 'quantum comp') DESC
-- LIMIT 50;
--
-- Alternative: tsvector prefix matching (faster, no typo tolerance)
-- SELECT DISTINCT p.title
-- FROM patent_schema.patents p
-- WHERE p.search_vector @@ to_tsquery('english', 'quantum:*')
-- LIMIT 50;


-- ---------------------------------------------------------------------------
-- compute_cpc_jaccard (was: TEMP TABLE + self-join on patent_cpc)
-- ---------------------------------------------------------------------------
-- PostgreSQL: reads from materialized view (instant), no temp tables needed.
-- Uses CTE chain: matched_patents -> matched_cpc -> top_codes ->
-- co_occurrence -> code_counts -> Jaccard computation


-- ---------------------------------------------------------------------------
-- EU/EEA filter (was: 30-clause OR on LIKE)
-- ---------------------------------------------------------------------------
-- SQLite:
--   AND (p.applicant_countries LIKE '%AT%'
--    OR  p.applicant_countries LIKE '%BE%'
--    OR  ... 30 more LIKE clauses ...)
--
-- PostgreSQL (array overlap operator, GIN-indexed):
-- AND p.applicant_countries && ARRAY[
--     'AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR',
--     'DE','GR','HU','IE','IT','LV','LT','LU','MT','NL',
--     'PL','PT','RO','SK','SI','ES','SE',
--     'IS','LI','NO','CH'
-- ]::TEXT[];


-- ============================================================================
-- CORDIS REPOSITORY TRANSLATIONS
-- ============================================================================

-- ---------------------------------------------------------------------------
-- search_projects (was: FTS5 MATCH on projects_fts)
-- ---------------------------------------------------------------------------
-- SELECT p.id, p.framework, p.acronym, p.title,
--        p.start_date, p.end_date, p.status,
--        p.total_cost, p.ec_max_contribution,
--        p.funding_scheme, p.keywords
-- FROM cordis_schema.projects p
-- WHERE p.search_vector @@ ti_websearch_tsquery('hydrogen fuel cell')
--   AND p.start_date >= '2015-01-01'::DATE
-- ORDER BY ts_rank_cd(p.search_vector, ti_websearch_tsquery('hydrogen fuel cell')) DESC
-- LIMIT 10000;


-- ---------------------------------------------------------------------------
-- funding_by_year_and_programme
-- ---------------------------------------------------------------------------
-- SELECT EXTRACT(YEAR FROM p.start_date)::INTEGER AS year,
--        p.framework,
--        SUM(p.ec_max_contribution) AS funding,
--        COUNT(*) AS count
-- FROM cordis_schema.projects p
-- WHERE p.search_vector @@ ti_plainto_tsquery('hydrogen')
--   AND p.start_date IS NOT NULL
--   AND p.ec_max_contribution IS NOT NULL
--   AND EXTRACT(YEAR FROM p.start_date) BETWEEN 2015 AND 2025
-- GROUP BY year, p.framework
-- ORDER BY year, p.framework;


-- ---------------------------------------------------------------------------
-- co_participation (was: self-join on organizations)
-- ---------------------------------------------------------------------------
-- SELECT o1.name AS actor_a,
--        o2.name AS actor_b,
--        COUNT(DISTINCT o1.project_id) AS co_count
-- FROM cordis_schema.projects p
-- JOIN cordis_schema.organizations o1 ON o1.project_id = p.id
-- JOIN cordis_schema.organizations o2 ON o2.project_id = p.id
--     AND o2.id > o1.id
-- WHERE p.search_vector @@ ti_plainto_tsquery('hydrogen')
--   AND o1.name IS NOT NULL AND o2.name IS NOT NULL
--   AND p.start_date >= '2015-01-01'::DATE
-- GROUP BY o1.name, o2.name
-- ORDER BY co_count DESC
-- LIMIT 200;


-- ---------------------------------------------------------------------------
-- top_organizations_with_country (sme is now BOOLEAN)
-- ---------------------------------------------------------------------------
-- SELECT o.name, o.country,
--        COUNT(DISTINCT o.project_id) AS count,
--        bool_or(o.sme) AS is_sme,
--        bool_or(o.role = 'coordinator') AS is_coordinator
-- FROM cordis_schema.projects p
-- JOIN cordis_schema.organizations o ON o.project_id = p.id
-- WHERE p.search_vector @@ ti_plainto_tsquery('hydrogen')
--   AND o.name IS NOT NULL
--   AND p.start_date >= '2015-01-01'::DATE
-- GROUP BY o.name, o.country
-- ORDER BY count DESC
-- LIMIT 50;


-- ============================================================================
-- ENTITY RESOLUTION QUERIES
-- ============================================================================

-- Find all source records for a unified actor
-- SELECT ua.canonical_name, ua.country, ua.actor_type,
--        asm.source_type, asm.source_name, asm.confidence, asm.match_method
-- FROM entity_schema.unified_actors ua
-- JOIN entity_schema.actor_source_mappings asm ON asm.unified_actor_id = ua.id
-- WHERE ua.id = 'some-uuid-here'
-- ORDER BY asm.source_type;

-- Cross-source actor search: find an actor across all sources
-- SELECT ua.id, ua.canonical_name,
--        array_agg(DISTINCT asm.source_type) AS present_in,
--        COUNT(DISTINCT asm.source_type) AS source_count
-- FROM entity_schema.unified_actors ua
-- JOIN entity_schema.actor_source_mappings asm ON asm.unified_actor_id = ua.id
-- WHERE ua.canonical_name % 'siemens'
-- GROUP BY ua.id, ua.canonical_name
-- ORDER BY similarity(ua.canonical_name, 'siemens') DESC
-- LIMIT 10;


-- ============================================================================
-- MATERIALIZED VIEW USAGE EXAMPLES
-- ============================================================================

-- Fast CPC co-occurrence lookup (replaces 237M-row self-join)
-- SELECT code_a, code_b, SUM(co_count) AS total_co_count
-- FROM cross_schema.mv_cpc_cooccurrence
-- WHERE pub_year BETWEEN 2020 AND 2025
--   AND (code_a = 'H04W' OR code_b = 'H04W')
-- GROUP BY code_a, code_b
-- ORDER BY total_co_count DESC
-- LIMIT 20;

-- Fast country distribution
-- SELECT country, SUM(patent_count) AS total
-- FROM cross_schema.mv_patent_country_distribution
-- WHERE year BETWEEN 2020 AND 2025
-- GROUP BY country
-- ORDER BY total DESC
-- LIMIT 20;
