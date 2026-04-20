/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Backend → Frontend Transform
 * Converts raw gRPC backend response shapes into
 * the frontend RadarResponse type definitions.
 * ────────────────────────────────────────────── */

import { getCountryName } from "@/lib/countries";

import type {
  RadarResponse,
  RadarMetadata,
  LandscapePanel,
  MaturityPanel,
  CompetitivePanel,
  FundingPanel,
  CpcFlowPanel,
  CpcFlowNode,
  CpcFlowLink,
  GeographicPanel,
  ResearchImpactPanel,
  ResearchMetric,
  TemporalPanel,
  TechClusterPanel,
  ActorTypePanel,
  PatentGrantPanel,
  EuroSciVocPanel,
  HhiTrendPoint,
  NetworkNode,
  NetworkEdge,
} from "@/lib/types";

// ── Helpers ──

/** Safe number parse — returns 0 for null, undefined, NaN, or unparseable strings. */
const num = (value: unknown): number => Number(value) || 0;

// ── Per-Panel Transformers ──

/**
 * Transform backend landscape data into LandscapePanel.
 *
 * Backend shape:
 *   time_series: [{year, patent_count(string), project_count(string), ...}]
 *   cagr_values: {patent_cagr, project_cagr}
 *   summary: {total_patents(string), total_projects(string)}
 *   top_cpc_codes: [{code, label, count(string)}]
 *
 * Frontend expects:
 *   time_series: [{year, patents(number), projects(number)}]
 *   cagr_patents, cagr_projects, total_patents, total_projects (all number)
 *   top_cpc_codes: [{code, label, count(number)}]
 */
function transformLandscape(raw: any): LandscapePanel | null {
  if (!raw) return null;

  const timeSeries = Array.isArray(raw.time_series)
    ? raw.time_series.map((pt: any) => ({
        year: num(pt.year),
        patents: num(pt.patent_count),
        projects: num(pt.project_count),
        publications: num(pt.publication_count),
      }))
    : [];

  const topCpcCodes = Array.isArray(raw.top_cpc_codes)
    ? raw.top_cpc_codes.map((c: any) => ({
        code: c.code ?? "",
        // Bug v3.4.9/N1: Backend liefert das Description-Feld (z.B.
        // "Quantum error correction; Fault-tolerant quantum computing"),
        // aber der alte Transform las nur `c.label` und zeigte deshalb
        // leere Bezeichnungen an. Jetzt: description hat Vorrang, label
        // als Abwärtskompat.-Fallback.
        label: c.description ?? c.label ?? "",
        count: num(c.count),
      }))
    : [];

  return {
    time_series: timeSeries,
    cagr_patents: num(raw.cagr_values?.patent_cagr),
    cagr_projects: num(raw.cagr_values?.project_cagr),
    cagr_publications: num(raw.cagr_values?.publication_cagr),
    total_patents: num(raw.summary?.total_patents),
    total_projects: num(raw.summary?.total_projects),
    total_publications: num(raw.summary?.total_publications),
    top_cpc_codes: topCpcCodes,
  };
}

/**
 * Transform backend maturity data into MaturityPanel.
 *
 * Backend shape:
 *   s_curve_data: [{year, cumulative, fitted, annual_count}]
 *   phase, r_squared, maturity_percent, cagr
 *   model_parameters: {carrying_capacity, growth_rate, inflection_year}
 *   fitted_on, aicc_selected, aicc_alternative, delta_aicc
 *   data_complete_year
 *
 * Frontend expects:
 *   s_curve_data, phase, phase_label, r_squared
 *   saturation_level(number), inflection_year(number|null)
 *   maturity_percent, cagr, model_name, aicc_selected/alternative/delta
 */
function transformMaturity(raw: any): MaturityPanel | null {
  if (!raw) return null;

  const phaseLabels: Record<string, string> = {
    emergence: "Entstehung",
    growth: "Wachstum",
    maturity: "Reife",
    saturation: "Sättigung",
    decline: "Rückgang",
    unknown: "Unklar",
  };

  // Backend liefert Protobuf-Enum-Namen (Mature, Growing, etc.)
  // Frontend erwartet (maturity, growth, etc.)
  const phaseMap: Record<string, string> = {
    emerging: "emergence",
    emergence: "emergence",
    growing: "growth",
    growth: "growth",
    mature: "maturity",
    maturity: "maturity",
    saturating: "saturation",
    saturation: "saturation",
    declining: "decline",
    decline: "decline",
    // Bug MAJ-9: Backend liefert "Unknown"/TECHNOLOGY_PHASE_UNSPECIFIED bei
    // unzuverlaessigem Fit; Frontend muss das deterministisch als "unknown"
    // erkennen, damit Phase-Badge ausgegraut werden kann (statt Default
    // "emergence" anzuzeigen — das war die alte Scheinsicherheit).
    unknown: "unknown",
    technology_phase_unspecified: "unknown",
    "": "unknown",
  };
  const rawPhase = (raw.phase ?? "unknown").toString().toLowerCase();
  const phase = (phaseMap[rawPhase] ?? "unknown") as MaturityPanel["phase"];

  const sCurveData = Array.isArray(raw.s_curve_data)
    ? raw.s_curve_data.map((pt: any) => ({
        year: num(pt.year),
        cumulative: num(pt.cumulative),
        fitted: num(pt.fitted),
        annual_count: num(pt.annual_count),
      }))
    : [];

  // Read saturation (carrying_capacity) and inflection_year from model_parameters.
  // Protobuf field name is "carrying_capacity", not "saturation".
  const saturation = num(raw.model_parameters?.carrying_capacity);
  // Inflection year comes directly from the logistic model parameters (x0).
  const rawInflection = num(raw.model_parameters?.inflection_year);
  const inflectionYear: number | null = rawInflection > 0 ? Math.round(rawInflection) : null;

  // Bug MAJ-9: R²/Konfidenz strukturell koppeln (Belt-and-Suspenders).
  // Wenn Backend (Bug-Drift) doch Konfidenz > 0 bei R² < 0.5 schickt,
  // erzwingt der Frontend-Gate Konfidenz = 0 und reliability_flag = false.
  const rSquared = num(raw.r_squared);
  const rawConfidence = num(raw.confidence?.confidence_level);
  const backendReliability = Boolean(raw.fit_reliability_flag);
  const isReliable = backendReliability && rSquared >= 0.5;
  const confidence = isReliable ? rawConfidence : 0;

  return {
    s_curve_data: sCurveData,
    phase,
    phase_label: phaseLabels[phase] ?? phase,
    r_squared: rSquared,
    saturation_level: saturation,
    inflection_year: inflectionYear,
    data_complete_year: num(raw.data_complete_year) || null,
    maturity_percent: num(raw.maturity_percent),
    cagr: num(raw.cagr),
    model_name: raw.fitted_on || "logistic",
    aicc_selected: num(raw.aicc_selected),
    aicc_alternative: num(raw.aicc_alternative),
    delta_aicc: num(raw.delta_aicc),
    confidence,
    fit_reliability_flag: isReliable,
    // Overfitting-Warnung: Backend liefert overfit_warning als bool, wenn
    // R² > 0.98 UND n < 30. Feld ist optional (aeltere Backends kennen es nicht).
    overfit_warning: Boolean(raw.overfit_warning),
  };
}

/**
 * Transform backend competitive data into CompetitivePanel.
 *
 * Backend: top_actors → Frontend: top_assignees
 * Backend: hhi_level → Frontend: concentration
 */

const ACTOR_TYPE_LABELS: Record<string, string> = {
  COMPANY: "Unternehmen",
  UNIVERSITY: "Hochschule",
  RESEARCH_INSTITUTION: "Forschung",
  GOVERNMENT: "Behörde",
  OTHER: "Sonstige",
};

/** Protobuf enum may arrive as numeric string — map to name first */
const ACTOR_TYPE_NUMERIC: Record<string, string> = {
  "1": "COMPANY",
  "2": "UNIVERSITY",
  "3": "RESEARCH_INSTITUTION",
  "4": "GOVERNMENT",
  "5": "OTHER",
};

function resolveActorType(raw: unknown): string {
  const s = (raw ?? "").toString();
  const key = /^\d+$/.test(s) ? (ACTOR_TYPE_NUMERIC[s] ?? "") : s;
  return ACTOR_TYPE_LABELS[key] ?? "Sonstige";
}

function transformCompetitive(raw: any): CompetitivePanel | null {
  if (!raw) return null;

  const topAssignees = Array.isArray(raw.top_actors)
    ? raw.top_actors.map((a: any) => ({
        name: a.name ?? "",
        patent_count: num(a.patent_count),
        project_count: num(a.project_count),
        market_share: num(a.market_share ?? a.share),
        country_code: a.country_code ?? a.country ?? "",
        actor_type: resolveActorType(a.actor_type),
      }))
    : [];

  // Map backend hhi_level string to frontend concentration enum
  const hhiLevel = (raw.hhi_level ?? "").toLowerCase();
  let concentration: "niedrig" | "mittel" | "hoch" = "niedrig";
  if (hhiLevel.includes("hoch") || hhiLevel.includes("high")) {
    concentration = "hoch";
  } else if (hhiLevel.includes("mittel") || hhiLevel.includes("moderate") || hhiLevel.includes("medium")) {
    concentration = "mittel";
  }

  return {
    top_assignees: topAssignees,
    hhi_index: num(raw.hhi_index),
    concentration,
    cr4_share: num(raw.cr4_share),
    top3_share: num(raw.top3_share),
    top10_share: num(raw.top10_share),
    total_actors: num(raw.total_actors),
    hhi_trend: Array.isArray(raw.hhi_trend)
      ? raw.hhi_trend.map((p: any) => ({
          year: num(p.year),
          hhi: num(p.hhi),
          level: String(p.level ?? ""),
        }))
      : [],
    network_nodes: Array.isArray(raw.network_nodes)
      ? raw.network_nodes.map((n: any) => ({
          id: n.id ?? "",
          label: n.label ?? "",
          size: num(n.size),
          community: num(n.community),
          country_code: n.country_code ?? "",
        }))
      : [],
    network_edges: Array.isArray(raw.network_edges)
      ? raw.network_edges.map((e: any) => ({
          source: e.source ?? "",
          target: e.target ?? "",
          weight: num(e.weight),
          collaboration_type: String(e.collaboration_type ?? ""),
        }))
      : [],
  };
}

/**
 * Transform backend funding data into FundingPanel.
 *
 * Backend: instrument_breakdown [{instrument, funding_eur, project_count, share}]
 * Frontend: by_program [{program, total_funding, project_count, avg_funding, share}]
 *
 * Backend: time_series [{year, funding_eur, project_count, avg_project_size, participant_count}]
 * Frontend: funding_trend [{year, funding_eur, project_count, avg_project_size, participant_count}]
 *
 * Backend: top_organisations [{name, country_code, funding_eur, project_count, organisation_type}]
 * Frontend: top_organisations [{name, country_code, funding_eur, project_count, organisation_type}]
 */
function transformFunding(raw: any): FundingPanel | null {
  if (!raw) return null;

  const byProgram = Array.isArray(raw.instrument_breakdown)
    ? raw.instrument_breakdown.map((item: any) => {
        const projectCount = num(item.project_count);
        const totalFunding = num(item.funding_eur);
        return {
          program: item.instrument ?? item.type ?? "",
          total_funding: totalFunding,
          project_count: projectCount,
          avg_funding: projectCount > 0 ? totalFunding / projectCount : 0,
          share: num(item.share),
        };
      })
    : [];

  const fundingTrend = Array.isArray(raw.time_series)
    ? raw.time_series.map((pt: any) => ({
        year: num(pt.year),
        funding_eur: num(pt.funding_eur),
        project_count: num(pt.project_count),
        avg_project_size: num(pt.avg_project_size),
        participant_count: num(pt.participant_count),
      }))
    : [];

  const topOrgs = Array.isArray(raw.top_organisations)
    ? raw.top_organisations.map((org: any) => ({
        name: org.name ?? "",
        country_code: org.country_code ?? "",
        funding_eur: num(org.funding_eur),
        project_count: num(org.project_count),
        organisation_type: org.organisation_type ?? "",
      }))
    : [];

  return {
    by_program: byProgram,
    total_funding: num(raw.total_funding_eur),
    total_projects: num(raw.project_count),
    funding_trend: fundingTrend,
    cagr: num(raw.cagr),
    avg_duration_months: num(raw.avg_duration_months),
    top_organisations: topOrgs,
  };
}

/**
 * Transform backend CPC flow data into CpcFlowPanel.
 *
 * Backend: jaccard_matrix [{code_a, code_b, similarity, co_occurrence_count}],
 *          top_pairs [{code_a, code_b, similarity, co_occurrence_count}],
 *          chord_data [{source, target, value}]
 * Frontend: nodes, links, top_combinations [{codes: [string, string], count, jaccard}]
 */
function transformCpcFlow(raw: any): CpcFlowPanel | null {
  if (!raw) return null;

  // Jaccard-Lookup aus jaccard_matrix UND top_pairs aufbauen.
  // jaccard_matrix enthaelt ALLE Paare oberhalb des Schwellenwerts,
  // top_pairs nur die Top-N — beides zusammen ergibt vollstaendige Abdeckung.
  const jaccardLookup = new Map<string, number>();
  if (Array.isArray(raw.jaccard_matrix)) {
    for (const entry of raw.jaccard_matrix) {
      const a = entry.code_a ?? "";
      const b = entry.code_b ?? "";
      const sim = Number(entry.similarity);
      if (a && b && !isNaN(sim) && sim > 0) {
        jaccardLookup.set(`${a}:${b}`, sim);
        jaccardLookup.set(`${b}:${a}`, sim);
      }
    }
  }
  if (Array.isArray(raw.top_pairs)) {
    for (const pair of raw.top_pairs) {
      const a = pair.code_a ?? pair.cpc_a ?? "";
      const b = pair.code_b ?? pair.cpc_b ?? "";
      const sim = Number(pair.similarity) || Number(pair.jaccard) || 0;
      if (a && b && sim > 0) {
        jaccardLookup.set(`${a}:${b}`, sim);
        jaccardLookup.set(`${b}:${a}`, sim);
      }
    }
  }

  // CPC-Code → Beschreibung Lookup aus cpc_codes
  const cpcDescLookup: Record<string, string> = {};
  if (Array.isArray(raw.cpc_codes)) {
    for (const c of raw.cpc_codes) {
      const code = c.code ?? "";
      const desc = c.description ?? "";
      if (code && desc) cpcDescLookup[code] = desc;
    }
  }

  // chord_data can be either {nodes, links} or a flat array of {source, target, value}
  let nodes: CpcFlowNode[] = [];
  let links: CpcFlowLink[] = [];

  if (Array.isArray(raw.chord_data)) {
    // Flat array format: derive nodes from unique sources/targets
    links = raw.chord_data.map((l: any) => {
      const src = l.source ?? l.source_label ?? "";
      const tgt = l.target ?? l.target_label ?? "";
      return {
        source: src,
        target: tgt,
        value: num(l.value),
        similarity: num(l.similarity) || num(l.jaccard) || jaccardLookup.get(`${src}:${tgt}`) || 0,
      };
    });
    const nodeSet = new Set<string>();
    for (const l of links) {
      if (l.source) nodeSet.add(l.source);
      if (l.target) nodeSet.add(l.target);
    }
    nodes = Array.from(nodeSet).map((id) => ({ id, label: cpcDescLookup[id] || id }));
  } else if (raw.chord_data) {
    nodes = Array.isArray(raw.chord_data.nodes)
      ? raw.chord_data.nodes.map((n: any) => ({ id: n.id ?? "", label: n.label ?? "" }))
      : [];
    links = Array.isArray(raw.chord_data.links)
      ? raw.chord_data.links.map((l: any) => {
          const src = l.source ?? "";
          const tgt = l.target ?? "";
          return {
            source: src,
            target: tgt,
            value: num(l.value),
            similarity: num(l.similarity) || num(l.jaccard) || jaccardLookup.get(`${src}:${tgt}`) || 0,
          };
        })
      : [];
  }

  // top_pairs → top_combinations:
  // Backend field "similarity" carries the Jaccard coefficient (primary metric).
  // "co_occurrence_count" is often 0 because the backend currently does not
  // populate it; fall back to scaled Jaccard so "count" is never misleadingly 0.
  const topCombinations = Array.isArray(raw.top_pairs)
    ? raw.top_pairs.map((pair: any) => {
        const jaccard = Number(pair.similarity) || Number(pair.jaccard) || 0;
        const coOcc = Number(pair.co_occurrence_count) || Number(pair.co_occurrence) || 0;
        return {
          codes: [pair.code_a ?? pair.cpc_a ?? "", pair.code_b ?? pair.cpc_b ?? ""],
          count: coOcc > 0 ? coOcc : Math.round(jaccard * 1000),
          jaccard,
        };
      })
    : [];

  // CPC patent counts aus cpc_codes extrahieren
  const cpcPatentCounts: Record<string, number> = {};
  if (Array.isArray(raw.cpc_codes)) {
    for (const c of raw.cpc_codes) {
      const code = c.code ?? "";
      const count = num(c.patent_count);
      if (code && count > 0) cpcPatentCounts[code] = count;
    }
  }

  // Whitespace-Analyse: Paare mit hoher Einzelaktivitaet aber niedriger Ko-Klassifikation
  const whitespaceOpportunities: Array<{
    code_a: string; code_b: string; jaccard: number;
    freq_a: number; freq_b: number; opportunity_score: number;
  }> = [];

  if (Object.keys(cpcPatentCounts).length >= 2) {
    const codes = Object.keys(cpcPatentCounts);
    const maxFreq = Math.max(...Object.values(cpcPatentCounts));
    const counts = Object.values(cpcPatentCounts).sort((a, b) => a - b);
    const minCount = counts[Math.floor(counts.length * 0.25)] || 0;

    // Jaccard-Lookup aus Links bauen
    const jaccardMap = new Map<string, number>();
    for (const l of links) {
      if (l.similarity > 0) {
        jaccardMap.set(`${l.source}:${l.target}`, l.similarity);
        jaccardMap.set(`${l.target}:${l.source}`, l.similarity);
      }
    }
    // Auch aus topCombinations
    for (const c of topCombinations) {
      if (c.jaccard > 0 && c.codes.length === 2) {
        jaccardMap.set(`${c.codes[0]}:${c.codes[1]}`, c.jaccard);
        jaccardMap.set(`${c.codes[1]}:${c.codes[0]}`, c.jaccard);
      }
    }

    for (let i = 0; i < codes.length; i++) {
      const freqA = cpcPatentCounts[codes[i]];
      if (freqA < minCount) continue;
      for (let j = i + 1; j < codes.length; j++) {
        const freqB = cpcPatentCounts[codes[j]];
        if (freqB < minCount) continue;
        const jac = jaccardMap.get(`${codes[i]}:${codes[j]}`) || 0;
        if (jac > 0.05) continue;
        const activity = Math.sqrt(freqA * freqB) / maxFreq;
        const score = Math.round((1.0 - jac) * activity * 10000) / 10000;
        whitespaceOpportunities.push({
          code_a: codes[i], code_b: codes[j], jaccard: jac,
          freq_a: freqA, freq_b: freqB, opportunity_score: score,
        });
      }
    }
    whitespaceOpportunities.sort((a, b) => b.opportunity_score - a.opportunity_score);
    whitespaceOpportunities.splice(10); // Top 10
  }

  return {
    nodes,
    links,
    top_combinations: topCombinations,
    cpc_patent_counts: cpcPatentCounts,
    whitespace_opportunities: whitespaceOpportunities,
  };
}

/**
 * Transform backend geographic data into GeographicPanel.
 *
 * Backend: country_distribution, cross_border_share, total_countries
 * Frontend: countries, eu_share, top_country
 */
function transformGeographic(raw: any): GeographicPanel | null {
  if (!raw) return null;

  const countries = Array.isArray(raw.country_distribution)
    ? raw.country_distribution.map((c: any) => {
        const code = c.country_code ?? "";
        return {
          country_code: code,
          country_name: c.country_name || getCountryName(code),
          patent_count: num(c.patent_count),
          project_count: num(c.project_count),
          share: num(c.share),
        };
      })
    : [];

  // Determine top country by combined patent + project count
  let topCountry = "";
  if (countries.length > 0) {
    const sorted = [...countries].sort(
      (a, b) =>
        b.patent_count + b.project_count - (a.patent_count + a.project_count)
    );
    topCountry = sorted[0].country_name || getCountryName(sorted[0].country_code);
  }

  const cooperationPairs = Array.isArray(raw.cooperation_pairs)
    ? raw.cooperation_pairs.map((p: any) => ({
        country_a: p.country_a ?? "",
        country_b: p.country_b ?? "",
        co_project_count: num(p.co_project_count),
      }))
    : [];

  return {
    countries,
    eu_share: num(raw.cross_border_share),
    top_country: topCountry,
    cooperation_pairs: cooperationPairs,
    total_cities: num(raw.total_cities),
  };
}

/**
 * Transform backend research impact data into ResearchImpactPanel.
 *
 * Backend: h_index, avg_citations, total_citations, total_publications,
 *          top_institutions [{name, project_count, country, activity_type}] (CORDIS),
 *          top_venues [{name, publication_count, avg_citations, share}],
 *          top_papers [{title, authors, citation_count, year, venue}]
 * Frontend: top_institutions [{institution, h_index, total_citations, paper_count}],
 *           avg_citations, total_papers, collaboration_rate
 *
 * Prefers CORDIS top_institutions from backend. Falls back to top_venues,
 * then to venue synthesis from top_papers.
 */
function transformResearchImpact(raw: any): ResearchImpactPanel | null {
  if (!raw) return null;

  let topInstitutions: ResearchMetric[];

  // 1) Prefer CORDIS top_institutions from backend (project participation data)
  const backendInstitutions: any[] = Array.isArray(raw.top_institutions) ? raw.top_institutions : [];
  if (backendInstitutions.length > 0) {
    topInstitutions = backendInstitutions.map((inst: any) => ({
      institution: inst.name || "Unbekannt",
      h_index: num(raw.h_index),
      total_citations: num(inst.project_count),
      paper_count: num(inst.project_count),
    }));
  }
  // 2) Fallback: use top_venues from Semantic Scholar
  else if (Array.isArray(raw.top_venues) && raw.top_venues.length > 0) {
    topInstitutions = raw.top_venues.map((v: any) => ({
      institution: v.name || "Unbekannt",
      h_index: num(raw.h_index),
      total_citations: Math.round(num(v.avg_citations) * num(v.publication_count)),
      paper_count: num(v.publication_count),
    }));
  }
  // 3) Last resort: synthesize from top_papers grouped by venue
  else {
    const topPapers: any[] = Array.isArray(raw.top_papers) ? raw.top_papers : [];
    const venueMap = new Map<string, { citations: number; count: number }>();
    for (const paper of topPapers) {
      const venue = paper.venue || paper.authors || "Unbekannt";
      const existing = venueMap.get(venue) ?? { citations: 0, count: 0 };
      existing.citations += num(paper.citation_count);
      existing.count += 1;
      venueMap.set(venue, existing);
    }
    topInstitutions = Array.from(venueMap.entries())
      .map(([venue, data]) => ({
        institution: venue,
        h_index: num(raw.h_index),
        total_citations: data.citations,
        paper_count: data.count,
      }))
      .sort((a, b) => b.total_citations - a.total_citations);
  }

  const citationTrend = Array.isArray(raw.citation_trend)
    ? raw.citation_trend.map((pt: any) => ({
        year: num(pt.year),
        total_citations: num(pt.total_citations),
        publication_count: num(pt.publication_count),
      }))
    : [];

  return {
    top_institutions: topInstitutions,
    avg_citations: num(raw.avg_citations),
    total_papers: num(raw.total_publications),
    collaboration_rate: 0, // Not provided by backend
    citation_trend: citationTrend,
  };
}

/**
 * Transform backend temporal data into TemporalPanel.
 *
 * Backend: entrant_persistence_trend [{year, cluster_label, patent_count, keywords}]
 *          dynamics_summary: {emerging: [string], declining: [string]}
 * Frontend: clusters, emerging_topics, declining_topics
 */
function transformTemporal(raw: any): TemporalPanel | null {
  if (!raw) return null;

  // programme_evolution maps to clusters (programme instrument breakdown over time)
  // entrant_persistence_trend maps separately to entrant_trend below
  const programmeSource = Array.isArray(raw.programme_evolution) && raw.programme_evolution.length > 0
    ? raw.programme_evolution
    : [];

  const clusters = programmeSource.map((entry: any) => ({
    year: num(entry.year),
    cluster_label: entry.cluster_label ?? entry.programme ?? "",
    patent_count: num(entry.patent_count ?? entry.project_count),
    keywords: Array.isArray(entry.keywords) ? entry.keywords : [],
  }));

  const emergingTopics = Array.isArray(raw.dynamics_summary?.emerging)
    ? raw.dynamics_summary.emerging
    : [];

  const decliningTopics = Array.isArray(raw.dynamics_summary?.declining)
    ? raw.dynamics_summary.declining
    : [];

  const entrantTrend = Array.isArray(raw.entrant_persistence_trend)
    ? raw.entrant_persistence_trend.map((pt: any) => ({
        year: num(pt.year),
        new_entrants: num(pt.new_entrants),
        persistent_actors: num(pt.persistent_actors),
        exited_actors: num(pt.exited_actors),
        total_active: num(pt.total_active),
      }))
    : [];

  return {
    clusters,
    emerging_topics: emergingTopics,
    declining_topics: decliningTopics,
    entrant_trend: entrantTrend,
    actor_scope_label:
      typeof raw.actor_scope_label === "string"
        ? raw.actor_scope_label
        : undefined,
  };
}

/**
 * Transform backend tech cluster data into TechClusterPanel.
 *
 * Backend clusters may use total_actors/total_patents field names;
 * Frontend expects actor_count/patent_count on each cluster item.
 */
function transformTechCluster(raw: any): TechClusterPanel | null {
  if (!raw) return null;

  const clusters = Array.isArray(raw.clusters)
    ? raw.clusters.map((c: any) => ({
        cluster_id: num(c.cluster_id),
        label: c.label ?? "",
        cpc_codes: Array.isArray(c.cpc_codes) ? c.cpc_codes : [],
        actor_count: num(c.actor_count ?? c.total_actors),
        patent_count: num(c.patent_count ?? c.total_patents),
        density: num(c.density),
        coherence: num(c.coherence),
        cagr: num(c.cagr),
        dominant_topics: Array.isArray(c.dominant_topics)
          ? c.dominant_topics
          : [],
      }))
    : [];

  // Extract quality metrics if present, otherwise provide defaults
  const quality = raw.quality ?? {
    avg_silhouette: 0,
    num_clusters: clusters.length,
    algorithm: "unknown",
    modularity: 0,
  };

  return {
    clusters,
    total_actors: num(raw.total_actors),
    total_cpc_codes: num(raw.total_cpc_codes),
    quality: {
      avg_silhouette: num(quality.avg_silhouette),
      num_clusters: num(quality.num_clusters) || clusters.length,
      algorithm: quality.algorithm ?? "unknown",
      modularity: num(quality.modularity),
    },
    actor_scope_label:
      typeof raw.actor_scope_label === "string"
        ? raw.actor_scope_label
        : undefined,
  };
}

/**
 * Transform backend actor type data into ActorTypePanel.
 *
 * Backend: type_breakdown, type_trend, total_classified_actors, unclassified_actors
 * Frontend: type_breakdown, type_trend, total_classified_actors,
 *           classification_coverage, sme_share
 */
function transformActorType(raw: any): ActorTypePanel | null {
  if (!raw) return null;

  const typeBreakdown = Array.isArray(raw.type_breakdown)
    ? raw.type_breakdown.map((entry: any) => ({
        label: entry.label ?? "",
        actor_count: num(entry.actor_count),
        patent_count: num(entry.patent_count),
        project_count: num(entry.project_count),
        actor_share: num(entry.actor_share),
        funding_eur: num(entry.funding_eur),
      }))
    : [];

  const typeTrend = Array.isArray(raw.type_trend)
    ? raw.type_trend.map((entry: any) => ({
        year: num(entry.year),
        hes_count: num(entry.hes_count),
        prc_count: num(entry.prc_count),
        rec_count: num(entry.rec_count),
        oth_count: num(entry.oth_count),
        pub_count: num(entry.pub_count),
        total: num(entry.total),
      }))
    : [];

  const totalClassified = num(raw.total_classified_actors);
  const unclassified = num(raw.unclassified_actors);
  const totalAll = totalClassified + unclassified;
  // Bug v3.4.9/N2-classification: Backend liefert jetzt `classification_coverage`
  // direkt (v3.4.7/Bundle B). Vorzugsweise Backend-Wert nehmen, nur als
  // Fallback selbst rechnen.
  const backendCoverage = raw.classification_coverage;
  const classificationCoverage =
    typeof backendCoverage === "number"
      ? backendCoverage
      : totalAll > 0
        ? totalClassified / totalAll
        : 1.0;

  // Bug v3.4.9/N2: Backend liefert `sme_share` direkt (z.B. 0.5401 bei
  // Quantum). Die alte PRC-Label-Suche traf den deutschen Label
  // "KMU / Unternehmen" nicht und fiel fälschlich auf 0 zurück — UI zeigte
  // deshalb "KMU-Anteil 0%" obwohl im Diagramm 46,6% zu sehen waren.
  // Jetzt: Backend-Wert hat Vorrang; PRC-Suche nur als Fallback.
  const rawSmeShare = raw.sme_share;
  let smeShare: number;
  if (typeof rawSmeShare === "number") {
    smeShare = rawSmeShare;
  } else {
    const prcEntry = typeBreakdown.find(
      (e: any) => e.label === "PRC" || e.label?.toLowerCase().includes("private")
    );
    smeShare = prcEntry ? num(prcEntry.actor_share) : 0;
  }

  return {
    type_breakdown: typeBreakdown,
    type_trend: typeTrend,
    total_classified_actors: totalClassified,
    classification_coverage: classificationCoverage,
    sme_share: smeShare,
    actor_scope_label:
      typeof raw.actor_scope_label === "string"
        ? raw.actor_scope_label
        : undefined,
  };
}

/**
 * Transform backend patent grant data into PatentGrantPanel.
 *
 * Backend and frontend shapes match — minimal transformation needed,
 * just ensure numeric types.
 */
function transformPatentGrant(raw: any): PatentGrantPanel | null {
  if (!raw) return null;

  return {
    summary: {
      total_applications: num(raw.summary?.total_applications),
      total_grants: num(raw.summary?.total_grants),
      grant_rate: num(raw.summary?.grant_rate),
      avg_time_to_grant_months: num(raw.summary?.avg_time_to_grant_months),
    },
    year_trend: Array.isArray(raw.year_trend)
      ? raw.year_trend.map((entry: any) => ({
          year: num(entry.year),
          application_count: num(entry.application_count),
          grant_count: num(entry.grant_count),
          grant_rate: num(entry.grant_rate),
        }))
      : [],
  };
}

/**
 * Transform backend EuroSciVoc data into EuroSciVocPanel.
 *
 * Backend and frontend shapes match — minimal transformation needed,
 * just ensure numeric types.
 */
function transformEuroSciVoc(raw: any): EuroSciVocPanel | null {
  if (!raw) return null;

  // Fields of Science (Level-1 der EuroSciVoc-Taxonomie)
  const fieldSource = Array.isArray(raw.fields_of_science) && raw.fields_of_science.length > 0
    ? raw.fields_of_science
    : [];

  // Bug v3.4.10/α-C: Disciplines separat übernehmen (Level 2, bis 50 Einträge).
  // Backend-Feld heißt genauso. Wird im Frontend-Chart als Primär-Quelle genutzt,
  // weil fields_of_science bei engen Technologien oft nur 1 Eintrag hat.
  const disciplinesSource = Array.isArray(raw.disciplines) ? raw.disciplines : [];

  return {
    fields_of_science: fieldSource.map((f: any) => ({
      id: f.id ?? "",
      label: f.label ?? "",
      total_publications: num(f.total_publications ?? f.publication_count),
      total_projects: num(f.total_projects ?? f.project_count),
      share: num(f.share),
      active_sub_fields: num(f.active_sub_fields ?? f.child_count),
      cagr: num(f.cagr),
    })),
    disciplines: disciplinesSource.map((d: any) => ({
      id: d.id ?? "",
      label: d.label ?? "",
      parent_id: d.parent_id ?? "",
      project_count: num(d.project_count),
      share: num(d.share),
      level: d.level ?? undefined,
      label_de: d.label_de ?? undefined,
      publication_count: num(d.publication_count),
      child_count: num(d.child_count),
    })),
    interdisciplinarity: {
      shannon_index: num(raw.interdisciplinarity?.shannon_index),
      simpson_index: num(raw.interdisciplinarity?.simpson_index),
      active_disciplines: num(raw.interdisciplinarity?.active_disciplines),
      active_fields: num(raw.interdisciplinarity?.active_fields),
      is_interdisciplinary:
        raw.interdisciplinarity?.is_interdisciplinary ?? false,
    },
    total_mapped_publications: num(raw.total_mapped_publications),
    mapping_coverage: num(raw.mapping_coverage),
  };
}

// ── Metadata ──

/**
 * Build RadarMetadata from top-level backend response fields.
 *
 * Backend provides: technology, analysis_period, timestamp, total_processing_time_ms
 * Frontend expects: technology, time_range, european_only, query_time_seconds,
 *                   data_sources, timestamp
 */
function buildMetadata(raw: any): RadarMetadata {
  // Parse analysis_period string (e.g. "2016-2026" or "10") into a numeric time range
  let timeRange = 10; // default
  const period = raw.analysis_period ?? "";
  if (typeof period === "string" && period.includes("-")) {
    const parts = period.split("-");
    const start = parseInt(parts[0], 10);
    const end = parseInt(parts[1], 10);
    if (!isNaN(start) && !isNaN(end)) {
      timeRange = end - start;
    }
  } else if (typeof period === "number") {
    timeRange = period;
  } else {
    const parsed = parseInt(period, 10);
    if (!isNaN(parsed) && parsed > 0) {
      timeRange = parsed;
    }
  }

  return {
    technology: raw.technology ?? "",
    time_range: timeRange,
    european_only: true, // Default — backend focuses on European data
    query_time_seconds: num(raw.total_processing_time_ms) / 1000,
    data_sources: ["CORDIS", "EPO", "OpenAIRE", "Semantic Scholar", "GLEIF"],
    timestamp: raw.timestamp ?? new Date().toISOString(),
  };
}

// ── UC Errors ──

/**
 * Transform backend uc_errors array into a Record<string, string>.
 *
 * Backend: [{use_case, error_code, error_message}]
 * Frontend: Record<string, string>  (use_case -> error_message)
 */
function transformUcErrors(raw: any): Record<string, string> {
  if (!Array.isArray(raw)) return {};

  const errors: Record<string, string> = {};
  for (const entry of raw) {
    if (entry.use_case) {
      errors[entry.use_case] = entry.error_message ?? entry.error_code ?? "Unbekannter Fehler";
    }
  }
  return errors;
}

// ── Main Transform ──

/**
 * Transform the raw backend radar response into the frontend RadarResponse type.
 *
 * This function handles all field renaming, string-to-number conversions,
 * structural reshaping, and safe defaults for missing data. Each use-case
 * panel is transformed independently; if a panel is null/undefined in the
 * raw response, it will be null in the output.
 *
 * @param raw - The raw JSON response from the backend gRPC gateway
 * @returns A fully typed RadarResponse ready for frontend consumption
 */
export function transformRadarResponse(raw: any): RadarResponse {
  if (!raw || typeof raw !== "object") {
    return {
      landscape: null,
      maturity: null,
      competitive: null,
      funding: null,
      cpc_flow: null,
      geographic: null,
      research_impact: null,
      temporal: null,
      tech_cluster: null,
      euroscivoc: null,
      actor_type: null,
      patent_grant: null,
      publication: null,
      uc_errors: {},
      metadata: buildMetadata({}),
    };
  }

  return {
    landscape: transformLandscape(raw.landscape),
    maturity: transformMaturity(raw.maturity),
    competitive: transformCompetitive(raw.competitive),
    funding: transformFunding(raw.funding),
    cpc_flow: transformCpcFlow(raw.cpc_flow),
    geographic: transformGeographic(raw.geographic),
    research_impact: transformResearchImpact(raw.research_impact),
    temporal: transformTemporal(raw.temporal),
    tech_cluster: transformTechCluster(raw.tech_cluster),
    euroscivoc: transformEuroSciVoc(raw.euroscivoc),
    actor_type: transformActorType(raw.actor_type),
    patent_grant: transformPatentGrant(raw.patent_grant),
    publication: raw.publication ?? null,
    uc_errors: transformUcErrors(raw.uc_errors),
    metadata: buildMetadata(raw),
  };
}
