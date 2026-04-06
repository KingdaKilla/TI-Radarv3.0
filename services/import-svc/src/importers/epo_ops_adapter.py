"""EPO Open Patent Services (OPS) REST API Adapter.

Async-Adapter fuer die EPO OPS API mit folgenden Funktionen:
- OAuth 2.0 Client Credentials Flow (consumer_key + consumer_secret)
- DB-Caching in patent_schema.epo_ops_cache mit 7-Tage-TTL
- Rate-Limiting via Semaphore + Mindestabstand zwischen Requests
- Exponentielles Backoff (1s, 2s, 4s) bei HTTP 429 / Timeout
- Stale-Cache-Fallback bei API-Fehlern
- Upsert in patent_schema.patents mit ON CONFLICT DO UPDATE
  (API-Daten ueberschreiben Bulk-Daten, da aktueller)

API-Dokumentation: https://developers.epo.org/ops-v3-2/apis
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import TYPE_CHECKING, Any

import httpx
import structlog

if TYPE_CHECKING:
    import asyncpg

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Modul-Level Token-Cache
# ---------------------------------------------------------------------------
# EPO OPS Token (Client Credentials) hat typischerweise 20 Min Laufzeit.
# Modul-Level-Cache vermeidet unnoetige Token-Requests bei parallelen Aufrufen.

_cached_token: str = ""
_cached_token_exp: float = 0.0

_TOKEN_MARGIN_S = 60  # Token 60s vor Ablauf erneuern

# ---------------------------------------------------------------------------
# API-Endpunkte
# ---------------------------------------------------------------------------
_TOKEN_URL = "https://ops.epo.org/3.2/auth/accesstoken"
_SEARCH_URL = (
    "https://ops.epo.org/3.2/rest-services/published-data/search"
)

# ---------------------------------------------------------------------------
# Retry-Konfiguration fuer Rate-Limiting (HTTP 429) und Timeouts
# ---------------------------------------------------------------------------
_MAX_RETRIES = 3
_BACKOFF_BASE_S = 1.0   # Exponentielles Backoff: 1s, 2s, 4s
_BACKOFF_FACTOR = 2.0

# ---------------------------------------------------------------------------
# Cache-Konfiguration
# ---------------------------------------------------------------------------
_CACHE_TTL_DAYS = 7

# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
_PAGE_SIZE = 100  # EPO OPS Maximum pro Request


def _normalize_technology(technology: str) -> str:
    """Technologie-Key fuer den Cache normalisieren (lowercase, stripped).

    Args:
        technology: Roher Suchbegriff.

    Returns:
        Normalisierter String fuer eindeutigen Cache-Lookup.
    """
    return technology.lower().strip()


class EpoOpsAdapter:
    """Async-Adapter fuer die EPO Open Patent Services REST API.

    Sucht Patente per CQL-Query und persistiert Ergebnisse sowohl
    im Cache (7 Tage TTL) als auch in patent_schema.patents via Upsert.

    Unterstuetzt:
    - OAuth 2.0 Client Credentials (consumer_key + consumer_secret)
    - Rate-Limiting (Semaphore + Mindestabstand)
    - Exponentielles Backoff bei HTTP 429 und Timeout-Fehlern
    - DB-Caching mit Stale-Fallback bei API-Ausfaellen
    - Graceful Degradation: leere Liste bei totalem Fehler

    Wird vom Import-Service als optionale Echtzeit-Datenquelle genutzt.
    """

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        timeout: float = 15.0,
        rate_limit_rpm: int = 200,
        pool: "asyncpg.Pool | None" = None,
    ) -> None:
        """Adapter initialisieren.

        Args:
            consumer_key: EPO OPS Consumer Key (API-Zugang).
            consumer_secret: EPO OPS Consumer Secret (API-Zugang).
            timeout: HTTP-Timeout in Sekunden fuer einzelne Requests.
            rate_limit_rpm: Maximale Requests pro Minute (EPO Limit).
                Steuert sowohl die Semaphore-Groesse als auch den
                Mindestabstand zwischen aufeinanderfolgenden Requests.
            pool: asyncpg Connection Pool fuer DB-Caching und Upsert.
                Ohne Pool wird kein Caching/Upsert durchgefuehrt.
        """
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._timeout = timeout
        self._pool = pool

        # Rate-Limiting: Semaphore fuer maximale Parallelitaet
        max_concurrent = max(1, rate_limit_rpm // 20)
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # Mindestabstand zwischen Requests (Sekunden)
        self._min_interval_s = 60.0 / max(1, rate_limit_rpm)
        self._last_request_time: float = 0.0
        self._rate_lock = asyncio.Lock()

    # -----------------------------------------------------------------------
    # Token-Management (OAuth 2.0 Client Credentials)
    # -----------------------------------------------------------------------

    async def _fetch_access_token(self) -> str:
        """Access-Token via OAuth 2.0 Client Credentials holen oder aus Cache.

        EPO OPS erwartet:
        - POST an /auth/accesstoken
        - Basic Auth mit consumer_key:consumer_secret
        - Body: grant_type=client_credentials

        Antwort: {"access_token": "...", "expires_in": 1200, ...}

        Returns:
            Gueltiges Bearer-Token als String.

        Raises:
            httpx.HTTPStatusError: Bei Auth-Fehlern (401, 403).
            httpx.TimeoutException: Bei Timeout.
        """
        global _cached_token, _cached_token_exp  # noqa: PLW0603

        now = time.time()

        # Gecachtes Token noch gueltig?
        if _cached_token and _cached_token_exp - now > _TOKEN_MARGIN_S:
            return _cached_token

        logger.info("epo_ops_token_anforderung")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                _TOKEN_URL,
                auth=(self._consumer_key, self._consumer_secret),
                data={"grant_type": "client_credentials"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()

        token = data.get("access_token", "")
        expires_in = int(data.get("expires_in", 1200))

        if not token:
            msg = "EPO OPS: Kein access_token in der Antwort"
            raise ValueError(msg)

        _cached_token = token
        _cached_token_exp = now + expires_in

        logger.info(
            "epo_ops_token_erhalten",
            gueltig_min=round(expires_in / 60, 1),
        )

        return token

    # -----------------------------------------------------------------------
    # Rate-Limiting
    # -----------------------------------------------------------------------

    async def _enforce_rate_limit(self) -> None:
        """Mindestabstand zwischen aufeinanderfolgenden Requests einhalten.

        Verwendet einen Lock, um Thread-sicheren Zugriff auf den
        Zeitstempel des letzten Requests zu gewaehrleisten.
        """
        async with self._rate_lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval_s:
                wait = self._min_interval_s - elapsed
                await asyncio.sleep(wait)
            self._last_request_time = time.monotonic()

    # -----------------------------------------------------------------------
    # DB-Cache-Methoden
    # -----------------------------------------------------------------------

    async def _read_cache(
        self,
        technology: str,
        start_year: int | None,
        end_year: int | None,
        *,
        allow_stale: bool = False,
    ) -> list[dict] | None:
        """Gecachte Suchergebnisse aus der Datenbank lesen.

        Args:
            technology: Normalisierter Suchbegriff.
            start_year: Erstes Jahr (inklusiv), None fuer unbegrenzt.
            end_year: Letztes Jahr (inklusiv), None fuer unbegrenzt.
            allow_stale: Auch abgelaufene Eintraege zurueckgeben (Fallback).

        Returns:
            Liste von Patent-Dicts, oder None bei Cache-Miss.
        """
        if self._pool is None:
            return None

        try:
            stale_clause = "" if allow_stale else "AND stale_after > NOW()"
            sql = f"""
                SELECT result_json
                FROM patent_schema.epo_ops_cache
                WHERE technology = $1
                  AND start_year IS NOT DISTINCT FROM $2
                  AND end_year IS NOT DISTINCT FROM $3
                  {stale_clause}
            """
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(sql, technology, start_year, end_year)

            if row is None:
                return None

            result = json.loads(row["result_json"]) if isinstance(row["result_json"], str) else row["result_json"]

            logger.debug(
                "epo_ops_cache_hit",
                technology=technology,
                start_year=start_year,
                end_year=end_year,
                allow_stale=allow_stale,
                eintraege=len(result),
            )

            return result

        except Exception as exc:
            logger.warning("epo_ops_cache_lesefehler", fehler=str(exc))
            return None

    async def _write_cache(
        self,
        technology: str,
        start_year: int | None,
        end_year: int | None,
        patents: list[dict],
    ) -> None:
        """Suchergebnisse in die Cache-Tabelle schreiben (Upsert).

        Verwendet ON CONFLICT ... DO UPDATE, damit wiederholte Abfragen
        den Cache aktualisieren statt Duplikate zu erzeugen.

        Args:
            technology: Normalisierter Suchbegriff.
            start_year: Erstes Jahr (inklusiv), None fuer unbegrenzt.
            end_year: Letztes Jahr (inklusiv), None fuer unbegrenzt.
            patents: Liste von Patent-Dicts als JSON zu persistieren.
        """
        if self._pool is None:
            return

        sql = """
            INSERT INTO patent_schema.epo_ops_cache
                (technology, start_year, end_year, result_json, fetched_at, stale_after)
            VALUES ($1, $2, $3, $4::jsonb, NOW(), NOW() + INTERVAL '7 days')
            ON CONFLICT (technology, start_year, end_year) DO UPDATE
                SET result_json = EXCLUDED.result_json,
                    fetched_at = EXCLUDED.fetched_at,
                    stale_after = EXCLUDED.stale_after
        """

        try:
            result_json = json.dumps(patents, ensure_ascii=False, default=str)
            async with self._pool.acquire() as conn:
                await conn.execute(sql, technology, start_year, end_year, result_json)
            logger.debug(
                "epo_ops_cache_geschrieben",
                technology=technology,
                eintraege=len(patents),
            )
        except Exception as exc:
            # Cache-Schreibfehler sind nicht kritisch — nur loggen
            logger.warning("epo_ops_cache_schreibfehler", fehler=str(exc))

    # -----------------------------------------------------------------------
    # Patent-Upsert (API-Daten > Bulk-Daten)
    # -----------------------------------------------------------------------

    async def _upsert_patents(self, patents: list[dict]) -> None:
        """Patente in patent_schema.patents per Upsert einfuegen/aktualisieren.

        WICHTIG: Verwendet ON CONFLICT (publication_number, publication_year)
        DO UPDATE SET ... — NICHT DO NOTHING. API-Daten sind aktueller als
        Bulk-Importe und muessen bestehende Zeilen ueberschreiben.

        Args:
            patents: Liste von Patent-Dicts mit den Feldern:
                publication_number, country, doc_number, kind,
                title, publication_date, publication_year, cpc_codes.
        """
        if self._pool is None or not patents:
            return

        sql = """
            INSERT INTO patent_schema.patents
                (publication_number, country, doc_number, kind,
                 title, publication_date, publication_year, cpc_codes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (publication_number, publication_year) DO UPDATE SET
                country          = EXCLUDED.country,
                doc_number       = EXCLUDED.doc_number,
                kind             = EXCLUDED.kind,
                title            = EXCLUDED.title,
                publication_date = EXCLUDED.publication_date,
                cpc_codes        = EXCLUDED.cpc_codes
        """

        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    for patent in patents:
                        await conn.execute(
                            sql,
                            patent.get("publication_number"),
                            patent.get("country"),
                            patent.get("doc_number"),
                            patent.get("kind"),
                            patent.get("title"),
                            patent.get("publication_date"),
                            patent.get("publication_year"),
                            patent.get("cpc_codes"),
                        )
            logger.info(
                "epo_ops_upsert_erledigt",
                eintraege=len(patents),
            )
        except Exception as exc:
            logger.warning("epo_ops_upsert_fehler", fehler=str(exc), anzahl=len(patents))

    # -----------------------------------------------------------------------
    # API-Abfrage mit Retry
    # -----------------------------------------------------------------------

    async def _fetch_from_api(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        max_results: int = 100,
    ) -> list[dict] | None:
        """Patente von der EPO OPS API abrufen (ohne Cache).

        Baut eine CQL-Query aus Technologie und optionalem Zeitraum,
        paginiert ueber Range-Header und parst die Ergebnisse.

        Implementiert exponentielles Backoff bei HTTP 429 und Timeouts.

        Args:
            technology: Suchbegriff fuer die Titelsuche (CQL ti=...).
            start_year: Erstes Publikationsjahr (inklusiv, optional).
            end_year: Letztes Publikationsjahr (inklusiv, optional).
            max_results: Maximale Anzahl zurueckgegebener Patente.

        Returns:
            Liste von Patent-Dicts oder None bei totalem Fehler.
        """
        try:
            token = await self._fetch_access_token()
        except Exception as exc:
            logger.warning(
                "epo_ops_token_fehler",
                fehler=str(exc),
            )
            return None

        # CQL-Query bauen
        cql_parts = [f'ti="{technology}"']
        if start_year and end_year:
            cql_parts.append(f"pd within {start_year}-{end_year}")
        elif start_year:
            cql_parts.append(f"pd >= {start_year}")
        elif end_year:
            cql_parts.append(f"pd <= {end_year}")

        cql_query = " and ".join(cql_parts)

        all_patents: list[dict] = []
        offset = 1

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            while len(all_patents) < max_results:
                # Seitengroesse berechnen (letzte Seite kann kleiner sein)
                remaining = max_results - len(all_patents)
                page_size = min(_PAGE_SIZE, remaining)
                range_end = offset + page_size - 1

                page_result = await self._fetch_page(
                    client=client,
                    token=token,
                    cql_query=cql_query,
                    range_start=offset,
                    range_end=range_end,
                )

                if page_result is None:
                    # Fehler oder keine weiteren Ergebnisse
                    break

                if not page_result:
                    # Leere Seite: keine weiteren Ergebnisse
                    break

                all_patents.extend(page_result)
                offset += page_size

                # Weniger Ergebnisse als angefragt: letzte Seite erreicht
                if len(page_result) < page_size:
                    break

        if not all_patents:
            return None

        return all_patents

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        token: str,
        cql_query: str,
        range_start: int,
        range_end: int,
    ) -> list[dict] | None:
        """Eine einzelne Seite von der EPO OPS API abrufen.

        Implementiert exponentielles Backoff bei HTTP 429 (Rate Limit)
        und Netzwerk-/Timeout-Fehlern.

        Args:
            client: Wiederverwendeter httpx.AsyncClient.
            token: Gueltiges Bearer-Token.
            cql_query: CQL-Suchausdruck.
            range_start: Erster Ergebnis-Index (1-basiert).
            range_end: Letzter Ergebnis-Index (inklusiv).

        Returns:
            Liste von Patent-Dicts, leere Liste bei leerem Ergebnis,
            oder None bei persistentem Fehler.
        """
        headers: dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Range": f"{range_start}-{range_end}",
        }
        params: dict[str, str] = {"q": cql_query}

        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            async with self._semaphore:
                await self._enforce_rate_limit()

                t0 = time.monotonic()
                try:
                    resp = await client.get(
                        _SEARCH_URL, params=params, headers=headers,
                    )
                    elapsed_ms = int((time.monotonic() - t0) * 1000)

                    logger.debug(
                        "epo_ops_request",
                        cql=cql_query,
                        range=f"{range_start}-{range_end}",
                        status=resp.status_code,
                        dauer_ms=elapsed_ms,
                        versuch=attempt + 1,
                    )

                    # 404 = keine Ergebnisse fuer diese Query
                    if resp.status_code == 404:
                        return []

                    # Rate Limit: Retry mit exponentiellem Backoff
                    if resp.status_code == 429:
                        retry_after = resp.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            wait_s = float(retry_after)
                        else:
                            wait_s = _BACKOFF_BASE_S * (_BACKOFF_FACTOR ** attempt)

                        logger.warning(
                            "epo_ops_rate_limit",
                            cql=cql_query,
                            versuch=attempt + 1,
                            warte_s=round(wait_s, 1),
                        )

                        if attempt < _MAX_RETRIES:
                            await asyncio.sleep(wait_s)
                            continue
                        # Letzter Versuch: aufgeben
                        return None

                    resp.raise_for_status()

                    data: dict[str, Any] = resp.json()
                    return self._parse_search_results(data)

                except httpx.HTTPStatusError as exc:
                    last_exc = exc
                    if exc.response.status_code == 429:
                        # Bereits oben behandelt, nur Sicherheit
                        continue
                    logger.warning(
                        "epo_ops_http_fehler",
                        status=exc.response.status_code,
                        cql=cql_query,
                        versuch=attempt + 1,
                    )
                    return None

                except (httpx.TimeoutException, httpx.ConnectError) as exc:
                    last_exc = exc
                    elapsed_ms = int((time.monotonic() - t0) * 1000)
                    logger.warning(
                        "epo_ops_netzwerkfehler",
                        cql=cql_query,
                        versuch=attempt + 1,
                        fehler=str(exc),
                        dauer_ms=elapsed_ms,
                    )
                    if attempt < _MAX_RETRIES:
                        wait_s = _BACKOFF_BASE_S * (_BACKOFF_FACTOR ** attempt)
                        await asyncio.sleep(wait_s)
                        continue
                    return None

        logger.error(
            "epo_ops_alle_versuche_fehlgeschlagen",
            cql=cql_query,
            letzter_fehler=str(last_exc) if last_exc else "unbekannt",
        )
        return None

    # -----------------------------------------------------------------------
    # Response-Parsing
    # -----------------------------------------------------------------------

    @staticmethod
    def _parse_search_results(data: dict[str, Any]) -> list[dict]:
        """EPO OPS JSON-Response in eine Liste von Patent-Dicts parsen.

        Navigiert die verschachtelte Struktur:
        ops:world-patent-data > ops:biblio-search > ops:search-result
        > ops:publication-reference (Array)

        Jede publication-reference enthaelt:
        - document-id mit country, doc-number, kind
        - (Optional) exchange-documents mit Titel und CPC-Codes

        Args:
            data: Geparstes JSON-Response von der EPO OPS API.

        Returns:
            Liste von Patent-Dicts mit normalisierten Feldern.
        """
        patents: list[dict] = []

        try:
            # Verschachtelte EPO-Struktur navigieren
            world_data = data.get("ops:world-patent-data", data)
            biblio_search = world_data.get("ops:biblio-search", {})
            search_result = biblio_search.get("ops:search-result", {})

            # publication-reference kann ein Dict (1 Ergebnis) oder
            # eine Liste (mehrere Ergebnisse) sein
            pub_refs = search_result.get("ops:publication-reference", [])
            if isinstance(pub_refs, dict):
                pub_refs = [pub_refs]

            for pub_ref in pub_refs:
                try:
                    patent = EpoOpsAdapter._parse_single_patent(pub_ref)
                    if patent:
                        patents.append(patent)
                except Exception as exc:
                    logger.debug(
                        "epo_ops_parse_einzelpatent_fehler",
                        fehler=str(exc),
                    )

        except Exception as exc:
            logger.warning(
                "epo_ops_parse_fehler",
                fehler=str(exc),
            )

        return patents

    @staticmethod
    def _parse_single_patent(pub_ref: dict[str, Any]) -> dict | None:
        """Ein einzelnes Patent aus einer publication-reference parsen.

        Args:
            pub_ref: Dict einer ops:publication-reference.

        Returns:
            Patent-Dict oder None wenn nicht parsbar.
        """
        # document-id kann Dict oder Liste sein
        doc_ids = pub_ref.get("document-id", [])
        if isinstance(doc_ids, dict):
            doc_ids = [doc_ids]

        # Bevorzugt docdb-Format verwenden
        doc_id = None
        for did in doc_ids:
            if did.get("@document-id-type") == "docdb":
                doc_id = did
                break
        if doc_id is None and doc_ids:
            doc_id = doc_ids[0]
        if doc_id is None:
            return None

        country = _extract_text(doc_id.get("country", ""))
        doc_number = _extract_text(doc_id.get("doc-number", ""))
        kind = _extract_text(doc_id.get("kind", ""))

        if not doc_number:
            return None

        publication_number = f"{country}{doc_number}{kind}".strip()

        # Publikationsdatum extrahieren
        publication_date = None
        publication_year = None
        date_str = _extract_text(doc_id.get("date", ""))
        if date_str and len(date_str) >= 4:
            try:
                publication_year = int(date_str[:4])
            except ValueError:
                pass
            if len(date_str) == 8 and date_str.isdigit():
                publication_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        # Titel extrahieren (falls in exchange-documents vorhanden)
        title = None
        exchange_docs = pub_ref.get("exchange-document", pub_ref.get("exchange-documents", {}))
        if isinstance(exchange_docs, list) and exchange_docs:
            exchange_docs = exchange_docs[0]
        if isinstance(exchange_docs, dict):
            biblio = exchange_docs.get("bibliographic-data", {})
            invention_title = biblio.get("invention-title", {})
            if isinstance(invention_title, list):
                # Englischen Titel bevorzugen
                for t in invention_title:
                    if isinstance(t, dict) and t.get("@lang") == "en":
                        title = _extract_text(t.get("$", ""))
                        break
                if title is None and invention_title:
                    first = invention_title[0]
                    title = _extract_text(first.get("$", "") if isinstance(first, dict) else first)
            elif isinstance(invention_title, dict):
                title = _extract_text(invention_title.get("$", ""))
            elif isinstance(invention_title, str):
                title = invention_title

        # CPC-Codes extrahieren
        cpc_codes: list[str] = []
        if isinstance(exchange_docs, dict):
            biblio = exchange_docs.get("bibliographic-data", {})
            classifications = biblio.get("patent-classifications", {})
            patent_classification = classifications.get("patent-classification", [])
            if isinstance(patent_classification, dict):
                patent_classification = [patent_classification]
            for cls in patent_classification:
                if isinstance(cls, dict):
                    scheme = _extract_text(cls.get("classification-scheme", {}).get("@scheme", ""))
                    if scheme.upper() in ("CPC", "CPCI", "CPCA", ""):
                        section = _extract_text(cls.get("section", ""))
                        class_val = _extract_text(cls.get("class", ""))
                        subclass = _extract_text(cls.get("subclass", ""))
                        main_group = _extract_text(cls.get("main-group", ""))
                        subgroup = _extract_text(cls.get("subgroup", ""))
                        if section:
                            code = f"{section}{class_val}{subclass}{main_group}/{subgroup}"
                            cpc_codes.append(code)

        return {
            "publication_number": publication_number,
            "country": country or None,
            "doc_number": doc_number,
            "kind": kind or None,
            "title": title,
            "publication_date": publication_date,
            "publication_year": publication_year,
            "cpc_codes": cpc_codes or None,
        }

    # -----------------------------------------------------------------------
    # Oeffentliche API
    # -----------------------------------------------------------------------

    async def search_patents(
        self,
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        max_results: int = 100,
    ) -> list[dict]:
        """Patente zu einer Technologie suchen (mit DB-Cache + Upsert).

        Ablauf:
        1. Cache-Lookup: frische Eintraege (stale_after > NOW()) pruefen
        2. Cache-Hit: gecachte Ergebnisse direkt zurueckgeben
        3. Cache-Miss: API-Abfrage durchfuehren, in Cache + patents-Tabelle schreiben
        4. API-Fehler: stale Cache als Fallback verwenden, sonst leere Liste

        Args:
            technology: Suchbegriff fuer die Patent-Titelsuche
                (z.B. 'quantum computing', 'machine learning').
            start_year: Erstes Publikationsjahr (inklusiv, optional).
            end_year: Letztes Publikationsjahr (inklusiv, optional).
            max_results: Maximale Anzahl zurueckgegebener Patente.
                Default 100, Maximum wird durch EPO API begrenzt.

        Returns:
            Liste von Patent-Dicts mit den Feldern:
            publication_number, country, doc_number, kind,
            title, publication_date, publication_year, cpc_codes.
            Leere Liste bei totalem Fehler (Graceful Degradation).
        """
        tech_key = _normalize_technology(technology)

        # 1. Cache-Lookup (nur frische Eintraege)
        cached = await self._read_cache(tech_key, start_year, end_year)
        if cached is not None:
            logger.info(
                "epo_ops_cache_hit",
                technology=tech_key,
                start_year=start_year,
                end_year=end_year,
                eintraege=len(cached),
            )
            return cached

        logger.info(
            "epo_ops_cache_miss",
            technology=tech_key,
            start_year=start_year,
            end_year=end_year,
        )

        # 2. API-Abfrage
        patents = await self._fetch_from_api(
            technology,
            start_year=start_year,
            end_year=end_year,
            max_results=max_results,
        )

        if patents:
            # 3a. Ergebnisse in Cache schreiben
            await self._write_cache(tech_key, start_year, end_year, patents)

            # 3b. Patente in die Haupttabelle upserten (API > Bulk)
            await self._upsert_patents(patents)

            return patents

        # 4. API-Fehler: stale Cache als Fallback
        stale = await self._read_cache(
            tech_key, start_year, end_year, allow_stale=True,
        )
        if stale is not None:
            logger.warning(
                "epo_ops_stale_cache_fallback",
                technology=tech_key,
                eintraege=len(stale),
            )
            return stale

        # Graceful Degradation: leere Liste statt Exception
        return []


# ---------------------------------------------------------------------------
# Hilfsfunktionen (modul-level)
# ---------------------------------------------------------------------------


def _extract_text(value: Any) -> str:
    """Text aus einem EPO OPS JSON-Wert extrahieren.

    EPO OPS gibt Werte manchmal als {"$": "text"} statt als
    einfachen String zurueck. Diese Funktion normalisiert beides.

    Args:
        value: String, Dict mit "$"-Key, oder anderer Typ.

    Returns:
        Extrahierter Text-String (stripped).
    """
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("$", "")).strip()
    if value is None:
        return ""
    return str(value).strip()
