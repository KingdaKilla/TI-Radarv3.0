"""PatentGrantRepository — PostgreSQL-Datenbankzugriff fuer UC12.

Abfragen fuer Patent-Erteilungsraten basierend auf EPO Kind-Codes.
Nutzt patent_schema fuer Anmelde- und Erteilungsdaten.
"""

from __future__ import annotations

from typing import Any

import asyncpg
import structlog

logger = structlog.get_logger(__name__)

EU_EEA_COUNTRIES: frozenset[str] = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    "IS", "LI", "NO", "CH", "GB", "UK", "EL",
})


class PatentGrantRepository:
    """Async PostgreSQL-Zugriff fuer UC12 Patent-Grant-Analysen."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def kind_code_distribution(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[dict[str, Any]]:
        """Verteilung der Kind-Codes fuer eine Technologie."""
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

        where = " AND ".join(conditions)

        sql = f"""
            SELECT COALESCE(p.kind, 'UNKNOWN') AS kind_code,
                   COUNT(*) AS count
            FROM patent_schema.patents p
            WHERE {where}
              AND p.kind IS NOT NULL
            GROUP BY p.kind
            ORDER BY count DESC
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            total = sum(row["count"] for row in rows)
            return [
                {
                    "kind_code": row["kind_code"],
                    "count": row["count"],
                    "share": round(row["count"] / total, 4) if total > 0 else 0.0,
                }
                for row in rows
            ]

    async def grant_rate_by_year(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[dict[str, Any]]:
        """Erteilungsrate pro Jahr (Anmeldungen vs. Erteilungen)."""
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

        where = " AND ".join(conditions)

        sql = f"""
            SELECT p.publication_year AS year,
                   COUNT(*) FILTER (WHERE p.kind IN ('A', 'A1', 'A2', 'A3', 'A4', 'A8', 'A9')) AS application_count,
                   COUNT(*) FILTER (WHERE p.kind IN ('B', 'B1', 'B2', 'B3', 'B8')) AS grant_count
            FROM patent_schema.patents p
            WHERE {where}
              AND p.publication_year IS NOT NULL
            GROUP BY p.publication_year
            ORDER BY p.publication_year
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {
                    "year": row["year"],
                    "application_count": row["application_count"],
                    "grant_count": row["grant_count"],
                    "grant_rate": round(row["grant_count"] / row["application_count"], 4) if row["application_count"] > 0 else 0.0,
                }
                for row in rows
            ]

    async def grant_rate_by_country(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Erteilungsrate pro Anmelder-Land."""
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

        country_eu_filter = ""
        if european_only:
            country_eu_filter = f"AND c.country_code = ANY(${idx}::text[])"
            params.append(list(EU_EEA_COUNTRIES))
            idx += 1

        params.append(limit)
        limit_idx = idx

        sql = f"""
            SELECT c.country_code AS country_code,
                   COUNT(*) FILTER (WHERE p.kind IN ('A', 'A1', 'A2', 'A3', 'A4', 'A8', 'A9')) AS application_count,
                   COUNT(*) FILTER (WHERE p.kind IN ('B', 'B1', 'B2', 'B3', 'B8')) AS grant_count
            FROM patent_schema.patents p,
                 LATERAL unnest(p.applicant_countries) AS c(country_code)
            WHERE {where}
              AND p.applicant_countries IS NOT NULL
              {country_eu_filter}
            GROUP BY c.country_code
            HAVING COUNT(*) FILTER (WHERE p.kind IN ('A', 'A1', 'A2', 'A3', 'A4', 'A8', 'A9')) > 0
            ORDER BY application_count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {
                    "country_code": row["country_code"],
                    "application_count": row["application_count"],
                    "grant_count": row["grant_count"],
                    "grant_rate": round(row["grant_count"] / row["application_count"], 4) if row["application_count"] > 0 else 0.0,
                }
                for row in rows
            ]

    async def grant_rate_by_cpc(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 15,
    ) -> list[dict[str, Any]]:
        """Erteilungsrate pro CPC-Code."""
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

        where = " AND ".join(conditions)
        params.append(limit)
        limit_idx = idx

        sql = f"""
            SELECT cpc.cpc_code,
                   COALESCE(cd.description_en, '') AS description,
                   COUNT(*) FILTER (WHERE p.kind IN ('A', 'A1', 'A2', 'A3', 'A4', 'A8', 'A9')) AS application_count,
                   COUNT(*) FILTER (WHERE p.kind IN ('B', 'B1', 'B2', 'B3', 'B8')) AS grant_count
            FROM patent_schema.patents p,
                 LATERAL unnest(p.cpc_codes) AS cpc(cpc_code)
            LEFT JOIN patent_schema.cpc_descriptions cd
                ON cd.code = cpc.cpc_code
            WHERE {where}
              AND p.cpc_codes IS NOT NULL
              AND array_length(p.cpc_codes, 1) > 0
            GROUP BY cpc.cpc_code, cd.description_en
            HAVING COUNT(*) FILTER (WHERE p.kind IN ('A', 'A1', 'A2', 'A3', 'A4', 'A8', 'A9')) > 0
            ORDER BY application_count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {
                    "cpc_code": row["cpc_code"],
                    "description": row["description"],
                    "application_count": row["application_count"],
                    "grant_count": row["grant_count"],
                    "grant_rate": round(row["grant_count"] / row["application_count"], 4) if row["application_count"] > 0 else 0.0,
                }
                for row in rows
            ]

    async def avg_time_to_grant(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> dict[str, float]:
        """Durchschnittliche Zeit von Anmeldung (filing_date) bis Erteilung (publication_date).

        Berechnet nur fuer erteilte Patente (kind IN ('B', 'B1', 'B2', 'B3'))
        bei denen sowohl filing_date als auch publication_date vorhanden sind.
        """
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

        where = " AND ".join(conditions)

        sql = f"""
            SELECT
                COALESCE(AVG(EXTRACT(EPOCH FROM AGE(p.publication_date, p.filing_date)) / 2592000.0), 0) AS avg_months,
                COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (
                    ORDER BY EXTRACT(EPOCH FROM AGE(p.publication_date, p.filing_date)) / 2592000.0
                ), 0) AS median_months
            FROM patent_schema.patents p
            WHERE {where}
              AND p.kind IN ('B', 'B1', 'B2', 'B3')
              AND p.filing_date IS NOT NULL
              AND p.publication_date IS NOT NULL
              AND p.publication_date > p.filing_date
        """

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, *params)
            if row is None:
                return {"avg_months": 0.0, "median_months": 0.0}
            return {
                "avg_months": round(float(row["avg_months"]), 1),
                "median_months": round(float(row["median_months"]), 1),
            }

    async def health_check(self) -> dict[str, Any]:
        """Datenbank-Health-Check."""
        async with self._pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            return {"status": "healthy", "pg_version": version}
