"""Unit-Tests fuer RetrieveDocuments Use Case (3-Stage Pipeline).

Alle externen Abhaengigkeiten (VectorSearch, SparseSearch, Reranker,
QueryEmbedder) werden durch AsyncMock-Objekte ersetzt.
Kein IO, kein gRPC, kein Protobuf.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, call, patch

import pytest

from src.domain.ports import RetrievedDoc
from src.use_case import RetrieveDocuments, RetrievalResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_doc(
    source: str = "patent",
    source_id: str = "1",
    title: str = "Test Doc",
    text_snippet: str = "Snippet",
    similarity_score: float = 0.8,
    metadata: dict[str, str] | None = None,
) -> RetrievedDoc:
    """Erstellt ein RetrievedDoc mit sinnvollen Defaults."""
    return RetrievedDoc(
        source=source,
        source_id=source_id,
        title=title,
        text_snippet=text_snippet,
        similarity_score=similarity_score,
        metadata=metadata or {},
    )


def _make_mocks(
    *,
    dense_docs: list[RetrievedDoc] | None = None,
    sparse_docs: list[RetrievedDoc] | None = None,
    reranked_docs: list[RetrievedDoc] | None = None,
    embedding: list[float] | None = None,
) -> tuple[AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    """Erstellt Mocks fuer alle 4 Ports: dense, sparse, reranker, embedder."""
    dense_search = AsyncMock()
    dense_search.search.return_value = dense_docs if dense_docs is not None else []

    sparse_search = AsyncMock()
    sparse_search.search.return_value = sparse_docs if sparse_docs is not None else []

    reranker = AsyncMock()
    reranker.rerank.return_value = reranked_docs if reranked_docs is not None else []

    embedder = AsyncMock()
    embedder.embed_query.return_value = (
        embedding if embedding is not None else [0.1, 0.2, 0.3]
    )

    return dense_search, sparse_search, reranker, embedder


# ---------------------------------------------------------------------------
# Tests: Leere Ergebnisse
# ---------------------------------------------------------------------------

class TestEmptyResults:
    """Testet Verhalten wenn keine Dokumente gefunden werden."""

    async def test_empty_results(self):
        dense, sparse, reranker, embedder = _make_mocks(
            dense_docs=[], sparse_docs=[], reranked_docs=[],
        )
        uc = RetrieveDocuments(
            dense_search=dense,
            sparse_search=sparse,
            reranker=reranker,
            embedder=embedder,
        )

        result = await uc.execute(technology="quantum", query="quantum computing")

        assert isinstance(result, RetrievalResult)
        assert result.documents == []
        assert result.query_embedding_ms >= 0
        assert result.search_ms >= 0
        assert result.rerank_ms >= 0


# ---------------------------------------------------------------------------
# Tests: Source-Filter
# ---------------------------------------------------------------------------

class TestSourceFilter:
    """Testet dass Sources korrekt weitergeleitet werden."""

    async def test_filters_by_sources(self):
        dense, sparse, reranker, embedder = _make_mocks()
        uc = RetrieveDocuments(
            dense_search=dense,
            sparse_search=sparse,
            reranker=reranker,
            embedder=embedder,
        )

        await uc.execute(
            technology="quantum",
            query="quantum computing",
            sources=["patents", "papers"],
        )

        dense_kwargs = dense.search.call_args.kwargs
        assert dense_kwargs["sources"] == ["patents", "papers"]

        sparse_kwargs = sparse.search.call_args.kwargs
        assert sparse_kwargs["sources"] == ["patents", "papers"]

    async def test_default_sources(self):
        dense, sparse, reranker, embedder = _make_mocks()
        uc = RetrieveDocuments(
            dense_search=dense,
            sparse_search=sparse,
            reranker=reranker,
            embedder=embedder,
        )

        await uc.execute(technology="quantum", query="quantum computing", sources=None)

        dense_kwargs = dense.search.call_args.kwargs
        assert dense_kwargs["sources"] == ["patents", "projects", "papers"]

        sparse_kwargs = sparse.search.call_args.kwargs
        assert sparse_kwargs["sources"] == ["patents", "projects", "papers"]


# ---------------------------------------------------------------------------
# Tests: Timing
# ---------------------------------------------------------------------------

class TestTiming:
    """Testet dass Timing-Informationen erfasst werden."""

    async def test_timing_tracked(self):
        doc = _make_doc()
        dense, sparse, reranker, embedder = _make_mocks(
            dense_docs=[doc], sparse_docs=[], reranked_docs=[doc],
        )
        uc = RetrieveDocuments(
            dense_search=dense,
            sparse_search=sparse,
            reranker=reranker,
            embedder=embedder,
        )

        result = await uc.execute(technology="quantum", query="quantum computing")

        assert result.query_embedding_ms >= 0
        assert result.search_ms >= 0
        assert result.rerank_ms >= 0


# ---------------------------------------------------------------------------
# Tests: RetrievalResult Dataclass
# ---------------------------------------------------------------------------

class TestRetrievalResult:
    """Testet RetrievalResult Dataclass."""

    def test_frozen(self):
        result = RetrievalResult(
            documents=[],
            query_embedding_ms=10.0,
            search_ms=5.0,
            rerank_ms=2.0,
        )
        with pytest.raises(AttributeError):
            result.documents = []  # type: ignore[misc]

    def test_slots(self):
        result = RetrievalResult(
            documents=[],
            query_embedding_ms=0.0,
            search_ms=0.0,
            rerank_ms=0.0,
        )
        assert not hasattr(result, "__dict__")

    def test_rerank_ms_field_exists(self):
        result = RetrievalResult(
            documents=[],
            query_embedding_ms=1.0,
            search_ms=2.0,
            rerank_ms=3.0,
        )
        assert result.rerank_ms == 3.0


# ---------------------------------------------------------------------------
# Tests: 3-Stage Pipeline
# ---------------------------------------------------------------------------

class TestThreeStagePipeline:
    """Testet die 3-stufige Pipeline: Dense+Sparse -> RRF -> Reranking."""

    async def test_3_stage_pipeline_flow(self):
        """Verifiziert dass alle 3 Stufen aufgerufen werden."""
        doc_a = _make_doc(source="patent", source_id="A", similarity_score=0.9)
        doc_b = _make_doc(source="paper", source_id="B", similarity_score=0.7)
        reranked = [doc_a, doc_b]

        dense, sparse, reranker, embedder = _make_mocks(
            dense_docs=[doc_a],
            sparse_docs=[doc_b],
            reranked_docs=reranked,
        )
        uc = RetrieveDocuments(
            dense_search=dense,
            sparse_search=sparse,
            reranker=reranker,
            embedder=embedder,
        )

        result = await uc.execute(technology="quantum", query="quantum computing", top_k=5)

        # Stage 1: Embedding was called
        embedder.embed_query.assert_awaited_once_with("quantum computing")
        # Stage 1: Both searches were called
        dense.search.assert_awaited_once()
        sparse.search.assert_awaited_once()
        # Stage 3: Reranker was called
        reranker.rerank.assert_awaited_once()
        # Final result comes from reranker
        assert result.documents == reranked

    async def test_parallel_search(self):
        """Verifiziert dass Dense und Sparse Search beide aufgerufen werden."""
        doc_dense = _make_doc(source="patent", source_id="D1", similarity_score=0.9)
        doc_sparse = _make_doc(source="paper", source_id="S1", similarity_score=0.6)

        dense, sparse, reranker, embedder = _make_mocks(
            dense_docs=[doc_dense],
            sparse_docs=[doc_sparse],
            reranked_docs=[doc_dense, doc_sparse],
        )
        uc = RetrieveDocuments(
            dense_search=dense,
            sparse_search=sparse,
            reranker=reranker,
            embedder=embedder,
        )

        await uc.execute(technology="quantum", query="quantum computing")

        # Dense search receives query_vector, technology, sources, top_k, threshold
        dense_kwargs = dense.search.call_args.kwargs
        assert dense_kwargs["query_vector"] == [0.1, 0.2, 0.3]
        assert dense_kwargs["technology"] == "quantum"

        # Sparse search receives query text, sources, top_k
        sparse_kwargs = sparse.search.call_args.kwargs
        assert sparse_kwargs["query"] == "quantum computing"

    async def test_rrf_fusion_combines_results(self):
        """Verifiziert dass RRF Ergebnisse aus Dense und Sparse kombiniert."""
        doc_dense = _make_doc(source="patent", source_id="D1", similarity_score=0.9)
        doc_sparse = _make_doc(source="paper", source_id="S1", similarity_score=0.6)
        doc_both = _make_doc(source="project", source_id="B1", similarity_score=0.8)

        # Both searches return doc_both; dense also has doc_dense, sparse also has doc_sparse
        dense, sparse, reranker, embedder = _make_mocks(
            dense_docs=[doc_both, doc_dense],
            sparse_docs=[doc_both, doc_sparse],
            reranked_docs=[doc_both, doc_dense, doc_sparse],  # reranker returns all
        )
        uc = RetrieveDocuments(
            dense_search=dense,
            sparse_search=sparse,
            reranker=reranker,
            embedder=embedder,
            fusion_top_n=20,
        )

        result = await uc.execute(technology="quantum", query="quantum computing", top_k=10)

        # Reranker should have been called with fused docs (all 3 unique docs)
        rerank_args = reranker.rerank.call_args
        fused_docs = rerank_args.kwargs["documents"]
        fused_ids = {f"{d.source}:{d.source_id}" for d in fused_docs}
        assert "project:B1" in fused_ids
        assert "patent:D1" in fused_ids
        assert "paper:S1" in fused_ids

    async def test_reranker_called_with_fused_docs(self):
        """Verifiziert dass der Reranker die fusionierten Dokumente erhaelt."""
        doc_a = _make_doc(source="patent", source_id="A", similarity_score=0.9)
        doc_b = _make_doc(source="paper", source_id="B", similarity_score=0.7)

        dense, sparse, reranker, embedder = _make_mocks(
            dense_docs=[doc_a],
            sparse_docs=[doc_b],
            reranked_docs=[doc_a],
        )
        uc = RetrieveDocuments(
            dense_search=dense,
            sparse_search=sparse,
            reranker=reranker,
            embedder=embedder,
        )

        await uc.execute(technology="quantum", query="quantum computing", top_k=1)

        rerank_kwargs = reranker.rerank.call_args.kwargs
        assert rerank_kwargs["query"] == "quantum computing"
        assert rerank_kwargs["top_k"] == 1
        # Should receive exactly the fused docs (2 unique docs from dense+sparse)
        assert len(rerank_kwargs["documents"]) == 2

    async def test_rerank_ms_tracked(self):
        """Verifiziert dass die Reranking-Zeit separat erfasst wird."""
        doc = _make_doc()
        dense, sparse, reranker, embedder = _make_mocks(
            dense_docs=[doc], sparse_docs=[], reranked_docs=[doc],
        )
        uc = RetrieveDocuments(
            dense_search=dense,
            sparse_search=sparse,
            reranker=reranker,
            embedder=embedder,
        )

        result = await uc.execute(technology="quantum", query="quantum computing")

        assert isinstance(result.rerank_ms, float)
        assert result.rerank_ms >= 0

    async def test_dense_doc_preferred_over_sparse_for_same_id(self):
        """Wenn ein Dokument in beiden Ergebnissen vorkommt, wird das Dense-Doc verwendet."""
        doc_dense = _make_doc(
            source="patent", source_id="X1", similarity_score=0.9, title="Dense Version",
        )
        doc_sparse = _make_doc(
            source="patent", source_id="X1", similarity_score=0.4, title="Sparse Version",
        )

        dense, sparse, reranker, embedder = _make_mocks(
            dense_docs=[doc_dense],
            sparse_docs=[doc_sparse],
        )
        # Make reranker return whatever it receives (pass-through)
        reranker.rerank.side_effect = lambda query, documents, top_k: documents[:top_k]

        uc = RetrieveDocuments(
            dense_search=dense,
            sparse_search=sparse,
            reranker=reranker,
            embedder=embedder,
        )

        result = await uc.execute(technology="quantum", query="quantum computing", top_k=5)

        # Should have exactly 1 doc (deduplicated), with dense version
        assert len(result.documents) == 1
        assert result.documents[0].title == "Dense Version"

    async def test_config_params_passed_to_searches(self):
        """Verifiziert dass dense_top_k und sparse_top_k korrekt weitergegeben werden."""
        dense, sparse, reranker, embedder = _make_mocks()
        uc = RetrieveDocuments(
            dense_search=dense,
            sparse_search=sparse,
            reranker=reranker,
            embedder=embedder,
            dense_top_k=100,
            sparse_top_k=75,
        )

        await uc.execute(technology="quantum", query="quantum computing")

        assert dense.search.call_args.kwargs["top_k"] == 100
        assert sparse.search.call_args.kwargs["top_k"] == 75

    async def test_fusion_top_n_limits_candidates(self):
        """Verifiziert dass fusion_top_n die Anzahl der Kandidaten fuer Reranking begrenzt."""
        # Create many docs so fusion_top_n actually limits
        dense_docs = [
            _make_doc(source="patent", source_id=str(i), similarity_score=0.9 - i * 0.01)
            for i in range(10)
        ]
        sparse_docs = [
            _make_doc(source="paper", source_id=str(i), similarity_score=0.8 - i * 0.01)
            for i in range(10)
        ]

        dense, sparse, reranker, embedder = _make_mocks(
            dense_docs=dense_docs,
            sparse_docs=sparse_docs,
        )
        reranker.rerank.side_effect = lambda query, documents, top_k: documents[:top_k]

        uc = RetrieveDocuments(
            dense_search=dense,
            sparse_search=sparse,
            reranker=reranker,
            embedder=embedder,
            fusion_top_n=5,  # Only top 5 from RRF
        )

        await uc.execute(technology="quantum", query="quantum computing", top_k=3)

        # Reranker should receive at most fusion_top_n docs
        rerank_kwargs = reranker.rerank.call_args.kwargs
        assert len(rerank_kwargs["documents"]) <= 5
