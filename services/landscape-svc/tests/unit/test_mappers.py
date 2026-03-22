"""Unit-Tests fuer landscape-svc Mapper-Module (dict_response.py).

Testet die korrekte Abbildung von LandscapeResult auf das dict-basierte
Response-Format, inkl. CAGR-Normalisierung, Zeitreihe, Summary und Metadata.
"""

from __future__ import annotations

import pytest

from src.mappers.dict_response import landscape_result_to_dict
from src.use_case import LandscapeResult


# ---------------------------------------------------------------------------
# Fixture Helper
# ---------------------------------------------------------------------------

def _make_result(**overrides: object) -> LandscapeResult:
    """Erstellt ein LandscapeResult mit sinnvollen Defaults."""
    defaults: dict = {
        "time_series": [
            {"year": 2020, "patents": 100, "projects": 10, "publications": 50},
            {"year": 2024, "patents": 200, "projects": 20, "publications": 80},
        ],
        "funding_by_year": {2020: 1_000_000.0, 2024: 2_000_000.0},
        "top_countries": [
            {"country": "DE", "total": 85, "patents": 80, "projects": 5},
            {"country": "FR", "total": 60, "patents": 60, "projects": 0},
        ],
        "top_cpc": [
            {"code": "H04W", "description": "Wireless", "count": 50},
        ],
        "total_patents": 300,
        "total_projects": 30,
        "total_publications": 130,
        "total_funding": 3_000_000.0,
        "active_countries": 3,
        "cagr_patents": 18.92,
        "cagr_projects": 18.92,
        "cagr_publications": 12.47,
        "cagr_funding": 18.92,
        "periods": 4,
        "data_sources": [
            {"name": "EPO DOCDB (PostgreSQL)", "type": "PATENT", "record_count": 300},
        ],
        "warnings": [],
        "processing_time_ms": 42,
    }
    defaults.update(overrides)
    return LandscapeResult(**defaults)


# ---------------------------------------------------------------------------
# Tests: Basis-Felder
# ---------------------------------------------------------------------------

class TestDictResponseMapperBasicFields:
    """Testet korrekte Abbildung der Basis-Felder."""

    def test_returns_dict(self):
        """Ergebnis ist ein dict."""
        result = _make_result()
        d = landscape_result_to_dict(result)
        assert isinstance(d, dict)

    def test_top_level_keys(self):
        """Alle erwarteten Top-Level-Keys sind vorhanden."""
        result = _make_result()
        d = landscape_result_to_dict(result)
        expected_keys = {
            "time_series", "top_countries", "cagr_values",
            "summary", "top_cpc_codes", "metadata",
        }
        assert expected_keys == set(d.keys())

    def test_summary_fields(self):
        """Summary enthaelt korrekte Totals."""
        result = _make_result()
        d = landscape_result_to_dict(result)
        s = d["summary"]

        assert s["total_patents"] == 300
        assert s["total_projects"] == 30
        assert s["total_publications"] == 130
        assert s["total_funding_eur"] == 3_000_000.0
        assert s["active_countries"] == 3
        assert s["active_actors"] == 0  # Hardcoded bis Entity Resolution

    def test_top_countries_passed_through(self):
        """top_countries wird direkt durchgereicht."""
        countries = [{"country": "DE", "total": 100}]
        result = _make_result(top_countries=countries)
        d = landscape_result_to_dict(result)
        assert d["top_countries"] == countries

    def test_top_cpc_codes_passed_through(self):
        """top_cpc_codes wird direkt durchgereicht."""
        cpc = [{"code": "G06N", "description": "AI", "count": 200}]
        result = _make_result(top_cpc=cpc)
        d = landscape_result_to_dict(result)
        assert d["top_cpc_codes"] == cpc


# ---------------------------------------------------------------------------
# Tests: CAGR-Normalisierung
# ---------------------------------------------------------------------------

class TestDictResponseMapperCagr:
    """Testet CAGR-Normalisierung (Prozent -> Fraktion, div 100)."""

    def test_patent_cagr_normalized(self):
        """Patent-CAGR wird von Prozent auf Fraktion normiert."""
        result = _make_result(cagr_patents=18.92)
        d = landscape_result_to_dict(result)
        assert d["cagr_values"]["patent_cagr"] == pytest.approx(0.1892, abs=0.0001)

    def test_project_cagr_normalized(self):
        """Projekt-CAGR wird von Prozent auf Fraktion normiert."""
        result = _make_result(cagr_projects=25.0)
        d = landscape_result_to_dict(result)
        assert d["cagr_values"]["project_cagr"] == pytest.approx(0.25, abs=0.0001)

    def test_publication_cagr_normalized(self):
        """Publikation-CAGR wird von Prozent auf Fraktion normiert."""
        result = _make_result(cagr_publications=12.5)
        d = landscape_result_to_dict(result)
        assert d["cagr_values"]["publication_cagr"] == pytest.approx(0.125, abs=0.001)

    def test_funding_cagr_normalized(self):
        """Foerder-CAGR wird von Prozent auf Fraktion normiert."""
        result = _make_result(cagr_funding=10.0)
        d = landscape_result_to_dict(result)
        assert d["cagr_values"]["funding_cagr"] == pytest.approx(0.10, abs=0.001)

    def test_zero_cagr(self):
        """CAGR 0.0 bleibt 0.0 nach Normalisierung."""
        result = _make_result(
            cagr_patents=0.0, cagr_projects=0.0,
            cagr_publications=0.0, cagr_funding=0.0,
        )
        d = landscape_result_to_dict(result)
        cv = d["cagr_values"]
        assert cv["patent_cagr"] == 0.0
        assert cv["project_cagr"] == 0.0
        assert cv["publication_cagr"] == 0.0
        assert cv["funding_cagr"] == 0.0

    def test_negative_cagr(self):
        """Negative CAGR-Werte werden korrekt normiert."""
        result = _make_result(cagr_patents=-5.0)
        d = landscape_result_to_dict(result)
        assert d["cagr_values"]["patent_cagr"] == pytest.approx(-0.05, abs=0.001)

    def test_period_years_passed_through(self):
        """period_years wird direkt aus result.periods uebernommen."""
        result = _make_result(periods=14)
        d = landscape_result_to_dict(result)
        assert d["cagr_values"]["period_years"] == 14


# ---------------------------------------------------------------------------
# Tests: Zeitreihe
# ---------------------------------------------------------------------------

class TestDictResponseMapperTimeSeries:
    """Testet Zeitreihen-Mapping."""

    def test_time_series_length(self):
        """Zeitreihe hat korrekte Anzahl Eintraege."""
        result = _make_result()
        d = landscape_result_to_dict(result)
        assert len(d["time_series"]) == 2

    def test_time_series_keys(self):
        """Jeder Zeitreihen-Eintrag hat year, patent_count, project_count, publication_count, funding_eur."""
        result = _make_result()
        d = landscape_result_to_dict(result)
        entry = d["time_series"][0]
        assert set(entry.keys()) == {
            "year", "patent_count", "project_count",
            "publication_count", "funding_eur",
        }

    def test_time_series_field_mapping(self):
        """Felder werden korrekt umbenannt (patents -> patent_count usw.)."""
        result = _make_result()
        d = landscape_result_to_dict(result)
        entry_2020 = next(e for e in d["time_series"] if e["year"] == 2020)
        assert entry_2020["patent_count"] == 100
        assert entry_2020["project_count"] == 10
        assert entry_2020["publication_count"] == 50
        assert entry_2020["funding_eur"] == 1_000_000.0

    def test_time_series_funding_from_funding_by_year(self):
        """funding_eur kommt aus result.funding_by_year, nicht aus time_series dict."""
        ts = [{"year": 2022, "patents": 50, "projects": 5, "publications": 20}]
        fby = {2022: 500_000.0}
        result = _make_result(time_series=ts, funding_by_year=fby)
        d = landscape_result_to_dict(result)
        assert d["time_series"][0]["funding_eur"] == 500_000.0

    def test_time_series_missing_funding_year(self):
        """Fehlende Jahre in funding_by_year ergeben 0.0."""
        ts = [{"year": 2023, "patents": 30}]
        result = _make_result(time_series=ts, funding_by_year={})
        d = landscape_result_to_dict(result)
        assert d["time_series"][0]["funding_eur"] == 0.0

    def test_time_series_missing_keys_default_to_zero(self):
        """Fehlende Keys in time_series dict defaulten zu 0."""
        ts = [{"year": 2020}]  # Nur year, keine patents/projects/publications
        result = _make_result(time_series=ts, funding_by_year={})
        d = landscape_result_to_dict(result)
        entry = d["time_series"][0]
        assert entry["patent_count"] == 0
        assert entry["project_count"] == 0
        assert entry["publication_count"] == 0


# ---------------------------------------------------------------------------
# Tests: Leere Daten
# ---------------------------------------------------------------------------

class TestDictResponseMapperEmptyData:
    """Testet Verhalten bei leeren Daten."""

    def test_empty_time_series(self):
        """Leere Zeitreihe wird korrekt durchgereicht."""
        result = _make_result(time_series=[])
        d = landscape_result_to_dict(result)
        assert d["time_series"] == []

    def test_empty_top_countries(self):
        """Leere Laenderliste wird korrekt durchgereicht."""
        result = _make_result(top_countries=[])
        d = landscape_result_to_dict(result)
        assert d["top_countries"] == []

    def test_empty_top_cpc(self):
        """Leere CPC-Liste wird korrekt durchgereicht."""
        result = _make_result(top_cpc=[])
        d = landscape_result_to_dict(result)
        assert d["top_cpc_codes"] == []

    def test_empty_warnings(self):
        """Leere Warnings werden korrekt durchgereicht."""
        result = _make_result(warnings=[])
        d = landscape_result_to_dict(result)
        assert d["metadata"]["warnings"] == []


# ---------------------------------------------------------------------------
# Tests: Metadata
# ---------------------------------------------------------------------------

class TestDictResponseMapperMetadata:
    """Testet Metadata-Abbildung."""

    def test_processing_time(self):
        """processing_time_ms wird korrekt uebertragen."""
        result = _make_result(processing_time_ms=123)
        d = landscape_result_to_dict(result)
        assert d["metadata"]["processing_time_ms"] == 123

    def test_data_sources(self):
        """data_sources werden korrekt durchgereicht."""
        ds = [{"name": "Test", "type": "PATENT", "record_count": 10}]
        result = _make_result(data_sources=ds)
        d = landscape_result_to_dict(result)
        assert d["metadata"]["data_sources"] == ds

    def test_request_id_passed(self):
        """request_id wird in Metadata aufgenommen."""
        result = _make_result()
        d = landscape_result_to_dict(result, request_id="req-42")
        assert d["metadata"]["request_id"] == "req-42"

    def test_request_id_default_empty(self):
        """request_id ist standardmaessig leer."""
        result = _make_result()
        d = landscape_result_to_dict(result)
        assert d["metadata"]["request_id"] == ""

    def test_timestamp_present(self):
        """timestamp wird automatisch gesetzt."""
        result = _make_result()
        d = landscape_result_to_dict(result)
        assert "timestamp" in d["metadata"]
        assert isinstance(d["metadata"]["timestamp"], str)
        assert len(d["metadata"]["timestamp"]) > 0
