"""Lokaler Embedding-Provider via sentence-transformers (GPU/CPU)."""
from __future__ import annotations

import structlog
import torch
from sentence_transformers import SentenceTransformer

from src.config import Settings
from src.domain.ports import EmbeddingProviderPort

logger = structlog.get_logger()


class LocalEmbedder(EmbeddingProviderPort):
    """Sentence-Transformers Embedding (lokal, GPU-beschleunigt)."""

    def __init__(self, settings: Settings) -> None:
        device = settings.device
        if device == "cuda" and not torch.cuda.is_available():
            logger.warning("cuda_nicht_verfuegbar_fallback_cpu")
            device = "cpu"

        self._model = SentenceTransformer(settings.embedding_model, device=device)
        self._device = device
        logger.info(
            "embedding_model_geladen",
            model=settings.embedding_model,
            device=device,
            gpu=torch.cuda.get_device_name(0) if device == "cuda" else "none",
        )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self._model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            batch_size=256,  # GPU can handle larger batches
        )
        vectors = [emb.tolist() for emb in embeddings]
        logger.info("embeddings_erzeugt", count=len(vectors), device=self._device)
        return vectors

    async def close(self) -> None:
        pass
