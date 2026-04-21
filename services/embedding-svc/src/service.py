"""EmbeddingServicer — duenner gRPC-Adapter.

Extrahiert Request-Parameter aus Protobuf, delegiert Geschaeftslogik
an den EmbedDocuments Use Case und mappt das EmbedResult
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
    from shared.generated.python import embedding_pb2
    from shared.generated.python import embedding_pb2_grpc
except ImportError:
    embedding_pb2 = None  # type: ignore[assignment]
    embedding_pb2_grpc = None  # type: ignore[assignment]

from src.config import Settings
from src.domain.ports import EmbeddingProviderPort
from src.infrastructure.chunker import RecursiveChunker
from src.infrastructure.local_embedder import LocalEmbedder
from src.infrastructure.remote_embedder import RemoteEmbedder
from src.infrastructure.repository import ChunkRepository, EmbeddingRepository
from src.use_case import ChunkAndEmbed, ChunkEmbedResult, EmbedDocuments, EmbedResult

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper: Basis-Klasse ermitteln (gRPC Servicer oder object)
# ---------------------------------------------------------------------------
def _get_base_class() -> type:
    """Gibt die gRPC-Servicer-Basisklasse zurueck, oder object als Fallback."""
    if embedding_pb2_grpc is not None:
        return embedding_pb2_grpc.EmbeddingServiceServicer  # type: ignore[return-value]
    return object


class EmbeddingServicer(_get_base_class()):  # type: ignore[misc]
    """gRPC-Servicer fuer den Embedding-Service.

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
        repo = EmbeddingRepository(pool)

        # --- Provider-Auswahl: lokal oder remote (TEI auf GPU-Pod) ---
        embedder: EmbeddingProviderPort
        if self._settings.embedding_provider == "remote":
            embedder = RemoteEmbedder(self._settings)
            logger.info("embedding_provider_remote_aktiv", tei_url=self._settings.tei_url)
        else:
            embedder = LocalEmbedder(self._settings)
            logger.info("embedding_provider_lokal_aktiv")

        self._use_case = EmbedDocuments(repo=repo, embedder=embedder)

        # --- ChunkAndEmbed Use Case ---
        chunk_repo = ChunkRepository(pool)
        chunker = RecursiveChunker()
        self._chunk_and_embed = ChunkAndEmbed(
            chunk_repo=chunk_repo,
            chunker=chunker,
            embedder=embedder,
        )

    async def EmbedBatch(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """Einen Batch Embeddings erzeugen und speichern.

        Args:
            request: tip.embedding.EmbedBatchRequest Protobuf-Message
            context: gRPC ServicerContext

        Returns:
            tip.embedding.EmbedBatchResponse Protobuf-Message oder dict
        """
        t0 = time.monotonic()

        source = request.source if hasattr(request, "source") else "patents"
        batch_size = request.batch_size if hasattr(request, "batch_size") and request.batch_size else self._settings.batch_size
        year_from = request.year_from if hasattr(request, "year_from") and request.year_from else None

        logger.info(
            "embed_batch_gestartet",
            source=source,
            batch_size=batch_size,
            year_from=year_from,
        )

        # --- Validierung ---
        if not source or not source.strip():
            if context is not None and grpc is not None:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "Feld 'source' darf nicht leer sein",
                )
            return self._build_result_response(
                EmbedResult(0, 0, 0, time.monotonic() - t0, "error"),
            )

        try:
            result = await self._use_case.execute(
                source=source,
                batch_size=batch_size,
                year_from=year_from,
            )
        except ValueError as e:
            if context is not None and grpc is not None:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
            return self._build_result_response(
                EmbedResult(0, 0, 0, time.monotonic() - t0, "error"),
            )

        return self._build_result_response(result)

    async def GetEmbeddingStatus(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """Status-Abfrage fuer Embedding-Fortschritt.

        Args:
            request: tip.embedding.EmbeddingStatusRequest Protobuf-Message
            context: gRPC ServicerContext

        Returns:
            tip.embedding.EmbeddingStatusResponse Protobuf-Message oder dict
        """
        source = request.source if hasattr(request, "source") else "patents"

        try:
            total, embedded = await self._use_case.get_status(source)
        except ValueError as e:
            if context is not None and grpc is not None:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
            return self._build_status_response(0, 0, source)

        return self._build_status_response(total, embedded, source)

    async def ChunkAndEmbedBatch(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """Dokumente chunken, embedden und als Chunks speichern.

        Args:
            request: Request mit source, batch_size, year_from Feldern
            context: gRPC ServicerContext

        Returns:
            dict mit ChunkEmbedResult-Statistiken
        """
        source = request.source if hasattr(request, "source") else "patents"
        batch_size = (
            request.batch_size
            if hasattr(request, "batch_size") and request.batch_size
            else 100
        )
        year_from = (
            request.year_from
            if hasattr(request, "year_from") and request.year_from
            else None
        )

        logger.info(
            "chunk_embed_batch_gestartet",
            source=source,
            batch_size=batch_size,
            year_from=year_from,
        )

        result = await self._chunk_and_embed.execute(
            source=source,
            batch_size=batch_size,
            year_from=year_from,
        )

        return {
            "chunks_created": result.chunks_created,
            "docs_processed": result.docs_processed,
            "remaining_docs": result.remaining_docs,
            "total_docs": result.total_docs,
            "elapsed_seconds": result.elapsed_seconds,
            "status": result.status,
        }

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_result_response(result: EmbedResult) -> Any:
        """Response aus EmbedResult bauen (Protobuf oder dict-Fallback)."""
        if embedding_pb2 is not None:
            return embedding_pb2.EmbedBatchResponse(
                embedded_count=result.embedded_count,
                remaining_count=result.remaining_count,
                total_count=result.total_count,
                elapsed_seconds=result.elapsed_seconds,
                status=result.status,
            )
        return {
            "embedded_count": result.embedded_count,
            "remaining_count": result.remaining_count,
            "total_count": result.total_count,
            "elapsed_seconds": result.elapsed_seconds,
            "status": result.status,
        }

    @staticmethod
    def _build_status_response(total: int, embedded: int, source: str) -> Any:
        """Status-Response bauen (Protobuf oder dict-Fallback)."""
        if embedding_pb2 is not None:
            return embedding_pb2.EmbeddingStatusResponse(
                source=source,
                total_count=total,
                embedded_count=embedded,
                remaining_count=total - embedded,
            )
        return {
            "source": source,
            "total_count": total,
            "embedded_count": embedded,
            "remaining_count": total - embedded,
        }
