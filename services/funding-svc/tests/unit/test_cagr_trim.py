"""Unit-Tests fuer den CAGR-Trim im funding-svc (Bug C-005).

Bug: funding-svc hat das laufende (unvollstaendige) Kalenderjahr in die
CAGR-Berechnung einbezogen, landscape-svc nicht. Bei identischer Rohgroesse
konnte das Endglied das Vorzeichen kippen (mRNA: -11.7% vs. +0.01%).

Kanonisch: Beide Services nutzen ``last_complete_year()`` als Endpunkt.
Die Analyse laeuft ueber ``analysis_period=2016-2026``, fuer CAGR wird 2026
(laufendes Jahr) ausgeschlossen.

Diese Tests ueberpruefen, dass der funding-svc:
1. time_series auf ``year <= data_complete_year`` filtert, bevor CAGR laeuft;
2. bei vollstaendigen Daten die gesamte Range benutzt;
3. ``cagr_period_end`` in der Response liefert.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import MagicMock

import pytest

from shared.domain.metrics import cagr
from shared.domain.result_types import FundingYear
from shared.domain.year_completeness import last_complete_year

from src import service as service_module
from src.service import FundingServicer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _force_dict_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Setzt Protobuf-Module auf None, damit Servicer dict-Response liefert."""
    monkeypatch.setattr(service_module, "uc4_funding_pb2", None)
    monkeypatch.setattr(service_module, "common_pb2", None)
    monkeypatch.setattr(service_module, "uc4_funding_pb2_grpc", None)


@pytest.fixture
def servicer() -> FundingServicer:
    """FundingServicer mit Mock-Pool (DB wird nicht beruehrt)."""
    return FundingServicer(pool=MagicMock())


class _FakeTimeRange:
    def __init__(self, start_year: int, end_year: int) -> None:
        self.start_year = start_year
        self.end_year = end_year


class _FakeRequest:
    def __init__(self, technology: str, start: int, end: int, request_id: str = "t") -> None:
        self.technology = technology
        self.request_id = request_id
        self.time_range = _FakeTimeRange(start, end)
        self.top_n = 5


# ---------------------------------------------------------------------------
# Repository-Patch: liefert deterministische Zeitreihen
# ---------------------------------------------------------------------------

def _patch_repo(
    servicer: FundingServicer,
    funding_years: list[FundingYear],
) -> None:
    """Ersetzt die Repository-Methoden durch Fakes.

    Nur ``funding_by_year`` liefert die Testdaten; die uebrigen Abfragen
    sind fuer den CAGR-Test irrelevant und liefern leere Listen bzw. 0.
    """
    async def _years(*_a: Any, **_kw: Any) -> list[FundingYear]:
        return funding_years

    async def _programme(*_a: Any, **_kw: Any) -> list[dict[str, Any]]:
        return []

    async def _instrument(*_a: Any, **_kw: Any) -> list[dict[str, Any]]:
        return []

    async def _orgs(*_a: Any, **_kw: Any) -> list[dict[str, Any]]:
        return []

    async def _country(*_a: Any, **_kw: Any) -> list[dict[str, Any]]:
        return []

    async def _avg_duration(*_a: Any, **_kw: Any) -> float:
        return 0.0

    servicer._repo.funding_by_year = _years  # type: ignore[method-assign]
    servicer._repo.funding_by_programme = _programme  # type: ignore[method-assign]
    servicer._repo.funding_by_instrument = _instrument  # type: ignore[method-assign]
    servicer._repo.top_funded_organizations = _orgs  # type: ignore[method-assign]
    servicer._repo.funding_by_country = _country  # type: ignore[method-assign]
    servicer._repo.avg_project_duration = _avg_duration  # type: ignore[method-assign]


# ---------------------------------------------------------------------------
# Tests: CAGR-Trim des laufenden Jahres
# ---------------------------------------------------------------------------

class TestCagrTrimsIncompleteYear:
    """CAGR darf das laufende (unvollstaendige) Jahr nicht einbeziehen."""

    async def test_cagr_uses_complete_years_only(
        self,
        servicer: FundingServicer,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Mit time_series 2016-2026 und 2026 unvollstaendig → CAGR nur 2016-2025."""
        # Fixiere "heute" auf 2026-04-17 -> last_complete_year() == 2025.
        monkeypatch.setattr(
            service_module,
            "last_complete_year",
            lambda: last_complete_year(today=date(2026, 4, 17)),
        )

        # 2016 -> 1.0M, stetiges Wachstum bis 2025 -> 2.0M, 2026 ein Teiljahr
        # mit stark reduzierter Foerderung, das den CAGR sonst kippen wuerde.
        years = [
            FundingYear(year=2016, funding=1_000_000.0, count=10),
            FundingYear(year=2017, funding=1_100_000.0, count=11),
            FundingYear(year=2018, funding=1_200_000.0, count=12),
            FundingYear(year=2019, funding=1_300_000.0, count=13),
            FundingYear(year=2020, funding=1_400_000.0, count=14),
            FundingYear(year=2021, funding=1_500_000.0, count=15),
            FundingYear(year=2022, funding=1_600_000.0, count=16),
            FundingYear(year=2023, funding=1_700_000.0, count=17),
            FundingYear(year=2024, funding=1_800_000.0, count=18),
            FundingYear(year=2025, funding=2_000_000.0, count=20),
            FundingYear(year=2026, funding=200_000.0, count=2),  # Teiljahr
        ]
        _patch_repo(servicer, years)

        response = await servicer.AnalyzeFunding(
            _FakeRequest("mRNA", 2016, 2026), context=None,
        )

        # Erwartung: CAGR nur ueber 2016-2025 (9 Jahre, 1.0M -> 2.0M).
        expected_percent = cagr(1_000_000.0, 2_000_000.0, 9)
        # Response.cagr ist Fraktion (percent/100).
        assert response["cagr"] == pytest.approx(
            expected_percent / 100.0, abs=1e-6,
        )
        assert response["cagr_period_end"] == 2025
        # Das Endjahr fuer CAGR ist strikt positiv, nicht negativ (Bug C-005).
        assert response["cagr"] > 0

    async def test_full_range_when_last_year_is_complete(
        self,
        servicer: FundingServicer,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Wenn 2026 bereits vollstaendig → ganze Range wird genutzt."""
        # Fixiere "heute" auf 2027-01-01 -> last_complete_year() == 2026.
        monkeypatch.setattr(
            service_module,
            "last_complete_year",
            lambda: last_complete_year(today=date(2027, 1, 1)),
        )

        years = [
            FundingYear(year=2016, funding=1_000_000.0, count=10),
            FundingYear(year=2021, funding=1_500_000.0, count=15),
            FundingYear(year=2026, funding=2_500_000.0, count=25),
        ]
        _patch_repo(servicer, years)

        response = await servicer.AnalyzeFunding(
            _FakeRequest("mRNA", 2016, 2026), context=None,
        )

        # Erwartung: CAGR ueber 2016-2026 (10 Jahre, 1.0M -> 2.5M).
        expected_percent = cagr(1_000_000.0, 2_500_000.0, 10)
        assert response["cagr"] == pytest.approx(
            expected_percent / 100.0, abs=1e-6,
        )
        assert response["cagr_period_end"] == 2026

    async def test_missing_last_year_uses_available_data(
        self,
        servicer: FundingServicer,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Wenn 2026 in den Daten fehlt → Range endet bei letztem verfuegbaren Jahr."""
        monkeypatch.setattr(
            service_module,
            "last_complete_year",
            lambda: last_complete_year(today=date(2026, 4, 17)),
        )

        # Keine 2026-Eintraege vorhanden, 2025 ist das letzte Jahr.
        years = [
            FundingYear(year=2016, funding=1_000_000.0, count=10),
            FundingYear(year=2020, funding=1_500_000.0, count=15),
            FundingYear(year=2025, funding=2_000_000.0, count=20),
        ]
        _patch_repo(servicer, years)

        response = await servicer.AnalyzeFunding(
            _FakeRequest("mRNA", 2016, 2026), context=None,
        )

        expected_percent = cagr(1_000_000.0, 2_000_000.0, 9)
        assert response["cagr"] == pytest.approx(
            expected_percent / 100.0, abs=1e-6,
        )
        assert response["cagr_period_end"] == 2025

    async def test_cagr_period_end_in_metadata(
        self,
        servicer: FundingServicer,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``cagr_period_end`` wird auch in der Metadata mitgeliefert."""
        monkeypatch.setattr(
            service_module,
            "last_complete_year",
            lambda: last_complete_year(today=date(2026, 4, 17)),
        )

        years = [
            FundingYear(year=2020, funding=1_000_000.0, count=5),
            FundingYear(year=2025, funding=2_000_000.0, count=10),
        ]
        _patch_repo(servicer, years)

        response = await servicer.AnalyzeFunding(
            _FakeRequest("mRNA", 2016, 2026), context=None,
        )

        assert "cagr_period_end" in response
        assert response["metadata"]["cagr_period_end"] == 2025


# ---------------------------------------------------------------------------
# Tests: Symmetrie mit landscape-svc
# ---------------------------------------------------------------------------

class TestCagrSymmetryWithLandscape:
    """Gleiche Rohgroesse -> gleiches Vorzeichen in funding und landscape."""

    async def test_sign_stable_between_services(
        self,
        servicer: FundingServicer,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Ohne Teiljahr-Trim wuerde das Vorzeichen kippen (Bug C-005)."""
        monkeypatch.setattr(
            service_module,
            "last_complete_year",
            lambda: last_complete_year(today=date(2026, 4, 17)),
        )

        # mRNA-aehnliches Szenario: stetiges Wachstum, 2026 stark unterzeichnet.
        years = [
            FundingYear(year=2016, funding=500_000.0, count=5),
            FundingYear(year=2025, funding=1_500_000.0, count=15),
            FundingYear(year=2026, funding=10_000.0, count=1),
        ]
        _patch_repo(servicer, years)

        response = await servicer.AnalyzeFunding(
            _FakeRequest("mRNA", 2016, 2026), context=None,
        )

        # Vorzeichen muss positiv sein — ohne Trim waere es stark negativ.
        assert response["cagr"] > 0
        assert response["cagr_period_end"] == 2025
