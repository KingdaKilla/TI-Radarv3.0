-- ============================================================================
-- 007_publication_role.sql
-- Database role for UC-C Publication Analytics Service
-- ============================================================================
-- The publication service queries cordis_schema.publications joined with
-- cordis_schema.projects. It needs read-only access to cordis_schema.
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'svc_publication') THEN
        CREATE ROLE svc_publication LOGIN;
    END IF;
END $$;

ALTER ROLE svc_publication PASSWORD 'svc_publication_pw';

-- Schema USAGE
GRANT USAGE ON SCHEMA cordis_schema TO svc_publication;

-- Read-only access to all tables in cordis_schema
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_publication;

-- Also grant on future tables in cordis_schema
ALTER DEFAULT PRIVILEGES IN SCHEMA cordis_schema
    GRANT SELECT ON TABLES TO svc_publication;
