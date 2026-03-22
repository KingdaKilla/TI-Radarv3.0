/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Cluster Data Model
 * Maps 13 UC panels into 4 thematic clusters
 * for progressive disclosure dashboard
 * ────────────────────────────────────────────── */

import type { RadarResponse, UseCaseKey } from "./types";

export interface ClusterMetric {
  label: string;
  value: string;
}

export interface Cluster {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  image: string;
  metrics: ClusterMetric[];
  ucKeys: UseCaseKey[];
}

export interface ClusterData {
  summary: {
    technology: string;
    text: string;
    badges: string[];
    totalPatents: number;
    totalProjects: number;
    totalPublications: number;
  };
  clusters: Cluster[];
}

export function buildClusterData(data: RadarResponse): ClusterData {
  const phase = data.maturity?.phase_label ?? "Unbekannt";
  const cagr = data.maturity?.cagr;
  const hhi = data.competitive?.hhi_index;
  const funding = data.funding?.total_funding;
  const topH = data.research_impact?.top_institutions?.[0]?.h_index;
  // geographic.countries is the transformed array from country_distribution
  const countryCount = data.geographic?.countries?.length ?? 0;
  // eu_share is actually cross_border_share (mapped in transform.ts)
  const crossBorder = data.geographic?.eu_share;
  // top3_share is a decimal (0.49 = 49%), multiply by 100 for display
  const top3Raw = data.competitive?.top3_share;
  const top3Pct = top3Raw !== undefined ? top3Raw * 100 : undefined;

  // HHI als natürlichsprachige Einschätzung
  const hhiLabel = hhi !== undefined
    ? hhi >= 2500 ? "Stark konzentrierter Markt"
      : hhi >= 1500 ? "Mäßig konzentrierter Markt"
      : "Wettbewerbsintensiver Markt"
    : undefined;

  // h-Index als natürlichsprachige Einschätzung
  const hLabel = topH !== undefined
    ? topH >= 100 ? "Sehr hoher Forschungsimpact"
      : topH >= 50 ? "Hoher Forschungsimpact"
      : topH >= 20 ? "Moderater Forschungsimpact"
      : "Geringer Forschungsimpact"
    : undefined;

  const badges: string[] = [];
  if (phase) badges.push(`Phase: ${phase}`);
  // CAGR als natürlichsprachige Einschätzung
  if (cagr !== undefined) {
    const cagrPct = cagr * 100;
    const cagrLabel = cagrPct > 15 ? "Sehr starkes Wachstum"
      : cagrPct > 5 ? "Starkes Wachstum"
      : cagrPct > 0 ? "Moderates Wachstum"
      : cagrPct > -5 ? "Stagnation"
      : "Rückläufige Entwicklung";
    badges.push(cagrLabel);
  }
  if (hhiLabel) badges.push(hhiLabel);
  if (funding) badges.push(`\u20AC${(funding / 1_000_000).toFixed(0)}M F\u00F6rderung`);
  if (hLabel) badges.push(hLabel);

  return {
    summary: {
      technology: data.metadata?.technology ?? "",
      text: badges.join(" \u00B7 "),
      badges,
      totalPatents: data.landscape?.total_patents ?? 0,
      totalProjects: data.landscape?.total_projects ?? 0,
      totalPublications: data.landscape?.total_publications ?? 0,
    },
    clusters: [
      {
        id: "technology",
        title: "Technologie & Reife",
        subtitle: `${phase}${cagr !== undefined ? ` (+${(cagr * 100).toFixed(1)}%/Jahr)` : ""}`,
        description: "Patentlandschaft, S-Kurven-Reife und CPC-Technologiekonvergenz",
        image: "/images/clusters/technology.png",
        metrics: [
          { label: "Phase", value: phase },
          { label: "R\u00B2", value: data.maturity?.r_squared?.toFixed(2) ?? "\u2014" },
          { label: "CAGR", value: cagr !== undefined ? `${(cagr * 100).toFixed(1)}%` : "\u2014" },
        ],
        ucKeys: ["landscape", "maturity", "cpc_flow"],
      },
      {
        id: "market",
        title: "Marktakteure",
        subtitle: `${data.competitive?.concentration ?? ""}, ${data.actor_type?.total_classified_actors ?? "?"} Akteure`,
        description: "Wettbewerber, Marktkonzentration und Akteurs-Dynamik",
        image: "/images/clusters/market.png",
        metrics: [
          { label: "HHI", value: hhi?.toFixed(2) ?? "\u2014" },
          { label: "Top-3", value: top3Pct !== undefined ? `${top3Pct.toFixed(1)}%` : "\u2014" },
        ],
        ucKeys: ["competitive", "temporal", "actor_type"],
      },
      {
        id: "research",
        title: "Forschung & F\u00F6rderung",
        subtitle: `${funding ? `\u20AC${(funding / 1_000_000).toFixed(0)}M` : "\u2014"}, h=${topH ?? "\u2014"}`,
        description: "EU-Förderung, Forschungsimpact und Publikationsanalyse",
        image: "/images/clusters/research.png",
        metrics: [
          { label: "F\u00F6rderung", value: funding ? `\u20AC${(funding / 1_000_000).toFixed(0)}M` : "\u2014" },
          { label: "h-Index", value: topH?.toString() ?? "\u2014" },
        ],
        ucKeys: ["funding", "research_impact", "publication"],
      },
      {
        id: "geography",
        title: "Geographische Perspektive",
        subtitle: `${countryCount} L\u00E4nder, ${crossBorder !== undefined ? `${(crossBorder * 100).toFixed(0)}% grenz\u00FCberschreitend` : ""}`,
        description: "Länderverteilung, Technologie-Cluster und Klassifikation",
        image: "/images/clusters/geography.png",
        metrics: [
          { label: "L\u00E4nder", value: countryCount > 0 ? countryCount.toString() : "\u2014" },
          { label: "Cross-Border", value: crossBorder !== undefined ? `${(crossBorder * 100).toFixed(0)}%` : "\u2014" },
        ],
        ucKeys: ["geographic", "tech_cluster", "euroscivoc", "patent_grant"],
      },
    ],
  };
}
