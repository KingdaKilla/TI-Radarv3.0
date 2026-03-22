"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- Vergleichs-Radar
 * Recharts RadarChart mit zwei Technologien als
 * ueberlagerte Polygone (normalisierte Achsen)
 * ────────────────────────────────────────────── */

import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { RadarResponse } from "@/lib/types";

interface ComparisonRadarProps {
  techA: { name: string; data: RadarResponse };
  techB: { name: string; data: RadarResponse };
}

/** Normalisiert einen Wert in den Bereich [0, 100] */
function normalize(
  value: number | null | undefined,
  maxRef: number,
  invert = false
): number {
  if (value == null || maxRef === 0) return 0;
  const clamped = Math.min(Math.max(value / maxRef, 0), 1);
  return Math.round((invert ? 1 - clamped : clamped) * 100);
}

export default function ComparisonRadar({
  techA,
  techB,
}: ComparisonRadarProps) {
  const a = techA.data;
  const b = techB.data;

  // Referenzwerte fuer Normalisierung (Maximum beider Technologien)
  const maxPatents = Math.max(
    a.landscape?.total_patents ?? 0,
    b.landscape?.total_patents ?? 0,
    1
  );
  const maxProjects = Math.max(
    a.landscape?.total_projects ?? 0,
    b.landscape?.total_projects ?? 0,
    1
  );
  const maxHhi = 10_000; // HHI-Maximum ist immer 10.000
  const maxHindex = Math.max(
    a.research_impact?.top_institutions?.[0]?.h_index ?? 0,
    b.research_impact?.top_institutions?.[0]?.h_index ?? 0,
    1
  );
  const maxFunding = Math.max(
    a.funding?.total_funding ?? 0,
    b.funding?.total_funding ?? 0,
    1
  );

  const radarData = [
    {
      axis: "Patente",
      [techA.name]: normalize(a.landscape?.total_patents, maxPatents),
      [techB.name]: normalize(b.landscape?.total_patents, maxPatents),
    },
    {
      axis: "Projekte",
      [techA.name]: normalize(a.landscape?.total_projects, maxProjects),
      [techB.name]: normalize(b.landscape?.total_projects, maxProjects),
    },
    {
      axis: "HHI (inv.)",
      [techA.name]: normalize(a.competitive?.hhi_index, maxHhi, true),
      [techB.name]: normalize(b.competitive?.hhi_index, maxHhi, true),
    },
    {
      axis: "h-Index",
      [techA.name]: normalize(
        a.research_impact?.top_institutions?.[0]?.h_index,
        maxHindex
      ),
      [techB.name]: normalize(
        b.research_impact?.top_institutions?.[0]?.h_index,
        maxHindex
      ),
    },
    {
      axis: "Förderung",
      [techA.name]: normalize(a.funding?.total_funding, maxFunding),
      [techB.name]: normalize(b.funding?.total_funding, maxFunding),
    },
  ];

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)] p-4">
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-text-primary)]">
        Radar-Vergleich (normalisiert 0–100)
      </h3>
      <div className="h-80" aria-label="Radar-Vergleich zweier Technologien">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
            <PolarGrid stroke="var(--color-border)" />
            <PolarAngleAxis
              dataKey="axis"
              tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={false}
              axisLine={false}
            />
            <Radar
              name={techA.name}
              dataKey={techA.name}
              stroke="var(--color-chart-1)"
              fill="var(--color-chart-1)"
              fillOpacity={0.2}
              strokeWidth={2}
            />
            <Radar
              name={techB.name}
              dataKey={techB.name}
              stroke="var(--color-chart-2)"
              fill="var(--color-chart-2)"
              fillOpacity={0.2}
              strokeWidth={2}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--color-bg-panel)",
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              formatter={(value: number) => [`${value}`, undefined]}
            />
            <Legend
              wrapperStyle={{ fontSize: "12px" }}
              iconSize={10}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-center text-xs text-[var(--color-text-muted)]">
        Achsen: Patente, Projekte, HHI (invertiert: hoeher = diverser), h-Index,
        Förderung. Werte relativ zum Maximum beider Technologien.
      </p>
    </div>
  );
}
