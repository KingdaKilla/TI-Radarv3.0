"""Port-Interfaces fuer Embedding-Service (Hexagonal Architecture)."""
from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProviderPort(ABC):
    """Abstraktes Interface fuer Embedding-Provider (sentence-transformers, etc.)."""

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Erzeugt Embeddings fuer eine Liste von Texten."""

    @abstractmethod
    async def close(self) -> None:
        """Resourcen freigeben."""


class EmbeddingRepositoryPort(ABC):
    """Abstraktes Interface fuer Embedding-Persistenz."""

    @abstractmethod
    async def fetch_unembedded(
        self, source: str, batch_size: int, year_from: int | None = None,
    ) -> list[tuple[int, str]]:
        """Liest Dokumente ohne Embedding (id, text)."""

    @abstractmethod
    async def store_embeddings(
        self, source: str, embeddings: list[tuple[int, list[float]]],
    ) -> int:
        """Schreibt Embeddings in die DB. Gibt Anzahl geschriebener Rows zurueck."""

    @abstractmethod
    async def count_status(self, source: str) -> tuple[int, int]:
        """Gibt (total, embedded) Counts zurueck."""


class ChunkingPort(ABC):
    """Abstraktes Interface fuer Text-Chunking."""

    @abstractmethod
    def chunk_text(self, text: str) -> list[str]:
        """Zerlegt Text in Chunks. Leerer Text -> leere Liste."""


class ChunkRepositoryPort(ABC):
    """Abstraktes Interface fuer Chunk-Persistenz."""

    @abstractmethod
    async def fetch_unchunked_docs(
        self, source: str, batch_size: int, year_from: int | None = None,
    ) -> list[tuple[str, str]]:
        """Liest Dokumente ohne Chunks (source_id, text). Gibt Tupel zurueck."""

    @abstractmethod
    async def store_chunks_with_embeddings(
        self, source: str, records: list[tuple[str, int, str, list[float]]],
    ) -> int:
        """Speichert (source_id, chunk_index, chunk_text, embedding). Gibt Anzahl zurueck."""

    @abstractmethod
    async def count_chunk_status(self, source: str) -> tuple[int, int]:
        """Gibt (total_docs_with_text, docs_already_chunked) Counts zurueck."""
