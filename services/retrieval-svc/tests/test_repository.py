"""Unit-Tests fuer VectorSearchRepository.

Testet die Dense-Search auf document_chunks, Schwellwert-Filterung,
Quellnamen-Singularisierung und Fehlerbehandlung.
Alle DB-Zugriffe werden durch AsyncMock ersetzt.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.ports import RetrievedDoc
from src.infrastructure.repository import VectorSearchRepository, _SOURCE_QUERIES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_pool(
    *,
    fetch_rows: list[dict] | None = None,
) -> MagicMock:
    """Erstellt einen Mock-asyncpg-Pool.

    asyncpg.Pool.acquire() ist ein synchroner Aufruf, der einen
    async context manager zurueckgibt — daher MagicMock fuer pool,
    AsyncMock fuer die Connection.
    """
    pool = MagicMock()
    conn = AsyncMock()

    conn.fetch.return_value = fetch_rows or []

    # pool.acquire() als async context manager
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx

    return pool


def _make_row(
    *,
    source_id: str = "1",
    title: str = "Test Patent",
    text_snippet: str = "Test Patent",
    similarity: float = 0.85,
    year: str = "2023",
    country: str = "DE",
) -> dict:
    """Erstellt eine Mock-DB-Row als dict."""
    return {
        "source_id": source_id,
        "title": title,
        "text_snippet": text_snippet,
        "similarity": similarity,
        "year": year,
        "country": country,
    }


# ---------------------------------------------------------------------------
# Tests: Unbekannte Quellen
# ---------------------------------------------------------------------------

class TestUnknownSource:
    """Testet dass unbekannte Quellen uebersprungen werden."""

    async def test_unknown_source_skipped(self):
        pool = _make_pool(fetch_rows=[])
        repo = VectorSearchRepository(pool)

        result = await repo.search(
            query_vector=[0.1, 0.2],
            technology="quantum",
            sources=["unknown_source"],
            top_k=10,
            threshold=0.3,
        )

        assert result == []
        # Pool.acquire() should NOT be called for unknown source
        pool.acquire.assert_not_called()

    async def test_unknown_source_mixed_with_known(self):
        rows = [_make_row(similarity=0.9)]
        pool = _make_pool(fetch_rows=rows)
        repo = VectorSearchRepository(pool)

        result = await repo.search(
            query_vector=[0.1, 0.2],
            technology="quantum",
            sources=["unknown_source", "patents"],
            top_k=10,
            threshold=0.3,
        )

        # Only the known source "patents" should produce results
        assert len(result) == 1
        assert result[0].source == "patent"


# ---------------------------------------------------------------------------
# Tests: Schwellwert-Filterung
# ---------------------------------------------------------------------------

class TestThresholdFiltering:
    """Testet dass Dokumente unter dem Threshold gefiltert werden."""

    async def test_threshold_filters_low_scores(self):
        rows = [
            _make_row(source_id="1", similarity=0.9),
            _make_row(source_id="2", similarity=0.1),  # below threshold
            _make_row(source_id="3", similarity=0.5),
        ]
        pool = _make_pool(fetch_rows=rows)
        repo = VectorSearchRepository(pool)

        result = await repo.search(
            query_vector=[0.1, 0.2],
            technology="quantum",
            sources=["patents"],
            top_k=10,
            threshold=0.3,
        )

        assert len(result) == 2
        source_ids = [d.source_id for d in result]
        assert "1" in source_ids
        assert "3" in source_ids
        assert "2" not in source_ids

    async def test_all_below_threshold_returns_empty(self):
        rows = [
            _make_row(source_id="1", similarity=0.1),
            _make_row(source_id="2", similarity=0.2),
        ]
        pool = _make_pool(fetch_rows=rows)
        repo = VectorSearchRepository(pool)

        result = await repo.search(
            query_vector=[0.1, 0.2],
            technology="quantum",
            sources=["patents"],
            top_k=10,
            threshold=0.5,
        )

        assert result == []


# ---------------------------------------------------------------------------
# Tests: Quellnamen-Singularisierung
# ---------------------------------------------------------------------------

class TestSourceSingularization:
    """Testet dass Quellnamen korrekt singularisiert werden."""

    async def test_patents_becomes_patent(self):
        rows = [_make_row(similarity=0.9)]
        pool = _make_pool(fetch_rows=rows)
        repo = VectorSearchRepository(pool)

        result = await repo.search(
            query_vector=[0.1, 0.2],
            technology="quantum",
            sources=["patents"],
            top_k=10,
            threshold=0.3,
        )

        assert len(result) == 1
        assert result[0].source == "patent"

    async def test_projects_becomes_project(self):
        rows = [_make_row(similarity=0.9, country="")]
        pool = _make_pool(fetch_rows=rows)
        repo = VectorSearchRepository(pool)

        result = await repo.search(
            query_vector=[0.1, 0.2],
            technology="quantum",
            sources=["projects"],
            top_k=10,
            threshold=0.3,
        )

        assert len(result) == 1
        assert result[0].source == "project"

    async def test_papers_becomes_paper(self):
        rows = [_make_row(similarity=0.9, country="")]
        pool = _make_pool(fetch_rows=rows)
        repo = VectorSearchRepository(pool)

        result = await repo.search(
            query_vector=[0.1, 0.2],
            technology="quantum",
            sources=["papers"],
            top_k=10,
            threshold=0.3,
        )

        assert len(result) == 1
        assert result[0].source == "paper"


# ---------------------------------------------------------------------------
# Tests: Metadaten
# ---------------------------------------------------------------------------

class TestMetadata:
    """Testet dass Metadaten korrekt extrahiert werden."""

    async def test_metadata_includes_year_and_country(self):
        rows = [_make_row(year="2023", country="DE", similarity=0.9)]
        pool = _make_pool(fetch_rows=rows)
        repo = VectorSearchRepository(pool)

        result = await repo.search(
            query_vector=[0.1, 0.2],
            technology="quantum",
            sources=["patents"],
            top_k=10,
            threshold=0.3,
        )

        assert result[0].metadata["year"] == "2023"
        assert result[0].metadata["country"] == "DE"

    async def test_empty_country_not_in_metadata(self):
        rows = [_make_row(country="", similarity=0.9)]
        pool = _make_pool(fetch_rows=rows)
        repo = VectorSearchRepository(pool)

        result = await repo.search(
            query_vector=[0.1, 0.2],
            technology="quantum",
            sources=["patents"],
            top_k=10,
            threshold=0.3,
        )

        assert "country" not in result[0].metadata

    async def test_empty_year_not_in_metadata(self):
        rows = [_make_row(year="", similarity=0.9)]
        pool = _make_pool(fetch_rows=rows)
        repo = VectorSearchRepository(pool)

        result = await repo.search(
            query_vector=[0.1, 0.2],
            technology="quantum",
            sources=["patents"],
            top_k=10,
            threshold=0.3,
        )

        assert "year" not in result[0].metadata


# ---------------------------------------------------------------------------
# Tests: RetrievedDoc Dataclass
# ---------------------------------------------------------------------------

class TestRetrievedDoc:
    """Testet RetrievedDoc Dataclass."""

    def test_frozen(self):
        doc = RetrievedDoc(
            source="patent",
            source_id="1",
            title="Test",
            text_snippet="Snippet",
            similarity_score=0.8,
            metadata={},
        )
        with pytest.raises(AttributeError):
            doc.source = "project"  # type: ignore[misc]

    def test_slots(self):
        doc = RetrievedDoc(
            source="patent",
            source_id="1",
            title="Test",
            text_snippet="Snippet",
            similarity_score=0.8,
            metadata={},
        )
        assert not hasattr(doc, "__dict__")


# ---------------------------------------------------------------------------
# Tests: Source Query Konfiguration
# ---------------------------------------------------------------------------

class TestSourceQueries:
    """Testet die Source-Query-Konfiguration."""

    def test_all_sources_have_queries(self):
        assert "patents" in _SOURCE_QUERIES
        assert "projects" in _SOURCE_QUERIES
        assert "papers" in _SOURCE_QUERIES

    def test_patents_query_uses_document_chunks(self):
        assert "document_chunks" in _SOURCE_QUERIES["patents"]
        assert "dc.source = 'patent'" in _SOURCE_QUERIES["patents"]

    def test_projects_query_uses_document_chunks(self):
        assert "document_chunks" in _SOURCE_QUERIES["projects"]
        assert "dc.source = 'project'" in _SOURCE_QUERIES["projects"]

    def test_papers_query_uses_document_chunks(self):
        assert "document_chunks" in _SOURCE_QUERIES["papers"]
        assert "dc.source = 'paper'" in _SOURCE_QUERIES["papers"]
