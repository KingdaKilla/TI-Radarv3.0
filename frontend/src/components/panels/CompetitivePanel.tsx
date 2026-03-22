"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- UC3: Wettbewerbsanalyse
 * Top assignees bar chart, HHI concentration
 * ────────────────────────────────────────────── */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import clsx from "clsx";
import PanelCard from "./PanelCard";
import { CHART_COLORS } from "@/lib/chart-colors";
import type { CompetitivePanel as CompetitivePanelData } from "@/lib/types";

interface CompetitivePanelProps {
  data: CompetitivePanelData | null;
  isLoading: boolean;
  error: string | null;
  onDetailClick?: () => void;
}

const CONCENTRATION_LABELS: Record<CompetitivePanelData["concentration"], string> = {
  niedrig: "Niedrige Konzentration",
  mittel: "Mittlere Konzentration",
  hoch: "Hohe Konzentration",
};

const CONCENTRATION_BADGE: Record<CompetitivePanelData["concentration"], string> = {
  niedrig: "badge-success",
  mittel: "badge-warning",
  hoch: "badge-error",
};

function truncateName(name: string, max = 18): string {
  if (name.length <= max) return name;
  return name.slice(0, max - 1).trimEnd() + "…";
}

export default function CompetitivePanel({
  data,
  isLoading,
  error,
  onDetailClick,
}: CompetitivePanelProps) {
  return (
    <PanelCard
      title="Wettbewerbsanalyse"
      ucNumber={3}
      isLoading={isLoading}
      error={error}
      onDetailClick={data ? onDetailClick : undefined}
    >
      {data && (
        <div className="flex flex-col gap-4">
          {/* HHI and concentration */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span
              className={clsx(CONCENTRATION_BADGE[data.concentration])}
              aria-label={`Marktkonzentration: ${CONCENTRATION_LABELS[data.concentration]}`}
            >
              {CONCENTRATION_LABELS[data.concentration]}
            </span>
          </div>

          {/* Top Wettbewerber */}
          <div className="h-[clamp(16rem,45vh,32rem)]" aria-label="Top Wettbewerber nach Patenten und Projekten">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={data.top_assignees.slice(0, 8)}
                    layout="vertical"
                    margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
                    barCategoryGap="20%"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
                    />
                    <YAxis
                      dataKey="name"
                      type="category"
                      width={110}
                      tick={{ fontSize: 9, fill: "var(--color-text-secondary)" }}
                      tickFormatter={(v: string) => truncateName(v)}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--color-bg-panel)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      formatter={(value: number, name: string) => [
                        value.toLocaleString("de-DE"),
                        name === "patent_count" ? "Patente" : "Projekte",
                      ]}
                    />
                    <Legend
                      iconSize={8}
                      wrapperStyle={{ fontSize: "11px" }}
                      formatter={(value: string) =>
                        value === "patent_count" ? "Patente" : "Projekte"
                      }
                    />
                    <Bar dataKey="patent_count" stackId="total" fill={CHART_COLORS.blue} radius={[0, 0, 0, 0]} />
                    <Bar dataKey="project_count" stackId="total" fill={CHART_COLORS.orange} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
          </div>
        </div>
      )}
    </PanelCard>
  );
}
