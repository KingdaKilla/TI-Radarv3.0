"""Unit-Tests fuer EmbeddingRepository und ChunkRepository.

Testet die Source-Konfiguration, SQL-Query-Logik und Fehlerbehandlung.
Alle DB-Zugriffe werden durch AsyncMock ersetzt.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.repository import (
    ChunkRepository,
    EmbeddingRepository,
    _SOURCE_CONFIG,
    _get_config,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_pool(
    *,
    fetch_rows: list | None = None,
    fetchrow_result: dict | None = None,
) -> MagicMock:
    """Erstellt einen Mock-asyncpg-Pool.

    asyncpg.Pool.acquire() ist ein synchroner Aufruf, der einen
    async context manager zurueckgibt — daher MagicMock fuer pool,
    AsyncMock fuer die Connection.
    """
    pool = MagicMock()
    conn = AsyncMock()

    conn.fetch.return_value = fetch_rows or []
    conn.fetchrow.return_value = fetchrow_result or {"total": 0, "embedded": 0}
    conn.executemany.return_value = None

    # pool.acquire() als async context manager
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx

    return pool


# ---------------------------------------------------------------------------
# Tests: Source-Konfiguration
# ---------------------------------------------------------------------------

class TestSourceConfig:
    """Testet das Source-Mapping und die Validierung."""

    def test_patents_config_exists(self):
        cfg = _get_config("patents")
        assert cfg["table"] == "patent_schema.patents"
        assert cfg["embedding_col"] == "title_embedding"

    def test_projects_config_uses_content_embedding(self):
        cfg = _get_config("projects")
        assert cfg["table"] == "cordis_schema.projects"
        assert cfg["embedding_col"] == "content_embedding"
        assert "COALESCE" in cfg["text_expr"]

    def test_papers_config_uses_abstract_embedding(self):
        cfg = _get_config("papers")
        assert cfg["table"] == "research_schema.papers"
        assert cfg["embedding_col"] == "abstract_embedding"

    def test_unknown_source_raises(self):
        with pytest.raises(ValueError, match="Unbekannte Quelle"):
            _get_config("unknown_source")

    def test_all_sources_have_required_keys(self):
        required = {"table", "id_col", "text_expr", "embedding_col", "text_not_null", "year_col"}
        for source, cfg in _SOURCE_CONFIG.items():
            assert required.issubset(cfg.keys()), f"Source '{source}' fehlen Keys"


# ---------------------------------------------------------------------------
# Tests: fetch_unembedded
# ---------------------------------------------------------------------------

class TestFetchUnembedded:
    """Testet das Lesen von Dokumenten ohne Embedding."""

    async def test_patents_query_filters_by_null_embedding(self):
        pool = _make_pool(fetch_rows=[
            {"id": 1, "text": "Quantum Patent"},
            {"id": 2, "text": "AI Patent"},
        ])
        repo = EmbeddingRepository(pool)

        result = await repo.fetch_unembedded("patents", 100)

        assert len(result) == 2
        assert result[0] == (1, "Quantum Patent")
        assert result[1] == (2, "AI Patent")

    async def test_patents_with_year_filter(self):
        pool = _make_pool(fetch_rows=[{"id": 5, "text": "Recent Patent"}])
        repo = EmbeddingRepository(pool)

        result = await repo.fetch_unembedded("patents", 50, year_from=2020)

        assert len(result) == 1
        # Verify the SQL was called with year_from parameter
        conn = pool.acquire.return_value.__aenter__.return_value
        call_args = conn.fetch.call_args
        assert 2020 in call_args[0]  # year_from in positional args

    async def test_projects_query(self):
        pool = _make_pool(fetch_rows=[{"id": 10, "text": "CORDIS Project Title Objective"}])
        repo = EmbeddingRepository(pool)

        result = await repo.fetch_unembedded("projects", 100)

        assert result[0] == (10, "CORDIS Project Title Objective")

    async def test_empty_result(self):
        pool = _make_pool(fetch_rows=[])
        repo = EmbeddingRepository(pool)

        result = await repo.fetch_unembedded("patents", 100)

        assert result == []

    async def test_unknown_source_raises(self):
        pool = _make_pool()
        repo = EmbeddingRepository(pool)

        with pytest.raises(ValueError, match="Unbekannte Quelle"):
            await repo.fetch_unembedded("unknown", 100)


# ---------------------------------------------------------------------------
# Tests: store_embeddings
# ---------------------------------------------------------------------------

class TestStoreEmbeddings:
    """Testet das Schreiben von Embeddings."""

    async def test_store_empty_list_returns_zero(self):
        pool = _make_pool()
        repo = EmbeddingRepository(pool)

        result = await repo.store_embeddings("patents", [])

        assert result == 0

    async def test_store_calls_executemany(self):
        pool = _make_pool()
        repo = EmbeddingRepository(pool)

        pairs = [(1, [0.1, 0.2]), (2, [0.3, 0.4])]
        result = await repo.store_embeddings("patents", pairs)

        assert result == 2
        conn = pool.acquire.return_value.__aenter__.return_value
        conn.executemany.assert_called_once()

    async def test_store_unknown_source_raises(self):
        pool = _make_pool()
        repo = EmbeddingRepository(pool)

        with pytest.raises(ValueError, match="Unbekannte Quelle"):
            await repo.store_embeddings("invalid", [(1, [0.1])])


# ---------------------------------------------------------------------------
# Tests: count_status
# ---------------------------------------------------------------------------

class TestCountStatus:
    """Testet die Status-Abfrage."""

    async def test_count_returns_tuple(self):
        pool = _make_pool(fetchrow_result={"total": 1000, "embedded": 750})
        repo = EmbeddingRepository(pool)

        total, embedded = await repo.count_status("patents")

        assert total == 1000
        assert embedded == 750

    async def test_count_projects(self):
        pool = _make_pool(fetchrow_result={"total": 500, "embedded": 200})
        repo = EmbeddingRepository(pool)

        total, embedded = await repo.count_status("projects")

        assert total == 500
        assert embedded == 200

    async def test_count_unknown_source_raises(self):
        pool = _make_pool()
        repo = EmbeddingRepository(pool)

        with pytest.raises(ValueError, match="Unbekannte Quelle"):
            await repo.count_status("nonexistent")


# ===========================================================================
# ChunkRepository Tests
# ===========================================================================

# ---------------------------------------------------------------------------
# Tests: fetch_unchunked_docs
# ---------------------------------------------------------------------------

class TestFetchUnchunkedDocs:
    """Testet das Lesen von Dokumenten ohne Chunks."""

    async def test_returns_source_id_text_tuples(self):
        pool = _make_pool(fetch_rows=[
            {"source_id": "PAT-001", "text": "Quantum computing patent"},
            {"source_id": "PAT-002", "text": "AI patent"},
        ])
        repo = ChunkRepository(pool)

        result = await repo.fetch_unchunked_docs("patents", 100)

        assert len(result) == 2
        assert result[0] == ("PAT-001", "Quantum computing patent")
        assert result[1] == ("PAT-002", "AI patent")

    async def test_empty_result(self):
        pool = _make_pool(fetch_rows=[])
        repo = ChunkRepository(pool)

        result = await repo.fetch_unchunked_docs("patents", 100)

        assert result == []

    async def test_unknown_source_raises(self):
        pool = _make_pool()
        repo = ChunkRepository(pool)

        with pytest.raises(ValueError, match="Unbekannte Quelle"):
            await repo.fetch_unchunked_docs("invalid", 100)

    async def test_sql_contains_not_in_subquery(self):
        """Verifiziert dass die SQL-Query eine NOT IN Subquery auf document_chunks nutzt."""
        pool = _make_pool(fetch_rows=[])
        repo = ChunkRepository(pool)

        await repo.fetch_unchunked_docs("patents", 50)

        conn = pool.acquire.return_value.__aenter__.return_value
        sql = conn.fetch.call_args[0][0]
        assert "document_chunks" in sql
        assert "NOT IN" in sql.upper() or "NOT EXISTS" in sql.upper()

    async def test_patents_with_year_filter(self):
        pool = _make_pool(fetch_rows=[{"source_id": "PAT-005", "text": "Recent"}])
        repo = ChunkRepository(pool)

        result = await repo.fetch_unchunked_docs("patents", 50, year_from=2020)

        assert len(result) == 1
        conn = pool.acquire.return_value.__aenter__.return_value
        call_args = conn.fetch.call_args
        assert 2020 in call_args[0]


# ---------------------------------------------------------------------------
# Tests: store_chunks_with_embeddings
# ---------------------------------------------------------------------------

class TestStoreChunksWithEmbeddings:
    """Testet das Speichern von Chunks mit Embeddings."""

    async def test_store_returns_count(self):
        pool = _make_pool()
        repo = ChunkRepository(pool)

        records = [
            ("DOC-1", 0, "chunk text a", [0.1, 0.2]),
            ("DOC-1", 1, "chunk text b", [0.3, 0.4]),
        ]
        result = await repo.store_chunks_with_embeddings("patents", records)

        assert result == 2

    async def test_store_empty_returns_zero(self):
        pool = _make_pool()
        repo = ChunkRepository(pool)

        result = await repo.store_chunks_with_embeddings("patents", [])

        assert result == 0

    async def test_store_calls_executemany(self):
        pool = _make_pool()
        repo = ChunkRepository(pool)

        records = [("DOC-1", 0, "text", [0.1])]
        await repo.store_chunks_with_embeddings("patents", records)

        conn = pool.acquire.return_value.__aenter__.return_value
        conn.executemany.assert_called_once()

    async def test_store_sql_targets_document_chunks(self):
        pool = _make_pool()
        repo = ChunkRepository(pool)

        records = [("DOC-1", 0, "text", [0.1])]
        await repo.store_chunks_with_embeddings("patents", records)

        conn = pool.acquire.return_value.__aenter__.return_value
        sql = conn.executemany.call_args[0][0]
        assert "cross_schema.document_chunks" in sql
        assert "INSERT" in sql.upper()


# ---------------------------------------------------------------------------
# Tests: count_chunk_status
# ---------------------------------------------------------------------------

class TestCountChunkStatus:
    """Testet die Chunk-Status-Abfrage."""

    async def test_returns_total_and_chunked(self):
        pool = _make_pool(fetchrow_result={"total": 1000, "chunked": 750})
        repo = ChunkRepository(pool)

        total, chunked = await repo.count_chunk_status("patents")

        assert total == 1000
        assert chunked == 750

    async def test_unknown_source_raises(self):
        pool = _make_pool()
        repo = ChunkRepository(pool)

        with pytest.raises(ValueError, match="Unbekannte Quelle"):
            await repo.count_chunk_status("nonexistent")
