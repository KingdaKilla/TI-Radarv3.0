"""Tests fuer shared.domain.models — Pydantic Domain-Modelle."""

from __future__ import annotations

from shared.domain.models import (
    ApiAlert,
    CompetitivePanel,
    CpcFlowPanel,
    ExplainabilityMetadata,
    FundingPanel,
    GeographicPanel,
    LandscapePanel,
    MaturityPanel,
    ResearchImpactPanel,
    TechClusterPanel,
    TemporalPanel,
)


class TestApiAlert:
    def test_defaults(self):
        alert = ApiAlert()
        assert alert.source == ""
        assert alert.level == "warning"
        assert alert.message == ""

    def test_custom(self):
        alert = ApiAlert(source="OpenAIRE", level="error", message="Token abgelaufen")
        assert alert.source == "OpenAIRE"
        assert alert.level == "error"


class TestPanelModels:
    def test_landscape_defaults(self):
        panel = LandscapePanel()
        assert panel.total_patents == 0
        assert panel.time_series == []
        assert panel.analysis_text == ""

    def test_maturity_defaults(self):
        panel = MaturityPanel()
        assert panel.phase == ""
        assert panel.confidence == 0.0

    def test_competitive_defaults(self):
        panel = CompetitivePanel()
        assert panel.hhi_index == 0.0
        assert panel.network_nodes == []

    def test_funding_defaults(self):
        panel = FundingPanel()
        assert panel.total_funding_eur == 0.0

    def test_cpc_flow_defaults(self):
        panel = CpcFlowPanel()
        assert panel.matrix == []
        assert panel.labels == []

    def test_geographic_defaults(self):
        panel = GeographicPanel()
        assert panel.total_countries == 0

    def test_research_impact_defaults(self):
        panel = ResearchImpactPanel()
        assert panel.h_index == 0

    def test_temporal_defaults(self):
        panel = TemporalPanel()
        assert panel.new_entrant_rate == 0.0

    def test_tech_cluster_defaults(self):
        panel = TechClusterPanel()
        assert panel.eu_patents == 0
        assert panel.global_patents == 0


class TestExplainabilityMetadata:
    def test_defaults(self):
        meta = ExplainabilityMetadata()
        assert meta.deterministic is True
        assert meta.sources_used == []
        assert meta.methods == []

    def test_custom(self):
        meta = ExplainabilityMetadata(
            sources_used=["EPO", "CORDIS"],
            methods=["CAGR", "HHI"],
            deterministic=True,
            query_time_ms=150,
        )
        assert len(meta.sources_used) == 2
        assert meta.query_time_ms == 150


class TestPanelSerialization:
    def test_landscape_json_roundtrip(self):
        panel = LandscapePanel(total_patents=100, total_projects=50)
        data = panel.model_dump()
        restored = LandscapePanel(**data)
        assert restored.total_patents == 100
        assert restored.total_projects == 50

    def test_competitive_json_roundtrip(self):
        panel = CompetitivePanel(
            hhi_index=2500,
            top_actors=[{"name": "Test", "share": 0.5}],
        )
        data = panel.model_dump()
        restored = CompetitivePanel(**data)
        assert restored.hhi_index == 2500
        assert restored.top_actors[0]["name"] == "Test"
