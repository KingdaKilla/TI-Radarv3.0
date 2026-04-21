"""Embedding Use Case — Batch-Population von Embeddings.

Orchestriert den Ablauf:
1. Unembedded Dokumente aus der DB lesen
2. Embeddings via OpenAI API erzeugen
3. Embeddings in die DB schreiben

Keine Abhaengigkeit zu gRPC, Protobuf oder HTTP.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import structlog

from src.domain.ports import (
    ChunkingPort,
    ChunkRepositoryPort,
    EmbeddingProviderPort,
    EmbeddingRepositoryPort,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Result Dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EmbedResult:
    """Ergebnis eines Embedding-Batch-Laufs."""

    embedded_count: int
    remaining_count: int
    total_count: int
    elapsed_seconds: float
    status: str  # "running" | "completed" | "error"


# ---------------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------------

class EmbedDocuments:
    """Orchestriert die Batch-Population von Embeddings.

    Transportunabhaengig: nimmt primitive Parameter, gibt EmbedResult zurueck.
    Keine Abhaengigkeit zu gRPC, Protobuf oder HTTP.
    """

    def __init__(
        self,
        repo: EmbeddingRepositoryPort,
        embedder: EmbeddingProviderPort,
    ) -> None:
        self._repo = repo
        self._embedder = embedder

    async def execute(
        self,
        source: str,
        batch_size: int = 1000,
        year_from: int | None = None,
    ) -> EmbedResult:
        """Einen Batch Embeddings erzeugen und speichern.

        Args:
            source: "patents", "projects" oder "papers"
            batch_size: Maximale Anzahl Dokumente pro Batch
            year_from: Optional — nur fuer patents: Filter publication_year >= year_from

        Returns:
            EmbedResult mit Statistiken zum Batch-Lauf
        """
        t0 = time.monotonic()

        # 1. Unembedded Dokumente lesen
        docs = await self._repo.fetch_unembedded(source, batch_size, year_from)

        if not docs:
            total, embedded = await self._repo.count_status(source)
            return EmbedResult(
                embedded_count=0,
                remaining_count=total - embedded,
                total_count=total,
                elapsed_seconds=time.monotonic() - t0,
                status="completed",
            )

        # 2. Embeddings erzeugen
        ids, texts = zip(*docs)
        vectors = await self._embedder.embed_batch(list(texts))

        # 3. Embeddings speichern
        pairs = list(zip(ids, vectors))
        stored = await self._repo.store_embeddings(source, pairs)

        # 4. Status abfragen
        total, embedded = await self._repo.count_status(source)
        remaining = total - embedded

        elapsed = time.monotonic() - t0
        logger.info(
            "embedding_batch_abgeschlossen",
            source=source,
            stored=stored,
            remaining=remaining,
            total=total,
            elapsed_s=round(elapsed, 2),
        )

        return EmbedResult(
            embedded_count=stored,
            remaining_count=remaining,
            total_count=total,
            elapsed_seconds=elapsed,
            status="running" if remaining > 0 else "completed",
        )

    async def get_status(self, source: str) -> tuple[int, int]:
        """Status-Abfrage: (total, embedded).

        Args:
            source: "patents", "projects" oder "papers"

        Returns:
            Tuple (total_with_text, already_embedded)
        """
        return await self._repo.count_status(source)


# ---------------------------------------------------------------------------
# Result Dataclass fuer ChunkAndEmbed
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ChunkEmbedResult:
    """Ergebnis eines Chunk-und-Embed-Batch-Laufs."""

    chunks_created: int
    docs_processed: int
    remaining_docs: int
    total_docs: int
    elapsed_seconds: float
    status: str  # "running" | "completed"


# ---------------------------------------------------------------------------
# Use Case: ChunkAndEmbed
# ---------------------------------------------------------------------------

class ChunkAndEmbed:
    """Orchestriert: fetch docs -> chunk -> embed -> store chunks.

    Transportunabhaengig: nimmt primitive Parameter, gibt ChunkEmbedResult zurueck.
    Keine Abhaengigkeit zu gRPC, Protobuf oder HTTP.
    """

    def __init__(
        self,
        chunk_repo: ChunkRepositoryPort,
        chunker: ChunkingPort,
        embedder: EmbeddingProviderPort,
    ) -> None:
        self._chunk_repo = chunk_repo
        self._chunker = chunker
        self._embedder = embedder

    async def execute(
        self,
        source: str,
        batch_size: int = 100,
        year_from: int | None = None,
    ) -> ChunkEmbedResult:
        """Einen Batch Dokumente chunken, embedden und speichern.

        Args:
            source: "patents", "projects" oder "papers"
            batch_size: Maximale Anzahl Dokumente pro Batch
            year_from: Optional — nur fuer patents: Filter publication_year >= year_from

        Returns:
            ChunkEmbedResult mit Statistiken zum Batch-Lauf
        """
        t0 = time.monotonic()

        # 1. Unchunked Dokumente lesen
        docs = await self._chunk_repo.fetch_unchunked_docs(source, batch_size, year_from)

        if not docs:
            total, chunked = await self._chunk_repo.count_chunk_status(source)
            return ChunkEmbedResult(
                chunks_created=0,
                docs_processed=0,
                remaining_docs=total - chunked,
                total_docs=total,
                elapsed_seconds=time.monotonic() - t0,
                status="completed",
            )

        # 2. Alle Dokumente chunken
        all_chunks: list[tuple[str, int, str]] = []  # (source_id, chunk_index, chunk_text)
        for source_id, text in docs:
            chunks = self._chunker.chunk_text(text)
            for idx, chunk_text in enumerate(chunks):
                all_chunks.append((source_id, idx, chunk_text))

        # 3. Alle Chunk-Texte embedden (nur wenn Chunks vorhanden)
        if all_chunks:
            texts = [c[2] for c in all_chunks]
            vectors = await self._embedder.embed_batch(texts)

            # 4. Chunks mit Embeddings speichern
            records = [
                (sid, idx, txt, vec)
                for (sid, idx, txt), vec in zip(all_chunks, vectors)
            ]
            stored = await self._chunk_repo.store_chunks_with_embeddings(source, records)
        else:
            stored = 0

        # 5. Status abfragen
        total, chunked = await self._chunk_repo.count_chunk_status(source)
        remaining = total - chunked

        elapsed = time.monotonic() - t0
        logger.info(
            "chunk_embed_batch_abgeschlossen",
            source=source,
            chunks_created=stored,
            docs_processed=len(docs),
            remaining=remaining,
            total=total,
            elapsed_s=round(elapsed, 2),
        )

        return ChunkEmbedResult(
            chunks_created=stored,
            docs_processed=len(docs),
            remaining_docs=remaining,
            total_docs=total,
            elapsed_seconds=elapsed,
            status="running" if remaining > 0 else "completed",
        )
