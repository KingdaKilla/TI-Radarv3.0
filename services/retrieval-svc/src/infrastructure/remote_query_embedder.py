"""Remote Query-Embedder via TEI (Text Embeddings Inference) auf dediziertem GPU-Pod."""
from __future__ import annotations

import httpx
import structlog

from src.config import Settings
from src.domain.ports import QueryEmbeddingPort

logger = structlog.get_logger()


class RemoteQueryEmbedder(QueryEmbeddingPort):
    """Query-Embedding ueber TEI HTTP API auf dediziertem RunPod Pod.

    TEI API: POST /embed  {"inputs": ["query"]}  -> [[float, ...]]
    """

    def __init__(self, settings: Settings) -> None:
        self._tei_url = settings.tei_url.rstrip("/")
        self._timeout = settings.tei_timeout_s
        self._client = httpx.AsyncClient()

    async def embed_query(self, text: str) -> list[float]:
        resp = await self._client.post(
            f"{self._tei_url}/embed",
            json={"inputs": [text]},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()[0]

    async def close(self) -> None:
        await self._client.aclose()
