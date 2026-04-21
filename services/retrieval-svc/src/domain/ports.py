"""Port-Interfaces fuer Retrieval-Service (Hexagonal Architecture)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetrievedDoc:
    """Ein einzelnes Retrieval-Ergebnis."""

    source: str
    source_id: str
    title: str
    text_snippet: str
    similarity_score: float
    metadata: dict[str, str]


class VectorSearchPort(ABC):
    """Abstraktes Interface fuer Vektor-/Hybrid-Suche."""

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        technology: str,
        sources: list[str],
        top_k: int,
        threshold: float,
    ) -> list[RetrievedDoc]:
        """Fuehrt Hybrid-Search (Keyword + Vektor) durch."""


class SparseSearchPort(ABC):
    """Abstraktes Interface fuer Sparse/BM25-Suche."""

    @abstractmethod
    async def search(
        self,
        query: str,
        sources: list[str],
        top_k: int,
    ) -> list[RetrievedDoc]:
        """Fuehrt BM25/Full-Text-Suche durch.

        Gibt RetrievedDoc mit ts_rank als similarity_score zurueck.
        """


class QueryEmbeddingPort(ABC):
    """Abstraktes Interface fuer Query-Embedding."""

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Erzeugt Embedding fuer eine einzelne Query."""


class RerankingPort(ABC):
    """Abstraktes Interface fuer Reranking von Retrieval-Ergebnissen."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: list[RetrievedDoc],
        top_k: int,
    ) -> list[RetrievedDoc]:
        """Rerankt Dokumente nach Relevanz zur Query. Gibt top_k zurueck."""
