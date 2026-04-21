"""Cross-Encoder Reranker (Nogueira & Cho 2019, Maharajan et al. 2026)."""
from __future__ import annotations

import asyncio
import functools

import structlog
from sentence_transformers import CrossEncoder

from src.config import Settings
from src.domain.ports import RerankingPort, RetrievedDoc

logger = structlog.get_logger()


class CrossEncoderReranker(RerankingPort):
    """Rerankt Dokumente via Cross-Encoder (ms-marco-MiniLM-L-6-v2)."""

    def __init__(self, settings: Settings) -> None:
        self._model = CrossEncoder(settings.reranker_model)
        logger.info("cross_encoder_geladen", model=settings.reranker_model)

    async def rerank(
        self,
        query: str,
        documents: list[RetrievedDoc],
        top_k: int,
    ) -> list[RetrievedDoc]:
        if not documents:
            return []

        # Build query-document pairs for cross-encoder
        pairs = [(query, doc.text_snippet) for doc in documents]

        # Run sync predict in executor to not block event loop
        loop = asyncio.get_running_loop()
        scores = await loop.run_in_executor(
            None,
            functools.partial(self._model.predict, pairs),
        )

        # Combine docs with scores, sort descending, return top_k
        scored = sorted(
            zip(documents, scores),
            key=lambda x: float(x[1]),
            reverse=True,
        )

        reranked = []
        for doc, score in scored[:top_k]:
            # Create new doc with cross-encoder score replacing similarity_score
            reranked.append(
                RetrievedDoc(
                    source=doc.source,
                    source_id=doc.source_id,
                    title=doc.title,
                    text_snippet=doc.text_snippet,
                    similarity_score=float(score),
                    metadata=doc.metadata,
                )
            )

        logger.info(
            "reranking_abgeschlossen",
            input_count=len(documents),
            output_count=len(reranked),
            top_score=round(float(scored[0][1]), 4) if scored else 0,
        )

        return reranked
