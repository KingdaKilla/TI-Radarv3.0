"""Unit-Tests fuer competitive-svc Mapper-Module (dict_response.py).

Testet die korrekte Abbildung von CompetitiveResult auf das dict-basierte
Response-Format, inkl. HHI-Rundung, CR4, Akteur-Listen und Netzwerk-Daten.
"""

from __future__ import annotations

import pytest

from src.mappers.dict_response import competitive_result_to_dict
from src.use_case import CompetitiveResult


# ---------------------------------------------------------------------------
# Fixture Helper
# ---------------------------------------------------------------------------

def _make_result(**overrides: object) -> CompetitiveResult:
    """Erstellt ein CompetitiveResult mit sinnvollen Defaults."""
    defaults: dict = {
        "hhi": 0.1523,
        "level_en": "Moderate",
        "cr4_share": 0.4512,
        "top_actors": [
            {
                "name": "SIEMENS AG",
                "country_code": "DE",
                "patent_count": 120,
                "project_count": 15,
                "share": 0.2345,
            },
            {
                "name": "BOSCH GMBH",
                "country_code": "DE",
                "patent_count": 80,
                "project_count": 10,
                "share": 0.1567,
            },
        ],
        "network_nodes": [
            {"id": "SIEMENS AG", "label": "SIEMENS AG", "size": 135.0, "community": 0, "country_code": "DE"},
            {"id": "BOSCH GMBH", "label": "BOSCH GMBH", "size": 90.0, "community": 0, "country_code": "DE"},
        ],
        "network_edges": [
            {"source": "BOSCH GMBH", "target": "SIEMENS AG", "weight": 5, "collaboration_type": "MIXED"},
        ],
        "top_3_share": 0.5678,
        "top_10_share": 0.8234,
        "total_actors": 45,
        "warnings": [],
        "data_sources": [
            {"name": "EPO DOCDB (PostgreSQL)", "type": "PATENT", "record_count": 500},
        ],
        "processing_time_ms": 78,
    }
    defaults.update(overrides)
    return CompetitiveResult(**defaults)


# ---------------------------------------------------------------------------
# Tests: Basis-Felder
# ---------------------------------------------------------------------------

class TestDictResponseMapperBasicFields:
    """Testet korrekte Abbildung der Basis-Felder."""

    def test_returns_dict(self):
        """Ergebnis ist ein dict."""
        result = _make_result()
        d = competitive_result_to_dict(result)
        assert isinstance(d, dict)

    def test_top_level_keys(self):
        """Alle erwarteten Top-Level-Keys sind vorhanden."""
        result = _make_result()
        d = competitive_result_to_dict(result)
        expected_keys = {
            "hhi_index", "hhi_level", "cr4_share", "top_actors",
            "network_edges", "network_nodes", "top3_share", "top10_share",
            "total_actors", "metadata",
        }
        assert expected_keys == set(d.keys())

    def test_hhi_level(self):
        """hhi_level wird korrekt aus level_en abgebildet."""
        result = _make_result(level_en="High")
        d = competitive_result_to_dict(result)
        assert d["hhi_level"] == "High"

    def test_total_actors(self):
        """total_actors wird korrekt uebertragen."""
        result = _make_result(total_actors=45)
        d = competitive_result_to_dict(result)
        assert d["total_actors"] == 45


# ---------------------------------------------------------------------------
# Tests: HHI und CR4 Rundung
# ---------------------------------------------------------------------------

class TestDictResponseMapperHhiCr4:
    """Testet HHI- und CR4-Rundung auf 4 Dezimalstellen."""

    def test_hhi_rounded(self):
        """HHI wird auf 4 Dezimalstellen gerundet."""
        result = _make_result(hhi=0.152345)
        d = competitive_result_to_dict(result)
        assert d["hhi_index"] == pytest.approx(0.1523, abs=0.00005)

    def test_cr4_rounded(self):
        """CR4 wird auf 4 Dezimalstellen gerundet."""
        result = _make_result(cr4_share=0.451289)
        d = competitive_result_to_dict(result)
        assert d["cr4_share"] == pytest.approx(0.4513, abs=0.00005)

    def test_top3_share_rounded(self):
        """top3_share wird auf 4 Dezimalstellen gerundet."""
        result = _make_result(top_3_share=0.567891)
        d = competitive_result_to_dict(result)
        assert d["top3_share"] == pytest.approx(0.5679, abs=0.00005)

    def test_top10_share_rounded(self):
        """top10_share wird auf 4 Dezimalstellen gerundet."""
        result = _make_result(top_10_share=0.823456)
        d = competitive_result_to_dict(result)
        assert d["top10_share"] == pytest.approx(0.8235, abs=0.00005)

    def test_hhi_zero(self):
        """HHI 0.0 wird korrekt durchgereicht."""
        result = _make_result(hhi=0.0)
        d = competitive_result_to_dict(result)
        assert d["hhi_index"] == 0.0

    def test_hhi_one(self):
        """HHI 1.0 (Monopol) wird korrekt durchgereicht."""
        result = _make_result(hhi=1.0)
        d = competitive_result_to_dict(result)
        assert d["hhi_index"] == 1.0


# ---------------------------------------------------------------------------
# Tests: Top Actors
# ---------------------------------------------------------------------------

class TestDictResponseMapperTopActors:
    """Testet Top-Akteur-Abbildung."""

    def test_top_actors_passed_through(self):
        """top_actors werden direkt durchgereicht."""
        result = _make_result()
        d = competitive_result_to_dict(result)
        assert len(d["top_actors"]) == 2
        assert d["top_actors"][0]["name"] == "SIEMENS AG"

    def test_top_actors_empty(self):
        """Leere top_actors werden korrekt durchgereicht."""
        result = _make_result(top_actors=[])
        d = competitive_result_to_dict(result)
        assert d["top_actors"] == []


# ---------------------------------------------------------------------------
# Tests: Netzwerk-Daten
# ---------------------------------------------------------------------------

class TestDictResponseMapperNetwork:
    """Testet Netzwerk-Daten-Abbildung."""

    def test_network_nodes_passed_through(self):
        """network_nodes werden direkt durchgereicht."""
        result = _make_result()
        d = competitive_result_to_dict(result)
        assert len(d["network_nodes"]) == 2

    def test_network_edges_passed_through(self):
        """network_edges werden direkt durchgereicht."""
        result = _make_result()
        d = competitive_result_to_dict(result)
        assert len(d["network_edges"]) == 1
        assert d["network_edges"][0]["source"] == "BOSCH GMBH"
        assert d["network_edges"][0]["target"] == "SIEMENS AG"

    def test_empty_network(self):
        """Leere Netzwerk-Daten werden korrekt durchgereicht."""
        result = _make_result(network_nodes=[], network_edges=[])
        d = competitive_result_to_dict(result)
        assert d["network_nodes"] == []
        assert d["network_edges"] == []


# ---------------------------------------------------------------------------
# Tests: Leere Daten
# ---------------------------------------------------------------------------

class TestDictResponseMapperEmptyData:
    """Testet Verhalten bei leeren/minimalen Daten."""

    def test_default_result(self):
        """Default-CompetitiveResult kann gemappt werden."""
        result = CompetitiveResult()
        d = competitive_result_to_dict(result)
        assert d["hhi_index"] == 0.0
        assert d["hhi_level"] == "Low"
        assert d["top_actors"] == []
        assert d["total_actors"] == 0


# ---------------------------------------------------------------------------
# Tests: Metadata
# ---------------------------------------------------------------------------

class TestDictResponseMapperMetadata:
    """Testet Metadata-Abbildung."""

    def test_processing_time(self):
        """processing_time_ms wird korrekt uebertragen."""
        result = _make_result(processing_time_ms=78)
        d = competitive_result_to_dict(result)
        assert d["metadata"]["processing_time_ms"] == 78

    def test_data_sources(self):
        """data_sources werden korrekt durchgereicht."""
        ds = [{"name": "Test", "type": "PATENT", "record_count": 500}]
        result = _make_result(data_sources=ds)
        d = competitive_result_to_dict(result)
        assert d["metadata"]["data_sources"] == ds

    def test_warnings_passed(self):
        """Warnings werden korrekt durchgereicht."""
        warnings = [{"message": "Test warning", "severity": "LOW", "code": "TEST"}]
        result = _make_result(warnings=warnings)
        d = competitive_result_to_dict(result)
        assert d["metadata"]["warnings"] == warnings

    def test_request_id_passed(self):
        """request_id wird in Metadata aufgenommen."""
        result = _make_result()
        d = competitive_result_to_dict(result, request_id="req-comp-1")
        assert d["metadata"]["request_id"] == "req-comp-1"

    def test_timestamp_present(self):
        """timestamp wird automatisch gesetzt."""
        result = _make_result()
        d = competitive_result_to_dict(result)
        assert "timestamp" in d["metadata"]
        assert isinstance(d["metadata"]["timestamp"], str)
