"use client";

import { ResponsiveHeatMap } from "@nivo/heatmap";
import type { CpcFlowNode, CpcFlowLink } from "@/lib/types";

interface CpcHeatmapProps {
  nodes: CpcFlowNode[];
  links: CpcFlowLink[];
}

export default function CpcHeatmap({ nodes, links }: CpcHeatmapProps) {
  const indexMap = new Map<string, number>();
  nodes.forEach((node, i) => indexMap.set(node.id, i));

  const n = nodes.length;
  const simMatrix: number[][] = Array.from({ length: n }, () => new Array(n).fill(0));
  const coOccMatrix: number[][] = Array.from({ length: n }, () => new Array(n).fill(0));

  for (const link of links) {
    const si = indexMap.get(link.source);
    const ti = indexMap.get(link.target);
    if (si !== undefined && ti !== undefined) {
      simMatrix[si][ti] = Math.max(simMatrix[si][ti], link.similarity);
      simMatrix[ti][si] = Math.max(simMatrix[ti][si], link.similarity);
      coOccMatrix[si][ti] += link.value;
      coOccMatrix[ti][si] += link.value;
    }
  }

  // Pruefen ob Jaccard-Daten vorhanden sind — sonst Fallback auf Co-Occurrence
  const hasJaccard = simMatrix.flat().some((v) => v > 0);
  const displayMatrix = hasJaccard ? simMatrix : coOccMatrix;
  const metricLabel = hasJaccard ? "Jaccard" : "Co-Occurrence";
  const maxVal = Math.max(0.01, ...displayMatrix.flat());

  // Nivo Heatmap Format
  const heatmapData = nodes.map((row, i) => ({
    id: row.id,
    data: nodes.map((col, j) => ({
      x: col.id,
      y: displayMatrix[i][j],
      // Beide Werte fuer Tooltip verfuegbar machen
      jaccard: simMatrix[i][j],
      coOcc: coOccMatrix[i][j],
    })),
  }));

  const showLabels = nodes.length <= 8;

  return (
    <ResponsiveHeatMap
      data={heatmapData}
      margin={{
        top: 40,
        right: 10,
        bottom: 10,
        left: 50,
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
        scheme: "blues",
        minValue: 0,
        maxValue: maxVal,
      }}
      emptyColor="var(--color-bg-primary)"
      borderWidth={1}
      borderColor="var(--color-bg-panel)"
      enableLabels={showLabels}
      label={({ data }) =>
        hasJaccard
          ? Number(data.y).toFixed(2)
          : Number(data.y).toLocaleString("de-DE")
      }
      labelTextColor={{
        from: "color",
        modifiers: [["darker", 2.5]],
      }}
      tooltip={({ cell }) => {
        const extra = cell.data as any;
        const jac = extra.jaccard ?? 0;
        const coOcc = extra.coOcc ?? 0;
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
            <strong>{cell.serieId}</strong> ↔ <strong>{cell.data.x}</strong>
            <br />
            {jac > 0 && <>Jaccard: {Number(jac).toFixed(3)}<br /></>}
            Co-Occurrence: {Number(coOcc).toLocaleString("de-DE")}
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
