"""ResearchImpactRepository — PostgreSQL-Datenbankzugriff fuer UC7.

Primaere Datenquelle fuer Publikationsmetriken ist Semantic Scholar.
CORDIS-Organisationen dienen als Proxy fuer Top-Institutionen,
da Semantic Scholar keine Institutionsdaten liefert.
"""

from __future__ import annotations

from typing import Any

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


class ResearchImpactRepository:
    """Async PostgreSQL-Zugriff fuer UC7 Research-Impact.

    Stellt CORDIS-basierte Institutionsabfragen und Health-Checks bereit.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def health_check(self) -> dict[str, Any]:
        """Datenbank-Health-Check."""
        async with self._pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            return {"status": "healthy", "pg_version": version}

    async def get_top_institutions(
        self,
        technology: str,
        *,
        limit: int = 15,
    ) -> list[dict[str, Any]]:
        """Top-Institutionen aus CORDIS-Projektbeteiligungen ermitteln.

        Sucht CORDIS-Projekte, deren Titel oder Objective den Suchbegriff
        enthalten (via tsvector full-text search), und gruppiert die
        beteiligten Organisationen nach Name, Land und Aktivitaetstyp.

        Args:
            technology: Suchbegriff (Technologie).
            limit: Maximale Anzahl zurueckgegebener Institutionen.

        Returns:
            Liste von Dicts mit name, project_count, country, activity_type.
        """
        # Build a tsquery from the technology search term.
        # plainto_tsquery handles multi-word terms safely.
        # Filter to research-relevant activity types:
        #   HES = Higher Education, REC = Research Organisation, PRC = Private Company
        # Excludes PUB (Public Body) and OTH (Other) which include
        # media outlets, government agencies, etc.
        sql = """
            SELECT o.name,
                   o.country,
                   COALESCE(o.activity_type, '') AS activity_type,
                   COUNT(DISTINCT o.project_id) AS project_count
            FROM cordis_schema.projects p
            JOIN cordis_schema.organizations o ON o.project_id = p.id
            WHERE p.search_vector @@ plainto_tsquery('english', $1)
              AND o.name IS NOT NULL
              AND o.name != ''
              AND o.activity_type IN ('HES', 'REC', 'PRC')
            GROUP BY o.name, o.country, o.activity_type
            ORDER BY project_count DESC
            LIMIT $2
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, technology, limit)
            return [
                {
                    "name": row["name"],
                    "project_count": row["project_count"],
                    "country": row["country"] or "",
                    "activity_type": row["activity_type"],
                }
                for row in rows
            ]
