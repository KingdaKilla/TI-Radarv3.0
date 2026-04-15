/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Tests for buildClusterData (AP7)
 *
 * Konsistenz-Audit MAJ-5 + MAJ-6:
 *  - Phase und Trend müssen in **getrennten** Badge-Slots stehen
 *    (kein „Reife + Rückläufige Entwicklung" mehr).
 *  - HHI-Label muss aus der echten Konzentration abgeleitet werden;
 *    insbesondere darf bei HHI < 1500 NIE „Wettbewerbsintensiv"
 *    erscheinen, sondern „Niedrige Konzentration".
 * ────────────────────────────────────────────── */

import { describe, expect, it } from "vitest";

import { buildClusterData } from "../clusters";
import type { RadarResponse } from "../types";

/** Minimal RadarResponse stub.  Felder, die der Test nicht braucht,
 *  werden bewusst auf null gesetzt – `buildClusterData` muss damit
 *  umgehen können. */
function makeResponse(overrides: {
  phase_label?: string | null;
  cagr?: number;
  hhi?: number;
  concentration?: "niedrig" | "mittel" | "hoch";
  technology?: string;
}): RadarResponse {
  const phaseLabel = overrides.phase_label;
  const maturity =
    overrides.cagr !== undefined || phaseLabel !== undefined
      ? ({
          phase: "maturity",
          phase_label: (phaseLabel ?? "") as string,
          s_curve_data: [],
          inflection_year: null,
          r_squared: 0,
          saturation_level: 0,
          data_complete_year: null,
          maturity_percent: 0,
          cagr: overrides.cagr ?? 0,
          model_name: "logistic",
          aicc_selected: 0,
          aicc_alternative: 0,
          delta_aicc: 0,
          confidence: 0,
          fit_reliability_flag: false,
        } as RadarResponse["maturity"])
      : null;

  const competitive =
    overrides.hhi !== undefined
      ? ({
          top_assignees: [],
          hhi_index: overrides.hhi,
          concentration: overrides.concentration ?? "niedrig",
          cr4_share: 0,
          top3_share: 0,
          top10_share: 0,
          total_actors: 0,
          hhi_trend: [],
          network_nodes: [],
          network_edges: [],
        } as RadarResponse["competitive"])
      : null;

  return {
    landscape: null,
    maturity,
    competitive,
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
    metadata: {
      technology: overrides.technology ?? "Test-Tech",
      time_range: 10,
      european_only: true,
      query_time_seconds: 0,
      data_sources: [],
      timestamp: "2026-04-14T00:00:00Z",
    },
  };
}

describe("buildClusterData – Badge-Erzeugung (AP7 / MAJ-5 + MAJ-6)", () => {
  it("trennt Phase, Trend und Konzentration in eigene Badges (Rückgang + niedriger HHI)", () => {
    const data = makeResponse({
      phase_label: "Reife",
      cagr: -0.05,
      hhi: 800,
      concentration: "niedrig",
    });

    const { summary } = buildClusterData(data);

    expect(summary.badges).toEqual(
      expect.arrayContaining([
        "Phase: Reife",
        "Trend: Rückgang",
        "Niedrige Konzentration",
      ]),
    );
    // MAJ-5: Phase darf NICHT mit Trend konkateniert sein
    expect(summary.badges).not.toContain("Reife + Rückläufige Entwicklung");
    expect(summary.badges.find((b) => b.startsWith("Phase:"))).toBe(
      "Phase: Reife",
    );
  });

  it("erzeugt für Wachstum + hohe Konzentration korrekte Labels", () => {
    const data = makeResponse({
      phase_label: "Wachstum",
      cagr: 0.15,
      hhi: 3000,
      concentration: "hoch",
    });

    const { summary } = buildClusterData(data);

    expect(summary.badges).toEqual(
      expect.arrayContaining([
        "Phase: Wachstum",
        "Trend: Wachstum",
        "Hohe Konzentration",
      ]),
    );
  });

  it("lässt Phase-Badge weg, wenn phase_label fehlt; Trend = Stagnation, HHI = Moderat", () => {
    const data = makeResponse({
      phase_label: null,
      cagr: 0.01,
      hhi: 1500,
      concentration: "mittel",
    });

    const { summary } = buildClusterData(data);

    expect(summary.badges.some((b) => b.startsWith("Phase:"))).toBe(false);
    expect(summary.badges).toEqual(
      expect.arrayContaining(["Trend: Stagnation", "Moderate Konzentration"]),
    );
  });

  it('verwendet NIEMALS das alte Fallback-Label "Wettbewerbsintensiv" (MAJ-6)', () => {
    const samples: Array<{ hhi: number; concentration: "niedrig" | "mittel" | "hoch" }> = [
      { hhi: 200, concentration: "niedrig" },
      { hhi: 1499, concentration: "niedrig" },
      { hhi: 1500, concentration: "mittel" },
      { hhi: 2499, concentration: "mittel" },
      { hhi: 2500, concentration: "hoch" },
      { hhi: 9000, concentration: "hoch" },
    ];

    for (const s of samples) {
      const { summary } = buildClusterData(
        makeResponse({ phase_label: "Reife", cagr: 0.05, ...s }),
      );
      for (const badge of summary.badges) {
        expect(badge.toLowerCase()).not.toContain("wettbewerbsintensiv");
      }
    }
  });

  it("nutzt das Backend-Konzentrations-Feld (concentration) und nicht die HHI-Heuristik allein", () => {
    // Backend sagt „hoch", obwohl HHI < 1500 (z. B. wegen alternativer Schwellen).
    // Frontend muss dem Backend folgen.
    const data = makeResponse({
      phase_label: "Reife",
      cagr: 0.05,
      hhi: 800,
      concentration: "hoch",
    });

    const { summary } = buildClusterData(data);
    expect(summary.badges).toEqual(
      expect.arrayContaining(["Hohe Konzentration"]),
    );
    expect(summary.badges).not.toContain("Niedrige Konzentration");
  });
});
