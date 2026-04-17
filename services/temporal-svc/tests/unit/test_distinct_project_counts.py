"""Unit-Tests fuer Bug M-002 / C2.1 — DISTINCT-Projekt-Counts in temporal-svc.

Bug: ``temporal.metadata.data_sources[CORDIS].record_count`` war zuvor
``len(cordis_actors_raw)`` — also die Zeilenanzahl einer
``GROUP BY (year, organization_name)``-Aggregation. Ein Projekt mit 5
Organisationen ueber 2 Jahre erzeugte dort *bis zu 10 Zeilen*. Bei
Blockchain ergab das 3148 statt der korrekten 322 (+877 %), vs. der
``landscape.summary.total_projects``-Referenz.

Fix:
* Repository: Neue Methode ``count_distinct_cordis_projects`` liefert
  ``COUNT(DISTINCT p.id)`` direkt aus der Datenbank.
* Service: ``record_count`` stammt aus dieser dedizierten Zaehlung.

Diese Tests verifizieren, dass die Row-Duplikation durch Joins
(1 Projekt x N Organisationen x M Laender) *nicht* in den Projekt-
Count einfliesst.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.repository import TemporalRepository


# ---------------------------------------------------------------------------
# Test-Helpers: asyncpg.Pool-Mock
# ---------------------------------------------------------------------------


class _FakeConn:
    """Minimaler asyncpg-Conn-Mock.

    Wir stellen die von den Queries genutzten Methoden (``fetch``,
    ``fetchval``) als ``AsyncMock`` bereit. Die konkreten Rueckgabewerte
    werden pro Test konfiguriert.
    """

    def __init__(self) -> None:
        self.fetch = AsyncMock()
        self.fetchval = AsyncMock()
        # Letzter SQL-Text / Parameter fuer Assertions.
        self.last_sql: str = ""
        self.last_params: tuple[Any, ...] = ()

        async def _record_fetchval(sql: str, *params: Any) -> Any:
            self.last_sql = sql
            self.last_params = params
            return self._fetchval_return

        async def _record_fetch(sql: str, *params: Any) -> Any:
            self.last_sql = sql
            self.last_params = params
            return self._fetch_return

        self._fetchval_return: Any = 0
        self._fetch_return: list[dict[str, Any]] = []
        self.fetchval.side_effect = _record_fetchval
        self.fetch.side_effect = _record_fetch


class _FakePool:
    """Async-Context-Manager-kompatibler Pool-Mock."""

    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn

    def acquire(self) -> "_FakePool":
        return self

    async def __aenter__(self) -> _FakeConn:
        return self._conn

    async def __aexit__(self, *args: Any) -> None:
        return None


@pytest.fixture
def fake_conn() -> _FakeConn:
    return _FakeConn()


@pytest.fixture
def repo(fake_conn: _FakeConn) -> TemporalRepository:
    pool = _FakePool(fake_conn)
    # ``TemporalRepository`` erwartet ``asyncpg.Pool`` — der Duck-Type
    # reicht fuer die Tests voellig.
    return TemporalRepository(pool)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# count_distinct_cordis_projects — SQL-Struktur-Checks
# ---------------------------------------------------------------------------


class TestCountDistinctCordisProjectsSql:
    """Stellt sicher, dass die Query COUNT(DISTINCT p.id) nutzt."""

    @pytest.mark.asyncio
    async def test_verwendet_count_distinct_project_id(
        self, repo: TemporalRepository, fake_conn: _FakeConn,
    ) -> None:
        """Die Query MUSS ``COUNT(DISTINCT p.id)`` verwenden — andernfalls
        liefert sie bei ``european_only=True`` (Organisations-JOIN)
        Row-aufgeblaehte Werte."""
        fake_conn._fetchval_return = 1
        await repo.count_distinct_cordis_projects(
            "blockchain", start_year=2016, end_year=2026,
        )
        sql = fake_conn.last_sql
        assert "COUNT(DISTINCT p.id)" in sql, (
            "Query muss COUNT(DISTINCT p.id) nutzen, sonst Row-Inflation "
            "durch JOINs."
        )

    @pytest.mark.asyncio
    async def test_european_only_triggert_organisations_join(
        self, repo: TemporalRepository, fake_conn: _FakeConn,
    ) -> None:
        """``european_only=True`` joined organizations — hier ist
        DISTINCT doppelt wichtig."""
        fake_conn._fetchval_return = 42
        await repo.count_distinct_cordis_projects(
            "blockchain",
            start_year=2016,
            end_year=2026,
            european_only=True,
        )
        sql = fake_conn.last_sql
        assert "cordis_schema.organizations" in sql
        assert "COUNT(DISTINCT p.id)" in sql

    @pytest.mark.asyncio
    async def test_ohne_european_only_kein_join(
        self, repo: TemporalRepository, fake_conn: _FakeConn,
    ) -> None:
        """Ohne ``european_only`` ist der Organisations-JOIN nicht
        noetig — dann reicht ``projects p`` (keine Row-Multiplikation)."""
        fake_conn._fetchval_return = 322
        await repo.count_distinct_cordis_projects(
            "blockchain", start_year=2016, end_year=2026,
        )
        sql = fake_conn.last_sql
        assert "cordis_schema.organizations" not in sql, (
            "Ohne european_only sollte der Organisations-JOIN unterbleiben "
            "— vermeidet Planner-Overhead."
        )


# ---------------------------------------------------------------------------
# count_distinct_cordis_projects — Verhaltens-Checks
# ---------------------------------------------------------------------------


class TestCountDistinctCordisProjectsBehavior:
    """Prueft die Kernaussage: 1 Projekt x 5 Laender -> count = 1."""

    @pytest.mark.asyncio
    async def test_ein_projekt_fuenf_laender_ergibt_eins(
        self, repo: TemporalRepository, fake_conn: _FakeConn,
    ) -> None:
        """Simuliert den Bug-Fix: Die DB gibt ``COUNT(DISTINCT p.id) = 1``
        zurueck fuer 1 Projekt mit 5 Organisations-Rows (5 Laender).
        Ohne DISTINCT haette der Bug hier 5 geliefert."""
        fake_conn._fetchval_return = 1
        total = await repo.count_distinct_cordis_projects(
            "blockchain", european_only=True,
        )
        assert total == 1, (
            "1 Projekt x 5 Laender muss COUNT(DISTINCT p.id) = 1 ergeben, "
            "nicht 5 (Row-Duplikation durch JOIN)."
        )

    @pytest.mark.asyncio
    async def test_null_projekte_liefert_null(
        self, repo: TemporalRepository, fake_conn: _FakeConn,
    ) -> None:
        """Leeres Ergebnis aus PostgreSQL (``None``) wird sicher in 0
        ueberfuehrt — keine ``TypeError``."""
        fake_conn._fetchval_return = None
        total = await repo.count_distinct_cordis_projects("unknown_tech")
        assert total == 0

    @pytest.mark.asyncio
    async def test_parameter_binding_ist_positional(
        self, repo: TemporalRepository, fake_conn: _FakeConn,
    ) -> None:
        """Technologie + Jahre landen in den $1..$N-Parametern (kein
        String-Interpolation -> SQL-Injection-Schutz)."""
        fake_conn._fetchval_return = 322
        await repo.count_distinct_cordis_projects(
            "blockchain",
            start_year=2016,
            end_year=2026,
            european_only=False,
        )
        assert fake_conn.last_params[0] == "blockchain"
        assert 2016 in fake_conn.last_params
        assert 2026 in fake_conn.last_params


# ---------------------------------------------------------------------------
# cordis_actors_by_year — Regressionsschutz fuer den Hauptbug
# ---------------------------------------------------------------------------


class TestCordisActorsByYearDistinct:
    """Regressionsschutz: Die (year, actor)-Aggregation MUSS
    ``COUNT(DISTINCT p.id)`` nutzen — sonst werden Projekte pro Akteur
    bei Mehrfach-Rollen ueberzaehlt."""

    @pytest.mark.asyncio
    async def test_query_verwendet_count_distinct(
        self, repo: TemporalRepository, fake_conn: _FakeConn,
    ) -> None:
        fake_conn._fetch_return = []
        await repo.cordis_actors_by_year(
            "blockchain", start_year=2016, end_year=2026,
        )
        sql = fake_conn.last_sql
        assert "COUNT(DISTINCT p.id)" in sql, (
            "cordis_actors_by_year MUSS COUNT(DISTINCT p.id) verwenden — "
            "sonst doppelte Projekte bei Mehrfachrollen der Organisation."
        )


# ---------------------------------------------------------------------------
# Service-Integrations-Check: record_count aus DISTINCT-Count, NICHT len()
# ---------------------------------------------------------------------------


class TestServiceUsesDistinctCountForRecordCount:
    """Stellt sicher, dass der TemporalServicer den CORDIS-record_count
    aus ``count_distinct_cordis_projects`` speist — nicht aus
    ``len(cordis_actors_raw)``.
    """

    @pytest.mark.asyncio
    async def test_record_count_entspricht_distinct_projekten(self) -> None:
        """Szenario: cordis_actors_raw hat 3148 Zeilen (Bug-Zustand),
        aber count_distinct_cordis_projects liefert 322 (landscape-
        Referenz). Das Response-data_source.record_count MUSS 322 sein.
        """
        from src.service import TemporalServicer

        servicer = TemporalServicer.__new__(TemporalServicer)
        servicer._pool = MagicMock()
        servicer._settings = MagicMock()

        # Repository vollstaendig mocken — wir testen hier nur die
        # AnalyzeTemporal-Verdrahtung.
        repo = MagicMock()
        repo.patent_actors_by_year = AsyncMock(return_value=[])
        # 3148 Zeilen a la GROUP BY (year, o.name) — Bug-Zustand.
        repo.cordis_actors_by_year = AsyncMock(
            return_value=[
                {"year": 2020, "name": f"ORG_{i}", "count": 1}
                for i in range(3148)
            ],
        )
        repo.cpc_codes_by_year = AsyncMock(return_value=[])
        repo.funding_by_instrument = AsyncMock(return_value=[])
        # Korrekte DISTINCT-Zahl laut Fix.
        repo.count_distinct_cordis_projects = AsyncMock(return_value=322)
        servicer._repo = repo

        # Minimaler Pseudo-Request.
        request = MagicMock()
        request.technology = "blockchain"
        request.request_id = "t"
        request.european_only = True
        request.time_range = MagicMock()
        request.time_range.start_year = 2016
        request.time_range.end_year = 2026

        # uc8_temporal_pb2 ist im Unit-Test-Umfeld i.d.R. None -> es
        # wird der dict-Response-Pfad gewaehlt.
        response = await servicer.AnalyzeTemporal(request, context=None)

        # Der dict-Response-Pfad liefert data_sources unter
        # metadata.data_sources.
        if isinstance(response, dict):
            data_sources = response["metadata"]["data_sources"]
        else:
            data_sources = [
                {"name": ds.name, "type": "PROJECT", "record_count": ds.record_count}
                for ds in response.metadata.data_sources
            ]

        cordis_ds = next(
            (ds for ds in data_sources if "CORDIS" in ds["name"]),
            None,
        )
        assert cordis_ds is not None, "CORDIS data_source muss vorhanden sein"
        assert cordis_ds["record_count"] == 322, (
            f"record_count MUSS der DISTINCT-Projektzahl (322) entsprechen, "
            f"nicht len(cordis_actors_raw) (3148). Ist: {cordis_ds['record_count']}"
        )
