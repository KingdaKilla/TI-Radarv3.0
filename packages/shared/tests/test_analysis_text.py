"""Tests fuer shared.domain.analysis_text — Deterministische Textgenerierung."""

from __future__ import annotations

from shared.domain.analysis_text import (
    _fmt_eur,
    _fmt_int,
    _fmt_pct,
    _trend_word,
    generate_competitive_text,
    generate_cpc_flow_text,
    generate_funding_text,
    generate_geographic_text,
    generate_landscape_text,
    generate_maturity_text,
    generate_research_impact_text,
    generate_tech_cluster_text,
    generate_temporal_text,
)
from shared.domain.models import (
    CompetitivePanel,
    CpcFlowPanel,
    FundingPanel,
    GeographicPanel,
    LandscapePanel,
    MaturityPanel,
    ResearchImpactPanel,
    TechClusterPanel,
    TemporalPanel,
)


# ============================================================================
# Formatierungshilfen
# ============================================================================


class TestFormatHelpers:
    def test_fmt_int(self):
        assert _fmt_int(1234) == "1.234"
        assert _fmt_int(0) == "0"
        assert _fmt_int(1_000_000) == "1.000.000"

    def test_fmt_pct(self):
        assert "67,3%" in _fmt_pct(67.3)
        assert "0,0%" in _fmt_pct(0.0)

    def test_fmt_eur_mrd(self):
        result = _fmt_eur(2_500_000_000)
        assert "Mrd" in result

    def test_fmt_eur_mio(self):
        result = _fmt_eur(5_000_000)
        assert "Mio" in result

    def test_fmt_eur_tsd(self):
        result = _fmt_eur(50_000)
        assert "Tsd" in result

    def test_fmt_eur_small(self):
        result = _fmt_eur(500)
        assert "EUR" in result

    def test_trend_word(self):
        assert "starkes Wachstum" in _trend_word(20)
        assert "solides" in _trend_word(10)
        assert "leichtes" in _trend_word(2)
        assert "Stagnation" in _trend_word(-2)
        assert "Rueckgang" in _trend_word(-10)


# ============================================================================
# UC1: Landscape Text
# ============================================================================


class TestGenerateLandscapeText:
    def test_empty_panel(self):
        panel = LandscapePanel()
        assert generate_landscape_text(panel) == ""

    def test_basic_text(self):
        panel = LandscapePanel(
            total_patents=1000,
            total_projects=200,
            total_publications=500,
            top_countries=[
                {"country": "DE", "total": 300},
                {"country": "FR", "total": 200},
            ],
        )
        text = generate_landscape_text(panel)
        assert "1.700" in text  # total
        assert "DE" in text
        assert len(text) > 50

    def test_dominant_source(self):
        panel = LandscapePanel(
            total_patents=900,
            total_projects=50,
            total_publications=50,
        )
        text = generate_landscape_text(panel)
        assert "Patente" in text


# ============================================================================
# UC2: Maturity Text
# ============================================================================


class TestGenerateMaturityText:
    def test_empty_panel(self):
        panel = MaturityPanel()
        assert generate_maturity_text(panel) == ""

    def test_emerging_phase(self):
        panel = MaturityPanel(
            phase="Emerging",
            phase_de="Aufkommend",
            maturity_percent=5.0,
            r_squared=0.8,
            fit_model="Logistic",
            confidence=0.7,
        )
        text = generate_maturity_text(panel)
        assert "Aufkommend" in text
        assert "Gao et al." in text


# ============================================================================
# UC3: Competitive Text
# ============================================================================


class TestGenerateCompetitiveText:
    def test_empty_panel(self):
        panel = CompetitivePanel()
        assert generate_competitive_text(panel) == ""

    def test_basic_text(self):
        panel = CompetitivePanel(
            hhi_index=2500,
            concentration_level="High",
            top_actors=[
                {"name": "Siemens", "share": 0.3, "count": 300},
                {"name": "Bosch", "share": 0.2, "count": 200},
            ],
            top_3_share=0.6,
        )
        text = generate_competitive_text(panel)
        assert "HHI" in text or "Herfindahl" in text
        assert "Siemens" in text


# ============================================================================
# UC4: Funding Text
# ============================================================================


class TestGenerateFundingText:
    def test_empty_panel(self):
        panel = FundingPanel()
        assert generate_funding_text(panel) == ""

    def test_basic_text(self):
        panel = FundingPanel(
            total_funding_eur=500_000_000,
            funding_cagr=12.5,
            avg_project_size=2_000_000,
            by_programme=[{"programme": "Horizon Europe", "funding": 300_000_000, "projects": 50}],
        )
        text = generate_funding_text(panel)
        assert "Mio" in text or "Mrd" in text
        assert "Horizon" in text


# ============================================================================
# UC5: CPC Flow Text
# ============================================================================


class TestGenerateCpcFlowText:
    def test_empty_panel(self):
        panel = CpcFlowPanel()
        assert generate_cpc_flow_text(panel) == ""

    def test_basic_text(self):
        panel = CpcFlowPanel(
            matrix=[[0, 0.3], [0.3, 0]],
            labels=["H01L", "G06N"],
            total_patents_analyzed=500,
            total_connections=1,
            cpc_level=4,
            cpc_descriptions={"H01L": "Semiconductor", "G06N": "Computing"},
        )
        text = generate_cpc_flow_text(panel)
        assert "500" in text
        assert "Jaccard" in text


# ============================================================================
# UC6: Geographic Text
# ============================================================================


class TestGenerateGeographicText:
    def test_empty_panel(self):
        panel = GeographicPanel()
        assert generate_geographic_text(panel) == ""

    def test_basic_text(self):
        panel = GeographicPanel(
            total_countries=25,
            total_cities=100,
            cross_border_share=0.7,
            country_distribution=[
                {"country": "DE", "total": 500},
                {"country": "FR", "total": 300},
                {"country": "IT", "total": 200},
            ],
        )
        text = generate_geographic_text(panel)
        assert "25" in text
        assert "DE" in text


# ============================================================================
# UC7: Research Impact Text
# ============================================================================


class TestGenerateResearchImpactText:
    def test_empty_panel(self):
        panel = ResearchImpactPanel()
        assert generate_research_impact_text(panel) == ""

    def test_basic_text(self):
        panel = ResearchImpactPanel(
            h_index=25,
            avg_citations=15.3,
            total_papers=200,
            top_papers=[{"title": "Test Paper", "citations": 500, "year": 2020}],
            top_venues=[{"venue": "Nature", "count": 10}],
        )
        text = generate_research_impact_text(panel)
        assert "h-Index" in text
        assert "25" in text
        assert "Banks" in text


# ============================================================================
# UC8: Temporal Text
# ============================================================================


class TestGenerateTemporalText:
    def test_empty_panel(self):
        panel = TemporalPanel()
        assert generate_temporal_text(panel) == ""

    def test_basic_text(self):
        panel = TemporalPanel(
            new_entrant_rate=0.35,
            persistence_rate=0.65,
            entrant_persistence_trend=[
                {"year": 2020, "new_entrant_rate": 0.4},
                {"year": 2021, "new_entrant_rate": 0.35},
                {"year": 2022, "new_entrant_rate": 0.3},
            ],
        )
        text = generate_temporal_text(panel)
        assert "Neueintrittrate" in text
        assert "Malerba" in text


# ============================================================================
# UC9: Tech Cluster Text
# ============================================================================


class TestGenerateTechClusterText:
    def test_empty_panel(self):
        panel = TechClusterPanel()
        assert generate_tech_cluster_text(panel) == ""

    def test_basic_text(self):
        panel = TechClusterPanel(
            eu_patents=500,
            global_patents=2000,
            eu_patent_share=0.25,
            eu_actors=100,
            global_actors=400,
            eu_actor_share=0.25,
        )
        text = generate_tech_cluster_text(panel)
        assert "25" in text
        assert "EU" in text
