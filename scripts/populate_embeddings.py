#!/usr/bin/env python3
"""populate_embeddings.py — v3.6.0 OPTIONALER Bulk-Embedding-Job.

**Standard-Ansatz ist jetzt Incremental Pre-Computation** (Variante B):
Der `retrieval-svc` embedded fehlende Kandidaten pro Chat-Query on-the-fly
und schreibt sie zurück. Häufig angefragte Tech-Bereiche werden dadurch
automatisch priorisiert. Siehe `services/retrieval-svc/src/infrastructure/repository.py`.

Dieser Bulk-Job ist nur noch für Sonderfälle gedacht:
  - Offline-Vorbefüllung vor einer Demo (damit die erste Chat-Query nicht
    3-8 s extra kostet)
  - Nachträgliche Vollabdeckung, nachdem die "heißen" Bereiche durch
    Incremental bereits gecovered sind
  - Re-Embedding nach Modell-Wechsel

Für den regulären Betrieb NICHT ausführen — Incremental reicht.

Füllt die vector(384)-Spalten der v3.x-Tabellen einmalig über einen
Batch-Job. Nutzt `sentence-transformers/multilingual-e5-small` direkt
(passt zur DB-Dimension 384).

Tables & Spalten:
    patent_schema.patents.title_embedding     ← title
    cordis_schema.projects.content_embedding  ← title + " " + objective
    research_schema.papers.abstract_embedding ← title + " " + abstract

Aufruf im embedding-svc-Container (nach `docker compose up -d`):

    docker compose exec -T embedding-svc python /app/scripts/populate_embeddings.py \
        --source patents --batch-size 256

Optionen:
    --source {patents,projects,papers,all}
    --batch-size N        (default 256; CPU: 100-500 sinnvoll, GPU: 1000+)
    --limit N             (default 0 = unbegrenzt; für Tests)

Dauer-Schätzung:
    150M Patents × CPU i5 4-core (~200 Embeddings/s): ~9 Tage
    150M Patents × GPU A100 (~5000 Embeddings/s): ~8 Stunden
    1.7M EU-Patents (european_only) × CPU: ~2.5 Stunden

Idempotent: Läuft nur gegen Rows mit NULL-Embedding. Re-Run überspringt
bereits befüllte Rows. Progress wird per logger.info alle batch_size
Rows ausgegeben.
"""
from __future__ import annotations

import argparse
import asyncio
import time

import asyncpg
import structlog

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except ImportError as exc:
    raise SystemExit(
        "sentence-transformers nicht installiert. Im embedding-svc-Container "
        "verfügbar. Aufruf: docker compose exec embedding-svc python ..."
    ) from exc

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
logger = structlog.get_logger()

MODEL_NAME = "intfloat/multilingual-e5-small"

# Quelle → (SELECT-Query, UPDATE-Query, Text-Spalten)
SOURCES: dict[str, dict[str, str]] = {
    "patents": {
        "select": (
            "SELECT id, title FROM patent_schema.patents "
            "WHERE title_embedding IS NULL AND title IS NOT NULL "
            "ORDER BY id LIMIT $1"
        ),
        "update": (
            "UPDATE patent_schema.patents SET title_embedding = $1::vector WHERE id = $2"
        ),
        "text_cols": ("title",),
    },
    "projects": {
        "select": (
            "SELECT id, title, objective FROM cordis_schema.projects "
            "WHERE content_embedding IS NULL AND (title IS NOT NULL OR objective IS NOT NULL) "
            "ORDER BY id LIMIT $1"
        ),
        "update": (
            "UPDATE cordis_schema.projects SET content_embedding = $1::vector WHERE id = $2"
        ),
        "text_cols": ("title", "objective"),
    },
    "papers": {
        "select": (
            "SELECT id, title, abstract FROM research_schema.papers "
            "WHERE abstract_embedding IS NULL AND (title IS NOT NULL OR abstract IS NOT NULL) "
            "ORDER BY id LIMIT $1"
        ),
        "update": (
            "UPDATE research_schema.papers SET abstract_embedding = $1::vector WHERE id = $2"
        ),
        "text_cols": ("title", "abstract"),
    },
}


def _concat_text(row: asyncpg.Record, text_cols: tuple[str, ...]) -> str:
    parts = [str(row[c]) for c in text_cols if row[c]]
    return " ".join(parts).strip()


async def process_source(
    pool: asyncpg.Pool,
    model: "SentenceTransformer",
    source: str,
    batch_size: int,
    limit: int,
) -> None:
    cfg = SOURCES[source]
    total = 0
    t0 = time.monotonic()
    while True:
        async with pool.acquire() as conn:
            rows = await conn.fetch(cfg["select"], batch_size)
        if not rows:
            logger.info("source_fertig", source=source, total=total)
            break
        texts = [_concat_text(r, cfg["text_cols"]) for r in rows]
        # e5-Modelle verlangen "passage: "-Präfix für Doc-Embeddings
        passages = [f"passage: {t[:8000]}" for t in texts]
        vectors = model.encode(
            passages,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        async with pool.acquire() as conn:
            async with conn.transaction():
                for row, vec in zip(rows, vectors, strict=False):
                    # pgvector erwartet '[x,y,z,...]' als Text-Cast
                    vec_str = "[" + ",".join(f"{v:.6f}" for v in vec.tolist()) + "]"
                    await conn.execute(cfg["update"], vec_str, row["id"])
        total += len(rows)
        elapsed = time.monotonic() - t0
        rate = total / elapsed if elapsed > 0 else 0.0
        logger.info(
            "batch_fertig",
            source=source,
            batch=len(rows),
            total=total,
            rate_per_s=round(rate, 1),
        )
        if limit and total >= limit:
            logger.info("limit_erreicht", source=source, total=total, limit=limit)
            break


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=[*SOURCES.keys(), "all"], default="all")
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument(
        "--dsn",
        default=None,
        help="DB-DSN; default aus EMBEDDING_DATABASE_URL Environment",
    )
    args = ap.parse_args()

    import os

    dsn = args.dsn or os.environ.get("EMBEDDING_DATABASE_URL")
    if not dsn:
        raise SystemExit(
            "Keine DB-DSN. Setze EMBEDDING_DATABASE_URL oder --dsn."
        )

    logger.info("modell_laden", model=MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)

    pool = await asyncpg.create_pool(
        dsn=dsn, min_size=2, max_size=5, command_timeout=600
    )

    sources = list(SOURCES.keys()) if args.source == "all" else [args.source]
    for src in sources:
        logger.info("starte_source", source=src, batch_size=args.batch_size, limit=args.limit)
        await process_source(pool, model, src, args.batch_size, args.limit)

    await pool.close()
    logger.info("alle_sources_fertig")


if __name__ == "__main__":
    asyncio.run(main())
