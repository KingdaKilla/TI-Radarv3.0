"""GeographicRepository — PostgreSQL-Datenbankzugriff fuer UC6.

Abfragen fuer geografische Verteilung, Kooperationspaare und
Cross-Border-Analyse. Nutzt patent_schema und cordis_schema.
"""

from __future__ import annotations

from typing import Any

import asyncpg
import structlog

from shared.domain.result_types import CountryCount

logger = structlog.get_logger(__name__)

# EU/EEA-Laendercodes fuer european_only-Filter
EU_EEA_COUNTRIES: frozenset[str] = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    "IS", "LI", "NO",
    "CH", "GB", "UK", "EL",
})


class GeographicRepository:
    """Async PostgreSQL-Zugriff fuer UC6 Geographic-Analysen.

    Alle Methoden verwenden den uebergebenen asyncpg Connection Pool.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # -----------------------------------------------------------------------
    # Patent-Laenderverteilung
    # -----------------------------------------------------------------------

    async def patent_country_distribution(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
        limit: int = 30,
    ) -> list[CountryCount]:
        """Patentanzahl pro Anmelder-Land fuer eine Technologie."""
        conditions = ["p.search_vector @@ plainto_tsquery('english', $1)"]
        params: list[Any] = [technology]
        idx = 2

        if start_year is not None:
            conditions.append(f"p.publication_year >= ${idx}")
            params.append(start_year)
            idx += 1

        if end_year is not None:
            conditions.append(f"p.publication_year <= ${idx}")
            params.append(end_year)
            idx += 1

        if european_only:
            conditions.append(f"p.applicant_countries && ${idx}::text[]")
            params.append(list(EU_EEA_COUNTRIES))
            idx += 1

        where = " AND ".join(conditions)

        country_filter = ""
        if european_only:
            country_filter = f"AND c.country_code = ANY(${idx}::text[])"
            params.append(list(EU_EEA_COUNTRIES))
            idx += 1

        params.append(limit)
        limit_idx = idx

        sql = f"""
            SELECT c.country_code AS country,
                   COUNT(*) AS count
            FROM patent_schema.patents p,
                 LATERAL unnest(p.applicant_countries) AS c(country_code)
            WHERE {where}
              AND p.applicant_countries IS NOT NULL
              AND array_length(p.applicant_countries, 1) > 0
              {country_filter}
            GROUP BY c.country_code
            ORDER BY count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [CountryCount(country=row["country"], count=row["count"]) for row in rows]

    # -----------------------------------------------------------------------
    # CORDIS-Laenderverteilung
    # -----------------------------------------------------------------------

    async def cordis_country_distribution(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
        limit: int = 30,
    ) -> list[CountryCount]:
        """Projektbeteiligungen pro Land aus CORDIS."""
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

        if european_only:
            conditions.append(f"o.country = ANY(${idx}::text[])")
            params.append(list(EU_EEA_COUNTRIES))
            idx += 1

        where = " AND ".join(conditions)
        params.append(limit)
        limit_idx = idx

        sql = f"""
            SELECT o.country,
                   COUNT(DISTINCT o.project_id) AS count
            FROM cordis_schema.projects p
            JOIN cordis_schema.organizations o ON o.project_id = p.id
            WHERE {where}
              AND o.country IS NOT NULL AND o.country != ''
            GROUP BY o.country
            ORDER BY count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [CountryCount(country=row["country"], count=row["count"]) for row in rows]

    # -----------------------------------------------------------------------
    # Stadt-Verteilung
    # -----------------------------------------------------------------------

    async def city_distribution(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Organisationen pro Stadt aus CORDIS-Projektpartnern."""
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

        if european_only:
            conditions.append(f"o.country = ANY(${idx}::text[])")
            params.append(list(EU_EEA_COUNTRIES))
            idx += 1

        where = " AND ".join(conditions)
        params.append(limit)
        limit_idx = idx

        sql = f"""
            SELECT o.city,
                   o.country,
                   COUNT(DISTINCT o.name) AS actor_count,
                   COUNT(DISTINCT o.project_id) AS project_count
            FROM cordis_schema.projects p
            JOIN cordis_schema.organizations o ON o.project_id = p.id
            WHERE {where}
              AND o.city IS NOT NULL AND o.city != ''
            GROUP BY o.city, o.country
            ORDER BY actor_count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {
                    "city": row["city"],
                    "country_code": row["country"],
                    "actor_count": row["actor_count"],
                    "project_count": row["project_count"],
                }
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # Kooperationspaare
    # -----------------------------------------------------------------------

    async def cooperation_pairs(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Laender-Kooperationspaare aus CORDIS-Projekten."""
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

        eu_filter = ""
        if european_only:
            eu_filter = f"""
                AND o1.country = ANY(${idx}::text[])
                AND o2.country = ANY(${idx}::text[])
            """
            params.append(list(EU_EEA_COUNTRIES))
            idx += 1

        params.append(limit)
        limit_idx = idx

        # Bipartiter-Jaccard-Score setzt Gesamt-Projektzahlen pro Land voraus.
        # Deshalb ergaenzt der CTE `country_totals` die rohen co-project counts
        # um `projects_a`/`projects_b`, sodass der Service den Score direkt
        # berechnen kann: (2 * co_projects) / (projects_a + projects_b).
        sql = f"""
            WITH country_totals AS (
                SELECT o.country AS country,
                       COUNT(DISTINCT p.id) AS total_projects
                FROM cordis_schema.projects p
                JOIN cordis_schema.organizations o ON o.project_id = p.id
                WHERE {where}
                  AND o.country IS NOT NULL AND o.country != ''
                GROUP BY o.country
            ),
            pair_counts AS (
                SELECT o1.country AS country_a,
                       o2.country AS country_b,
                       COUNT(DISTINCT p.id) AS co_project_count
                FROM cordis_schema.projects p
                JOIN cordis_schema.organizations o1 ON o1.project_id = p.id
                JOIN cordis_schema.organizations o2 ON o2.project_id = p.id
                WHERE {where}
                  AND o1.country IS NOT NULL AND o1.country != ''
                  AND o2.country IS NOT NULL AND o2.country != ''
                  AND o1.country < o2.country
                  {eu_filter}
                GROUP BY o1.country, o2.country
            )
            SELECT pc.country_a,
                   pc.country_b,
                   pc.co_project_count,
                   COALESCE(ta.total_projects, 0) AS projects_a,
                   COALESCE(tb.total_projects, 0) AS projects_b
            FROM pair_counts pc
            LEFT JOIN country_totals ta ON ta.country = pc.country_a
            LEFT JOIN country_totals tb ON tb.country = pc.country_b
            ORDER BY pc.co_project_count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {
                    "country_a": row["country_a"],
                    "country_b": row["country_b"],
                    "co_project_count": row["co_project_count"],
                    "projects_a": row["projects_a"],
                    "projects_b": row["projects_b"],
                }
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # Cross-Border-Anteil
    # -----------------------------------------------------------------------

    async def cross_border_share(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        min_countries: int = 2,
    ) -> dict[str, int | float]:
        """Anteil grenzueberschreitender Projekte berechnen."""
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
        params.append(min_countries)
        min_idx = idx

        sql = f"""
            WITH project_countries AS (
                SELECT p.id,
                       COUNT(DISTINCT o.country) AS n_countries
                FROM cordis_schema.projects p
                JOIN cordis_schema.organizations o ON o.project_id = p.id
                WHERE {where}
                  AND o.country IS NOT NULL AND o.country != ''
                GROUP BY p.id
            )
            SELECT COUNT(*) AS total_projects,
                   COUNT(*) FILTER (WHERE n_countries >= ${min_idx}) AS cross_border_projects
            FROM project_countries
        """

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, *params)
            total = row["total_projects"] if row else 0
            cross = row["cross_border_projects"] if row else 0
            share = cross / total if total > 0 else 0.0
            return {
                "total_projects": total,
                "cross_border_projects": cross,
                "cross_border_share": round(share, 4),
            }

    # -----------------------------------------------------------------------
    # Health Check
    # -----------------------------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        """Datenbank-Health-Check."""
        async with self._pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            return {"status": "healthy", "pg_version": version}
