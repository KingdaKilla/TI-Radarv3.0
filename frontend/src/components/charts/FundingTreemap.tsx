"use client";

import { ResponsiveTreeMap } from "@nivo/treemap";
import type { FundingEntry } from "@/lib/types";

interface FundingTreemapProps {
  data: FundingEntry[];
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)} Mrd.`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)} Mio.`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)} Tsd.`;
  return `${value.toFixed(0)}`;
}

const COLORS = ["#22c55e", "#16a34a", "#15803d", "#166534", "#14532d", "#0f766e", "#0d9488", "#2dd4bf"];

export default function FundingTreemap({ data }: FundingTreemapProps) {
  const treemapData = {
    name: "Förderung",
    children: data.map((entry, idx) => ({
      name: entry.program,
      value: entry.total_funding,
      projectCount: entry.project_count,
      color: COLORS[idx % COLORS.length],
    })),
  };

  return (
    <ResponsiveTreeMap
      data={treemapData}
      identity="name"
      value="value"
      leavesOnly={true}
      margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
      label={(node) => {
        if (node.width < 50 || node.height < 25) return "";
        const maxChars = Math.floor(node.width / 7);
        const name = String(node.id);
        return name.length > maxChars ? name.slice(0, maxChars - 1).trimEnd() + "\u2026" : name;
      }}
      labelSkipSize={25}
      labelTextColor={{
        from: "color",
        modifiers: [["darker", 3]],
      }}
      parentLabelTextColor={{
        from: "color",
        modifiers: [["darker", 3]],
      }}
      colors={(node) => {
        const idx = treemapData.children.findIndex((c) => c.name === node.id);
        return COLORS[idx >= 0 ? idx % COLORS.length : 0];
      }}
      borderWidth={2}
      borderColor="var(--color-bg-panel)"
      tooltip={({ node }) => (
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
          <strong>{node.id}</strong>
          <br />
          {formatCurrency(node.value)} EUR
          <br />
          {(node.data as { projectCount?: number })?.projectCount?.toLocaleString("de-DE") ?? "?"} Projekte
        </div>
      )}
      theme={{
        text: {
          fontSize: 10,
          fill: "var(--color-text-primary)",
        },
        labels: {
          text: {
            fontSize: 10,
            fontWeight: 600,
          },
        },
      }}
      animate={true}
      motionConfig="gentle"
    />
  );
}
