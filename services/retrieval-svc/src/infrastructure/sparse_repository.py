"""SparseSearchRepository — BM25/Full-Text-Suche ueber PostgreSQL tsvector.

Fuehrt pro Quelle (patents, projects, papers) eine Full-Text-Suche
mit ts_rank_cd durch und gibt RetrievedDoc-Instanzen zurueck.
"""
from __future__ import annotations

from typing import Any

import asyncpg
import structlog

from src.domain.ports import RetrievedDoc, SparseSearchPort

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Source-spezifische SQL-Queries: BM25/Full-Text via ts_rank_cd
# ---------------------------------------------------------------------------
_SPARSE_QUERIES: dict[str, str] = {
    "patents": """
        SELECT id::text AS source_id,
               title,
               title AS text_snippet,
               ts_rank_cd(search_vector, plainto_tsquery('english', $1)) AS rank,
               publication_year::text AS year,
               country
        FROM patent_schema.patents
        WHERE search_vector @@ plainto_tsquery('english', $1)
        ORDER BY rank DESC
        LIMIT $2
    """,
    "projects": """
        SELECT id::text AS source_id,
               title,
               COALESCE(objective, title) AS text_snippet,
               ts_rank_cd(search_vector, plainto_tsquery('english', $1)) AS rank,
               start_date::text AS year,
               '' AS country
        FROM cordis_schema.projects
        WHERE search_vector @@ plainto_tsquery('english', $1)
        ORDER BY rank DESC
        LIMIT $2
    """,
    "papers": """
        SELECT id::text AS source_id,
               title,
               title AS text_snippet,
               ts_rank_cd(search_vector, plainto_tsquery('english', $1)) AS rank,
               year::text AS year,
               '' AS country
        FROM research_schema.papers
        WHERE search_vector @@ plainto_tsquery('english', $1)
        ORDER BY rank DESC
        LIMIT $2
    """,
}

# Mapping fuer Singularisierung der Quellnamen in Ergebnissen
_SOURCE_SINGULAR: dict[str, str] = {
    "patents": "patent",
    "projects": "project",
    "papers": "paper",
}


class SparseSearchRepository(SparseSearchPort):
    """Async PostgreSQL-Zugriff fuer BM25/Full-Text-Suche via tsvector."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def search(
        self,
        query: str,
        sources: list[str],
        top_k: int,
    ) -> list[RetrievedDoc]:
        """Fuehrt BM25/Full-Text-Suche ueber angegebene Quellen durch.

        Args:
            query: Suchbegriff fuer Full-Text-Suche
            sources: Liste der zu durchsuchenden Quellen
            top_k: Maximale Anzahl Ergebnisse pro Quelle

        Returns:
            Liste von RetrievedDoc-Instanzen mit ts_rank_cd als similarity_score
        """
        results: list[RetrievedDoc] = []

        for source in sources:
            sql = _SPARSE_QUERIES.get(source)
            if sql is None:
                logger.warning(
                    "sparse_suche_unbekannte_quelle_uebersprungen",
                    source=source,
                    erlaubte_quellen=list(_SPARSE_QUERIES.keys()),
                )
                continue

            source_singular = _SOURCE_SINGULAR.get(source, source)

            async with self._pool.acquire() as conn:
                rows: list[Any] = await conn.fetch(sql, query, top_k)

            for row in rows:
                metadata: dict[str, str] = {}
                if row["year"]:
                    metadata["year"] = str(row["year"])
                if row["country"]:
                    metadata["country"] = str(row["country"])

                results.append(
                    RetrievedDoc(
                        source=source_singular,
                        source_id=str(row["source_id"]),
                        title=row["title"] or "",
                        text_snippet=row["text_snippet"] or "",
                        similarity_score=float(row["rank"]),
                        metadata=metadata,
                    )
                )

        return results
