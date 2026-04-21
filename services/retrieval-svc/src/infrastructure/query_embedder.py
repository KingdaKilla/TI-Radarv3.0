"""Lokaler Query-Embedder via sentence-transformers."""
from __future__ import annotations

from sentence_transformers import SentenceTransformer

from src.config import Settings
from src.domain.ports import QueryEmbeddingPort


class QueryEmbedder(QueryEmbeddingPort):
    """Sentence-Transformers Embedding fuer einzelne Queries (lokal).

    v3.6.0: Unterstuetzt jetzt auch Batch-Embedding via `embed_batch()` fuer
    die Incremental-Pre-Computation-Strategie im retrieval-svc.
    """

    def __init__(self, settings: Settings) -> None:
        self._model = SentenceTransformer(settings.embedding_model)

    async def embed_query(self, text: str) -> list[float]:
        # e5-Modelle: "query: "-Präfix für Such-Anfragen
        prefixed = f"query: {text}" if "e5" in str(self._model).lower() else text
        embedding = self._model.encode(
            [prefixed], show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True,
        )
        return embedding[0].tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch-Embedding für Incremental-Pre-Computation (Bug v3.6.0).

        Nutzt denselben Modell-Cache, kein separater gRPC-Call zum
        embedding-svc nötig. Wichtig: Dokumente (nicht Queries) bekommen
        bei e5-Modellen das `passage: `-Präfix.
        """
        if not texts:
            return []
        is_e5 = "e5" in str(self._model).lower()
        prefixed = [f"passage: {t}" if is_e5 else t for t in texts]
        embeddings = self._model.encode(
            prefixed,
            batch_size=min(64, len(prefixed)),
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return [e.tolist() for e in embeddings]

    async def close(self) -> None:
        pass
