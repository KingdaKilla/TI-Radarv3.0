"""Domain layer — deterministic metrics, models, and pure functions.

Re-exports key items for convenient access:

    from shared.domain import cagr, hhi_index, fit_best_model
    from shared.domain import LandscapePanel, MaturityPanel, ApiAlert
"""

from __future__ import annotations

# --- Actor / Publication / Patent master-definitions (Bugs CRIT-1/3/4) ---
from shared.domain.actor_definitions import (
    ActorScope,
    canonical_actor_label,
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

# --- API health ---
from shared.domain.api_health import (
    check_jwt_expiry,
    detect_runtime_failures,
)

# --- CPC descriptions ---
from shared.domain.cpc_descriptions import (
    CPC_CLASS_DESCRIPTIONS,
    CPC_SECTION_DESCRIPTIONS,
    CPC_SUBCLASS_DESCRIPTIONS,
    describe_cpc,
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

# --- Entity resolution ---
from shared.domain.entity_resolution import (
    find_matches,
    generate_blocking_key,
    levenshtein_similarity,
    normalize_actor_name,
    tfidf_cosine_similarity,
)

# --- EU countries ---
from shared.domain.eu_countries import EU_EEA_COUNTRIES, is_european

# --- Metrics (pure functions) ---
from shared.domain.metrics import (
    R2_RELIABILITY_THRESHOLD,
    cagr,
    classify_maturity_phase,
    hhi_concentration_level,
    hhi_index,
    merge_country_data,
    merge_time_series,
    s_curve_confidence,
    yoy_growth,
)

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
from shared.domain.patent_definitions import (
    APPLICATION_KIND_CODES,
    GRANT_KIND_CODES,
    PatentScope,
    canonical_patent_label,
)
from shared.domain.publication_definitions import (
    PublicationScope,
    canonical_publication_label,
)

# --- Research metrics ---
from shared.domain.research_metrics import (
    _compute_citation_trend,
    _compute_h_index,
    _compute_publication_types,
    _compute_top_papers,
    _compute_venue_distribution,
)

# --- Sampling ---
from shared.domain.sampling import (
    JaccardConfidence,
    SamplingResult,
    StratumInfo,
    estimate_jaccard_confidence,
    stratified_sample,
)

# --- S-Curve fitting ---
from shared.domain.scurve import (
    fit_best_model,
    fit_gompertz,
    fit_s_curve,
    gompertz_function,
    logistic_function,
)

# --- Temporal metrics ---
from shared.domain.temporal_metrics import (
    _compute_actor_dynamics,
    _compute_actor_timeline,
    _compute_programme_evolution,
    _compute_technology_breadth,
)

# --- Year completeness (Bugs MAJ-7 / MAJ-8) ---
from shared.domain.year_completeness import (
    clip_to_complete_years,
    is_year_complete,
    last_complete_year,
)

__all__ = [
    # patent_definitions
    "APPLICATION_KIND_CODES",
    "CPC_CLASS_DESCRIPTIONS",
    # cpc_descriptions
    "CPC_SECTION_DESCRIPTIONS",
    "CPC_SUBCLASS_DESCRIPTIONS",
    # eu_countries
    "EU_EEA_COUNTRIES",
    "GRANT_KIND_CODES",
    # metrics constants
    "R2_RELIABILITY_THRESHOLD",
    # actor_definitions
    "ActorScope",
    # models
    "ApiAlert",
    "CompetitivePanel",
    "CpcFlowPanel",
    "ExplainabilityMetadata",
    "FundingPanel",
    "GeographicPanel",
    "JaccardConfidence",
    "LandscapePanel",
    "MaturityPanel",
    # patent_definitions
    "PatentScope",
    # publication_definitions
    "PublicationScope",
    "ResearchImpactPanel",
    "SamplingResult",
    "StratumInfo",
    "TechClusterPanel",
    "TemporalPanel",
    # temporal_metrics
    "_compute_actor_dynamics",
    "_compute_actor_timeline",
    "_compute_citation_trend",
    # research_metrics
    "_compute_h_index",
    "_compute_programme_evolution",
    "_compute_publication_types",
    "_compute_technology_breadth",
    "_compute_top_papers",
    "_compute_venue_distribution",
    "assign_colors",
    "build_cooccurrence",
    "build_cooccurrence_with_years",
    "build_jaccard_from_sql",
    "build_year_data_from_aggregates",
    # metrics
    "cagr",
    # actor_definitions helper
    "canonical_actor_label",
    # patent_definitions helper
    "canonical_patent_label",
    # publication_definitions helper
    "canonical_publication_label",
    # api_health
    "check_jwt_expiry",
    "classify_maturity_phase",
    # year_completeness
    "clip_to_complete_years",
    "describe_cpc",
    "detect_runtime_failures",
    "estimate_jaccard_confidence",
    "extract_cpc_sets",
    "extract_cpc_sets_with_years",
    "find_matches",
    "fit_best_model",
    "fit_gompertz",
    "fit_s_curve",
    "generate_blocking_key",
    "generate_competitive_text",
    "generate_cpc_flow_text",
    "generate_funding_text",
    "generate_geographic_text",
    # analysis_text
    "generate_landscape_text",
    "generate_maturity_text",
    "generate_research_impact_text",
    "generate_tech_cluster_text",
    "generate_temporal_text",
    "gompertz_function",
    "hhi_concentration_level",
    "hhi_index",
    "is_european",
    # year_completeness
    "is_year_complete",
    # year_completeness
    "last_complete_year",
    "levenshtein_similarity",
    # scurve
    "logistic_function",
    "merge_country_data",
    "merge_time_series",
    # entity_resolution
    "normalize_actor_name",
    # cpc_flow
    "normalize_cpc",
    "s_curve_confidence",
    # sampling
    "stratified_sample",
    "tfidf_cosine_similarity",
    "yoy_growth",
]
