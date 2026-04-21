"""Unit-Tests fuer EmbedDocuments und ChunkAndEmbed Use Cases.

Alle externen Abhaengigkeiten (Repository, Embedder, Chunker) werden durch
AsyncMock/MagicMock-Objekte ersetzt. Kein IO, kein gRPC, kein Protobuf.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.use_case import ChunkAndEmbed, ChunkEmbedResult, EmbedDocuments, EmbedResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_mocks(
    *,
    docs: list[tuple[int, str]] | None = None,
    vectors: list[list[float]] | None = None,
    stored: int = 0,
    total: int = 100,
    embedded: int = 50,
) -> tuple[AsyncMock, AsyncMock]:
    """Erstellt Mock-Repository und Mock-Embedder mit sinnvollen Defaults."""
    repo = AsyncMock()
    repo.fetch_unembedded.return_value = docs if docs is not None else []
    repo.store_embeddings.return_value = stored
    repo.count_status.return_value = (total, embedded)

    embedder = AsyncMock()
    embedder.embed_batch.return_value = vectors if vectors is not None else []

    return repo, embedder


# ---------------------------------------------------------------------------
# Tests: Kein unembedded Dokument
# ---------------------------------------------------------------------------

class TestNoUnembedded:
    """Testet Verhalten wenn keine unembedded Dokumente vorhanden sind."""

    async def test_no_unembedded_returns_zero(self):
        repo, embedder = _make_mocks(docs=[], total=100, embedded=100)
        uc = EmbedDocuments(repo=repo, embedder=embedder)

        result = await uc.execute("patents", batch_size=100)

        assert isinstance(result, EmbedResult)
        assert result.embedded_count == 0
        assert result.status == "completed"

    async def test_no_unembedded_does_not_call_embedder(self):
        repo, embedder = _make_mocks(docs=[], total=100, embedded=100)
        uc = EmbedDocuments(repo=repo, embedder=embedder)

        await uc.execute("patents", batch_size=100)

        embedder.embed_batch.assert_not_called()

    async def test_no_unembedded_reports_total_count(self):
        repo, embedder = _make_mocks(docs=[], total=500, embedded=500)
        uc = EmbedDocuments(repo=repo, embedder=embedder)

        result = await uc.execute("projects")

        assert result.total_count == 500
        assert result.remaining_count == 0


# ---------------------------------------------------------------------------
# Tests: Batch Embedding
# ---------------------------------------------------------------------------

class TestBatchEmbedding:
    """Testet den normalen Batch-Embedding-Ablauf."""

    async def test_embeds_and_stores_batch(self):
        docs = [(1, "Text A"), (2, "Text B"), (3, "Text C")]
        vectors = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        repo, embedder = _make_mocks(
            docs=docs, vectors=vectors, stored=3, total=100, embedded=53,
        )
        uc = EmbedDocuments(repo=repo, embedder=embedder)

        result = await uc.execute("patents", batch_size=100)

        assert result.embedded_count == 3
        assert result.remaining_count == 47  # 100 - 53
        assert result.total_count == 100

    async def test_calls_embedder_with_texts(self):
        docs = [(10, "Hello"), (20, "World")]
        vectors = [[1.0], [2.0]]
        repo, embedder = _make_mocks(docs=docs, vectors=vectors, stored=2)
        uc = EmbedDocuments(repo=repo, embedder=embedder)

        await uc.execute("papers", batch_size=50)

        embedder.embed_batch.assert_called_once_with(["Hello", "World"])

    async def test_stores_id_vector_pairs(self):
        docs = [(1, "A"), (2, "B")]
        vectors = [[0.1], [0.2]]
        repo, embedder = _make_mocks(docs=docs, vectors=vectors, stored=2)
        uc = EmbedDocuments(repo=repo, embedder=embedder)

        await uc.execute("projects", batch_size=10)

        repo.store_embeddings.assert_called_once_with(
            "projects", [(1, [0.1]), (2, [0.2])],
        )

    async def test_status_running_when_remaining(self):
        docs = [(1, "A")]
        vectors = [[0.1]]
        repo, embedder = _make_mocks(
            docs=docs, vectors=vectors, stored=1, total=100, embedded=51,
        )
        uc = EmbedDocuments(repo=repo, embedder=embedder)

        result = await uc.execute("patents")

        assert result.status == "running"

    async def test_status_completed_when_all_done(self):
        docs = [(1, "A")]
        vectors = [[0.1]]
        repo, embedder = _make_mocks(
            docs=docs, vectors=vectors, stored=1, total=100, embedded=100,
        )
        uc = EmbedDocuments(repo=repo, embedder=embedder)

        result = await uc.execute("patents")

        assert result.status == "completed"

    async def test_elapsed_seconds_positive(self):
        docs = [(1, "A")]
        vectors = [[0.1]]
        repo, embedder = _make_mocks(
            docs=docs, vectors=vectors, stored=1, total=10, embedded=10,
        )
        uc = EmbedDocuments(repo=repo, embedder=embedder)

        result = await uc.execute("patents")

        assert result.elapsed_seconds >= 0.0


# ---------------------------------------------------------------------------
# Tests: get_status
# ---------------------------------------------------------------------------

class TestGetStatus:
    """Testet die Status-Abfrage."""

    async def test_get_status_returns_tuple(self):
        repo, embedder = _make_mocks(total=1000, embedded=750)
        uc = EmbedDocuments(repo=repo, embedder=embedder)

        total, embedded = await uc.get_status("patents")

        assert total == 1000
        assert embedded == 750

    async def test_get_status_delegates_to_repo(self):
        repo, embedder = _make_mocks()
        uc = EmbedDocuments(repo=repo, embedder=embedder)

        await uc.get_status("projects")

        repo.count_status.assert_called_with("projects")


# ---------------------------------------------------------------------------
# Tests: EmbedResult Dataclass
# ---------------------------------------------------------------------------

class TestEmbedResult:
    """Testet EmbedResult Dataclass."""

    def test_frozen(self):
        result = EmbedResult(
            embedded_count=10,
            remaining_count=90,
            total_count=100,
            elapsed_seconds=1.5,
            status="completed",
        )
        with pytest.raises(AttributeError):
            result.embedded_count = 99  # type: ignore[misc]

    def test_slots(self):
        result = EmbedResult(
            embedded_count=0,
            remaining_count=0,
            total_count=0,
            elapsed_seconds=0.0,
            status="completed",
        )
        assert not hasattr(result, "__dict__")


# ===========================================================================
# ChunkAndEmbed Use Case
# ===========================================================================

# ---------------------------------------------------------------------------
# Fixtures fuer ChunkAndEmbed
# ---------------------------------------------------------------------------

def _make_chunk_mocks(
    *,
    docs: list[tuple[str, str]] | None = None,
    chunks_per_doc: list[list[str]] | None = None,
    vectors: list[list[float]] | None = None,
    stored: int = 0,
    total: int = 100,
    chunked: int = 50,
) -> tuple[AsyncMock, MagicMock, AsyncMock]:
    """Erstellt Mock-ChunkRepo, Mock-Chunker und Mock-Embedder fuer ChunkAndEmbed."""
    chunk_repo = AsyncMock()
    chunk_repo.fetch_unchunked_docs.return_value = docs if docs is not None else []
    chunk_repo.store_chunks_with_embeddings.return_value = stored
    chunk_repo.count_chunk_status.return_value = (total, chunked)

    chunker = MagicMock()
    if chunks_per_doc is not None:
        chunker.chunk_text.side_effect = chunks_per_doc
    else:
        chunker.chunk_text.return_value = []

    embedder = AsyncMock()
    embedder.embed_batch.return_value = vectors if vectors is not None else []

    return chunk_repo, chunker, embedder


# ---------------------------------------------------------------------------
# Tests: ChunkAndEmbed — Normaler Ablauf
# ---------------------------------------------------------------------------

class TestChunkAndEmbedProcessesDocs:
    """Testet den normalen Chunk-und-Embed-Ablauf mit Dokumenten."""

    async def test_chunk_and_embed_processes_docs(self):
        """Verifiziert dass Dokumente gechunked, embedded und gespeichert werden."""
        docs = [("DOC-1", "Text about quantum computing"), ("DOC-2", "Text about AI")]
        chunks_per_doc = [["chunk1a", "chunk1b"], ["chunk2a"]]
        vectors = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]  # 3 chunks = 3 vectors

        chunk_repo, chunker, embedder = _make_chunk_mocks(
            docs=docs,
            chunks_per_doc=chunks_per_doc,
            vectors=vectors,
            stored=3,
            total=100,
            chunked=52,
        )
        uc = ChunkAndEmbed(chunk_repo=chunk_repo, chunker=chunker, embedder=embedder)

        result = await uc.execute("patents", batch_size=50)

        assert isinstance(result, ChunkEmbedResult)
        assert result.chunks_created == 3
        assert result.docs_processed == 2
        assert result.remaining_docs == 48  # 100 - 52
        assert result.total_docs == 100
        assert result.status == "running"

        # Embedder wird mit allen Chunk-Texten aufgerufen
        embedder.embed_batch.assert_called_once_with(["chunk1a", "chunk1b", "chunk2a"])

        # Store erhaelt source_id, chunk_index, chunk_text, vector
        expected_records = [
            ("DOC-1", 0, "chunk1a", [0.1, 0.2]),
            ("DOC-1", 1, "chunk1b", [0.3, 0.4]),
            ("DOC-2", 0, "chunk2a", [0.5, 0.6]),
        ]
        chunk_repo.store_chunks_with_embeddings.assert_called_once_with("patents", expected_records)

    async def test_elapsed_seconds_positive(self):
        docs = [("DOC-1", "Text")]
        chunks_per_doc = [["chunk"]]
        vectors = [[0.1]]
        chunk_repo, chunker, embedder = _make_chunk_mocks(
            docs=docs, chunks_per_doc=chunks_per_doc, vectors=vectors, stored=1,
        )
        uc = ChunkAndEmbed(chunk_repo=chunk_repo, chunker=chunker, embedder=embedder)

        result = await uc.execute("patents")

        assert result.elapsed_seconds >= 0.0


# ---------------------------------------------------------------------------
# Tests: ChunkAndEmbed — Keine Dokumente
# ---------------------------------------------------------------------------

class TestChunkAndEmbedNoDocs:
    """Testet Verhalten wenn keine unchunked Dokumente vorhanden sind."""

    async def test_chunk_and_embed_no_docs(self):
        """Leerer Fetch gibt completed-Ergebnis mit 0 Chunks zurueck."""
        chunk_repo, chunker, embedder = _make_chunk_mocks(
            docs=[], total=200, chunked=200,
        )
        uc = ChunkAndEmbed(chunk_repo=chunk_repo, chunker=chunker, embedder=embedder)

        result = await uc.execute("projects", batch_size=100)

        assert isinstance(result, ChunkEmbedResult)
        assert result.chunks_created == 0
        assert result.docs_processed == 0
        assert result.remaining_docs == 0  # 200 - 200
        assert result.total_docs == 200
        assert result.status == "completed"

    async def test_no_docs_does_not_call_chunker(self):
        chunk_repo, chunker, embedder = _make_chunk_mocks(docs=[])
        uc = ChunkAndEmbed(chunk_repo=chunk_repo, chunker=chunker, embedder=embedder)

        await uc.execute("patents")

        chunker.chunk_text.assert_not_called()

    async def test_no_docs_does_not_call_embedder(self):
        chunk_repo, chunker, embedder = _make_chunk_mocks(docs=[])
        uc = ChunkAndEmbed(chunk_repo=chunk_repo, chunker=chunker, embedder=embedder)

        await uc.execute("patents")

        embedder.embed_batch.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: ChunkAndEmbed — Mehrere Chunks pro Dokument
# ---------------------------------------------------------------------------

class TestChunkAndEmbedMultipleChunks:
    """Testet dass ein Dokument mit mehreren Chunks korrekt verarbeitet wird."""

    async def test_chunk_and_embed_multiple_chunks_per_doc(self):
        """Ein Dokument das in 3 Chunks zerlegt wird, erzeugt 3 Embeddings."""
        docs = [("LONG-DOC", "Very long text about many topics")]
        chunks_per_doc = [["Part 1 about quantum", "Part 2 about AI", "Part 3 about patents"]]
        vectors = [[0.1], [0.2], [0.3]]

        chunk_repo, chunker, embedder = _make_chunk_mocks(
            docs=docs,
            chunks_per_doc=chunks_per_doc,
            vectors=vectors,
            stored=3,
            total=50,
            chunked=50,
        )
        uc = ChunkAndEmbed(chunk_repo=chunk_repo, chunker=chunker, embedder=embedder)

        result = await uc.execute("papers", batch_size=10)

        assert result.chunks_created == 3
        assert result.docs_processed == 1
        assert result.status == "completed"

        # Alle 3 Chunks werden an den Embedder uebergeben
        embedder.embed_batch.assert_called_once_with([
            "Part 1 about quantum", "Part 2 about AI", "Part 3 about patents",
        ])

        # Store erhaelt korrekte Chunk-Indizes
        expected = [
            ("LONG-DOC", 0, "Part 1 about quantum", [0.1]),
            ("LONG-DOC", 1, "Part 2 about AI", [0.2]),
            ("LONG-DOC", 2, "Part 3 about patents", [0.3]),
        ]
        chunk_repo.store_chunks_with_embeddings.assert_called_once_with("papers", expected)


# ---------------------------------------------------------------------------
# Tests: ChunkAndEmbed — Leere Chunks werden uebersprungen
# ---------------------------------------------------------------------------

class TestChunkAndEmbedEmptyChunks:
    """Testet dass Dokumente die keine Chunks erzeugen, uebersprungen werden."""

    async def test_chunk_and_embed_empty_chunk_skipped(self):
        """Chunker gibt leere Liste fuer ein Dokument zurueck -> keine Embeddings."""
        docs = [("DOC-OK", "Good text"), ("DOC-EMPTY", "")]
        chunks_per_doc = [["chunk from good text"], []]  # zweites Dok erzeugt keine Chunks
        vectors = [[0.1, 0.2]]  # nur 1 Chunk -> 1 Vector

        chunk_repo, chunker, embedder = _make_chunk_mocks(
            docs=docs,
            chunks_per_doc=chunks_per_doc,
            vectors=vectors,
            stored=1,
            total=100,
            chunked=51,
        )
        uc = ChunkAndEmbed(chunk_repo=chunk_repo, chunker=chunker, embedder=embedder)

        result = await uc.execute("patents", batch_size=50)

        assert result.chunks_created == 1
        assert result.docs_processed == 2  # Beide Docs wurden verarbeitet

        # Embedder bekommt nur den einen nicht-leeren Chunk
        embedder.embed_batch.assert_called_once_with(["chunk from good text"])

        # Store bekommt nur den einen Record
        expected_records = [("DOC-OK", 0, "chunk from good text", [0.1, 0.2])]
        chunk_repo.store_chunks_with_embeddings.assert_called_once_with("patents", expected_records)

    async def test_all_docs_produce_empty_chunks(self):
        """Alle Dokumente erzeugen leere Chunks -> embed_batch wird nicht aufgerufen."""
        docs = [("DOC-A", ""), ("DOC-B", "  ")]
        chunks_per_doc = [[], []]
        chunk_repo, chunker, embedder = _make_chunk_mocks(
            docs=docs,
            chunks_per_doc=chunks_per_doc,
            stored=0,
            total=100,
            chunked=52,
        )
        uc = ChunkAndEmbed(chunk_repo=chunk_repo, chunker=chunker, embedder=embedder)

        result = await uc.execute("patents")

        assert result.chunks_created == 0
        assert result.docs_processed == 2
        embedder.embed_batch.assert_not_called()
        chunk_repo.store_chunks_with_embeddings.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: ChunkEmbedResult Dataclass
# ---------------------------------------------------------------------------

class TestChunkEmbedResult:
    """Testet ChunkEmbedResult Dataclass."""

    def test_frozen(self):
        result = ChunkEmbedResult(
            chunks_created=5,
            docs_processed=2,
            remaining_docs=10,
            total_docs=100,
            elapsed_seconds=1.5,
            status="completed",
        )
        with pytest.raises(AttributeError):
            result.chunks_created = 99  # type: ignore[misc]

    def test_slots(self):
        result = ChunkEmbedResult(
            chunks_created=0,
            docs_processed=0,
            remaining_docs=0,
            total_docs=0,
            elapsed_seconds=0.0,
            status="completed",
        )
        assert not hasattr(result, "__dict__")
