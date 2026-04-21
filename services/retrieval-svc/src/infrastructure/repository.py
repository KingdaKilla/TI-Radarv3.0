"""VectorSearchRepository — v3.x-Hybrid-Dense-Suche mit Incremental-Embedding.

**v3.6.0 Backport-Variante (Incremental Pre-Computation / Variante B):**

v3.x hat die vector(384)-Embedding-Spalten direkt in den Quell-Tabellen
(nicht in `cross_schema.document_chunks` wie v4.x). Beim Start sind die
Spalten leer. Statt eines mehrtägigen Bulk-Embedding-Jobs füllen wir die
Embeddings bedarfsgetrieben:

1. **Candidate-Retrieval per tsvector:** Top-N relevante Rows via der
   existierenden `search_vector`-Spalten (schnell, nutzt bereits
   vorhandene FTS-Indizes).
2. **NULL-Check:** Welche Kandidaten haben noch kein Embedding?
3. **Incremental-Embedding:** Für fehlende Kandidaten holen wir den Text,
   rufen `embedding-svc` per gRPC auf und schreiben den Vektor in die
   zugehörige Spalte. Das UPDATE ist transaktional und idempotent.
4. **Re-Ranking per Vector-Distance:** Unter den nun vollständig
   embeddeten Kandidaten wird Top-K über `embedding <=> query` gerankt.

Vorteil: Kein Wartezustand nach Deploy — die Tool-Nutzung selbst
produziert die Embedding-Abdeckung. Häufig angefragte Technologien werden
zuerst embedded. Long-Tail bleibt langsam, ist aber bedarfsgetrieben.

Tables & Spalten:
    patent_schema.patents.title_embedding     (text = title)
    cordis_schema.projects.content_embedding  (text = title + " " + objective)
    research_schema.papers.abstract_embedding (text = title + " " + abstract)
"""
from __future__ import annotations

from typing import Any

import asyncpg
import structlog

from src.domain.ports import RetrievedDoc, VectorSearchPort

logger = structlog.get_logger(__name__)

# Candidate-Cap für tsvector-Vorfilter. Zu hoch = Embedding-Batch langsam,
# zu niedrig = Re-Ranking-Qualität leidet.
CANDIDATE_LIMIT = 100

# Maximale Anzahl Rows die pro Request on-the-fly embedded werden dürfen.
# Verhindert, dass ein einzelner Chat-Request alle Embeddings für eine
# frische Technologie blockierend generiert (3-8s extra statt 60s+).
INCREMENTAL_EMBED_LIMIT = 50

# Quellkonfiguration: SELECT-Template, Text-Zusammensetzung, UPDATE.
_SOURCE_CONFIG: dict[str, dict[str, str]] = {
    "patents": {
        "candidate_sql": """
            SELECT p.id, p.title, p.publication_year, p.country,
                   (p.title_embedding IS NULL) AS needs_embed,
                   p.title_embedding
            FROM patent_schema.patents p
            WHERE p.search_vector @@ plainto_tsquery('english', $1)
              AND p.title IS NOT NULL
            ORDER BY ts_rank_cd(p.search_vector, plainto_tsquery('english', $1)) DESC
            LIMIT $2
        """,
        "update_sql": (
            "UPDATE patent_schema.patents "
            "SET title_embedding = $1::vector WHERE id = $2"
        ),
        "rank_sql": """
            SELECT p.id::text AS source_id,
                   p.title,
                   COALESCE(p.title, '') AS text_snippet,
                   1 - (p.title_embedding <=> $1::vector) AS similarity,
                   p.publication_year::text AS year,
                   COALESCE(p.country, '') AS country
            FROM patent_schema.patents p
            WHERE p.id = ANY($2::bigint[])
              AND p.title_embedding IS NOT NULL
            ORDER BY p.title_embedding <=> $1::vector
            LIMIT $3
        """,
    },
    "projects": {
        "candidate_sql": """
            SELECT p.id, p.title, p.objective, p.start_date,
                   (p.content_embedding IS NULL) AS needs_embed,
                   p.content_embedding
            FROM cordis_schema.projects p
            WHERE p.search_vector @@ plainto_tsquery('english', $1)
              AND (p.title IS NOT NULL OR p.objective IS NOT NULL)
            ORDER BY ts_rank_cd(p.search_vector, plainto_tsquery('english', $1)) DESC
            LIMIT $2
        """,
        "update_sql": (
            "UPDATE cordis_schema.projects "
            "SET content_embedding = $1::vector WHERE id = $2"
        ),
        "rank_sql": """
            SELECT p.id::text AS source_id,
                   p.title,
                   COALESCE(p.objective, p.title, '') AS text_snippet,
                   1 - (p.content_embedding <=> $1::vector) AS similarity,
                   EXTRACT(YEAR FROM p.start_date)::text AS year,
                   '' AS country
            FROM cordis_schema.projects p
            WHERE p.id = ANY($2::bigint[])
              AND p.content_embedding IS NOT NULL
            ORDER BY p.content_embedding <=> $1::vector
            LIMIT $3
        """,
    },
    "papers": {
        "candidate_sql": """
            SELECT p.id, p.title, p.abstract, p.year,
                   (p.abstract_embedding IS NULL) AS needs_embed,
                   p.abstract_embedding
            FROM research_schema.papers p
            WHERE p.search_vector @@ plainto_tsquery('english', $1)
              AND (p.title IS NOT NULL OR p.abstract IS NOT NULL)
            ORDER BY ts_rank_cd(p.search_vector, plainto_tsquery('english', $1)) DESC
            LIMIT $2
        """,
        "update_sql": (
            "UPDATE research_schema.papers "
            "SET abstract_embedding = $1::vector WHERE id = $2"
        ),
        "rank_sql": """
            SELECT p.id::text AS source_id,
                   p.title,
                   COALESCE(p.abstract, p.title, '') AS text_snippet,
                   1 - (p.abstract_embedding <=> $1::vector) AS similarity,
                   p.year::text AS year,
                   '' AS country
            FROM research_schema.papers p
            WHERE p.id = ANY($2::bigint[])
              AND p.abstract_embedding IS NOT NULL
            ORDER BY p.abstract_embedding <=> $1::vector
            LIMIT $3
        """,
    },
}

_SOURCE_SINGULAR: dict[str, str] = {
    "patents": "patent",
    "projects": "project",
    "papers": "paper",
}


def _compose_text(row: asyncpg.Record, source: str) -> str:
    """Baut den Text der embedded werden soll, analog zum Schema."""
    if source == "patents":
        return str(row["title"] or "")[:8000]
    if source == "projects":
        parts = [str(row[c]) for c in ("title", "objective") if row[c]]
        return " ".join(parts)[:8000]
    if source == "papers":
        parts = [str(row[c]) for c in ("title", "abstract") if row[c]]
        return " ".join(parts)[:8000]
    return ""


def _vec_to_pg(vec: list[float]) -> str:
    """pgvector erwartet '[x,y,z,...]' als Text-Cast."""
    return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"


class VectorSearchRepository(VectorSearchPort):
    """Async PostgreSQL-Zugriff für v3.x Hybrid-Dense-Suche mit
    Incremental-Embedding (Bug v3.6.0/Ξ-5-6-7).
    """

    def __init__(self, pool: asyncpg.Pool, embedder: "IncrementalEmbedder | None" = None) -> None:
        self._pool = pool
        self._embedder = embedder

    async def search(
        self,
        query_vector: list[float],
        technology: str,
        sources: list[str],
        top_k: int,
        threshold: float,
    ) -> list[RetrievedDoc]:
        """Führt Hybrid-Dense-Search durch.

        Args:
            query_vector: Embedding-Vektor der Suchanfrage (bereits berechnet
                vom use_case via embedding-svc).
            technology: Technologie-Suchbegriff für den tsvector-Candidate-Filter.
            sources: Liste der zu durchsuchenden Quellen (`patents`, `projects`, `papers`).
            top_k: Maximale Anzahl Ergebnisse pro Quelle.
            threshold: Minimale Cosine-Similarity im Endergebnis.

        Returns:
            Liste von RetrievedDoc-Instanzen (Top-K pro Quelle, ranked nach Cosine).
        """
        results: list[RetrievedDoc] = []

        for source in sources:
            cfg = _SOURCE_CONFIG.get(source)
            if cfg is None:
                logger.warning("unbekannte_quelle_uebersprungen", source=source)
                continue

            # --- 1. Candidate-Retrieval per tsvector (schnell, nutzt FTS-Index) ---
            async with self._pool.acquire() as conn:
                candidates: list[asyncpg.Record] = await conn.fetch(
                    cfg["candidate_sql"], technology, CANDIDATE_LIMIT,
                )

            if not candidates:
                logger.debug("keine_kandidaten", source=source, technology=technology)
                continue

            # --- 2. Fehlende Embeddings on-the-fly generieren ---
            missing_rows = [r for r in candidates if r["needs_embed"]][:INCREMENTAL_EMBED_LIMIT]
            if missing_rows and self._embedder is not None:
                texts = [_compose_text(r, source) for r in missing_rows]
                texts_nonempty = [t for t in texts if t]
                if texts_nonempty:
                    logger.info(
                        "incremental_embedding_start",
                        source=source,
                        count=len(texts_nonempty),
                        technology=technology,
                    )
                    try:
                        vectors = await self._embedder.embed_batch(texts)
                    except Exception as exc:
                        logger.warning(
                            "incremental_embedding_fehler",
                            source=source,
                            error=str(exc),
                        )
                        vectors = []
                    if vectors and len(vectors) == len(missing_rows):
                        async with self._pool.acquire() as conn:
                            async with conn.transaction():
                                for row, vec in zip(missing_rows, vectors, strict=False):
                                    if not vec:
                                        continue
                                    await conn.execute(
                                        cfg["update_sql"], _vec_to_pg(vec), row["id"],
                                    )
                        logger.info(
                            "incremental_embedding_persistiert",
                            source=source,
                            count=len(vectors),
                        )

            # --- 3. Re-Ranking per Vector-Distance (nur nicht-NULL Rows) ---
            candidate_ids = [r["id"] for r in candidates]
            async with self._pool.acquire() as conn:
                ranked: list[asyncpg.Record] = await conn.fetch(
                    cfg["rank_sql"], _vec_to_pg(query_vector), candidate_ids, top_k,
                )

            source_singular = _SOURCE_SINGULAR.get(source, source)
            for row in ranked:
                similarity = float(row["similarity"])
                if similarity < threshold:
                    continue
                metadata: dict[str, str] = {}
                if row["year"]:
                    metadata["year"] = str(row["year"])
                if row["country"]:
                    metadata["country"] = str(row["country"])
                results.append(
                    RetrievedDoc(
                        source=source_singular,
                        source_id=str(row["source_id"]),
                        title=row["title"] or "",
                        text_snippet=(row["text_snippet"] or "")[:500],
                        similarity_score=similarity,
                        metadata=metadata,
                    )
                )

        return results


class IncrementalEmbedder:
    """Dünner Wrapper um einen Embedder-Port mit `embed_batch(texts)`-Methode.

    In v3.6.0 nutzen wir den lokalen QueryEmbedder des retrieval-svc direkt
    (das SentenceTransformer-Modell ist bereits im RAM). Alternativ kann
    ein gRPC-Stub zum embedding-svc übergeben werden — dessen Port muss
    dieselbe `async embed_batch(texts) -> list[list[float]]`-Signatur haben.
    """

    def __init__(self, port: Any) -> None:
        self._port = port

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await self._port.embed_batch(texts)
