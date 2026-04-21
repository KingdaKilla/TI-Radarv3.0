"""Remote Embedding-Provider via TEI (Text Embeddings Inference) auf dediziertem GPU-Pod."""
from __future__ import annotations

import httpx
import structlog

from src.config import Settings
from src.domain.ports import EmbeddingProviderPort

logger = structlog.get_logger()


class RemoteEmbedder(EmbeddingProviderPort):
    """Embedding-Provider ueber TEI HTTP API auf dediziertem RunPod Pod.

    TEI API: POST /embed  {"inputs": [...]}  -> [[float, ...], ...]
    """

    def __init__(self, settings: Settings) -> None:
        self._tei_url = settings.tei_url.rstrip("/")
        self._sub_batch_size = settings.tei_batch_size
        self._timeout = settings.tei_timeout_s
        self._client = httpx.AsyncClient()
        logger.info(
            "remote_embedder_initialisiert",
            tei_url=self._tei_url,
            sub_batch_size=self._sub_batch_size,
            timeout_s=self._timeout,
        )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Erzeugt Embeddings ueber TEI API mit Sub-Batching."""
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self._sub_batch_size):
            sub_batch = texts[i : i + self._sub_batch_size]
            logger.debug(
                "tei_sub_batch",
                batch_nr=i // self._sub_batch_size + 1,
                size=len(sub_batch),
                total=len(texts),
            )

            try:
                response = await self._client.post(
                    f"{self._tei_url}/embed",
                    json={"inputs": sub_batch},
                    timeout=self._timeout,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(
                    f"TEI API Fehler: HTTP {exc.response.status_code} — {exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                raise RuntimeError(
                    f"TEI Verbindungsfehler: {exc}"
                ) from exc

            all_embeddings.extend(response.json())

        logger.info("remote_embeddings_erzeugt", count=len(all_embeddings))
        return all_embeddings

    async def close(self) -> None:
        """Schliesst den httpx-Client."""
        await self._client.aclose()
        logger.info("remote_embedder_geschlossen")
