"""Unit-Tests fuer CrossEncoderReranker.

CrossEncoder.predict wird gemockt — kein Modell-Download noetig.
sentence_transformers wird als sys.modules-Mock eingefuegt, damit
kein echtes ML-Paket installiert sein muss.
"""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from src.config import Settings
from src.domain.ports import RetrievedDoc

# ---------------------------------------------------------------------------
# sentence_transformers-Stub in sys.modules registrieren,
# damit `from sentence_transformers import CrossEncoder` klappt.
# ---------------------------------------------------------------------------
_fake_st = ModuleType("sentence_transformers")
_fake_st.CrossEncoder = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("sentence_transformers", _fake_st)

# Jetzt kann das Modul sicher importiert werden
from src.infrastructure.reranker import CrossEncoderReranker  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    """Erstellt Settings ohne .env-Datei."""
    defaults = {"reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2"}
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


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


def _build_reranker(predict_scores: list[float]) -> tuple[CrossEncoderReranker, MagicMock]:
    """Erstellt CrossEncoderReranker mit gemocktem predict.

    Returns (reranker, mock_model).
    """
    mock_model = MagicMock()
    mock_model.predict.return_value = predict_scores

    with patch("src.infrastructure.reranker.CrossEncoder", return_value=mock_model):
        reranker = CrossEncoderReranker(_make_settings())

    return reranker, mock_model


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCrossEncoderReranker:
    """Tests fuer CrossEncoderReranker — Reranking via Cross-Encoder."""

    async def test_rerank_returns_sorted_by_score(self):
        """Dokumente werden nach Cross-Encoder Score absteigend sortiert."""
        reranker, _mock = _build_reranker([0.3, 0.9, 0.5])

        docs = [
            _make_doc(source_id="A", text_snippet="Alpha"),
            _make_doc(source_id="B", text_snippet="Beta"),
            _make_doc(source_id="C", text_snippet="Gamma"),
        ]

        result = await reranker.rerank(query="test query", documents=docs, top_k=3)

        assert len(result) == 3
        assert result[0].source_id == "B"  # score 0.9
        assert result[1].source_id == "C"  # score 0.5
        assert result[2].source_id == "A"  # score 0.3

    async def test_rerank_empty_docs(self):
        """Leere Dokumentenliste gibt leere Liste zurueck."""
        reranker, mock_model = _build_reranker([])

        result = await reranker.rerank(query="test", documents=[], top_k=5)

        assert result == []
        mock_model.predict.assert_not_called()

    async def test_rerank_top_k_truncation(self):
        """top_k=2 bei 5 Dokumenten gibt nur 2 zurueck."""
        reranker, _mock = _build_reranker([0.1, 0.9, 0.5, 0.3, 0.7])

        docs = [_make_doc(source_id=str(i)) for i in range(5)]

        result = await reranker.rerank(query="test", documents=docs, top_k=2)

        assert len(result) == 2
        # Top 2 by score: doc[1]=0.9, doc[4]=0.7
        assert result[0].source_id == "1"  # score 0.9
        assert result[1].source_id == "4"  # score 0.7

    async def test_rerank_pairs_correct(self):
        """Cross-Encoder wird mit korrekten (query, text_snippet) Paaren aufgerufen."""
        reranker, mock_model = _build_reranker([0.5, 0.6])

        docs = [
            _make_doc(source_id="X", text_snippet="First snippet"),
            _make_doc(source_id="Y", text_snippet="Second snippet"),
        ]

        await reranker.rerank(query="my query", documents=docs, top_k=2)

        # Verify predict was called with correct pairs
        call_args = mock_model.predict.call_args
        pairs = call_args[0][0]  # first positional arg
        assert pairs == [
            ("my query", "First snippet"),
            ("my query", "Second snippet"),
        ]

    async def test_rerank_replaces_similarity_score(self):
        """Output-Dokumente haben Cross-Encoder Scores, nicht Original-Scores."""
        reranker, _mock = _build_reranker([0.85, 0.42])

        docs = [
            _make_doc(source_id="A", similarity_score=0.99, text_snippet="First"),
            _make_doc(source_id="B", similarity_score=0.10, text_snippet="Second"),
        ]

        result = await reranker.rerank(query="test", documents=docs, top_k=2)

        # Cross-encoder scores should replace original similarity_score
        assert result[0].source_id == "A"
        assert result[0].similarity_score == pytest.approx(0.85)
        assert result[1].source_id == "B"
        assert result[1].similarity_score == pytest.approx(0.42)

        # Confirm original scores are NOT preserved
        assert result[0].similarity_score != 0.99
        assert result[1].similarity_score != 0.10
