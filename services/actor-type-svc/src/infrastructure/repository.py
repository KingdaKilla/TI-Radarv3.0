"""ActorTypeRepository — PostgreSQL-Datenbankzugriff fuer UC11.

Abfragen fuer Akteur-Typ-Verteilung aus CORDIS project_participants.
Nutzt das activity_type Feld (HES, PRC, REC, OTH, PUB).
"""

from __future__ import annotations

from typing import Any

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


class ActorTypeRepository:
    """Async PostgreSQL-Zugriff fuer UC11 Actor-Type-Analysen."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def type_breakdown(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[dict[str, Any]]:
        """Akteur-Typ-Verteilung fuer eine Technologie."""
        conditions = ["p.search_vector @@ plainto_tsquery('english', $1)"]
        params: list[Any] = [technology]
        idx = 2

        if start_year is not None:
            conditions.append(f"EXTRACT(YEAR FROM p.start_date)::int >= ${idx}")
            params.append(start_year)
            idx += 1
        if end_year is not None:
            conditions.append(f"EXTRACT(YEAR FROM p.start_date)::int <= ${idx}")
            params.append(end_year)
            idx += 1

        where = " AND ".join(conditions)

        sql = f"""
            SELECT COALESCE(o.activity_type, 'OTH') AS activity_type,
                   COUNT(DISTINCT o.name) AS actor_count,
                   COUNT(DISTINCT o.project_id) AS project_count,
                   COALESCE(SUM(o.ec_contribution), 0) AS funding
            FROM cordis_schema.projects p
            JOIN cordis_schema.organizations o ON o.project_id = p.id
            WHERE {where}
              AND o.name IS NOT NULL AND o.name != ''
            GROUP BY COALESCE(o.activity_type, 'OTH')
            ORDER BY actor_count DESC
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {
                    "activity_type": row["activity_type"],
                    "actor_count": row["actor_count"],
                    "project_count": row["project_count"],
                    "funding": float(row["funding"]),
                }
                for row in rows
            ]

    async def type_trend(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[dict[str, Any]]:
        """Jahres-Trend der Akteur-Typ-Verteilung."""
        conditions = ["p.search_vector @@ plainto_tsquery('english', $1)"]
        params: list[Any] = [technology]
        idx = 2

        if start_year is not None:
            conditions.append(f"EXTRACT(YEAR FROM p.start_date)::int >= ${idx}")
            params.append(start_year)
            idx += 1
        if end_year is not None:
            conditions.append(f"EXTRACT(YEAR FROM p.start_date)::int <= ${idx}")
            params.append(end_year)
            idx += 1

        where = " AND ".join(conditions)

        sql = f"""
            SELECT EXTRACT(YEAR FROM p.start_date)::int AS year,
                   COALESCE(o.activity_type, 'OTH') AS activity_type,
                   COUNT(DISTINCT o.name) AS count
            FROM cordis_schema.projects p
            JOIN cordis_schema.organizations o ON o.project_id = p.id
            WHERE {where}
              AND p.start_date IS NOT NULL
              AND o.name IS NOT NULL AND o.name != ''
            GROUP BY year, COALESCE(o.activity_type, 'OTH')
            ORDER BY year
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {"year": row["year"], "activity_type": row["activity_type"], "count": row["count"]}
                for row in rows
            ]

    async def top_actors_by_type(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Top-Akteure pro Organisationstyp."""
        conditions = ["p.search_vector @@ plainto_tsquery('english', $1)"]
        params: list[Any] = [technology]
        idx = 2

        if start_year is not None:
            conditions.append(f"EXTRACT(YEAR FROM p.start_date)::int >= ${idx}")
            params.append(start_year)
            idx += 1
        if end_year is not None:
            conditions.append(f"EXTRACT(YEAR FROM p.start_date)::int <= ${idx}")
            params.append(end_year)
            idx += 1

        where = " AND ".join(conditions)
        params.append(limit)
        limit_idx = idx

        sql = f"""
            SELECT o.name,
                   COALESCE(o.activity_type, 'OTH') AS activity_type,
                   o.country AS country_code,
                   COUNT(DISTINCT o.project_id) AS project_count,
                   COALESCE(o.sme, false) AS is_sme
            FROM cordis_schema.projects p
            JOIN cordis_schema.organizations o ON o.project_id = p.id
            WHERE {where}
              AND o.name IS NOT NULL AND o.name != ''
            GROUP BY o.name, o.activity_type, o.country, o.sme
            ORDER BY project_count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {
                    "name": row["name"],
                    "type": row["activity_type"],
                    "country_code": row["country_code"] or "",
                    "project_count": row["project_count"],
                    "is_sme": row["is_sme"],
                }
                for row in rows
            ]

    async def sme_count(self, technology: str) -> dict[str, int]:
        """Zaehlung der SME-Akteure unter PRC-Typ."""
        sql = """
            SELECT COUNT(DISTINCT CASE WHEN o.sme = true THEN o.name END) AS sme_count,
                   COUNT(DISTINCT o.name) AS total_prc
            FROM cordis_schema.projects p
            JOIN cordis_schema.organizations o ON o.project_id = p.id
            WHERE p.search_vector @@ plainto_tsquery('english', $1)
              AND COALESCE(o.activity_type, '') = 'PRC'
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, technology)
            return {
                "sme_count": row["sme_count"] if row else 0,
                "total_prc": row["total_prc"] if row else 0,
            }

    async def health_check(self) -> dict[str, Any]:
        """Datenbank-Health-Check."""
        async with self._pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            return {"status": "healthy", "pg_version": version}
