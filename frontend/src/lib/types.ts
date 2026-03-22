/* ──────────────────────────────────────────────
 * TI-Radar v2 -- TypeScript Type Definitions
 * Mirrors the FastAPI backend Pydantic schemas
 * ────────────────────────────────────────────── */

// ── Request ──

export interface RadarRequest {
  technology: string;
  time_range: number;
  european_only: boolean;
  use_cases: string[];
  top_n: number;
  use_mock?: boolean;
}

// ── Individual Panel Types ──

export interface TimeSeriesPoint {
  year: number;
  patents: number;
  projects: number;
  publications: number;
}

export interface CpcCode {
  code: string;
  label: string;
  count: number;
}

export interface LandscapePanel {
  time_series: TimeSeriesPoint[];
  cagr_patents: number;
  cagr_projects: number;
  cagr_publications: number;
  top_cpc_codes: CpcCode[];
  total_patents: number;
  total_projects: number;
  total_publications: number;
}

export interface MaturityDataPoint {
  year: number;
  cumulative: number;
  fitted: number;
  annual_count: number;
}

export interface MaturityPanel {
  phase: "emergence" | "growth" | "maturity" | "saturation" | "decline";
  phase_label: string;
  s_curve_data: MaturityDataPoint[];
  inflection_year: number | null;
  r_squared: number;
  saturation_level: number;
  data_complete_year: number | null;
  maturity_percent: number;
  cagr: number;
  model_name: string;
  aicc_selected: number;
  aicc_alternative: number;
  delta_aicc: number;
}

export interface CompetitorEntry {
  name: string;
  patent_count: number;
  project_count: number;
  market_share: number;
  country_code: string;
  actor_type: string;
}

export interface HhiTrendPoint {
  year: number;
  hhi: number;
  level: string;
}

export interface NetworkNode {
  id: string;
  label: string;
  size: number;
  community: number;
  country_code: string;
}

export interface NetworkEdge {
  source: string;
  target: string;
  weight: number;
  collaboration_type: string;
}

export interface CompetitivePanel {
  top_assignees: CompetitorEntry[];
  hhi_index: number;
  concentration: "niedrig" | "mittel" | "hoch";
  cr4_share: number;
  top3_share: number;
  top10_share: number;
  total_actors: number;
  hhi_trend: HhiTrendPoint[];
  network_nodes: NetworkNode[];
  network_edges: NetworkEdge[];
}

export interface FundingEntry {
  program: string;
  total_funding: number;
  project_count: number;
  avg_funding: number;
  share: number;
}

export interface FundedOrganisation {
  name: string;
  country_code: string;
  funding_eur: number;
  project_count: number;
  organisation_type: string;
}

export interface FundingTrendPoint {
  year: number;
  funding_eur: number;
  project_count: number;
  avg_project_size: number;
  participant_count: number;
}

export interface FundingPanel {
  by_program: FundingEntry[];
  total_funding: number;
  total_projects: number;
  funding_trend: FundingTrendPoint[];
  cagr: number;
  avg_duration_months: number;
  top_organisations: FundedOrganisation[];
}

export interface CpcFlowLink {
  source: string;
  target: string;
  value: number;
  similarity: number;  // Jaccard-Index
}

export interface CpcFlowNode {
  id: string;
  label: string;
}

export interface WhitespaceOpportunity {
  code_a: string;
  code_b: string;
  jaccard: number;
  freq_a: number;
  freq_b: number;
  opportunity_score: number;
}

export interface CpcFlowPanel {
  nodes: CpcFlowNode[];
  links: CpcFlowLink[];
  top_combinations: Array<{ codes: string[]; count: number; jaccard: number }>;
  cpc_patent_counts: Record<string, number>;
  whitespace_opportunities: WhitespaceOpportunity[];
}

export interface CountryData {
  country_code: string;
  country_name: string;
  patent_count: number;
  project_count: number;
  share: number;
}

export interface CooperationPair {
  country_a: string;
  country_b: string;
  co_project_count: number;
}

export interface GeographicPanel {
  countries: CountryData[];
  eu_share: number;
  top_country: string;
  cooperation_pairs: CooperationPair[];
  total_cities: number;
}

export interface ResearchMetric {
  institution: string;
  h_index: number;
  total_citations: number;
  paper_count: number;
}

export interface CitationTrendPoint {
  year: number;
  total_citations: number;
  publication_count: number;
}

export interface ResearchImpactPanel {
  top_institutions: ResearchMetric[];
  avg_citations: number;
  total_papers: number;
  collaboration_rate: number;
  citation_trend: CitationTrendPoint[];
}

export interface TemporalCluster {
  year: number;
  cluster_label: string;
  patent_count: number;
  keywords: string[];
}

export interface EntrantTrendPoint {
  year: number;
  new_entrants: number;
  persistent_actors: number;
  exited_actors: number;
  total_active: number;
}

export interface TemporalPanel {
  clusters: TemporalCluster[];
  emerging_topics: string[];
  declining_topics: string[];
  entrant_trend: EntrantTrendPoint[];
}

// ── Tier-2 Panel Types ──

export interface TechCluster {
  cluster_id: number;
  label: string;
  cpc_codes: string[];
  actor_count: number;
  patent_count: number;
  density: number;
  coherence: number;
  cagr: number;
  dominant_topics: string[];
}

export interface TechClusterPanel {
  clusters: TechCluster[];
  total_actors: number;
  total_cpc_codes: number;
  quality: {
    avg_silhouette: number;
    num_clusters: number;
    algorithm: string;
    modularity: number;
  };
}

export interface EuroSciVocField {
  id: string;
  label: string;
  total_publications: number;
  total_projects: number;
  share: number;
  active_sub_fields: number;
  cagr: number;
}

export interface EuroSciVocPanel {
  fields_of_science: EuroSciVocField[];
  interdisciplinarity: {
    shannon_index: number;
    simpson_index: number;
    active_disciplines: number;
    active_fields: number;
    is_interdisciplinary: boolean;
  };
  total_mapped_publications: number;
  mapping_coverage: number;
}

export interface ActorTypeBreakdown {
  label: string;
  actor_count: number;
  patent_count: number;
  project_count: number;
  actor_share: number;
  funding_eur: number;
}

export interface ActorTypeYearEntry {
  year: number;
  hes_count: number;
  prc_count: number;
  rec_count: number;
  oth_count: number;
  pub_count: number;
  total: number;
}

export interface ActorTypePanel {
  type_breakdown: ActorTypeBreakdown[];
  type_trend: ActorTypeYearEntry[];
  total_classified_actors: number;
  classification_coverage: number;
  sme_share: number;
}

export interface GrantRateYearEntry {
  year: number;
  application_count: number;
  grant_count: number;
  grant_rate: number;
}

export interface PatentGrantPanel {
  summary: {
    total_applications: number;
    total_grants: number;
    grant_rate: number;
    avg_time_to_grant_months: number;
  };
  year_trend: GrantRateYearEntry[];
}

// ── UC-C Publication Panel Types ──

export interface PublicationYearEntry {
  year: number;
  publication_count: number;
  project_count: number;
}

export interface ProjectPublicationLink {
  project_acronym: string;
  framework: string;
  ec_contribution_eur: number;
  publication_count: number;
  publications_per_million_eur: number;
}

export interface TopPublication {
  title: string;
  doi: string;
  journal: string;
  publication_year: number;
  project_acronym: string;
}

export interface PublicationPanel {
  total_publications: number;
  total_projects_with_pubs: number;
  publications_per_project: number;
  doi_coverage: number;
  pub_trend: PublicationYearEntry[];
  top_projects: ProjectPublicationLink[];
  top_publications: TopPublication[];
}

// ── Metadata ──

export interface RadarMetadata {
  technology: string;
  time_range: number;
  european_only: boolean;
  query_time_seconds: number;
  data_sources: string[];
  timestamp: string;
}

// ── Aggregated Response ──

export interface RadarResponse {
  landscape: LandscapePanel | null;
  maturity: MaturityPanel | null;
  competitive: CompetitivePanel | null;
  funding: FundingPanel | null;
  cpc_flow: CpcFlowPanel | null;
  geographic: GeographicPanel | null;
  research_impact: ResearchImpactPanel | null;
  temporal: TemporalPanel | null;
  tech_cluster: TechClusterPanel | null;
  euroscivoc: EuroSciVocPanel | null;
  actor_type: ActorTypePanel | null;
  patent_grant: PatentGrantPanel | null;
  publication: PublicationPanel | null;
  uc_errors: Record<string, string>;
  metadata: RadarMetadata;
}

// ── Health Check ──

export interface HealthResponse {
  status: string;
  version: string;
  uptime: number;
  services: Record<string, boolean>;
}

// ── Use Case Enum ──

export const USE_CASES = [
  "landscape",
  "maturity",
  "competitive",
  "funding",
  "cpc_flow",
  "geographic",
  "research_impact",
  "temporal",
  "tech_cluster",
  "euroscivoc",
  "actor_type",
  "patent_grant",
  "publication",
] as const;

export type UseCaseKey = (typeof USE_CASES)[number];

export const USE_CASE_LABELS: Record<UseCaseKey, string> = {
  landscape: "Technologie-Landschaft",
  maturity: "Reifegrad-Analyse",
  competitive: "Wettbewerbsanalyse",
  funding: "Förderungsanalyse",
  cpc_flow: "Cross-Tech Intelligence",
  geographic: "Geographische Verteilung",
  research_impact: "Forschungsimpact",
  temporal: "Zeitliche Entwicklung",
  tech_cluster: "Technologie-Cluster",
  euroscivoc: "Wissenschaftsdisziplinen",
  actor_type: "Akteurs-Typen",
  patent_grant: "Erteilungsquoten",
  publication: "Publikations-Impact",
};

// ── UC Number Mapping ──

export const UC_NUMBERS: Record<UseCaseKey, { number: number; label?: string }> = {
  landscape:       { number: 1 },
  maturity:        { number: 2 },
  competitive:     { number: 3 },
  funding:         { number: 4 },
  cpc_flow:        { number: 5 },
  geographic:      { number: 6 },
  research_impact: { number: 7 },
  temporal:        { number: 8 },
  tech_cluster:    { number: 9 },
  euroscivoc:      { number: 10 },
  actor_type:      { number: 11 },
  patent_grant:    { number: 12 },
  publication:     { number: 13 },
};

// ── Time Range Options ──

export const TIME_RANGE_OPTIONS = [
  { value: 5, label: "5 Jahre" },
  { value: 10, label: "10 Jahre" },
  { value: 15, label: "15 Jahre" },
  { value: 20, label: "20 Jahre" },
] as const;
