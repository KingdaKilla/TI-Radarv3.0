"""Unit-Tests fuer publication-svc dict_response Mapper.

Testet die Konvertierung von PublicationResult in ein dict-basiertes
Response-Format fuer REST/JSON-Auslieferung.
"""

from __future__ import annotations

import pytest

from src.mappers.dict_response import publication_result_to_dict
from src.use_case import PublicationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(**overrides) -> PublicationResult:
    """Erstellt ein PublicationResult mit sinnvollen Standardwerten."""
    defaults = dict(
        total_publications=250,
        total_projects_with_pubs=80,
        publications_per_project=3.125,
        doi_coverage=0.78,
        pub_trend=[
            {"year": 2020, "count": 50},
            {"year": 2021, "count": 65},
            {"year": 2022, "count": 70},
        ],
        top_projects=[
            {
                "project_id": "P001",
                "acronym": "QUANTUM-EU",
                "publication_count": 15,
                "ec_contribution_eur": 2000000.0,
                "publications_per_million_eur": 7.5,
            },
        ],
        top_publications=[
            {
                "title": "Advances in Quantum Computing",
                "doi": "10.1234/example",
                "year": 2021,
            },
        ],
        warnings=[],
        data_sources=[
            {"name": "CORDIS Publications (PostgreSQL)", "type": "PUBLICATION", "record_count": 250},
        ],
        processing_time_ms=22,
    )
    defaults.update(overrides)
    return PublicationResult(**defaults)


# ---------------------------------------------------------------------------
# Tests: Grundstruktur
# ---------------------------------------------------------------------------

class TestDictResponseMapper:
    """Testet die Grundstruktur des Response-Dicts."""

    def test_returns_dict(self):
        result = _make_result()
        d = publication_result_to_dict(result)
        assert isinstance(d, dict)

    def test_top_level_keys(self):
        result = _make_result()
        d = publication_result_to_dict(result)
        expected_keys = {
            "total_publications", "total_projects_with_pubs",
            "publications_per_project", "doi_coverage",
            "pub_trend", "top_projects", "top_publications",
            "metadata",
        }
        assert set(d.keys()) == expected_keys

    def test_metadata_keys(self):
        result = _make_result()
        d = publication_result_to_dict(result, request_id="pub-001")
        meta = d["metadata"]
        assert "processing_time_ms" in meta
        assert "data_sources" in meta
        assert "warnings" in meta
        assert "request_id" in meta
        assert "timestamp" in meta


# ---------------------------------------------------------------------------
# Tests: Werte-Mapping
# ---------------------------------------------------------------------------

class TestFieldMapping:
    """Testet korrekte Zuordnung der Feldwerte."""

    def test_total_publications(self):
        result = _make_result(total_publications=500)
        d = publication_result_to_dict(result)
        assert d["total_publications"] == 500

    def test_total_projects_with_pubs(self):
        result = _make_result(total_projects_with_pubs=120)
        d = publication_result_to_dict(result)
        assert d["total_projects_with_pubs"] == 120

    def test_publications_per_project(self):
        result = _make_result(publications_per_project=4.2)
        d = publication_result_to_dict(result)
        assert d["publications_per_project"] == pytest.approx(4.2)

    def test_doi_coverage(self):
        result = _make_result(doi_coverage=0.85)
        d = publication_result_to_dict(result)
        assert d["doi_coverage"] == pytest.approx(0.85)

    def test_pub_trend_passthrough(self):
        trend = [{"year": 2023, "count": 90}]
        result = _make_result(pub_trend=trend)
        d = publication_result_to_dict(result)
        assert d["pub_trend"] == trend

    def test_top_projects_passthrough(self):
        projects = [{"project_id": "X", "publication_count": 20}]
        result = _make_result(top_projects=projects)
        d = publication_result_to_dict(result)
        assert d["top_projects"] == projects

    def test_top_publications_passthrough(self):
        pubs = [{"title": "Paper A", "doi": "10.xxx", "year": 2022}]
        result = _make_result(top_publications=pubs)
        d = publication_result_to_dict(result)
        assert d["top_publications"] == pubs


# ---------------------------------------------------------------------------
# Tests: Metadata
# ---------------------------------------------------------------------------

class TestMetadata:
    """Testet Metadata-Felder im Response-Dict."""

    def test_request_id_forwarded(self):
        result = _make_result()
        d = publication_result_to_dict(result, request_id="pub-abc")
        assert d["metadata"]["request_id"] == "pub-abc"

    def test_request_id_default_empty(self):
        result = _make_result()
        d = publication_result_to_dict(result)
        assert d["metadata"]["request_id"] == ""

    def test_processing_time_ms(self):
        result = _make_result(processing_time_ms=55)
        d = publication_result_to_dict(result)
        assert d["metadata"]["processing_time_ms"] == 55

    def test_data_sources_forwarded(self):
        sources = [{"name": "CORDIS", "type": "PUBLICATION", "record_count": 100}]
        result = _make_result(data_sources=sources)
        d = publication_result_to_dict(result)
        assert d["metadata"]["data_sources"] == sources

    def test_warnings_forwarded(self):
        warnings = [{"message": "Test", "severity": "LOW", "code": "T"}]
        result = _make_result(warnings=warnings)
        d = publication_result_to_dict(result)
        assert d["metadata"]["warnings"] == warnings

    def test_timestamp_iso_format(self):
        result = _make_result()
        d = publication_result_to_dict(result)
        ts = d["metadata"]["timestamp"]
        assert isinstance(ts, str)
        assert "T" in ts


# ---------------------------------------------------------------------------
# Tests: Leere / Grenzwerte
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Testet Randfaelle: leere Listen, Nullwerte, Default-Result."""

    def test_empty_lists(self):
        result = _make_result(
            pub_trend=[], top_projects=[], top_publications=[],
        )
        d = publication_result_to_dict(result)
        assert d["pub_trend"] == []
        assert d["top_projects"] == []
        assert d["top_publications"] == []

    def test_zero_values(self):
        result = _make_result(
            total_publications=0,
            total_projects_with_pubs=0,
            publications_per_project=0.0,
            doi_coverage=0.0,
        )
        d = publication_result_to_dict(result)
        assert d["total_publications"] == 0
        assert d["total_projects_with_pubs"] == 0
        assert d["publications_per_project"] == 0.0
        assert d["doi_coverage"] == 0.0

    def test_default_result(self):
        result = PublicationResult()
        d = publication_result_to_dict(result)
        assert d["total_publications"] == 0
        assert d["total_projects_with_pubs"] == 0
        assert d["publications_per_project"] == 0.0
        assert d["doi_coverage"] == 0.0
        assert d["pub_trend"] == []
        assert d["top_projects"] == []
        assert d["top_publications"] == []
        assert d["metadata"]["processing_time_ms"] == 0

    def test_high_doi_coverage(self):
        result = _make_result(doi_coverage=1.0)
        d = publication_result_to_dict(result)
        assert d["doi_coverage"] == pytest.approx(1.0)
