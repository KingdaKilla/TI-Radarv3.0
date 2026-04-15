"""CpcFlowRepository — PostgreSQL-Datenbankzugriff fuer UC5.

Liefert CPC-Co-Klassifikationsdaten fuer Jaccard-Analyse.
Zwei Pfade:
1. SQL-nativ: Direkte Aggregation ueber patent_cpc Tabelle
2. Rohdaten: CPC-Codes als Komma-separierte Strings (Fallback)

Queries nutzen PostgreSQL-spezifische Syntax:
- tsvector @@ plainto_tsquery fuer Volltextsuche
- LEFT(cpc_code, n) fuer CPC-Level-Truncation
- Self-Join auf patent_cpc fuer Co-Occurrence-Berechnung
"""

from __future__ import annotations

from typing import Any

import asyncpg
import structlog

# --- Shared Domain fuer Jaccard-Berechnung ---
try:
    from shared.domain.cpc_flow import build_jaccard_from_sql
except ImportError:
    from src.domain.metrics import build_jaccard_from_sql  # type: ignore[attr-defined]

logger = structlog.get_logger(__name__)


class CpcFlowRepository:
    """Async PostgreSQL-Zugriff fuer UC5 CPC Flow-Analysen."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # -----------------------------------------------------------------------
    # Schema-Pruefung
    # -----------------------------------------------------------------------

    async def has_cpc_table(self) -> bool:
        """Pruefen ob die normalisierte patent_cpc Tabelle existiert.

        Hinweis: Auch wenn patent_cpc leer ist, funktioniert der SQL-Pfad,
        da _top_cpc_codes und _cpc_pair_counts via LATERAL unnest(p.cpc_codes)
        direkt auf das Array in der patents-Tabelle zugreifen.
        """
        sql = """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'patent_schema'
                  AND table_name = 'patent_cpc'
            )
        """
        async with self._pool.acquire() as conn:
            return bool(await conn.fetchval(sql))

    # -----------------------------------------------------------------------
    # SQL-nativer Pfad: Jaccard-Berechnung via patent_cpc
    # -----------------------------------------------------------------------

    async def compute_cpc_jaccard(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        top_n: int = 15,
        cpc_level: int = 4,
    ) -> dict[str, Any]:
        """SQL-native Jaccard-Berechnung fuer Top-CPC-Codes.

        Fuehrt drei Schritte aus:
        1. Top-N CPC-Codes nach Patent-Haeufigkeit ermitteln
        2. Einzelne Code-Counts abfragen
        3. Paarweise Co-Occurrence zaehlen
        4. Jaccard-Matrix in Python berechnen (via shared.domain.cpc_flow)
        """
        # Schritt 1: Top CPC-Codes
        top_codes_rows = await self._top_cpc_codes(
            technology, start_year=start_year, end_year=end_year,
            cpc_level=cpc_level, limit=top_n,
        )

        if len(top_codes_rows) < 2:
            return {
                "labels": [r["code"] for r in top_codes_rows],
                "matrix": [],
                "total_connections": 0,
                "total_patents": sum(r["count"] for r in top_codes_rows),
                "year_data": {},
            }

        top_codes = [r["code"] for r in top_codes_rows]
        code_counts = {r["code"]: r["count"] for r in top_codes_rows}
        total_patents = sum(code_counts.values())

        # Schritt 2: Paarweise Co-Occurrence
        pair_rows = await self._cpc_pair_counts(
            technology, top_codes, start_year=start_year, end_year=end_year,
            cpc_level=cpc_level,
        )

        pair_counts = [(r["code_a"], r["code_b"], r["co_count"]) for r in pair_rows]

        # Schritt 3: Jaccard-Matrix berechnen
        matrix, total_connections = build_jaccard_from_sql(
            top_codes, code_counts, pair_counts,
        )

        return {
            "labels": top_codes,
            "matrix": matrix,
            "total_connections": total_connections,
            "total_patents": total_patents,
            "code_counts": code_counts,
            "year_data": {},
        }

    async def _top_cpc_codes(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        cpc_level: int = 4,
        limit: int = 15,
    ) -> list[dict[str, Any]]:
        """Top CPC-Codes nach Patentanzahl fuer eine Technologie."""
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
        params.append(cpc_level)
        level_idx = idx
        idx += 1
        params.append(limit)
        limit_idx = idx

        sql = f"""
            SELECT LEFT(cpc.cpc_code, ${level_idx}) AS code,
                   COUNT(DISTINCT p.id) AS count
            FROM patent_schema.patents p,
                 LATERAL unnest(p.cpc_codes) AS cpc(cpc_code)
            WHERE {where}
              AND p.cpc_codes IS NOT NULL
              AND array_length(p.cpc_codes, 1) > 0
            GROUP BY LEFT(cpc.cpc_code, ${level_idx})
            ORDER BY count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [{"code": row["code"], "count": row["count"]} for row in rows]

    async def _cpc_pair_counts(
        self,
        technology: str,
        top_codes: list[str],
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        cpc_level: int = 4,
    ) -> list[dict[str, Any]]:
        """Paarweise Co-Occurrence der Top-CPC-Codes zaehlen.

        Self-Join auf patent_cpc: Patente die beide Codes tragen.
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

        # Top-Codes als Array-Parameter
        params.append(top_codes)
        codes_idx = idx
        idx += 1

        params.append(cpc_level)
        level_idx = idx

        where = " AND ".join(conditions)

        sql = f"""
            SELECT LEFT(c1.cpc_code, ${level_idx}) AS code_a,
                   LEFT(c2.cpc_code, ${level_idx}) AS code_b,
                   COUNT(DISTINCT p.id) AS co_count
            FROM patent_schema.patents p,
                 LATERAL unnest(p.cpc_codes) AS c1(cpc_code),
                 LATERAL unnest(p.cpc_codes) AS c2(cpc_code)
            WHERE {where}
              AND p.cpc_codes IS NOT NULL
              AND array_length(p.cpc_codes, 1) > 1
              AND LEFT(c1.cpc_code, ${level_idx}) = ANY(${codes_idx}::text[])
              AND LEFT(c2.cpc_code, ${level_idx}) = ANY(${codes_idx}::text[])
              AND LEFT(c1.cpc_code, ${level_idx}) < LEFT(c2.cpc_code, ${level_idx})
            GROUP BY LEFT(c1.cpc_code, ${level_idx}), LEFT(c2.cpc_code, ${level_idx})
            HAVING COUNT(DISTINCT p.id) >= 1
            ORDER BY co_count DESC
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {"code_a": row["code_a"], "code_b": row["code_b"], "co_count": row["co_count"]}
                for row in rows
            ]

    # -----------------------------------------------------------------------
    # Python-Pfad: Rohdaten laden
    # -----------------------------------------------------------------------

    async def get_cpc_codes_raw(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 50_000,
    ) -> list[dict[str, Any]]:
        """CPC-Codes als Rohdaten laden (Fallback wenn patent_cpc nicht existiert).

        Gibt Patente mit komma-separierten CPC-Codes zurueck.
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

        sql = f"""
            SELECT p.cpc_codes,
                   p.publication_year AS year
            FROM patent_schema.patents p
            WHERE {where}
              AND p.cpc_codes IS NOT NULL
              AND array_length(p.cpc_codes, 1) > 0
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {"cpc_codes": row["cpc_codes"], "year": row["year"]}
                for row in rows
            ]
