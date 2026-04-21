"""Retrieval Use Case — 3-Stufen-Pipeline fuer RAG.

Orchestriert den Ablauf:
1. Query-Embedding erzeugen
2. Parallel: Dense Search (pgvector cosine) + Sparse Search (BM25/tsvector)
3. RRF-Fusion (k=60) -> Top-N Kandidaten
4. Cross-Encoder Reranking -> Top-K

Keine Abhaengigkeit zu gRPC, Protobuf oder HTTP.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import structlog

from src.domain.ports import (
    QueryEmbeddingPort,
    RerankingPort,
    RetrievedDoc,
    SparseSearchPort,
    VectorSearchPort,
)
from src.fusion import reciprocal_rank_fusion

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Result Dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Ergebnis einer 3-stufigen Retrieval-Pipeline."""

    documents: list[RetrievedDoc]
    query_embedding_ms: float
    search_ms: float
    rerank_ms: float


# ---------------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------------

class RetrieveDocuments:
    """Orchestriert die 3-stufige Retrieval-Pipeline fuer RAG.

    Stufe 1: Dense + Sparse Search parallel
    Stufe 2: RRF-Fusion -> Top-N Kandidaten
    Stufe 3: Cross-Encoder Reranking -> Top-K

    Transportunabhaengig: nimmt primitive Parameter, gibt RetrievalResult zurueck.
    Keine Abhaengigkeit zu gRPC, Protobuf oder HTTP.
    """

    def __init__(
        self,
        dense_search: VectorSearchPort,
        sparse_search: SparseSearchPort,
        reranker: RerankingPort,
        embedder: QueryEmbeddingPort,
        *,
        rrf_k: int = 60,
        dense_top_k: int = 50,
        sparse_top_k: int = 50,
        fusion_top_n: int = 20,
    ) -> None:
        self._dense_search = dense_search
        self._sparse_search = sparse_search
        self._reranker = reranker
        self._embedder = embedder
        self._rrf_k = rrf_k
        self._dense_top_k = dense_top_k
        self._sparse_top_k = sparse_top_k
        self._fusion_top_n = fusion_top_n

    async def execute(
        self,
        technology: str,
        query: str,
        top_k: int = 10,
        sources: list[str] | None = None,
        threshold: float = 0.3,
    ) -> RetrievalResult:
        """3-stufige Retrieval-Pipeline ausfuehren.

        Args:
            technology: Technologie-Suchbegriff fuer Full-Text-Filter
            query: Freie Suchanfrage fuer Embedding + Sparse Search
            top_k: Maximale Anzahl zurueckgegebener Dokumente (nach Reranking)
            sources: Zu durchsuchende Quellen (None = alle)
            threshold: Minimale Cosine-Similarity fuer Dense Search

        Returns:
            RetrievalResult mit Dokumenten und Timing-Informationen
        """
        if sources is None:
            sources = ["patents", "projects", "papers"]

        # 1. Query-Embedding erzeugen
        t0 = time.monotonic()
        query_vector = await self._embedder.embed_query(query)
        embed_ms = (time.monotonic() - t0) * 1000

        # 2. Parallel: Dense + Sparse Search
        t1 = time.monotonic()
        dense_results, sparse_results = await asyncio.gather(
            self._dense_search.search(
                query_vector=query_vector,
                technology=technology,
                sources=sources,
                top_k=self._dense_top_k,
                threshold=threshold,
            ),
            self._sparse_search.search(
                query=query,
                sources=sources,
                top_k=self._sparse_top_k,
            ),
        )
        search_ms = (time.monotonic() - t1) * 1000

        # 3. Build lookup dict: "source:source_id" -> RetrievedDoc
        #    Dense docs take priority over sparse for the same key.
        doc_lookup: dict[str, RetrievedDoc] = {}
        for doc in sparse_results:
            key = f"{doc.source}:{doc.source_id}"
            doc_lookup[key] = doc
        for doc in dense_results:
            key = f"{doc.source}:{doc.source_id}"
            doc_lookup[key] = doc  # overwrites sparse if same key

        # 4. RRF Fusion
        dense_ids = [f"{d.source}:{d.source_id}" for d in dense_results]
        sparse_ids = [f"{d.source}:{d.source_id}" for d in sparse_results]

        fused = reciprocal_rank_fusion(
            ranked_lists=[dense_ids, sparse_ids],
            k=self._rrf_k,
            top_n=self._fusion_top_n,
        )

        # 5. Map fused IDs back to RetrievedDoc objects
        fused_docs = [doc_lookup[doc_id] for doc_id, _score in fused if doc_id in doc_lookup]

        # 6. Cross-Encoder Reranking -> top_k
        t2 = time.monotonic()
        reranked_docs = await self._reranker.rerank(
            query=query,
            documents=fused_docs,
            top_k=top_k,
        )
        rerank_ms = (time.monotonic() - t2) * 1000

        logger.info(
            "retrieval_pipeline_abgeschlossen",
            technology=technology,
            query_len=len(query),
            sources=sources,
            dense_found=len(dense_results),
            sparse_found=len(sparse_results),
            fused_candidates=len(fused_docs),
            reranked=len(reranked_docs),
            top_k=top_k,
            embed_ms=round(embed_ms, 1),
            search_ms=round(search_ms, 1),
            rerank_ms=round(rerank_ms, 1),
        )

        return RetrievalResult(
            documents=reranked_docs,
            query_embedding_ms=embed_ms,
            search_ms=search_ms,
            rerank_ms=rerank_ms,
        )
