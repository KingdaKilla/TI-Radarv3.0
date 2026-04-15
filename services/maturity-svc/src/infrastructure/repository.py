"""MaturityRepository — PostgreSQL-Datenbankzugriff fuer UC2.

Liefert Patent-Familien-Zeitreihen fuer S-Curve-Analyse.
Migriert von SQLite (aiosqlite + FTS5) zu PostgreSQL (asyncpg + tsvector).

Zentrale Abfragen:
- Patent-Familien pro Jahr (DISTINCT family_id, OECD 2009)
- Fallback: Patent-Zaehlungen pro Jahr (ohne Deduplizierung)
"""

from __future__ import annotations

from typing import Any

import asyncpg
import structlog

from shared.domain.result_types import YearCount

logger = structlog.get_logger(__name__)

# EU/EEA-Laendercodes fuer european_only-Filter
EU_EEA_COUNTRIES: frozenset[str] = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    "IS", "LI", "NO",
    "CH", "GB",
})


class MaturityRepository:
    """Async PostgreSQL-Zugriff fuer UC2 Maturity-Analysen.

    Alle Methoden verwenden den uebergebenen asyncpg Connection Pool.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def count_families_by_year(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = True,
    ) -> list[YearCount]:
        """Patent-Familien pro Jahr zaehlen (DISTINCT family_id).

        OECD (2009): Patent-Familien-Deduplizierung vermeidet
        Mehrfachzaehlung von Patentanmeldungen derselben Erfindung.
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

        if european_only:
            conditions.append(f"p.applicant_countries && ${idx}::text[]")
            params.append(list(EU_EEA_COUNTRIES))
            idx += 1

        where = " AND ".join(conditions)

        sql = f"""
            SELECT p.publication_year AS year,
                   COUNT(DISTINCT p.family_id) AS count
            FROM patent_schema.patents p
            WHERE {where}
              AND p.publication_year IS NOT NULL
              AND p.family_id IS NOT NULL
            GROUP BY p.publication_year
            ORDER BY p.publication_year
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [YearCount(year=row["year"], count=row["count"]) for row in rows]

    async def count_patents_by_year(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = True,
    ) -> list[YearCount]:
        """Patentanzahl pro Jahr (ohne Deduplizierung).

        Fallback wenn family_id nicht verfuegbar.
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

        if european_only:
            conditions.append(f"p.applicant_countries && ${idx}::text[]")
            params.append(list(EU_EEA_COUNTRIES))
            idx += 1

        where = " AND ".join(conditions)

        sql = f"""
            SELECT p.publication_year AS year,
                   COUNT(*) AS count
            FROM patent_schema.patents p
            WHERE {where}
              AND p.publication_year IS NOT NULL
            GROUP BY p.publication_year
            ORDER BY p.publication_year
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [YearCount(year=row["year"], count=row["count"]) for row in rows]
