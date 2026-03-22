"""Unit-Tests fuer cpc-flow-svc Mapper-Module (dict_response.py).

Testet die korrekte Abbildung von CpcFlowResult auf das dict-basierte
Response-Format, inkl. Jaccard-Matrix, Top-Pairs, Chord-Daten und
CPC-Codes-Info.
"""

from __future__ import annotations

import pytest

from src.mappers.dict_response import cpc_flow_result_to_dict
from src.use_case import CpcFlowResult


# ---------------------------------------------------------------------------
# Fixture Helper
# ---------------------------------------------------------------------------

def _make_result(**overrides: object) -> CpcFlowResult:
    """Erstellt ein CpcFlowResult mit sinnvollen Defaults."""
    defaults: dict = {
        "labels": ["H04W", "G06N", "H04L"],
        "matrix": [
            [1.0, 0.25, 0.10],
            [0.25, 1.0, 0.15],
            [0.10, 0.15, 1.0],
        ],
        "total_connections": 42,
        "total_patents": 500,
        "cpc_codes_info": [
            {"code": "H04W", "description": "Wireless", "patent_count": 200, "section": "H"},
            {"code": "G06N", "description": "AI/ML", "patent_count": 180, "section": "G"},
            {"code": "H04L", "description": "Digital Networks", "patent_count": 120, "section": "H"},
        ],
        "top_pairs": [
            {"code_a": "H04W", "code_b": "G06N", "similarity": 0.25},
            {"code_a": "G06N", "code_b": "H04L", "similarity": 0.15},
            {"code_a": "H04W", "code_b": "H04L", "similarity": 0.10},
        ],
        "year_data_entries": [
            {"year": 2020, "active_codes": 3, "avg_similarity": 0.17, "max_similarity": 0.25, "patent_count": 150},
            {"year": 2024, "active_codes": 3, "avg_similarity": 0.20, "max_similarity": 0.30, "patent_count": 350},
        ],
        "chord_data": [
            {"source": "H04W", "target": "G06N", "value": 250, "source_label": "H04W", "target_label": "G06N"},
            {"source": "G06N", "target": "H04L", "value": 150, "source_label": "G06N", "target_label": "H04L"},
        ],
        "similarity_threshold": 0.01,
        "warnings": [],
        "data_sources": [
            {"name": "EPO DOCDB (PostgreSQL)", "type": "PATENT", "record_count": 500},
        ],
        "processing_time_ms": 92,
    }
    defaults.update(overrides)
    return CpcFlowResult(**defaults)


# ---------------------------------------------------------------------------
# Tests: Basis-Felder
# ---------------------------------------------------------------------------

class TestDictResponseMapperBasicFields:
    """Testet korrekte Abbildung der Basis-Felder."""

    def test_returns_dict(self):
        """Ergebnis ist ein dict."""
        result = _make_result()
        d = cpc_flow_result_to_dict(result)
        assert isinstance(d, dict)

    def test_top_level_keys(self):
        """Alle erwarteten Top-Level-Keys sind vorhanden."""
        result = _make_result()
        d = cpc_flow_result_to_dict(result)
        expected_keys = {
            "labels", "matrix", "total_connections", "total_patents",
            "cpc_codes_info", "top_pairs", "year_data_entries",
            "chord_data", "similarity_threshold", "metadata",
        }
        assert expected_keys == set(d.keys())

    def test_total_connections(self):
        """total_connections wird korrekt uebertragen."""
        result = _make_result(total_connections=42)
        d = cpc_flow_result_to_dict(result)
        assert d["total_connections"] == 42

    def test_total_patents(self):
        """total_patents wird korrekt uebertragen."""
        result = _make_result(total_patents=500)
        d = cpc_flow_result_to_dict(result)
        assert d["total_patents"] == 500

    def test_similarity_threshold(self):
        """similarity_threshold wird korrekt uebertragen."""
        result = _make_result(similarity_threshold=0.05)
        d = cpc_flow_result_to_dict(result)
        assert d["similarity_threshold"] == pytest.approx(0.05, abs=0.001)


# ---------------------------------------------------------------------------
# Tests: Labels und Matrix
# ---------------------------------------------------------------------------

class TestDictResponseMapperLabelsMatrix:
    """Testet Labels und Matrix Abbildung."""

    def test_labels_passed_through(self):
        """labels werden direkt durchgereicht."""
        result = _make_result()
        d = cpc_flow_result_to_dict(result)
        assert d["labels"] == ["H04W", "G06N", "H04L"]

    def test_matrix_passed_through(self):
        """matrix wird direkt durchgereicht."""
        result = _make_result()
        d = cpc_flow_result_to_dict(result)
        assert len(d["matrix"]) == 3
        assert len(d["matrix"][0]) == 3
        assert d["matrix"][0][1] == pytest.approx(0.25, abs=0.01)

    def test_matrix_diagonal_one(self):
        """Diagonale der Jaccard-Matrix ist 1.0."""
        result = _make_result()
        d = cpc_flow_result_to_dict(result)
        for i in range(3):
            assert d["matrix"][i][i] == pytest.approx(1.0, abs=0.001)

    def test_matrix_symmetric(self):
        """Matrix ist symmetrisch: matrix[i][j] == matrix[j][i]."""
        result = _make_result()
        d = cpc_flow_result_to_dict(result)
        n = len(d["matrix"])
        for i in range(n):
            for j in range(n):
                assert d["matrix"][i][j] == pytest.approx(d["matrix"][j][i], abs=0.001)


# ---------------------------------------------------------------------------
# Tests: Top Pairs
# ---------------------------------------------------------------------------

class TestDictResponseMapperTopPairs:
    """Testet Top-Pairs Abbildung."""

    def test_top_pairs_passed_through(self):
        """top_pairs werden direkt durchgereicht."""
        result = _make_result()
        d = cpc_flow_result_to_dict(result)
        assert len(d["top_pairs"]) == 3

    def test_top_pairs_fields(self):
        """Jedes Top-Pair hat code_a, code_b, similarity."""
        result = _make_result()
        d = cpc_flow_result_to_dict(result)
        pair = d["top_pairs"][0]
        assert "code_a" in pair
        assert "code_b" in pair
        assert "similarity" in pair

    def test_top_pairs_empty(self):
        """Leere top_pairs werden korrekt durchgereicht."""
        result = _make_result(top_pairs=[])
        d = cpc_flow_result_to_dict(result)
        assert d["top_pairs"] == []


# ---------------------------------------------------------------------------
# Tests: CPC Codes Info
# ---------------------------------------------------------------------------

class TestDictResponseMapperCpcCodesInfo:
    """Testet CPC-Codes-Info Abbildung."""

    def test_cpc_codes_info_passed_through(self):
        """cpc_codes_info werden direkt durchgereicht."""
        result = _make_result()
        d = cpc_flow_result_to_dict(result)
        assert len(d["cpc_codes_info"]) == 3
        assert d["cpc_codes_info"][0]["code"] == "H04W"
        assert d["cpc_codes_info"][0]["description"] == "Wireless"

    def test_cpc_codes_info_empty(self):
        """Leere cpc_codes_info werden korrekt durchgereicht."""
        result = _make_result(cpc_codes_info=[])
        d = cpc_flow_result_to_dict(result)
        assert d["cpc_codes_info"] == []


# ---------------------------------------------------------------------------
# Tests: Year Data und Chord Data
# ---------------------------------------------------------------------------

class TestDictResponseMapperYearAndChord:
    """Testet Year-Data und Chord-Data Abbildung."""

    def test_year_data_passed_through(self):
        """year_data_entries werden direkt durchgereicht."""
        result = _make_result()
        d = cpc_flow_result_to_dict(result)
        assert len(d["year_data_entries"]) == 2

    def test_chord_data_passed_through(self):
        """chord_data werden direkt durchgereicht."""
        result = _make_result()
        d = cpc_flow_result_to_dict(result)
        assert len(d["chord_data"]) == 2
        assert d["chord_data"][0]["source"] == "H04W"
        assert d["chord_data"][0]["target"] == "G06N"

    def test_empty_year_and_chord(self):
        """Leere year_data und chord_data werden korrekt durchgereicht."""
        result = _make_result(year_data_entries=[], chord_data=[])
        d = cpc_flow_result_to_dict(result)
        assert d["year_data_entries"] == []
        assert d["chord_data"] == []


# ---------------------------------------------------------------------------
# Tests: Leere Daten
# ---------------------------------------------------------------------------

class TestDictResponseMapperEmptyData:
    """Testet Verhalten bei leeren/minimalen Daten."""

    def test_empty_labels_and_matrix(self):
        """Leere labels und matrix werden korrekt durchgereicht."""
        result = _make_result(labels=[], matrix=[])
        d = cpc_flow_result_to_dict(result)
        assert d["labels"] == []
        assert d["matrix"] == []

    def test_default_result(self):
        """Default-CpcFlowResult kann gemappt werden."""
        result = CpcFlowResult()
        d = cpc_flow_result_to_dict(result)
        assert d["labels"] == []
        assert d["matrix"] == []
        assert d["total_connections"] == 0
        assert d["total_patents"] == 0
        assert d["similarity_threshold"] == 0.0


# ---------------------------------------------------------------------------
# Tests: Metadata
# ---------------------------------------------------------------------------

class TestDictResponseMapperMetadata:
    """Testet Metadata-Abbildung."""

    def test_processing_time(self):
        """processing_time_ms wird korrekt uebertragen."""
        result = _make_result(processing_time_ms=92)
        d = cpc_flow_result_to_dict(result)
        assert d["metadata"]["processing_time_ms"] == 92

    def test_data_sources(self):
        """data_sources werden korrekt durchgereicht."""
        ds = [{"name": "EPO DOCDB", "type": "PATENT", "record_count": 500}]
        result = _make_result(data_sources=ds)
        d = cpc_flow_result_to_dict(result)
        assert d["metadata"]["data_sources"] == ds

    def test_request_id_passed(self):
        """request_id wird in Metadata aufgenommen."""
        result = _make_result()
        d = cpc_flow_result_to_dict(result, request_id="req-cpc-3")
        assert d["metadata"]["request_id"] == "req-cpc-3"

    def test_timestamp_present(self):
        """timestamp wird automatisch gesetzt."""
        result = _make_result()
        d = cpc_flow_result_to_dict(result)
        assert "timestamp" in d["metadata"]
        assert isinstance(d["metadata"]["timestamp"], str)
