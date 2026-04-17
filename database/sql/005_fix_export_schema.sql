-- ============================================================================
-- 005_fix_export_schema.sql
-- Fix: export_schema.analysis_cache + export_schema.export_log an Code angleichen
-- ============================================================================
-- Hintergrund:
--   Der Export-Service (router_export.py + db_schema.py) nutzt die Spalten
--   `cache_key`, `use_cases[]`, `export_format`, `client_ip`.
--   Die ursprüngliche DDL in 002_schema.sql (Stand vor diesem Fix) hatte
--   `request_hash`, `use_case VARCHAR(10)`, `format`, kein `client_ip`.
--   Das führte im DB-Log zu permanenten Fehlern wie
--     ERROR:  column "cache_key" does not exist
--     ERROR:  column "export_format" of relation "export_log" does not exist
--
-- Fix-Strategie:
--   Cache + Audit-Log sind ephemeral (24h TTL bzw. nur Historie der letzten
--   Exports). DROP + neue CREATE ist akzeptabel und sauberer als ALTER.
--   Ausführung als tip_admin, damit Ownership + DEFAULT-PRIVILEGES stimmen.
--
-- Ausführung (einmalig auf dem Server):
--   docker compose exec -T db psql -U tip_admin -d ti_radar \
--       < database/sql/005_fix_export_schema.sql
--   docker compose restart export-svc
-- ============================================================================

BEGIN;

-- 1) Alte Tabellen entfernen (kein Datenverlust: reiner Cache/Log).
DROP TABLE IF EXISTS export_schema.analysis_cache CASCADE;
DROP TABLE IF EXISTS export_schema.export_log     CASCADE;

-- 2) analysis_cache neu anlegen — identisch zu services/export-svc/src/db_schema.py
CREATE TABLE export_schema.analysis_cache (
    id              BIGSERIAL PRIMARY KEY,
    cache_key       TEXT UNIQUE NOT NULL,
    technology      TEXT NOT NULL,
    start_year      INTEGER NOT NULL,
    end_year        INTEGER NOT NULL,
    european_only   BOOLEAN NOT NULL DEFAULT FALSE,
    use_cases       TEXT[] NOT NULL DEFAULT '{}',
    result_json     JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_cache_key
    ON export_schema.analysis_cache (cache_key);

CREATE INDEX idx_cache_expires
    ON export_schema.analysis_cache (expires_at);

COMMENT ON TABLE export_schema.analysis_cache IS
    'Gecachte Radar-Responses (ein Row = ein kompletter Request mit use_cases-Array). '
    'TTL 24h via expires_at. Lookup per cache_key (SHA-256 hash des Request-Keys).';

-- 3) export_log neu anlegen — identisch zu services/export-svc/src/db_schema.py
CREATE TABLE export_schema.export_log (
    id              BIGSERIAL PRIMARY KEY,
    technology      TEXT NOT NULL,
    export_format   TEXT NOT NULL,
    use_cases       TEXT[] NOT NULL DEFAULT '{}',
    row_count       INTEGER NOT NULL DEFAULT 0,
    file_size_bytes BIGINT NOT NULL DEFAULT 0,
    duration_ms     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    client_ip       TEXT DEFAULT '',
    request_id      TEXT DEFAULT ''
);

CREATE INDEX idx_el_technology ON export_schema.export_log (technology);
CREATE INDEX idx_el_created    ON export_schema.export_log (created_at);

COMMENT ON TABLE export_schema.export_log IS
    'Audit-Trail aller Export-Operationen (PDF/CSV/XLSX/JSON). '
    'Trackt technology, Format, Use-Cases, Größe und Dauer. Kein Datenbezug.';

-- 4) Grants: tip_admin besitzt die Tabellen; svc_export erhält DML.
-- (DEFAULT PRIVILEGES aus 002_schema.sql greifen für neue Tabellen von
--  tip_admin nicht automatisch — deshalb explizit.)
GRANT SELECT, INSERT, UPDATE, DELETE ON export_schema.analysis_cache TO svc_export;
GRANT SELECT, INSERT, UPDATE, DELETE ON export_schema.export_log     TO svc_export;
GRANT USAGE, SELECT ON SEQUENCE export_schema.analysis_cache_id_seq TO svc_export;
GRANT USAGE, SELECT ON SEQUENCE export_schema.export_log_id_seq     TO svc_export;

-- Readonly-Role ebenfalls versorgen.
GRANT SELECT ON export_schema.analysis_cache TO tip_readonly;
GRANT SELECT ON export_schema.export_log     TO tip_readonly;

COMMIT;

-- Sanity-Check (zum manuellen Ausführen nach der Migration):
-- \d+ export_schema.analysis_cache
-- \d+ export_schema.export_log
