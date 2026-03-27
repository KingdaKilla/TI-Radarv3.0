"""LandscapeRepository — PostgreSQL-Datenbankzugriff fuer UC1.

Migriert von SQLite (aiosqlite + FTS5) zu PostgreSQL (asyncpg + tsvector).
Nutzt den asyncpg Connection Pool fuer hochperformanten async Zugriff.

Zentrale Migrationsaenderungen gegenueber v1.0:
- FTS5 MATCH -> tsvector @@ plainto_tsquery('english', ...)
- SUBSTR(publication_date, 1, 4) -> publication_year (Partition-Key)
- WHERE country IN ('AT','BE',...) -> WHERE applicant_countries && '{AT,BE,...}'::text[]
- ? Placeholder -> $1, $2 (asyncpg Dollar-Notation)
- aiosqlite.connect() -> pool.acquire() (Connection Pool)
- Materialized Views wo verfuegbar (statt Raw-Table-Queries)

Datenbankschema (PostgreSQL):
- patent_schema.patents: 154.8M Zeilen, partitioniert nach publication_year
  Spalten: id, publication_number, country, title, publication_date,
  publication_year, family_id, applicant_countries (text[]), cpc_codes (text[]),
  search_vector (tsvector, GIN-indexiert)
- patent_schema.patent_cpc: 237M Zeilen, co-partitioniert nach pub_year
  Spalten: patent_id, cpc_code (VARCHAR(8)), pub_year
- patent_schema.cpc_descriptions: ~670 Eintraege (statische Referenztabelle)
  Spalten: code, section, class_code, description_en, description_de
- cordis_schema.projects: 80.5K Zeilen
  Spalten: id, framework, acronym, title, objective, start_date, end_date,
  total_cost, ec_max_contribution, funding_scheme, search_vector
- cordis_schema.organizations: 438K Zeilen
  Spalten: id, project_id, name, country, city, role, ec_contribution
"""

from __future__ import annotations

from typing import Any

import asyncpg
import structlog

from shared.domain.result_types import CountryCount, CpcCount, FundingYear, YearCount

logger = structlog.get_logger(__name__)

# EU/EEA-Laendercodes fuer european_only-Filter
EU_EEA_COUNTRIES: frozenset[str] = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    # EEA (nicht EU)
    "IS", "LI", "NO",
    # Assoziierte (CH, UK)
    "CH", "GB",
})


class LandscapeRepository:
    """Async PostgreSQL-Zugriff fuer UC1 Landscape-Analysen.

    Alle Methoden verwenden den uebergebenen asyncpg Connection Pool.
    Queries nutzen PostgreSQL-spezifische Syntax:
    - tsvector @@ plainto_tsquery fuer Volltextsuche
    - $1, $2 fuer Parameter-Binding (SQL-Injection-Schutz)
    - text[] mit && und @> fuer Array-Operationen
    - Materialized Views fuer voraggregierte Daten

    Die Klasse implementiert das Repository-Pattern und kapselt alle
    SQL-Abfragen. Der Service-Layer (LandscapeServicer) ruft die
    Methoden parallel via asyncio.gather auf.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        """Repository initialisieren.

        Args:
            pool: asyncpg Connection Pool, erstellt in server.py.
        """
        self._pool = pool

    # -----------------------------------------------------------------------
    # Patent-Abfragen
    # -----------------------------------------------------------------------

    async def count_patents_by_year(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
    ) -> list[YearCount]:
        """Patentanzahl pro Jahr fuer eine Technologie.

        Nutzt tsvector-Volltextsuche auf patent_schema.patents.search_vector.
        Partition Pruning ueber publication_year (WHERE-Klausel).

        Args:
            technology: Suchbegriff fuer Volltextsuche (z.B. 'quantum computing').
            start_year: Erstes Jahr im Zeitraum (inklusiv). None = unbeschraenkt.
            end_year: Letztes Jahr im Zeitraum (inklusiv). None = unbeschraenkt.
            european_only: Nur Patente mit EU/EEA-Anmeldern beruecksichtigen.

        Returns:
            Liste von Dicts mit Schluessel 'year' (int) und 'count' (int),
            sortiert aufsteigend nach Jahr.
        """
        conditions = ["p.search_vector @@ plainto_tsquery('english', $1)"]
        params: list[Any] = [technology]
        idx = 2  # Naechster Parameter-Index

        if start_year is not None:
            conditions.append(f"p.publication_year >= ${idx}")
            params.append(start_year)
            idx += 1

        if end_year is not None:
            conditions.append(f"p.publication_year <= ${idx}")
            params.append(end_year)
            idx += 1

        if european_only:
            conditions.append(
                f"p.applicant_countries && ${idx}::text[]"
            )
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

        logger.debug(
            "query_patents_by_year",
            technology=technology,
            start_year=start_year,
            end_year=end_year,
            european_only=european_only,
        )

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [YearCount(year=row["year"], count=row["count"]) for row in rows]

    async def count_patents_by_country(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
        limit: int = 20,
    ) -> list[CountryCount]:
        """Patentanzahl pro Anmelder-Land fuer eine Technologie.

        Nutzt LATERAL unnest() auf applicant_countries (text[]-Array).
        Ersetzt die CSV-Parsing-Logik aus v1.0 (WHERE LIKE '%XX%').

        Args:
            technology: Suchbegriff fuer Volltextsuche.
            start_year: Erstes Jahr (inklusiv).
            end_year: Letztes Jahr (inklusiv).
            european_only: Nur EU/EEA-Laender zaehlen.
            limit: Maximale Anzahl Laender im Ergebnis (Top-N).

        Returns:
            Liste von Dicts mit 'country' (str, ISO-2) und 'count' (int),
            absteigend sortiert nach count.
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

        # EU-Filter: nur Patente mit mindestens einem EU-Anmelder
        if european_only:
            conditions.append(f"p.applicant_countries && ${idx}::text[]")
            params.append(list(EU_EEA_COUNTRIES))
            idx += 1

        where = " AND ".join(conditions)

        # EU-Filter auf das ungenestete Land (nur EU-Laender zaehlen)
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

        logger.debug(
            "query_patents_by_country",
            technology=technology,
            european_only=european_only,
            limit=limit,
        )

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [CountryCount(country=row["country"], count=row["count"]) for row in rows]

    async def top_cpc_codes(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 15,
    ) -> list[CpcCount]:
        """Top-CPC-Codes fuer eine Technologie.

        Nutzt die normalisierte patent_cpc-Tabelle (237M Zeilen) und joined
        mit cpc_descriptions (~670 Eintraege) fuer menschenlesbare Beschreibungen.
        Co-Partition patent_cpc.pub_year = patents.publication_year ermoeglicht
        effizientes Partition Pruning.

        Args:
            technology: Suchbegriff fuer Volltextsuche.
            start_year: Erstes Jahr (inklusiv).
            end_year: Letztes Jahr (inklusiv).
            limit: Maximale Anzahl CPC-Codes (Top-N).

        Returns:
            Liste von Dicts mit 'code' (str, z.B. 'H04W'),
            'description' (str, englisch) und 'count' (int),
            absteigend sortiert nach count.
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
        params.append(limit)
        limit_idx = idx

        # Fallback: wenn patent_cpc leer ist, direkt aus patents.cpc_codes lesen.
        # JOIN auf cpc_descriptions mit laengstem Praefix-Match (exact -> kuerzer).
        sql = f"""
            SELECT cpc.code,
                   COALESCE(cd_exact.description_en,
                            cd_prefix.description_en, '') AS description,
                   COUNT(DISTINCT p.id) AS count
            FROM patent_schema.patents p,
                 LATERAL unnest(p.cpc_codes) AS cpc(code)
            LEFT JOIN patent_schema.cpc_descriptions cd_exact
                ON cd_exact.code = cpc.code
            LEFT JOIN LATERAL (
                SELECT description_en FROM patent_schema.cpc_descriptions
                WHERE cpc.code LIKE code || '%'
                ORDER BY length(code) DESC
                LIMIT 1
            ) cd_prefix ON cd_exact.code IS NULL
            WHERE {where}
              AND p.cpc_codes IS NOT NULL
              AND array_length(p.cpc_codes, 1) > 0
            GROUP BY cpc.code, COALESCE(cd_exact.description_en, cd_prefix.description_en, '')
            ORDER BY count DESC
            LIMIT ${limit_idx}
        """

        logger.debug(
            "query_top_cpc_codes",
            technology=technology,
            limit=limit,
        )

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                CpcCount(code=row["code"], description=row["description"], count=row["count"])
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # CORDIS-Projekt-Abfragen
    # -----------------------------------------------------------------------

    async def count_projects_by_year(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[YearCount]:
        """Projektanzahl pro Startjahr fuer eine Technologie.

        CORDIS-Projekte sind per Definition EU-finanziert,
        daher kein european_only-Filter noetig.

        Args:
            technology: Suchbegriff fuer Volltextsuche.
            start_year: Erstes Jahr (inklusiv).
            end_year: Letztes Jahr (inklusiv).

        Returns:
            Liste von Dicts mit 'year' (int) und 'count' (int),
            sortiert aufsteigend nach Jahr.
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

        where = " AND ".join(conditions)

        sql = f"""
            SELECT EXTRACT(YEAR FROM p.start_date)::int AS year,
                   COUNT(*) AS count
            FROM cordis_schema.projects p
            WHERE {where}
              AND p.start_date IS NOT NULL
            GROUP BY year
            ORDER BY year
        """

        logger.debug(
            "query_projects_by_year",
            technology=technology,
            start_year=start_year,
            end_year=end_year,
        )

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [YearCount(year=row["year"], count=row["count"]) for row in rows]

    async def count_projects_by_country(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
        limit: int = 20,
    ) -> list[CountryCount]:
        """Projektanzahl pro Land (ueber cordis_schema.organizations).

        Zaehlt Projekte pro Organisation-Land via JOIN. Ein Projekt kann
        mehrere Laender haben (Konsortium), daher COUNT(DISTINCT project_id).

        Args:
            technology: Suchbegriff fuer Volltextsuche.
            start_year: Erstes Jahr (inklusiv).
            end_year: Letztes Jahr (inklusiv).
            european_only: Nur EU/EEA-Laender beruecksichtigen.
            limit: Maximale Anzahl Laender (Top-N).

        Returns:
            Liste von Dicts mit 'country' (str, ISO-2) und 'count' (int),
            absteigend sortiert nach count.
        """
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
              AND o.country IS NOT NULL
              AND o.country != ''
            GROUP BY o.country
            ORDER BY count DESC
            LIMIT ${limit_idx}
        """

        logger.debug(
            "query_projects_by_country",
            technology=technology,
            european_only=european_only,
            limit=limit,
        )

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [CountryCount(country=row["country"], count=row["count"]) for row in rows]

    async def funding_by_year(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[FundingYear]:
        """EU-Foerderung (ec_max_contribution) pro Jahr fuer eine Technologie.

        Aggregiert ueber cordis_schema.projects. CORDIS-Projekte sind per
        Definition EU-finanziert, daher kein european_only-Filter noetig.

        Args:
            technology: Suchbegriff fuer Volltextsuche.
            start_year: Erstes Jahr (inklusiv).
            end_year: Letztes Jahr (inklusiv).

        Returns:
            Liste von Dicts mit 'year' (int), 'funding' (float, Euro)
            und 'count' (int, Anzahl gefoerderter Projekte),
            sortiert aufsteigend nach Jahr.
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

        logger.debug(
            "query_funding_by_year",
            technology=technology,
            start_year=start_year,
            end_year=end_year,
        )

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                FundingYear(year=row["year"], funding=float(row["funding"]), count=row["count"])
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # Materialized-View-basierte Abfragen (fuer voraggregierte Daten)
    # -----------------------------------------------------------------------

    async def patent_counts_from_mv(
        self,
        cpc_code: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[YearCount]:
        """Patentanzahl pro Jahr aus Materialized View (CPC-basiert).

        Nutzt cross_schema.mv_yearly_tech_counts — schneller als
        Live-Query, aber nur fuer bekannte CPC-Codes verfuegbar.
        Ideal fuer Dashboard-Aggregationen ohne Freitext-Suche.

        Args:
            cpc_code: CPC-Code (z.B. 'H04W') als Technologie-Identifikator.
            start_year: Erstes Jahr (inklusiv).
            end_year: Letztes Jahr (inklusiv).

        Returns:
            Liste von Dicts mit 'year' (int) und 'count' (int).
        """
        conditions = ["technology = $1"]
        params: list[Any] = [cpc_code]
        idx = 2

        if start_year is not None:
            conditions.append(f"year >= ${idx}")
            params.append(start_year)
            idx += 1

        if end_year is not None:
            conditions.append(f"year <= ${idx}")
            params.append(end_year)
            idx += 1

        where = " AND ".join(conditions)

        sql = f"""
            SELECT year, patent_count AS count
            FROM cross_schema.mv_yearly_tech_counts
            WHERE {where}
            ORDER BY year
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [YearCount(year=row["year"], count=row["count"]) for row in rows]

    async def country_distribution_from_mv(
        self,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
        limit: int = 20,
    ) -> list[CountryCount]:
        """Laenderverteilung aus Materialized View.

        Nutzt cross_schema.mv_patent_country_distribution — voraggregiert
        aus dem unnest-Join, der bei 154M Zeilen teuer waere.

        Args:
            start_year: Erstes Jahr (inklusiv).
            end_year: Letztes Jahr (inklusiv).
            european_only: Nur EU/EEA-Laender beruecksichtigen.
            limit: Maximale Anzahl Laender.

        Returns:
            Liste von Dicts mit 'country' (str) und 'count' (int).
        """
        conditions: list[str] = []
        params: list[Any] = []
        idx = 1

        if start_year is not None:
            conditions.append(f"year >= ${idx}")
            params.append(start_year)
            idx += 1

        if end_year is not None:
            conditions.append(f"year <= ${idx}")
            params.append(end_year)
            idx += 1

        if european_only:
            conditions.append(f"country_code = ANY(${idx}::text[])")
            params.append(list(EU_EEA_COUNTRIES))
            idx += 1

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(limit)
        limit_idx = idx

        sql = f"""
            SELECT country_code AS country,
                   SUM(patent_count) AS count
            FROM cross_schema.mv_patent_country_distribution
            {where}
            GROUP BY country_code
            ORDER BY count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [CountryCount(country=row["country"], count=row["count"]) for row in rows]

    async def project_counts_from_mv(
        self,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[YearCount]:
        """Projektanzahl pro Jahr aus Materialized View.

        Nutzt cross_schema.mv_project_counts_by_year — aggregiert
        ueber alle Frameworks (FP7, H2020, HORIZON).

        Args:
            start_year: Erstes Jahr (inklusiv).
            end_year: Letztes Jahr (inklusiv).

        Returns:
            Liste von Dicts mit 'year' (int) und 'count' (int).
        """
        conditions: list[str] = []
        params: list[Any] = []
        idx = 1

        if start_year is not None:
            conditions.append(f"year >= ${idx}")
            params.append(start_year)
            idx += 1

        if end_year is not None:
            conditions.append(f"year <= ${idx}")
            params.append(end_year)
            idx += 1

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        sql = f"""
            SELECT year,
                   SUM(project_count) AS count
            FROM cross_schema.mv_project_counts_by_year
            {where}
            GROUP BY year
            ORDER BY year
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [YearCount(year=row["year"], count=row["count"]) for row in rows]

    # -----------------------------------------------------------------------
    # Health Check
    # -----------------------------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        """Datenbank-Health-Check: Verbindung und Basisdaten pruefen.

        Fuehrt leichtgewichtige Zaehlung durch, um sicherzustellen,
        dass die Schemas und Tabellen erreichbar sind.

        Returns:
            Dict mit 'status', 'pg_version', 'total_patents', 'total_projects'.
        """
        async with self._pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            patent_count = await conn.fetchval(
                "SELECT COUNT(*) FROM patent_schema.patents"
            )
            project_count = await conn.fetchval(
                "SELECT COUNT(*) FROM cordis_schema.projects"
            )
            return {
                "status": "healthy",
                "pg_version": version,
                "total_patents": patent_count,
                "total_projects": project_count,
            }
