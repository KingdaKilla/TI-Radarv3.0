"""PublicationRepository — PostgreSQL-Datenbankzugriff fuer UC-C.

Abfragen fuer Publikations-Impact-Chain aus cordis_schema.publications.
Verknuepft Publikationen mit Projekten ueber project_id.

Hinweis: publication_date ist bei vielen CORDIS-Publikationen NULL.
Daher wird p.start_date als primaerer Zeitfilter verwendet.
"""

from __future__ import annotations

from typing import Any

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


class PublicationRepository:
    """Async PostgreSQL-Zugriff fuer UC-C Publikations-Analysen."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def pub_count_by_year(
        self,
        technology: str,
        start_year: int,
        end_year: int,
    ) -> list[dict[str, Any]]:
        """Publikationen pro Projekt-Startjahr fuer passende Projekte zaehlen."""
        sql = """
            SELECT EXTRACT(YEAR FROM p.start_date)::int AS year,
                   COUNT(*) AS publication_count,
                   COUNT(DISTINCT pub.project_id) AS project_count
            FROM cordis_schema.publications pub
            JOIN cordis_schema.projects p ON pub.project_id = p.id
            WHERE p.search_vector @@ plainto_tsquery('english', $1)
              AND EXTRACT(YEAR FROM p.start_date) BETWEEN $2 AND $3
            GROUP BY year
            ORDER BY year
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, technology, start_year, end_year)
            return [dict(r) for r in rows]

    async def top_projects_by_pub_count(
        self,
        technology: str,
        start_year: int,
        end_year: int,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Projekte mit den meisten Publikationen, inkl. Foerderung."""
        sql = """
            SELECT p.acronym AS project_acronym,
                   p.framework,
                   COALESCE(p.ec_max_contribution, 0) AS ec_contribution_eur,
                   COUNT(pub.id) AS publication_count
            FROM cordis_schema.publications pub
            JOIN cordis_schema.projects p ON pub.project_id = p.id
            WHERE p.search_vector @@ plainto_tsquery('english', $1)
              AND p.start_date >= make_date($2, 1, 1)
              AND p.start_date < make_date($3 + 1, 1, 1)
            GROUP BY p.id, p.acronym, p.framework, p.ec_max_contribution
            HAVING COUNT(pub.id) > 0
            ORDER BY publication_count DESC
            LIMIT $4
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, technology, start_year, end_year, limit)
            return [dict(r) for r in rows]

    async def top_publications(
        self,
        technology: str,
        start_year: int,
        end_year: int,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Top-Publikationen mit DOI und Projekt-Link."""
        sql = """
            SELECT pub.title, pub.doi, pub.journal,
                   EXTRACT(YEAR FROM p.start_date)::int AS publication_year,
                   p.acronym AS project_acronym
            FROM cordis_schema.publications pub
            JOIN cordis_schema.projects p ON pub.project_id = p.id
            WHERE p.search_vector @@ plainto_tsquery('english', $1)
              AND p.start_date >= make_date($2, 1, 1)
              AND p.start_date < make_date($3 + 1, 1, 1)
              AND pub.doi IS NOT NULL AND pub.doi != ''
            ORDER BY p.start_date DESC
            LIMIT $4
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, technology, start_year, end_year, limit)
            return [dict(r) for r in rows]

    async def publication_summary(
        self,
        technology: str,
        start_year: int,
        end_year: int,
    ) -> dict[str, Any]:
        """Zusammenfassungsstatistiken: Gesamt-Pubs, Projekte mit Pubs, DOI-Abdeckung."""
        sql = """
            SELECT COUNT(*) AS total_publications,
                   COUNT(DISTINCT pub.project_id) AS total_projects_with_pubs,
                   COUNT(CASE WHEN pub.doi IS NOT NULL AND pub.doi != '' THEN 1 END)::float
                       / NULLIF(COUNT(*), 0) AS doi_coverage
            FROM cordis_schema.publications pub
            JOIN cordis_schema.projects p ON pub.project_id = p.id
            WHERE p.search_vector @@ plainto_tsquery('english', $1)
              AND p.start_date >= make_date($2, 1, 1)
              AND p.start_date < make_date($3 + 1, 1, 1)
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, technology, start_year, end_year)
            return dict(row) if row else {
                "total_publications": 0,
                "total_projects_with_pubs": 0,
                "doi_coverage": 0.0,
            }

    async def health_check(self) -> dict[str, Any]:
        """Datenbank-Health-Check."""
        async with self._pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            return {"status": "healthy", "pg_version": version}
