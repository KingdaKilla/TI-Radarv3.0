"""Unit-Tests fuer patent-grant-svc dict_response Mapper.

Testet die Konvertierung von PatentGrantResult in ein dict-basiertes
Response-Format fuer REST/JSON-Auslieferung.

Besonderer Fokus: Feld-Renaming (kind_codes -> kind_code_distribution,
country_rates -> country_grant_rates, cpc_rates -> cpc_grant_rates).
"""

from __future__ import annotations

import pytest

from src.mappers.dict_response import patent_grant_result_to_dict
from src.use_case import PatentGrantResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(**overrides) -> PatentGrantResult:
    """Erstellt ein PatentGrantResult mit sinnvollen Standardwerten."""
    defaults = dict(
        summary={
            "total_applications": 500,
            "total_grants": 200,
            "grant_rate": 0.4,
            "avg_time_to_grant_months": 36.5,
            "median_time_to_grant_months": 34.0,
        },
        year_trend=[
            {"year": 2020, "application_count": 100, "grant_count": 40, "grant_rate": 0.4},
            {"year": 2021, "application_count": 120, "grant_count": 50, "grant_rate": 0.417},
        ],
        kind_codes=[
            {"kind_code": "A1", "count": 300, "description": "Application with search report"},
            {"kind_code": "B1", "count": 200, "description": "Granted patent"},
        ],
        country_rates=[
            {"country": "DE", "application_count": 80, "grant_count": 35, "grant_rate": 0.4375},
            {"country": "FR", "application_count": 60, "grant_count": 25, "grant_rate": 0.4167},
        ],
        cpc_rates=[
            {"cpc_section": "H", "application_count": 200, "grant_count": 80, "grant_rate": 0.4},
        ],
        warnings=[],
        data_sources=[
            {"name": "EPO DOCDB (PostgreSQL)", "type": "PATENT", "record_count": 500},
        ],
        processing_time_ms=48,
    )
    defaults.update(overrides)
    return PatentGrantResult(**defaults)


# ---------------------------------------------------------------------------
# Tests: Grundstruktur
# ---------------------------------------------------------------------------

class TestDictResponseMapper:
    """Testet die Grundstruktur des Response-Dicts."""

    def test_returns_dict(self):
        result = _make_result()
        d = patent_grant_result_to_dict(result)
        assert isinstance(d, dict)

    def test_top_level_keys(self):
        result = _make_result()
        d = patent_grant_result_to_dict(result)
        expected_keys = {
            "summary", "year_trend", "kind_code_distribution",
            "country_grant_rates", "cpc_grant_rates", "metadata",
        }
        assert set(d.keys()) == expected_keys

    def test_metadata_keys(self):
        result = _make_result()
        d = patent_grant_result_to_dict(result, request_id="pg-001")
        meta = d["metadata"]
        assert "processing_time_ms" in meta
        assert "data_sources" in meta
        assert "warnings" in meta
        assert "request_id" in meta
        assert "timestamp" in meta


# ---------------------------------------------------------------------------
# Tests: Feld-Renaming
# ---------------------------------------------------------------------------

class TestFieldRenaming:
    """Testet korrekte Umbenennung der Felder fuer die API-Response.

    - kind_codes -> kind_code_distribution
    - country_rates -> country_grant_rates
    - cpc_rates -> cpc_grant_rates
    """

    def test_kind_codes_renamed(self):
        data = [{"kind_code": "A1", "count": 100}]
        result = _make_result(kind_codes=data)
        d = patent_grant_result_to_dict(result)
        assert d["kind_code_distribution"] == data
        assert "kind_codes" not in d

    def test_country_rates_renamed(self):
        data = [{"country": "US", "grant_rate": 0.5}]
        result = _make_result(country_rates=data)
        d = patent_grant_result_to_dict(result)
        assert d["country_grant_rates"] == data
        assert "country_rates" not in d

    def test_cpc_rates_renamed(self):
        data = [{"cpc_section": "G", "grant_rate": 0.35}]
        result = _make_result(cpc_rates=data)
        d = patent_grant_result_to_dict(result)
        assert d["cpc_grant_rates"] == data
        assert "cpc_rates" not in d

    def test_summary_passthrough(self):
        summary = {
            "total_applications": 1000,
            "total_grants": 400,
            "grant_rate": 0.4,
            "avg_time_to_grant_months": 40.0,
            "median_time_to_grant_months": 38.0,
        }
        result = _make_result(summary=summary)
        d = patent_grant_result_to_dict(result)
        assert d["summary"] == summary

    def test_year_trend_passthrough(self):
        data = [{"year": 2022, "application_count": 150, "grant_count": 65}]
        result = _make_result(year_trend=data)
        d = patent_grant_result_to_dict(result)
        assert d["year_trend"] == data


# ---------------------------------------------------------------------------
# Tests: Summary-Felder
# ---------------------------------------------------------------------------

class TestSummaryFields:
    """Testet Summary-Dict-Inhalte (Passthrough)."""

    def test_grant_rate_value(self):
        result = _make_result()
        d = patent_grant_result_to_dict(result)
        assert d["summary"]["grant_rate"] == pytest.approx(0.4)

    def test_total_applications(self):
        result = _make_result()
        d = patent_grant_result_to_dict(result)
        assert d["summary"]["total_applications"] == 500

    def test_total_grants(self):
        result = _make_result()
        d = patent_grant_result_to_dict(result)
        assert d["summary"]["total_grants"] == 200

    def test_avg_time_to_grant(self):
        result = _make_result()
        d = patent_grant_result_to_dict(result)
        assert d["summary"]["avg_time_to_grant_months"] == pytest.approx(36.5)

    def test_median_time_to_grant(self):
        result = _make_result()
        d = patent_grant_result_to_dict(result)
        assert d["summary"]["median_time_to_grant_months"] == pytest.approx(34.0)


# ---------------------------------------------------------------------------
# Tests: Metadata
# ---------------------------------------------------------------------------

class TestMetadata:
    """Testet Metadata-Felder im Response-Dict."""

    def test_request_id_forwarded(self):
        result = _make_result()
        d = patent_grant_result_to_dict(result, request_id="pg-xyz")
        assert d["metadata"]["request_id"] == "pg-xyz"

    def test_request_id_default_empty(self):
        result = _make_result()
        d = patent_grant_result_to_dict(result)
        assert d["metadata"]["request_id"] == ""

    def test_processing_time_ms(self):
        result = _make_result(processing_time_ms=88)
        d = patent_grant_result_to_dict(result)
        assert d["metadata"]["processing_time_ms"] == 88

    def test_data_sources_forwarded(self):
        sources = [{"name": "EPO", "type": "PATENT", "record_count": 300}]
        result = _make_result(data_sources=sources)
        d = patent_grant_result_to_dict(result)
        assert d["metadata"]["data_sources"] == sources

    def test_timestamp_iso_format(self):
        result = _make_result()
        d = patent_grant_result_to_dict(result)
        assert "T" in d["metadata"]["timestamp"]


# ---------------------------------------------------------------------------
# Tests: Leere / Grenzwerte
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Testet Randfaelle: leere Listen, Default-Result."""

    def test_empty_lists(self):
        result = _make_result(
            year_trend=[], kind_codes=[], country_rates=[], cpc_rates=[],
        )
        d = patent_grant_result_to_dict(result)
        assert d["year_trend"] == []
        assert d["kind_code_distribution"] == []
        assert d["country_grant_rates"] == []
        assert d["cpc_grant_rates"] == []

    def test_default_result(self):
        result = PatentGrantResult()
        d = patent_grant_result_to_dict(result)
        assert d["summary"]["total_applications"] == 0
        assert d["summary"]["total_grants"] == 0
        assert d["summary"]["grant_rate"] == 0.0
        assert d["year_trend"] == []
        assert d["kind_code_distribution"] == []
        assert d["country_grant_rates"] == []
        assert d["cpc_grant_rates"] == []
        assert d["metadata"]["processing_time_ms"] == 0

    def test_default_summary_time_values(self):
        result = PatentGrantResult()
        d = patent_grant_result_to_dict(result)
        assert d["summary"]["avg_time_to_grant_months"] == 0.0
        assert d["summary"]["median_time_to_grant_months"] == 0.0
