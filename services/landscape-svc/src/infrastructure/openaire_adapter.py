"""OpenAIRE Search API Adapter fuer Publikationsdaten.

Migriert von v1.0 mit folgenden Verbesserungen:
- Rate-Limit-Handling (HTTP 429) mit exponentiellem Backoff
- Graceful Degradation: leere Liste bei Fehlern, Warning-Log
- Modul-Level Token-Cache fuer parallele Year-Requests
- DB-Caching: Ergebnisse werden in research_schema.openaire_cache
  persistiert und bei erneutem Aufruf wiederverwendet (TTL 7 Tage).
  Bei API-Fehler werden auch abgelaufene (stale) Cache-Eintraege
  als Fallback zurueckgegeben.

Der Adapter zaehlt Publikationen pro Jahr ueber parallele
Requests gegen die OpenAIRE Search API. Der Gesamtcount
kommt aus dem JSON-Header-Feld, nicht aus den Ergebnissen selbst.

API-Dokumentation: https://graph.openaire.eu/develop/api.html
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from typing import Any

import asyncpg
import httpx
import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Modul-Level Token-Cache
# ---------------------------------------------------------------------------
# Vermeidet Token-Refresh bei jedem parallelen Year-Request.
# Da OpenAIREAdapter-Instanzen pro LandscapeServicer erzeugt werden
# und mehrere Requests gleichzeitig laufen, ist ein Modul-Level-Cache
# effizienter als ein Instanz-Attribut.

_cached_token: str = ""
_cached_token_exp: float = 0.0

# ---------------------------------------------------------------------------
# Modul-Level Token-Invalid-Flag
# ---------------------------------------------------------------------------
# Wird gesetzt, sobald der Refresh-Token-Endpunkt einen 4xx-Fehler liefert
# (abgelaufener oder widerrufener Token). Das ist ein Konfigurationsfehler,
# kein transientes Problem: die nachfolgenden API-Calls liefern alle 403
# Forbidden. Wir unterdruecken diese vorhersehbaren Warnings (Log-Spam
# mit 22+ Zeilen pro Analyse) und senken sie auf `debug`. Die fachliche
# Behandlung (Fallback auf CORDIS) bleibt unveraendert.
# Der Flag wird beim naechsten erfolgreichen Token-Refresh zurueckgesetzt.
_token_invalid: bool = False

_REFRESH_URL = (
    "https://services.openaire.eu/uoa-user-management"
    "/api/users/getAccessToken"
)
_TOKEN_MARGIN_S = 60  # Refresh 60s vor Ablauf

# ---------------------------------------------------------------------------
# Retry-Konfiguration fuer Rate-Limiting (HTTP 429)
# ---------------------------------------------------------------------------
_MAX_RETRIES = 3
_BACKOFF_BASE_S = 1.0  # Exponentielles Backoff: 1s, 2s, 4s
_BACKOFF_FACTOR = 2.0

# ---------------------------------------------------------------------------
# Cache-Konfiguration
# ---------------------------------------------------------------------------
_CACHE_TTL_DAYS = 7


def _reset_token_invalid_flag() -> None:
    """Setzt das Modul-Level Token-Invalid-Flag zurueck.

    Hauptsaechlich fuer Tests: zwischen Testfaellen muss der Flag-Zustand
    reproduzierbar sein, da `_token_invalid` ein Modul-Level-Singleton ist.
    """
    global _token_invalid  # noqa: PLW0603
    _token_invalid = False


def _normalize_query(query: str) -> str:
    """Query-Key fuer den Cache normalisieren (lowercase, stripped).

    Args:
        query: Rohtext-Suchbegriff.

    Returns:
        Normalisierter String fuer eindeutigen Cache-Lookup.
    """
    return query.lower().strip()


def _token_expiry(token: str) -> float:
    """JWT-Ablaufzeitpunkt (Unix-Timestamp) aus dem Payload extrahieren.

    Dekodiert den Base64-kodierten JWT-Payload und liest das 'exp'-Feld.
    Gibt 0.0 zurueck bei ungueltigem oder fehlendem Token.

    Args:
        token: JWT-String (drei Base64-Teile, getrennt durch '.').

    Returns:
        Unix-Timestamp des Ablaufzeitpunkts oder 0.0 bei Fehler.
    """
    if not token or "." not in token:
        return 0.0
    try:
        parts = token.split(".")
        # Base64-Padding hinzufuegen (JWT-Payloads haben oft kein Padding)
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return float(payload.get("exp", 0))
    except Exception:
        return 0.0


class OpenAIREAdapter:
    """Async-Adapter fuer die OpenAIRE Search API (Publikationen).

    Zaehlt Publikationen pro Jahr ueber parallele API-Abfragen.
    Unterstuetzt:
    - Automatischen Token-Refresh via Refresh-Token
    - Rate-Limit-Handling (HTTP 429) mit exponentiellem Backoff
    - Graceful Degradation: leere Liste bei Gesamtfehler, Warning-Log
    - DB-Caching mit konfigurierbarem TTL und Stale-Fallback

    Wird vom LandscapeServicer als optionale externe Datenquelle genutzt.
    Fehler fuehren nicht zum Abbruch der gesamten Analyse, sondern
    werden als Warnings in der Response dokumentiert.
    """

    BASE_URL = "https://api.openaire.eu/search/publications"

    def __init__(
        self,
        access_token: str = "",
        refresh_token: str = "",
        timeout: float = 10.0,
        pool: asyncpg.Pool | None = None,
    ) -> None:
        """Adapter initialisieren.

        Args:
            access_token: OpenAIRE JWT Access-Token (optional).
                Ohne Token wird die oeffentliche API mit niedrigeren
                Rate-Limits genutzt.
            refresh_token: OpenAIRE Refresh-Token fuer automatische
                Token-Erneuerung (optional).
            timeout: HTTP-Timeout in Sekunden fuer einzelne Requests.
            pool: asyncpg Connection Pool fuer DB-Caching (optional).
                Ohne Pool wird kein Caching durchgefuehrt.
        """
        self._token = access_token
        self._refresh_token = refresh_token
        self._timeout = timeout
        self._pool = pool

    # -----------------------------------------------------------------------
    # Token-Management
    # -----------------------------------------------------------------------

    async def _ensure_valid_token(self) -> None:
        """Access-Token pruefen und bei Bedarf per Refresh-Token erneuern.

        Token-Management-Logik:
        1. Gecachtes Token aus vorherigem Refresh noch gueltig? -> verwenden
        2. Aktuelles Token noch gueltig? -> beibehalten
        3. Refresh-Token vorhanden? -> neues Access-Token holen
        4. Fallback: altes Token verwenden (ggf. niedrigere Rate-Limits)
        """
        global _cached_token, _cached_token_exp, _token_invalid  # noqa: PLW0603

        # Kein Token und kein Refresh-Token -> oeffentlicher Zugang
        if not self._token and not self._refresh_token:
            return

        now = time.time()

        # 1. Gecachtes Token aus vorherigem Refresh noch gueltig?
        if (
            self._refresh_token
            and _cached_token
            and _cached_token_exp - now > _TOKEN_MARGIN_S
        ):
            self._token = _cached_token
            return

        # 2. Aktuelles Token noch gueltig?
        current_exp = _token_expiry(self._token)
        if current_exp - now > _TOKEN_MARGIN_S:
            return

        # 3. Refresh-Token vorhanden? -> neues Access-Token holen
        # Wenn Flag bereits gesetzt ist (voriger Refresh schlug mit 4xx fehl),
        # versuchen wir es dennoch einmal pro Analyse — das Token koennte
        # zwischenzeitlich erneuert worden sein. Schlaegt es wieder fehl,
        # wird das Flag einfach beibehalten.
        if self._refresh_token:
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.get(
                        _REFRESH_URL,
                        params={"refreshToken": self._refresh_token},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                new_token = data.get("access_token", "")
                if new_token:
                    self._token = new_token
                    _cached_token = new_token
                    _cached_token_exp = _token_expiry(new_token)
                    # Erfolgreicher Refresh -> Flag zuruecksetzen,
                    # Warnings wieder aktivieren.
                    _token_invalid = False
                    logger.info(
                        "openaire_token_erneuert",
                        gueltig_min=round((_cached_token_exp - time.time()) / 60, 1),
                    )
                    return
            except httpx.HTTPStatusError as exc:
                # 4xx beim Refresh = Konfigurationsfehler (abgelaufener oder
                # widerrufener Refresh-Token). Einmal klar loggen, dann die
                # vorhersehbare 403-Kaskade unterdruecken.
                status = exc.response.status_code
                if 400 <= status < 500 and not _token_invalid:
                    _token_invalid = True
                    logger.warning(
                        "openaire_token_refresh_fehlgeschlagen",
                        fehler=str(exc),
                        status=status,
                        hinweis=(
                            "Refresh-Token ungueltig/abgelaufen — bitte "
                            "OPENAIRE_REFRESH_TOKEN in .env erneuern "
                            "(siehe docs/DEPLOYMENT.md#openaire-token-erneuern). "
                            "Folgende 403-Meldungen werden bis zum naechsten "
                            "erfolgreichen Refresh auf debug-Level unterdrueckt."
                        ),
                    )
                else:
                    # 5xx oder bereits bekannter Konfigurationsfehler:
                    # leise loggen (debug), um Log-Spam zu vermeiden.
                    logger.debug(
                        "openaire_token_refresh_fehlgeschlagen",
                        fehler=str(exc),
                        status=status,
                    )
            except Exception as exc:
                # Transiente Fehler (Netzwerk, Timeout) — einmalige Warnung.
                if not _token_invalid:
                    logger.warning(
                        "openaire_token_refresh_fehlgeschlagen", fehler=str(exc),
                    )
                else:
                    logger.debug(
                        "openaire_token_refresh_fehlgeschlagen", fehler=str(exc),
                    )

        # 4. Fallback: altes Token verwenden (ggf. niedrigere Rate-Limits)

    # -----------------------------------------------------------------------
    # DB-Cache-Methoden
    # -----------------------------------------------------------------------

    async def _read_cache(
        self, query_key: str, start_year: int, end_year: int, *, allow_stale: bool = False,
    ) -> list[dict[str, int]] | None:
        """Gecachte Ergebnisse aus der Datenbank lesen.

        Args:
            query_key: Normalisierter Suchbegriff.
            start_year: Erstes Jahr (inklusiv).
            end_year: Letztes Jahr (inklusiv).
            allow_stale: Auch abgelaufene Eintraege zurueckgeben (Fallback).

        Returns:
            Liste von Dicts mit 'year' und 'count', oder None bei Cache-Miss.
            None wird zurueckgegeben wenn kein Pool vorhanden, bei DB-Fehler,
            oder wenn nicht alle Jahre im Cache vorhanden sind.
        """
        if self._pool is None:
            return None

        try:
            stale_clause = "" if allow_stale else "AND stale_after > now()"
            sql = f"""
                SELECT year, count
                FROM research_schema.openaire_cache
                WHERE query_key = $1
                  AND year >= $2
                  AND year <= $3
                  {stale_clause}
                ORDER BY year
            """
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(sql, query_key, start_year, end_year)

            if not rows:
                return None

            # Vollstaendigkeitspruefung: alle Jahre muessen vorhanden sein
            expected_years = set(range(start_year, end_year + 1))
            cached_years = {row["year"] for row in rows}
            if not expected_years.issubset(cached_years):
                logger.debug(
                    "openaire_cache_unvollstaendig",
                    query_key=query_key,
                    erwartet=len(expected_years),
                    vorhanden=len(cached_years),
                    fehlend=sorted(expected_years - cached_years),
                )
                return None

            return [{"year": row["year"], "count": row["count"]} for row in rows]

        except Exception as exc:
            logger.warning("openaire_cache_lesefehler", fehler=str(exc))
            return None

    async def _write_cache(
        self, query_key: str, yearly: list[dict[str, int]],
    ) -> None:
        """Ergebnisse in die Datenbank-Cache-Tabelle schreiben (Upsert).

        Verwendet ON CONFLICT ... DO UPDATE, damit wiederholte Abfragen
        den Cache aktualisieren statt Duplikate zu erzeugen.

        Args:
            query_key: Normalisierter Suchbegriff.
            yearly: Liste von Dicts mit 'year' und 'count'.
        """
        if self._pool is None or not yearly:
            return

        sql = """
            INSERT INTO research_schema.openaire_cache (query_key, year, count, fetched_at, stale_after)
            VALUES ($1, $2, $3, now(), now() + INTERVAL '7 days')
            ON CONFLICT (query_key, year) DO UPDATE
                SET count = EXCLUDED.count,
                    fetched_at = EXCLUDED.fetched_at,
                    stale_after = EXCLUDED.stale_after
        """

        try:
            async with self._pool.acquire() as conn:
                # Batch-Upsert in einer Transaktion
                async with conn.transaction():
                    for entry in yearly:
                        await conn.execute(
                            sql, query_key, entry["year"], entry["count"],
                        )
            logger.debug(
                "openaire_cache_geschrieben",
                query_key=query_key,
                eintraege=len(yearly),
            )
        except Exception as exc:
            # Cache-Schreibfehler sind nicht kritisch — nur loggen
            logger.warning("openaire_cache_schreibfehler", fehler=str(exc))

    # -----------------------------------------------------------------------
    # Oeffentliche API
    # -----------------------------------------------------------------------

    async def count_by_year(
        self, query: str, start_year: int, end_year: int,
    ) -> list[dict[str, int]]:
        """Publikationen pro Jahr zaehlen (mit DB-Cache).

        Ablauf:
        1. Cache-Lookup: frische Eintraege (stale_after > now()) pruefen
        2. Cache-Hit: gecachte Ergebnisse direkt zurueckgeben
        3. Cache-Miss: API-Abfrage durchfuehren, Ergebnisse cachen
        4. API-Fehler: stale Cache als Fallback verwenden, sonst leere Liste

        Args:
            query: Freitext-Suchbegriff (z.B. 'quantum computing').
            start_year: Erstes Jahr (inklusiv).
            end_year: Letztes Jahr (inklusiv).

        Returns:
            Liste von Dicts mit 'year' (int) und 'count' (int),
            sortiert aufsteigend nach Jahr. Leere Liste bei Fehler.
        """
        query_key = _normalize_query(query)

        # 1. Cache-Lookup (nur frische Eintraege)
        cached = await self._read_cache(query_key, start_year, end_year)
        if cached is not None:
            logger.info(
                "openaire_cache_hit",
                query_key=query_key,
                start_year=start_year,
                end_year=end_year,
                eintraege=len(cached),
            )
            return cached

        logger.info(
            "openaire_cache_miss",
            query_key=query_key,
            start_year=start_year,
            end_year=end_year,
        )

        # 2. API-Abfrage
        yearly = await self._fetch_from_api(query, start_year, end_year)

        if yearly:
            # 3. Ergebnisse in Cache schreiben
            await self._write_cache(query_key, yearly)
            return yearly

        # 4. API-Fehler: stale Cache als Fallback
        stale = await self._read_cache(
            query_key, start_year, end_year, allow_stale=True,
        )
        if stale is not None:
            logger.warning(
                "openaire_stale_cache_fallback",
                query_key=query_key,
                eintraege=len(stale),
            )
            return stale

        return []

    async def _fetch_from_api(
        self, query: str, start_year: int, end_year: int,
    ) -> list[dict[str, int]]:
        """Publikationen pro Jahr von der OpenAIRE API abrufen (ohne Cache).

        Sendet pro Jahr einen Request an die OpenAIRE Search API
        und extrahiert den Gesamt-Count aus dem JSON-Response-Header.

        Graceful Degradation: Bei Gesamtfehler (z.B. Token-Refresh
        fehlgeschlagen, Netzwerkfehler) wird eine leere Liste zurueckgegeben
        und ein Warning geloggt. Einzelne fehlgeschlagene Jahre werden
        uebersprungen.

        Args:
            query: Freitext-Suchbegriff (z.B. 'quantum computing').
            start_year: Erstes Jahr (inklusiv).
            end_year: Letztes Jahr (inklusiv).

        Returns:
            Liste von Dicts mit 'year' (int) und 'count' (int),
            sortiert aufsteigend nach Jahr. Leere Liste bei Fehler.
        """
        try:
            await self._ensure_valid_token()
        except Exception as exc:
            logger.warning(
                "openaire_token_vorbereitung_fehlgeschlagen",
                fehler=str(exc),
            )
            return []

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                tasks = [
                    self._count_single_year(client, query, year)
                    for year in range(start_year, end_year + 1)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as exc:
            logger.warning(
                "openaire_abfrage_fehlgeschlagen",
                fehler=str(exc),
                query=query,
                start_year=start_year,
                end_year=end_year,
            )
            return []

        # Bei bekanntem Konfigurationsfehler (Refresh-Token ungueltig) sind
        # 403-Fehler vorhersehbar — auf debug-Level absenken, um Log-Spam
        # (22+ Zeilen pro Analyse) zu vermeiden. Die fachliche Behandlung
        # (Fallback auf CORDIS) bleibt unveraendert.
        log_jahr_fehler = logger.debug if _token_invalid else logger.warning
        log_teilergebnis = logger.debug if _token_invalid else logger.warning

        yearly: list[dict[str, int]] = []
        fehler_count = 0
        for result in results:
            if isinstance(result, dict):
                yearly.append(result)
            elif isinstance(result, Exception):
                fehler_count += 1
                log_jahr_fehler(
                    "openaire_jahr_fehlgeschlagen",
                    fehler=str(result),
                )

        if fehler_count > 0:
            log_teilergebnis(
                "openaire_teilergebnis",
                erfolg=len(yearly),
                fehlgeschlagen=fehler_count,
                gesamt=end_year - start_year + 1,
            )

        yearly.sort(key=lambda x: x["year"])
        return yearly

    # -----------------------------------------------------------------------
    # Interne Hilfsmethoden
    # -----------------------------------------------------------------------

    async def _count_single_year(
        self, client: httpx.AsyncClient, query: str, year: int,
    ) -> dict[str, int]:
        """Publikationen fuer ein einzelnes Jahr zaehlen.

        Implementiert exponentielles Backoff bei HTTP 429 (Rate Limit).
        Maximal _MAX_RETRIES Versuche mit ansteigenden Wartezeiten.

        API-Parameter:
        - keywords: Freitext-Suche
        - fromDateAccepted/toDateAccepted: Zeitraum (YYYY-MM-DD)
        - format: json
        - size: 1 (nur Header mit Count, nicht die Ergebnisse selbst)

        Args:
            client: Wiederverwendeter httpx.AsyncClient (Connection Pooling).
            query: Suchbegriff.
            year: Einzelnes Jahr.

        Returns:
            Dict mit 'year' und 'count'.

        Raises:
            httpx.HTTPStatusError: Bei persistenten Server-Fehlern
                (nach Ausschoepfung aller Retries bei 429).
        """
        params: dict[str, str | int] = {
            "keywords": query,
            "fromDateAccepted": f"{year}-01-01",
            "toDateAccepted": f"{year}-12-31",
            "format": "json",
            "size": 1,
        }
        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            t0 = time.monotonic()
            try:
                resp = await client.get(
                    self.BASE_URL, params=params, headers=headers,
                )
                elapsed_ms = int((time.monotonic() - t0) * 1000)

                logger.debug(
                    "openaire_request",
                    year=year,
                    status=resp.status_code,
                    dauer_ms=elapsed_ms,
                    versuch=attempt + 1,
                )

                # Rate Limit: Retry mit exponentiellem Backoff
                if resp.status_code == 429:
                    # Retry-After-Header respektieren, falls vorhanden
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait_s = float(retry_after)
                    else:
                        wait_s = _BACKOFF_BASE_S * (_BACKOFF_FACTOR ** attempt)

                    logger.warning(
                        "openaire_rate_limit",
                        year=year,
                        versuch=attempt + 1,
                        warte_s=round(wait_s, 1),
                    )

                    if attempt < _MAX_RETRIES:
                        await asyncio.sleep(wait_s)
                        continue
                    # Letzter Versuch: Exception ausloesen
                    resp.raise_for_status()

                resp.raise_for_status()

                data: dict[str, Any] = resp.json()
                total_str = data["response"]["header"]["total"]["$"]
                return {"year": year, "count": int(total_str)}

            except httpx.HTTPStatusError as exc:
                last_exc = exc
                # Nur bei 429 retry, andere HTTP-Fehler sofort propagieren
                if exc.response.status_code != 429:
                    raise
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                logger.warning(
                    "openaire_netzwerkfehler",
                    year=year,
                    versuch=attempt + 1,
                    fehler=str(exc),
                    dauer_ms=elapsed_ms,
                )
                if attempt < _MAX_RETRIES:
                    wait_s = _BACKOFF_BASE_S * (_BACKOFF_FACTOR ** attempt)
                    await asyncio.sleep(wait_s)
                    continue
                raise

        # Sollte nicht erreicht werden, aber fuer Typsicherheit
        if last_exc is not None:
            raise last_exc
        msg = f"Unerwarteter Zustand nach {_MAX_RETRIES + 1} Versuchen fuer Jahr {year}"
        raise RuntimeError(msg)
