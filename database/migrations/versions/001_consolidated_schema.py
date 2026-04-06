"""Consolidated initial schema: Complete TI-Radar database.

Revision ID: 001_consolidated
Revises: None
Create Date: 2026-04-06

Squash of: 001_initial, 002_add_filing_date, 003_api_cache_tables
Includes: patent_citations (006), import_log (005), svc_publication (007),
          openaire_cache (009), epo_ops_cache + cordis_api_cache (003)

This migration reads and executes the consolidated SQL files rather than
using SQLAlchemy ORM, because the schema uses PostgreSQL-specific features
(partitioning, tsvector triggers, pgvector) that are more naturally
expressed in raw SQL.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "001_consolidated"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"


def _execute_sql_file(filename: str) -> None:
    """Read and execute a SQL file."""
    sql_path = _SQL_DIR / filename
    sql_content = sql_path.read_text(encoding="utf-8")
    for statement in sql_content.split(";"):
        stripped = statement.strip()
        if stripped and not stripped.startswith("--"):
            op.execute(stripped + ";")


def upgrade() -> None:
    _execute_sql_file("001_extensions.sql")
    _execute_sql_file("002_schema.sql")


def downgrade() -> None:
    for schema in [
        "export_schema",
        "entity_schema",
        "research_schema",
        "cross_schema",
        "cordis_schema",
        "patent_schema",
    ]:
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS public.ti_plainto_tsquery CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS public.ti_websearch_tsquery CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS public.ti_fuzzy_score CASCADE;")
