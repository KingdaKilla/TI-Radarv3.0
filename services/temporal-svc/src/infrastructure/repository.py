"""TemporalRepository — PostgreSQL-Datenbankzugriff fuer UC8.

Abfragen fuer Akteur-Dynamik, CPC-Breite und Programmevolution.
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
    "IS", "LI", "NO",
    "CH", "GB", "UK", "EL",
})


class TemporalRepository:
    """Async PostgreSQL-Zugriff fuer UC8 Temporal-Analysen."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # -----------------------------------------------------------------------
    # Patent-Akteure pro Jahr
    # -----------------------------------------------------------------------

    async def patent_actors_by_year(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Patent-Anmelder pro Jahr fuer eine Technologie."""
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
                   trim(a.name) AS name,
                   COUNT(*) AS count
            FROM patent_schema.patents p,
                 LATERAL string_to_table(p.applicant_names, '; ') AS a(name)
            WHERE {where}
              AND p.applicant_names IS NOT NULL
              AND length(p.applicant_names) > 0
            GROUP BY p.publication_year, trim(a.name)
            ORDER BY p.publication_year, count DESC
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {"year": row["year"], "name": row["name"], "count": row["count"]}
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # CORDIS-Akteure pro Jahr
    # -----------------------------------------------------------------------

    async def cordis_actors_by_year(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
    ) -> list[dict[str, Any]]:
        """CORDIS-Organisationen pro Jahr fuer eine Technologie.

        Bug M-002: Der JOIN projects -> organizations erzeugt
        Row-Duplikation (1 Projekt x N Organisationen).  Ohne
        ``COUNT(DISTINCT p.id)`` wuerden Projekte pro (Jahr, Akteur)
        mehrfach gezaehlt werden, wenn derselbe Akteur in mehreren
        Rollen am Projekt beteiligt ist.  DISTINCT ist hier zwingend.
        """
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

        if european_only:
            conditions.append(f"o.country = ANY(${idx}::text[])")
            params.append(list(EU_EEA_COUNTRIES))
            idx += 1

        where = " AND ".join(conditions)

        # DISTINCT p.id: Entdoppelt die (year, actor)-Aggregation bei
        # Mehrfach-Rollen der Organisation im selben Projekt.
        sql = f"""
            SELECT EXTRACT(YEAR FROM p.start_date)::int AS year,
                   o.name,
                   COUNT(DISTINCT p.id) AS count
            FROM cordis_schema.projects p
            JOIN cordis_schema.organizations o ON o.project_id = p.id
            WHERE {where}
              AND o.name IS NOT NULL AND o.name != ''
              AND p.start_date IS NOT NULL
            GROUP BY year, o.name
            ORDER BY year, count DESC
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {"year": row["year"], "name": row["name"], "count": row["count"]}
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # Distinct Project Count (Bug M-002 / C2.1)
    # -----------------------------------------------------------------------

    async def count_distinct_cordis_projects(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
    ) -> int:
        """Anzahl DISTINCT CORDIS-Projekte fuer eine Technologie.

        Bug M-002 / C2.1: Frueher wurde ``record_count`` fuer die
        CORDIS-Datenquelle aus ``len(cordis_actors_raw)`` berechnet —
        also aus den Zeilen einer ``GROUP BY (year, o.name)``-Aggregation.
        Ein Projekt mit 5 Organisationen in 3 Laendern ueber 2 Jahre
        taucht dort als *bis zu 10 Zeilen* auf.  Bei Blockchain ergab
        das 3148 statt 322 (+877 %).

        Diese Methode liefert die korrekte DISTINCT-Projekt-Anzahl
        direkt aus der Datenbank.  ``european_only`` triggert den
        Organisations-JOIN — deshalb ist ``DISTINCT p.id`` im
        ``european_only=True``-Pfad zwingend (sonst gaebe es erneut
        Row-Multiplikation pro Land/Organisation).

        Args:
            technology: Suchbegriff fuer Volltextsuche.
            start_year: Erstes Jahr (inklusiv).
            end_year: Letztes Jahr (inklusiv).
            european_only: Nur Projekte mit mindestens einer EU/EEA-
                Organisation beruecksichtigen.

        Returns:
            Anzahl unterschiedlicher Projekte (``COUNT(DISTINCT p.id)``).
        """
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

        # european_only erfordert den Organisations-JOIN — ohne DISTINCT
        # wird jedes Projekt pro Organisation mehrfach gezaehlt.
        if european_only:
            conditions.append(f"o.country = ANY(${idx}::text[])")
            params.append(list(EU_EEA_COUNTRIES))
            idx += 1
            from_clause = (
                "cordis_schema.projects p "
                "JOIN cordis_schema.organizations o ON o.project_id = p.id"
            )
        else:
            from_clause = "cordis_schema.projects p"

        where = " AND ".join(conditions)

        sql = f"""
            SELECT COUNT(DISTINCT p.id) AS total
            FROM {from_clause}
            WHERE {where}
              AND p.start_date IS NOT NULL
        """

        async with self._pool.acquire() as conn:
            total = await conn.fetchval(sql, *params)
            return int(total or 0)

    # -----------------------------------------------------------------------
    # CPC-Codes pro Jahr (fuer Technologie-Breite)
    # -----------------------------------------------------------------------

    async def cpc_codes_by_year(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
    ) -> list[dict[str, Any]]:
        """CPC-Codes pro Jahr fuer Technologie-Breite-Analyse."""
        conditions = ["p.search_vector @@ plainto_tsquery('english', $1)"]
        params: list[Any] = [technology]
        idx = 2

        if start_year is not None:
            conditions.append(f"pc.pub_year >= ${idx}")
            params.append(start_year)
            idx += 1

        if end_year is not None:
            conditions.append(f"pc.pub_year <= ${idx}")
            params.append(end_year)
            idx += 1

        if european_only:
            conditions.append(f"p.applicant_countries && ${idx}::text[]")
            params.append(list(EU_EEA_COUNTRIES))
            idx += 1

        where = " AND ".join(conditions)

        sql = f"""
            SELECT pc.pub_year AS year,
                   pc.cpc_code AS cpc_codes
            FROM patent_schema.patents p
            JOIN patent_schema.patent_cpc pc
                ON pc.patent_id = p.id AND pc.pub_year = p.publication_year
            WHERE {where}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {"year": row["year"], "cpc_codes": row["cpc_codes"]}
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # Programm-/Instrumenten-Daten
    # -----------------------------------------------------------------------

    async def funding_by_instrument(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[dict[str, Any]]:
        """Foerderung nach Instrument/Programm pro Jahr."""
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
                   COALESCE(p.funding_scheme, 'UNKNOWN') AS scheme,
                   COUNT(*) AS count,
                   COALESCE(SUM(p.ec_max_contribution), 0) AS funding
            FROM cordis_schema.projects p
            WHERE {where}
              AND p.start_date IS NOT NULL
            GROUP BY year, scheme
            ORDER BY year, count DESC
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {
                    "year": row["year"],
                    "scheme": row["scheme"],
                    "count": row["count"],
                    "funding": float(row["funding"]),
                }
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # Health Check
    # -----------------------------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        """Datenbank-Health-Check."""
        async with self._pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            return {"status": "healthy", "pg_version": version}
