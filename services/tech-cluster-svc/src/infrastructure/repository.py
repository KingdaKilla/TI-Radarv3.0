"""TechClusterRepository — PostgreSQL-Datenbankzugriff fuer UC9.

Abfragen fuer Akteur-CPC-Beziehungen und Cluster-Daten.
Nutzt patent_schema und cordis_schema.
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


class TechClusterRepository:
    """Async PostgreSQL-Zugriff fuer UC9 Tech-Cluster-Analysen."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def actor_cpc_matrix(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Akteur-CPC-Paare fuer Co-Occurrence-Matrix."""
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
        params.append(limit)
        limit_idx = idx

        sql = f"""
            SELECT a.name AS actor,
                   cpc.cpc_code,
                   COUNT(DISTINCT p.id) AS count
            FROM patent_schema.patents p,
                 LATERAL unnest(p.cpc_codes) AS cpc(cpc_code),
                 LATERAL string_to_table(p.applicant_names, '; ') AS a(name)
            WHERE {where}
              AND p.cpc_codes IS NOT NULL
              AND array_length(p.cpc_codes, 1) > 0
              AND p.applicant_names IS NOT NULL
              AND length(p.applicant_names) > 0
            GROUP BY a.name, cpc.cpc_code
            ORDER BY count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {"actor": row["actor"], "cpc_code": row["cpc_code"], "count": row["count"]}
                for row in rows
            ]

    async def cpc_co_occurrence(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """CPC-Co-Occurrence-Paare fuer Clustering."""
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
            SELECT c1.cpc_code AS cpc_a,
                   c2.cpc_code AS cpc_b,
                   COUNT(DISTINCT p.id) AS co_count
            FROM patent_schema.patents p,
                 LATERAL unnest(p.cpc_codes) AS c1(cpc_code),
                 LATERAL unnest(p.cpc_codes) AS c2(cpc_code)
            WHERE {where}
              AND p.cpc_codes IS NOT NULL
              AND array_length(p.cpc_codes, 1) > 1
              AND c1.cpc_code < c2.cpc_code
            GROUP BY c1.cpc_code, c2.cpc_code
            ORDER BY co_count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {"cpc_a": row["cpc_a"], "cpc_b": row["cpc_b"], "co_count": row["co_count"]}
                for row in rows
            ]

    async def patent_counts_by_cpc_year(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[dict[str, Any]]:
        """Patent-Zahlen pro CPC-Code und Jahr (fuer Cluster-CAGR)."""
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
            SELECT cpc.cpc_code,
                   p.publication_year AS year,
                   COUNT(DISTINCT p.id) AS count
            FROM patent_schema.patents p,
                 LATERAL unnest(p.cpc_codes) AS cpc(cpc_code)
            WHERE {where}
              AND p.cpc_codes IS NOT NULL
              AND array_length(p.cpc_codes, 1) > 0
            GROUP BY cpc.cpc_code, p.publication_year
            ORDER BY cpc.cpc_code, p.publication_year
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {"cpc_code": row["cpc_code"], "year": row["year"], "count": row["count"]}
                for row in rows
            ]

    async def health_check(self) -> dict[str, Any]:
        """Datenbank-Health-Check."""
        async with self._pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            return {"status": "healthy", "pg_version": version}
