"""Unit-Tests fuer funding-svc Mapper-Module (dict_response.py).

Testet die korrekte Abbildung von FundingResult auf das dict-basierte
Response-Format, inkl. CAGR-Normalisierung, Zeitreihe, Programme und
Research-Area-Breakdown.
"""

from __future__ import annotations

import pytest

from shared.domain.result_types import FundingYear
from src.mappers.dict_response import funding_result_to_dict, _build_research_area_breakdown
from src.use_case import FundingResult


# ---------------------------------------------------------------------------
# Fixture Helper
# ---------------------------------------------------------------------------

def _make_result(**overrides: object) -> FundingResult:
    """Erstellt ein FundingResult mit sinnvollen Defaults."""
    defaults: dict = {
        "total_funding": 5_000_000.0,
        "total_projects": 25,
        "funding_cagr": 15.5,
        "funding_years": [
            FundingYear(year=2020, funding=1_000_000.0, count=5),
            FundingYear(year=2022, funding=1_500_000.0, count=8),
            FundingYear(year=2024, funding=2_500_000.0, count=12),
        ],
        "programme_data": [
            {"programme": "Horizon Europe", "funding": 3_000_000.0, "count": 15},
            {"programme": "Horizon 2020", "funding": 2_000_000.0, "count": 10},
        ],
        "instrument_data": [
            {"funding_scheme": "RIA", "funding": 3_500_000.0, "count": 18},
            {"funding_scheme": "CSA", "funding": 1_500_000.0, "count": 7},
        ],
        "top_orgs": [
            {"name": "Fraunhofer", "country": "DE", "funding": 800_000.0, "count": 4, "type": "REC"},
        ],
        "country_data": [
            {"country": "DE", "funding": 1_200_000.0, "count": 8},
            {"country": "FR", "funding": 900_000.0, "count": 6},
        ],
        "research_area_data": [],
        "avg_duration": 36.5,
        "avg_size": 200_000.0,
        "warnings": [],
        "data_sources": [
            {"name": "CORDIS (PostgreSQL)", "type": "FUNDING", "record_count": 25},
        ],
        "processing_time_ms": 65,
    }
    defaults.update(overrides)
    return FundingResult(**defaults)


# ---------------------------------------------------------------------------
# Tests: Basis-Felder
# ---------------------------------------------------------------------------

class TestDictResponseMapperBasicFields:
    """Testet korrekte Abbildung der Basis-Felder."""

    def test_returns_dict(self):
        """Ergebnis ist ein dict."""
        result = _make_result()
        d = funding_result_to_dict(result)
        assert isinstance(d, dict)

    def test_top_level_keys(self):
        """Alle erwarteten Top-Level-Keys sind vorhanden."""
        result = _make_result()
        d = funding_result_to_dict(result)
        expected_keys = {
            "total_funding_eur", "project_count", "cagr",
            "programme_breakdown", "instrument_breakdown",
            "time_series", "top_organisations", "country_distribution",
            "avg_duration_months", "avg_funding_per_project",
            "research_area_breakdown", "metadata",
        }
        assert expected_keys == set(d.keys())

    def test_total_funding_rounded(self):
        """total_funding_eur wird auf 2 Dezimalstellen gerundet."""
        result = _make_result(total_funding=5_000_000.123456)
        d = funding_result_to_dict(result)
        assert d["total_funding_eur"] == pytest.approx(5_000_000.12, abs=0.005)

    def test_project_count(self):
        """project_count wird korrekt uebertragen."""
        result = _make_result(total_projects=25)
        d = funding_result_to_dict(result)
        assert d["project_count"] == 25

    def test_avg_duration(self):
        """avg_duration_months wird korrekt uebertragen."""
        result = _make_result(avg_duration=36.5)
        d = funding_result_to_dict(result)
        assert d["avg_duration_months"] == pytest.approx(36.5, abs=0.1)

    def test_avg_funding_per_project_rounded(self):
        """avg_funding_per_project wird auf 2 Dezimalstellen gerundet."""
        result = _make_result(avg_size=200_000.456)
        d = funding_result_to_dict(result)
        assert d["avg_funding_per_project"] == pytest.approx(200_000.46, abs=0.005)


# ---------------------------------------------------------------------------
# Tests: CAGR-Normalisierung
# ---------------------------------------------------------------------------

class TestDictResponseMapperCagr:
    """Testet CAGR-Normalisierung (Prozent -> Fraktion, div 100)."""

    def test_cagr_normalized(self):
        """funding_cagr wird von Prozent auf Fraktion normiert."""
        result = _make_result(funding_cagr=15.5)
        d = funding_result_to_dict(result)
        assert d["cagr"] == pytest.approx(0.155, abs=0.001)

    def test_zero_cagr(self):
        """CAGR 0.0 bleibt 0.0."""
        result = _make_result(funding_cagr=0.0)
        d = funding_result_to_dict(result)
        assert d["cagr"] == 0.0

    def test_negative_cagr(self):
        """Negative CAGR wird korrekt normiert."""
        result = _make_result(funding_cagr=-12.3)
        d = funding_result_to_dict(result)
        assert d["cagr"] == pytest.approx(-0.123, abs=0.001)

    def test_large_cagr(self):
        """Grosse CAGR-Werte werden korrekt normiert."""
        result = _make_result(funding_cagr=200.0)
        d = funding_result_to_dict(result)
        assert d["cagr"] == pytest.approx(2.0, abs=0.001)


# ---------------------------------------------------------------------------
# Tests: Zeitreihe
# ---------------------------------------------------------------------------

class TestDictResponseMapperTimeSeries:
    """Testet Zeitreihen-Mapping."""

    def test_time_series_length(self):
        """Zeitreihe hat korrekte Anzahl Eintraege."""
        result = _make_result()
        d = funding_result_to_dict(result)
        assert len(d["time_series"]) == 3

    def test_time_series_entry_keys(self):
        """Jeder Zeitreihen-Eintrag hat die erwarteten Keys."""
        result = _make_result()
        d = funding_result_to_dict(result)
        entry = d["time_series"][0]
        expected_keys = {
            "year", "funding_eur", "project_count",
            "avg_project_size", "participant_count",
        }
        assert set(entry.keys()) == expected_keys

    def test_time_series_values(self):
        """Zeitreihen-Werte werden korrekt aus FundingYear abgebildet."""
        result = _make_result()
        d = funding_result_to_dict(result)
        entry_2020 = d["time_series"][0]
        assert entry_2020["year"] == 2020
        assert entry_2020["funding_eur"] == 1_000_000.0
        assert entry_2020["project_count"] == 5

    def test_avg_project_size_calculated(self):
        """avg_project_size wird als funding/count berechnet."""
        result = _make_result()
        d = funding_result_to_dict(result)
        entry_2020 = d["time_series"][0]
        # 1_000_000 / 5 = 200_000
        assert entry_2020["avg_project_size"] == pytest.approx(200_000.0, abs=0.01)

    def test_avg_project_size_zero_count(self):
        """avg_project_size ist 0 bei count == 0 (Division durch Null)."""
        result = _make_result(
            funding_years=[FundingYear(year=2020, funding=100_000.0, count=0)],
        )
        d = funding_result_to_dict(result)
        assert d["time_series"][0]["avg_project_size"] == 0.0

    def test_participant_count_always_zero(self):
        """participant_count ist immer 0 (noch nicht implementiert)."""
        result = _make_result()
        d = funding_result_to_dict(result)
        for entry in d["time_series"]:
            assert entry["participant_count"] == 0

    def test_empty_time_series(self):
        """Leere Zeitreihe wird korrekt durchgereicht."""
        result = _make_result(funding_years=[])
        d = funding_result_to_dict(result)
        assert d["time_series"] == []


# ---------------------------------------------------------------------------
# Tests: Programme und Instrument Breakdown
# ---------------------------------------------------------------------------

class TestDictResponseMapperBreakdowns:
    """Testet Programme- und Instrument-Breakdown-Abbildung."""

    def test_programme_passed_through(self):
        """programme_breakdown wird direkt durchgereicht."""
        result = _make_result()
        d = funding_result_to_dict(result)
        assert len(d["programme_breakdown"]) == 2
        assert d["programme_breakdown"][0]["programme"] == "Horizon Europe"

    def test_instrument_passed_through(self):
        """instrument_breakdown wird direkt durchgereicht."""
        result = _make_result()
        d = funding_result_to_dict(result)
        assert len(d["instrument_breakdown"]) == 2

    def test_empty_breakdowns(self):
        """Leere Breakdowns werden korrekt durchgereicht."""
        result = _make_result(programme_data=[], instrument_data=[])
        d = funding_result_to_dict(result)
        assert d["programme_breakdown"] == []
        assert d["instrument_breakdown"] == []


# ---------------------------------------------------------------------------
# Tests: Top-Organisationen und Laender
# ---------------------------------------------------------------------------

class TestDictResponseMapperOrgsCountries:
    """Testet Top-Organisationen und Laenderverteilung."""

    def test_top_orgs_passed_through(self):
        """top_organisations werden direkt durchgereicht."""
        result = _make_result()
        d = funding_result_to_dict(result)
        assert len(d["top_organisations"]) == 1
        assert d["top_organisations"][0]["name"] == "Fraunhofer"

    def test_country_distribution_passed_through(self):
        """country_distribution wird direkt durchgereicht."""
        result = _make_result()
        d = funding_result_to_dict(result)
        assert len(d["country_distribution"]) == 2

    def test_empty_orgs_and_countries(self):
        """Leere Listen werden korrekt durchgereicht."""
        result = _make_result(top_orgs=[], country_data=[])
        d = funding_result_to_dict(result)
        assert d["top_organisations"] == []
        assert d["country_distribution"] == []


# ---------------------------------------------------------------------------
# Tests: Research Area Breakdown (Hilfsfunktion)
# ---------------------------------------------------------------------------

class TestBuildResearchAreaBreakdown:
    """Testet _build_research_area_breakdown Hilfsfunktion."""

    def test_empty_input(self):
        """Leere Eingabe ergibt leere Liste."""
        assert _build_research_area_breakdown([]) == []

    def test_single_area_single_year(self):
        """Einzelner Forschungsbereich mit einem Jahr."""
        raw = [{
            "area_code": "LS",
            "area_label": "Life Sciences",
            "level": 1,
            "parent_code": "",
            "year": 2020,
            "funding": 500_000.0,
            "count": 3,
        }]
        result = _build_research_area_breakdown(raw)
        assert len(result) == 1
        assert result[0]["area_code"] == "LS"
        assert result[0]["area_label"] == "Life Sciences"
        assert len(result[0]["years"]) == 1
        assert result[0]["years"][0]["year"] == 2020
        assert result[0]["years"][0]["funding_eur"] == 500_000.0
        assert result[0]["years"][0]["project_count"] == 3

    def test_multiple_years_grouped(self):
        """Mehrere Jahre werden unter demselben Bereich gruppiert."""
        raw = [
            {"area_code": "PE", "area_label": "Physical Sciences", "level": 1,
             "parent_code": "", "year": 2020, "funding": 100_000.0, "count": 2},
            {"area_code": "PE", "area_label": "Physical Sciences", "level": 1,
             "parent_code": "", "year": 2022, "funding": 200_000.0, "count": 4},
        ]
        result = _build_research_area_breakdown(raw)
        assert len(result) == 1
        assert len(result[0]["years"]) == 2
        # Sortiert nach year
        assert result[0]["years"][0]["year"] == 2020
        assert result[0]["years"][1]["year"] == 2022

    def test_multiple_areas_sorted(self):
        """Bereiche werden nach level, dann nach Foerderung (absteigend) sortiert."""
        raw = [
            {"area_code": "PE", "area_label": "Physical", "level": 1,
             "parent_code": "", "year": 2020, "funding": 100_000.0, "count": 1},
            {"area_code": "LS", "area_label": "Life Sci", "level": 1,
             "parent_code": "", "year": 2020, "funding": 500_000.0, "count": 5},
        ]
        result = _build_research_area_breakdown(raw)
        assert len(result) == 2
        # LS hat mehr funding -> kommt zuerst (innerhalb level 1)
        assert result[0]["area_code"] == "LS"
        assert result[1]["area_code"] == "PE"

    def test_funding_rounded(self):
        """funding_eur in years wird auf 2 Dezimalstellen gerundet."""
        raw = [{
            "area_code": "LS", "area_label": "Life", "level": 1,
            "parent_code": "", "year": 2020, "funding": 123456.789, "count": 1,
        }]
        result = _build_research_area_breakdown(raw)
        assert result[0]["years"][0]["funding_eur"] == pytest.approx(123456.79, abs=0.005)


# ---------------------------------------------------------------------------
# Tests: Leere Daten
# ---------------------------------------------------------------------------

class TestDictResponseMapperEmptyData:
    """Testet Verhalten bei leeren/minimalen Daten."""

    def test_default_result(self):
        """Default-FundingResult kann gemappt werden."""
        result = FundingResult()
        d = funding_result_to_dict(result)
        assert d["total_funding_eur"] == 0.0
        assert d["project_count"] == 0
        assert d["cagr"] == 0.0
        assert d["time_series"] == []
        assert d["research_area_breakdown"] == []


# ---------------------------------------------------------------------------
# Tests: Metadata
# ---------------------------------------------------------------------------

class TestDictResponseMapperMetadata:
    """Testet Metadata-Abbildung."""

    def test_processing_time(self):
        """processing_time_ms wird korrekt uebertragen."""
        result = _make_result(processing_time_ms=65)
        d = funding_result_to_dict(result)
        assert d["metadata"]["processing_time_ms"] == 65

    def test_data_sources(self):
        """data_sources werden korrekt durchgereicht."""
        ds = [{"name": "CORDIS", "type": "FUNDING", "record_count": 25}]
        result = _make_result(data_sources=ds)
        d = funding_result_to_dict(result)
        assert d["metadata"]["data_sources"] == ds

    def test_request_id_passed(self):
        """request_id wird in Metadata aufgenommen."""
        result = _make_result()
        d = funding_result_to_dict(result, request_id="req-fund-7")
        assert d["metadata"]["request_id"] == "req-fund-7"

    def test_timestamp_present(self):
        """timestamp wird automatisch gesetzt."""
        result = _make_result()
        d = funding_result_to_dict(result)
        assert "timestamp" in d["metadata"]
        assert isinstance(d["metadata"]["timestamp"], str)
