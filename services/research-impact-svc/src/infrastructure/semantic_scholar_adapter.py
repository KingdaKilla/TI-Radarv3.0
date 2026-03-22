"""Semantic Scholar Academic Graph API Adapter.

Migriert von v1.0 mit minimalen Aenderungen:
- Gleiche API-Endpunkte und Parameter
- x-api-key Header fuer authentifizierten Zugriff
- httpx.AsyncClient fuer async HTTP-Requests

Der Adapter sucht Paper via der Relevance-Search-API und
gibt strukturierte Ergebnisse mit Zitationen zurueck.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class SemanticScholarAdapter:
    """Async-Adapter fuer die Semantic Scholar Academic Graph API.

    Sucht Paper zu einem Technologie-Suchbegriff und gibt
    strukturierte Ergebnisse mit Zitationsdaten zurueck.
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
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._max_results = max_results

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
                except Exception as exc:
                    logger.warning(
                        "semantic_scholar_request_fehlgeschlagen",
                        offset=offset,
                        fehler=str(exc),
                    )
                    break

                papers = data.get("data", [])
                if not papers:
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

        return all_papers[:effective_limit]
