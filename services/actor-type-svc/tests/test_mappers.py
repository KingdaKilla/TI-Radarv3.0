"""Unit-Tests fuer actor-type-svc dict_response Mapper.

Testet die Konvertierung von ActorTypeResult in ein dict-basiertes
Response-Format fuer REST/JSON-Auslieferung.

Besonderer Fokus: Feld-Renaming (top_actors -> top_actors_by_type,
total_classified -> total_classified_actors).
"""

from __future__ import annotations

import pytest

from src.mappers.dict_response import actor_type_result_to_dict
from src.use_case import ActorTypeResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(**overrides) -> ActorTypeResult:
    """Erstellt ein ActorTypeResult mit sinnvollen Standardwerten."""
    defaults = dict(
        type_breakdown=[
            {"activity_type": "HES", "label": "Higher Education", "actor_count": 40, "share": 0.4},
            {"activity_type": "PRC", "label": "Private Company", "actor_count": 35, "share": 0.35},
            {"activity_type": "REC", "label": "Research Organisation", "actor_count": 25, "share": 0.25},
        ],
        type_trend=[
            {"year": 2020, "hes_count": 15, "prc_count": 12, "rec_count": 8, "oth_count": 2, "pub_count": 1, "total": 38},
            {"year": 2021, "hes_count": 18, "prc_count": 15, "rec_count": 10, "oth_count": 3, "pub_count": 2, "total": 48},
        ],
        top_actors=[
            {"name": "TU MUENCHEN", "activity_type": "HES", "project_count": 12},
            {"name": "SIEMENS AG", "activity_type": "PRC", "project_count": 10},
        ],
        total_classified=100,
        classification_coverage=0.85,
        sme_share=0.32,
        warnings=[],
        data_sources=[
            {"name": "CORDIS + Patent-Heuristik", "type": "PROJECT", "record_count": 100},
        ],
        processing_time_ms=30,
    )
    defaults.update(overrides)
    return ActorTypeResult(**defaults)


# ---------------------------------------------------------------------------
# Tests: Grundstruktur
# ---------------------------------------------------------------------------

class TestDictResponseMapper:
    """Testet die Grundstruktur des Response-Dicts."""

    def test_returns_dict(self):
        result = _make_result()
        d = actor_type_result_to_dict(result)
        assert isinstance(d, dict)

    def test_top_level_keys(self):
        result = _make_result()
        d = actor_type_result_to_dict(result)
        expected_keys = {
            "type_breakdown", "type_trend", "top_actors_by_type",
            "total_classified_actors", "classification_coverage",
            "sme_share", "metadata",
        }
        assert set(d.keys()) == expected_keys

    def test_metadata_keys(self):
        result = _make_result()
        d = actor_type_result_to_dict(result, request_id="at-001")
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

    - top_actors -> top_actors_by_type
    - total_classified -> total_classified_actors
    """

    def test_top_actors_renamed_to_top_actors_by_type(self):
        actors = [{"name": "MIT", "activity_type": "HES", "project_count": 20}]
        result = _make_result(top_actors=actors)
        d = actor_type_result_to_dict(result)
        assert d["top_actors_by_type"] == actors
        assert "top_actors" not in d

    def test_total_classified_renamed(self):
        result = _make_result(total_classified=150)
        d = actor_type_result_to_dict(result)
        assert d["total_classified_actors"] == 150
        assert "total_classified" not in d

    def test_type_breakdown_passthrough(self):
        data = [{"activity_type": "HES", "label": "Higher Education", "actor_count": 10, "share": 1.0}]
        result = _make_result(type_breakdown=data)
        d = actor_type_result_to_dict(result)
        assert d["type_breakdown"] == data

    def test_type_trend_passthrough(self):
        data = [{"year": 2022, "hes_count": 5, "prc_count": 3, "total": 8}]
        result = _make_result(type_trend=data)
        d = actor_type_result_to_dict(result)
        assert d["type_trend"] == data


# ---------------------------------------------------------------------------
# Tests: Scalar-Felder
# ---------------------------------------------------------------------------

class TestScalarFields:
    """Testet skalare Felder."""

    def test_classification_coverage(self):
        result = _make_result(classification_coverage=0.92)
        d = actor_type_result_to_dict(result)
        assert d["classification_coverage"] == pytest.approx(0.92)

    def test_sme_share(self):
        result = _make_result(sme_share=0.45)
        d = actor_type_result_to_dict(result)
        assert d["sme_share"] == pytest.approx(0.45)

    def test_sme_share_zero(self):
        result = _make_result(sme_share=0.0)
        d = actor_type_result_to_dict(result)
        assert d["sme_share"] == 0.0

    def test_classification_coverage_full(self):
        result = _make_result(classification_coverage=1.0)
        d = actor_type_result_to_dict(result)
        assert d["classification_coverage"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Tests: Metadata
# ---------------------------------------------------------------------------

class TestMetadata:
    """Testet Metadata-Felder im Response-Dict."""

    def test_request_id_forwarded(self):
        result = _make_result()
        d = actor_type_result_to_dict(result, request_id="at-xyz")
        assert d["metadata"]["request_id"] == "at-xyz"

    def test_request_id_default_empty(self):
        result = _make_result()
        d = actor_type_result_to_dict(result)
        assert d["metadata"]["request_id"] == ""

    def test_processing_time_ms(self):
        result = _make_result(processing_time_ms=66)
        d = actor_type_result_to_dict(result)
        assert d["metadata"]["processing_time_ms"] == 66

    def test_data_sources_forwarded(self):
        sources = [{"name": "CORDIS", "type": "PROJECT", "record_count": 80}]
        result = _make_result(data_sources=sources)
        d = actor_type_result_to_dict(result)
        assert d["metadata"]["data_sources"] == sources

    def test_warnings_forwarded(self):
        warnings = [{"message": "Test", "severity": "LOW", "code": "T1"}]
        result = _make_result(warnings=warnings)
        d = actor_type_result_to_dict(result)
        assert d["metadata"]["warnings"] == warnings

    def test_timestamp_iso_format(self):
        result = _make_result()
        d = actor_type_result_to_dict(result)
        assert "T" in d["metadata"]["timestamp"]


# ---------------------------------------------------------------------------
# Tests: Leere / Grenzwerte
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Testet Randfaelle: leere Listen, Default-Result."""

    def test_empty_lists(self):
        result = _make_result(
            type_breakdown=[], type_trend=[], top_actors=[],
        )
        d = actor_type_result_to_dict(result)
        assert d["type_breakdown"] == []
        assert d["type_trend"] == []
        assert d["top_actors_by_type"] == []

    def test_zero_classified(self):
        result = _make_result(total_classified=0)
        d = actor_type_result_to_dict(result)
        assert d["total_classified_actors"] == 0

    def test_default_result(self):
        result = ActorTypeResult()
        d = actor_type_result_to_dict(result)
        assert d["type_breakdown"] == []
        assert d["type_trend"] == []
        assert d["top_actors_by_type"] == []
        assert d["total_classified_actors"] == 0
        assert d["classification_coverage"] == pytest.approx(1.0)
        assert d["sme_share"] == 0.0
        assert d["metadata"]["processing_time_ms"] == 0
