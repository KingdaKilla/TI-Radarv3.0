"""Unit-Tests fuer maturity-svc Service-Fallback-Logik (Bug MAJ-9).

Stellt sicher, dass bei unzuverlaessigen Fits (kein Sigmoid-Fit moeglich
oder R² < 0.5) keine Scheinsicherheiten entstehen:

- ``confidence_level`` muss exakt 0.0 sein.
- ``phase`` muss "Unknown" sein (NICHT "Emerging").
- ``fit_reliability_flag`` muss False sein.

Strukturelle Kopplung: ``shared.domain.metrics.s_curve_confidence`` gibt
bei R² < 0.5 garantiert 0.0 zurueck. Die Fallback-Logik im Service nutzt
diese Funktion, statt rohe Heuristik-Konfidenzen direkt durchzureichen.
"""

from __future__ import annotations

import asyncio
import math
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.domain.result_types import YearCount
from src import service as service_module
from src.config import Settings
from src.service import MaturityServicer


# ---------------------------------------------------------------------------
# Auto-Fixture: Erzwinge dict-Response (umgeht gRPC-Protobuf-Pfad)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _force_dict_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Setzt Protobuf-Module auf None, damit Servicer dict-Response liefert."""
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
    """Erstellt einen Servicer mit gemocktem Repository."""
    pool = MagicMock()
    settings = Settings()
    servicer = MaturityServicer(pool=pool, settings=settings)

    rows = [YearCount(year=y, count=c) for y, c in sorted(year_counts.items())]

    async def _fake_count_families(
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = True,
    ) -> list[YearCount]:
        return rows

    async def _fake_count_patents(
        technology: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        european_only: bool = True,
    ) -> list[YearCount]:
        return rows

    servicer._repo.count_families_by_year = AsyncMock(side_effect=_fake_count_families)  # type: ignore[method-assign]
    servicer._repo.count_patents_by_year = AsyncMock(side_effect=_fake_count_patents)  # type: ignore[method-assign]

    return servicer


def _run(coro: Any) -> Any:
    return asyncio.new_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Tests: Fallback bei zu wenig Datenpunkten (kein Fit)
# ---------------------------------------------------------------------------


class TestFallbackInsufficientData:
    """Wenn zu wenig Daten fuer Fit -> Fallback-Heuristik darf KEINE
    Scheinsicherheit liefern."""

    def test_three_datapoints_returns_zero_confidence(self):
        """3 Datenpunkte (zu wenig fuer Fit) -> confidence == 0.0."""
        # Nur 3 Jahre mit Daten, gesamt unter min_patents_for_fit
        servicer = _make_servicer({2010: 1, 2011: 1, 2012: 1})
        request = _FakeRequest()
        response = _run(servicer.AnalyzeMaturity(request, context=None))

        assert response["confidence"]["confidence_level"] == 0.0

    def test_three_datapoints_returns_unknown_phase(self):
        """3 Datenpunkte (zu wenig fuer Fit) -> phase == 'Unknown'.

        Kein 'Emerging'-Fake-Label.
        """
        servicer = _make_servicer({2010: 1, 2011: 1, 2012: 1})
        request = _FakeRequest()
        response = _run(servicer.AnalyzeMaturity(request, context=None))

        assert response["phase"] == "Unknown"

    def test_three_datapoints_returns_zero_r_squared(self):
        """3 Datenpunkte -> r_squared == 0.0 (kein Fit)."""
        servicer = _make_servicer({2010: 1, 2011: 1, 2012: 1})
        request = _FakeRequest()
        response = _run(servicer.AnalyzeMaturity(request, context=None))

        assert response["r_squared"] == 0.0

    def test_three_datapoints_fit_reliability_flag_false(self):
        """3 Datenpunkte -> fit_reliability_flag == False.

        Frontend-Gate: Phase-Label nur rendern wenn flag == True.
        """
        servicer = _make_servicer({2010: 1, 2011: 1, 2012: 1})
        request = _FakeRequest()
        response = _run(servicer.AnalyzeMaturity(request, context=None))

        assert response["fit_reliability_flag"] is False


# ---------------------------------------------------------------------------
# Tests: Fallback bei keinerlei Daten
# ---------------------------------------------------------------------------


class TestFallbackNoData:
    """Wenn ueberhaupt keine Patente -> alles auf 0/Unknown."""

    def test_no_data_zero_confidence(self):
        servicer = _make_servicer({})
        request = _FakeRequest()
        response = _run(servicer.AnalyzeMaturity(request, context=None))

        assert response["confidence"]["confidence_level"] == 0.0

    def test_no_data_unknown_phase(self):
        servicer = _make_servicer({})
        request = _FakeRequest()
        response = _run(servicer.AnalyzeMaturity(request, context=None))

        assert response["phase"] == "Unknown"

    def test_no_data_fit_reliability_flag_false(self):
        servicer = _make_servicer({})
        request = _FakeRequest()
        response = _run(servicer.AnalyzeMaturity(request, context=None))

        assert response["fit_reliability_flag"] is False


# ---------------------------------------------------------------------------
# Tests: Guter Fit -> reliability_flag == True
# ---------------------------------------------------------------------------


class TestFitSuccess:
    """Mit ausreichend sigmoid-foermigen Daten muss Fit gelingen
    und zu hoher Konfidenz fuehren."""

    def test_good_sigmoid_fit_has_positive_confidence(self):
        """Sauberer Logistic-Verlauf -> confidence > 0.5, fit_reliability_flag True."""
        # Logistik-Verlauf mit L=1000, k=0.5, x0=2017
        # Annual counts (approx. derivative)
        year_counts = {
            2010: 5, 2011: 8, 2012: 14, 2013: 23, 2014: 38,
            2015: 60, 2016: 85, 2017: 100, 2018: 95, 2019: 70,
            2020: 45, 2021: 27, 2022: 15, 2023: 8, 2024: 5,
        }
        servicer = _make_servicer(year_counts)
        request = _FakeRequest()
        response = _run(servicer.AnalyzeMaturity(request, context=None))

        assert response["r_squared"] >= 0.5
        assert response["confidence"]["confidence_level"] > 0.5
        assert response["fit_reliability_flag"] is True
        # Phase muss aus dem S-Curve-Mapping kommen, nicht 'Unknown'
        assert response["phase"] in {"Emerging", "Growing", "Mature", "Saturation", "Decline"}


# ---------------------------------------------------------------------------
# Tests: Schlechter Fit (R² < 0.5) -> reliability_flag == False
# ---------------------------------------------------------------------------


class TestLowRSquared:
    """Wenn ein Fit erzeugt wird, aber R² < 0.5 -> Fit gilt als unzuverlaessig."""

    def test_low_r_squared_zero_confidence(self):
        """Stark verrauschte Daten -> r² < 0.5 -> confidence == 0.0.

        Strukturelle Kopplung via s_curve_confidence().
        """
        # Stark oszillierende Daten, die kein S-Curve-Modell erklaeren kann
        year_counts = {
            2010: 50, 2011: 5, 2012: 80, 2013: 2, 2014: 100,
            2015: 1, 2016: 90, 2017: 3, 2018: 70, 2019: 4,
            2020: 60, 2021: 1, 2022: 50, 2023: 2, 2024: 40,
        }
        servicer = _make_servicer(year_counts)
        request = _FakeRequest()
        response = _run(servicer.AnalyzeMaturity(request, context=None))

        # Bei verrauschten Daten kann der Logistic-Fit zwar laufen,
        # aber wenn r_squared < 0.5 => confidence muss 0 sein.
        if response["r_squared"] < 0.5:
            assert response["confidence"]["confidence_level"] == 0.0
            assert response["fit_reliability_flag"] is False
            assert response["phase"] == "Unknown"
        else:
            # Wenn doch ein guter Fit zustande kommt, ist Konfidenz erlaubt > 0
            assert response["fit_reliability_flag"] is True


# ---------------------------------------------------------------------------
# Tests: AP8 — data_complete_year aus shared-Helper, kein Hardcoding
# ---------------------------------------------------------------------------


class TestDataCompleteYearMaj7Maj8:
    """``data_complete_year`` MUSS aus ``last_complete_year()`` kommen.

    Vor AP8 war das Feld auf 2024 hardcoded. Heute (2026-04-14) muss es
    2025 ergeben — sonst zeigt das Frontend dauerhaft eine veraltete
    Vollstaendigkeitsgrenze.
    """

    def test_dict_response_uses_dynamic_year(self):
        from shared.domain.year_completeness import last_complete_year

        servicer = _make_servicer({2010: 5, 2015: 30, 2020: 100, 2024: 200})
        request = _FakeRequest()
        response = _run(servicer.AnalyzeMaturity(request, context=None))

        assert "data_complete_year" in response
        assert response["data_complete_year"] == last_complete_year()

    def test_data_complete_year_at_least_2025_for_2026(self):
        """Heute (Stand 2026-04-14) muss data_complete_year mindestens 2025 sein."""
        servicer = _make_servicer({2020: 100, 2024: 200})
        request = _FakeRequest()
        response = _run(servicer.AnalyzeMaturity(request, context=None))

        # Niemals < 2025, solange wir nach dem 1.1.2026 sind.
        assert response["data_complete_year"] >= 2025


# ---------------------------------------------------------------------------
# Tests: Overfitting-Warnung (R² > 0.98 bei n < 30 Datenpunkten)
# ---------------------------------------------------------------------------


class TestOverfitWarningResponse:
    """Response-Flag ``overfit_warning`` ergaenzt ``fit_reliability_flag``.

    Unterschied: ``fit_reliability_flag`` prueft "Fit zu schlecht" (R² < 0.5);
    ``overfit_warning`` prueft "Fit zu gut bei zu wenig Daten" — klassischer
    Overfitting-Fall eines 3-Parameter Sigmoid-Fits (Semiconductor Laser
    v3.4.0 Live-Lauf: R² = 0.9983 bei n = 9).
    """

    def test_overfit_warning_true_for_few_strong_sigmoid_points(self):
        """9 Datenpunkte mit sauberer Sigmoid-Form -> R² > 0.98 -> overfit_warning True."""
        # Kleine Zeitreihe (2016-2024) mit starker Sigmoid-Kurve.
        # Logistische kumulative Form: saubere S-Kurve, n = 9.
        year_counts = {
            2016: 2,
            2017: 5,
            2018: 12,
            2019: 25,
            2020: 40,
            2021: 30,
            2022: 15,
            2023: 7,
            2024: 3,
        }
        servicer = _make_servicer(year_counts)
        request = _FakeRequest(start_year=2016, end_year=2024)
        response = _run(servicer.AnalyzeMaturity(request, context=None))

        # Vorbedingung: R² muss >= 0.98 liegen, sonst ist Test nicht aussagekraeftig.
        assert response["r_squared"] > 0.98, (
            f"Fixture nicht geeignet: R²={response['r_squared']} muss > 0.98 sein"
        )
        # Kernaussage: Warnung ist aktiv.
        assert response["overfit_warning"] is True
        # Fit-Reliability bleibt True (Fit ist ja "gut" im R²-Sinn)
        assert response["fit_reliability_flag"] is True

    def test_overfit_warning_false_for_many_datapoints(self):
        """>= 30 vollstaendige Datenpunkte -> overfit_warning False."""
        # 40 Jahre saubere Sigmoid-Kurve: Zeitraum 1985..2024.
        # Auch bei hohem R² darf kein Overfit-Flag gesetzt werden.
        # Logistische jaehrliche Raten (Glocke um inflection ~ 2005).
        year_counts = {}
        for offset, year in enumerate(range(1985, 2025)):
            # Bell-shape: jaehrliche Raten um Inflection = 2005
            distance = abs(year - 2005)
            count = max(1, int(100 * math.exp(-0.05 * distance * distance)))
            year_counts[year] = count

        servicer = _make_servicer(year_counts)
        request = _FakeRequest(start_year=1985, end_year=2024)
        response = _run(servicer.AnalyzeMaturity(request, context=None))

        assert response["overfit_warning"] is False

    def test_overfit_warning_false_when_no_fit(self):
        """Ohne Fit (zu wenige Patente) -> overfit_warning False (defensiv)."""
        # 3 Jahre, Gesamtsumme unter min_patents_for_fit -> kein Fit
        servicer = _make_servicer({2010: 1, 2011: 1, 2012: 1})
        request = _FakeRequest()
        response = _run(servicer.AnalyzeMaturity(request, context=None))

        assert response["overfit_warning"] is False
