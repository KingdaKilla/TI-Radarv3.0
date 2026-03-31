"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC5: CPC Chord-Diagramm
 * Visualisiert CPC-Code-Beziehungen als Chord-Diagramm
 * (ersetzt die vorherige Heatmap-Darstellung)
 * ────────────────────────────────────────────── */

import { ResponsiveChord } from "@nivo/chord";
import { PALETTE } from "@/lib/chart-colors";
import type { CpcFlowNode, CpcFlowLink } from "@/lib/types";

interface CpcChordDiagramProps {
  nodes: CpcFlowNode[];
  links: CpcFlowLink[];
}

/** Erweiterte Palette fuer >8 Nodes */
const CHORD_COLORS = [
  ...PALETTE,
  "#00b4d8", // Cyan
  "#8338ec", // Violet
  "#ff006e", // Magenta
  "#fb5607", // Tangerine
];

export default function CpcChordDiagram({ nodes, links }: CpcChordDiagramProps) {
  const indexMap = new Map<string, number>();
  nodes.forEach((node, i) => indexMap.set(node.id, i));

  const n = nodes.length;
  const matrix: number[][] = Array.from({ length: n }, () => new Array(n).fill(0));

  // Lookup fuer Tooltip-Daten (Jaccard + Co-Occurrence pro Paar)
  const pairData = new Map<string, { jaccard: number; coOcc: number }>();

  for (const link of links) {
    const si = indexMap.get(link.source);
    const ti = indexMap.get(link.target);
    if (si !== undefined && ti !== undefined) {
      // Jaccard als primaere Metrik, Fallback auf Co-Occurrence
      const weight = link.similarity > 0
        ? Math.round(link.similarity * 1000)
        : link.value;
      matrix[si][ti] = Math.max(matrix[si][ti], weight);
      matrix[ti][si] = Math.max(matrix[ti][si], weight);

      const key = si < ti ? `${si}:${ti}` : `${ti}:${si}`;
      const existing = pairData.get(key);
      if (!existing || link.similarity > existing.jaccard) {
        pairData.set(key, { jaccard: link.similarity, coOcc: link.value });
      }
    }
  }

  // Pruefen ob Matrix komplett leer ist
  const hasData = matrix.some((row) => row.some((v) => v > 0));
  if (!hasData) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm italic text-[var(--color-text-muted)]">
          Keine ausreichenden Daten fuer die Chord-Darstellung.
        </p>
      </div>
    );
  }

  const keys = nodes.map((node) => node.id);
  const hasJaccard = links.some((l) => l.similarity > 0);

  // Label-Lookup fuer Tooltips
  const labelMap: Record<string, string> = {};
  for (const node of nodes) {
    labelMap[node.id] = node.label;
  }

  return (
    <ResponsiveChord
      data={matrix}
      keys={keys}
      margin={{ top: 40, right: 40, bottom: 40, left: 40 }}
      padAngle={0.04}
      innerRadiusRatio={0.96}
      innerRadiusOffset={0.02}
      arcOpacity={1}
      arcBorderWidth={1}
      arcBorderColor={{ from: "color", modifiers: [["darker", 0.4]] }}
      ribbonOpacity={0.6}
      ribbonBorderWidth={1}
      ribbonBorderColor={{ from: "color", modifiers: [["darker", 0.4]] }}
      enableLabel={nodes.length <= 12}
      label="id"
      labelOffset={12}
      labelRotation={-90}
      labelTextColor={{ from: "color", modifiers: [["darker", 1.5]] }}
      colors={CHORD_COLORS.slice(0, Math.max(n, 1))}
      arcTooltip={({ arc }) => (
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
          <strong>{arc.id}</strong>
          {labelMap[arc.id] && (
            <>
              <br />
              <span style={{ color: "var(--color-text-muted)" }}>
                {labelMap[arc.id]}
              </span>
            </>
          )}
        </div>
      )}
      ribbonTooltip={({ ribbon }) => {
        const si = indexMap.get(ribbon.source.id) ?? 0;
        const ti = indexMap.get(ribbon.target.id) ?? 0;
        const key = si < ti ? `${si}:${ti}` : `${ti}:${si}`;
        const pair = pairData.get(key);
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
            <strong>{ribbon.source.id}</strong> ↔ <strong>{ribbon.target.id}</strong>
            {pair && (
              <>
                <br />
                {pair.jaccard > 0 && (
                  <>Jaccard: {pair.jaccard.toFixed(3)}<br /></>
                )}
                Co-Occurrence: {pair.coOcc.toLocaleString("de-DE")}
              </>
            )}
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
