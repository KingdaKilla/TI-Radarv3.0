#!/usr/bin/env python3
"""Trigger-Skript: Chunking + Embedding Pipeline in Schleife ausfuehren.

Wird per docker exec im embedding-svc Container ausgefuehrt:
    docker exec -it ti-radar-embedding python3 trigger_chunk_embed.py --source patents --batch-size 100

Fuehrt ChunkAndEmbed.execute() in Schleife aus, bis alle Dokumente verarbeitet sind.
"""
from __future__ import annotations

import argparse
import asyncio
import time

import asyncpg
import structlog

from src.config import Settings
from src.domain.ports import EmbeddingProviderPort
from src.infrastructure.chunker import RecursiveChunker
from src.infrastructure.remote_embedder import RemoteEmbedder
from src.infrastructure.local_embedder import LocalEmbedder
from src.infrastructure.repository import ChunkRepository
from src.use_case import ChunkAndEmbed

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


async def run_pipeline(
    source: str,
    batch_size: int,
    year_from: int | None,
    max_batches: int | None,
) -> None:
    settings = Settings()

    pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=2,
        max_size=5,
        command_timeout=300,
    )

    # Provider auswahl
    embedder: EmbeddingProviderPort
    if settings.embedding_provider == "remote":
        embedder = RemoteEmbedder(settings)
        logger.info("provider_remote", tei_url=settings.tei_url)
    else:
        embedder = LocalEmbedder(settings)
        logger.info("provider_lokal")

    chunk_repo = ChunkRepository(pool)
    chunker = RecursiveChunker()
    use_case = ChunkAndEmbed(
        chunk_repo=chunk_repo,
        chunker=chunker,
        embedder=embedder,
    )

    t_global = time.monotonic()
    total_chunks = 0
    total_docs = 0
    batch_nr = 0

    while True:
        batch_nr += 1
        if max_batches and batch_nr > max_batches:
            logger.info("max_batches_erreicht", max_batches=max_batches)
            break

        result = await use_case.execute(
            source=source,
            batch_size=batch_size,
            year_from=year_from,
        )

        total_chunks += result.chunks_created
        total_docs += result.docs_processed

        logger.info(
            "batch_ergebnis",
            batch_nr=batch_nr,
            docs=result.docs_processed,
            chunks=result.chunks_created,
            remaining=result.remaining_docs,
            total=result.total_docs,
            batch_s=round(result.elapsed_seconds, 2),
        )

        if result.status == "completed":
            logger.info("pipeline_abgeschlossen")
            break

    elapsed = time.monotonic() - t_global
    logger.info(
        "pipeline_gesamt",
        total_docs=total_docs,
        total_chunks=total_chunks,
        elapsed_s=round(elapsed, 2),
        elapsed_min=round(elapsed / 60, 1),
    )

    if hasattr(embedder, "close"):
        await embedder.close()
    await pool.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk + Embed Pipeline Trigger")
    parser.add_argument("--source", default="patents", help="patents|projects|papers")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--year-from", type=int, default=None)
    parser.add_argument("--max-batches", type=int, default=None, help="Stop nach N Batches (fuer Tests)")
    args = parser.parse_args()

    asyncio.run(run_pipeline(
        source=args.source,
        batch_size=args.batch_size,
        year_from=args.year_from,
        max_batches=args.max_batches,
    ))


if __name__ == "__main__":
    main()
