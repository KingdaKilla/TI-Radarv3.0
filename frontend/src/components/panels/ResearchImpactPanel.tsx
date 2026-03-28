"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC7: Forschungsimpact
 * Citation trend chart + top institutions list
 * ────────────────────────────────────────────── */

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceArea,
} from "recharts";
import PanelCard from "./PanelCard";
import { CHART_COLORS } from "@/lib/chart-colors";
import type { ResearchImpactPanel as ResearchImpactPanelData } from "@/lib/types";

interface ResearchImpactPanelProps {
  data: ResearchImpactPanelData | null;
  isLoading: boolean;
  error: string | null;
  onDetailClick?: () => void;
  dataCompleteYear?: number;
  queryTimeSeconds?: number;
}

export default function ResearchImpactPanel({
  data,
  isLoading,
  error,
  onDetailClick,
  dataCompleteYear,
  queryTimeSeconds,
}: ResearchImpactPanelProps) {
  return (
    <PanelCard
      title="Forschungsimpact"
      ucNumber={7}
      ucKey="research_impact"
      isLoading={isLoading}
      error={error}
      onDetailClick={data ? onDetailClick : undefined}
      queryTimeSeconds={queryTimeSeconds}
    >
      {data && (
        <div className="flex flex-col gap-4">
          {/* Key Metrics */}
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-lg border border-[var(--color-border)] p-2 text-center">
              <p className="text-lg font-bold text-[var(--color-accent)]">
                {data.total_papers.toLocaleString("de-DE")}
              </p>
              <p className="text-[10px] text-[var(--color-text-muted)]">
                Publikationen
              </p>
            </div>
            <div className="rounded-lg border border-[var(--color-border)] p-2 text-center">
              <p className="text-lg font-bold text-[var(--color-accent)]">
                {data.avg_citations.toFixed(1)}
              </p>
              <p className="text-[10px] text-[var(--color-text-muted)]">
                Zitate/Pub.
              </p>
            </div>
            <div className="rounded-lg border border-[var(--color-border)] p-2 text-center">
              <p className="text-lg font-bold text-[var(--color-accent)]">
                {data.top_institutions.length}
              </p>
              <p className="text-[10px] text-[var(--color-text-muted)]">
                Institutionen
              </p>
            </div>
          </div>

          {/* Citation Trend Chart */}
          {data.citation_trend.length > 0 && (
            <div
              className="h-[clamp(11rem,35vh,24rem)]"
              aria-label="Zitations-Trend: Publikationen und Zitationen pro Jahr"
            >
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={data.citation_trend}
                  margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="var(--color-border)"
                  />
                  <XAxis
                    dataKey="year"
                    tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                  />
                  <YAxis
                    yAxisId="left"
                    tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                    width={40}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                    width={50}
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
                      name === "publication_count"
                        ? "Publikationen"
                        : "Zitationen",
                    ]}
                  />
                  <Legend
                    iconSize={8}
                    wrapperStyle={{ fontSize: "11px" }}
                    formatter={(value: string) =>
                      value === "publication_count"
                        ? "Publikationen"
                        : "Zitationen"
                    }
                  />
                  <Bar
                    yAxisId="left"
                    dataKey="publication_count"
                    fill={CHART_COLORS.blue}
                    radius={[3, 3, 0, 0]}
                    opacity={0.8}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="total_citations"
                    stroke={CHART_COLORS.orange}
                    strokeWidth={2}
                    dot={{ r: 3, fill: CHART_COLORS.orange }}
                  />
                  {dataCompleteYear &&
                    data.citation_trend.length > 0 &&
                    data.citation_trend[data.citation_trend.length - 1].year > dataCompleteYear && (
                      <ReferenceArea
                        x1={dataCompleteYear}
                        x2={data.citation_trend[data.citation_trend.length - 1].year}
                        yAxisId="left"
                        fill="#9ca3af"
                        fillOpacity={0.15}
                        label={{
                          value: "Daten ggf. unvollständig",
                          position: "insideTop",
                          fontSize: 9,
                          fill: "#9ca3af",
                        }}
                      />
                    )}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

        </div>
      )}
    </PanelCard>
  );
}
