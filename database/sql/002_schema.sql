-- ============================================================================
-- 002_schema.sql
-- Complete PostgreSQL 17 Schema for Technology Intelligence Platform
-- Migration from 2x SQLite (patents.db, cordis.db) to single PostgreSQL
-- ============================================================================
--
-- Schema-per-service isolation:
--   patent_schema  -> patent-related services (UC2 maturity, UC5 cpc-flow, patent-grant)
--   cordis_schema  -> CORDIS services (UC4 funding, actor-type, euroscivoc)
--   cross_schema   -> cross-source services (UC1 landscape, UC3 competitive,
--                     UC6 geographic, UC8 temporal)
--   research_schema -> Semantic Scholar cache (UC7 research-impact)
--   entity_schema  -> entity resolution with pg_trgm fuzzy matching
--   export_schema  -> export service cache and report templates
--
-- Depends on: 001_extensions.sql (pg_trgm, vector, uuid-ossp, unaccent)
--
-- Design Decisions:
--
-- 1. PARTITIONING: The patents table is range-partitioned by publication_year.
--    At 154.8M rows, partition pruning eliminates entire decades from scans.
--    Each partition holds ~5-8M rows (per-year), which fits comfortably in
--    PostgreSQL buffer cache. Year-based queries (the dominant access pattern
--    in all 8 use cases) touch only 1-3 partitions instead of a 154M row heap.
--
-- 2. BRIN INDEXES on dates: Block Range INdexes are 100-1000x smaller than
--    B-tree on large monotonically increasing columns. Since patents are
--    imported chronologically, physical row order strongly correlates with
--    publication_date, making BRIN extremely effective.
--
-- 3. tsvector COLUMNS stored as materialized columns (not generated) because
--    PostgreSQL does not support GIN indexes on generated columns. They are
--    maintained via triggers, replacing SQLite FTS5 virtual tables.
--
-- 4. INTEGER PRIMARY KEYS instead of UUIDs for junction tables: At 237M+
--    rows, 4-byte integers save ~3 GB vs 16-byte UUIDs in the patent_cpc
--    table alone. UUIDs are reserved for the entity resolution layer where
--    cross-system identity is the core requirement.
--
-- 5. TEXT[] ARRAYS for denormalized fields (applicant_countries, ipc_codes):
--    PostgreSQL native arrays with GIN indexes replace comma-separated TEXT
--    columns. This eliminates LIKE '%XX%' scans (O(n)) in favor of array
--    containment operators (@>, &&) backed by GIN (O(log n)).
--
-- 6. SEPARATE SCHEMAS per service boundary: patent_schema, cordis_schema,
--    cross_schema, research_schema, entity_schema, export_schema. Each
--    service role gets READ-ONLY access to its own schema plus read from
--    source schemas as needed.
--
-- 7. CHECK CONSTRAINTS replace application-level validation for data
--    integrity on country codes, CPC format, framework programmes, etc.
--
-- 8. MATERIALIZED VIEWS in cross_schema pre-aggregate the expensive joins
--    (CPC co-occurrence, yearly counts, top actors, country distributions)
--    that were computed per-request in the SQLite version.
--
-- 9. pgvector COLUMNS (vector(384)) are provisioned on key tables for
--    future LLM embedding storage. Not populated at initial deployment.
--
-- ============================================================================


-- ============================================================================
-- TRANSACTION: entire schema creation is atomic
-- ============================================================================
BEGIN;


-- ============================================================================
-- SCHEMAS
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS patent_schema;
CREATE SCHEMA IF NOT EXISTS cordis_schema;
CREATE SCHEMA IF NOT EXISTS cross_schema;
CREATE SCHEMA IF NOT EXISTS research_schema;
CREATE SCHEMA IF NOT EXISTS entity_schema;
CREATE SCHEMA IF NOT EXISTS export_schema;

COMMENT ON SCHEMA patent_schema IS
    'EPO patent data and patent-specific analytics. Services: maturity (UC2), cpc-flow (UC5), patent-grant.';
COMMENT ON SCHEMA cordis_schema IS
    'CORDIS EU research project data. Services: funding (UC4), actor-type, euroscivoc.';
COMMENT ON SCHEMA cross_schema IS
    'Cross-source materialized views and analytics. Services: landscape (UC1), competitive (UC3), geographic (UC6), temporal (UC8).';
COMMENT ON SCHEMA research_schema IS
    'Semantic Scholar cache for research impact analysis. Service: research-impact (UC7).';
COMMENT ON SCHEMA entity_schema IS
    'Entity resolution: unified actors across EPO, CORDIS, GLEIF with pg_trgm fuzzy matching.';
COMMENT ON SCHEMA export_schema IS
    'Export service: cached analysis results and report templates.';


-- ============================================================================
-- ============================================================================
-- PATENT_SCHEMA: EPO PATENT DATA (154.8M rows, partitioned)
-- ============================================================================
-- ============================================================================

-- --------------------------------------------------------------------------
-- Main patents table: range-partitioned by publication_year
-- --------------------------------------------------------------------------
-- publication_year is extracted from publication_date at import time and
-- stored as a physical column to enable partition pruning without function
-- evaluation on every row.

CREATE TABLE patent_schema.patents (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY,
    publication_number  TEXT NOT NULL,
    country             CHAR(2) NOT NULL,
    doc_number          TEXT NOT NULL,
    kind                VARCHAR(4),                 -- A1, A2, B1, B2, U1, etc.
    title               TEXT,
    publication_date    DATE,                       -- proper DATE, not TEXT
    publication_year    SMALLINT,                   -- denormalized for partitioning
    family_id           TEXT,
    applicant_names     TEXT,                       -- denormalized legacy field (kept for migration)
    applicant_countries TEXT[],                     -- array replaces CSV text
    cpc_codes           TEXT[],                     -- array replaces CSV text
    ipc_codes           TEXT[],                     -- array replaces CSV text
    filing_date         DATE,                       -- application/filing date for time-to-grant (UC12)
    -- Full-text search vector (maintained by trigger, replaces SQLite FTS5)
    search_vector       tsvector,
    -- LLM embedding of title (384-dim for multilingual-e5-small)
    title_embedding     vector(384),

    CONSTRAINT pk_patents PRIMARY KEY (id, publication_year),
    CONSTRAINT uq_patents_pubnum UNIQUE (publication_number, publication_year),
    CONSTRAINT ck_patents_country CHECK (country ~ '^[A-Z]{2}$'),
    CONSTRAINT ck_patents_kind CHECK (kind IS NULL OR kind ~ '^[A-Z][0-9]?$'),
    CONSTRAINT ck_patents_year CHECK (
        publication_year IS NULL
        OR (publication_year >= 1900 AND publication_year <= 2100)
    )
) PARTITION BY RANGE (publication_year);

-- Partitions: pre-1980 catch-all, decade partitions, per-year 2000-2030, future
CREATE TABLE patent_schema.patents_pre1980 PARTITION OF patent_schema.patents
    FOR VALUES FROM (MINVALUE) TO (1980);
CREATE TABLE patent_schema.patents_1980s PARTITION OF patent_schema.patents
    FOR VALUES FROM (1980) TO (1990);
CREATE TABLE patent_schema.patents_1990s PARTITION OF patent_schema.patents
    FOR VALUES FROM (1990) TO (2000);

DO $$
BEGIN
    FOR yr IN 2000..2030 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS patent_schema.patents_%s PARTITION OF patent_schema.patents
             FOR VALUES FROM (%s) TO (%s)',
            yr, yr, yr + 1
        );
    END LOOP;
END $$;

CREATE TABLE patent_schema.patents_future PARTITION OF patent_schema.patents
    FOR VALUES FROM (2031) TO (MAXVALUE);

COMMENT ON TABLE patent_schema.patents IS
    'EPO DOCDB patent publications. 154.8M rows. Range-partitioned by publication_year.';
COMMENT ON COLUMN patent_schema.patents.publication_year IS
    'Extracted from publication_date at import time. Partition key. Maintained by trigger.';
COMMENT ON COLUMN patent_schema.patents.applicant_countries IS
    'Array of 2-letter ISO country codes from applicant residence. GIN-indexed for @> containment.';
COMMENT ON COLUMN patent_schema.patents.search_vector IS
    'tsvector of title (weight A) + cpc_codes (weight B) for full-text search. Replaces SQLite FTS5.';
COMMENT ON COLUMN patent_schema.patents.title_embedding IS
    '384-dim vector (multilingual-e5-small) for semantic similarity search via pgvector.';


-- --------------------------------------------------------------------------
-- Normalized applicants (15.5M unique)
-- --------------------------------------------------------------------------

CREATE TABLE patent_schema.applicants (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    raw_name            TEXT NOT NULL,
    normalized_name     TEXT NOT NULL,

    CONSTRAINT uq_applicants_raw UNIQUE (raw_name)
);

COMMENT ON TABLE patent_schema.applicants IS
    'Unique patent applicants. 15.5M rows. raw_name = original EPO string, '
    'normalized_name = corporate suffixes stripped, uppercase, deduplicated.';


-- --------------------------------------------------------------------------
-- Patent-Applicant junction (147M rows, co-partitioned)
-- --------------------------------------------------------------------------

CREATE TABLE patent_schema.patent_applicants (
    patent_id           BIGINT NOT NULL,
    patent_year         SMALLINT NOT NULL,          -- enables partition-aware joins
    applicant_id        INTEGER NOT NULL REFERENCES patent_schema.applicants(id),
    CONSTRAINT pk_patent_applicants PRIMARY KEY (patent_id, patent_year, applicant_id)
) PARTITION BY RANGE (patent_year);

-- Mirror the patents partition structure for co-located joins
CREATE TABLE patent_schema.patent_applicants_pre1980 PARTITION OF patent_schema.patent_applicants
    FOR VALUES FROM (MINVALUE) TO (1980);
CREATE TABLE patent_schema.patent_applicants_1980s PARTITION OF patent_schema.patent_applicants
    FOR VALUES FROM (1980) TO (1990);
CREATE TABLE patent_schema.patent_applicants_1990s PARTITION OF patent_schema.patent_applicants
    FOR VALUES FROM (1990) TO (2000);

DO $$
BEGIN
    FOR yr IN 2000..2030 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS patent_schema.patent_applicants_%s
             PARTITION OF patent_schema.patent_applicants
             FOR VALUES FROM (%s) TO (%s)',
            yr, yr, yr + 1
        );
    END LOOP;
END $$;

CREATE TABLE patent_schema.patent_applicants_future PARTITION OF patent_schema.patent_applicants
    FOR VALUES FROM (2031) TO (MAXVALUE);

COMMENT ON TABLE patent_schema.patent_applicants IS
    'Patent-to-applicant N:M junction. 147M rows. Co-partitioned with patents by year.';


-- --------------------------------------------------------------------------
-- Patent-CPC junction (237M rows, co-partitioned)
-- --------------------------------------------------------------------------
-- Heaviest table by join frequency: every UC5 CPC Jaccard computation runs
-- a self-join here. Partitioning + covering index are critical.

CREATE TABLE patent_schema.patent_cpc (
    patent_id           BIGINT NOT NULL,
    cpc_code            VARCHAR(8) NOT NULL,        -- level-4 subclass e.g. 'H04W'
    pub_year            SMALLINT NOT NULL,
    CONSTRAINT pk_patent_cpc PRIMARY KEY (patent_id, cpc_code, pub_year),
    CONSTRAINT ck_cpc_format CHECK (cpc_code ~ '^[A-HY][0-9]{2}[A-Z]?$')
) PARTITION BY RANGE (pub_year);

CREATE TABLE patent_schema.patent_cpc_pre1980 PARTITION OF patent_schema.patent_cpc
    FOR VALUES FROM (MINVALUE) TO (1980);
CREATE TABLE patent_schema.patent_cpc_1980s PARTITION OF patent_schema.patent_cpc
    FOR VALUES FROM (1980) TO (1990);
CREATE TABLE patent_schema.patent_cpc_1990s PARTITION OF patent_schema.patent_cpc
    FOR VALUES FROM (1990) TO (2000);

DO $$
BEGIN
    FOR yr IN 2000..2030 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS patent_schema.patent_cpc_%s
             PARTITION OF patent_schema.patent_cpc
             FOR VALUES FROM (%s) TO (%s)',
            yr, yr, yr + 1
        );
    END LOOP;
END $$;

CREATE TABLE patent_schema.patent_cpc_future PARTITION OF patent_schema.patent_cpc
    FOR VALUES FROM (2031) TO (MAXVALUE);

COMMENT ON TABLE patent_schema.patent_cpc IS
    'Patent-to-CPC junction at level 4 (subclass). 237M rows. '
    'Only patents with >= 2 distinct CPC codes are included (Jaccard requires pairs).';


-- --------------------------------------------------------------------------
-- CPC descriptions (static reference, ~670 subclasses)
-- --------------------------------------------------------------------------

CREATE TABLE patent_schema.cpc_descriptions (
    code                VARCHAR(8) PRIMARY KEY,     -- e.g. 'H04W'
    section             CHAR(1) NOT NULL,           -- A-H, Y
    class_code          VARCHAR(4),                 -- e.g. 'H04'
    description_en      TEXT NOT NULL,
    description_de      TEXT,

    CONSTRAINT ck_cpc_section CHECK (section ~ '^[A-HY]$')
);

COMMENT ON TABLE patent_schema.cpc_descriptions IS
    'CPC classification code descriptions. Static reference data (~670 subclass entries).';


-- --------------------------------------------------------------------------
-- EPO import metadata (tracks which ZIP files have been processed)
-- --------------------------------------------------------------------------

CREATE TABLE patent_schema.import_metadata (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source              TEXT NOT NULL DEFAULT 'EPO-DOCDB',
    file_name           TEXT NOT NULL,
    import_date         TIMESTAMPTZ NOT NULL DEFAULT now(),
    record_count        INTEGER,
    duration_seconds    REAL
);

COMMENT ON TABLE patent_schema.import_metadata IS
    'Tracks processed EPO DOCDB ZIP files for resume support.';


-- --------------------------------------------------------------------------
-- EPO OPS API Cache (query-level caching for live adapter)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patent_schema.epo_ops_cache (
    technology   TEXT        NOT NULL,
    start_year   SMALLINT,
    end_year     SMALLINT,
    result_json  JSONB       NOT NULL DEFAULT '[]',
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stale_after  TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '7 days',
    CONSTRAINT pk_epo_ops_cache PRIMARY KEY (technology, start_year, end_year)
);

CREATE INDEX IF NOT EXISTS idx_epo_ops_cache_stale
    ON patent_schema.epo_ops_cache (stale_after);

COMMENT ON TABLE patent_schema.epo_ops_cache IS
    'Query-level cache for EPO OPS REST API responses (7-day TTL).';


-- --------------------------------------------------------------------------
-- Patent Citations (Forward/Backward Citation Analysis, UC-F)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patent_schema.patent_citations (
    citing_patent      TEXT NOT NULL,
    cited_patent       TEXT NOT NULL,
    citation_category  TEXT,
    cited_phase        TEXT,
    citing_year        INTEGER,
    PRIMARY KEY (citing_patent, cited_patent)
);

CREATE INDEX IF NOT EXISTS idx_citations_cited
    ON patent_schema.patent_citations (cited_patent);

CREATE INDEX IF NOT EXISTS idx_citations_year
    ON patent_schema.patent_citations (citing_year);

CREATE INDEX IF NOT EXISTS idx_citations_category
    ON patent_schema.patent_citations (citation_category)
    WHERE citation_category IS NOT NULL;

COMMENT ON TABLE patent_schema.patent_citations IS
    'Patent citation network — Forward/Backward Citations from EPO DOCDB XML (UC-F).';
COMMENT ON COLUMN patent_schema.patent_citations.citation_category IS
    'EPO category: X=particularly relevant, Y=relevant in combination, A=prior art, D=cited in proceedings.';


-- --------------------------------------------------------------------------
-- PATENT_SCHEMA INDEXES
-- --------------------------------------------------------------------------

-- BRIN on publication_date: tiny index (~200 KB) for date-range scans on 154M rows.
-- Effective because data is imported chronologically (physical order = date order).
CREATE INDEX idx_patents_date_brin ON patent_schema.patents
    USING brin (publication_date) WITH (pages_per_range = 32);

-- B-tree on filing_date for UC12 time-to-grant calculation (filing_date → publication_date)
CREATE INDEX idx_patents_filing_date ON patent_schema.patents (filing_date)
    WHERE filing_date IS NOT NULL;

-- B-tree on country (high selectivity for single-country queries)
CREATE INDEX idx_patents_country ON patent_schema.patents (country);

-- B-tree on family_id (UC2 patent family deduplication, Gao et al. 2013)
CREATE INDEX idx_patents_family ON patent_schema.patents (family_id)
    WHERE family_id IS NOT NULL;

-- GIN on tsvector for full-text search (replaces SQLite FTS5)
CREATE INDEX idx_patents_search ON patent_schema.patents USING gin (search_vector);

-- GIN on arrays for containment queries (WHERE 'DE' = ANY(applicant_countries))
CREATE INDEX idx_patents_applicant_countries ON patent_schema.patents
    USING gin (applicant_countries);
CREATE INDEX idx_patents_cpc_array ON patent_schema.patents
    USING gin (cpc_codes);

-- pg_trgm GIN on title for fuzzy/autocomplete search
CREATE INDEX idx_patents_title_trgm ON patent_schema.patents
    USING gin (title gin_trgm_ops);

-- Applicant indexes
CREATE INDEX idx_applicants_norm ON patent_schema.applicants (normalized_name);
CREATE INDEX idx_applicants_norm_trgm ON patent_schema.applicants
    USING gin (normalized_name gin_trgm_ops);

-- Patent-applicant junction index
CREATE INDEX idx_pa_applicant ON patent_schema.patent_applicants (applicant_id);

-- Patent-CPC covering indexes for Jaccard self-join
-- (cpc_code, pub_year, patent_id) allows index-only scans for co-occurrence
CREATE INDEX idx_pc_cpc_year_patent ON patent_schema.patent_cpc (cpc_code, pub_year, patent_id);
CREATE INDEX idx_pc_patent_cpc ON patent_schema.patent_cpc (patent_id, cpc_code);


-- --------------------------------------------------------------------------
-- PATENT_SCHEMA TRIGGERS
-- --------------------------------------------------------------------------

-- Trigger function: builds search_vector from title + array-to-string(cpc_codes)
CREATE OR REPLACE FUNCTION patent_schema.patents_search_vector_update()
RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(array_to_string(NEW.cpc_codes, ' '), '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_patents_search_vector
    BEFORE INSERT OR UPDATE OF title, cpc_codes
    ON patent_schema.patents
    FOR EACH ROW
    EXECUTE FUNCTION patent_schema.patents_search_vector_update();

-- Trigger function: auto-populate publication_year from publication_date
CREATE OR REPLACE FUNCTION patent_schema.patents_year_update()
RETURNS trigger AS $$
BEGIN
    IF NEW.publication_date IS NOT NULL THEN
        NEW.publication_year := EXTRACT(YEAR FROM NEW.publication_date)::SMALLINT;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_patents_year
    BEFORE INSERT OR UPDATE OF publication_date
    ON patent_schema.patents
    FOR EACH ROW
    EXECUTE FUNCTION patent_schema.patents_year_update();


-- ============================================================================
-- ============================================================================
-- CORDIS_SCHEMA: EU RESEARCH PROJECT DATA
-- ============================================================================
-- ============================================================================

-- --------------------------------------------------------------------------
-- Projects (80.5K rows, not partitioned -- small table)
-- --------------------------------------------------------------------------

CREATE TABLE cordis_schema.projects (
    id                  INTEGER PRIMARY KEY,        -- CORDIS project ID (natural key)
    rcn                 INTEGER,
    framework           VARCHAR(10) NOT NULL,
    acronym             VARCHAR(50),
    title               TEXT NOT NULL,
    objective           TEXT,
    keywords            TEXT,
    start_date          DATE,                       -- proper DATE, not TEXT
    end_date            DATE,                       -- proper DATE, not TEXT
    status              VARCHAR(20),
    total_cost          NUMERIC(15,2),              -- NUMERIC for monetary precision
    ec_max_contribution NUMERIC(15,2),
    funding_scheme      VARCHAR(50),
    topics              TEXT,
    legal_basis         TEXT,
    cordis_update_date  TIMESTAMPTZ,
    -- Full-text search (replaces SQLite FTS5)
    search_vector       tsvector,
    -- Future: LLM embedding of title + objective
    content_embedding   vector(384),

    CONSTRAINT ck_framework CHECK (
        framework IN ('FP7', 'H2020', 'HORIZON', 'UNKNOWN')
    ),
    CONSTRAINT ck_dates CHECK (
        start_date IS NULL OR end_date IS NULL OR start_date <= end_date
    ),
    CONSTRAINT ck_cost CHECK (
        total_cost IS NULL OR total_cost >= 0
    ),
    CONSTRAINT ck_ec_contribution CHECK (
        ec_max_contribution IS NULL OR ec_max_contribution >= 0
    )
);

COMMENT ON TABLE cordis_schema.projects IS
    'CORDIS EU research projects (FP7, H2020, HORIZON). 80.5K rows. Natural key = CORDIS project ID.';


-- --------------------------------------------------------------------------
-- Organizations / project participants (438K rows)
-- --------------------------------------------------------------------------

CREATE TABLE cordis_schema.organizations (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    organisation_id     INTEGER,                    -- CORDIS internal org ID
    project_id          INTEGER NOT NULL REFERENCES cordis_schema.projects(id),
    name                TEXT NOT NULL,
    short_name          VARCHAR(50),
    country             CHAR(2),
    city                TEXT,
    role                VARCHAR(20),                -- 'coordinator', 'participant'
    activity_type       VARCHAR(5),                 -- 'HES', 'PRC', 'REC', 'OTH', 'PUB'
    sme                 BOOLEAN,                    -- proper BOOLEAN (was TEXT 'YES'/'false' in SQLite)
    ec_contribution     NUMERIC(15,2),
    total_cost          NUMERIC(15,2),

    CONSTRAINT ck_org_role CHECK (
        role IS NULL OR role IN (
            'coordinator', 'participant', 'partner',
            'associatedpartner', 'thirdparty', 'internationalpartner'
        )
    ),
    CONSTRAINT ck_org_activity CHECK (
        activity_type IS NULL
        OR activity_type IN ('HES', 'PRC', 'REC', 'OTH', 'PUB')
    ),
    CONSTRAINT uq_org_project_name UNIQUE (project_id, name)
);

COMMENT ON TABLE cordis_schema.organizations IS
    'CORDIS project participants. 438K rows. sme = native BOOLEAN (was TEXT in SQLite). '
    'activity_type: HES=Higher Education, PRC=Private Company, REC=Research Org, PUB=Public Body, OTH=Other.';


-- --------------------------------------------------------------------------
-- CORDIS Publications (529K rows)
-- --------------------------------------------------------------------------

CREATE TABLE cordis_schema.publications (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id          INTEGER REFERENCES cordis_schema.projects(id),
    title               TEXT,
    authors             TEXT,
    journal             TEXT,
    publication_date    DATE,
    doi                 TEXT,
    open_access         BOOLEAN,
    -- Full-text search
    search_vector       tsvector,

    CONSTRAINT uq_publications_doi UNIQUE (doi)
);

COMMENT ON TABLE cordis_schema.publications IS
    'CORDIS project publications. 529K rows. DOI unique-constrained for deduplication.';


-- --------------------------------------------------------------------------
-- EuroSciVoc taxonomy (~220K entries, hierarchical self-referencing)
-- --------------------------------------------------------------------------

CREATE TABLE cordis_schema.euroscivoc (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code                TEXT NOT NULL UNIQUE,        -- EuroSciVoc URI / code
    label_en            TEXT NOT NULL,
    label_de            TEXT,
    parent_code         TEXT,                        -- self-ref added as FK after table creation
    level               SMALLINT NOT NULL DEFAULT 0,

    CONSTRAINT ck_euroscivoc_level CHECK (level >= 0 AND level <= 10)
);

-- Self-referencing FK (must be added after table creation for insert ordering)
ALTER TABLE cordis_schema.euroscivoc
    ADD CONSTRAINT fk_euroscivoc_parent
    FOREIGN KEY (parent_code) REFERENCES cordis_schema.euroscivoc(code)
    DEFERRABLE INITIALLY DEFERRED;

COMMENT ON TABLE cordis_schema.euroscivoc IS
    'EuroSciVoc scientific taxonomy. ~220K entries. Hierarchical tree via parent_code self-reference.';


-- --------------------------------------------------------------------------
-- Project-EuroSciVoc junction
-- --------------------------------------------------------------------------

CREATE TABLE cordis_schema.project_euroscivoc (
    project_id          INTEGER NOT NULL REFERENCES cordis_schema.projects(id),
    euroscivoc_id       INTEGER NOT NULL REFERENCES cordis_schema.euroscivoc(id),
    PRIMARY KEY (project_id, euroscivoc_id)
);

COMMENT ON TABLE cordis_schema.project_euroscivoc IS
    'Junction: which EuroSciVoc categories are assigned to which CORDIS projects.';


-- --------------------------------------------------------------------------
-- CORDIS import metadata
-- --------------------------------------------------------------------------

CREATE TABLE cordis_schema.import_metadata (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source              TEXT NOT NULL,               -- 'FP7', 'H2020', 'HORIZON'
    file_name           TEXT NOT NULL,
    import_date         TIMESTAMPTZ NOT NULL DEFAULT now(),
    record_count        INTEGER,
    cordis_update_date  TIMESTAMPTZ
);

COMMENT ON TABLE cordis_schema.import_metadata IS
    'Tracks processed CORDIS bulk download files.';


-- --------------------------------------------------------------------------
-- CORDIS API Cache (query-level caching for live adapter)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cordis_schema.cordis_api_cache (
    technology   TEXT        PRIMARY KEY,
    result_json  JSONB       NOT NULL DEFAULT '[]',
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stale_after  TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '7 days'
);

CREATE INDEX IF NOT EXISTS idx_cordis_api_cache_stale
    ON cordis_schema.cordis_api_cache (stale_after);

COMMENT ON TABLE cordis_schema.cordis_api_cache IS
    'Query-level cache for CORDIS REST API responses (7-day TTL).';


-- --------------------------------------------------------------------------
-- CORDIS_SCHEMA INDEXES
-- --------------------------------------------------------------------------

-- Projects
CREATE INDEX idx_projects_framework ON cordis_schema.projects (framework);
CREATE INDEX idx_projects_dates_brin ON cordis_schema.projects
    USING brin (start_date);
CREATE INDEX idx_projects_status ON cordis_schema.projects (status);
CREATE INDEX idx_projects_search ON cordis_schema.projects USING gin (search_vector);
CREATE INDEX idx_projects_title_trgm ON cordis_schema.projects
    USING gin (title gin_trgm_ops);

-- Organizations
CREATE INDEX idx_orgs_project ON cordis_schema.organizations (project_id);
CREATE INDEX idx_orgs_country ON cordis_schema.organizations (country);
CREATE INDEX idx_orgs_name ON cordis_schema.organizations (name);
CREATE INDEX idx_orgs_name_trgm ON cordis_schema.organizations
    USING gin (name gin_trgm_ops);
CREATE INDEX idx_orgs_activity ON cordis_schema.organizations (activity_type);
CREATE INDEX idx_orgs_org_id ON cordis_schema.organizations (organisation_id)
    WHERE organisation_id IS NOT NULL;

-- Publications
CREATE INDEX idx_pubs_project ON cordis_schema.publications (project_id);
CREATE INDEX idx_pubs_date_brin ON cordis_schema.publications
    USING brin (publication_date);
CREATE INDEX idx_pubs_doi ON cordis_schema.publications (doi)
    WHERE doi IS NOT NULL;
CREATE INDEX idx_pubs_search ON cordis_schema.publications USING gin (search_vector);

-- EuroSciVoc
CREATE INDEX idx_euroscivoc_parent ON cordis_schema.euroscivoc (parent_code);
CREATE INDEX idx_euroscivoc_label_trgm ON cordis_schema.euroscivoc
    USING gin (label_en gin_trgm_ops);
CREATE INDEX idx_euroscivoc_level ON cordis_schema.euroscivoc (level);

-- Project-EuroSciVoc junction
CREATE INDEX idx_pe_euroscivoc ON cordis_schema.project_euroscivoc (euroscivoc_id);


-- --------------------------------------------------------------------------
-- CORDIS_SCHEMA TRIGGERS
-- --------------------------------------------------------------------------

-- Projects: tsvector maintenance
CREATE OR REPLACE FUNCTION cordis_schema.projects_search_vector_update()
RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.objective, '')), 'B') ||
        setweight(to_tsvector('simple', coalesce(NEW.keywords, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_projects_search_vector
    BEFORE INSERT OR UPDATE OF title, objective, keywords
    ON cordis_schema.projects
    FOR EACH ROW
    EXECUTE FUNCTION cordis_schema.projects_search_vector_update();

-- Publications: tsvector maintenance
CREATE OR REPLACE FUNCTION cordis_schema.publications_search_vector_update()
RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(NEW.authors, '')), 'B') ||
        setweight(to_tsvector('simple', coalesce(NEW.journal, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_publications_search_vector
    BEFORE INSERT OR UPDATE OF title, authors, journal
    ON cordis_schema.publications
    FOR EACH ROW
    EXECUTE FUNCTION cordis_schema.publications_search_vector_update();


-- ============================================================================
-- ============================================================================
-- RESEARCH_SCHEMA: Semantic Scholar cache (UC7)
-- ============================================================================
-- ============================================================================

-- --------------------------------------------------------------------------
-- Cached papers from Semantic Scholar Academic Graph API
-- --------------------------------------------------------------------------

CREATE TABLE research_schema.papers (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    semantic_scholar_id TEXT NOT NULL UNIQUE,        -- Semantic Scholar paper ID (corpusId or paperId)
    title               TEXT NOT NULL,
    year                SMALLINT,
    venue               TEXT,
    citation_count      INTEGER NOT NULL DEFAULT 0,
    influential_citation_count INTEGER NOT NULL DEFAULT 0,
    reference_count     INTEGER NOT NULL DEFAULT 0,
    doi                 TEXT,
    is_open_access      BOOLEAN,
    publication_types   TEXT[],                      -- e.g. {'JournalArticle', 'Conference'}
    fields_of_study     TEXT[],                      -- e.g. {'Computer Science', 'Physics'}
    -- Full-text search
    search_vector       tsvector,
    -- Future: abstract embedding for semantic search
    abstract_embedding  vector(384),
    -- Cache management
    fetched_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    query_technology    TEXT NOT NULL,                -- which technology query fetched this paper
    stale_after         TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '30 days'),

    CONSTRAINT ck_paper_year CHECK (year IS NULL OR (year >= 1900 AND year <= 2100)),
    CONSTRAINT ck_citations CHECK (citation_count >= 0)
);

COMMENT ON TABLE research_schema.papers IS
    'Semantic Scholar paper cache for UC7 research impact. 30-day TTL. '
    'Re-fetched when stale_after is reached.';


-- --------------------------------------------------------------------------
-- Cached authors from Semantic Scholar
-- --------------------------------------------------------------------------

CREATE TABLE research_schema.authors (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    semantic_scholar_id TEXT NOT NULL UNIQUE,        -- Semantic Scholar author ID
    name                TEXT NOT NULL,
    affiliation         TEXT,
    country_code        CHAR(2),
    h_index             INTEGER,
    paper_count         INTEGER,
    citation_count      INTEGER,
    fetched_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE research_schema.authors IS
    'Semantic Scholar author cache. Linked to papers via paper_authors junction.';


-- --------------------------------------------------------------------------
-- Paper-Author junction
-- --------------------------------------------------------------------------

CREATE TABLE research_schema.paper_authors (
    paper_id            BIGINT NOT NULL REFERENCES research_schema.papers(id) ON DELETE CASCADE,
    author_id           BIGINT NOT NULL REFERENCES research_schema.authors(id) ON DELETE CASCADE,
    author_position     SMALLINT,                   -- 1 = first author, NULL = unknown
    PRIMARY KEY (paper_id, author_id)
);


-- --------------------------------------------------------------------------
-- Search query log (tracks which queries have been cached)
-- --------------------------------------------------------------------------

CREATE TABLE research_schema.query_cache (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    technology          TEXT NOT NULL,
    year_start          SMALLINT NOT NULL,
    year_end            SMALLINT NOT NULL,
    result_count        INTEGER NOT NULL DEFAULT 0,
    total_available     INTEGER,                     -- total from S2 API
    fetched_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    stale_after         TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '30 days'),

    CONSTRAINT uq_query_cache UNIQUE (technology, year_start, year_end)
);

COMMENT ON TABLE research_schema.query_cache IS
    'Tracks which Semantic Scholar queries have been cached and when they expire.';


-- --------------------------------------------------------------------------
-- OpenAIRE API Cache (publication counts per keyword+year)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS research_schema.openaire_cache (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    query_key       TEXT NOT NULL,
    year            INT NOT NULL,
    count           INT NOT NULL,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    stale_after     TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '7 days'),
    CONSTRAINT uq_openaire_cache UNIQUE (query_key, year)
);

COMMENT ON TABLE research_schema.openaire_cache IS
    'Cache for OpenAIRE publication count API responses (7-day TTL). '
    'Each row stores the publication count for a (keyword, year) pair.';


-- --------------------------------------------------------------------------
-- RESEARCH_SCHEMA INDEXES
-- --------------------------------------------------------------------------

CREATE INDEX idx_papers_year ON research_schema.papers (year);
CREATE INDEX idx_papers_citations ON research_schema.papers (citation_count DESC);
CREATE INDEX idx_papers_doi ON research_schema.papers (doi) WHERE doi IS NOT NULL;
CREATE INDEX idx_papers_query ON research_schema.papers (query_technology);
CREATE INDEX idx_papers_stale ON research_schema.papers (stale_after);
CREATE INDEX idx_papers_search ON research_schema.papers USING gin (search_vector);
CREATE INDEX idx_papers_fields ON research_schema.papers USING gin (fields_of_study);
CREATE INDEX idx_papers_types ON research_schema.papers USING gin (publication_types);

CREATE INDEX idx_authors_name_trgm ON research_schema.authors
    USING gin (name gin_trgm_ops);
CREATE INDEX idx_authors_hindex ON research_schema.authors (h_index DESC NULLS LAST);

CREATE INDEX idx_pa_author ON research_schema.paper_authors (author_id);
CREATE INDEX idx_query_cache_stale ON research_schema.query_cache (stale_after);

CREATE INDEX IF NOT EXISTS idx_openaire_cache_stale
    ON research_schema.openaire_cache (query_key, stale_after);


-- --------------------------------------------------------------------------
-- RESEARCH_SCHEMA TRIGGERS
-- --------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION research_schema.papers_search_vector_update()
RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(NEW.venue, '')), 'B') ||
        setweight(to_tsvector('simple', coalesce(array_to_string(NEW.fields_of_study, ' '), '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_papers_search_vector
    BEFORE INSERT OR UPDATE OF title, venue, fields_of_study
    ON research_schema.papers
    FOR EACH ROW
    EXECUTE FUNCTION research_schema.papers_search_vector_update();


-- ============================================================================
-- ============================================================================
-- ENTITY_SCHEMA: Cross-source entity resolution
-- ============================================================================
-- ============================================================================

-- --------------------------------------------------------------------------
-- GLEIF LEI cache (migrated from gleif_cache.db)
-- --------------------------------------------------------------------------

CREATE TABLE entity_schema.gleif_cache (
    raw_name            TEXT PRIMARY KEY,
    lei                 CHAR(20),                   -- LEI is always 20 chars
    legal_name          TEXT,
    country             CHAR(2),
    city                TEXT,
    category            VARCHAR(20),                -- 'FUND', 'GENERAL', etc.
    registration_status VARCHAR(20),
    resolved_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ck_lei_format CHECK (
        lei IS NULL OR lei ~ '^[A-Z0-9]{20}$'
    )
);

CREATE INDEX idx_gleif_lei ON entity_schema.gleif_cache (lei) WHERE lei IS NOT NULL;
CREATE INDEX idx_gleif_resolved ON entity_schema.gleif_cache (resolved_at);
CREATE INDEX idx_gleif_name_trgm ON entity_schema.gleif_cache
    USING gin (raw_name gin_trgm_ops);

COMMENT ON TABLE entity_schema.gleif_cache IS
    'GLEIF LEI lookup cache. 90-day TTL. Negative results stored as NULL lei/legal_name.';


-- --------------------------------------------------------------------------
-- Unified actors: single source of truth for "who is this organization?"
-- --------------------------------------------------------------------------
-- Each row represents one real-world entity that may appear under different
-- names in EPO, CORDIS, and GLEIF.

CREATE TABLE entity_schema.unified_actors (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name      TEXT NOT NULL,              -- best-known name
    country             CHAR(2),
    actor_type          VARCHAR(20),                -- classification
    gleif_lei           CHAR(20),                   -- optional GLEIF link
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Future: LLM embedding of actor profile for semantic actor search
    name_embedding      vector(384),

    CONSTRAINT ck_actor_type CHECK (
        actor_type IS NULL OR actor_type IN (
            'company', 'university', 'research_org', 'individual', 'government'
        )
    )
);

CREATE INDEX idx_unified_canonical_trgm ON entity_schema.unified_actors
    USING gin (canonical_name gin_trgm_ops);
CREATE INDEX idx_unified_country ON entity_schema.unified_actors (country);
CREATE INDEX idx_unified_actor_type ON entity_schema.unified_actors (actor_type);
CREATE INDEX idx_unified_lei ON entity_schema.unified_actors (gleif_lei)
    WHERE gleif_lei IS NOT NULL;

COMMENT ON TABLE entity_schema.unified_actors IS
    'Entity resolution: one row per real-world organization. UUID PK for cross-system identity. '
    'actor_type: company, university, research_org, individual, government.';


-- --------------------------------------------------------------------------
-- Source record mappings: links unified_actor_id to EPO / CORDIS / GLEIF
-- --------------------------------------------------------------------------

CREATE TABLE entity_schema.actor_source_mappings (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unified_actor_id    UUID NOT NULL REFERENCES entity_schema.unified_actors(id) ON DELETE CASCADE,
    source_type         VARCHAR(20) NOT NULL,        -- 'epo_applicant', 'cordis_org', 'gleif'
    source_id           TEXT NOT NULL,               -- applicant.id, organization.id, or LEI
    source_name         TEXT NOT NULL,               -- original name in that source
    confidence          REAL NOT NULL DEFAULT 1.0,   -- fuzzy match confidence (0.0-1.0)
    match_method        VARCHAR(30),                 -- 'exact', 'fuzzy_trgm', 'levenshtein', 'lei_match', 'manual'
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_actor_source UNIQUE (source_type, source_id),
    CONSTRAINT ck_source_type CHECK (
        source_type IN ('epo_applicant', 'cordis_org', 'gleif')
    ),
    CONSTRAINT ck_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

CREATE INDEX idx_asm_unified ON entity_schema.actor_source_mappings (unified_actor_id);
CREATE INDEX idx_asm_source ON entity_schema.actor_source_mappings (source_type, source_id);
CREATE INDEX idx_asm_source_name_trgm ON entity_schema.actor_source_mappings
    USING gin (source_name gin_trgm_ops);
CREATE INDEX idx_asm_confidence ON entity_schema.actor_source_mappings (confidence)
    WHERE confidence < 1.0;

COMMENT ON TABLE entity_schema.actor_source_mappings IS
    'Maps unified_actors to source records in EPO, CORDIS, GLEIF. '
    'confidence indicates fuzzy match quality. match_method records resolution algorithm.';


-- --------------------------------------------------------------------------
-- Entity resolution run log
-- --------------------------------------------------------------------------

CREATE TABLE entity_schema.resolution_runs (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ,
    status              VARCHAR(20) NOT NULL DEFAULT 'running',
    source_type         VARCHAR(20) NOT NULL,
    records_processed   INTEGER DEFAULT 0,
    records_matched     INTEGER DEFAULT 0,
    records_created     INTEGER DEFAULT 0,
    strategy            VARCHAR(50),                 -- 'trgm_batch', 'lei_exact', 'manual_review'
    notes               TEXT,

    CONSTRAINT ck_resolution_status CHECK (
        status IN ('running', 'completed', 'failed', 'cancelled')
    )
);

COMMENT ON TABLE entity_schema.resolution_runs IS
    'Audit log of entity resolution batch runs.';


-- ============================================================================
-- ============================================================================
-- CROSS_SCHEMA: Pre-aggregated materialized views for cross-source analysis
-- ============================================================================
-- ============================================================================
-- These replace expensive per-request aggregations that were computed live
-- in the SQLite version. Refresh strategy: REFRESH MATERIALIZED VIEW CONCURRENTLY
-- after each data import (does not block reads).


-- --------------------------------------------------------------------------
-- MV1: Patent counts by CPC code and year
-- Used by: UC1 (landscape), UC5 (CPC flow), UC8 (temporal)
-- --------------------------------------------------------------------------

CREATE MATERIALIZED VIEW cross_schema.mv_patent_counts_by_cpc_year AS
SELECT
    pc.cpc_code,
    pc.pub_year,
    COUNT(DISTINCT pc.patent_id) AS patent_count
FROM patent_schema.patent_cpc pc
GROUP BY pc.cpc_code, pc.pub_year
WITH DATA;

CREATE UNIQUE INDEX idx_mv_pccy ON cross_schema.mv_patent_counts_by_cpc_year (cpc_code, pub_year);

COMMENT ON MATERIALIZED VIEW cross_schema.mv_patent_counts_by_cpc_year IS
    'Pre-aggregated patent counts per CPC code per year. Refresh after import.';


-- --------------------------------------------------------------------------
-- MV2: CPC co-occurrence pairs (top 200 codes) with shared patent counts
-- Used by: UC5 (CPC Jaccard similarity)
-- --------------------------------------------------------------------------
-- Replaces the per-request self-join on 237M rows in SQLite.
-- Only stores pairs for top-200 CPC codes (by total patent count) to keep
-- the view manageable. For less common codes, fall back to live query.

CREATE MATERIALIZED VIEW cross_schema.mv_cpc_cooccurrence AS
WITH top_codes AS (
    SELECT cpc_code
    FROM patent_schema.patent_cpc
    GROUP BY cpc_code
    ORDER BY COUNT(DISTINCT patent_id) DESC
    LIMIT 200
)
SELECT
    a.cpc_code AS code_a,
    b.cpc_code AS code_b,
    a.pub_year,
    COUNT(DISTINCT a.patent_id) AS co_count
FROM patent_schema.patent_cpc a
JOIN patent_schema.patent_cpc b
    ON a.patent_id = b.patent_id
    AND a.pub_year = b.pub_year
    AND a.cpc_code < b.cpc_code
WHERE a.cpc_code IN (SELECT cpc_code FROM top_codes)
  AND b.cpc_code IN (SELECT cpc_code FROM top_codes)
GROUP BY a.cpc_code, b.cpc_code, a.pub_year
WITH DATA;

CREATE UNIQUE INDEX idx_mv_cooc ON cross_schema.mv_cpc_cooccurrence (code_a, code_b, pub_year);
CREATE INDEX idx_mv_cooc_a ON cross_schema.mv_cpc_cooccurrence (code_a);
CREATE INDEX idx_mv_cooc_b ON cross_schema.mv_cpc_cooccurrence (code_b);

COMMENT ON MATERIALIZED VIEW cross_schema.mv_cpc_cooccurrence IS
    'CPC co-occurrence pairs for top-200 codes by year. '
    'Replaces per-request self-join on 237M-row patent_cpc. Key table for UC5 Jaccard.';


-- --------------------------------------------------------------------------
-- MV3: Yearly patent + project counts per technology (top CPC codes)
-- Used by: UC1 (landscape time series)
-- --------------------------------------------------------------------------

CREATE MATERIALIZED VIEW cross_schema.mv_yearly_tech_counts AS
SELECT
    pc.cpc_code          AS technology,
    pc.pub_year          AS year,
    COUNT(DISTINCT pc.patent_id)  AS patent_count,
    NULL::INTEGER        AS project_count,
    'patent'::TEXT       AS source
FROM patent_schema.patent_cpc pc
GROUP BY pc.cpc_code, pc.pub_year
WITH DATA;

CREATE UNIQUE INDEX idx_mv_ytc ON cross_schema.mv_yearly_tech_counts (technology, year, source);

COMMENT ON MATERIALIZED VIEW cross_schema.mv_yearly_tech_counts IS
    'Patent counts per CPC code per year. Basis for UC1 landscape time series.';


-- --------------------------------------------------------------------------
-- MV4: Top patent applicants with counts
-- Used by: UC3 (competitive intelligence), UC8 (temporal actor dynamics)
-- --------------------------------------------------------------------------

CREATE MATERIALIZED VIEW cross_schema.mv_top_applicants AS
SELECT
    a.normalized_name,
    a.id AS applicant_id,
    COUNT(DISTINCT pa.patent_id) AS patent_count,
    MIN(p.publication_year) AS first_year,
    MAX(p.publication_year) AS last_year
FROM patent_schema.applicants a
JOIN patent_schema.patent_applicants pa ON pa.applicant_id = a.id
JOIN patent_schema.patents p ON p.id = pa.patent_id AND p.publication_year = pa.patent_year
GROUP BY a.id, a.normalized_name
HAVING COUNT(DISTINCT pa.patent_id) >= 10          -- only actors with meaningful activity
WITH DATA;

CREATE UNIQUE INDEX idx_mv_ta ON cross_schema.mv_top_applicants (applicant_id);
CREATE INDEX idx_mv_ta_count ON cross_schema.mv_top_applicants (patent_count DESC);
CREATE INDEX idx_mv_ta_name_trgm ON cross_schema.mv_top_applicants
    USING gin (normalized_name gin_trgm_ops);

COMMENT ON MATERIALIZED VIEW cross_schema.mv_top_applicants IS
    'Top patent applicants with >= 10 patents. Used by UC3 competitive + UC8 temporal dynamics.';


-- --------------------------------------------------------------------------
-- MV5: Country distribution (patent applicant countries)
-- Used by: UC6 (geographic analysis)
-- --------------------------------------------------------------------------

CREATE MATERIALIZED VIEW cross_schema.mv_patent_country_distribution AS
SELECT
    country_code,
    p.publication_year AS year,
    COUNT(*) AS patent_count
FROM patent_schema.patents p,
     LATERAL unnest(p.applicant_countries) AS country_code
WHERE p.applicant_countries IS NOT NULL
  AND array_length(p.applicant_countries, 1) > 0
GROUP BY country_code, p.publication_year
WITH DATA;

CREATE UNIQUE INDEX idx_mv_pcd ON cross_schema.mv_patent_country_distribution (country_code, year);

COMMENT ON MATERIALIZED VIEW cross_schema.mv_patent_country_distribution IS
    'Patent counts by applicant country by year. Replaces per-request CSV text splitting.';


-- --------------------------------------------------------------------------
-- MV6: CORDIS project counts by year and framework
-- Used by: UC1 (landscape), UC4 (funding)
-- --------------------------------------------------------------------------

CREATE MATERIALIZED VIEW cross_schema.mv_project_counts_by_year AS
SELECT
    EXTRACT(YEAR FROM p.start_date)::SMALLINT AS year,
    p.framework,
    COUNT(*) AS project_count,
    SUM(p.ec_max_contribution) AS total_ec_funding,
    AVG(p.ec_max_contribution) AS avg_ec_funding
FROM cordis_schema.projects p
WHERE p.start_date IS NOT NULL
GROUP BY EXTRACT(YEAR FROM p.start_date)::SMALLINT, p.framework
WITH DATA;

CREATE UNIQUE INDEX idx_mv_pcby ON cross_schema.mv_project_counts_by_year (year, framework);

COMMENT ON MATERIALIZED VIEW cross_schema.mv_project_counts_by_year IS
    'CORDIS project counts and funding by year and framework programme. Used by UC1 + UC4.';


-- --------------------------------------------------------------------------
-- MV7: CORDIS country collaboration pairs
-- Used by: UC6 (geographic analysis)
-- --------------------------------------------------------------------------

CREATE MATERIALIZED VIEW cross_schema.mv_cordis_country_pairs AS
SELECT
    o1.country AS country_a,
    o2.country AS country_b,
    EXTRACT(YEAR FROM p.start_date)::SMALLINT AS year,
    COUNT(DISTINCT p.id) AS project_count
FROM cordis_schema.projects p
JOIN cordis_schema.organizations o1 ON o1.project_id = p.id
JOIN cordis_schema.organizations o2 ON o2.project_id = p.id
    AND o2.country > o1.country
WHERE o1.country IS NOT NULL
  AND o2.country IS NOT NULL
  AND p.start_date IS NOT NULL
GROUP BY o1.country, o2.country, EXTRACT(YEAR FROM p.start_date)::SMALLINT
WITH DATA;

CREATE UNIQUE INDEX idx_mv_ccp ON cross_schema.mv_cordis_country_pairs (country_a, country_b, year);

COMMENT ON MATERIALIZED VIEW cross_schema.mv_cordis_country_pairs IS
    'CORDIS country collaboration pairs by year. Used by UC6 geographic analysis.';


-- --------------------------------------------------------------------------
-- MV8: Top CORDIS organizations with metadata
-- Used by: UC3 (competitive), UC4 (funding), UC8 (temporal)
-- --------------------------------------------------------------------------

CREATE MATERIALIZED VIEW cross_schema.mv_top_cordis_orgs AS
SELECT
    o.name,
    o.country,
    o.activity_type,
    COUNT(DISTINCT o.project_id) AS project_count,
    SUM(o.ec_contribution) AS total_ec_contribution,
    bool_or(o.sme) AS is_sme,
    bool_or(o.role = 'coordinator') AS is_coordinator,
    MIN(EXTRACT(YEAR FROM p.start_date))::SMALLINT AS first_year,
    MAX(EXTRACT(YEAR FROM p.start_date))::SMALLINT AS last_year
FROM cordis_schema.organizations o
JOIN cordis_schema.projects p ON p.id = o.project_id
WHERE o.name IS NOT NULL
  AND p.start_date IS NOT NULL
GROUP BY o.name, o.country, o.activity_type
HAVING COUNT(DISTINCT o.project_id) >= 3
WITH DATA;

CREATE UNIQUE INDEX idx_mv_tco ON cross_schema.mv_top_cordis_orgs (name, country, activity_type);
CREATE INDEX idx_mv_tco_count ON cross_schema.mv_top_cordis_orgs (project_count DESC);
CREATE INDEX idx_mv_tco_name_trgm ON cross_schema.mv_top_cordis_orgs
    USING gin (name gin_trgm_ops);

COMMENT ON MATERIALIZED VIEW cross_schema.mv_top_cordis_orgs IS
    'Top CORDIS organizations with >= 3 projects. Includes funding, SME/coordinator flags, active years.';


-- --------------------------------------------------------------------------
-- MV9: Funding by instrument type and year
-- Used by: UC4 (funding radar instrument breakdown)
-- --------------------------------------------------------------------------

CREATE MATERIALIZED VIEW cross_schema.mv_funding_by_instrument AS
SELECT
    p.funding_scheme,
    EXTRACT(YEAR FROM p.start_date)::SMALLINT AS year,
    COUNT(*) AS project_count,
    SUM(COALESCE(p.ec_max_contribution, 0)) AS total_funding,
    AVG(COALESCE(p.ec_max_contribution, 0)) AS avg_funding
FROM cordis_schema.projects p
WHERE p.funding_scheme IS NOT NULL
  AND p.funding_scheme != ''
  AND p.start_date IS NOT NULL
GROUP BY p.funding_scheme, EXTRACT(YEAR FROM p.start_date)::SMALLINT
WITH DATA;

CREATE UNIQUE INDEX idx_mv_fbi ON cross_schema.mv_funding_by_instrument (funding_scheme, year);

COMMENT ON MATERIALIZED VIEW cross_schema.mv_funding_by_instrument IS
    'Funding by instrument type (RIA, IA, CSA, ERC) per year. Used by UC4 instrument breakdown.';


-- ============================================================================
-- ============================================================================
-- EXPORT_SCHEMA: Export service cache and report templates
-- ============================================================================
-- ============================================================================

-- --------------------------------------------------------------------------
-- Cached analysis results (keyed by technology + time range + UC)
-- --------------------------------------------------------------------------

-- Kanonische Definition — identisch zu services/export-svc/src/db_schema.py.
-- Ein Row = ein kompletter Radar-Request (use_cases als Array), keyed per cache_key.
CREATE TABLE export_schema.analysis_cache (
    id              BIGSERIAL PRIMARY KEY,
    cache_key       TEXT UNIQUE NOT NULL,            -- SHA-256 hash of request key
    technology      TEXT NOT NULL,
    start_year      INTEGER NOT NULL,
    end_year        INTEGER NOT NULL,
    european_only   BOOLEAN NOT NULL DEFAULT FALSE,
    use_cases       TEXT[] NOT NULL DEFAULT '{}',    -- which UCs are in this cached response
    result_json     JSONB NOT NULL,                  -- full RadarResponse as JSONB
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL             -- application sets TTL (default 24h)
);

CREATE INDEX idx_cache_key ON export_schema.analysis_cache (cache_key);
CREATE INDEX idx_cache_expires ON export_schema.analysis_cache (expires_at);

COMMENT ON TABLE export_schema.analysis_cache IS
    'Gecachte Radar-Responses (ein Row = ein kompletter Request mit use_cases-Array). '
    'TTL via expires_at (default 24h applikativ). Lookup per cache_key.';


-- --------------------------------------------------------------------------
-- Report templates (for structured export)
-- --------------------------------------------------------------------------

CREATE TABLE export_schema.report_templates (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                VARCHAR(100) NOT NULL UNIQUE,
    description         TEXT,
    format              VARCHAR(10) NOT NULL,        -- 'csv', 'pdf', 'xlsx', 'json'
    template_config     JSONB NOT NULL,              -- column definitions, formatting rules
    use_cases           TEXT[] NOT NULL,              -- which UCs this template covers
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ck_report_format CHECK (
        format IN ('csv', 'pdf', 'xlsx', 'json')
    )
);

COMMENT ON TABLE export_schema.report_templates IS
    'Reusable export templates. template_config contains column definitions and formatting rules.';


-- --------------------------------------------------------------------------
-- Export history / audit log
-- --------------------------------------------------------------------------

-- Kanonische Definition — identisch zu services/export-svc/src/db_schema.py.
CREATE TABLE export_schema.export_log (
    id              BIGSERIAL PRIMARY KEY,
    technology      TEXT NOT NULL,
    export_format   TEXT NOT NULL,                 -- 'csv', 'pdf', 'xlsx', 'json'
    use_cases       TEXT[] NOT NULL DEFAULT '{}',
    row_count       INTEGER NOT NULL DEFAULT 0,
    file_size_bytes BIGINT NOT NULL DEFAULT 0,
    duration_ms     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    client_ip       TEXT DEFAULT '',
    request_id      TEXT DEFAULT ''                -- correlation with gRPC request_id
);

CREATE INDEX idx_el_technology ON export_schema.export_log (technology);
CREATE INDEX idx_el_created ON export_schema.export_log (created_at);

COMMENT ON TABLE export_schema.export_log IS
    'Audit-Trail aller Export-Operationen (PDF/CSV/XLSX/JSON). '
    'Trackt technology, Format, Use-Cases, Größe und Dauer. Kein Datenbezug.';


-- ============================================================================
-- ============================================================================
-- HELPER FUNCTIONS (public schema)
-- ============================================================================
-- ============================================================================

-- Platform-standard tsquery: unaccent + english stemming
-- Replaces SQLite FTS5 phrase wrapping
CREATE OR REPLACE FUNCTION public.ti_plainto_tsquery(query TEXT)
RETURNS tsquery AS $$
BEGIN
    RETURN plainto_tsquery('english', unaccent(query));
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT;

COMMENT ON FUNCTION public.ti_plainto_tsquery IS
    'Platform-standard tsquery builder: unaccent + english stemming. '
    'Replaces SQLite FTS5 MATCH. Use for programmatic queries.';

-- Websearch-style query (supports "quoted phrases" and OR)
CREATE OR REPLACE FUNCTION public.ti_websearch_tsquery(query TEXT)
RETURNS tsquery AS $$
BEGIN
    RETURN websearch_to_tsquery('english', unaccent(query));
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT;

COMMENT ON FUNCTION public.ti_websearch_tsquery IS
    'Websearch-style tsquery: supports "quoted phrases", OR, and - negation. '
    'Use for user-facing search inputs.';

-- Fuzzy match score using pg_trgm similarity
CREATE OR REPLACE FUNCTION public.ti_fuzzy_score(a TEXT, b TEXT)
RETURNS REAL AS $$
BEGIN
    RETURN similarity(unaccent(upper(a)), unaccent(upper(b)));
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT;

COMMENT ON FUNCTION public.ti_fuzzy_score IS
    'Trigram similarity score (0.0-1.0) between two strings. '
    'Case-insensitive, accent-insensitive. For entity resolution.';


-- ============================================================================
-- ADDITIONAL TABLES (created by services/migrations on source system)
-- ============================================================================

-- Alembic migration version tracking
CREATE TABLE IF NOT EXISTS public.alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);

-- Patent embedding enrichment progress tracking
CREATE TABLE IF NOT EXISTS patent_schema.enrichment_progress (
    zip_name            TEXT PRIMARY KEY,
    updated_count       INTEGER NOT NULL DEFAULT 0,
    completed_at        TIMESTAMPTZ
);

-- RAG document chunks with embeddings for semantic search
CREATE TABLE IF NOT EXISTS cross_schema.document_chunks (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source              TEXT NOT NULL,
    source_id           TEXT NOT NULL,
    chunk_index         INTEGER NOT NULL,
    chunk_text          TEXT NOT NULL,
    embedding           vector(384)
);

CREATE INDEX IF NOT EXISTS idx_dc_source ON cross_schema.document_chunks (source, source_id);

-- ETL sync checkpoints per data source
CREATE TABLE IF NOT EXISTS cross_schema.etl_checkpoints (
    source              TEXT PRIMARY KEY,
    last_sync_at        TIMESTAMPTZ,
    last_sync_cursor    TEXT,
    records_synced      INTEGER DEFAULT 0,
    total_records_ever  BIGINT DEFAULT 0,
    status              VARCHAR(20),
    error_message       TEXT,
    run_duration_s      REAL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ETL run history log
CREATE TABLE IF NOT EXISTS cross_schema.etl_run_log (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source              TEXT NOT NULL,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at         TIMESTAMPTZ,
    status              VARCHAR(20) NOT NULL DEFAULT 'running',
    records_fetched     INTEGER DEFAULT 0,
    records_inserted    INTEGER DEFAULT 0,
    records_updated     INTEGER DEFAULT 0,
    records_skipped     INTEGER DEFAULT 0,
    error_message       TEXT,
    cursor_before       TEXT,
    cursor_after        TEXT,
    mv_refresh_duration_s REAL
);

CREATE INDEX IF NOT EXISTS idx_erl_source ON cross_schema.etl_run_log (source, started_at DESC);


-- --------------------------------------------------------------------------
-- Import Log (file-level tracking for incremental imports)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cross_schema.import_log (
    id                  SERIAL PRIMARY KEY,
    source              TEXT NOT NULL,
    filename            TEXT NOT NULL,
    imported_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    record_count        INTEGER NOT NULL DEFAULT 0,
    duration_seconds    REAL,
    status              TEXT NOT NULL DEFAULT 'completed',

    CONSTRAINT uq_import_log_source_file UNIQUE (source, filename),
    CONSTRAINT ck_import_log_status CHECK (status IN ('completed', 'failed', 'skipped')),
    CONSTRAINT ck_import_log_source CHECK (source IN ('epo', 'cordis', 'euroscivoc'))
);

COMMENT ON TABLE cross_schema.import_log IS
    'Import tracking for incremental imports. Prevents re-importing already processed files.';

CREATE INDEX IF NOT EXISTS idx_import_log_source
    ON cross_schema.import_log (source);
CREATE INDEX IF NOT EXISTS idx_import_log_imported_at
    ON cross_schema.import_log (imported_at DESC);


-- OpenAIRE publications cache
CREATE TABLE IF NOT EXISTS research_schema.openaire_publications (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    openaire_id         TEXT UNIQUE,
    title               TEXT,
    authors             TEXT,
    doi                 TEXT,
    year                SMALLINT,
    date_of_acceptance  DATE,
    publisher           TEXT,
    journal             TEXT,
    is_open_access      BOOLEAN,
    subjects            TEXT[],
    query_technology    TEXT,
    fetched_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_oap_tech ON research_schema.openaire_publications (query_technology);
CREATE INDEX IF NOT EXISTS idx_oap_year ON research_schema.openaire_publications (year);


-- ============================================================================
-- REFRESH FUNCTION: call after each data import
-- ============================================================================

CREATE OR REPLACE FUNCTION cross_schema.refresh_all_views()
RETURNS void AS $$
BEGIN
    RAISE NOTICE 'Refreshing cross_schema materialized views...';
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_patent_counts_by_cpc_year;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_cpc_cooccurrence;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_yearly_tech_counts;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_top_applicants;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_patent_country_distribution;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_project_counts_by_year;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_cordis_country_pairs;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_top_cordis_orgs;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_funding_by_instrument;
    RAISE NOTICE 'All materialized views refreshed.';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cross_schema.refresh_all_views IS
    'Refresh all 9 materialized views concurrently (non-blocking). '
    'Call after each EPO or CORDIS data import.';


-- Selective refresh: patent-only views (faster, for EPO-only imports)
CREATE OR REPLACE FUNCTION cross_schema.refresh_patent_views()
RETURNS void AS $$
BEGIN
    RAISE NOTICE 'Refreshing patent-related materialized views...';
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_patent_counts_by_cpc_year;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_cpc_cooccurrence;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_yearly_tech_counts;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_top_applicants;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_patent_country_distribution;
    RAISE NOTICE 'Patent views refreshed.';
END;
$$ LANGUAGE plpgsql;

-- Selective refresh: CORDIS-only views
CREATE OR REPLACE FUNCTION cross_schema.refresh_cordis_views()
RETURNS void AS $$
BEGIN
    RAISE NOTICE 'Refreshing CORDIS-related materialized views...';
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_project_counts_by_year;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_cordis_country_pairs;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_top_cordis_orgs;
    REFRESH MATERIALIZED VIEW CONCURRENTLY cross_schema.mv_funding_by_instrument;
    RAISE NOTICE 'CORDIS views refreshed.';
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- ============================================================================
-- CACHE MAINTENANCE FUNCTIONS
-- ============================================================================
-- ============================================================================

-- Purge expired analysis cache entries
CREATE OR REPLACE FUNCTION export_schema.purge_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM export_schema.analysis_cache
    WHERE expires_at < now();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Purge stale Semantic Scholar cache
CREATE OR REPLACE FUNCTION research_schema.purge_stale_papers()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM research_schema.papers
    WHERE stale_after < now();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    DELETE FROM research_schema.query_cache
    WHERE stale_after < now();
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Purge expired GLEIF cache (>90 days)
CREATE OR REPLACE FUNCTION entity_schema.purge_stale_gleif()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM entity_schema.gleif_cache
    WHERE resolved_at < (now() - INTERVAL '90 days');
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- ============================================================================
-- SERVICE ROLES AND PERMISSIONS
-- ============================================================================
-- ============================================================================
-- Each microservice gets a dedicated role with minimal privileges.
-- Pattern: svc_<service_name> with READ-ONLY on own schema + source schemas.
-- Data import roles get INSERT/UPDATE on their target schemas.

-- --------------------------------------------------------------------------
-- Application roles (CREATE ROLE is idempotent with IF NOT EXISTS)
-- --------------------------------------------------------------------------

DO $$
BEGIN
    -- Service roles (read-only query access)
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_landscape') THEN
        CREATE ROLE svc_landscape LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_maturity') THEN
        CREATE ROLE svc_maturity LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_competitive') THEN
        CREATE ROLE svc_competitive LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_funding') THEN
        CREATE ROLE svc_funding LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_cpc_flow') THEN
        CREATE ROLE svc_cpc_flow LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_geographic') THEN
        CREATE ROLE svc_geographic LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_research_impact') THEN
        CREATE ROLE svc_research_impact LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_temporal') THEN
        CREATE ROLE svc_temporal LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_tech_cluster') THEN
        CREATE ROLE svc_tech_cluster LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_actor_type') THEN
        CREATE ROLE svc_actor_type LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_patent_grant') THEN
        CREATE ROLE svc_patent_grant LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_euroscivoc') THEN
        CREATE ROLE svc_euroscivoc LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_publication') THEN
        CREATE ROLE svc_publication LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_export') THEN
        CREATE ROLE svc_export LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_entity_resolution') THEN
        CREATE ROLE svc_entity_resolution LOGIN;
    END IF;

    -- Data import roles (write access)
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'importer_epo') THEN
        CREATE ROLE importer_epo LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'importer_cordis') THEN
        CREATE ROLE importer_cordis LOGIN;
    END IF;

    -- Admin role (full access for maintenance)
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tip_admin') THEN
        CREATE ROLE tip_admin LOGIN;
    END IF;

    -- Read-only role for analytics/reporting (all schemas)
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tip_readonly') THEN
        CREATE ROLE tip_readonly LOGIN;
    END IF;
END $$;


-- --------------------------------------------------------------------------
-- Role passwords (env-basiert, Defaults fuer Development)
-- --------------------------------------------------------------------------
ALTER ROLE svc_landscape PASSWORD 'svc_landscape_pw';
ALTER ROLE svc_maturity PASSWORD 'svc_maturity_pw';
ALTER ROLE svc_competitive PASSWORD 'svc_competitive_pw';
ALTER ROLE svc_funding PASSWORD 'svc_funding_pw';
ALTER ROLE svc_cpc_flow PASSWORD 'svc_cpc_flow_pw';
ALTER ROLE svc_geographic PASSWORD 'svc_geographic_pw';
ALTER ROLE svc_research_impact PASSWORD 'svc_research_impact_pw';
ALTER ROLE svc_temporal PASSWORD 'svc_temporal_pw';
ALTER ROLE svc_tech_cluster PASSWORD 'svc_tech_cluster_pw';
ALTER ROLE svc_actor_type PASSWORD 'svc_actor_type_pw';
ALTER ROLE svc_patent_grant PASSWORD 'svc_patent_grant_pw';
ALTER ROLE svc_euroscivoc PASSWORD 'svc_euroscivoc_pw';
ALTER ROLE svc_publication PASSWORD 'svc_publication_pw';
ALTER ROLE svc_export PASSWORD 'svc_export_pw';
ALTER ROLE svc_entity_resolution PASSWORD 'svc_entity_pw';
ALTER ROLE importer_epo PASSWORD 'importer_epo_pw';
ALTER ROLE importer_cordis PASSWORD 'importer_cordis_pw';


-- --------------------------------------------------------------------------
-- Schema USAGE grants (required before any table access)
-- --------------------------------------------------------------------------

-- All service roles need USAGE on the schemas they read from
GRANT USAGE ON SCHEMA patent_schema  TO svc_landscape, svc_maturity, svc_competitive,
    svc_cpc_flow, svc_geographic, svc_temporal, svc_tech_cluster, svc_actor_type,
    svc_patent_grant, svc_export, svc_entity_resolution,
    importer_epo, tip_admin, tip_readonly;

GRANT USAGE ON SCHEMA cordis_schema  TO svc_landscape, svc_competitive, svc_funding,
    svc_geographic, svc_research_impact, svc_temporal, svc_tech_cluster, svc_actor_type,
    svc_euroscivoc, svc_publication, svc_export, svc_entity_resolution,
    importer_cordis, tip_admin, tip_readonly;

GRANT USAGE ON SCHEMA cross_schema   TO svc_landscape, svc_maturity, svc_competitive,
    svc_funding, svc_cpc_flow, svc_geographic, svc_temporal, svc_tech_cluster,
    svc_actor_type, svc_patent_grant, svc_euroscivoc, svc_export,
    importer_epo, importer_cordis, tip_admin, tip_readonly;

GRANT USAGE ON SCHEMA research_schema TO svc_research_impact, svc_landscape, svc_export,
    tip_admin, tip_readonly;

GRANT USAGE ON SCHEMA entity_schema  TO svc_competitive, svc_geographic, svc_temporal,
    svc_actor_type, svc_entity_resolution, svc_export, tip_admin, tip_readonly;

GRANT USAGE ON SCHEMA export_schema  TO svc_export, svc_landscape, svc_maturity,
    svc_competitive, svc_funding, svc_cpc_flow, svc_geographic,
    svc_research_impact, svc_temporal, tip_admin, tip_readonly;


-- --------------------------------------------------------------------------
-- Table-level READ grants per service
-- --------------------------------------------------------------------------

-- UC1 Landscape: reads patents + projects + cross-schema MVs + research papers
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_landscape;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_landscape;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_landscape;
GRANT SELECT ON ALL TABLES IN SCHEMA research_schema TO svc_landscape;
GRANT INSERT, UPDATE, DELETE ON research_schema.openaire_cache TO svc_landscape;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA research_schema TO svc_landscape;

-- UC2 Maturity: reads patents + patent_cpc + cross-schema MVs
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_maturity;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_maturity;

-- UC3 Competitive: reads patents + CORDIS + entity + cross-schema MVs
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_competitive;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_competitive;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_competitive;
GRANT SELECT ON ALL TABLES IN SCHEMA entity_schema TO svc_competitive;

-- UC4 Funding: reads CORDIS + cross-schema MVs
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_funding;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_funding;

-- UC5 CPC Flow: reads patent_cpc + cross-schema MVs
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_cpc_flow;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_cpc_flow;

-- UC6 Geographic: reads patents + CORDIS + entity + cross-schema MVs
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_geographic;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_geographic;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_geographic;
GRANT SELECT ON ALL TABLES IN SCHEMA entity_schema TO svc_geographic;

-- UC7 Research Impact: reads + writes research_schema (cache management) + reads cordis_schema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA research_schema TO svc_research_impact;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA research_schema TO svc_research_impact;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_research_impact;

-- UC9 Tech Cluster: reads patents + CORDIS + cross-schema MVs
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_tech_cluster;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_tech_cluster;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_tech_cluster;

-- UC10 EuroSciVoc: reads CORDIS + cross-schema MVs
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_euroscivoc;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_euroscivoc;

-- UC12 Patent Grant: reads patents + cross-schema MVs
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_patent_grant;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_patent_grant;

-- UC8 Temporal: reads patents + CORDIS + cross-schema MVs
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_temporal;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_temporal;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_temporal;

-- UC11 Actor Type: reads CORDIS + patents + cross-schema + entity (GLEIF cache write)
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_actor_type;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_actor_type;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_actor_type;
GRANT SELECT ON ALL TABLES IN SCHEMA entity_schema TO svc_actor_type;
GRANT INSERT, UPDATE ON entity_schema.gleif_cache TO svc_actor_type;

-- Export service: reads everything, writes to export_schema
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_export;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_export;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_export;
GRANT SELECT ON ALL TABLES IN SCHEMA research_schema TO svc_export;
GRANT SELECT ON ALL TABLES IN SCHEMA entity_schema TO svc_export;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA export_schema TO svc_export;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA export_schema TO svc_export;
-- svc_export legt beim Startup fehlende Tabellen/Indizes idempotent an:
GRANT CREATE ON SCHEMA export_schema TO svc_export;
ALTER DEFAULT PRIVILEGES IN SCHEMA export_schema
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO svc_export;
ALTER DEFAULT PRIVILEGES IN SCHEMA export_schema
    GRANT USAGE ON SEQUENCES TO svc_export;

-- Entity resolution: reads patents + CORDIS, writes entity_schema
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_entity_resolution;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_entity_resolution;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA entity_schema TO svc_entity_resolution;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA entity_schema TO svc_entity_resolution;

-- UC-C Publication: reads cordis_schema
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_publication;
ALTER DEFAULT PRIVILEGES IN SCHEMA cordis_schema
    GRANT SELECT ON TABLES TO svc_publication;


-- --------------------------------------------------------------------------
-- Data import roles: write access to their target schemas
-- --------------------------------------------------------------------------

-- EPO importer: writes to patent_schema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA patent_schema TO importer_epo;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA patent_schema TO importer_epo;
GRANT EXECUTE ON FUNCTION cross_schema.refresh_patent_views() TO importer_epo;
GRANT SELECT, INSERT, UPDATE ON cross_schema.import_log TO importer_epo;
GRANT USAGE ON SEQUENCE cross_schema.import_log_id_seq TO importer_epo;

-- CORDIS importer: writes to cordis_schema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA cordis_schema TO importer_cordis;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA cordis_schema TO importer_cordis;
GRANT EXECUTE ON FUNCTION cross_schema.refresh_cordis_views() TO importer_cordis;
GRANT SELECT, INSERT, UPDATE ON cross_schema.import_log TO importer_cordis;
GRANT USAGE ON SEQUENCE cross_schema.import_log_id_seq TO importer_cordis;


-- --------------------------------------------------------------------------
-- Admin and read-only roles
-- --------------------------------------------------------------------------

-- Admin: full access everywhere
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA patent_schema TO tip_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cordis_schema TO tip_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cross_schema TO tip_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA research_schema TO tip_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA entity_schema TO tip_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA export_schema TO tip_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA patent_schema TO tip_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA cordis_schema TO tip_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA research_schema TO tip_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA entity_schema TO tip_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA export_schema TO tip_admin;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA cross_schema TO tip_admin;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA export_schema TO tip_admin;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA research_schema TO tip_admin;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA entity_schema TO tip_admin;

-- Read-only: SELECT on everything
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO tip_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO tip_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO tip_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA research_schema TO tip_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA entity_schema TO tip_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA export_schema TO tip_readonly;


-- --------------------------------------------------------------------------
-- Default privileges for future tables (auto-grant on new tables)
-- --------------------------------------------------------------------------

ALTER DEFAULT PRIVILEGES IN SCHEMA patent_schema  GRANT SELECT ON TABLES TO tip_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA cordis_schema  GRANT SELECT ON TABLES TO tip_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA cross_schema   GRANT SELECT ON TABLES TO tip_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA research_schema GRANT SELECT ON TABLES TO tip_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA entity_schema  GRANT SELECT ON TABLES TO tip_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA export_schema  GRANT SELECT ON TABLES TO tip_readonly;


-- ============================================================================
-- COMMIT TRANSACTION
-- ============================================================================
COMMIT;


-- ============================================================================
-- POST-TRANSACTION: informational output
-- ============================================================================

-- Summary of created objects (informational, not part of transaction)
DO $$
DECLARE
    schema_name TEXT;
    table_count INTEGER;
    index_count INTEGER;
BEGIN
    FOR schema_name IN
        SELECT unnest(ARRAY['patent_schema', 'cordis_schema', 'cross_schema',
                            'research_schema', 'entity_schema', 'export_schema'])
    LOOP
        SELECT COUNT(*) INTO table_count
        FROM information_schema.tables
        WHERE table_schema = schema_name AND table_type IN ('BASE TABLE', 'VIEW');

        SELECT COUNT(*) INTO index_count
        FROM pg_indexes
        WHERE schemaname = schema_name;

        RAISE NOTICE 'Schema %-20s: % tables/views, % indexes', schema_name, table_count, index_count;
    END LOOP;
END $$;
