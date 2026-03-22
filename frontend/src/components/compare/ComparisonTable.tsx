"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- Vergleichstabelle
 * Zeigt Kennzahlen zweier Technologien
 * nebeneinander in einer Tabelle
 * ────────────────────────────────────────────── */

import type { RadarResponse } from "@/lib/types";

interface ComparisonTableProps {
  techA: { name: string; data: RadarResponse };
  techB: { name: string; data: RadarResponse };
}

/** Formatiert eine Zahl mit optionaler Nachkommastelle */
function fmt(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined) return "–";
  return value.toLocaleString("de-DE", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/** Formatiert Prozentwerte */
function fmtPct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "–";
  return `${fmt(value * 100, 1)} %`;
}

/** Bestimmt welche Zelle "besser" ist (gruen hervorgehoben) */
function betterClass(
  a: number | null | undefined,
  b: number | null | undefined,
  higherIsBetter: boolean
): [string, string] {
  if (a == null || b == null || a === b) return ["", ""];
  const aWins = higherIsBetter ? a > b : a < b;
  const highlight =
    "font-semibold text-[var(--color-success)]";
  return aWins ? [highlight, ""] : ["", highlight];
}

/** Konzentrations-Label */
function concentrationLabel(
  level: "niedrig" | "mittel" | "hoch" | undefined
): string {
  if (!level) return "–";
  return level.charAt(0).toUpperCase() + level.slice(1);
}

/** Reifephase-Label */
function phaseLabel(
  phase: string | undefined
): string {
  if (!phase) return "–";
  const labels: Record<string, string> = {
    emergence: "Entstehung",
    growth: "Wachstum",
    maturity: "Reife",
    saturation: "Sättigung",
    decline: "Rückgang",
  };
  return labels[phase] ?? phase;
}

export default function ComparisonTable({ techA, techB }: ComparisonTableProps) {
  const a = techA.data;
  const b = techB.data;

  /** Zeilen-Definition: [Label, Wert A, Wert B, CSS-Klassen A, CSS-Klassen B] */
  type Row = [string, string, string, string, string];

  const cagrPatA = a.landscape?.cagr_patents ?? null;
  const cagrPatB = b.landscape?.cagr_patents ?? null;
  const [cpA, cpB] = betterClass(cagrPatA, cagrPatB, true);

  const cagrPrjA = a.landscape?.cagr_projects ?? null;
  const cagrPrjB = b.landscape?.cagr_projects ?? null;
  const [cprA, cprB] = betterClass(cagrPrjA, cagrPrjB, true);

  const hhiA = a.competitive?.hhi_index ?? null;
  const hhiB = b.competitive?.hhi_index ?? null;
  const [hA, hB] = betterClass(hhiA, hhiB, false); // niedrigerer HHI = diverser

  const r2A = a.maturity?.r_squared ?? null;
  const r2B = b.maturity?.r_squared ?? null;
  const [rA, rB] = betterClass(r2A, r2B, true);

  const totalPatA = a.landscape?.total_patents ?? null;
  const totalPatB = b.landscape?.total_patents ?? null;
  const [tpA, tpB] = betterClass(totalPatA, totalPatB, true);

  const totalPrjA = a.landscape?.total_projects ?? null;
  const totalPrjB = b.landscape?.total_projects ?? null;
  const [tprA, tprB] = betterClass(totalPrjA, totalPrjB, true);

  const euShareA = a.geographic?.eu_share ?? null;
  const euShareB = b.geographic?.eu_share ?? null;
  const [eA, eB] = betterClass(euShareA, euShareB, true);

  const totalPapA = a.research_impact?.total_papers ?? null;
  const totalPapB = b.research_impact?.total_papers ?? null;
  const [papA, papB] = betterClass(totalPapA, totalPapB, true);

  const hIdxA = a.research_impact?.top_institutions?.[0]?.h_index ?? null;
  const hIdxB = b.research_impact?.top_institutions?.[0]?.h_index ?? null;
  const [hiA, hiB] = betterClass(hIdxA, hIdxB, true);

  const rows: Row[] = [
    ["CAGR (Patente)", `${fmt(cagrPatA)} %`, `${fmt(cagrPatB)} %`, cpA, cpB],
    ["CAGR (Projekte)", `${fmt(cagrPrjA)} %`, `${fmt(cagrPrjB)} %`, cprA, cprB],
    ["HHI-Index", fmt(hhiA, 0), fmt(hhiB, 0), hA, hB],
    [
      "Konzentration",
      concentrationLabel(a.competitive?.concentration),
      concentrationLabel(b.competitive?.concentration),
      "",
      "",
    ],
    [
      "Reifephase",
      phaseLabel(a.maturity?.phase),
      phaseLabel(b.maturity?.phase),
      "",
      "",
    ],
    ["R\u00B2 (S-Kurve)", fmt(r2A, 3), fmt(r2B, 3), rA, rB],
    [
      "Top-Land",
      a.geographic?.top_country ?? "–",
      b.geographic?.top_country ?? "–",
      "",
      "",
    ],
    ["EU-Anteil", fmtPct(euShareA), fmtPct(euShareB), eA, eB],
    ["Patente gesamt", fmt(totalPatA, 0), fmt(totalPatB, 0), tpA, tpB],
    ["Projekte gesamt", fmt(totalPrjA, 0), fmt(totalPrjB, 0), tprA, tprB],
    ["h-Index (Top)", fmt(hIdxA, 0), fmt(hIdxB, 0), hiA, hiB],
    ["Publikationen gesamt", fmt(totalPapA, 0), fmt(totalPapB, 0), papA, papB],
  ];

  return (
    <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)]">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
            <th className="px-4 py-3 text-left font-medium text-[var(--color-text-secondary)]">
              Kennzahl
            </th>
            <th className="px-4 py-3 text-right font-semibold text-[var(--color-accent)]">
              {techA.name}
            </th>
            <th className="px-4 py-3 text-right font-semibold text-[var(--color-chart-2)]">
              {techB.name}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, valA, valB, clsA, clsB], i) => (
            <tr
              key={label}
              className={
                i % 2 === 0
                  ? ""
                  : "bg-[var(--color-bg-secondary)]/30"
              }
            >
              <td className="px-4 py-2.5 text-[var(--color-text-secondary)]">
                {label}
              </td>
              <td className={`px-4 py-2.5 text-right tabular-nums text-[var(--color-text-primary)] ${clsA}`}>
                {valA}
              </td>
              <td className={`px-4 py-2.5 text-right tabular-nums text-[var(--color-text-primary)] ${clsB}`}>
                {valB}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
