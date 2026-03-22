-- ============================================================
-- TI-Radar v3 — Mock-Datenbank Seed (Quantum Computing)
-- Laedt CSV-Dateien aus db/mock_data/ in die Datenbank.
-- Voraussetzung: Schema bereits initialisiert (002_schema.sql)
-- ============================================================

BEGIN;

-- 1. EuroSciVoc Taxonomie (muss vor project_euroscivoc geladen werden)
\echo 'Lade EuroSciVoc Taxonomie...'
\copy cordis_schema.euroscivoc FROM 'db/mock_data/euroscivoc.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

-- 2. CORDIS Projekte
\echo 'Lade CORDIS Projekte...'
\copy cordis_schema.projects(id, framework, title, acronym, objective, keywords, start_date, end_date, total_cost, ec_max_contribution, funding_scheme, status, topics, legal_basis) FROM 'db/mock_data/projects.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

-- 3. CORDIS Organisationen
\echo 'Lade CORDIS Organisationen...'
\copy cordis_schema.organizations(id, organisation_id, project_id, name, short_name, country, city, role, activity_type, sme, ec_contribution, total_cost) FROM 'db/mock_data/organizations.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

-- 4. CORDIS Publikationen
\echo 'Lade CORDIS Publikationen...'
\copy cordis_schema.publications FROM 'db/mock_data/publications.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

-- 5. Projekt-EuroSciVoc Zuordnungen
\echo 'Lade EuroSciVoc-Zuordnungen...'
\copy cordis_schema.project_euroscivoc(project_id, euroscivoc_id) FROM 'db/mock_data/project_euroscivoc.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

-- 6. EPO Patente
\echo 'Lade EPO Patente...'
\copy patent_schema.patents(id, publication_number, country, doc_number, kind, title, publication_date, publication_year, family_id, applicant_names, applicant_countries, cpc_codes, ipc_codes, filing_date) FROM 'db/mock_data/patents.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

-- 7. Volltext-Suchvektoren aktualisieren
\echo 'Aktualisiere Suchvektoren...'
UPDATE patent_schema.patents SET search_vector = to_tsvector('english', coalesce(title, ''));
UPDATE cordis_schema.projects SET search_vector = to_tsvector('english', coalesce(title, '') || ' ' || coalesce(objective, '') || ' ' || coalesce(keywords, ''));

-- 8. Materialized Views erstellen/aktualisieren
\echo 'Aktualisiere Materialized Views...'
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_patent_counts_by_cpc_year;
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_cpc_cooccurrence;
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_yearly_tech_counts;
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_top_applicants;
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_patent_country_distribution;
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_project_counts_by_year;
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_cordis_country_pairs;
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_top_cordis_orgs;
REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_funding_by_instrument;

COMMIT;

\echo 'Mock-Datenbank geladen: ~37.000 Records fuer Quantum Computing.'
