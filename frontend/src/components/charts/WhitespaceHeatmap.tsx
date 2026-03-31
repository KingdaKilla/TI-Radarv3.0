"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC5: Whitespace Opportunity Heatmap
 * Visualisiert Opportunity Scores als Heatmap
 * ueber der Whitespace-Analyse-Tabelle
 * ────────────────────────────────────────────── */

import { ResponsiveHeatMap } from "@nivo/heatmap";
import type { WhitespaceOpportunity } from "@/lib/types";

interface WhitespaceHeatmapProps {
  opportunities: WhitespaceOpportunity[];
  cpcLabels: Record<string, string>;
}

export default function WhitespaceHeatmap({
  opportunities,
  cpcLabels,
}: WhitespaceHeatmapProps) {
  // Unique CPC-Codes extrahieren
  const codeSet = new Set<string>();
  for (const ws of opportunities) {
    codeSet.add(ws.code_a);
    codeSet.add(ws.code_b);
  }
  const codes = Array.from(codeSet).sort();

  if (codes.length < 2) return null;

  // Lookup: code-paar → opportunity data
  const pairMap = new Map<string, WhitespaceOpportunity>();
  for (const ws of opportunities) {
    const keyAB = `${ws.code_a}:${ws.code_b}`;
    const keyBA = `${ws.code_b}:${ws.code_a}`;
    pairMap.set(keyAB, ws);
    pairMap.set(keyBA, ws);
  }

  // Max-Wert fuer Farbskala
  const maxScore = Math.max(
    0.01,
    ...opportunities.map((ws) => ws.opportunity_score),
  );

  // Nivo HeatMap Format
  const heatmapData = codes.map((rowCode) => ({
    id: rowCode,
    data: codes.map((colCode) => {
      const pair = pairMap.get(`${rowCode}:${colCode}`);
      return {
        x: colCode,
        y: pair ? pair.opportunity_score : 0,
        // Zusaetzliche Tooltip-Daten
        jaccard: pair?.jaccard ?? 0,
        freqA: pair?.freq_a ?? 0,
        freqB: pair?.freq_b ?? 0,
        codeA: rowCode,
        codeB: colCode,
      };
    }),
  }));

  const showLabels = codes.length <= 8;

  return (
    <ResponsiveHeatMap
      data={heatmapData}
      margin={{
        top: 50,
        right: 10,
        bottom: 10,
        left: 60,
      }}
      axisTop={{
        tickSize: 0,
        tickPadding: 5,
        tickRotation: -45,
        legend: "",
        legendOffset: 0,
        truncateTickAt: 0,
      }}
      axisLeft={{
        tickSize: 0,
        tickPadding: 5,
        tickRotation: 0,
        legend: "",
        legendOffset: 0,
        truncateTickAt: 0,
      }}
      axisRight={null}
      axisBottom={null}
      colors={{
        type: "sequential",
        scheme: "oranges",
        minValue: 0,
        maxValue: maxScore,
      }}
      emptyColor="var(--color-bg-primary)"
      borderWidth={1}
      borderColor="var(--color-bg-panel)"
      enableLabels={showLabels}
      label={({ data }) =>
        Number(data.y) > 0 ? Number(data.y).toFixed(2) : ""
      }
      labelTextColor={{
        from: "color",
        modifiers: [["darker", 2.5]],
      }}
      tooltip={({ cell }) => {
        const extra = cell.data as Record<string, unknown>;
        const score = Number(cell.data.y ?? 0);
        const jac = Number(extra.jaccard ?? 0);
        const freqA = Number(extra.freqA ?? 0);
        const freqB = Number(extra.freqB ?? 0);
        const codeA = String(extra.codeA ?? cell.serieId);
        const codeB = String(extra.codeB ?? cell.data.x);

        if (score === 0) {
          return (
            <div
              style={{
                backgroundColor: "var(--color-bg-panel)",
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
                padding: "8px 12px",
                fontSize: "12px",
                color: "var(--color-text-muted)",
              }}
            >
              {codeA} ↔ {codeB}: Kein Whitespace-Paar
            </div>
          );
        }

        return (
          <div
            style={{
              backgroundColor: "var(--color-bg-panel)",
              border: "1px solid var(--color-border)",
              borderRadius: "8px",
              padding: "8px 12px",
              fontSize: "12px",
              color: "var(--color-text-primary)",
            }}
          >
            <strong>{codeA}</strong> ↔ <strong>{codeB}</strong>
            <br />
            {cpcLabels[codeA] && (
              <span style={{ color: "var(--color-text-muted)", fontSize: "11px" }}>
                {cpcLabels[codeA]} × {cpcLabels[codeB]}
                <br />
              </span>
            )}
            Opportunity Score: <strong>{score.toFixed(2)}</strong>
            <br />
            Jaccard: {jac.toFixed(3)}
            <br />
            Patente: {freqA.toLocaleString("de-DE")} / {freqB.toLocaleString("de-DE")}
          </div>
        );
      }}
      theme={{
        text: {
          fontSize: 10,
          fill: "var(--color-text-muted)",
        },
      }}
      animate={true}
      motionConfig="gentle"
    />
  );
}
