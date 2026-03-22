"""Domain-Modelle fuer Technology Intelligence.

Zentrale Datenstrukturen der Domain-Schicht. Diese Modelle sind
framework-unabhaengig definiert (nur Pydantic fuer Serialisierung)
und haben keine Abhaengigkeiten zu aeusseren Schichten (API, Infrastructure).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

# --- API Alerts ---

class ApiAlert(BaseModel):
    """API-Key/Token-Status-Warnung (Domain-Objekt)."""

    source: str = ""
    level: str = "warning"
    message: str = ""


# --- Panel-Modelle (UC1-UC8) ---

class LandscapePanel(BaseModel):
    """UC1: Landschaft-Panel."""

    total_patents: int = 0
    total_projects: int = 0
    total_publications: int = 0
    time_series: list[dict[str, Any]] = []
    top_countries: list[dict[str, Any]] = []
    analysis_text: str = ""


class MaturityPanel(BaseModel):
    """UC2: Reifegrad-Panel."""

    phase: str = ""
    phase_de: str = ""
    confidence: float = 0.0
    cagr: float = 0.0
    maturity_percent: float = 0.0
    saturation_level: float = 0.0
    inflection_year: float = 0.0
    r_squared: float = 0.0
    fit_model: str = ""
    time_series: list[dict[str, Any]] = []
    s_curve_fitted: list[dict[str, Any]] = []
    analysis_text: str = ""


class CompetitivePanel(BaseModel):
    """UC3: Wettbewerb-Panel."""

    hhi_index: float = 0.0
    concentration_level: str = ""
    top_actors: list[dict[str, Any]] = []
    top_3_share: float = 0.0

    # Netzwerk-Graph Daten (Force-Directed)
    network_nodes: list[dict[str, Any]] = []
    network_edges: list[dict[str, Any]] = []

    # Vollstaendige Akteur-Tabelle
    full_actors: list[dict[str, Any]] = []
    analysis_text: str = ""


class FundingPanel(BaseModel):
    """UC4: Foerderungs-Panel."""

    total_funding_eur: float = 0.0
    funding_cagr: float = 0.0
    funding_cagr_period: str = ""
    avg_project_size: float = 0.0
    by_programme: list[dict[str, Any]] = []
    time_series: list[dict[str, Any]] = []
    time_series_by_programme: list[dict[str, Any]] = []
    instrument_breakdown: list[dict[str, Any]] = []
    analysis_text: str = ""


class CpcFlowPanel(BaseModel):
    """UC5: CPC-Technologiefluss-Panel."""

    matrix: list[list[float]] = []
    labels: list[str] = []
    colors: list[str] = []
    total_patents_analyzed: int = 0
    total_connections: int = 0
    cpc_level: int = 4
    year_data: dict[str, Any] = {}
    cpc_descriptions: dict[str, str] = {}
    analysis_text: str = ""


class GeographicPanel(BaseModel):
    """UC6: Geografie-Panel."""

    total_countries: int = 0
    total_cities: int = 0
    cross_border_share: float = 0.0
    country_distribution: list[dict[str, Any]] = []
    city_distribution: list[dict[str, Any]] = []
    collaboration_pairs: list[dict[str, Any]] = []
    analysis_text: str = ""


class ResearchImpactPanel(BaseModel):
    """UC7: Research-Impact-Panel."""

    h_index: int = 0
    avg_citations: float = 0.0
    total_papers: int = 0
    influential_ratio: float = 0.0
    citation_trend: list[dict[str, Any]] = []
    top_papers: list[dict[str, Any]] = []
    top_venues: list[dict[str, Any]] = []
    publication_types: list[dict[str, Any]] = []
    analysis_text: str = ""


class TemporalPanel(BaseModel):
    """UC8: Temporal-Dynamik-Panel."""

    new_entrant_rate: float = 0.0
    persistence_rate: float = 0.0
    dominant_programme: str = ""
    actor_timeline: list[dict[str, Any]] = []
    programme_evolution: list[dict[str, Any]] = []
    entrant_persistence_trend: list[dict[str, Any]] = []
    instrument_evolution: list[dict[str, Any]] = []
    technology_breadth: list[dict[str, Any]] = []
    analysis_text: str = ""


class TechClusterPanel(BaseModel):
    """UC9: Internationaler Vergleich (EU vs. Global).

    Vergleicht europaeische und globale Metriken:
    Patente, Projekte, Akteure, Foerderung.
    """

    # EU-Metriken
    eu_patents: int = 0
    eu_projects: int = 0
    eu_actors: int = 0
    eu_funding_eur: float = 0.0
    eu_top_actors: list[dict[str, Any]] = []

    # Globale Metriken
    global_patents: int = 0
    global_projects: int = 0
    global_actors: int = 0
    global_top_actors: list[dict[str, Any]] = []

    # Anteil-Metriken (EU-Share %)
    eu_patent_share: float = 0.0
    eu_project_share: float = 0.0
    eu_actor_share: float = 0.0

    # Laendervergleich
    eu_top_countries: list[dict[str, Any]] = []
    global_top_countries: list[dict[str, Any]] = []

    analysis_text: str = ""


# --- Explainability ---

class ExplainabilityMetadata(BaseModel):
    """Transparenz-Metadaten fuer jede Analyse."""

    sources_used: list[str] = []
    methods: list[str] = []
    deterministic: bool = True
    warnings: list[str] = []
    api_alerts: list[ApiAlert] = []
    query_time_ms: int = 0
    data_complete_until: int | None = None
