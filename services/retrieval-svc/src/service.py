"""RetrievalServicer — duenner gRPC-Adapter.

Extrahiert Request-Parameter aus Protobuf, delegiert Geschaeftslogik
an den RetrieveDocuments Use Case und mappt das RetrievalResult
zurueck auf gRPC-/dict-Responses.
"""
from __future__ import annotations

import time
from typing import Any

import asyncpg
import structlog

# --- gRPC-Imports (try/except, da Stubs noch nicht generiert) ---
try:
    import grpc
    from grpc import aio as grpc_aio
except ImportError:
    grpc = None  # type: ignore[assignment]
    grpc_aio = None  # type: ignore[assignment]

try:
    from shared.generated.python import retrieval_pb2
    from shared.generated.python import retrieval_pb2_grpc
except ImportError:
    retrieval_pb2 = None  # type: ignore[assignment]
    retrieval_pb2_grpc = None  # type: ignore[assignment]

from src.config import Settings
from src.domain.ports import QueryEmbeddingPort
from src.infrastructure.query_embedder import QueryEmbedder
from src.infrastructure.remote_query_embedder import RemoteQueryEmbedder
from src.infrastructure.reranker import CrossEncoderReranker
from src.infrastructure.repository import VectorSearchRepository
from src.infrastructure.sparse_repository import SparseSearchRepository
from src.use_case import RetrieveDocuments, RetrievalResult

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper: Basis-Klasse ermitteln (gRPC Servicer oder object)
# ---------------------------------------------------------------------------
def _get_base_class() -> type:
    """Gibt die gRPC-Servicer-Basisklasse zurueck, oder object als Fallback."""
    if retrieval_pb2_grpc is not None:
        return retrieval_pb2_grpc.RetrievalServiceServicer  # type: ignore[return-value]
    return object


class RetrievalServicer(_get_base_class()):  # type: ignore[misc]
    """gRPC-Servicer fuer den Retrieval-Service.

    Duenner Adapter: extrahiert Parameter, delegiert an Use Case,
    mappt Ergebnis auf gRPC-Response.
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        settings: Settings | None = None,
    ) -> None:
        self._pool = pool
        self._settings = settings or Settings()
        sparse_search = SparseSearchRepository(pool)
        reranker = CrossEncoderReranker(self._settings)
        embedder: QueryEmbeddingPort
        if self._settings.embedding_provider == "remote":
            embedder = RemoteQueryEmbedder(self._settings)
            logger.info("query_embedder_remote", tei_url=self._settings.tei_url)
        else:
            embedder = QueryEmbedder(self._settings)
            logger.info("query_embedder_lokal", model=self._settings.embedding_model)
        # v3.6.0/Ξ-7: Incremental-Embedder für Dokumente direkt aus dem
        # lokalen QueryEmbedder-Modell (das Modell ist sowieso geladen).
        # Kein separater embedding-svc-Call nötig, spart Latenz und
        # vermeidet eine zusätzliche gRPC-Dependency.
        from src.infrastructure.repository import IncrementalEmbedder
        incremental = (
            IncrementalEmbedder(embedder)
            if hasattr(embedder, "embed_batch")
            else None
        )
        dense_search = VectorSearchRepository(pool, embedder=incremental)
        self._use_case = RetrieveDocuments(
            dense_search=dense_search,
            sparse_search=sparse_search,
            reranker=reranker,
            embedder=embedder,
        )

    async def Retrieve(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """Semantische Suche ausfuehren.

        Args:
            request: tip.retrieval.RetrievalRequest Protobuf-Message
            context: gRPC ServicerContext

        Returns:
            tip.retrieval.RetrievalResponse Protobuf-Message oder dict
        """
        t0 = time.monotonic()

        technology = request.technology if hasattr(request, "technology") else ""
        query = request.query if hasattr(request, "query") else ""
        top_k = (
            request.top_k
            if hasattr(request, "top_k") and request.top_k
            else self._settings.top_k
        )
        sources = list(request.sources) if hasattr(request, "sources") and request.sources else None

        logger.info(
            "retrieve_gestartet",
            technology=technology,
            query_len=len(query),
            top_k=top_k,
            sources=sources,
        )

        # --- Validierung ---
        if not query or not query.strip():
            if context is not None and grpc is not None:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "Feld 'query' darf nicht leer sein",
                )
            return self._build_response(
                RetrievalResult(documents=[], query_embedding_ms=0, search_ms=0, rerank_ms=0),
            )

        try:
            result = await self._use_case.execute(
                technology=technology,
                query=query,
                top_k=top_k,
                sources=sources,
            )
        except Exception as e:
            logger.error("retrieve_fehler", error=str(e))
            if context is not None and grpc is not None:
                await context.abort(grpc.StatusCode.INTERNAL, str(e))
            return self._build_response(
                RetrievalResult(documents=[], query_embedding_ms=0, search_ms=0, rerank_ms=0),
            )

        return self._build_response(result)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_response(result: RetrievalResult) -> Any:
        """Response aus RetrievalResult bauen (Protobuf oder dict-Fallback)."""
        if retrieval_pb2 is not None:
            docs = []
            for doc in result.documents:
                docs.append(
                    retrieval_pb2.RetrievedDocument(
                        source=doc.source,
                        source_id=doc.source_id,
                        title=doc.title,
                        text_snippet=doc.text_snippet,
                        similarity_score=doc.similarity_score,
                        metadata=doc.metadata,
                    )
                )
            return retrieval_pb2.RetrievalResponse(
                documents=docs,
                query_embedding_ms=result.query_embedding_ms,
                search_ms=result.search_ms,
            )
        return {
            "documents": [
                {
                    "source": doc.source,
                    "source_id": doc.source_id,
                    "title": doc.title,
                    "text_snippet": doc.text_snippet,
                    "similarity_score": doc.similarity_score,
                    "metadata": doc.metadata,
                }
                for doc in result.documents
            ],
            "query_embedding_ms": result.query_embedding_ms,
            "search_ms": result.search_ms,
            "rerank_ms": result.rerank_ms,
        }
