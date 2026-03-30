"""GLEIF LEI Lookup Adapter — Organisationsnamen zu Legal Entity Identifiers aufloesen.

Nutzt die GLEIF Fuzzy-Completions API (kostenlos, kein API-Key):
    GET https://api.gleif.org/api/v1/fuzzy-completions?field=entity.legalName&q={name}

Caching in entity_schema.gleif_cache (90-Tage-TTL).
Negative Ergebnisse (kein LEI gefunden) werden ebenfalls gecacht (lei=NULL).
Bei API-Fehler wird stale Cache als Fallback verwendet.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Retry- und Rate-Limit-Konfiguration
# ---------------------------------------------------------------------------
_MAX_RETRIES = 3
_BACKOFF_BASE_S = 1.0
_BACKOFF_FACTOR = 2.0
_CACHE_TTL_DAYS = 90

_BASE_URL = "https://api.gleif.org/api/v1/fuzzy-completions"


@dataclass(frozen=True)
class GLEIFResult:
    """Ergebnis eines GLEIF LEI Lookups."""

    raw_name: str
    lei: str | None
    legal_name: str | None
    country: str | None
    entity_status: str | None


class GLEIFAdapter:
    """Async-Adapter fuer die GLEIF LEI API mit PostgreSQL-Cache.

    Ablauf:
    1. Cache-Pruefung (entity_schema.gleif_cache, 90-Tage-TTL)
    2. Cache-Hit (frisch) -> sofort zurueckgeben
    3. Cache-Miss -> GLEIF API aufrufen
    4. Ergebnis im Cache speichern (inkl. Negativ-Ergebnis mit lei=NULL)
    5. API-Fehler -> stale Cache als Fallback, sonst None
    """

    def __init__(
        self,
        pool: Any | None = None,
        timeout: float = 10.0,
        rate_limit_rpm: int = 55,
    ) -> None:
        self._pool = pool
        self._timeout = httpx.Timeout(timeout)
        # Semaphore fuer Rate-Limiting (max concurrent requests)
        self._semaphore = asyncio.Semaphore(min(rate_limit_rpm // 10, 5))
        self._min_interval = 60.0 / rate_limit_rpm
        self._last_request_time = 0.0

    # ------------------------------------------------------------------
    # Oeffentliche API
    # ------------------------------------------------------------------

    async def resolve(self, organization_name: str) -> GLEIFResult | None:
        """Organisationsname gegen GLEIF aufloesen.

        Args:
            organization_name: Name der Organisation (z.B. 'Siemens AG').

        Returns:
            GLEIFResult mit LEI-Daten oder None bei Fehler.
        """
        name = organization_name.strip()
        if not name:
            return None

        # 1. Cache pruefen
        cached = await self._read_cache(name)
        if cached is not None:
            return cached

        # 2. API aufrufen
        try:
            result = await self._fetch_from_api(name)
            await self._write_cache(result)
            return result
        except Exception as exc:
            logger.warning(
                "GLEIF Entity Resolution fehlgeschlagen",
                name=name,
                error=str(exc),
            )
            # 3. Stale Cache als Fallback
            stale = await self._read_cache(name, allow_stale=True)
            if stale is not None:
                logger.info("gleif_stale_cache_fallback", name=name)
                return stale
            return None

    async def resolve_batch(
        self,
        names: list[str],
        *,
        concurrency: int = 5,
    ) -> dict[str, GLEIFResult | None]:
        """Batch-Aufloesung mehrerer Namen mit Rate-Limiting.

        Args:
            names: Liste von Organisationsnamen.
            concurrency: Max gleichzeitige Requests.

        Returns:
            Dict: Name -> GLEIFResult oder None.
        """
        sem = asyncio.Semaphore(concurrency)

        async def _resolve_one(name: str) -> tuple[str, GLEIFResult | None]:
            async with sem:
                result = await self.resolve(name)
                return name, result

        tasks = [_resolve_one(n) for n in names if n.strip()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: dict[str, GLEIFResult | None] = {}
        for item in results:
            if isinstance(item, Exception):
                logger.warning("gleif_batch_fehler", error=str(item))
                continue
            name, result = item
            output[name] = result
        return output

    # ------------------------------------------------------------------
    # Cache-Operationen
    # ------------------------------------------------------------------

    async def _read_cache(
        self, raw_name: str, *, allow_stale: bool = False,
    ) -> GLEIFResult | None:
        """Cache-Eintrag lesen. Gibt None bei Miss zurueck."""
        if self._pool is None:
            return None

        try:
            async with self._pool.acquire() as conn:
                if allow_stale:
                    sql = (
                        "SELECT lei, legal_name, country, entity_status "
                        "FROM entity_schema.gleif_cache "
                        "WHERE raw_name = $1"
                    )
                else:
                    sql = (
                        "SELECT lei, legal_name, country, entity_status "
                        "FROM entity_schema.gleif_cache "
                        "WHERE raw_name = $1 "
                        "AND resolved_at > now() - INTERVAL '%d days'" % _CACHE_TTL_DAYS
                    )
                row = await conn.fetchrow(sql, raw_name)

            if row is None:
                return None

            return GLEIFResult(
                raw_name=raw_name,
                lei=row["lei"],
                legal_name=row["legal_name"],
                country=row["country"],
                entity_status=row["entity_status"],
            )
        except Exception as exc:
            logger.warning("gleif_cache_read_fehler", error=str(exc))
            return None

    async def _write_cache(self, result: GLEIFResult) -> None:
        """Ergebnis in den Cache schreiben (Upsert)."""
        if self._pool is None:
            return

        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO entity_schema.gleif_cache
                        (raw_name, lei, legal_name, country, entity_status, resolved_at)
                    VALUES ($1, $2, $3, $4, $5, now())
                    ON CONFLICT (raw_name) DO UPDATE SET
                        lei = EXCLUDED.lei,
                        legal_name = EXCLUDED.legal_name,
                        country = EXCLUDED.country,
                        entity_status = EXCLUDED.entity_status,
                        resolved_at = now()
                    """,
                    result.raw_name,
                    result.lei,
                    result.legal_name,
                    result.country,
                    result.entity_status,
                )
        except Exception as exc:
            logger.warning("gleif_cache_write_fehler", error=str(exc))

    # ------------------------------------------------------------------
    # API-Aufruf
    # ------------------------------------------------------------------

    async def _fetch_from_api(self, name: str) -> GLEIFResult:
        """GLEIF Fuzzy-Completions API aufrufen.

        Implementiert exponentielles Backoff bei Rate-Limiting (HTTP 429).

        Args:
            name: Organisationsname.

        Returns:
            GLEIFResult (lei kann None sein bei keinem Treffer).

        Raises:
            httpx.HTTPStatusError: Bei persistenten Server-Fehlern.
            httpx.TimeoutException: Bei Timeout.
        """
        # Rate-Limiting
        async with self._semaphore:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_request_time)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_time = time.monotonic()

            last_exc: Exception | None = None

            for attempt in range(_MAX_RETRIES):
                try:
                    async with httpx.AsyncClient(timeout=self._timeout) as client:
                        resp = await client.get(
                            _BASE_URL,
                            params={
                                "field": "entity.legalName",
                                "q": name,
                            },
                        )
                        resp.raise_for_status()

                    data = resp.json()
                    return self._parse_response(name, data)

                except httpx.HTTPStatusError as exc:
                    last_exc = exc
                    if exc.response.status_code != 429:
                        raise
                    backoff = _BACKOFF_BASE_S * (_BACKOFF_FACTOR ** attempt)
                    logger.warning(
                        "gleif_rate_limit",
                        attempt=attempt + 1,
                        backoff_s=backoff,
                    )
                    await asyncio.sleep(backoff)

                except (httpx.TimeoutException, httpx.ConnectError) as exc:
                    last_exc = exc
                    backoff = _BACKOFF_BASE_S * (_BACKOFF_FACTOR ** attempt)
                    logger.warning(
                        "gleif_verbindungsfehler",
                        attempt=attempt + 1,
                        backoff_s=backoff,
                        error=str(exc),
                    )
                    await asyncio.sleep(backoff)

            raise last_exc or RuntimeError("GLEIF API: max retries exhausted")

    @staticmethod
    def _parse_response(raw_name: str, data: dict[str, Any]) -> GLEIFResult:
        """GLEIF JSON:API Response parsen.

        Die API gibt ein JSON:API-Format zurueck. Bester Treffer ist data[0].

        Returns:
            GLEIFResult mit lei=None wenn kein Treffer.
        """
        records = data.get("data", [])
        if not records:
            return GLEIFResult(
                raw_name=raw_name,
                lei=None,
                legal_name=None,
                country=None,
                entity_status=None,
            )

        top = records[0]
        # JSON:API: id ist der LEI, Attribute unter "attributes"
        lei = top.get("id")
        attrs = top.get("attributes", {})
        entity = attrs.get("entity", {})

        legal_name = entity.get("legalName", {}).get("name")
        address = entity.get("legalAddress", {})
        country = address.get("country")
        status = entity.get("status")

        return GLEIFResult(
            raw_name=raw_name,
            lei=lei if lei and len(lei) == 20 else None,
            legal_name=legal_name,
            country=country[:2] if country else None,
            entity_status=status,
        )
