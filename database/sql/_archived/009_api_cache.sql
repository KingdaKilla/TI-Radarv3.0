-- ============================================================================
-- 009_api_cache.sql
-- Database cache table for OpenAIRE API responses (UC1 Landscape Service)
-- ============================================================================
-- The landscape service fetches publication counts per year from the OpenAIRE
-- Search API. To avoid redundant API calls and to provide graceful degradation
-- when the API is unavailable, results are cached in this table with a
-- configurable staleness window (default 7 days).
-- ============================================================================

CREATE TABLE IF NOT EXISTS research_schema.openaire_cache (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    query_key       TEXT NOT NULL,           -- technology keyword (normalized: lowercase, stripped)
    year            INT NOT NULL,
    count           INT NOT NULL,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    stale_after     TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '7 days'),
    CONSTRAINT uq_openaire_cache UNIQUE (query_key, year)
);

COMMENT ON TABLE research_schema.openaire_cache IS
    'Cache for OpenAIRE publication count API responses. '
    'Each row stores the publication count for a (keyword, year) pair. '
    'Rows with stale_after < now() are considered stale but may still be '
    'returned as fallback when the API is unreachable.';

-- Index for fast staleness checks
CREATE INDEX IF NOT EXISTS idx_openaire_cache_stale
    ON research_schema.openaire_cache (query_key, stale_after);

-- Grant svc_landscape write access to the cache table
GRANT SELECT, INSERT, UPDATE, DELETE
    ON research_schema.openaire_cache TO svc_landscape;

GRANT USAGE ON ALL SEQUENCES IN SCHEMA research_schema TO svc_landscape;
