"""Unit-Tests fuer maturity-svc Mapper-Module (dict_response.py).

Testet die korrekte Abbildung von MaturityResult auf das dict-basierte
Response-Format, inkl. CAGR-Normalisierung, S-Curve-Daten, Phase und Konfidenz.
"""

from __future__ import annotations

import pytest

from src.mappers.dict_response import maturity_result_to_dict
from src.use_case import MaturityResult


# ---------------------------------------------------------------------------
# Fixture Helper
# ---------------------------------------------------------------------------

def _make_result(**overrides: object) -> MaturityResult:
    """Erstellt ein MaturityResult mit sinnvollen Defaults."""
    defaults: dict = {
        "all_years": [2020, 2021, 2022, 2023, 2024],
        "cumulative": [100, 250, 450, 700, 1000],
        "combined": [100, 150, 200, 250, 300],
        "s_curve_fitted": [
            {"year": 2020, "fitted": 95.0},
            {"year": 2021, "fitted": 240.0},
            {"year": 2022, "fitted": 430.0},
            {"year": 2023, "fitted": 680.0},
            {"year": 2024, "fitted": 980.0},
        ],
        "phase_en": "Growing",
        "maturity_pct": 45.0,
        "r_sq": 0.9876,
        "growth_rate": 24.57,
        "sat_level": 5000.0,
        "growth_rate_k": 0.35,
        "inflection": 2025.5,
        "confidence_lower": 40.0,
        "confidence_upper": 50.0,
        "confidence_level": 0.95,
        "years_to_next_phase": 3,
        "fitted_on": "logistic",
        "is_declining": False,
        "data_complete_year": 2024,
        "aicc_selected": 45.2,
        "aicc_alternative": 52.8,
        "delta_aicc": 7.6,
        "warnings": [],
        "data_sources": [
            {"name": "EPO DOCDB (PostgreSQL)", "type": "PATENT", "record_count": 1000},
        ],
        "processing_time_ms": 55,
    }
    defaults.update(overrides)
    return MaturityResult(**defaults)


# ---------------------------------------------------------------------------
# Tests: Basis-Felder
# ---------------------------------------------------------------------------

class TestDictResponseMapperBasicFields:
    """Testet korrekte Abbildung der Basis-Felder."""

    def test_returns_dict(self):
        """Ergebnis ist ein dict."""
        result = _make_result()
        d = maturity_result_to_dict(result)
        assert isinstance(d, dict)

    def test_top_level_keys(self):
        """Alle erwarteten Top-Level-Keys sind vorhanden."""
        result = _make_result()
        d = maturity_result_to_dict(result)
        expected_keys = {
            "s_curve_data", "phase", "maturity_percent", "r_squared",
            "cagr", "model_parameters", "confidence", "years_to_next_phase",
            "fitted_on", "is_declining", "data_complete_year",
            "aicc_selected", "aicc_alternative", "delta_aicc", "metadata",
        }
        assert expected_keys == set(d.keys())

    def test_phase_mapped(self):
        """Phase wird korrekt abgebildet."""
        result = _make_result(phase_en="Emerging")
        d = maturity_result_to_dict(result)
        assert d["phase"] == "Emerging"

    def test_maturity_percent(self):
        """maturity_percent wird korrekt uebertragen."""
        result = _make_result(maturity_pct=67.3)
        d = maturity_result_to_dict(result)
        assert d["maturity_percent"] == pytest.approx(67.3, abs=0.01)

    def test_r_squared(self):
        """r_squared wird korrekt uebertragen."""
        result = _make_result(r_sq=0.9876)
        d = maturity_result_to_dict(result)
        assert d["r_squared"] == pytest.approx(0.9876, abs=0.0001)

    def test_years_to_next_phase(self):
        """years_to_next_phase wird korrekt uebertragen."""
        result = _make_result(years_to_next_phase=5)
        d = maturity_result_to_dict(result)
        assert d["years_to_next_phase"] == 5

    def test_fitted_on(self):
        """fitted_on wird korrekt uebertragen."""
        result = _make_result(fitted_on="gompertz")
        d = maturity_result_to_dict(result)
        assert d["fitted_on"] == "gompertz"

    def test_is_declining(self):
        """is_declining wird korrekt uebertragen."""
        result = _make_result(is_declining=True)
        d = maturity_result_to_dict(result)
        assert d["is_declining"] is True

    def test_data_complete_year(self):
        """data_complete_year wird korrekt uebertragen."""
        result = _make_result(data_complete_year=2024)
        d = maturity_result_to_dict(result)
        assert d["data_complete_year"] == 2024

    def test_aicc_values(self):
        """AICc-Werte werden korrekt uebertragen."""
        result = _make_result(
            aicc_selected=45.2, aicc_alternative=52.8, delta_aicc=7.6,
        )
        d = maturity_result_to_dict(result)
        assert d["aicc_selected"] == pytest.approx(45.2, abs=0.01)
        assert d["aicc_alternative"] == pytest.approx(52.8, abs=0.01)
        assert d["delta_aicc"] == pytest.approx(7.6, abs=0.01)


# ---------------------------------------------------------------------------
# Tests: CAGR-Normalisierung
# ---------------------------------------------------------------------------

class TestDictResponseMapperCagr:
    """Testet CAGR-Normalisierung (Prozent -> Fraktion, div 100)."""

    def test_cagr_normalized(self):
        """growth_rate wird von Prozent auf Fraktion normiert."""
        result = _make_result(growth_rate=24.57)
        d = maturity_result_to_dict(result)
        assert d["cagr"] == pytest.approx(0.2457, abs=0.0001)

    def test_zero_cagr(self):
        """CAGR 0.0 bleibt 0.0 nach Normalisierung."""
        result = _make_result(growth_rate=0.0)
        d = maturity_result_to_dict(result)
        assert d["cagr"] == 0.0

    def test_negative_cagr(self):
        """Negative CAGR-Werte werden korrekt normiert."""
        result = _make_result(growth_rate=-8.5)
        d = maturity_result_to_dict(result)
        assert d["cagr"] == pytest.approx(-0.085, abs=0.001)

    def test_large_cagr(self):
        """Grosse CAGR-Werte werden korrekt normiert."""
        result = _make_result(growth_rate=150.0)
        d = maturity_result_to_dict(result)
        assert d["cagr"] == pytest.approx(1.5, abs=0.001)


# ---------------------------------------------------------------------------
# Tests: S-Curve-Daten
# ---------------------------------------------------------------------------

class TestDictResponseMapperSCurve:
    """Testet S-Curve-Daten-Mapping."""

    def test_s_curve_length(self):
        """S-Curve-Daten haben korrekte Anzahl Eintraege (= all_years)."""
        result = _make_result()
        d = maturity_result_to_dict(result)
        assert len(d["s_curve_data"]) == 5

    def test_s_curve_entry_keys(self):
        """Jeder S-Curve-Eintrag hat year, cumulative, fitted, annual_count."""
        result = _make_result()
        d = maturity_result_to_dict(result)
        entry = d["s_curve_data"][0]
        assert set(entry.keys()) == {"year", "cumulative", "fitted", "annual_count"}

    def test_s_curve_year_mapping(self):
        """year wird korrekt aus all_years uebernommen."""
        result = _make_result()
        d = maturity_result_to_dict(result)
        years = [e["year"] for e in d["s_curve_data"]]
        assert years == [2020, 2021, 2022, 2023, 2024]

    def test_s_curve_cumulative(self):
        """cumulative wird korrekt als float uebertragen."""
        result = _make_result()
        d = maturity_result_to_dict(result)
        assert d["s_curve_data"][0]["cumulative"] == 100.0
        assert isinstance(d["s_curve_data"][0]["cumulative"], float)

    def test_s_curve_fitted(self):
        """fitted wird aus s_curve_fitted dict korrekt gemappt."""
        result = _make_result()
        d = maturity_result_to_dict(result)
        assert d["s_curve_data"][0]["fitted"] == pytest.approx(95.0, abs=0.1)

    def test_s_curve_fitted_missing_year(self):
        """Fehlende Jahre in s_curve_fitted ergeben 0.0."""
        result = _make_result(
            all_years=[2020], cumulative=[100], combined=[100],
            s_curve_fitted=[],  # Kein Fit
        )
        d = maturity_result_to_dict(result)
        assert d["s_curve_data"][0]["fitted"] == 0.0

    def test_s_curve_annual_count(self):
        """annual_count wird korrekt aus combined uebernommen."""
        result = _make_result()
        d = maturity_result_to_dict(result)
        assert d["s_curve_data"][0]["annual_count"] == 100.0
        assert d["s_curve_data"][2]["annual_count"] == 200.0


# ---------------------------------------------------------------------------
# Tests: Model Parameters
# ---------------------------------------------------------------------------

class TestDictResponseMapperModelParams:
    """Testet Model-Parameter-Abbildung."""

    def test_carrying_capacity(self):
        """carrying_capacity (sat_level) wird korrekt abgebildet."""
        result = _make_result(sat_level=5000.0)
        d = maturity_result_to_dict(result)
        assert d["model_parameters"]["carrying_capacity"] == 5000.0

    def test_growth_rate_k(self):
        """growth_rate (growth_rate_k) wird korrekt abgebildet."""
        result = _make_result(growth_rate_k=0.35)
        d = maturity_result_to_dict(result)
        assert d["model_parameters"]["growth_rate"] == pytest.approx(0.35, abs=0.01)

    def test_inflection_year(self):
        """inflection_year wird korrekt abgebildet."""
        result = _make_result(inflection=2025.5)
        d = maturity_result_to_dict(result)
        assert d["model_parameters"]["inflection_year"] == pytest.approx(2025.5, abs=0.1)


# ---------------------------------------------------------------------------
# Tests: Confidence
# ---------------------------------------------------------------------------

class TestDictResponseMapperConfidence:
    """Testet Konfidenz-Abbildung."""

    def test_confidence_lower(self):
        """confidence lower_bound wird korrekt abgebildet."""
        result = _make_result(confidence_lower=40.0)
        d = maturity_result_to_dict(result)
        assert d["confidence"]["lower_bound"] == 40.0

    def test_confidence_upper(self):
        """confidence upper_bound wird korrekt abgebildet."""
        result = _make_result(confidence_upper=50.0)
        d = maturity_result_to_dict(result)
        assert d["confidence"]["upper_bound"] == 50.0

    def test_confidence_level(self):
        """confidence_level wird korrekt abgebildet."""
        result = _make_result(confidence_level=0.95)
        d = maturity_result_to_dict(result)
        assert d["confidence"]["confidence_level"] == 0.95


# ---------------------------------------------------------------------------
# Tests: Leere Daten
# ---------------------------------------------------------------------------

class TestDictResponseMapperEmptyData:
    """Testet Verhalten bei leeren/minimalen Daten."""

    def test_empty_s_curve(self):
        """Leere S-Curve-Daten (leere all_years) ergeben leere Liste."""
        result = _make_result(all_years=[], cumulative=[], combined=[], s_curve_fitted=[])
        d = maturity_result_to_dict(result)
        assert d["s_curve_data"] == []

    def test_default_result(self):
        """Default-MaturityResult kann gemappt werden."""
        result = MaturityResult()
        d = maturity_result_to_dict(result)
        assert d["phase"] == "Unknown"
        assert d["maturity_percent"] == 0.0
        assert d["cagr"] == 0.0
        assert d["s_curve_data"] == []


# ---------------------------------------------------------------------------
# Tests: Metadata
# ---------------------------------------------------------------------------

class TestDictResponseMapperMetadata:
    """Testet Metadata-Abbildung."""

    def test_processing_time(self):
        """processing_time_ms wird korrekt uebertragen."""
        result = _make_result(processing_time_ms=55)
        d = maturity_result_to_dict(result)
        assert d["metadata"]["processing_time_ms"] == 55

    def test_data_sources(self):
        """data_sources werden korrekt durchgereicht."""
        ds = [{"name": "Test", "type": "PATENT", "record_count": 1000}]
        result = _make_result(data_sources=ds)
        d = maturity_result_to_dict(result)
        assert d["metadata"]["data_sources"] == ds

    def test_request_id_passed(self):
        """request_id wird in Metadata aufgenommen."""
        result = _make_result()
        d = maturity_result_to_dict(result, request_id="req-99")
        assert d["metadata"]["request_id"] == "req-99"

    def test_timestamp_present(self):
        """timestamp wird automatisch gesetzt."""
        result = _make_result()
        d = maturity_result_to_dict(result)
        assert "timestamp" in d["metadata"]
        assert isinstance(d["metadata"]["timestamp"], str)
