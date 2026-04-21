"""EmbeddingRepository — PostgreSQL-Datenbankzugriff fuer Embedding-Service.

Liest Dokumente ohne Embedding aus drei Quellen (patents, projects, papers)
und schreibt die erzeugten Vektoren zurueck in die jeweilige Tabelle.
"""
from __future__ import annotations

from typing import Any

import asyncpg
import structlog

from src.domain.ports import ChunkRepositoryPort, EmbeddingRepositoryPort

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Source-Konfiguration: Mapping von Source-Name auf DB-Tabelle/Spalten
# ---------------------------------------------------------------------------
_SOURCE_CONFIG: dict[str, dict[str, str]] = {
    "patents": {
        "table": "patent_schema.patents",
        "id_col": "id",
        "text_expr": "title",
        "embedding_col": "title_embedding",
        "text_not_null": "title IS NOT NULL",
        "year_col": "publication_year",
    },
    "projects": {
        "table": "cordis_schema.projects",
        "id_col": "id",
        "text_expr": "COALESCE(title, '') || ' ' || COALESCE(objective, '')",
        "embedding_col": "content_embedding",
        "text_not_null": "(title IS NOT NULL OR objective IS NOT NULL)",
        "year_col": "",
    },
    "papers": {
        "table": "research_schema.papers",
        "id_col": "id",
        "text_expr": "title",
        "embedding_col": "abstract_embedding",
        "text_not_null": "title IS NOT NULL",
        "year_col": "",
    },
}


def _get_config(source: str) -> dict[str, str]:
    """Source-Konfiguration lesen oder ValueError werfen."""
    if source not in _SOURCE_CONFIG:
        raise ValueError(
            f"Unbekannte Quelle: '{source}'. "
            f"Erlaubt: {', '.join(sorted(_SOURCE_CONFIG.keys()))}"
        )
    return _SOURCE_CONFIG[source]


class EmbeddingRepository(EmbeddingRepositoryPort):
    """Async PostgreSQL-Zugriff fuer Embedding-Operationen."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # -----------------------------------------------------------------------
    # Unembedded Dokumente lesen
    # -----------------------------------------------------------------------

    async def fetch_unembedded(
        self, source: str, batch_size: int, year_from: int | None = None,
    ) -> list[tuple[int, str]]:
        """Liest Dokumente ohne Embedding (id, text).

        Args:
            source: "patents", "projects" oder "papers"
            batch_size: Maximale Anzahl Dokumente pro Batch
            year_from: Optional — nur fuer patents: Filter publication_year >= year_from
        """
        cfg = _get_config(source)

        conditions = [
            f"{cfg['embedding_col']} IS NULL",
            cfg["text_not_null"],
        ]
        params: list[Any] = []
        idx = 1

        if year_from is not None and cfg["year_col"]:
            conditions.append(f"{cfg['year_col']} >= ${idx}")
            params.append(year_from)
            idx += 1

        params.append(batch_size)
        where = " AND ".join(conditions)

        sql = f"""
            SELECT {cfg['id_col']}, {cfg['text_expr']} AS text
            FROM {cfg['table']}
            WHERE {where}
            LIMIT ${idx}
        """

        logger.debug(
            "fetch_unembedded",
            source=source,
            batch_size=batch_size,
            year_from=year_from,
        )

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [(row["id"], row["text"]) for row in rows]

    # -----------------------------------------------------------------------
    # Embeddings schreiben
    # -----------------------------------------------------------------------

    async def store_embeddings(
        self, source: str, embeddings: list[tuple[int, list[float]]],
    ) -> int:
        """Schreibt Embeddings in die DB via executemany.

        Args:
            source: "patents", "projects" oder "papers"
            embeddings: Liste von (id, vector) Tupeln

        Returns:
            Anzahl geschriebener Rows
        """
        if not embeddings:
            return 0

        cfg = _get_config(source)

        sql = f"""
            UPDATE {cfg['table']}
            SET {cfg['embedding_col']} = $2
            WHERE {cfg['id_col']} = $1
        """

        # asyncpg executemany erwartet list of tuples/lists
        data = [(row_id, vector) for row_id, vector in embeddings]

        async with self._pool.acquire() as conn:
            await conn.executemany(sql, data)

        stored = len(embeddings)
        logger.info(
            "embeddings_gespeichert",
            source=source,
            count=stored,
        )
        return stored

    # -----------------------------------------------------------------------
    # Status-Abfrage
    # -----------------------------------------------------------------------

    async def count_status(self, source: str) -> tuple[int, int]:
        """Gibt (total, embedded) Counts zurueck.

        Args:
            source: "patents", "projects" oder "papers"

        Returns:
            Tuple (total_with_text, already_embedded)
        """
        cfg = _get_config(source)

        sql = f"""
            SELECT
                COUNT(*) FILTER (WHERE {cfg['text_not_null']}) AS total,
                COUNT(*) FILTER (WHERE {cfg['embedding_col']} IS NOT NULL) AS embedded
            FROM {cfg['table']}
        """

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql)
            return (row["total"], row["embedded"])


# ===========================================================================
# ChunkRepository — Chunk-basierte Persistenz fuer document_chunks
# ===========================================================================

class ChunkRepository(ChunkRepositoryPort):
    """Async PostgreSQL-Zugriff fuer Chunk-Operationen auf cross_schema.document_chunks."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # -----------------------------------------------------------------------
    # Unchunked Dokumente lesen
    # -----------------------------------------------------------------------

    async def fetch_unchunked_docs(
        self, source: str, batch_size: int, year_from: int | None = None,
    ) -> list[tuple[str, str]]:
        """Liest Dokumente ohne Chunks (source_id, text).

        Gibt Dokumente zurueck, deren ID noch nicht in document_chunks vorkommt.

        Args:
            source: "patents", "projects" oder "papers"
            batch_size: Maximale Anzahl Dokumente pro Batch
            year_from: Optional — nur fuer patents: Filter publication_year >= year_from
        """
        cfg = _get_config(source)

        conditions = [cfg["text_not_null"]]
        params: list[Any] = [source]
        idx = 2  # $1 = source (fuer Subquery)

        if year_from is not None and cfg["year_col"]:
            conditions.append(f"{cfg['year_col']} >= ${idx}")
            params.append(year_from)
            idx += 1

        params.append(batch_size)
        where = " AND ".join(conditions)

        sql = f"""
            SELECT CAST({cfg['id_col']} AS TEXT) AS source_id,
                   {cfg['text_expr']} AS text
            FROM {cfg['table']}
            WHERE {where}
              AND CAST({cfg['id_col']} AS TEXT) NOT IN (
                  SELECT DISTINCT source_id
                  FROM cross_schema.document_chunks
                  WHERE source = $1
              )
            LIMIT ${idx}
        """

        logger.debug(
            "fetch_unchunked_docs",
            source=source,
            batch_size=batch_size,
            year_from=year_from,
        )

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [(row["source_id"], row["text"]) for row in rows]

    # -----------------------------------------------------------------------
    # Chunks mit Embeddings speichern
    # -----------------------------------------------------------------------

    async def store_chunks_with_embeddings(
        self, source: str, records: list[tuple[str, int, str, list[float]]],
    ) -> int:
        """Speichert Chunks mit Embeddings in cross_schema.document_chunks.

        Args:
            source: "patents", "projects" oder "papers"
            records: Liste von (source_id, chunk_index, chunk_text, embedding) Tupeln

        Returns:
            Anzahl geschriebener Rows
        """
        if not records:
            return 0

        sql = """
            INSERT INTO cross_schema.document_chunks
                (source, source_id, chunk_index, chunk_text, embedding)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (source, source_id, chunk_index) DO UPDATE
                SET chunk_text = EXCLUDED.chunk_text,
                    embedding  = EXCLUDED.embedding
        """

        data = [
            (source, source_id, chunk_index, chunk_text, embedding)
            for source_id, chunk_index, chunk_text, embedding in records
        ]

        async with self._pool.acquire() as conn:
            await conn.executemany(sql, data)

        stored = len(records)
        logger.info(
            "chunks_gespeichert",
            source=source,
            count=stored,
        )
        return stored

    # -----------------------------------------------------------------------
    # Chunk-Status-Abfrage
    # -----------------------------------------------------------------------

    async def count_chunk_status(self, source: str) -> tuple[int, int]:
        """Gibt (total_docs_with_text, docs_already_chunked) Counts zurueck.

        Args:
            source: "patents", "projects" oder "papers"

        Returns:
            Tuple (total_with_text, already_chunked)
        """
        cfg = _get_config(source)

        sql = f"""
            SELECT
                (SELECT COUNT(*)
                 FROM {cfg['table']}
                 WHERE {cfg['text_not_null']}) AS total,
                (SELECT COUNT(DISTINCT source_id)
                 FROM cross_schema.document_chunks
                 WHERE source = $1) AS chunked
        """

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, source)
            return (row["total"], row["chunked"])
