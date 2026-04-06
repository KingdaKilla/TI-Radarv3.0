"""Add filing_date column to patent_schema.patents for UC12 time-to-grant.

Revision ID: 002_add_filing_date
Revises: 001_initial
Create Date: 2026-03-05

The filing_date (application date) is extracted from EPO DOCDB XML
<application-reference><document-id><date> elements. UC12 uses it to
compute avg_time_to_grant_months = AVG(publication_date - filing_date).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "002_add_filing_date"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE patent_schema.patents "
        "ADD COLUMN IF NOT EXISTS filing_date DATE;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_patents_filing_date "
        "ON patent_schema.patents (filing_date) WHERE filing_date IS NOT NULL;"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS patent_schema.idx_patents_filing_date;")
    op.execute("ALTER TABLE patent_schema.patents DROP COLUMN IF EXISTS filing_date;")
