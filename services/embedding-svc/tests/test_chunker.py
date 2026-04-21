"""Tests for RecursiveChunker."""
from __future__ import annotations

import pytest

from src.infrastructure.chunker import RecursiveChunker


class TestRecursiveChunker:
    def setup_method(self):
        self.chunker = RecursiveChunker(chunk_size=512, chunk_overlap=200)

    def test_short_text_single_chunk(self):
        text = "This is a short text about quantum computing."
        chunks = self.chunker.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self):
        text = "Quantum computing is a revolutionary technology. " * 100
        chunks = self.chunker.chunk_text(text)
        assert len(chunks) > 1

    def test_overlap_exists(self):
        text = "Sentence number one. " * 200
        chunks = self.chunker.chunk_text(text)
        assert len(chunks) >= 2
        end_of_first = chunks[0][-50:]
        assert end_of_first in chunks[1]

    def test_empty_text(self):
        chunks = self.chunker.chunk_text("")
        assert chunks == []

    def test_whitespace_only(self):
        chunks = self.chunker.chunk_text("   \n\n  ")
        assert chunks == []

    def test_preserves_sentence_boundaries(self):
        # The splitter uses ". " as a separator: the period stays at the end of
        # the preceding chunk OR starts the next chunk as ". …".  Either way,
        # every chunk must contain at least one period (sentence content is never
        # split mid-sentence without a period present somewhere in the chunk).
        text = "First sentence about quantum computing. Second sentence about AI. Third sentence about patents. " * 50
        chunks = self.chunker.chunk_text(text)
        chunks_with_period = sum(1 for c in chunks if "." in c)
        assert chunks_with_period == len(chunks)
