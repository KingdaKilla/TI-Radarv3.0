"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- UC12: Erteilungsquoten
 * Composed chart with bars for counts and line
 * for grant rate, dual Y-axes
 * ────────────────────────────────────────────── */

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea,
} from "recharts";
import PanelCard from "./PanelCard";
import InfoTooltip from "@/components/ui/InfoTooltip";
import { METRIC_TOOLTIPS } from "@/lib/metric-tooltips";
import { CHART_COLORS } from "@/lib/chart-colors";
import type { PatentGrantPanel as PatentGrantPanelData } from "@/lib/types";

interface PatentGrantPanelProps {
  data: PatentGrantPanelData | null;
  isLoading: boolean;
  error: string | null;
  onDetailClick?: () => void;
  dataCompleteYear?: number;
  queryTimeSeconds?: number;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export default function PatentGrantPanel({
  data,
  isLoading,
  error,
  onDetailClick,
  dataCompleteYear,
  queryTimeSeconds,
}: PatentGrantPanelProps) {
  const chartData = data?.year_trend.map((entry) => ({
    ...entry,
    grant_rate_pct: entry.grant_rate * 100,
  }));

  return (
    <PanelCard
      title="Erteilungsquoten"
      ucNumber={12}
      ucKey="patent_grant"
      isLoading={isLoading}
      error={error}
      onDetailClick={data ? onDetailClick : undefined}
      queryTimeSeconds={queryTimeSeconds}
    >
      {data && (
        <div className="flex flex-col gap-4">
          {/* Summary Badges */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className="badge-success">
              Quote: {formatPercent(data.summary.grant_rate)}
              <InfoTooltip text={METRIC_TOOLTIPS.grant_rate} />
            </span>
            <span className="badge-info">
              {data.summary.avg_time_to_grant_months.toFixed(1)} Mon. bis Erteilung
            </span>
            <span className="badge bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
              {data.summary.total_applications.toLocaleString("de-DE")} Anmeldungen
            </span>
            <span className="badge bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
              {data.summary.total_grants.toLocaleString("de-DE")} Erteilungen
            </span>
          </div>

          {/* Composed Chart: Bars + Line */}
          <div className="h-[clamp(13rem,40vh,28rem)]" aria-label="Anmeldungen, Erteilungen und Quote über Zeit">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={chartData}
                margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis
                  dataKey="year"
                  tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                />
                <YAxis
                  yAxisId="left"
                  tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                  width={45}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                  tickFormatter={(v) => `${v}%`}
                  domain={[0, 100]}
                  width={45}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--color-bg-panel)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                  formatter={(value: number, name: string) => {
                    if (name === "grant_rate_pct")
                      return [`${value.toFixed(1)}%`, "Quote"];
                    if (name === "application_count")
                      return [value.toLocaleString("de-DE"), "Anmeldungen"];
                    if (name === "grant_count")
                      return [value.toLocaleString("de-DE"), "Erteilungen"];
                    return [value, name];
                  }}
                />
                <Legend
                  formatter={(value: string) => {
                    const labels: Record<string, string> = {
                      application_count: "Anmeldungen",
                      grant_count: "Erteilungen",
                      grant_rate_pct: "Quote (%)",
                    };
                    return labels[value] ?? value;
                  }}
                />
                <Bar
                  yAxisId="left"
                  dataKey="application_count"
                  fill={CHART_COLORS.skyBlue}
                  radius={[2, 2, 0, 0]}
                  barSize={12}
                />
                <Bar
                  yAxisId="left"
                  dataKey="grant_count"
                  fill={CHART_COLORS.green}
                  radius={[2, 2, 0, 0]}
                  barSize={12}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="grant_rate_pct"
                  stroke={CHART_COLORS.blue}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
                {dataCompleteYear &&
                  chartData &&
                  chartData.length > 0 &&
                  chartData[chartData.length - 1].year > dataCompleteYear && (
                    <ReferenceArea
                      x1={dataCompleteYear}
                      x2={chartData[chartData.length - 1].year}
                      yAxisId="left"
                      fill="#9ca3af"
                      fillOpacity={0.15}
                      label={{
                        value: "Daten unvollständig",
                        position: "insideTop",
                        fontSize: 9,
                        fill: "#9ca3af",
                      }}
                    />
                  )}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </PanelCard>
  );
}
