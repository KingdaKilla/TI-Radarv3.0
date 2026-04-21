"""Tests fuer Remote Embedding-Provider (TEI auf dediziertem GPU-Pod)."""
from __future__ import annotations

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.config import Settings


def _make_settings(**overrides) -> Settings:
    """Erzeugt Settings mit TEI-Defaults fuer Tests."""
    defaults = {
        "embedding_model": "BAAI/bge-large-en-v1.5",
        "embedding_dimensions": 1024,
        "device": "cpu",
        "embedding_provider": "remote",
        "tei_url": "https://test-pod-8000.proxy.runpod.net",
        "tei_batch_size": 3,
        "tei_timeout_s": 30.0,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def _mock_response(status_code: int = 200, embeddings: list[list[float]] | None = None):
    """Erzeugt ein Mock-httpx-Response-Objekt (TEI-Format: direkt Liste von Vektoren)."""
    resp = MagicMock()
    resp.status_code = status_code
    if embeddings is not None:
        resp.json.return_value = embeddings
    else:
        resp.json.return_value = {"error": "something went wrong"}
    resp.text = "mock response text"
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp,
        )
    return resp


class TestRemoteEmbedder:
    """Tests fuer RemoteEmbedder (TEI API auf dediziertem Pod)."""

    @patch("src.infrastructure.remote_embedder.httpx.AsyncClient")
    async def test_embed_batch_returns_vectors(self, mock_client_class):
        """embed_batch sendet korrekte Anfrage und gibt Vektoren zurueck."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        vectors = [[0.1] * 1024, [0.2] * 1024]
        mock_client.post.return_value = _mock_response(200, embeddings=vectors)

        from src.infrastructure.remote_embedder import RemoteEmbedder
        settings = _make_settings()
        embedder = RemoteEmbedder(settings)

        result = await embedder.embed_batch(["text1", "text2"])

        assert len(result) == 2
        assert len(result[0]) == 1024
        assert result == vectors

        # Korrekte URL und Payload pruefen (TEI-Format, kein Auth)
        mock_client.post.assert_called_once_with(
            "https://test-pod-8000.proxy.runpod.net/embed",
            json={"inputs": ["text1", "text2"]},
            timeout=30.0,
        )

    @patch("src.infrastructure.remote_embedder.httpx.AsyncClient")
    async def test_embed_batch_empty_input(self, mock_client_class):
        """Leere Eingabe gibt leere Liste zurueck, kein API-Aufruf."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        from src.infrastructure.remote_embedder import RemoteEmbedder
        settings = _make_settings()
        embedder = RemoteEmbedder(settings)

        result = await embedder.embed_batch([])

        assert result == []
        mock_client.post.assert_not_called()

    @patch("src.infrastructure.remote_embedder.httpx.AsyncClient")
    async def test_close_closes_client(self, mock_client_class):
        """close() ruft aclose() auf dem httpx-Client auf."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        from src.infrastructure.remote_embedder import RemoteEmbedder
        settings = _make_settings()
        embedder = RemoteEmbedder(settings)

        await embedder.close()

        mock_client.aclose.assert_awaited_once()

    @patch("src.infrastructure.remote_embedder.httpx.AsyncClient")
    async def test_sub_batching(self, mock_client_class):
        """Input groesser als batch_size wird in Sub-Batches aufgeteilt."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # batch_size=3, 7 Texte -> 3 Requests (3+3+1)
        settings = _make_settings(tei_batch_size=3)
        dim = 1024

        # Drei Responses fuer drei Sub-Batches (TEI gibt direkt Liste zurueck)
        mock_client.post.side_effect = [
            _mock_response(200, embeddings=[[0.1] * dim] * 3),
            _mock_response(200, embeddings=[[0.2] * dim] * 3),
            _mock_response(200, embeddings=[[0.3] * dim] * 1),
        ]

        from src.infrastructure.remote_embedder import RemoteEmbedder
        embedder = RemoteEmbedder(settings)

        texts = [f"text{i}" for i in range(7)]
        result = await embedder.embed_batch(texts)

        # 7 Vektoren insgesamt
        assert len(result) == 7
        # 3 API-Aufrufe
        assert mock_client.post.call_count == 3

        # Pruefen, dass die Sub-Batches korrekt aufgeteilt wurden
        calls = mock_client.post.call_args_list
        assert calls[0].kwargs["json"]["inputs"] == ["text0", "text1", "text2"]
        assert calls[1].kwargs["json"]["inputs"] == ["text3", "text4", "text5"]
        assert calls[2].kwargs["json"]["inputs"] == ["text6"]

    @patch("src.infrastructure.remote_embedder.httpx.AsyncClient")
    async def test_tei_error_raises(self, mock_client_class):
        """Nicht-200-Response loest RuntimeError aus."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_client.post.return_value = _mock_response(500)

        from src.infrastructure.remote_embedder import RemoteEmbedder
        settings = _make_settings()
        embedder = RemoteEmbedder(settings)

        with pytest.raises(RuntimeError, match="TEI"):
            await embedder.embed_batch(["some text"])

    @patch("src.infrastructure.remote_embedder.httpx.AsyncClient")
    async def test_connection_error_raises(self, mock_client_class):
        """Netzwerkfehler (Timeout, DNS etc.) loest RuntimeError aus."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_client.post.side_effect = httpx.RequestError("connection refused")

        from src.infrastructure.remote_embedder import RemoteEmbedder
        settings = _make_settings()
        embedder = RemoteEmbedder(settings)

        with pytest.raises(RuntimeError, match="Verbindungsfehler"):
            await embedder.embed_batch(["some text"])
