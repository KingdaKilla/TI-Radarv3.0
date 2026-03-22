"""Domain layer — deterministic metrics, models, and pure functions.

Re-exports key items for convenient access:

    from shared.domain import cagr, hhi_index, fit_best_model
    from shared.domain import LandscapePanel, MaturityPanel, ApiAlert
"""

from __future__ import annotations

# --- Metrics (pure functions) ---
from shared.domain.metrics import (
    cagr,
    classify_maturity_phase,
    hhi_concentration_level,
    hhi_index,
    merge_country_data,
    merge_time_series,
    s_curve_confidence,
    yoy_growth,
)

# --- S-Curve fitting ---
from shared.domain.scurve import (
    fit_best_model,
    fit_gompertz,
    fit_s_curve,
    gompertz_function,
    logistic_function,
)

# --- CPC flow (Jaccard) ---
from shared.domain.cpc_flow import (
    assign_colors,
    build_cooccurrence,
    build_cooccurrence_with_years,
    build_jaccard_from_sql,
    build_year_data_from_aggregates,
    extract_cpc_sets,
    extract_cpc_sets_with_years,
    normalize_cpc,
)

# --- Research metrics ---
from shared.domain.research_metrics import (
    _compute_citation_trend,
    _compute_h_index,
    _compute_publication_types,
    _compute_top_papers,
    _compute_venue_distribution,
)

# --- Temporal metrics ---
from shared.domain.temporal_metrics import (
    _compute_actor_dynamics,
    _compute_actor_timeline,
    _compute_programme_evolution,
    _compute_technology_breadth,
)

# --- Sampling ---
from shared.domain.sampling import (
    JaccardConfidence,
    SamplingResult,
    StratumInfo,
    estimate_jaccard_confidence,
    stratified_sample,
)

# --- CPC descriptions ---
from shared.domain.cpc_descriptions import (
    CPC_CLASS_DESCRIPTIONS,
    CPC_SECTION_DESCRIPTIONS,
    CPC_SUBCLASS_DESCRIPTIONS,
    describe_cpc,
)

# --- EU countries ---
from shared.domain.eu_countries import EU_EEA_COUNTRIES, is_european

# --- Domain models ---
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

# --- Analysis text generation ---
from shared.domain.analysis_text import (
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

# --- Entity resolution ---
from shared.domain.entity_resolution import (
    find_matches,
    generate_blocking_key,
    levenshtein_similarity,
    normalize_actor_name,
    tfidf_cosine_similarity,
)

# --- API health ---
from shared.domain.api_health import (
    check_jwt_expiry,
    detect_runtime_failures,
)

__all__ = [
    # metrics
    "cagr",
    "hhi_index",
    "hhi_concentration_level",
    "s_curve_confidence",
    "classify_maturity_phase",
    "yoy_growth",
    "merge_time_series",
    "merge_country_data",
    # scurve
    "logistic_function",
    "gompertz_function",
    "fit_s_curve",
    "fit_gompertz",
    "fit_best_model",
    # cpc_flow
    "normalize_cpc",
    "extract_cpc_sets",
    "extract_cpc_sets_with_years",
    "build_cooccurrence",
    "build_cooccurrence_with_years",
    "build_jaccard_from_sql",
    "build_year_data_from_aggregates",
    "assign_colors",
    # research_metrics
    "_compute_h_index",
    "_compute_citation_trend",
    "_compute_top_papers",
    "_compute_venue_distribution",
    "_compute_publication_types",
    # temporal_metrics
    "_compute_actor_dynamics",
    "_compute_technology_breadth",
    "_compute_actor_timeline",
    "_compute_programme_evolution",
    # sampling
    "stratified_sample",
    "SamplingResult",
    "StratumInfo",
    "JaccardConfidence",
    "estimate_jaccard_confidence",
    # cpc_descriptions
    "CPC_SECTION_DESCRIPTIONS",
    "CPC_CLASS_DESCRIPTIONS",
    "CPC_SUBCLASS_DESCRIPTIONS",
    "describe_cpc",
    # eu_countries
    "EU_EEA_COUNTRIES",
    "is_european",
    # models
    "ApiAlert",
    "LandscapePanel",
    "MaturityPanel",
    "CompetitivePanel",
    "FundingPanel",
    "CpcFlowPanel",
    "GeographicPanel",
    "ResearchImpactPanel",
    "TemporalPanel",
    "TechClusterPanel",
    "ExplainabilityMetadata",
    # analysis_text
    "generate_landscape_text",
    "generate_maturity_text",
    "generate_competitive_text",
    "generate_funding_text",
    "generate_cpc_flow_text",
    "generate_geographic_text",
    "generate_research_impact_text",
    "generate_temporal_text",
    "generate_tech_cluster_text",
    # entity_resolution
    "normalize_actor_name",
    "generate_blocking_key",
    "levenshtein_similarity",
    "tfidf_cosine_similarity",
    "find_matches",
    # api_health
    "check_jwt_expiry",
    "detect_runtime_failures",
]
