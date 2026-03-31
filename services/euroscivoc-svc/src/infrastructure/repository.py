"""EuroSciVocRepository — PostgreSQL-Datenbankzugriff fuer UC10.

Abfragen fuer EuroSciVoc-Taxonomie-Klassifikationen aus CORDIS-Projekten.
CORDIS-Projekte koennen EuroSciVoc-Tags enthalten, die wissenschaftliche
Disziplinen nach dem OECD Frascati Manual kodieren.

Tabellenstruktur:
    cordis_schema.euroscivoc:           id, code, label_en, label_de, parent_code, level
    cordis_schema.project_euroscivoc:   project_id, euroscivoc_id (Junction)
"""

from __future__ import annotations

from typing import Any

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


class EuroSciVocRepository:
    """Async PostgreSQL-Zugriff fuer UC10 EuroSciVoc-Analysen."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def discipline_distribution(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """EuroSciVoc-Disziplinen pro Technologie aus CORDIS-Projekten."""
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
            SELECT esv.id AS id,
                   esv.label_en AS label,
                   esv.level AS level,
                   esv.parent_code,
                   COUNT(DISTINCT pe.project_id) AS project_count,
                   COUNT(DISTINCT pe.project_id)::float /
                       NULLIF((SELECT COUNT(DISTINCT p2.id)
                               FROM cordis_schema.projects p2
                               WHERE p2.search_vector @@ plainto_tsquery('english', $1)), 0) AS share
            FROM cordis_schema.projects p
            JOIN cordis_schema.project_euroscivoc pe ON pe.project_id = p.id
            JOIN cordis_schema.euroscivoc esv ON esv.id = pe.euroscivoc_id
            WHERE {where}
            GROUP BY esv.id, esv.label_en, esv.level, esv.parent_code
            ORDER BY project_count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {
                    "id": row["id"],
                    "label": row["label"],
                    "level": row["level"],
                    "parent_id": row["parent_code"] or "",
                    "project_count": row["project_count"],
                    "share": float(row["share"] or 0.0),
                }
                for row in rows
            ]

    async def discipline_trend(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[dict[str, Any]]:
        """Zeitliche Entwicklung der Disziplin-Verteilung."""
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
                   esv.label_en AS discipline,
                   esv.id AS discipline_id,
                   COUNT(DISTINCT pe.project_id) AS project_count
            FROM cordis_schema.projects p
            JOIN cordis_schema.project_euroscivoc pe ON pe.project_id = p.id
            JOIN cordis_schema.euroscivoc esv ON esv.id = pe.euroscivoc_id
            WHERE {where}
              AND p.start_date IS NOT NULL
            GROUP BY year, esv.label_en, esv.id
            ORDER BY year, project_count DESC
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {
                    "year": row["year"],
                    "discipline": row["discipline"],
                    "discipline_id": row["discipline_id"],
                    "publication_count": row["project_count"],
                }
                for row in rows
            ]

    async def cross_disciplinary_links(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Co-Occurrence von Disziplinen in Projekten."""
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
            SELECT e1.id AS discipline_a_id,
                   e1.label_en AS discipline_a_label,
                   e2.id AS discipline_b_id,
                   e2.label_en AS discipline_b_label,
                   COUNT(DISTINCT p.id) AS co_occurrence_count
            FROM cordis_schema.projects p
            JOIN cordis_schema.project_euroscivoc pe1 ON pe1.project_id = p.id
            JOIN cordis_schema.euroscivoc e1 ON e1.id = pe1.euroscivoc_id
            JOIN cordis_schema.project_euroscivoc pe2 ON pe2.project_id = p.id
            JOIN cordis_schema.euroscivoc e2 ON e2.id = pe2.euroscivoc_id
            WHERE {where}
              AND e1.id < e2.id
            GROUP BY e1.id, e1.label_en,
                     e2.id, e2.label_en
            ORDER BY co_occurrence_count DESC
            LIMIT ${limit_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [
                {
                    "discipline_a_id": row["discipline_a_id"],
                    "discipline_a_label": row["discipline_a_label"],
                    "discipline_b_id": row["discipline_b_id"],
                    "discipline_b_label": row["discipline_b_label"],
                    "co_occurrence_count": row["co_occurrence_count"],
                }
                for row in rows
            ]

    async def total_mapped_projects(self, technology: str) -> int:
        """Gesamtanzahl der Projekte mit EuroSciVoc-Mapping."""
        sql = """
            SELECT COUNT(DISTINCT pe.project_id)
            FROM cordis_schema.projects p
            JOIN cordis_schema.project_euroscivoc pe ON pe.project_id = p.id
            WHERE p.search_vector @@ plainto_tsquery('english', $1)
        """
        async with self._pool.acquire() as conn:
            return await conn.fetchval(sql, technology) or 0

    async def total_projects(self, technology: str) -> int:
        """Gesamtanzahl aller Projekte fuer eine Technologie."""
        sql = """
            SELECT COUNT(*)
            FROM cordis_schema.projects p
            WHERE p.search_vector @@ plainto_tsquery('english', $1)
        """
        async with self._pool.acquire() as conn:
            return await conn.fetchval(sql, technology) or 0

    async def health_check(self) -> dict[str, Any]:
        """Datenbank-Health-Check."""
        async with self._pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            return {"status": "healthy", "pg_version": version}
