"""Semantic Scholar Academic Graph API Adapter.

Migriert von v1.0 mit minimalen Aenderungen:
- Gleiche API-Endpunkte und Parameter
- x-api-key Header fuer authentifizierten Zugriff
- httpx.AsyncClient fuer async HTTP-Requests

Der Adapter sucht Paper via der Relevance-Search-API und
gibt strukturierte Ergebnisse mit Zitationen zurueck.

Erweiterung: PostgreSQL-Cache via research_schema.papers / authors /
query_cache mit 30-Tage-TTL (ON CONFLICT DO UPDATE-Upsert).
"""

from __future__ import annotations

import time
from typing import Any

import asyncpg
import httpx
import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Cache-Konstanten
# ---------------------------------------------------------------------------
_CACHE_TTL_DAYS = 30


class SemanticScholarAdapter:
    """Async-Adapter fuer die Semantic Scholar Academic Graph API.

    Sucht Paper zu einem Technologie-Suchbegriff und gibt
    strukturierte Ergebnisse mit Zitationsdaten zurueck.

    Unterstuetzt optionales DB-Caching ueber ``research_schema``:
    1. Cache-Hit (frisch)  -> sofortige Rueckgabe aus DB
    2. Cache-Miss          -> API-Call, Ergebnis in DB speichern
    3. API-Fehler          -> veralteten Cache als Fallback nutzen
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    # Felder, die von der API zurueckgegeben werden sollen
    PAPER_FIELDS = (
        "title,venue,year,citationCount,influentialCitationCount,"
        "authors,externalIds,isOpenAccess,publicationTypes"
    )

    def __init__(
        self,
        api_key: str = "",
        timeout: float = 15.0,
        max_results: int = 200,
        pool: asyncpg.Pool | None = None,
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._max_results = max_results
        self._pool = pool

    # ------------------------------------------------------------------
    # Oeffentliche API
    # ------------------------------------------------------------------

    async def search_papers(
        self,
        query: str,
        *,
        year_start: int | None = None,
        year_end: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Paper-Suche ueber die Semantic Scholar Relevance Search API.

        Args:
            query: Suchbegriff (Technologie)
            year_start: Startjahr (optional)
            year_end: Endjahr (optional)
            limit: Max. Ergebnisse (Default: self._max_results)

        Returns:
            Liste von Paper-Dicts mit Zitations- und Metadaten
        """
        effective_limit = min(limit or self._max_results, self._max_results)
        cache_key = self._normalize_key(query)
        eff_year_start = year_start or 0
        eff_year_end = year_end or 9999

        # --- 1. Cache pruefen ---
        if self._pool is not None:
            try:
                cached = await self._load_from_cache(
                    cache_key, eff_year_start, eff_year_end, effective_limit,
                )
                if cached is not None:
                    return cached
            except Exception as exc:
                logger.warning(
                    "cache_lesen_fehlgeschlagen",
                    fehler=str(exc),
                    query=cache_key,
                )

        # --- 2. API-Call ---
        papers = await self._fetch_from_api(
            query,
            year_start=year_start,
            year_end=year_end,
            effective_limit=effective_limit,
        )

        if papers is not None:
            # API-Ergebnis im Cache speichern
            if self._pool is not None:
                try:
                    await self._store_in_cache(
                        papers, cache_key, eff_year_start, eff_year_end,
                    )
                except Exception as exc:
                    logger.warning(
                        "cache_schreiben_fehlgeschlagen",
                        fehler=str(exc),
                        query=cache_key,
                    )
            return papers

        # --- 3. API fehlgeschlagen -> veralteten Cache als Fallback ---
        if self._pool is not None:
            try:
                stale = await self._load_from_cache(
                    cache_key, eff_year_start, eff_year_end,
                    effective_limit, allow_stale=True,
                )
                if stale is not None:
                    logger.info(
                        "cache_stale_fallback",
                        query=cache_key,
                        anzahl=len(stale),
                    )
                    return stale
            except Exception as exc:
                logger.warning(
                    "cache_stale_lesen_fehlgeschlagen",
                    fehler=str(exc),
                    query=cache_key,
                )

        return []

    # ------------------------------------------------------------------
    # Interner API-Call (extrahiert aus dem alten search_papers)
    # ------------------------------------------------------------------

    async def _fetch_from_api(
        self,
        query: str,
        *,
        year_start: int | None,
        year_end: int | None,
        effective_limit: int,
    ) -> list[dict[str, Any]] | None:
        """Fuehrt den eigentlichen HTTP-Call gegen Semantic Scholar durch.

        Returns:
            Paper-Liste bei Erfolg, ``None`` bei komplettem Fehlschlag.
        """
        params: dict[str, str | int] = {
            "query": query,
            "limit": min(effective_limit, 100),  # API-Max pro Request = 100
            "fields": self.PAPER_FIELDS,
        }

        if year_start and year_end:
            params["year"] = f"{year_start}-{year_end}"
        elif year_start:
            params["year"] = f"{year_start}-"
        elif year_end:
            params["year"] = f"-{year_end}"

        headers: dict[str, str] = {}
        if self._api_key:
            headers["x-api-key"] = self._api_key

        all_papers: list[dict[str, Any]] = []
        offset = 0
        had_any_success = False

        t0 = time.monotonic()

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            while len(all_papers) < effective_limit:
                params["offset"] = offset

                try:
                    resp = await client.get(
                        self.BASE_URL, params=params, headers=headers,
                    )

                    if resp.status_code == 429:
                        logger.warning(
                            "semantic_scholar_rate_limit",
                            hinweis="Rate-Limit erreicht — Abbruch",
                        )
                        break

                    resp.raise_for_status()
                    data = resp.json()
                    had_any_success = True
                except Exception as exc:
                    logger.warning(
                        "semantic_scholar_request_fehlgeschlagen",
                        offset=offset,
                        fehler=str(exc),
                    )
                    break

                papers = data.get("data", [])
                if not papers:
                    had_any_success = True
                    break

                all_papers.extend(papers)
                offset += len(papers)

                # Weniger Ergebnisse als angefordert -> keine weiteren Seiten
                if len(papers) < int(params["limit"]):
                    break

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "semantic_scholar_suche",
            query=query,
            gefunden=len(all_papers),
            dauer_ms=elapsed_ms,
        )

        if not had_any_success and not all_papers:
            return None  # signalisiert kompletten Fehlschlag

        return all_papers[:effective_limit]

    # ------------------------------------------------------------------
    # Cache-Hilfsroutinen
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_key(query: str) -> str:
        """Suchbegriff normalisieren (lowercase, stripped)."""
        return query.strip().lower()

    async def _load_from_cache(
        self,
        technology: str,
        year_start: int,
        year_end: int,
        limit: int,
        *,
        allow_stale: bool = False,
    ) -> list[dict[str, Any]] | None:
        """Laedt gecachte Paper aus ``research_schema``.

        Returns:
            Paper-Liste wenn Cache-Treffer, sonst ``None``.
        """
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            # Pruefe ob die Abfrage gecacht ist
            if allow_stale:
                qc_sql = """
                    SELECT id, result_count
                    FROM research_schema.query_cache
                    WHERE technology = $1
                      AND year_start  = $2
                      AND year_end    = $3
                    ORDER BY fetched_at DESC
                    LIMIT 1
                """
            else:
                qc_sql = """
                    SELECT id, result_count
                    FROM research_schema.query_cache
                    WHERE technology = $1
                      AND year_start  = $2
                      AND year_end    = $3
                      AND stale_after > now()
                    ORDER BY fetched_at DESC
                    LIMIT 1
                """

            row = await conn.fetchrow(qc_sql, technology, year_start, year_end)
            if row is None:
                logger.debug(
                    "cache_miss",
                    technology=technology,
                    allow_stale=allow_stale,
                )
                return None

            # Paper laden
            papers_sql = """
                SELECT p.semantic_scholar_id,
                       p.title,
                       p.year,
                       p.venue,
                       p.citation_count,
                       p.influential_citation_count,
                       p.doi,
                       p.is_open_access,
                       p.publication_types
                FROM research_schema.papers p
                WHERE p.query_technology = $1
                ORDER BY p.citation_count DESC
                LIMIT $2
            """
            paper_rows = await conn.fetch(papers_sql, technology, limit)

            if not paper_rows:
                return None

            # Autoren pro Paper laden (Batch)
            paper_ids_sql = """
                SELECT p.id, p.semantic_scholar_id
                FROM research_schema.papers p
                WHERE p.query_technology = $1
                ORDER BY p.citation_count DESC
                LIMIT $2
            """
            id_rows = await conn.fetch(paper_ids_sql, technology, limit)
            paper_db_ids = [r["id"] for r in id_rows]

            authors_sql = """
                SELECT pa.paper_id,
                       a.semantic_scholar_id AS author_id,
                       a.name
                FROM research_schema.paper_authors pa
                JOIN research_schema.authors a ON a.id = pa.author_id
                WHERE pa.paper_id = ANY($1::bigint[])
                ORDER BY pa.paper_id, pa.author_position NULLS LAST
            """
            author_rows = await conn.fetch(authors_sql, paper_db_ids)

            # Autoren gruppiert nach paper_id
            authors_by_paper: dict[int, list[dict[str, Any]]] = {}
            for ar in author_rows:
                authors_by_paper.setdefault(ar["paper_id"], []).append({
                    "authorId": ar["author_id"],
                    "name": ar["name"],
                })

        # In das Format umwandeln, das die API liefert
        results: list[dict[str, Any]] = []
        for pr, idr in zip(paper_rows, id_rows):
            paper_dict: dict[str, Any] = {
                "paperId": pr["semantic_scholar_id"],
                "title": pr["title"],
                "year": pr["year"],
                "venue": pr["venue"] or "",
                "citationCount": pr["citation_count"],
                "influentialCitationCount": pr["influential_citation_count"],
                "isOpenAccess": pr["is_open_access"],
                "publicationTypes": list(pr["publication_types"]) if pr["publication_types"] else [],
                "authors": authors_by_paper.get(idr["id"], []),
                "externalIds": {"DOI": pr["doi"]} if pr["doi"] else {},
            }
            results.append(paper_dict)

        cache_type = "stale" if allow_stale else "frisch"
        logger.info(
            "cache_hit",
            technology=technology,
            anzahl=len(results),
            cache_typ=cache_type,
        )
        return results

    async def _store_in_cache(
        self,
        papers: list[dict[str, Any]],
        technology: str,
        year_start: int,
        year_end: int,
    ) -> None:
        """Speichert API-Ergebnisse in ``research_schema``."""
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # 1. query_cache upsert
                await conn.execute(
                    """
                    INSERT INTO research_schema.query_cache
                        (technology, year_start, year_end, result_count,
                         fetched_at, stale_after)
                    VALUES ($1, $2, $3, $4, now(),
                            now() + INTERVAL '30 days')
                    ON CONFLICT ON CONSTRAINT uq_query_cache
                    DO UPDATE SET
                        result_count = EXCLUDED.result_count,
                        fetched_at   = EXCLUDED.fetched_at,
                        stale_after  = EXCLUDED.stale_after
                    """,
                    technology, year_start, year_end, len(papers),
                )

                for paper in papers:
                    ss_paper_id = paper.get("paperId") or ""
                    if not ss_paper_id:
                        continue

                    # DOI extrahieren
                    ext_ids = paper.get("externalIds") or {}
                    doi = ext_ids.get("DOI")

                    pub_types = paper.get("publicationTypes") or []

                    # 2. Paper upsert
                    paper_db_id = await conn.fetchval(
                        """
                        INSERT INTO research_schema.papers
                            (semantic_scholar_id, title, year, venue,
                             citation_count, influential_citation_count,
                             doi, is_open_access, publication_types,
                             query_technology, fetched_at, stale_after)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::text[],
                                $10, now(), now() + INTERVAL '30 days')
                        ON CONFLICT (semantic_scholar_id)
                        DO UPDATE SET
                            title                       = EXCLUDED.title,
                            year                        = EXCLUDED.year,
                            venue                       = EXCLUDED.venue,
                            citation_count              = EXCLUDED.citation_count,
                            influential_citation_count  = EXCLUDED.influential_citation_count,
                            doi                         = EXCLUDED.doi,
                            is_open_access              = EXCLUDED.is_open_access,
                            publication_types           = EXCLUDED.publication_types,
                            query_technology            = EXCLUDED.query_technology,
                            fetched_at                  = EXCLUDED.fetched_at,
                            stale_after                 = EXCLUDED.stale_after
                        RETURNING id
                        """,
                        ss_paper_id,
                        paper.get("title") or "Untitled",
                        paper.get("year"),
                        paper.get("venue") or None,
                        paper.get("citationCount") or 0,
                        paper.get("influentialCitationCount") or 0,
                        doi,
                        paper.get("isOpenAccess"),
                        pub_types if pub_types else None,
                        technology,
                    )

                    # 3. Autoren upsert + Junction
                    authors = paper.get("authors") or []
                    for position, author in enumerate(authors, start=1):
                        author_ss_id = author.get("authorId") or ""
                        author_name = author.get("name") or "Unknown"
                        if not author_ss_id:
                            continue

                        author_db_id = await conn.fetchval(
                            """
                            INSERT INTO research_schema.authors
                                (semantic_scholar_id, name, fetched_at)
                            VALUES ($1, $2, now())
                            ON CONFLICT (semantic_scholar_id)
                            DO UPDATE SET
                                name       = EXCLUDED.name,
                                fetched_at = EXCLUDED.fetched_at
                            RETURNING id
                            """,
                            author_ss_id,
                            author_name,
                        )

                        # Junction
                        await conn.execute(
                            """
                            INSERT INTO research_schema.paper_authors
                                (paper_id, author_id, author_position)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (paper_id, author_id)
                            DO UPDATE SET author_position = EXCLUDED.author_position
                            """,
                            paper_db_id,
                            author_db_id,
                            position,
                        )

        logger.info(
            "cache_gespeichert",
            technology=technology,
            anzahl=len(papers),
        )
