"""Infrastructure-Adapter fuer Embedding-Service."""

from src.infrastructure.chunker import RecursiveChunker
from src.infrastructure.repository import ChunkRepository, EmbeddingRepository

__all__ = ["ChunkRepository", "EmbeddingRepository", "RecursiveChunker"]

# Optional Adapter (benoetigen externe Abhaengigkeiten)
try:
    from src.infrastructure.local_embedder import LocalEmbedder
    __all__.append("LocalEmbedder")
except ImportError:
    pass

try:
    from src.infrastructure.remote_embedder import RemoteEmbedder
    __all__.append("RemoteEmbedder")
except ImportError:
    pass
