"""Tests fuer lokalen Embedding-Provider."""
import pytest
from unittest.mock import patch, MagicMock
import numpy as np

from src.config import Settings


class TestLocalEmbedder:
    def _make_settings(self, **overrides):
        defaults = {"embedding_model": "all-MiniLM-L6-v2", "embedding_dimensions": 384, "device": "cpu"}
        defaults.update(overrides)
        return Settings(**defaults)

    @patch("src.infrastructure.local_embedder.torch")
    @patch("src.infrastructure.local_embedder.SentenceTransformer")
    async def test_embed_batch_returns_vectors(self, mock_st_class, mock_torch):
        mock_torch.cuda.is_available.return_value = False
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1] * 384, [0.2] * 384])
        mock_st_class.return_value = mock_model

        from src.infrastructure.local_embedder import LocalEmbedder
        settings = self._make_settings()
        embedder = LocalEmbedder(settings)

        result = await embedder.embed_batch(["text1", "text2"])
        assert len(result) == 2
        assert len(result[0]) == 384
        mock_model.encode.assert_called_once()

    @patch("src.infrastructure.local_embedder.torch")
    @patch("src.infrastructure.local_embedder.SentenceTransformer")
    async def test_embed_batch_empty_input(self, mock_st_class, mock_torch):
        mock_torch.cuda.is_available.return_value = False
        mock_st_class.return_value = MagicMock()

        from src.infrastructure.local_embedder import LocalEmbedder
        settings = self._make_settings()
        embedder = LocalEmbedder(settings)

        result = await embedder.embed_batch([])
        assert result == []

    @patch("src.infrastructure.local_embedder.torch")
    @patch("src.infrastructure.local_embedder.SentenceTransformer")
    async def test_close_does_not_raise(self, mock_st_class, mock_torch):
        mock_torch.cuda.is_available.return_value = False
        mock_st_class.return_value = MagicMock()

        from src.infrastructure.local_embedder import LocalEmbedder
        settings = self._make_settings()
        embedder = LocalEmbedder(settings)
        await embedder.close()  # Should not raise

    @patch("src.infrastructure.local_embedder.torch")
    @patch("src.infrastructure.local_embedder.SentenceTransformer")
    async def test_cuda_fallback_when_unavailable(self, mock_st_class, mock_torch):
        mock_torch.cuda.is_available.return_value = False
        mock_st_class.return_value = MagicMock()

        from src.infrastructure.local_embedder import LocalEmbedder
        settings = self._make_settings(device="cuda")
        embedder = LocalEmbedder(settings)
        # Should fall back to CPU without crashing
        assert embedder._device == "cpu"

    @patch("src.infrastructure.local_embedder.torch")
    @patch("src.infrastructure.local_embedder.SentenceTransformer")
    async def test_cuda_used_when_available(self, mock_st_class, mock_torch):
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "NVIDIA GeForce RTX 4070 SUPER"
        mock_st_class.return_value = MagicMock()

        from src.infrastructure.local_embedder import LocalEmbedder
        settings = self._make_settings(device="cuda")
        embedder = LocalEmbedder(settings)
        assert embedder._device == "cuda"
        mock_st_class.assert_called_once_with("all-MiniLM-L6-v2", device="cuda")

    @patch("src.infrastructure.local_embedder.torch")
    @patch("src.infrastructure.local_embedder.SentenceTransformer")
    async def test_batch_size_256_for_gpu(self, mock_st_class, mock_torch):
        mock_torch.cuda.is_available.return_value = False
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1] * 384])
        mock_st_class.return_value = mock_model

        from src.infrastructure.local_embedder import LocalEmbedder
        settings = self._make_settings()
        embedder = LocalEmbedder(settings)

        await embedder.embed_batch(["test"])
        call_kwargs = mock_model.encode.call_args[1]
        assert call_kwargs["batch_size"] == 256
