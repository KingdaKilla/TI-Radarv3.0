"""Initial schema: EPO patents, CORDIS projects, GLEIF cache, entity resolution.

Revision ID: 001_initial
Revises: None
Create Date: 2026-02-19

This migration creates the complete TI Platform database schema.
It reads and executes the SQL files in db/sql/ rather than using
SQLAlchemy ORM operations, because the schema uses PostgreSQL-specific
features (partitioning, tsvector triggers, pgvector) that are more
naturally expressed in raw SQL.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Resolve SQL file paths relative to this migration file
_SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"


def _execute_sql_file(filename: str) -> None:
    """Read and execute a SQL file."""
    sql_path = _SQL_DIR / filename
    sql_content = sql_path.read_text(encoding="utf-8")
    # Split on semicolons but skip empty statements
    for statement in sql_content.split(";"):
        stripped = statement.strip()
        if stripped and not stripped.startswith("--"):
            op.execute(stripped + ";")


def upgrade() -> None:
    # Step 1: Extensions (requires superuser -- may already exist)
    _execute_sql_file("001_extensions.sql")

    # Step 2: Full schema
    _execute_sql_file("002_schema.sql")


def downgrade() -> None:
    # Drop everything in reverse dependency order
    op.execute("DROP SCHEMA IF EXISTS analytics CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS entity CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS gleif CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS cordis CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS epo CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS public.ti_plainto_tsquery CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS public.ti_websearch_tsquery CASCADE;")
