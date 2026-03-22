-- ============================================================================
-- 001_extensions.sql
-- PostgreSQL 17 Extensions for Technology Intelligence Platform
-- ============================================================================
-- Run once per database as superuser before deploying the schema.
-- These cannot live inside Alembic migrations because they require
-- superuser privileges on most managed PostgreSQL providers.
-- ============================================================================

-- Full-text search trigram support (autocomplete, fuzzy matching)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Vector similarity search (future LLM embedding columns)
CREATE EXTENSION IF NOT EXISTS vector;

-- Universally unique identifiers for entity resolution
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Unaccented text comparisons (European names: Muller = Mueller)
CREATE EXTENSION IF NOT EXISTS unaccent;
