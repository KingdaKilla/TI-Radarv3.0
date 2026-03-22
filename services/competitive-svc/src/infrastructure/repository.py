"""CompetitiveRepository — PostgreSQL-Datenbankzugriff fuer UC3.

Liefert Patent-Anmelder, CORDIS-Organisationen und Netzwerk-Kanten
fuer die Wettbewerbs-Analyse.

Queries nutzen PostgreSQL-spezifische Syntax:
- tsvector @@ plainto_tsquery fuer Volltextsuche
- $1, $2 fuer Parameter-Binding
- text[] mit && fuer Array-Operationen (european_only-Filter)

Entity Resolution (optional):
- entity_schema.unified_actors + entity_schema.actor_source_mappings
- Mappt Original-Namen (Patent-Anmelder, CORDIS-Organisationen)
  auf kanonische, deduplizierte Akteur-Namen
- Graceful Degradation: Leere Liste falls entity-Tabellen nicht existieren
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
    "CH", "GB",
})


class CompetitiveRepository:
    """Async PostgreSQL-Zugriff fuer UC3 Competitive Intelligence."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # -----------------------------------------------------------------------
    # Patent-Anmelder
    # -----------------------------------------------------------------------

    async def top_patent_applicants(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Top Patent-Anmelder fuer eine Technologie.

        Nutzt die unnest()-Funktion auf applicant_names (text[]-Array).
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
        params.append(limit)
        limit_idx = idx

        sql = f"""
            SELECT trim(a.applicant_name) AS name,
                   COUNT(*) AS count
            FROM patent_schema.patents p,
                 LATERAL string_to_table(p.applicant_names, '; ') AS a(applicant_name)
            WHERE {where}
              AND p.applicant_names IS NOT NULL
              AND length(p.applicant_names) > 0
            GROUP BY trim(a.applicant_name)
            ORDER BY count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [{"name": row["name"], "count": row["count"]} for row in rows]

    # -----------------------------------------------------------------------
    # CORDIS-Organisationen
    # -----------------------------------------------------------------------

    async def top_cordis_organizations(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Top CORDIS-Organisationen mit Land-Info fuer eine Technologie."""
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
                   COUNT(DISTINCT o.project_id) AS count
            FROM cordis_schema.projects p
            JOIN cordis_schema.organizations o ON o.project_id = p.id
            WHERE {where}
              AND o.name IS NOT NULL
              AND o.name != ''
            GROUP BY o.name, o.country
            ORDER BY count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {"name": row["name"], "country": row["country"], "count": row["count"]}
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # Netzwerk-Kanten: Co-Patent-Anmelder
    # -----------------------------------------------------------------------

    async def co_patent_applicants(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Co-Patent-Anmelder-Paare (Akteure die gemeinsam auf Patenten stehen)."""
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
            SELECT trim(a1.applicant_name) AS actor_a,
                   trim(a2.applicant_name) AS actor_b,
                   COUNT(*) AS co_count
            FROM patent_schema.patents p,
                 LATERAL string_to_table(p.applicant_names, '; ') WITH ORDINALITY AS a1(applicant_name, ord1),
                 LATERAL string_to_table(p.applicant_names, '; ') WITH ORDINALITY AS a2(applicant_name, ord2)
            WHERE {where}
              AND p.applicant_names LIKE '%;%'
              AND a1.ord1 < a2.ord2
            GROUP BY trim(a1.applicant_name), trim(a2.applicant_name)
            HAVING COUNT(*) >= 2
            ORDER BY co_count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {"actor_a": row["actor_a"], "actor_b": row["actor_b"], "co_count": row["co_count"]}
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # Netzwerk-Kanten: CORDIS Co-Partizipation
    # -----------------------------------------------------------------------

    async def co_project_participants(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Co-Partizipation-Paare (Organisationen im selben CORDIS-Projekt)."""
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
            SELECT o1.name AS actor_a,
                   o2.name AS actor_b,
                   COUNT(DISTINCT p.id) AS co_count
            FROM cordis_schema.projects p
            JOIN cordis_schema.organizations o1 ON o1.project_id = p.id
            JOIN cordis_schema.organizations o2 ON o2.project_id = p.id
            WHERE {where}
              AND o1.name < o2.name
              AND o1.name IS NOT NULL AND o1.name != ''
              AND o2.name IS NOT NULL AND o2.name != ''
            GROUP BY o1.name, o2.name
            HAVING COUNT(DISTINCT p.id) >= 2
            ORDER BY co_count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {"actor_a": row["actor_a"], "actor_b": row["actor_b"], "co_count": row["co_count"]}
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # Entity Resolution: Unified Actors
    # -----------------------------------------------------------------------

    async def _entity_tables_exist(self) -> bool:
        """Pruefen ob die entity_schema-Tabellen vorhanden und befuellt sind.

        Returns:
            True wenn entity_schema.unified_actors existiert und Eintraege hat.
        """
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'entity_schema'
                          AND table_name = 'unified_actors'
                    ) AS table_exists
                """)
                if not row or not row["table_exists"]:
                    return False

                # Pruefen ob die Tabelle auch Daten hat
                count_row = await conn.fetchrow(
                    "SELECT COUNT(*) AS cnt FROM entity_schema.unified_actors"
                )
                return bool(count_row and count_row["cnt"] > 0)

        except Exception as exc:
            logger.debug(
                "entity_tabellen_pruefung_fehlgeschlagen",
                error=str(exc),
            )
            return False

    async def top_unified_actors(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Top Akteure ueber Entity Resolution (unified_actors).

        Mappt Original-Namen aus Patent-Anmeldern und CORDIS-Organisationen
        auf kanonische, deduplizierte Akteur-Namen via
        entity_schema.actor_source_mappings -> entity_schema.unified_actors.

        Aggregiert Patent- und Projekt-Counts pro kanonischem Akteur.
        Faellt graceful auf leere Liste zurueck wenn entity-Tabellen
        nicht existieren oder leer sind.

        Schema:
            entity_schema.unified_actors (
                id UUID PK, canonical_name, country CHAR(2),
                actor_type VARCHAR(20)
            )
            entity_schema.actor_source_mappings (
                unified_actor_id FK, source_type VARCHAR(20),
                source_id TEXT, source_name TEXT, confidence REAL
            )

        Args:
            technology: Technologie-Suchbegriff fuer Volltextsuche.
            start_year: Optionaler Start-Jahresfilter.
            end_year: Optionaler End-Jahresfilter.
            european_only: Nur EU/EEA-Laender beruecksichtigen.
            limit: Maximale Anzahl zurueckgegebener Akteure.

        Returns:
            Liste von Dicts mit canonical_name, country_code, actor_type,
            patent_count, project_count, total_count, confidence.
            Leere Liste bei Fehler oder fehlenden entity-Tabellen.
        """
        # Graceful Degradation: entity-Tabellen pruefen
        if not await self._entity_tables_exist():
            logger.info(
                "entity_resolution_nicht_verfuegbar",
                grund="Tabellen nicht vorhanden oder leer",
            )
            return []

        try:
            return await self._query_unified_actors(
                technology,
                start_year=start_year,
                end_year=end_year,
                european_only=european_only,
                limit=limit,
            )
        except Exception as exc:
            logger.warning(
                "entity_resolution_fehlgeschlagen",
                error=str(exc),
                technology=technology,
            )
            return []

    async def _query_unified_actors(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Interne Query fuer unified actors — Patent + CORDIS Counts.

        Verwendet zwei CTEs:
        1. patent_counts: Patent-Anmelder-Namen -> unified_actors via Mapping
        2. cordis_counts: CORDIS-Org-Namen -> unified_actors via Mapping
        Dann: Aggregation nach canonical_name ueber unified_actors.
        """
        # --- Parameter-Index-Verwaltung ---
        params: list[Any] = [technology]
        idx = 2

        # --- Patent-WHERE-Bedingungen ---
        patent_conditions = ["p.search_vector @@ plainto_tsquery('english', $1)"]
        patent_conditions.append("p.applicant_names IS NOT NULL")
        patent_conditions.append("length(p.applicant_names) > 0")

        if start_year is not None:
            patent_conditions.append(f"p.publication_year >= ${idx}")
            params.append(start_year)
            idx += 1

        if end_year is not None:
            patent_conditions.append(f"p.publication_year <= ${idx}")
            params.append(end_year)
            idx += 1

        if european_only:
            patent_conditions.append(f"p.applicant_countries && ${idx}::text[]")
            params.append(list(EU_EEA_COUNTRIES))
            idx += 1

        patent_where = " AND ".join(patent_conditions)

        # --- CORDIS-WHERE-Bedingungen (nutzt gleichen $1 fuer Technologie) ---
        cordis_conditions = [
            "cp.search_vector @@ plainto_tsquery('english', $1)"
        ]

        # Start/End-Year fuer CORDIS: eigene Param-Indizes
        if start_year is not None:
            cordis_conditions.append(f"cp.start_date >= make_date(${idx}, 1, 1)")
            params.append(start_year)
            idx += 1

        if end_year is not None:
            cordis_conditions.append(f"cp.start_date <= make_date(${idx}, 12, 31)")
            params.append(end_year)
            idx += 1

        cordis_where = " AND ".join(cordis_conditions)

        # --- European-only Filter fuer unified_actors ---
        unified_conditions: list[str] = []
        if european_only:
            unified_conditions.append(f"ua.country = ANY(${idx}::text[])")
            params.append(list(EU_EEA_COUNTRIES))
            idx += 1

        unified_where = (" AND " + " AND ".join(unified_conditions)) if unified_conditions else ""

        # Limit-Parameter
        params.append(limit)
        limit_idx = idx

        sql = f"""
            WITH patent_counts AS (
                -- Patent-Anmelder -> unified_actors via source_mappings
                SELECT
                    asm.unified_actor_id,
                    COUNT(*) AS patent_count
                FROM patent_schema.patents p,
                     LATERAL string_to_table(p.applicant_names, '; ') AS a(applicant_name)
                JOIN entity_schema.actor_source_mappings asm
                    ON UPPER(TRIM(asm.source_name)) = UPPER(TRIM(a.applicant_name))
                    AND asm.source_type = 'epo_applicant'
                WHERE {patent_where}
                GROUP BY asm.unified_actor_id
            ),
            cordis_counts AS (
                -- CORDIS-Organisationen -> unified_actors via source_mappings
                SELECT
                    asm.unified_actor_id,
                    COUNT(DISTINCT co.project_id) AS project_count
                FROM cordis_schema.projects cp
                JOIN cordis_schema.organizations co ON co.project_id = cp.id
                JOIN entity_schema.actor_source_mappings asm
                    ON UPPER(TRIM(asm.source_name)) = UPPER(TRIM(co.name))
                    AND asm.source_type = 'cordis_org'
                WHERE {cordis_where}
                  AND co.name IS NOT NULL
                  AND co.name != ''
                GROUP BY asm.unified_actor_id
            )
            SELECT
                ua.canonical_name,
                ua.country AS country_code,
                ua.actor_type,
                asm_conf.avg_confidence AS confidence,
                COALESCE(pc.patent_count, 0)  AS patent_count,
                COALESCE(cc.project_count, 0) AS project_count,
                COALESCE(pc.patent_count, 0) + COALESCE(cc.project_count, 0) AS total_count
            FROM entity_schema.unified_actors ua
            LEFT JOIN patent_counts pc ON pc.unified_actor_id = ua.id
            LEFT JOIN cordis_counts cc ON cc.unified_actor_id = ua.id
            LEFT JOIN LATERAL (
                SELECT AVG(confidence) AS avg_confidence
                FROM entity_schema.actor_source_mappings
                WHERE unified_actor_id = ua.id
            ) asm_conf ON true
            WHERE (pc.patent_count IS NOT NULL OR cc.project_count IS NOT NULL)
                {unified_where}
            ORDER BY total_count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        return [
            {
                "name": row["canonical_name"],
                "country_code": row["country_code"] or "",
                "actor_type": row["actor_type"] or "",
                "patent_count": row["patent_count"],
                "project_count": row["project_count"],
                "total_count": row["total_count"],
                "confidence": float(row["confidence"]) if row["confidence"] else 0.0,
            }
            for row in rows
        ]
