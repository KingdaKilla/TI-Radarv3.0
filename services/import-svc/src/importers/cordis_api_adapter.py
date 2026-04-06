"""CORDIS REST API Adapter — EU-Forschungsprojekte per Technologie-Suche abrufen.

Nutzt die oeffentliche CORDIS Search API (kein API-Key erforderlich):
    GET https://cordis.europa.eu/api/search?q={technology}&type=project&page={n}&pageSize={size}

Caching in cordis_schema.cordis_api_cache (JSONB, 7-Tage-TTL).
Rate-Limiting: konservativ 30 RPM via Semaphore + Mindest-Intervall.
Exponentielles Backoff bei HTTP 429 / Timeout (1s, 2s, 4s).
Stale-Cache-Fallback bei API-Fehlern.
Upsert in cordis_schema.projects mit ON CONFLICT DO UPDATE — API-Daten
ueberschreiben aeltere Bulk-Daten.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

import httpx
import structlog

if TYPE_CHECKING:
    import asyncpg

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

_BASE_URL = "https://cordis.europa.eu/api/search"
_MAX_RETRIES = 3
_BACKOFF_BASE_S = 1.0
_BACKOFF_FACTOR = 2.0
_CACHE_TTL_DAYS = 7
_MAX_PAGE_SIZE = 100


# ---------------------------------------------------------------------------
# Hilfs-Funktionen (sichere Konvertierung)
# ---------------------------------------------------------------------------


def _safe_str(value: Any, max_len: int | None = None) -> str | None:
    """Sicherer String-Zugriff mit optionaler Laengenbegrenzung."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if max_len is not None:
        s = s[:max_len]
    return s


def _safe_int(value: Any) -> int | None:
    """Sicher einen Integer parsen."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_date(date_str: str | None) -> date | None:
    """Datum aus verschiedenen CORDIS-Formaten parsen.

    Unterstuetzte Formate:
        YYYY-MM-DD, DD/MM/YYYY, YYYY-MM-DDTHH:MM:SS
    """
    if not date_str or (isinstance(date_str, str) and not date_str.strip()):
        return None
    date_str = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(value: Any) -> Decimal | None:
    """Dezimalwert sicher parsen (Komma und Punkt als Trennzeichen)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        cleaned = value.strip().replace(",", ".")
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _detect_framework(record: dict[str, Any]) -> str:
    """Framework-Programm aus dem Projekt-Record ableiten.

    CORDIS liefert das Framework oft unter ``frameworkProgramme``,
    ``programme`` oder im Titel/Thema.
    """
    fp = _safe_str(record.get("frameworkProgramme")) or ""
    programme = _safe_str(record.get("programme")) or ""
    combined = (fp + " " + programme).upper()

    if "HORIZON" in combined:
        return "HORIZON"
    if "H2020" in combined:
        return "H2020"
    if "FP7" in combined:
        return "FP7"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# CordisApiAdapter
# ---------------------------------------------------------------------------


class CordisApiAdapter:
    """Async-Adapter fuer die CORDIS REST API mit PostgreSQL-Cache.

    Ablauf von ``search_projects()``:
    1. Cache-Pruefung (cordis_schema.cordis_api_cache, 7-Tage-TTL)
    2. Cache-Hit (frisch) -> sofort zurueckgeben
    3. Cache-Miss -> CORDIS API aufrufen (paginiert, max 100 pro Seite)
    4. Ergebnis im Cache speichern + Upsert in cordis_schema.projects
    5. API-Fehler -> stale Cache als Fallback, sonst leere Liste
    """

    def __init__(
        self,
        timeout: float = 15.0,
        rate_limit_rpm: int = 30,
        pool: Any | None = None,
    ) -> None:
        self._pool: asyncpg.Pool | None = pool
        self._timeout = httpx.Timeout(timeout)
        # Semaphore: maximal 3 gleichzeitige Requests (konservativ fuer 30 RPM)
        self._semaphore = asyncio.Semaphore(min(max(rate_limit_rpm // 10, 1), 3))
        self._min_interval = 60.0 / rate_limit_rpm
        self._last_request_time = 0.0

    # ------------------------------------------------------------------
    # Oeffentliche API
    # ------------------------------------------------------------------

    async def search_projects(
        self,
        technology: str,
        *,
        max_results: int = 200,
    ) -> list[dict]:
        """Projekte zu einer Technologie suchen.

        Prueft zuerst den Cache. Bei Cache-Miss wird die CORDIS API
        abgefragt und die Ergebnisse sowohl gecacht als auch per Upsert
        in cordis_schema.projects geschrieben.

        Args:
            technology: Suchbegriff (z.B. 'quantum computing').
            max_results: Maximale Anzahl zurueckzugebender Projekte.

        Returns:
            Liste von Projekt-Dicts (kann leer sein bei Fehler).
        """
        technology = technology.strip()
        if not technology:
            return []

        # 1. Cache pruefen (frisch)
        cached = await self._read_cache(technology)
        if cached is not None:
            logger.info(
                "cordis_api_cache_hit",
                technology=technology,
                count=len(cached),
            )
            return cached[:max_results]

        # 2. API aufrufen
        try:
            projects = await self._fetch_from_api(technology, max_results=max_results)
        except Exception as exc:
            logger.warning(
                "cordis_api_fetch_fehlgeschlagen",
                technology=technology,
                error=str(exc),
            )
            projects = None

        if projects is not None:
            # 3a. Erfolg -> Cache + Upsert
            await self._write_cache(technology, projects)
            await self._upsert_projects(projects)
            logger.info(
                "cordis_api_fetch_erfolg",
                technology=technology,
                count=len(projects),
            )
            return projects

        # 3b. Fehler -> stale Cache als Fallback
        stale = await self._read_cache(technology, allow_stale=True)
        if stale is not None:
            logger.info(
                "cordis_api_stale_cache_fallback",
                technology=technology,
                count=len(stale),
            )
            return stale[:max_results]

        # 4. Totaler Fehler -> leere Liste (graceful degradation)
        logger.warning(
            "cordis_api_keine_ergebnisse",
            technology=technology,
        )
        return []

    # ------------------------------------------------------------------
    # API-Aufruf mit Pagination
    # ------------------------------------------------------------------

    async def _fetch_from_api(
        self,
        technology: str,
        max_results: int = 200,
    ) -> list[dict] | None:
        """CORDIS Search API paginiert aufrufen.

        Implementiert exponentielles Backoff bei HTTP 429 und Timeouts.
        Sammelt Ergebnisse seitenweise bis ``max_results`` oder alle
        verfuegbaren Ergebnisse abgerufen sind.

        Args:
            technology: Suchbegriff.
            max_results: Maximale Ergebnisanzahl.

        Returns:
            Liste von Projekt-Dicts oder None bei persistentem Fehler.

        Raises:
            httpx.HTTPStatusError: Bei nicht-retriable Server-Fehlern.
        """
        all_projects: list[dict] = []
        page = 1
        page_size = min(max_results, _MAX_PAGE_SIZE)

        while len(all_projects) < max_results:
            page_data = await self._fetch_page(technology, page=page, page_size=page_size)

            if page_data is None:
                # Erster Seitenaufruf fehlgeschlagen -> None zurueck
                if not all_projects:
                    return None
                # Spaetere Seite fehlgeschlagen -> bisherige Ergebnisse behalten
                break

            results = page_data.get("results", [])
            total = page_data.get("total", 0)

            for record in results:
                project = self._parse_project(record)
                if project is not None:
                    all_projects.append(project)

            # Abbruch: keine weiteren Seiten oder max_results erreicht
            fetched_so_far = page * page_size
            if not results or fetched_so_far >= total or len(all_projects) >= max_results:
                break

            page += 1

        return all_projects[:max_results]

    async def _fetch_page(
        self,
        technology: str,
        *,
        page: int,
        page_size: int,
    ) -> dict | None:
        """Einzelne Seite von der CORDIS API abrufen (mit Retry + Backoff).

        Args:
            technology: Suchbegriff.
            page: Seitennummer (1-basiert).
            page_size: Ergebnisse pro Seite (max 100).

        Returns:
            Parsed JSON-Response oder None bei Fehler.
        """
        await self._enforce_rate_limit()

        last_exc: Exception | None = None

        async with self._semaphore:
            for attempt in range(_MAX_RETRIES):
                try:
                    async with httpx.AsyncClient(timeout=self._timeout) as client:
                        resp = await client.get(
                            _BASE_URL,
                            params={
                                "q": technology,
                                "type": "project",
                                "page": page,
                                "pageSize": page_size,
                            },
                            headers={"Accept": "application/json"},
                        )
                        resp.raise_for_status()

                    return resp.json()

                except httpx.HTTPStatusError as exc:
                    last_exc = exc
                    if exc.response.status_code == 429:
                        backoff = _BACKOFF_BASE_S * (_BACKOFF_FACTOR ** attempt)
                        logger.warning(
                            "cordis_api_rate_limit",
                            attempt=attempt + 1,
                            backoff_s=backoff,
                            page=page,
                        )
                        await asyncio.sleep(backoff)
                        continue
                    # Andere HTTP-Fehler: nicht retrybar
                    logger.error(
                        "cordis_api_http_fehler",
                        status=exc.response.status_code,
                        page=page,
                    )
                    return None

                except (httpx.TimeoutException, httpx.ConnectError) as exc:
                    last_exc = exc
                    backoff = _BACKOFF_BASE_S * (_BACKOFF_FACTOR ** attempt)
                    logger.warning(
                        "cordis_api_verbindungsfehler",
                        attempt=attempt + 1,
                        backoff_s=backoff,
                        error=str(exc),
                        page=page,
                    )
                    await asyncio.sleep(backoff)

            logger.error(
                "cordis_api_max_retries",
                technology=technology,
                page=page,
                error=str(last_exc),
            )
            return None

    # ------------------------------------------------------------------
    # Rate-Limiting
    # ------------------------------------------------------------------

    async def _enforce_rate_limit(self) -> None:
        """Mindest-Intervall zwischen Requests einhalten (30 RPM = 2s)."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        wait = self._min_interval - elapsed
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request_time = time.monotonic()

    # ------------------------------------------------------------------
    # Response-Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_project(record: dict[str, Any]) -> dict | None:
        """Einzelnes Projekt aus der CORDIS API-Response parsen.

        Args:
            record: Rohes Projekt-Dict aus der API-Response.

        Returns:
            Normalisiertes Projekt-Dict oder None bei ungueltigem Record.
        """
        try:
            project_id = record.get("id")
            if project_id is None:
                return None

            try:
                project_id = int(project_id)
            except (ValueError, TypeError):
                return None

            return {
                "id": project_id,
                "rcn": _safe_int(record.get("rcn")),
                "framework": _detect_framework(record),
                "acronym": _safe_str(record.get("acronym"), max_len=50),
                "title": _safe_str(record.get("title"), max_len=2000) or "",
                "objective": _safe_str(record.get("objective")),
                "keywords": _safe_str(record.get("keywords")),
                "start_date": _parse_date(record.get("startDate")),
                "end_date": _parse_date(record.get("endDate")),
                "status": _safe_str(record.get("status"), max_len=20),
                "total_cost": _parse_decimal(record.get("totalCost")),
                "ec_max_contribution": _parse_decimal(
                    record.get("ecMaxContribution"),
                ),
                "funding_scheme": _safe_str(
                    record.get("fundingScheme"), max_len=50,
                ),
                "topics": _safe_str(record.get("topics")),
                "legal_basis": _safe_str(record.get("legalBasis")),
                "cordis_update_date": _parse_date(
                    record.get("contentUpdateDate"),
                ),
            }
        except Exception as exc:
            logger.warning("cordis_api_parse_fehler", error=str(exc))
            return None

    # ------------------------------------------------------------------
    # Cache-Operationen
    # ------------------------------------------------------------------

    async def _read_cache(
        self,
        technology: str,
        *,
        allow_stale: bool = False,
    ) -> list[dict] | None:
        """Cache-Eintrag fuer eine Technologie lesen.

        Args:
            technology: Suchbegriff (Cache-Key).
            allow_stale: Auch abgelaufene Eintraege zurueckgeben.

        Returns:
            Liste von Projekt-Dicts oder None bei Cache-Miss.
        """
        if self._pool is None:
            return None

        try:
            async with self._pool.acquire() as conn:
                if allow_stale:
                    sql = (
                        "SELECT result_json "
                        "FROM cordis_schema.cordis_api_cache "
                        "WHERE technology = $1"
                    )
                else:
                    sql = (
                        "SELECT result_json "
                        "FROM cordis_schema.cordis_api_cache "
                        "WHERE technology = $1 "
                        "AND stale_after > NOW()"
                    )
                row = await conn.fetchrow(sql, technology)

            if row is None:
                return None

            result_json = row["result_json"]
            # asyncpg liefert JSONB als Python-Objekt (list/dict) zurueck
            if isinstance(result_json, str):
                return json.loads(result_json)
            return result_json

        except Exception as exc:
            logger.warning("cordis_cache_read_fehler", error=str(exc))
            return None

    async def _write_cache(
        self,
        technology: str,
        projects: list[dict],
    ) -> None:
        """Suchergebnis in den Cache schreiben (Upsert).

        Args:
            technology: Suchbegriff (Cache-Key).
            projects: Liste von Projekt-Dicts.
        """
        if self._pool is None:
            return

        try:
            # Daten fuer JSONB serialisieren (date/Decimal nicht JSON-faehig)
            serializable = json.dumps(
                projects, default=str, ensure_ascii=False,
            )

            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO cordis_schema.cordis_api_cache
                        (technology, result_json, fetched_at, stale_after)
                    VALUES ($1, $2::jsonb, NOW(), NOW() + INTERVAL '%d days')
                    ON CONFLICT (technology) DO UPDATE SET
                        result_json = EXCLUDED.result_json,
                        fetched_at = NOW(),
                        stale_after = NOW() + INTERVAL '%d days'
                    """ % (_CACHE_TTL_DAYS, _CACHE_TTL_DAYS),
                    technology,
                    serializable,
                )
        except Exception as exc:
            logger.warning("cordis_cache_write_fehler", error=str(exc))

    # ------------------------------------------------------------------
    # Upsert in cordis_schema.projects (API > Bulk)
    # ------------------------------------------------------------------

    async def _upsert_projects(self, projects: list[dict]) -> None:
        """Projekte per Upsert in cordis_schema.projects schreiben.

        Wichtig: ON CONFLICT (id) DO UPDATE SET — API-Daten sind aktueller
        als Bulk-Imports und ueberschreiben diese daher bewusst.

        Args:
            projects: Liste von normalisierten Projekt-Dicts.
        """
        if self._pool is None:
            return

        valid = [p for p in projects if p.get("id") is not None]
        if not valid:
            return

        try:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO cordis_schema.projects (
                        id, rcn, framework, acronym, title, objective,
                        keywords, start_date, end_date, status,
                        total_cost, ec_max_contribution, funding_scheme,
                        topics, legal_basis, cordis_update_date
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6,
                        $7, $8, $9, $10,
                        $11, $12, $13,
                        $14, $15, $16
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        rcn = EXCLUDED.rcn,
                        framework = EXCLUDED.framework,
                        acronym = EXCLUDED.acronym,
                        title = EXCLUDED.title,
                        objective = EXCLUDED.objective,
                        keywords = EXCLUDED.keywords,
                        start_date = EXCLUDED.start_date,
                        end_date = EXCLUDED.end_date,
                        status = EXCLUDED.status,
                        total_cost = EXCLUDED.total_cost,
                        ec_max_contribution = EXCLUDED.ec_max_contribution,
                        funding_scheme = EXCLUDED.funding_scheme,
                        topics = EXCLUDED.topics,
                        legal_basis = EXCLUDED.legal_basis,
                        cordis_update_date = EXCLUDED.cordis_update_date
                    """,
                    [
                        (
                            p["id"],
                            p.get("rcn"),
                            p.get("framework", "UNKNOWN"),
                            p.get("acronym"),
                            p.get("title", ""),
                            p.get("objective"),
                            p.get("keywords"),
                            p.get("start_date"),
                            p.get("end_date"),
                            p.get("status"),
                            p.get("total_cost"),
                            p.get("ec_max_contribution"),
                            p.get("funding_scheme"),
                            p.get("topics"),
                            p.get("legal_basis"),
                            p.get("cordis_update_date"),
                        )
                        for p in valid
                    ],
                )

            logger.info("cordis_api_upsert_erfolg", count=len(valid))

        except Exception as exc:
            logger.error(
                "cordis_api_upsert_fehler",
                count=len(valid),
                error=str(exc),
            )
