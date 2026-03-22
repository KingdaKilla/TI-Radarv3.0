"""OpenAIRE Search API Adapter fuer Publikationsdaten.

Migriert von v1.0 mit folgenden Verbesserungen:
- Rate-Limit-Handling (HTTP 429) mit exponentiellem Backoff
- Graceful Degradation: leere Liste bei Fehlern, Warning-Log
- Modul-Level Token-Cache fuer parallele Year-Requests

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
    ) -> None:
        """Adapter initialisieren.

        Args:
            access_token: OpenAIRE JWT Access-Token (optional).
                Ohne Token wird die oeffentliche API mit niedrigeren
                Rate-Limits genutzt.
            refresh_token: OpenAIRE Refresh-Token fuer automatische
                Token-Erneuerung (optional).
            timeout: HTTP-Timeout in Sekunden fuer einzelne Requests.
        """
        self._token = access_token
        self._refresh_token = refresh_token
        self._timeout = timeout

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
        global _cached_token, _cached_token_exp  # noqa: PLW0603

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
                    logger.info(
                        "openaire_token_erneuert",
                        gueltig_min=round((_cached_token_exp - time.time()) / 60, 1),
                    )
                    return
            except Exception as exc:
                logger.warning("openaire_token_refresh_fehlgeschlagen", fehler=str(exc))

        # 4. Fallback: altes Token verwenden (ggf. niedrigere Rate-Limits)

    # -----------------------------------------------------------------------
    # Oeffentliche API
    # -----------------------------------------------------------------------

    async def count_by_year(
        self, query: str, start_year: int, end_year: int,
    ) -> list[dict[str, int]]:
        """Publikationen pro Jahr zaehlen (parallele API-Abfragen).

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

        yearly: list[dict[str, int]] = []
        fehler_count = 0
        for result in results:
            if isinstance(result, dict):
                yearly.append(result)
            elif isinstance(result, Exception):
                fehler_count += 1
                logger.warning(
                    "openaire_jahr_fehlgeschlagen",
                    fehler=str(result),
                )

        if fehler_count > 0:
            logger.warning(
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
