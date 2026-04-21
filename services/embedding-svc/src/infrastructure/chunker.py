"""RecursiveChunker — Adapter fuer langchain RecursiveCharacterTextSplitter.

Chunking-Strategie: 512 Token, 200 Overlap (Staebler et al. 2025).
"""
from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.domain.ports import ChunkingPort


class RecursiveChunker(ChunkingPort):
    """Chunking via RecursiveCharacterTextSplitter (Bose 2025, Kap. 5)."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 200) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " "],
            length_function=len,
        )

    def chunk_text(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        chunks = self._splitter.split_text(text)
        return [c for c in chunks if c.strip()]
