"""Unit-Tests fuer geographic-svc Mapper-Module (dict_response.py).

Testet die korrekte Abbildung von GeographicResult auf das dict-basierte
Response-Format, inkl. Laenderverteilung, Staedte, Kooperationspaare
und Cross-Border-Share.
"""

from __future__ import annotations

import pytest

from src.mappers.dict_response import geographic_result_to_dict
from src.use_case import GeographicResult


# ---------------------------------------------------------------------------
# Fixture Helper
# ---------------------------------------------------------------------------

def _make_result(**overrides: object) -> GeographicResult:
    """Erstellt ein GeographicResult mit sinnvollen Defaults."""
    defaults: dict = {
        "country_dist": [
            {"country": "DE", "patents": 500, "projects": 80, "total": 580},
            {"country": "FR", "patents": 300, "projects": 60, "total": 360},
            {"country": "NL", "patents": 100, "projects": 40, "total": 140},
        ],
        "city_data": [
            {"city": "Berlin", "country_code": "DE", "actor_count": 25, "project_count": 15},
            {"city": "Paris", "country_code": "FR", "actor_count": 20, "project_count": 12},
        ],
        "collab_pairs": [
            {"country_a": "DE", "country_b": "FR", "co_project_count": 18},
            {"country_a": "DE", "country_b": "NL", "co_project_count": 12},
        ],
        "cross_border_share": 0.35,
        "total_countries": 3,
        "total_cities": 2,
        "warnings": [],
        "data_sources": [
            {"name": "EPO DOCDB (PostgreSQL)", "type": "PATENT", "record_count": 900},
            {"name": "CORDIS (PostgreSQL)", "type": "PROJECT", "record_count": 180},
        ],
        "processing_time_ms": 48,
    }
    defaults.update(overrides)
    return GeographicResult(**defaults)


# ---------------------------------------------------------------------------
# Tests: Basis-Felder
# ---------------------------------------------------------------------------

class TestDictResponseMapperBasicFields:
    """Testet korrekte Abbildung der Basis-Felder."""

    def test_returns_dict(self):
        """Ergebnis ist ein dict."""
        result = _make_result()
        d = geographic_result_to_dict(result)
        assert isinstance(d, dict)

    def test_top_level_keys(self):
        """Alle erwarteten Top-Level-Keys sind vorhanden."""
        result = _make_result()
        d = geographic_result_to_dict(result)
        expected_keys = {
            "country_distribution", "city_distribution",
            "cooperation_pairs", "cross_border_share",
            "total_countries", "total_cities", "metadata",
        }
        assert expected_keys == set(d.keys())

    def test_total_countries(self):
        """total_countries wird korrekt uebertragen."""
        result = _make_result(total_countries=3)
        d = geographic_result_to_dict(result)
        assert d["total_countries"] == 3

    def test_total_cities(self):
        """total_cities wird korrekt uebertragen."""
        result = _make_result(total_cities=2)
        d = geographic_result_to_dict(result)
        assert d["total_cities"] == 2

    def test_cross_border_share(self):
        """cross_border_share wird korrekt uebertragen."""
        result = _make_result(cross_border_share=0.35)
        d = geographic_result_to_dict(result)
        assert d["cross_border_share"] == pytest.approx(0.35, abs=0.001)

    def test_cross_border_share_zero(self):
        """cross_border_share 0.0 wird korrekt durchgereicht."""
        result = _make_result(cross_border_share=0.0)
        d = geographic_result_to_dict(result)
        assert d["cross_border_share"] == 0.0


# ---------------------------------------------------------------------------
# Tests: Laenderverteilung
# ---------------------------------------------------------------------------

class TestDictResponseMapperCountryDist:
    """Testet Laenderverteilung-Abbildung."""

    def test_country_dist_passed_through(self):
        """country_distribution wird direkt durchgereicht."""
        result = _make_result()
        d = geographic_result_to_dict(result)
        assert len(d["country_distribution"]) == 3

    def test_country_dist_fields(self):
        """Laender-Eintraege behalten ihre Felder."""
        result = _make_result()
        d = geographic_result_to_dict(result)
        de = d["country_distribution"][0]
        assert de["country"] == "DE"
        assert de["patents"] == 500
        assert de["projects"] == 80
        assert de["total"] == 580

    def test_empty_country_dist(self):
        """Leere Laenderliste wird korrekt durchgereicht."""
        result = _make_result(country_dist=[])
        d = geographic_result_to_dict(result)
        assert d["country_distribution"] == []


# ---------------------------------------------------------------------------
# Tests: Staedteverteilung
# ---------------------------------------------------------------------------

class TestDictResponseMapperCityDist:
    """Testet Staedteverteilung-Abbildung."""

    def test_city_data_passed_through(self):
        """city_distribution wird direkt durchgereicht."""
        result = _make_result()
        d = geographic_result_to_dict(result)
        assert len(d["city_distribution"]) == 2

    def test_city_data_fields(self):
        """Stadt-Eintraege behalten ihre Felder."""
        result = _make_result()
        d = geographic_result_to_dict(result)
        berlin = d["city_distribution"][0]
        assert berlin["city"] == "Berlin"
        assert berlin["country_code"] == "DE"
        assert berlin["actor_count"] == 25
        assert berlin["project_count"] == 15

    def test_empty_city_data(self):
        """Leere Staedteliste wird korrekt durchgereicht."""
        result = _make_result(city_data=[])
        d = geographic_result_to_dict(result)
        assert d["city_distribution"] == []


# ---------------------------------------------------------------------------
# Tests: Kooperationspaare
# ---------------------------------------------------------------------------

class TestDictResponseMapperCoopPairs:
    """Testet Kooperationspaare-Abbildung."""

    def test_collab_pairs_passed_through(self):
        """cooperation_pairs werden direkt durchgereicht."""
        result = _make_result()
        d = geographic_result_to_dict(result)
        assert len(d["cooperation_pairs"]) == 2

    def test_collab_pair_fields(self):
        """Kooperationspaar-Eintraege behalten ihre Felder."""
        result = _make_result()
        d = geographic_result_to_dict(result)
        pair = d["cooperation_pairs"][0]
        assert pair["country_a"] == "DE"
        assert pair["country_b"] == "FR"
        assert pair["co_project_count"] == 18

    def test_empty_collab_pairs(self):
        """Leere Kooperationsliste wird korrekt durchgereicht."""
        result = _make_result(collab_pairs=[])
        d = geographic_result_to_dict(result)
        assert d["cooperation_pairs"] == []


# ---------------------------------------------------------------------------
# Tests: Leere Daten
# ---------------------------------------------------------------------------

class TestDictResponseMapperEmptyData:
    """Testet Verhalten bei leeren/minimalen Daten."""

    def test_default_result(self):
        """Default-GeographicResult kann gemappt werden."""
        result = GeographicResult()
        d = geographic_result_to_dict(result)
        assert d["country_distribution"] == []
        assert d["city_distribution"] == []
        assert d["cooperation_pairs"] == []
        assert d["cross_border_share"] == 0.0
        assert d["total_countries"] == 0
        assert d["total_cities"] == 0

    def test_all_empty_lists(self):
        """Alle leeren Listen werden korrekt durchgereicht."""
        result = _make_result(
            country_dist=[], city_data=[], collab_pairs=[],
        )
        d = geographic_result_to_dict(result)
        assert d["country_distribution"] == []
        assert d["city_distribution"] == []
        assert d["cooperation_pairs"] == []


# ---------------------------------------------------------------------------
# Tests: Metadata
# ---------------------------------------------------------------------------

class TestDictResponseMapperMetadata:
    """Testet Metadata-Abbildung."""

    def test_processing_time(self):
        """processing_time_ms wird korrekt uebertragen."""
        result = _make_result(processing_time_ms=48)
        d = geographic_result_to_dict(result)
        assert d["metadata"]["processing_time_ms"] == 48

    def test_data_sources(self):
        """data_sources werden korrekt durchgereicht."""
        result = _make_result()
        d = geographic_result_to_dict(result)
        assert len(d["metadata"]["data_sources"]) == 2
        source_names = [ds["name"] for ds in d["metadata"]["data_sources"]]
        assert "EPO DOCDB (PostgreSQL)" in source_names
        assert "CORDIS (PostgreSQL)" in source_names

    def test_warnings_passed(self):
        """Warnings werden korrekt durchgereicht."""
        warnings = [
            {"message": "Daten unvollstaendig", "severity": "MEDIUM", "code": "DATA_INCOMPLETE"},
        ]
        result = _make_result(warnings=warnings)
        d = geographic_result_to_dict(result)
        assert d["metadata"]["warnings"] == warnings

    def test_request_id_passed(self):
        """request_id wird in Metadata aufgenommen."""
        result = _make_result()
        d = geographic_result_to_dict(result, request_id="req-geo-5")
        assert d["metadata"]["request_id"] == "req-geo-5"

    def test_request_id_default_empty(self):
        """request_id ist standardmaessig leer."""
        result = _make_result()
        d = geographic_result_to_dict(result)
        assert d["metadata"]["request_id"] == ""

    def test_timestamp_present(self):
        """timestamp wird automatisch gesetzt."""
        result = _make_result()
        d = geographic_result_to_dict(result)
        assert "timestamp" in d["metadata"]
        assert isinstance(d["metadata"]["timestamp"], str)
        assert len(d["metadata"]["timestamp"]) > 0
