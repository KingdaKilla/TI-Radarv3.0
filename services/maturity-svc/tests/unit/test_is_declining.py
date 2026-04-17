"""Unit-Tests fuer die neue is_declining-Logik (Bug A-002 / B-9, Bundle H).

Vorher: ``is_declining`` war nur True, wenn ``maturity_pct >= 90`` UND
``detect_decline(combined)`` gleichzeitig zutrafen. Das fuehrte zu
falsch-negativen Labels fuer mRNA (cagr=-18.4 %, maturity=39 %) und
CRISPR (cagr=-22 %, maturity=41 %).

Neu: ODER-Verknuepfung aus (a) negativem empirischen CAGR und (b) dem
klassischen Plateau-Kriterium. Dazu wird Phase-Konsistenz geprueft:
``is_declining=True`` muss in ``phase=Decline`` resultieren.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.domain.result_types import YearCount
from src import service as service_module
from src.config import Settings
from src.service import MaturityServicer, determine_is_declining


# ---------------------------------------------------------------------------
# Auto-Fixture: dict-Response (umgeht gRPC-Protobuf-Pfad)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _force_dict_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service_module, "uc2_maturity_pb2", None)
    monkeypatch.setattr(service_module, "common_pb2", None)


# ---------------------------------------------------------------------------
# Test-Helfer
# ---------------------------------------------------------------------------


class _FakeRange:
    def __init__(self, start: int, end: int) -> None:
        self.start_year = start
        self.end_year = end


class _FakeRequest:
    def __init__(
        self,
        technology: str = "test-tech",
        start_year: int = 2010,
        end_year: int = 2024,
        request_id: str = "req-1",
    ) -> None:
        self.technology = technology
        self.request_id = request_id
        self.time_range = _FakeRange(start_year, end_year)


def _make_servicer(year_counts: dict[int, int]) -> MaturityServicer:
    pool = MagicMock()
    settings = Settings()
    servicer = MaturityServicer(pool=pool, settings=settings)
    rows = [YearCount(year=y, count=c) for y, c in sorted(year_counts.items())]

    async def _fake(*args: Any, **kwargs: Any) -> list[YearCount]:
        return rows

    servicer._repo.count_families_by_year = AsyncMock(side_effect=_fake)  # type: ignore[method-assign]
    servicer._repo.count_patents_by_year = AsyncMock(side_effect=_fake)  # type: ignore[method-assign]
    return servicer


def _run(coro: Any) -> Any:
    return asyncio.new_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Tests: Pure Funktion ``determine_is_declining``
# ---------------------------------------------------------------------------


class TestDetermineIsDeclining:
    """Reine Logik-Tests — unabhaengig vom Servicer-Pfad."""

    def test_is_declining_true_when_cagr_negative(self):
        """Regel (a): negativer CAGR allein genuegt."""
        # mRNA-artiger Fall: maturity nur 39 %, aber cagr klar negativ.
        combined = [10, 12, 15, 18, 22, 20, 17, 14, 11, 9]
        # -18 %: genuegt, auch ohne 90 %-Plateau.
        assert determine_is_declining(
            empirical_cagr_percent=-18.0,
            maturity_pct=39.0,
            combined=combined,
        ) is True

    def test_is_declining_true_for_crispr_like_case(self):
        """CRISPR-Live-Fall (cagr=-22 %, maturity=41 %) muss True liefern."""
        combined = [5, 10, 20, 40, 70, 50, 35, 20, 12, 8]
        assert determine_is_declining(
            empirical_cagr_percent=-22.0,
            maturity_pct=41.0,
            combined=combined,
        ) is True

    def test_is_declining_false_when_cagr_positive_and_not_plateau(self):
        """Weder negativer CAGR noch Plateau -> False."""
        combined = [10, 15, 22, 30, 40, 50, 60, 75, 90]
        assert determine_is_declining(
            empirical_cagr_percent=25.0,
            maturity_pct=45.0,
            combined=combined,
        ) is False

    def test_is_declining_respects_maturity_plateau(self):
        """Regel (b): positive CAGR + 90 %-Plateau + detect_decline -> True."""
        # Maturity >= 90, aber jaehrliche Raten fallen in den letzten 3 Jahren.
        combined = [5, 10, 20, 40, 60, 80, 100, 120, 100, 80, 60]
        # empirical_cagr > 0 (Startwert klein, Endwert moderat), aber
        # maturity_pct 95 + detect_decline => True.
        assert determine_is_declining(
            empirical_cagr_percent=5.0,
            maturity_pct=95.0,
            combined=combined,
        ) is True

    def test_is_declining_false_at_plateau_without_decline_signal(self):
        """Regel (b) inaktiv ohne konsekutive Rueckgaenge."""
        # Maturity >= 90, aber die letzten Jahre sind nicht monoton fallend.
        combined = [5, 10, 20, 40, 60, 80, 100, 120, 125, 128, 130]
        assert determine_is_declining(
            empirical_cagr_percent=10.0,
            maturity_pct=95.0,
            combined=combined,
        ) is False


# ---------------------------------------------------------------------------
# Tests: End-to-End ueber Servicer
# ---------------------------------------------------------------------------


class TestIsDecliningResponseIntegration:
    """Das Response-Feld ``is_declining`` muss die neue Logik spiegeln."""

    def test_negative_cagr_flips_phase_to_decline(self):
        """Neg. CAGR bei mittlerer Maturity -> is_declining=True, phase=Decline."""
        # Steiler Anstieg bis 2018, danach klarer Rueckgang.
        year_counts = {
            2010: 5, 2011: 10, 2012: 20, 2013: 40, 2014: 60,
            2015: 80, 2016: 100, 2017: 120, 2018: 130,
            2019: 90, 2020: 60, 2021: 30, 2022: 15, 2023: 8, 2024: 4,
        }
        servicer = _make_servicer(year_counts)
        response = _run(servicer.AnalyzeMaturity(_FakeRequest(), context=None))

        # Der empirische CAGR ueber 2010..2024 ist negativ (5 -> 4 ist Grenzfall,
        # hier aber 5 -> 4 -> cagr leicht negativ wegen Endpunktwahl).
        assert response["cagr"] < 0
        assert response["is_declining"] is True

    def test_phase_matches_is_declining(self):
        """``is_declining=True`` impliziert ``phase=Decline``."""
        year_counts = {
            2010: 5, 2011: 10, 2012: 20, 2013: 40, 2014: 60,
            2015: 80, 2016: 100, 2017: 120, 2018: 130,
            2019: 90, 2020: 60, 2021: 30, 2022: 15, 2023: 8, 2024: 4,
        }
        servicer = _make_servicer(year_counts)
        response = _run(servicer.AnalyzeMaturity(_FakeRequest(), context=None))

        if response["is_declining"]:
            assert response["phase"] == "Decline"

    def test_positive_trend_yields_is_declining_false(self):
        """Monoton steigende Reihe -> is_declining bleibt False."""
        year_counts = {y: max(1, (y - 2009) ** 2) for y in range(2010, 2025)}
        servicer = _make_servicer(year_counts)
        response = _run(servicer.AnalyzeMaturity(_FakeRequest(), context=None))

        assert response["is_declining"] is False
        assert response["phase"] != "Decline"
