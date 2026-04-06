-- ============================================================================
-- 005_import_log.sql
-- Import-Tracking fuer inkrementelle Imports (EPO, CORDIS, EuroSciVoc)
-- ============================================================================
--
-- Ermoeglicht das Ueberspringen bereits importierter Dateien bei erneutem
-- Import-Lauf. Jeder erfolgreich abgeschlossene Import wird mit Dateiname,
-- Quelle, Anzahl und Dauer protokolliert.
--
-- Depends on: 002_schema.sql (cross_schema muss existieren)
-- ============================================================================

BEGIN;

-- --------------------------------------------------------------------------
-- Import-Log Tabelle in cross_schema (quellenuebergreifend)
-- --------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS cross_schema.import_log (
    id                  SERIAL PRIMARY KEY,
    source              TEXT NOT NULL,               -- 'epo', 'cordis', 'euroscivoc'
    filename            TEXT NOT NULL,               -- ZIP-/CSV-Dateiname
    imported_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    record_count        INTEGER NOT NULL DEFAULT 0,
    duration_seconds    REAL,
    status              TEXT NOT NULL DEFAULT 'completed',  -- 'completed', 'failed', 'skipped'

    CONSTRAINT uq_import_log_source_file UNIQUE (source, filename),
    CONSTRAINT ck_import_log_status CHECK (
        status IN ('completed', 'failed', 'skipped')
    ),
    CONSTRAINT ck_import_log_source CHECK (
        source IN ('epo', 'cordis', 'euroscivoc')
    )
);

COMMENT ON TABLE cross_schema.import_log IS
    'Import-Tracking fuer inkrementelle Imports. Jede erfolgreich importierte '
    'Datei wird protokolliert, um bei erneutem Import-Lauf uebersprungen zu werden.';

COMMENT ON COLUMN cross_schema.import_log.source IS
    'Datenquelle: epo, cordis oder euroscivoc.';
COMMENT ON COLUMN cross_schema.import_log.filename IS
    'Dateiname der importierten Datei (ZIP oder CSV).';
COMMENT ON COLUMN cross_schema.import_log.record_count IS
    'Anzahl der importierten Datensaetze aus dieser Datei.';
COMMENT ON COLUMN cross_schema.import_log.duration_seconds IS
    'Import-Dauer fuer diese Datei in Sekunden.';
COMMENT ON COLUMN cross_schema.import_log.status IS
    'Import-Status: completed (erfolgreich), failed (fehlgeschlagen), skipped (uebersprungen).';


-- --------------------------------------------------------------------------
-- Indexes
-- --------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_import_log_source
    ON cross_schema.import_log (source);

CREATE INDEX IF NOT EXISTS idx_import_log_imported_at
    ON cross_schema.import_log (imported_at DESC);


-- --------------------------------------------------------------------------
-- Grants: Importer-Rollen brauchen INSERT/UPDATE/SELECT
-- --------------------------------------------------------------------------

GRANT SELECT, INSERT, UPDATE ON cross_schema.import_log TO importer_epo;
GRANT SELECT, INSERT, UPDATE ON cross_schema.import_log TO importer_cordis;
GRANT USAGE ON SEQUENCE cross_schema.import_log_id_seq TO importer_epo;
GRANT USAGE ON SEQUENCE cross_schema.import_log_id_seq TO importer_cordis;

-- Admin: voller Zugriff
GRANT ALL PRIVILEGES ON cross_schema.import_log TO tip_admin;
GRANT USAGE ON SEQUENCE cross_schema.import_log_id_seq TO tip_admin;

-- Read-only: nur SELECT
GRANT SELECT ON cross_schema.import_log TO tip_readonly;


COMMIT;
