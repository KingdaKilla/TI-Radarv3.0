/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Cluster Data Model
 * Maps 13 UC panels into 4 thematic clusters
 * for progressive disclosure dashboard
 * ────────────────────────────────────────────── */

import type { CompetitivePanel, RadarResponse, UseCaseKey } from "./types";
import { METRIC_TOOLTIPS } from "./metric-tooltips";

// INFO-12: Single Source of Truth fuer die h-Index-Schwellen-Erklaerung,
// die der ExecutiveSummary-Tooltip beim Hover auf den Impact-Badge anzeigt.
const H_INDEX_THRESHOLD_TOOLTIP = METRIC_TOOLTIPS.h_index_thresholds;

/* ──────────────────────────────────────────────
 * AP7 / MAJ-5: Trend-Klassifikation aus dem CAGR.
 * Bewusst nur drei Stufen — die feinabgestuften
 * Marketing-Texte ("Sehr starkes Wachstum") werden
 * nicht mehr als zweite Phase verkauft, sondern
 * landen in einem eigenen Badge-Slot "Trend: ...".
 *
 * Schwelle ±2 % p. a. trennt Stagnation von echtem
 * Wachstum / Rueckgang.
 * ────────────────────────────────────────────── */
export type TrendLabel = "Wachstum" | "Stagnation" | "Rückgang";

export function trendFromCagr(cagr: number): TrendLabel {
  const pct = cagr * 100;
  if (pct > 2) return "Wachstum";
  if (pct < -2) return "Rückgang";
  return "Stagnation";
}

/* ──────────────────────────────────────────────
 * AP7 / MAJ-6: Konzentrations-Label aus UC3.
 *
 * Bevorzugt das Backend-Feld `concentration`
 * (CompetitivePanel.concentration). Fehlt es, faellt
 * die Funktion auf eine HHI-Heuristik zurueck — in
 * keinem Fall wird der frueher hartcodierte Fallback
 * "Wettbewerbsintensiver Markt" verwendet.
 *
 * HHI-Schwellen folgen der gaengigen Definition:
 *   HHI < 1500  → niedrig  ("Niedrige Konzentration")
 *   HHI < 2500  → mittel   ("Moderate Konzentration")
 *   sonst       → hoch     ("Hohe Konzentration")
 * ────────────────────────────────────────────── */
export type ConcentrationLevel = "niedrig" | "mittel" | "hoch";

const CONCENTRATION_BADGE_LABEL: Record<ConcentrationLevel, string> = {
  niedrig: "Niedrige Konzentration",
  mittel: "Moderate Konzentration",
  hoch: "Hohe Konzentration",
};

export function concentrationLevelFromHhi(hhi: number): ConcentrationLevel {
  if (hhi >= 2500) return "hoch";
  if (hhi >= 1500) return "mittel";
  return "niedrig";
}

export function concentrationBadge(
  competitive: Pick<CompetitivePanel, "hhi_index" | "concentration"> | null | undefined,
): string | undefined {
  if (!competitive) return undefined;
  const level: ConcentrationLevel | undefined =
    competitive.concentration ??
    (typeof competitive.hhi_index === "number"
      ? concentrationLevelFromHhi(competitive.hhi_index)
      : undefined);
  return level ? CONCENTRATION_BADGE_LABEL[level] : undefined;
}

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
    /** INFO-12: Optionale Tooltip-Texte fuer einzelne Badges.
     *  Key = exakter Badge-Text (z. B. "Sehr hoher Impact (h=120)"),
     *  Value = Erklaerungstext fuer den InfoTooltip (z. B. die
     *  hartcodierten h-Index-Schwellen). Fehlt der Key, rendert die UI
     *  keinen Info-Icon.
     */
    badgeTooltips?: Record<string, string>;
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

  // AP7 / MAJ-6: Konzentrations-Badge bevorzugt das Backend-Label aus UC3
  // (CompetitivePanel.concentration); fehlt es, wird die HHI-Schwelle
  // genutzt. Niemals der alte Fallback "Wettbewerbsintensiver Markt".
  const hhiLabel = concentrationBadge(data.competitive ?? undefined);

  // h-Index als natürlichsprachige Einschätzung.
  // INFO-12: Schwellen sind hartcodiert (100/50/20). Damit Nutzer den
  // qualitativen Begriff (z. B. „Sehr hoher Impact") mit dem konkreten
  // Zahlenwert belegen koennen, wird der h-Index inline mitgegeben:
  //   "Sehr hoher Impact (h=120)" statt nur "Sehr hoher Forschungsimpact".
  // Die Schwellen selbst werden in `metric-tooltips.ts` als Tooltip
  // hinterlegt (Key: H_INDEX_THRESHOLDS).
  const hLabelBase = topH !== undefined
    ? topH >= 100 ? "Sehr hoher Impact"
      : topH >= 50 ? "Hoher Impact"
      : topH >= 20 ? "Moderater Impact"
      : "Geringer Impact"
    : undefined;
  const hLabel = hLabelBase !== undefined && topH !== undefined
    ? `${hLabelBase} (h=${topH})`
    : undefined;

  // AP7 / MAJ-5: Phase- und Trend-Badge stehen in *getrennten* Slots.
  // - Phase  = exakt das UC2-`phase_label` (kein Anhaengsel mehr).
  // - Trend  = grobe CAGR-Klassifikation in eigenem Slot "Trend: ...".
  // Damit verschwindet die irrefuehrende Verkettung
  // "Reife + Rueckläufige Entwicklung".
  const phaseBadge =
    data.maturity?.phase_label && data.maturity.phase_label.trim().length > 0
      ? `Phase: ${data.maturity.phase_label}`
      : undefined;
  const trendBadge =
    cagr !== undefined ? `Trend: ${trendFromCagr(cagr)}` : undefined;

  const badges: string[] = [];
  if (phaseBadge) badges.push(phaseBadge);
  if (trendBadge) badges.push(trendBadge);
  if (hhiLabel) badges.push(hhiLabel);
  if (funding) badges.push(`\u20AC${(funding / 1_000_000).toFixed(0)}M F\u00F6rderung`);
  if (hLabel) badges.push(hLabel);

  // INFO-12: Tooltip-Texte fuer Badges, die hartcodierte Schwellen-Werte
  // erklaeren. Aktuell nur fuer den h-Index-Impact-Badge.
  const badgeTooltips: Record<string, string> = {};
  if (hLabel) {
    badgeTooltips[hLabel] = H_INDEX_THRESHOLD_TOOLTIP;
  }

  return {
    summary: {
      technology: data.metadata?.technology ?? "",
      text: badges.join(" \u00B7 "),
      badges,
      badgeTooltips,
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
