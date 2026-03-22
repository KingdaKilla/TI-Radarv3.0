"""Unit-Tests fuer research-impact-svc dict_response Mapper.

Testet die Konvertierung von ResearchImpactResult in ein dict-basiertes
Response-Format fuer REST/JSON-Auslieferung.
"""

from __future__ import annotations

import pytest

from src.mappers.dict_response import research_impact_result_to_dict
from src.use_case import ResearchImpactResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(**overrides) -> ResearchImpactResult:
    """Erstellt ein ResearchImpactResult mit sinnvollen Standardwerten."""
    defaults = dict(
        h_index=12,
        avg_citations=8.5,
        median_citations=5.0,
        total_citations=850,
        total_publications=100,
        citation_trend=[
            {"year": 2020, "citations": 200},
            {"year": 2021, "citations": 300},
        ],
        top_papers=[
            {"title": "Paper A", "citations": 50},
            {"title": "Paper B", "citations": 30},
        ],
        top_venues=[
            {"venue": "Nature", "count": 10},
        ],
        publication_types=[
            {"type": "JournalArticle", "count": 80},
            {"type": "Conference", "count": 20},
        ],
        open_access_share=0.65,
        collaboration_rate=0.82,
        i10_index=8,
        top_institutions=[
            {"name": "Fraunhofer", "project_count": 15},
        ],
        warnings=[],
        data_sources=[
            {"name": "Semantic Scholar", "type": "PUBLICATION", "record_count": 100},
        ],
        processing_time_ms=42,
    )
    defaults.update(overrides)
    return ResearchImpactResult(**defaults)


# ---------------------------------------------------------------------------
# Tests: Grundstruktur
# ---------------------------------------------------------------------------

class TestDictResponseMapper:
    """Testet die Grundstruktur des Response-Dicts."""

    def test_returns_dict(self):
        result = _make_result()
        d = research_impact_result_to_dict(result)
        assert isinstance(d, dict)

    def test_top_level_keys(self):
        result = _make_result()
        d = research_impact_result_to_dict(result)
        expected_keys = {
            "h_index", "avg_citations", "median_citations",
            "total_citations", "total_publications",
            "citation_trend", "top_papers", "top_venues",
            "publication_types", "open_access_share",
            "collaboration_rate", "i10_index",
            "top_institutions", "metadata",
        }
        assert set(d.keys()) == expected_keys

    def test_metadata_keys(self):
        result = _make_result()
        d = research_impact_result_to_dict(result, request_id="req-123")
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

    def test_h_index(self):
        result = _make_result(h_index=25)
        d = research_impact_result_to_dict(result)
        assert d["h_index"] == 25

    def test_avg_citations(self):
        result = _make_result(avg_citations=12.3)
        d = research_impact_result_to_dict(result)
        assert d["avg_citations"] == pytest.approx(12.3)

    def test_median_citations(self):
        result = _make_result(median_citations=7.0)
        d = research_impact_result_to_dict(result)
        assert d["median_citations"] == pytest.approx(7.0)

    def test_total_citations(self):
        result = _make_result(total_citations=1234)
        d = research_impact_result_to_dict(result)
        assert d["total_citations"] == 1234

    def test_total_publications(self):
        result = _make_result(total_publications=50)
        d = research_impact_result_to_dict(result)
        assert d["total_publications"] == 50

    def test_open_access_share(self):
        result = _make_result(open_access_share=0.72)
        d = research_impact_result_to_dict(result)
        assert d["open_access_share"] == pytest.approx(0.72)

    def test_collaboration_rate(self):
        result = _make_result(collaboration_rate=0.91)
        d = research_impact_result_to_dict(result)
        assert d["collaboration_rate"] == pytest.approx(0.91)

    def test_i10_index(self):
        result = _make_result(i10_index=15)
        d = research_impact_result_to_dict(result)
        assert d["i10_index"] == 15

    def test_citation_trend_passthrough(self):
        trend = [{"year": 2020, "citations": 200}]
        result = _make_result(citation_trend=trend)
        d = research_impact_result_to_dict(result)
        assert d["citation_trend"] == trend

    def test_top_papers_passthrough(self):
        papers = [{"title": "X", "citations": 99}]
        result = _make_result(top_papers=papers)
        d = research_impact_result_to_dict(result)
        assert d["top_papers"] == papers

    def test_top_venues_passthrough(self):
        venues = [{"venue": "Science", "count": 5}]
        result = _make_result(top_venues=venues)
        d = research_impact_result_to_dict(result)
        assert d["top_venues"] == venues

    def test_publication_types_passthrough(self):
        types = [{"type": "JournalArticle", "count": 80}]
        result = _make_result(publication_types=types)
        d = research_impact_result_to_dict(result)
        assert d["publication_types"] == types

    def test_top_institutions_passthrough(self):
        insts = [{"name": "MIT", "project_count": 20}]
        result = _make_result(top_institutions=insts)
        d = research_impact_result_to_dict(result)
        assert d["top_institutions"] == insts


# ---------------------------------------------------------------------------
# Tests: Metadata
# ---------------------------------------------------------------------------

class TestMetadata:
    """Testet Metadata-Felder im Response-Dict."""

    def test_request_id_forwarded(self):
        result = _make_result()
        d = research_impact_result_to_dict(result, request_id="abc-456")
        assert d["metadata"]["request_id"] == "abc-456"

    def test_request_id_default_empty(self):
        result = _make_result()
        d = research_impact_result_to_dict(result)
        assert d["metadata"]["request_id"] == ""

    def test_processing_time_ms(self):
        result = _make_result(processing_time_ms=123)
        d = research_impact_result_to_dict(result)
        assert d["metadata"]["processing_time_ms"] == 123

    def test_data_sources_forwarded(self):
        sources = [{"name": "S2", "type": "PUBLICATION", "record_count": 50}]
        result = _make_result(data_sources=sources)
        d = research_impact_result_to_dict(result)
        assert d["metadata"]["data_sources"] == sources

    def test_warnings_forwarded(self):
        warnings = [{"message": "Test warning", "severity": "LOW", "code": "TEST"}]
        result = _make_result(warnings=warnings)
        d = research_impact_result_to_dict(result)
        assert d["metadata"]["warnings"] == warnings

    def test_timestamp_iso_format(self):
        result = _make_result()
        d = research_impact_result_to_dict(result)
        ts = d["metadata"]["timestamp"]
        assert isinstance(ts, str)
        # ISO format contains 'T' separator
        assert "T" in ts


# ---------------------------------------------------------------------------
# Tests: Leere / Grenzwerte
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Testet Randfaelle: leere Listen, Nullwerte."""

    def test_empty_lists(self):
        result = _make_result(
            citation_trend=[],
            top_papers=[],
            top_venues=[],
            publication_types=[],
            top_institutions=[],
        )
        d = research_impact_result_to_dict(result)
        assert d["citation_trend"] == []
        assert d["top_papers"] == []
        assert d["top_venues"] == []
        assert d["publication_types"] == []
        assert d["top_institutions"] == []

    def test_zero_values(self):
        result = _make_result(
            h_index=0,
            avg_citations=0.0,
            median_citations=0.0,
            total_citations=0,
            total_publications=0,
            open_access_share=0.0,
            collaboration_rate=0.0,
            i10_index=0,
        )
        d = research_impact_result_to_dict(result)
        assert d["h_index"] == 0
        assert d["avg_citations"] == 0.0
        assert d["total_citations"] == 0
        assert d["open_access_share"] == 0.0

    def test_default_result(self):
        result = ResearchImpactResult()
        d = research_impact_result_to_dict(result)
        assert d["h_index"] == 0
        assert d["total_publications"] == 0
        assert d["citation_trend"] == []
        assert d["metadata"]["processing_time_ms"] == 0
