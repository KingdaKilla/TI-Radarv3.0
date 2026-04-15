"""FundingRepository — PostgreSQL-Datenbankzugriff fuer UC4.

Liefert EU-Foerderdaten aus CORDIS: Zeitreihen, Programme,
Instrumente, Top-Organisationen und Laenderverteilung.

Alle Queries arbeiten auf cordis_schema.projects und
cordis_schema.organizations.
"""

from __future__ import annotations

from typing import Any

import asyncpg
import structlog

from shared.domain.result_types import FundingYear

logger = structlog.get_logger(__name__)


class FundingRepository:
    """Async PostgreSQL-Zugriff fuer UC4 Funding-Analysen."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # -----------------------------------------------------------------------
    # Foerderung pro Jahr
    # -----------------------------------------------------------------------

    async def funding_by_year(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[FundingYear]:
        """EU-Foerderung pro Jahr fuer eine Technologie."""
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
                   COALESCE(SUM(p.ec_max_contribution), 0) AS funding,
                   COUNT(*) AS count
            FROM cordis_schema.projects p
            WHERE {where}
              AND p.start_date IS NOT NULL
              AND p.ec_max_contribution IS NOT NULL
            GROUP BY year
            ORDER BY year
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                FundingYear(year=row["year"], funding=float(row["funding"]), count=row["count"])
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # Foerderung pro Programm
    # -----------------------------------------------------------------------

    async def funding_by_programme(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[dict[str, Any]]:
        """Foerderung aufgeschluesselt nach EU-Rahmenprogramm."""
        conditions = ["p.search_vector @@ plainto_tsquery('english', $1)"]
        params: list[Any] = [technology]
        idx = 2

        if start_year is not None:
            conditions.append(f"p.start_date >= make_date(${idx}, 1, 1)")
            params.append(start_year)
            idx += 1

        if end_year is not None:
            conditions.append(f"p.start_date <= make_date(${idx}, 12, 31)")
            params.append(end_year)
            idx += 1

        where = " AND ".join(conditions)

        sql = f"""
            SELECT COALESCE(p.framework, 'UNKNOWN') AS programme,
                   COALESCE(SUM(p.ec_max_contribution), 0) AS funding,
                   COUNT(*) AS count
            FROM cordis_schema.projects p
            WHERE {where}
              AND p.start_date IS NOT NULL
            GROUP BY programme
            ORDER BY funding DESC
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {
                    "programme": row["programme"],
                    "funding": float(row["funding"]),
                    "count": row["count"],
                }
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # Foerderung pro Instrument (RIA, IA, CSA)
    # -----------------------------------------------------------------------

    async def funding_by_instrument(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[dict[str, Any]]:
        """Foerderung aufgeschluesselt nach Instrument (RIA, IA, CSA, ERC)."""
        conditions = ["p.search_vector @@ plainto_tsquery('english', $1)"]
        params: list[Any] = [technology]
        idx = 2

        if start_year is not None:
            conditions.append(f"p.start_date >= make_date(${idx}, 1, 1)")
            params.append(start_year)
            idx += 1

        if end_year is not None:
            conditions.append(f"p.start_date <= make_date(${idx}, 12, 31)")
            params.append(end_year)
            idx += 1

        where = " AND ".join(conditions)

        sql = f"""
            SELECT COALESCE(p.funding_scheme, 'UNKNOWN') AS funding_scheme,
                   COALESCE(SUM(p.ec_max_contribution), 0) AS funding,
                   COUNT(*) AS count
            FROM cordis_schema.projects p
            WHERE {where}
              AND p.start_date IS NOT NULL
            GROUP BY p.funding_scheme
            ORDER BY funding DESC
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {
                    "funding_scheme": row["funding_scheme"],
                    "funding": float(row["funding"]),
                    "count": row["count"],
                }
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # Top-finanzierte Organisationen
    # -----------------------------------------------------------------------

    async def top_funded_organizations(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Top-Organisationen nach erhaltenem Foerdervolumen."""
        conditions = ["p.search_vector @@ plainto_tsquery('english', $1)"]
        params: list[Any] = [technology]
        idx = 2

        if start_year is not None:
            conditions.append(f"p.start_date >= make_date(${idx}, 1, 1)")
            params.append(start_year)
            idx += 1

        if end_year is not None:
            conditions.append(f"p.start_date <= make_date(${idx}, 12, 31)")
            params.append(end_year)
            idx += 1

        where = " AND ".join(conditions)
        params.append(limit)
        limit_idx = idx

        sql = f"""
            SELECT o.name,
                   o.country,
                   COALESCE(o.activity_type, '') AS type,
                   COALESCE(SUM(o.ec_contribution), 0) AS funding,
                   COUNT(DISTINCT o.project_id) AS count
            FROM cordis_schema.projects p
            JOIN cordis_schema.organizations o ON o.project_id = p.id
            WHERE {where}
              AND o.name IS NOT NULL
              AND o.name != ''
            GROUP BY o.name, o.country, o.activity_type
            ORDER BY funding DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {
                    "name": row["name"],
                    "country": row["country"],
                    "type": row["type"],
                    "funding": float(row["funding"]),
                    "count": row["count"],
                }
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # Laenderverteilung
    # -----------------------------------------------------------------------

    async def funding_by_country(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Foerderung pro Land (aus Organizations-Tabelle)."""
        conditions = ["p.search_vector @@ plainto_tsquery('english', $1)"]
        params: list[Any] = [technology]
        idx = 2

        if start_year is not None:
            conditions.append(f"p.start_date >= make_date(${idx}, 1, 1)")
            params.append(start_year)
            idx += 1

        if end_year is not None:
            conditions.append(f"p.start_date <= make_date(${idx}, 12, 31)")
            params.append(end_year)
            idx += 1

        where = " AND ".join(conditions)
        params.append(limit)
        limit_idx = idx

        sql = f"""
            SELECT o.country,
                   COALESCE(SUM(o.ec_contribution), 0) AS funding,
                   COUNT(DISTINCT o.project_id) AS count
            FROM cordis_schema.projects p
            JOIN cordis_schema.organizations o ON o.project_id = p.id
            WHERE {where}
              AND o.country IS NOT NULL
              AND o.country != ''
            GROUP BY o.country
            ORDER BY funding DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {
                    "country": row["country"],
                    "funding": float(row["funding"]),
                    "count": row["count"],
                }
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # Durchschnittliche Projektdauer
    # -----------------------------------------------------------------------

    async def avg_project_duration(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> float:
        """Durchschnittliche Projektdauer in Monaten."""
        conditions = ["p.search_vector @@ plainto_tsquery('english', $1)"]
        params: list[Any] = [technology]
        idx = 2

        if start_year is not None:
            conditions.append(f"p.start_date >= make_date(${idx}, 1, 1)")
            params.append(start_year)
            idx += 1

        if end_year is not None:
            conditions.append(f"p.start_date <= make_date(${idx}, 12, 31)")
            params.append(end_year)
            idx += 1

        where = " AND ".join(conditions)

        sql = f"""
            SELECT AVG(
                (p.end_date - p.start_date)::float / 30.44
            ) AS avg_months
            FROM cordis_schema.projects p
            WHERE {where}
              AND p.start_date IS NOT NULL
              AND p.end_date IS NOT NULL
              AND p.end_date > p.start_date
        """

        async with self._pool.acquire() as conn:
            result = await conn.fetchval(sql, *params)
            return round(float(result), 1) if result else 0.0
