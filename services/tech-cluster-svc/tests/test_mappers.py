"""Unit-Tests fuer tech-cluster-svc dict_response Mapper.

Testet die Konvertierung von TechClusterResult in ein dict-basiertes
Response-Format fuer REST/JSON-Auslieferung.

Besonderer Fokus: CAGR-Normalisierung (/ 100) im Mapper.
"""

from __future__ import annotations

import pytest

from src.mappers.dict_response import tech_cluster_result_to_dict
from src.use_case import TechClusterResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(**overrides) -> TechClusterResult:
    """Erstellt ein TechClusterResult mit sinnvollen Standardwerten."""
    defaults = dict(
        clusters=[
            {
                "cluster_id": 0,
                "label": "CPC Section H",
                "cpc_codes": ["H04L", "H04W"],
                "dominant_topics": ["H04L"],
                "actor_count": 25,
                "patent_count": 120,
                "density": 0.6321,
                "coherence": 0.45,
                "cagr": 15.0,
            },
            {
                "cluster_id": 1,
                "label": "CPC Section G",
                "cpc_codes": ["G06F", "G06N"],
                "dominant_topics": ["G06F"],
                "actor_count": 18,
                "patent_count": 85,
                "density": 0.5123,
                "coherence": 0.38,
                "cagr": -5.0,
            },
        ],
        actor_cpc_links=[
            {"actor": "SIEMENS AG", "cpc_code": "H04L", "count": 10},
        ],
        total_actors=40,
        total_cpc_codes=15,
        quality={
            "avg_silhouette": 0.35,
            "num_clusters": 2,
            "algorithm": "cpc_section_grouping",
            "modularity": 0.0,
        },
        warnings=[],
        data_sources=[
            {"name": "EPO DOCDB (PostgreSQL)", "type": "PATENT", "record_count": 200},
        ],
        processing_time_ms=55,
    )
    defaults.update(overrides)
    return TechClusterResult(**defaults)


# ---------------------------------------------------------------------------
# Tests: Grundstruktur
# ---------------------------------------------------------------------------

class TestDictResponseMapper:
    """Testet die Grundstruktur des Response-Dicts."""

    def test_returns_dict(self):
        result = _make_result()
        d = tech_cluster_result_to_dict(result)
        assert isinstance(d, dict)

    def test_top_level_keys(self):
        result = _make_result()
        d = tech_cluster_result_to_dict(result)
        expected_keys = {
            "clusters", "actor_cpc_links", "total_actors",
            "total_cpc_codes", "quality", "metadata",
        }
        assert set(d.keys()) == expected_keys

    def test_metadata_keys(self):
        result = _make_result()
        d = tech_cluster_result_to_dict(result, request_id="req-tc")
        meta = d["metadata"]
        assert "processing_time_ms" in meta
        assert "data_sources" in meta
        assert "warnings" in meta
        assert "request_id" in meta
        assert "timestamp" in meta


# ---------------------------------------------------------------------------
# Tests: CAGR-Normalisierung (/ 100)
# ---------------------------------------------------------------------------

class TestCagrNormalization:
    """Testet die CAGR-Normalisierung von Prozent auf Fraktion.

    Convention: Backend liefert CAGR als Prozentwert (z.B. 15.0 fuer 15%).
    Der dict_response Mapper teilt durch 100: 15.0 -> 0.15.
    Frontend formatPercent() multipliziert dann wieder x100.
    """

    def test_positive_cagr_normalized(self):
        result = _make_result(clusters=[
            {"cluster_id": 0, "label": "H", "cagr": 15.0,
             "cpc_codes": [], "dominant_topics": [], "actor_count": 1,
             "patent_count": 1, "density": 0.5, "coherence": 0.4},
        ])
        d = tech_cluster_result_to_dict(result)
        assert d["clusters"][0]["cagr"] == pytest.approx(0.15, abs=0.001)

    def test_negative_cagr_normalized(self):
        result = _make_result(clusters=[
            {"cluster_id": 0, "label": "G", "cagr": -5.0,
             "cpc_codes": [], "dominant_topics": [], "actor_count": 1,
             "patent_count": 1, "density": 0.3, "coherence": 0.2},
        ])
        d = tech_cluster_result_to_dict(result)
        assert d["clusters"][0]["cagr"] == pytest.approx(-0.05, abs=0.001)

    def test_zero_cagr(self):
        result = _make_result(clusters=[
            {"cluster_id": 0, "label": "A", "cagr": 0.0,
             "cpc_codes": [], "dominant_topics": [], "actor_count": 1,
             "patent_count": 1, "density": 0.0, "coherence": 0.0},
        ])
        d = tech_cluster_result_to_dict(result)
        assert d["clusters"][0]["cagr"] == pytest.approx(0.0)

    def test_large_cagr_normalized(self):
        result = _make_result(clusters=[
            {"cluster_id": 0, "label": "B", "cagr": 150.0,
             "cpc_codes": [], "dominant_topics": [], "actor_count": 1,
             "patent_count": 1, "density": 0.5, "coherence": 0.5},
        ])
        d = tech_cluster_result_to_dict(result)
        assert d["clusters"][0]["cagr"] == pytest.approx(1.50, abs=0.001)

    def test_multiple_clusters_each_normalized(self):
        result = _make_result()  # default has two clusters: cagr=15.0 and cagr=-5.0
        d = tech_cluster_result_to_dict(result)
        assert d["clusters"][0]["cagr"] == pytest.approx(0.15, abs=0.001)
        assert d["clusters"][1]["cagr"] == pytest.approx(-0.05, abs=0.001)

    def test_missing_cagr_defaults_to_zero(self):
        """Cluster ohne cagr-Key bekommt 0.0 / 100 = 0.0."""
        result = _make_result(clusters=[
            {"cluster_id": 0, "label": "X",
             "cpc_codes": [], "dominant_topics": [], "actor_count": 1,
             "patent_count": 1, "density": 0.0, "coherence": 0.0},
        ])
        d = tech_cluster_result_to_dict(result)
        assert d["clusters"][0]["cagr"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests: Cluster-Felder (nicht-CAGR)
# ---------------------------------------------------------------------------

class TestClusterFields:
    """Testet dass nicht-CAGR Cluster-Felder unveraendert durchgereicht werden."""

    def test_cluster_id_preserved(self):
        result = _make_result()
        d = tech_cluster_result_to_dict(result)
        assert d["clusters"][0]["cluster_id"] == 0

    def test_label_preserved(self):
        result = _make_result()
        d = tech_cluster_result_to_dict(result)
        assert d["clusters"][0]["label"] == "CPC Section H"

    def test_cpc_codes_preserved(self):
        result = _make_result()
        d = tech_cluster_result_to_dict(result)
        assert d["clusters"][0]["cpc_codes"] == ["H04L", "H04W"]

    def test_dominant_topics_preserved(self):
        result = _make_result()
        d = tech_cluster_result_to_dict(result)
        assert d["clusters"][0]["dominant_topics"] == ["H04L"]

    def test_density_preserved(self):
        result = _make_result()
        d = tech_cluster_result_to_dict(result)
        assert d["clusters"][0]["density"] == pytest.approx(0.6321)

    def test_coherence_preserved(self):
        result = _make_result()
        d = tech_cluster_result_to_dict(result)
        assert d["clusters"][0]["coherence"] == pytest.approx(0.45)


# ---------------------------------------------------------------------------
# Tests: Scalar-Felder
# ---------------------------------------------------------------------------

class TestScalarFields:
    """Testet skalare Felder (total_actors, total_cpc_codes, quality)."""

    def test_total_actors(self):
        result = _make_result(total_actors=42)
        d = tech_cluster_result_to_dict(result)
        assert d["total_actors"] == 42

    def test_total_cpc_codes(self):
        result = _make_result(total_cpc_codes=18)
        d = tech_cluster_result_to_dict(result)
        assert d["total_cpc_codes"] == 18

    def test_quality_passthrough(self):
        quality = {"avg_silhouette": 0.5, "num_clusters": 3,
                    "algorithm": "cpc_section_grouping", "modularity": 0.1}
        result = _make_result(quality=quality)
        d = tech_cluster_result_to_dict(result)
        assert d["quality"] == quality

    def test_actor_cpc_links_passthrough(self):
        links = [{"actor": "BOSCH", "cpc_code": "G06F", "count": 5}]
        result = _make_result(actor_cpc_links=links)
        d = tech_cluster_result_to_dict(result)
        assert d["actor_cpc_links"] == links


# ---------------------------------------------------------------------------
# Tests: Metadata
# ---------------------------------------------------------------------------

class TestMetadata:
    """Testet Metadata-Felder im Response-Dict."""

    def test_request_id_forwarded(self):
        result = _make_result()
        d = tech_cluster_result_to_dict(result, request_id="tc-001")
        assert d["metadata"]["request_id"] == "tc-001"

    def test_processing_time_ms(self):
        result = _make_result(processing_time_ms=77)
        d = tech_cluster_result_to_dict(result)
        assert d["metadata"]["processing_time_ms"] == 77

    def test_timestamp_iso_format(self):
        result = _make_result()
        d = tech_cluster_result_to_dict(result)
        assert "T" in d["metadata"]["timestamp"]


# ---------------------------------------------------------------------------
# Tests: Leere / Grenzwerte
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Testet Randfaelle: leere Cluster-Liste, Default-Result."""

    def test_empty_clusters(self):
        result = _make_result(clusters=[])
        d = tech_cluster_result_to_dict(result)
        assert d["clusters"] == []

    def test_empty_actor_cpc_links(self):
        result = _make_result(actor_cpc_links=[])
        d = tech_cluster_result_to_dict(result)
        assert d["actor_cpc_links"] == []

    def test_default_result(self):
        result = TechClusterResult()
        d = tech_cluster_result_to_dict(result)
        assert d["clusters"] == []
        assert d["total_actors"] == 0
        assert d["total_cpc_codes"] == 0
        assert d["metadata"]["processing_time_ms"] == 0
