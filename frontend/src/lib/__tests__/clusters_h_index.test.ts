/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Tests fuer h-Index-Impact-Badge (INFO-12)
 *
 * Konsistenz-Audit INFO-12: Der Header-Badge "Sehr hoher Forschungsimpact"
 * wurde aus hartcodierten h-Index-Schwellen abgeleitet (100/50/20), aber
 * weder Wert noch Schwellen waren fuer den Nutzer sichtbar.
 *
 * Erwartung nach Fix:
 *  - Badge enthaelt den konkreten h-Index-Wert: "Sehr hoher Impact (h=120)".
 *  - In `summary.badgeTooltips` liegt ein Erklaerungstext mit den Schwellen.
 * ────────────────────────────────────────────── */

import { describe, expect, it } from "vitest";

import { buildClusterData } from "../clusters";
import { METRIC_TOOLTIPS } from "../metric-tooltips";
import type { RadarResponse } from "../types";

function makeResponse(topH: number | undefined): RadarResponse {
  const research_impact = topH !== undefined
    ? ({
        top_institutions: [
          { name: "Top Inst", h_index: topH, country: "DE", paper_count: 0 },
        ],
        // Folgende Felder sind fuer diesen Test irrelevant, muessen aber
        // typkompatibel sein.
        avg_h_index: topH,
        median_h_index: topH,
        total_papers: 0,
        total_citations: 0,
        annual_pubs: [],
      } as unknown as RadarResponse["research_impact"])
    : null;

  return {
    landscape: null,
    maturity: null,
    competitive: null,
    funding: null,
    cpc_flow: null,
    geographic: null,
    research_impact,
    temporal: null,
    tech_cluster: null,
    euroscivoc: null,
    actor_type: null,
    patent_grant: null,
    publication: null,
    uc_errors: {},
    metadata: {
      technology: "Test-Tech",
      time_range: 10,
      european_only: true,
      query_time_seconds: 0,
      data_sources: [],
      timestamp: "2026-04-14T00:00:00Z",
    },
  };
}

describe("buildClusterData – Impact-Badge zeigt h-Wert + Tooltip (INFO-12)", () => {
  it("h=120 erzeugt 'Sehr hoher Impact (h=120)' statt nur Label", () => {
    const { summary } = buildClusterData(makeResponse(120));
    expect(summary.badges).toContain("Sehr hoher Impact (h=120)");
    // Das alte rein-qualitative Label darf nicht mehr auftauchen.
    expect(summary.badges).not.toContain("Sehr hoher Forschungsimpact");
  });

  it("h=75 -> 'Hoher Impact (h=75)'", () => {
    const { summary } = buildClusterData(makeResponse(75));
    expect(summary.badges).toContain("Hoher Impact (h=75)");
  });

  it("h=35 -> 'Moderater Impact (h=35)'", () => {
    const { summary } = buildClusterData(makeResponse(35));
    expect(summary.badges).toContain("Moderater Impact (h=35)");
  });

  it("h=10 -> 'Geringer Impact (h=10)'", () => {
    const { summary } = buildClusterData(makeResponse(10));
    expect(summary.badges).toContain("Geringer Impact (h=10)");
  });

  it("kein h-Index -> kein Impact-Badge, kein Tooltip", () => {
    const { summary } = buildClusterData(makeResponse(undefined));
    expect(
      summary.badges.some((b) => b.toLowerCase().includes("impact")),
    ).toBe(false);
    expect(summary.badgeTooltips ?? {}).toEqual({});
  });

  it("hinterlegt Tooltip-Text mit den Schwellen-Werten am Impact-Badge", () => {
    const { summary } = buildClusterData(makeResponse(120));
    const badge = "Sehr hoher Impact (h=120)";
    const tooltip = summary.badgeTooltips?.[badge];
    expect(tooltip).toBeDefined();
    // Tooltip muss alle vier Schwellen nennen, damit der Nutzer die
    // qualitative Einstufung verifizieren kann.
    expect(tooltip).toContain("100");
    expect(tooltip).toContain("50");
    expect(tooltip).toContain("20");
    // Single-Source-of-Truth: der Tooltip kommt aus METRIC_TOOLTIPS.
    expect(tooltip).toBe(METRIC_TOOLTIPS.h_index_thresholds);
  });
});
