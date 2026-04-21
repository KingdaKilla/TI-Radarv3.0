"""Unit-Tests fuer SparseSearchRepository.

Testet die BM25/Full-Text-Suche via ts_rank_cd, Quellnamen-Singularisierung,
und Fehlerbehandlung bei unbekannten Quellen.
Alle DB-Zugriffe werden durch AsyncMock ersetzt.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.ports import RetrievedDoc
from src.infrastructure.sparse_repository import (
    SparseSearchRepository,
    _SPARSE_QUERIES,
)


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
    rank: float = 0.42,
    year: str = "2023",
    country: str = "DE",
) -> dict:
    """Erstellt eine Mock-DB-Row als dict fuer Sparse-Suche."""
    return {
        "source_id": source_id,
        "title": title,
        "text_snippet": text_snippet,
        "rank": rank,
        "year": year,
        "country": country,
    }


# ---------------------------------------------------------------------------
# Tests: Ergebnis-Konvertierung
# ---------------------------------------------------------------------------

class TestSearchReturnsRetrievedDocs:
    """Testet dass DB-Rows korrekt in RetrievedDoc konvertiert werden."""

    async def test_search_returns_retrieved_docs(self):
        rows = [
            _make_row(source_id="42", title="Quantum Computing", text_snippet="Quantum Computing", rank=0.85, year="2024", country="US"),
            _make_row(source_id="99", title="Neural Networks", text_snippet="Neural Networks", rank=0.55, year="2022", country="DE"),
        ]
        pool = _make_pool(fetch_rows=rows)
        repo = SparseSearchRepository(pool)

        result = await repo.search(query="quantum computing", sources=["patents"], top_k=10)

        assert len(result) == 2

        # Erstes Dokument
        assert isinstance(result[0], RetrievedDoc)
        assert result[0].source == "patent"
        assert result[0].source_id == "42"
        assert result[0].title == "Quantum Computing"
        assert result[0].text_snippet == "Quantum Computing"
        assert result[0].similarity_score == pytest.approx(0.85)
        assert result[0].metadata["year"] == "2024"
        assert result[0].metadata["country"] == "US"

        # Zweites Dokument
        assert result[1].source == "patent"
        assert result[1].source_id == "99"
        assert result[1].similarity_score == pytest.approx(0.55)

    async def test_none_title_becomes_empty_string(self):
        rows = [_make_row()]
        rows[0]["title"] = None
        rows[0]["text_snippet"] = None
        pool = _make_pool(fetch_rows=rows)
        repo = SparseSearchRepository(pool)

        result = await repo.search(query="test", sources=["patents"], top_k=5)

        assert result[0].title == ""
        assert result[0].text_snippet == ""


# ---------------------------------------------------------------------------
# Tests: Leere Ergebnisse
# ---------------------------------------------------------------------------

class TestSearchEmptyResult:
    """Testet dass leere DB-Ergebnisse korrekt behandelt werden."""

    async def test_search_empty_result(self):
        pool = _make_pool(fetch_rows=[])
        repo = SparseSearchRepository(pool)

        result = await repo.search(query="nonexistent topic", sources=["patents"], top_k=10)

        assert result == []
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Tests: Unbekannte Quellen
# ---------------------------------------------------------------------------

class TestUnknownSourceSkipped:
    """Testet dass unbekannte Quellen uebersprungen werden."""

    async def test_search_unknown_source_skipped(self):
        pool = _make_pool(fetch_rows=[])
        repo = SparseSearchRepository(pool)

        result = await repo.search(query="quantum", sources=["unknown_source"], top_k=10)

        assert result == []
        # Pool.acquire() sollte NICHT aufgerufen werden bei unbekannter Quelle
        pool.acquire.assert_not_called()

    async def test_unknown_source_mixed_with_known(self):
        rows = [_make_row(source_id="1", rank=0.7)]
        pool = _make_pool(fetch_rows=rows)
        repo = SparseSearchRepository(pool)

        result = await repo.search(
            query="quantum",
            sources=["unknown_source", "patents"],
            top_k=10,
        )

        # Nur die bekannte Quelle "patents" sollte Ergebnisse liefern
        assert len(result) == 1
        assert result[0].source == "patent"


# ---------------------------------------------------------------------------
# Tests: Mehrere Quellen
# ---------------------------------------------------------------------------

class TestSearchMultipleSources:
    """Testet Suche ueber mehrere Quellen."""

    async def test_search_multiple_sources(self):
        patent_rows = [_make_row(source_id="p1", rank=0.9)]
        project_rows = [_make_row(source_id="c1", rank=0.6, country="")]

        pool = MagicMock()
        conn = AsyncMock()

        # conn.fetch gibt je nach Aufruf unterschiedliche Ergebnisse
        conn.fetch.side_effect = [patent_rows, project_rows]

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=conn)
        ctx.__aexit__ = AsyncMock(return_value=False)
        pool.acquire.return_value = ctx

        repo = SparseSearchRepository(pool)

        result = await repo.search(
            query="quantum computing",
            sources=["patents", "projects"],
            top_k=5,
        )

        assert len(result) == 2
        sources = {d.source for d in result}
        assert "patent" in sources
        assert "project" in sources

        # conn.fetch sollte 2x aufgerufen werden (einmal pro Quelle)
        assert conn.fetch.call_count == 2

    async def test_all_three_sources(self):
        patent_rows = [_make_row(source_id="p1", rank=0.9)]
        project_rows = [_make_row(source_id="c1", rank=0.7, country="")]
        paper_rows = [_make_row(source_id="r1", rank=0.5, country="")]

        pool = MagicMock()
        conn = AsyncMock()
        conn.fetch.side_effect = [patent_rows, project_rows, paper_rows]

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=conn)
        ctx.__aexit__ = AsyncMock(return_value=False)
        pool.acquire.return_value = ctx

        repo = SparseSearchRepository(pool)

        result = await repo.search(
            query="machine learning",
            sources=["patents", "projects", "papers"],
            top_k=5,
        )

        assert len(result) == 3
        sources = {d.source for d in result}
        assert sources == {"patent", "project", "paper"}


# ---------------------------------------------------------------------------
# Tests: SQL-Queries verwenden ts_rank_cd
# ---------------------------------------------------------------------------

class TestSqlUsesTsRankCd:
    """Testet dass die SQL-Queries ts_rank_cd verwenden."""

    def test_patents_query_uses_ts_rank_cd(self):
        assert "ts_rank_cd" in _SPARSE_QUERIES["patents"]

    def test_projects_query_uses_ts_rank_cd(self):
        assert "ts_rank_cd" in _SPARSE_QUERIES["projects"]

    def test_papers_query_uses_ts_rank_cd(self):
        assert "ts_rank_cd" in _SPARSE_QUERIES["papers"]

    def test_all_queries_use_plainto_tsquery(self):
        for source, sql in _SPARSE_QUERIES.items():
            assert "plainto_tsquery" in sql, f"Query fuer '{source}' fehlt plainto_tsquery"

    def test_all_queries_use_search_vector(self):
        for source, sql in _SPARSE_QUERIES.items():
            assert "search_vector" in sql, f"Query fuer '{source}' fehlt search_vector"


# ---------------------------------------------------------------------------
# Tests: Quellnamen-Singularisierung
# ---------------------------------------------------------------------------

class TestSourceSingularization:
    """Testet dass Quellnamen korrekt singularisiert werden."""

    async def test_patents_becomes_patent(self):
        rows = [_make_row(rank=0.8)]
        pool = _make_pool(fetch_rows=rows)
        repo = SparseSearchRepository(pool)

        result = await repo.search(query="quantum", sources=["patents"], top_k=5)

        assert result[0].source == "patent"

    async def test_projects_becomes_project(self):
        rows = [_make_row(rank=0.8, country="")]
        pool = _make_pool(fetch_rows=rows)
        repo = SparseSearchRepository(pool)

        result = await repo.search(query="quantum", sources=["projects"], top_k=5)

        assert result[0].source == "project"

    async def test_papers_becomes_paper(self):
        rows = [_make_row(rank=0.8, country="")]
        pool = _make_pool(fetch_rows=rows)
        repo = SparseSearchRepository(pool)

        result = await repo.search(query="quantum", sources=["papers"], top_k=5)

        assert result[0].source == "paper"


# ---------------------------------------------------------------------------
# Tests: Metadaten
# ---------------------------------------------------------------------------

class TestMetadata:
    """Testet dass Metadaten korrekt extrahiert werden."""

    async def test_metadata_includes_year_and_country(self):
        rows = [_make_row(year="2023", country="DE", rank=0.8)]
        pool = _make_pool(fetch_rows=rows)
        repo = SparseSearchRepository(pool)

        result = await repo.search(query="quantum", sources=["patents"], top_k=5)

        assert result[0].metadata["year"] == "2023"
        assert result[0].metadata["country"] == "DE"

    async def test_empty_country_not_in_metadata(self):
        rows = [_make_row(country="", rank=0.8)]
        pool = _make_pool(fetch_rows=rows)
        repo = SparseSearchRepository(pool)

        result = await repo.search(query="quantum", sources=["patents"], top_k=5)

        assert "country" not in result[0].metadata

    async def test_empty_year_not_in_metadata(self):
        rows = [_make_row(year="", rank=0.8)]
        pool = _make_pool(fetch_rows=rows)
        repo = SparseSearchRepository(pool)

        result = await repo.search(query="quantum", sources=["patents"], top_k=5)

        assert "year" not in result[0].metadata


# ---------------------------------------------------------------------------
# Tests: Query-Konfiguration
# ---------------------------------------------------------------------------

class TestSparseQueries:
    """Testet die Sparse-Query-Konfiguration."""

    def test_all_sources_have_queries(self):
        assert "patents" in _SPARSE_QUERIES
        assert "projects" in _SPARSE_QUERIES
        assert "papers" in _SPARSE_QUERIES

    def test_patents_query_searches_patent_schema(self):
        assert "patent_schema.patents" in _SPARSE_QUERIES["patents"]

    def test_projects_query_searches_cordis_schema(self):
        assert "cordis_schema.projects" in _SPARSE_QUERIES["projects"]

    def test_papers_query_searches_research_schema(self):
        assert "research_schema.papers" in _SPARSE_QUERIES["papers"]
