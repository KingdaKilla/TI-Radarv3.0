-- ============================================================================
-- 010_fix_vector_dims_and_missing_tables.sql
-- Fix vector dimensions (1536 → 384) and add missing tables
-- Run AFTER restoring the old dump (ti_radar_dump.backup) on the server
-- ============================================================================

-- ============================================================================
-- 1. Fix vector column dimensions (1536 → 384)
-- ============================================================================

ALTER TABLE patent_schema.patents
    ALTER COLUMN title_embedding TYPE vector(384);

ALTER TABLE cordis_schema.projects
    ALTER COLUMN content_embedding TYPE vector(384);

ALTER TABLE research_schema.papers
    ALTER COLUMN abstract_embedding TYPE vector(384);

ALTER TABLE entity_schema.unified_actors
    ALTER COLUMN name_embedding TYPE vector(384);


-- ============================================================================
-- 2. Add missing tables
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

CREATE INDEX IF NOT EXISTS idx_dc_source
    ON cross_schema.document_chunks (source, source_id);

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

CREATE INDEX IF NOT EXISTS idx_erl_source
    ON cross_schema.etl_run_log (source, started_at DESC);

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

CREATE INDEX IF NOT EXISTS idx_oap_tech
    ON research_schema.openaire_publications (query_technology);
CREATE INDEX IF NOT EXISTS idx_oap_year
    ON research_schema.openaire_publications (year);


-- ============================================================================
-- Done
-- ============================================================================
SELECT 'Fix applied successfully' AS status;
