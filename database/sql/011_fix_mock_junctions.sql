-- ============================================================================
-- 011_fix_mock_junctions.sql
-- Fehlende Junction-Tabellen aus denormalisierten Mock-Daten ableiten
--
-- Behebt: UC1/UC5/UC8 leer (patent_cpc fehlt)
--         UC3/UC8      leer (patent_applicants / unified_actors fehlen)
--         UC7          leer (research_schema.papers fehlt)
--
-- Voraussetzung: 002_schema.sql + seed_mock.sql bereits ausgefuehrt
-- Ausfuehren:    psql -U postgres -d ti_radar -f 011_fix_mock_junctions.sql
-- ============================================================================

BEGIN;

\echo ''
\echo '=== TI-Radar v3 — Mock-Daten Junction-Fix ==='
\echo ''


-- ============================================================================
-- 1. patent_schema.applicants
--    Extrahiert eindeutige Anmeldernamen aus dem denormalisierten Feld
--    patents.applicant_names (Semikolon-separiert)
-- ============================================================================

\echo '1/6  Fuege Anmeldernamen in patent_schema.applicants ein...'

INSERT INTO patent_schema.applicants (raw_name, normalized_name)
SELECT DISTINCT
    trim(applicant_name)                                   AS raw_name,
    upper(regexp_replace(trim(applicant_name),
          '\s+(GMBH|AG|SA|SAS|SRL|LTD|LLC|INC|CORP|BV|NV|SE|PLC|CO\.)\.?$',
          '', 'i'))                                        AS normalized_name
FROM patent_schema.patents p,
     LATERAL unnest(string_to_array(p.applicant_names, ';')) AS applicant_name
WHERE p.applicant_names IS NOT NULL
  AND trim(applicant_name) <> ''
ON CONFLICT (raw_name) DO NOTHING;

\echo '    -> Fertig.'


-- ============================================================================
-- 2. patent_schema.patent_applicants
--    Verknuepft jedes Patent mit seinen Anmeldern (N:M)
-- ============================================================================

\echo '2/6  Fuege Eintraege in patent_schema.patent_applicants ein...'

INSERT INTO patent_schema.patent_applicants (patent_id, patent_year, applicant_id)
SELECT DISTINCT
    sub.patent_id,
    sub.patent_year,
    a.id
FROM (
    SELECT
        p.id                          AS patent_id,
        p.publication_year            AS patent_year,
        trim(applicant_name)          AS raw_name
    FROM patent_schema.patents p,
         LATERAL unnest(string_to_array(p.applicant_names, ';')) AS applicant_name
    WHERE p.applicant_names IS NOT NULL
      AND p.publication_year IS NOT NULL
      AND trim(applicant_name) <> ''
) sub
JOIN patent_schema.applicants a ON a.raw_name = sub.raw_name
ON CONFLICT DO NOTHING;

\echo '    -> Fertig.'


-- ============================================================================
-- 3. patent_schema.patent_cpc
--    Extrahiert CPC-Subklassen (4-stellig, z.B. 'G06N') aus dem
--    denormalisierten Array patents.cpc_codes.
--    Nur Patente mit >= 2 CPC-Codes (Jaccard-Anforderung).
-- ============================================================================

\echo '3/6  Fuege Eintraege in patent_schema.patent_cpc ein...'

INSERT INTO patent_schema.patent_cpc (patent_id, cpc_code, pub_year)
SELECT DISTINCT
    p.id                             AS patent_id,
    substring(code, 1, 4)           AS cpc_code,
    p.publication_year              AS pub_year
FROM patent_schema.patents p,
     LATERAL unnest(p.cpc_codes) AS code
WHERE p.cpc_codes IS NOT NULL
  AND array_length(p.cpc_codes, 1) >= 2
  AND p.publication_year IS NOT NULL
  AND substring(code, 1, 4) ~ '^[A-HY][0-9]{2}[A-Z]$'
ON CONFLICT DO NOTHING;

\echo '    -> Fertig.'


-- ============================================================================
-- 4. patent_schema.cpc_descriptions
--    Laedt Beschreibungen fuer alle CPC-Subklassen die im Mock vorkommen.
--    Bekannte Quantum-Computing-relevante Codes mit echten Beschreibungen,
--    Rest erhaelt generischen Platzhalter.
-- ============================================================================

\echo '4/6  Fuege CPC-Beschreibungen ein...'

-- Bekannte Beschreibungen fuer haeufige Quantum-Computing-CPC-Codes
INSERT INTO patent_schema.cpc_descriptions (code, section, class_code, description_en, description_de)
VALUES
    ('G06N', 'G', 'G06', 'Computing; Calculating; Counting — Models based on specific computational theories', 'Datenverarbeitung — Modelle basierend auf spezifischen Rechentheorien'),
    ('H04L', 'H', 'H04', 'Electric Communication Technique — Transmission of digital information', 'Elektrische Nachrichtentechnik — Uebertragung digitaler Informationen'),
    ('H04B', 'H', 'H04', 'Electric Communication Technique — Transmission', 'Elektrische Nachrichtentechnik — Uebertragung'),
    ('H04W', 'H', 'H04', 'Electric Communication Technique — Wireless communication networks', 'Elektrische Nachrichtentechnik — Drahtlose Kommunikationsnetze'),
    ('G06F', 'G', 'G06', 'Electric Digital Data Processing', 'Elektrische digitale Datenverarbeitung'),
    ('G06Q', 'G', 'G06', 'Data Processing Systems or Methods specially adapted for Administrative, Commercial, Financial, Managerial, Supervisory, or Forecasting Purposes', 'Datenverarbeitungssysteme fuer administrative, kommerzielle oder finanzielle Zwecke'),
    ('H01L', 'H', 'H01', 'Basic Electric Elements — Semiconductor devices', 'Grundlegende elektrische Bauelemente — Halbleiterbauteile'),
    ('B82Y', 'B', 'B82', 'Nanotechnology', 'Nanotechnologie'),
    ('G01R', 'G', 'G01', 'Measuring; Testing — Electric variables', 'Messen; Pruefen — Elektrische Groessen'),
    ('H03K', 'H', 'H03', 'Basic Electronic Circuitry — Pulse technique', 'Grundlegende elektronische Schaltkreise — Impulstechnik'),
    ('H05H', 'H', 'H05', 'Electric Techniques not otherwise provided for — Plasma technique', 'Elektrische Techniken — Plasmatechnik'),
    ('G01N', 'G', 'G01', 'Investigating or Analysing Materials by determining their chemical or physical properties', 'Untersuchen oder Analysieren von Materialien'),
    ('G02B', 'G', 'G02', 'Optics — Optical elements, systems or apparatus', 'Optik — Optische Elemente, Systeme oder Vorrichtungen'),
    ('A61B', 'A', 'A61', 'Medical or Veterinary Science — Diagnosis; Surgery', 'Medizin oder Veterinaerwesen — Diagnostik; Chirurgie'),
    ('C12N', 'C', 'C12', 'Biochemistry; Microbiology — Micro-organisms or enzymes', 'Biochemie; Mikrobiologie — Mikroorganismen oder Enzyme')
ON CONFLICT (code) DO NOTHING;

-- Alle weiteren Codes aus dem Mock-Datensatz mit generischem Platzhalter
INSERT INTO patent_schema.cpc_descriptions (code, section, class_code, description_en, description_de)
SELECT DISTINCT
    substring(code, 1, 4)           AS code,
    substring(code, 1, 1)           AS section,
    substring(code, 1, 3)           AS class_code,
    '(Description not loaded in mock dataset)' AS description_en,
    NULL                            AS description_de
FROM patent_schema.patents p,
     LATERAL unnest(p.cpc_codes) AS code
WHERE substring(code, 1, 4) ~ '^[A-HY][0-9]{2}[A-Z]$'
ON CONFLICT (code) DO NOTHING;

\echo '    -> Fertig.'


-- ============================================================================
-- 5. entity_schema.unified_actors + actor_source_mappings
--    Erstellt unified_actors aus CORDIS-Organisationen fuer UC3/UC4.
--    Ermoeglicht organisationsuebergreifende Verknuepfungen.
-- ============================================================================

\echo '5/6  Fuege unified_actors und source_mappings aus CORDIS-Orgs ein...'

-- Eindeutige Organisationen als unified_actors
INSERT INTO entity_schema.unified_actors (id, canonical_name, country, actor_type)
SELECT
    gen_random_uuid()                                       AS id,
    o.name                                                  AS canonical_name,
    NULLIF(trim(o.country), '')                             AS country,
    CASE o.activity_type
        WHEN 'HES' THEN 'university'
        WHEN 'REC' THEN 'research_org'
        WHEN 'PRC' THEN 'company'
        WHEN 'PUB' THEN 'government'
        ELSE NULL
    END                                                     AS actor_type
FROM (
    SELECT DISTINCT ON (name)
        name, country, activity_type
    FROM cordis_schema.organizations
    WHERE name IS NOT NULL
    ORDER BY name, id
) o
ON CONFLICT DO NOTHING;

-- source_mappings: CORDIS-Org-IDs mit den unified_actors verknuepfen
INSERT INTO entity_schema.actor_source_mappings
    (unified_actor_id, source_type, source_id, source_name, confidence, match_method)
SELECT
    ua.id                                                   AS unified_actor_id,
    'cordis_org'                                            AS source_type,
    o.id::TEXT                                              AS source_id,
    o.name                                                  AS source_name,
    1.0                                                     AS confidence,
    'exact'                                                 AS match_method
FROM cordis_schema.organizations o
JOIN entity_schema.unified_actors ua ON ua.canonical_name = o.name
ON CONFLICT (source_type, source_id) DO NOTHING;

\echo '    -> Fertig.'


-- ============================================================================
-- 6. research_schema.papers + query_cache
--    Leitet Mock-Papers aus CORDIS-Publikationen ab, damit UC7 nicht leer ist.
-- ============================================================================

\echo '6/6  Fuege Mock-Papers in research_schema aus CORDIS-Publikationen ein...'

-- Papers aus CORDIS-Publikationen
INSERT INTO research_schema.papers
    (semantic_scholar_id, title, year, venue, citation_count,
     influential_citation_count, reference_count, doi,
     is_open_access, fields_of_study, query_technology)
SELECT
    COALESCE(pub.doi, 'mock-cordis-' || pub.id::TEXT)       AS semantic_scholar_id,
    pub.title                                               AS title,
    EXTRACT(YEAR FROM pub.publication_date)::SMALLINT       AS year,
    pub.journal                                             AS venue,
    0                                                       AS citation_count,
    0                                                       AS influential_citation_count,
    0                                                       AS reference_count,
    pub.doi                                                 AS doi,
    pub.open_access                                         AS is_open_access,
    ARRAY['Computer Science', 'Physics']                    AS fields_of_study,
    'quantum computing'                                     AS query_technology
FROM cordis_schema.publications pub
WHERE pub.title IS NOT NULL
  AND pub.title <> ''
ON CONFLICT (semantic_scholar_id) DO NOTHING;

-- Query-Cache-Eintrag damit UC7 weiss: Daten sind vorhanden
INSERT INTO research_schema.query_cache
    (technology, year_start, year_end, result_count, fetched_at, stale_after)
VALUES
    ('quantum computing', 2000, 2024,
     (SELECT COUNT(*) FROM research_schema.papers WHERE query_technology = 'quantum computing'),
     now(),
     now() + INTERVAL '90 days')
ON CONFLICT (technology, year_start, year_end) DO UPDATE
    SET result_count = EXCLUDED.result_count,
        fetched_at   = EXCLUDED.fetched_at,
        stale_after  = EXCLUDED.stale_after;

\echo '    -> Fertig.'


-- ============================================================================
-- Materialized Views neu aufbauen
-- ============================================================================

\echo ''
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

\echo '    -> Alle Views aktualisiert.'


-- ============================================================================
-- Zusammenfassung
-- ============================================================================

\echo ''
\echo '=== Ergebnis ==='

SELECT 'patent_schema.applicants'       AS tabelle, COUNT(*) AS zeilen FROM patent_schema.applicants
UNION ALL
SELECT 'patent_schema.patent_applicants',            COUNT(*) FROM patent_schema.patent_applicants
UNION ALL
SELECT 'patent_schema.patent_cpc',                   COUNT(*) FROM patent_schema.patent_cpc
UNION ALL
SELECT 'patent_schema.cpc_descriptions',             COUNT(*) FROM patent_schema.cpc_descriptions
UNION ALL
SELECT 'entity_schema.unified_actors',               COUNT(*) FROM entity_schema.unified_actors
UNION ALL
SELECT 'entity_schema.actor_source_mappings',        COUNT(*) FROM entity_schema.actor_source_mappings
UNION ALL
SELECT 'research_schema.papers',                     COUNT(*) FROM research_schema.papers
UNION ALL
SELECT 'mv_patent_counts_by_cpc_year',               COUNT(*) FROM cross_schema.mv_patent_counts_by_cpc_year
UNION ALL
SELECT 'mv_cpc_cooccurrence',                        COUNT(*) FROM cross_schema.mv_cpc_cooccurrence
UNION ALL
SELECT 'mv_top_applicants',                          COUNT(*) FROM cross_schema.mv_top_applicants;

COMMIT;

\echo ''
\echo '=== 011_fix_mock_junctions.sql erfolgreich ausgefuehrt ==='
\echo ''
