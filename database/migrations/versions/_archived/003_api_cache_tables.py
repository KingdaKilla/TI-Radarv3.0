"""Add API cache tables for EPO OPS and CORDIS live adapters.

Revision ID: 003_api_cache_tables
Revises: 002_add_filing_date
Create Date: 2026-04-05

These tables cache query-level results from the EPO OPS and CORDIS REST APIs.
Patent/project data is upserted into the existing patent_schema.patents and
cordis_schema.projects tables (ON CONFLICT DO UPDATE — API data overwrites bulk).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "003_api_cache_tables"
down_revision: Union[str, None] = "002_add_filing_date"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # EPO OPS query-level cache
    op.execute("""
        CREATE TABLE IF NOT EXISTS patent_schema.epo_ops_cache (
            technology   TEXT        NOT NULL,
            start_year   SMALLINT,
            end_year     SMALLINT,
            result_json  JSONB       NOT NULL DEFAULT '[]',
            fetched_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            stale_after  TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '7 days',
            CONSTRAINT pk_epo_ops_cache PRIMARY KEY (technology, start_year, end_year)
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_epo_ops_cache_stale
        ON patent_schema.epo_ops_cache (stale_after);
    """)

    # CORDIS query-level cache
    op.execute("""
        CREATE TABLE IF NOT EXISTS cordis_schema.cordis_api_cache (
            technology   TEXT        PRIMARY KEY,
            result_json  JSONB       NOT NULL DEFAULT '[]',
            fetched_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            stale_after  TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '7 days'
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cordis_api_cache_stale
        ON cordis_schema.cordis_api_cache (stale_after);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS patent_schema.epo_ops_cache;")
    op.execute("DROP TABLE IF EXISTS cordis_schema.cordis_api_cache;")
