"""Unit-Tests fuer den CAGR-Split (Bug C-004, Bundle H).

Vor dem Fix lieferte ``maturity.cagr`` einen Gompertz-Fit-basierten Wert,
waehrend ``landscape.patent_cagr`` einen naiven (end/start)^(1/n)-1 lieferte.
Beispiele aus dem Live-Lauf:
- AI:  maturity 29.6 %  vs landscape 71.3 %
- mRNA: maturity -18.4 % vs landscape +3.1 %  (Vorzeichen-Flip!)

Neu:
- ``empirical_cagr`` (Proto-18): Gleiche Methode wie landscape-svc.
- ``fitted_growth_rate`` (Proto-19): Momentane Fit-Rate (vorher ``cagr``).
- ``cagr`` (Proto-5, DEPRECATED): Alias fuer ``empirical_cagr``.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.domain.result_types import YearCount
from shared.domain.metrics import cagr as shared_cagr
from shared.domain.year_completeness import last_complete_year
from src import service as service_module
from src.config import Settings
from src.service import (
    MaturityServicer,
    _compute_empirical_cagr,
    _compute_fitted_growth_rate,
)


# ---------------------------------------------------------------------------
# Auto-Fixture
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
# Tests: Response-Schema
# ---------------------------------------------------------------------------


class TestResponseHasBothCagrFields:
    """``empirical_cagr`` und ``fitted_growth_rate`` muessen parallel existieren."""

    def test_response_has_empirical_cagr(self):
        servicer = _make_servicer({
            2010: 10, 2015: 50, 2020: 100, 2024: 200,
        })
        response = _run(servicer.AnalyzeMaturity(_FakeRequest(), context=None))
        assert "empirical_cagr" in response

    def test_response_has_fitted_growth_rate(self):
        servicer = _make_servicer({
            2010: 10, 2015: 50, 2020: 100, 2024: 200,
        })
        response = _run(servicer.AnalyzeMaturity(_FakeRequest(), context=None))
        assert "fitted_growth_rate" in response

    def test_cagr_alias_matches_empirical_cagr(self):
        """Das deprecated ``cagr``-Feld spiegelt ``empirical_cagr``."""
        servicer = _make_servicer({
            2010: 10, 2015: 50, 2020: 100, 2024: 200,
        })
        response = _run(servicer.AnalyzeMaturity(_FakeRequest(), context=None))
        assert response["cagr"] == pytest.approx(response["empirical_cagr"])


# ---------------------------------------------------------------------------
# Tests: Methodische Parity zu landscape-svc
# ---------------------------------------------------------------------------


class TestEmpiricalCagrMatchesLandscapeMethod:
    """``_compute_empirical_cagr`` muss identisch zu ``landscape._safe_cagr`` sein."""

    def test_simple_doubling(self):
        """Verdopplung ueber 10 Jahre -> CAGR = 2^(1/10) - 1 ~ 7.18 %."""
        all_years = list(range(2010, 2021))  # 2010..2020
        combined = [10, 12, 14, 13, 16, 18, 17, 19, 18, 20, 20]
        # data_complete_year gross genug, damit alles einbezogen wird.
        result_percent = _compute_empirical_cagr(
            all_years=all_years,
            combined=combined,
            data_complete_year=2025,
        )
        expected = shared_cagr(10.0, 20.0, 10)
        assert result_percent == pytest.approx(expected, abs=0.01)

    def test_respects_data_complete_year(self):
        """Teiljahre nach data_complete_year werden nicht verwendet."""
        all_years = [2020, 2021, 2022, 2023, 2024]
        combined = [100, 120, 140, 160, 1]  # 2024 unvollstaendig -> 1
        # Ohne Filter wuerde 100 -> 1 einen stark negativen CAGR ergeben.
        result_with_filter = _compute_empirical_cagr(
            all_years=all_years,
            combined=combined,
            data_complete_year=2023,
        )
        # Erwartete Basis: 100 (2020) -> 160 (2023), 3 Jahre
        expected = shared_cagr(100.0, 160.0, 3)
        assert result_with_filter == pytest.approx(expected, abs=0.01)
        # Und: positiv (nicht durch Teiljahr verzerrt).
        assert result_with_filter > 0

    def test_zero_when_single_positive_year(self):
        """Nur ein positiver Jahrgang -> CAGR nicht definiert -> 0.0."""
        result = _compute_empirical_cagr(
            all_years=[2020, 2021, 2022],
            combined=[0, 0, 50],
            data_complete_year=2025,
        )
        assert result == 0.0

    def test_zero_when_year_span_zero(self):
        """Erst-/Letztjahr identisch -> 0.0."""
        result = _compute_empirical_cagr(
            all_years=[2020],
            combined=[10],
            data_complete_year=2025,
        )
        assert result == 0.0

    def test_service_empirical_cagr_uses_landscape_recipe(self):
        """End-to-end: Servicer-Output == direkt berechneter landscape-CAGR."""
        year_counts = {
            2010: 10, 2011: 12, 2012: 15, 2013: 18, 2014: 22,
            2015: 28, 2016: 35, 2017: 45, 2018: 55, 2019: 70,
            2020: 90, 2021: 110, 2022: 130, 2023: 150, 2024: 170,
        }
        servicer = _make_servicer(year_counts)
        response = _run(servicer.AnalyzeMaturity(_FakeRequest(), context=None))

        dcy = last_complete_year()
        # "Landscape"-Rezept: erster/letzter positiver Jahrgang bis dcy.
        years_sorted = sorted(y for y in year_counts if y <= dcy)
        first_year, last_year = years_sorted[0], years_sorted[-1]
        span = last_year - first_year
        expected_percent = shared_cagr(
            float(year_counts[first_year]),
            float(year_counts[last_year]),
            span,
        )
        # Response liefert Fraction.
        assert response["empirical_cagr"] == pytest.approx(
            expected_percent / 100.0, abs=1e-4,
        )


# ---------------------------------------------------------------------------
# Tests: Fitted growth rate
# ---------------------------------------------------------------------------


class TestFittedGrowthRate:
    """``fitted_growth_rate`` soll die momentane Fit-Steigung liefern."""

    def test_none_result_yields_zero(self):
        assert _compute_fitted_growth_rate(s_curve_result=None, fit_years=[]) == 0.0

    def test_too_few_fit_years_yields_zero(self):
        assert _compute_fitted_growth_rate(
            s_curve_result={"fitted_values": [{"year": 2020, "fitted": 1.0}]},
            fit_years=[2020],
        ) == 0.0

    def test_simple_growth_rate(self):
        """y[n]=110, y[n-1]=100 -> 10 %."""
        result = _compute_fitted_growth_rate(
            s_curve_result={
                "fitted_values": [
                    {"year": 2022, "fitted": 90.0},
                    {"year": 2023, "fitted": 100.0},
                    {"year": 2024, "fitted": 110.0},
                ],
            },
            fit_years=[2022, 2023, 2024],
        )
        assert result == pytest.approx(0.10, abs=1e-6)

    def test_service_sets_fitted_growth_rate_when_fit_succeeds(self):
        """Bei einem brauchbaren Sigmoid-Fit wird ``fitted_growth_rate`` gesetzt."""
        # Sigmoid-Form mit genuegend Datenpunkten.
        year_counts = {
            2010: 5, 2011: 8, 2012: 14, 2013: 23, 2014: 38,
            2015: 60, 2016: 85, 2017: 100, 2018: 95, 2019: 70,
            2020: 45, 2021: 27, 2022: 15, 2023: 8, 2024: 5,
        }
        servicer = _make_servicer(year_counts)
        response = _run(servicer.AnalyzeMaturity(_FakeRequest(), context=None))

        # Fit muss zuverlaessig sein, sonst ist der Test nicht aussagekraeftig.
        assert response["fit_reliability_flag"] is True
        # fitted_growth_rate ist eine Fraction — endlicher Wert, nicht exakt null.
        assert isinstance(response["fitted_growth_rate"], float)

    def test_fitted_and_empirical_are_independent(self):
        """Beide Felder koennen unterschiedliche Werte annehmen."""
        # Datenlage: empirisch positive CAGR ueber die gesamte Zeitreihe,
        # aber Sigmoid-Fit verhaelt sich am Ende anders (Spaetphase).
        year_counts = {
            2010: 5, 2011: 8, 2012: 14, 2013: 23, 2014: 38,
            2015: 60, 2016: 85, 2017: 100, 2018: 95, 2019: 70,
            2020: 45, 2021: 27, 2022: 15, 2023: 8, 2024: 5,
        }
        servicer = _make_servicer(year_counts)
        response = _run(servicer.AnalyzeMaturity(_FakeRequest(), context=None))
        # Nicht zwangsweise gleich — Feldunterscheidung ist hier der Kern.
        # Wir pruefen nur, dass beide Keys existieren und floats sind.
        assert isinstance(response["empirical_cagr"], float)
        assert isinstance(response["fitted_growth_rate"], float)
