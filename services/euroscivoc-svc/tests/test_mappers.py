"""Unit-Tests fuer euroscivoc-svc dict_response Mapper.

Testet die Konvertierung von EuroSciVocResult in ein dict-basiertes
Response-Format fuer REST/JSON-Auslieferung.

Besonderer Fokus: Feld-Renaming und interdisciplinarity-Objekt.
"""

from __future__ import annotations

import pytest

from src.mappers.dict_response import euroscivoc_result_to_dict
from src.use_case import EuroSciVocResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(**overrides) -> EuroSciVocResult:
    """Erstellt ein EuroSciVocResult mit sinnvollen Standardwerten."""
    defaults = dict(
        disciplines=[
            {"label": "Computer Science", "project_count": 50, "level": "FIELD"},
            {"label": "Mathematics", "project_count": 30, "level": "FIELD"},
        ],
        tree_roots=[],
        fields=[
            {"label": "Computer Science", "project_count": 50, "level": "FIELD"},
        ],
        links=[
            {"source": "Computer Science", "target": "Mathematics", "weight": 10},
        ],
        trend=[
            {"year": 2020, "discipline": "Computer Science", "count": 20},
            {"year": 2021, "discipline": "Computer Science", "count": 30},
        ],
        shannon=1.85,
        simpson=0.62,
        active_disciplines=5,
        active_fields=3,
        is_interdisciplinary=True,
        total_mapped=200,
        total_projects=250,
        mapping_coverage=0.80,
        warnings=[],
        data_sources=[
            {"name": "CORDIS EuroSciVoc (PostgreSQL)", "type": "PROJECT", "record_count": 200},
        ],
        processing_time_ms=28,
    )
    defaults.update(overrides)
    return EuroSciVocResult(**defaults)


# ---------------------------------------------------------------------------
# Tests: Grundstruktur
# ---------------------------------------------------------------------------

class TestDictResponseMapper:
    """Testet die Grundstruktur des Response-Dicts."""

    def test_returns_dict(self):
        result = _make_result()
        d = euroscivoc_result_to_dict(result)
        assert isinstance(d, dict)

    def test_top_level_keys(self):
        result = _make_result()
        d = euroscivoc_result_to_dict(result)
        expected_keys = {
            "disciplines", "fields_of_science", "disciplinary_links",
            "discipline_trend", "interdisciplinarity",
            "total_mapped_publications", "mapping_coverage",
            "metadata",
        }
        assert set(d.keys()) == expected_keys

    def test_metadata_keys(self):
        result = _make_result()
        d = euroscivoc_result_to_dict(result, request_id="esv-001")
        meta = d["metadata"]
        assert "processing_time_ms" in meta
        assert "data_sources" in meta
        assert "warnings" in meta
        assert "request_id" in meta
        assert "timestamp" in meta


# ---------------------------------------------------------------------------
# Tests: Feld-Renaming (dataclass -> dict key)
# ---------------------------------------------------------------------------

class TestFieldRenaming:
    """Testet korrekte Umbenennung der Felder fuer die API-Response.

    - fields -> fields_of_science
    - links -> disciplinary_links
    - trend -> discipline_trend
    - total_mapped -> total_mapped_publications
    """

    def test_fields_renamed_to_fields_of_science(self):
        data = [{"label": "Physics", "project_count": 20, "level": "FIELD"}]
        result = _make_result(fields=data)
        d = euroscivoc_result_to_dict(result)
        assert d["fields_of_science"] == data
        assert "fields" not in d

    def test_links_renamed_to_disciplinary_links(self):
        data = [{"source": "A", "target": "B", "weight": 5}]
        result = _make_result(links=data)
        d = euroscivoc_result_to_dict(result)
        assert d["disciplinary_links"] == data
        assert "links" not in d

    def test_trend_renamed_to_discipline_trend(self):
        data = [{"year": 2020, "discipline": "CS", "count": 10}]
        result = _make_result(trend=data)
        d = euroscivoc_result_to_dict(result)
        assert d["discipline_trend"] == data
        assert "trend" not in d

    def test_total_mapped_renamed(self):
        result = _make_result(total_mapped=300)
        d = euroscivoc_result_to_dict(result)
        assert d["total_mapped_publications"] == 300
        assert "total_mapped" not in d

    def test_disciplines_passthrough(self):
        data = [{"label": "Biology", "project_count": 15}]
        result = _make_result(disciplines=data)
        d = euroscivoc_result_to_dict(result)
        assert d["disciplines"] == data


# ---------------------------------------------------------------------------
# Tests: Interdisciplinarity-Objekt
# ---------------------------------------------------------------------------

class TestInterdisciplinarityObject:
    """Testet das geschachtelte interdisciplinarity-Objekt."""

    def test_interdisciplinarity_is_dict(self):
        result = _make_result()
        d = euroscivoc_result_to_dict(result)
        assert isinstance(d["interdisciplinarity"], dict)

    def test_interdisciplinarity_keys(self):
        result = _make_result()
        d = euroscivoc_result_to_dict(result)
        inter = d["interdisciplinarity"]
        expected_keys = {
            "shannon_index", "simpson_index",
            "active_disciplines", "active_fields",
            "is_interdisciplinary",
        }
        assert set(inter.keys()) == expected_keys

    def test_shannon_index(self):
        result = _make_result(shannon=2.15)
        d = euroscivoc_result_to_dict(result)
        assert d["interdisciplinarity"]["shannon_index"] == pytest.approx(2.15)

    def test_simpson_index(self):
        result = _make_result(simpson=0.75)
        d = euroscivoc_result_to_dict(result)
        assert d["interdisciplinarity"]["simpson_index"] == pytest.approx(0.75)

    def test_active_disciplines(self):
        result = _make_result(active_disciplines=8)
        d = euroscivoc_result_to_dict(result)
        assert d["interdisciplinarity"]["active_disciplines"] == 8

    def test_active_fields(self):
        result = _make_result(active_fields=4)
        d = euroscivoc_result_to_dict(result)
        assert d["interdisciplinarity"]["active_fields"] == 4

    def test_is_interdisciplinary_true(self):
        result = _make_result(is_interdisciplinary=True)
        d = euroscivoc_result_to_dict(result)
        assert d["interdisciplinarity"]["is_interdisciplinary"] is True

    def test_is_interdisciplinary_false(self):
        result = _make_result(is_interdisciplinary=False)
        d = euroscivoc_result_to_dict(result)
        assert d["interdisciplinarity"]["is_interdisciplinary"] is False


# ---------------------------------------------------------------------------
# Tests: Scalar-Felder
# ---------------------------------------------------------------------------

class TestScalarFields:
    """Testet skalare Felder."""

    def test_mapping_coverage(self):
        result = _make_result(mapping_coverage=0.85)
        d = euroscivoc_result_to_dict(result)
        assert d["mapping_coverage"] == pytest.approx(0.85)

    def test_mapping_coverage_zero(self):
        result = _make_result(mapping_coverage=0.0)
        d = euroscivoc_result_to_dict(result)
        assert d["mapping_coverage"] == 0.0

    def test_total_mapped_publications(self):
        result = _make_result(total_mapped=500)
        d = euroscivoc_result_to_dict(result)
        assert d["total_mapped_publications"] == 500


# ---------------------------------------------------------------------------
# Tests: Metadata
# ---------------------------------------------------------------------------

class TestMetadata:
    """Testet Metadata-Felder im Response-Dict."""

    def test_request_id_forwarded(self):
        result = _make_result()
        d = euroscivoc_result_to_dict(result, request_id="esv-abc")
        assert d["metadata"]["request_id"] == "esv-abc"

    def test_request_id_default_empty(self):
        result = _make_result()
        d = euroscivoc_result_to_dict(result)
        assert d["metadata"]["request_id"] == ""

    def test_processing_time_ms(self):
        result = _make_result(processing_time_ms=45)
        d = euroscivoc_result_to_dict(result)
        assert d["metadata"]["processing_time_ms"] == 45

    def test_timestamp_iso_format(self):
        result = _make_result()
        d = euroscivoc_result_to_dict(result)
        assert "T" in d["metadata"]["timestamp"]


# ---------------------------------------------------------------------------
# Tests: Leere / Grenzwerte
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Testet Randfaelle: leere Listen, Default-Result."""

    def test_empty_lists(self):
        result = _make_result(
            disciplines=[], fields=[], links=[], trend=[],
        )
        d = euroscivoc_result_to_dict(result)
        assert d["disciplines"] == []
        assert d["fields_of_science"] == []
        assert d["disciplinary_links"] == []
        assert d["discipline_trend"] == []

    def test_zero_metrics(self):
        result = _make_result(
            shannon=0.0, simpson=0.0,
            active_disciplines=0, active_fields=0,
            is_interdisciplinary=False,
            total_mapped=0, mapping_coverage=0.0,
        )
        d = euroscivoc_result_to_dict(result)
        assert d["interdisciplinarity"]["shannon_index"] == 0.0
        assert d["interdisciplinarity"]["simpson_index"] == 0.0
        assert d["total_mapped_publications"] == 0
        assert d["mapping_coverage"] == 0.0

    def test_default_result(self):
        result = EuroSciVocResult()
        d = euroscivoc_result_to_dict(result)
        assert d["disciplines"] == []
        assert d["fields_of_science"] == []
        assert d["interdisciplinarity"]["shannon_index"] == 0.0
        assert d["total_mapped_publications"] == 0
        assert d["metadata"]["processing_time_ms"] == 0
