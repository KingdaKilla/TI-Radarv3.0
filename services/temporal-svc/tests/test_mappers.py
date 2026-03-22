"""Unit-Tests fuer temporal-svc dict_response Mapper.

Testet die Konvertierung von TemporalResult in ein dict-basiertes
Response-Format fuer REST/JSON-Auslieferung.
"""

from __future__ import annotations

import pytest

from src.mappers.dict_response import temporal_result_to_dict
from src.use_case import TemporalResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(**overrides) -> TemporalResult:
    """Erstellt ein TemporalResult mit sinnvollen Standardwerten."""
    defaults = dict(
        entrant_persistence=[
            {"year": 2020, "new_entrants": 5, "persistent": 3, "exited": 1},
            {"year": 2021, "new_entrants": 3, "persistent": 6, "exited": 2},
        ],
        actor_timeline=[
            {"actor": "SIEMENS AG", "years": [2020, 2021, 2022], "total_count": 37},
        ],
        programme_evo=[
            {"scheme": "Horizon 2020", "year": 2020, "count": 5, "funding": 1000000.0},
        ],
        tech_breadth=[
            {"year": 2020, "unique_cpc_sections": 3, "unique_cpc_codes": 12},
        ],
        dynamics_summary={
            "total_actors": 10,
            "persistent_count": 4,
            "one_timer_count": 3,
            "avg_lifespan_years": 2.5,
            "median_lifespan_years": 2.0,
        },
        warnings=[],
        data_sources=[
            {"name": "EPO DOCDB (PostgreSQL)", "type": "PATENT", "record_count": 50},
        ],
        processing_time_ms=35,
    )
    defaults.update(overrides)
    return TemporalResult(**defaults)


# ---------------------------------------------------------------------------
# Tests: Grundstruktur
# ---------------------------------------------------------------------------

class TestDictResponseMapper:
    """Testet die Grundstruktur des Response-Dicts."""

    def test_returns_dict(self):
        result = _make_result()
        d = temporal_result_to_dict(result)
        assert isinstance(d, dict)

    def test_top_level_keys(self):
        result = _make_result()
        d = temporal_result_to_dict(result)
        expected_keys = {
            "entrant_persistence_trend", "actor_timeline",
            "programme_evolution", "technology_breadth",
            "dynamics_summary", "metadata",
        }
        assert set(d.keys()) == expected_keys

    def test_metadata_keys(self):
        result = _make_result()
        d = temporal_result_to_dict(result, request_id="req-001")
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

    Das Mapper-Modul benennt interne Felder zu API-kompatiblen Keys um:
    - entrant_persistence -> entrant_persistence_trend
    - programme_evo -> programme_evolution
    - tech_breadth -> technology_breadth
    """

    def test_entrant_persistence_renamed(self):
        data = [{"year": 2020, "new_entrants": 5}]
        result = _make_result(entrant_persistence=data)
        d = temporal_result_to_dict(result)
        assert d["entrant_persistence_trend"] == data
        assert "entrant_persistence" not in d

    def test_programme_evo_renamed(self):
        data = [{"scheme": "H2020", "year": 2020, "count": 3}]
        result = _make_result(programme_evo=data)
        d = temporal_result_to_dict(result)
        assert d["programme_evolution"] == data
        assert "programme_evo" not in d

    def test_tech_breadth_renamed(self):
        data = [{"year": 2020, "unique_cpc_sections": 4}]
        result = _make_result(tech_breadth=data)
        d = temporal_result_to_dict(result)
        assert d["technology_breadth"] == data
        assert "tech_breadth" not in d

    def test_actor_timeline_passthrough(self):
        data = [{"actor": "BOSCH", "years": [2020], "total_count": 5}]
        result = _make_result(actor_timeline=data)
        d = temporal_result_to_dict(result)
        assert d["actor_timeline"] == data

    def test_dynamics_summary_passthrough(self):
        summary = {"total_actors": 20, "persistent_count": 8,
                    "one_timer_count": 5, "avg_lifespan_years": 3.0,
                    "median_lifespan_years": 2.5}
        result = _make_result(dynamics_summary=summary)
        d = temporal_result_to_dict(result)
        assert d["dynamics_summary"] == summary


# ---------------------------------------------------------------------------
# Tests: Metadata
# ---------------------------------------------------------------------------

class TestMetadata:
    """Testet Metadata-Felder im Response-Dict."""

    def test_request_id_forwarded(self):
        result = _make_result()
        d = temporal_result_to_dict(result, request_id="xyz-789")
        assert d["metadata"]["request_id"] == "xyz-789"

    def test_request_id_default_empty(self):
        result = _make_result()
        d = temporal_result_to_dict(result)
        assert d["metadata"]["request_id"] == ""

    def test_processing_time_ms(self):
        result = _make_result(processing_time_ms=99)
        d = temporal_result_to_dict(result)
        assert d["metadata"]["processing_time_ms"] == 99

    def test_data_sources_forwarded(self):
        sources = [{"name": "CORDIS", "type": "PROJECT", "record_count": 20}]
        result = _make_result(data_sources=sources)
        d = temporal_result_to_dict(result)
        assert d["metadata"]["data_sources"] == sources

    def test_warnings_forwarded(self):
        warnings = [{"message": "Warnung", "severity": "LOW", "code": "W1"}]
        result = _make_result(warnings=warnings)
        d = temporal_result_to_dict(result)
        assert d["metadata"]["warnings"] == warnings

    def test_timestamp_iso_format(self):
        result = _make_result()
        d = temporal_result_to_dict(result)
        ts = d["metadata"]["timestamp"]
        assert isinstance(ts, str)
        assert "T" in ts


# ---------------------------------------------------------------------------
# Tests: Leere / Grenzwerte
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Testet Randfaelle: leere Listen, Default-Result."""

    def test_empty_lists(self):
        result = _make_result(
            entrant_persistence=[],
            actor_timeline=[],
            programme_evo=[],
            tech_breadth=[],
        )
        d = temporal_result_to_dict(result)
        assert d["entrant_persistence_trend"] == []
        assert d["actor_timeline"] == []
        assert d["programme_evolution"] == []
        assert d["technology_breadth"] == []

    def test_default_result(self):
        result = TemporalResult()
        d = temporal_result_to_dict(result)
        assert d["entrant_persistence_trend"] == []
        assert d["actor_timeline"] == []
        assert d["programme_evolution"] == []
        assert d["technology_breadth"] == []
        assert d["dynamics_summary"]["total_actors"] == 0
        assert d["metadata"]["processing_time_ms"] == 0

    def test_default_dynamics_summary(self):
        result = TemporalResult()
        d = temporal_result_to_dict(result)
        summary = d["dynamics_summary"]
        assert summary["persistent_count"] == 0
        assert summary["one_timer_count"] == 0
        assert summary["avg_lifespan_years"] == 0.0
