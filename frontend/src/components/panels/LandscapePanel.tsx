"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- UC1: Technologie-Landschaft
 * Line chart showing patents + projects over time
 * with CAGR badge and top CPC codes
 * ────────────────────────────────────────────── */

import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceArea,
  ResponsiveContainer,
} from "recharts";
import PanelCard from "./PanelCard";
import InfoTooltip from "@/components/ui/InfoTooltip";
import { METRIC_TOOLTIPS } from "@/lib/metric-tooltips";
import { CHART_COLORS } from "@/lib/chart-colors";
import type { LandscapePanel as LandscapePanelData } from "@/lib/types";

interface LandscapePanelProps {
  data: LandscapePanelData | null;
  isLoading: boolean;
  error: string | null;
  onDetailClick?: () => void;
  dataCompleteYear?: number;
  queryTimeSeconds?: number;
}

function formatCAGR(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export default function LandscapePanel({
  data,
  isLoading,
  error,
  onDetailClick,
  dataCompleteYear,
  queryTimeSeconds,
}: LandscapePanelProps) {
  const growthData =
    data && data.time_series.length > 1
      ? data.time_series.slice(1).map((pt, i) => {
          const prev = data.time_series[i];
          return {
            year: pt.year,
            patents:
              prev.patents > 0
                ? ((pt.patents - prev.patents) / prev.patents) * 100
                : 0,
            projects:
              prev.projects > 0
                ? ((pt.projects - prev.projects) / prev.projects) * 100
                : 0,
            publications:
              prev.publications > 0
                ? ((pt.publications - prev.publications) / prev.publications) *
                  100
                : 0,
          };
        })
      : [];

  return (
    <PanelCard
      title="Technologie-Landschaft"
      ucNumber={1}
      ucKey="landscape"
      isLoading={isLoading}
      error={error}
      onDetailClick={data ? onDetailClick : undefined}
      queryTimeSeconds={queryTimeSeconds}
    >
      {data && (
        <div className="flex flex-col gap-4">
          {/* CAGR Badges */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className="badge-patents" aria-label="Patent-CAGR">
              Patente CAGR: {formatCAGR(data.cagr_patents)}
              <InfoTooltip text={METRIC_TOOLTIPS.cagr} />
            </span>
            <span className="badge-projects" aria-label="Projekt-CAGR">
              Projekte CAGR: {formatCAGR(data.cagr_projects)}
              <InfoTooltip text={METRIC_TOOLTIPS.cagr} />
            </span>
            {data.total_publications > 0 && (
              <span className="badge-publications" aria-label="Publikationen-CAGR">
                Publikationen CAGR: {formatCAGR(data.cagr_publications)}
              </span>
            )}
          </div>

          {/* Zeitreihe */}
          <div className="h-[clamp(13rem,40vh,28rem)]" aria-label="Zeitreihe: Patente und Projekte">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={growthData}
                    margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
                  >
                    <defs>
                      <linearGradient id="panel-gradPatents" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={CHART_COLORS.blue} stopOpacity={0.15} />
                        <stop offset="95%" stopColor={CHART_COLORS.blue} stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="panel-gradProjects" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={CHART_COLORS.orange} stopOpacity={0.15} />
                        <stop offset="95%" stopColor={CHART_COLORS.orange} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis
                      dataKey="year"
                      tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                      width={45}
                      tickFormatter={(v: number) => `${v.toFixed(0)}%`}
                    />
                    <Tooltip
                      content={({ payload, label }) => {
                        if (!payload || payload.length === 0) return null;
                        const original = data.time_series.find(p => p.year === label);
                        if (!original) return null;
                        const growth = growthData.find(p => p.year === label);
                        return (
                          <div
                            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-3 py-2 text-xs shadow-lg"
                          >
                            <p className="mb-1 font-semibold text-[var(--color-text-primary)]">{label}</p>
                            <p className="text-[var(--color-text-secondary)]">
                              Patente: {original.patents.toLocaleString("de-DE")}
                              {growth && (
                                <span className={growth.patents >= 0 ? "text-green-500" : "text-red-500"}>
                                  {" "}({growth.patents >= 0 ? "+" : ""}{growth.patents.toFixed(1)}%)
                                </span>
                              )}
                            </p>
                            <p className="text-[var(--color-text-secondary)]">
                              Projekte: {original.projects.toLocaleString("de-DE")}
                              {growth && (
                                <span className={growth.projects >= 0 ? "text-green-500" : "text-red-500"}>
                                  {" "}({growth.projects >= 0 ? "+" : ""}{growth.projects.toFixed(1)}%)
                                </span>
                              )}
                            </p>
                            {original.publications > 0 && (
                              <p className="text-[var(--color-text-secondary)]">
                                Publikationen: {original.publications.toLocaleString("de-DE")}
                                {growth && (
                                  <span className={growth.publications >= 0 ? "text-green-500" : "text-red-500"}>
                                    {" "}({growth.publications >= 0 ? "+" : ""}{growth.publications.toFixed(1)}%)
                                  </span>
                                )}
                              </p>
                            )}
                          </div>
                        );
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="patents"
                      fill="url(#panel-gradPatents)"
                      stroke="none"
                      fillOpacity={1}
                      legendType="none"
                      tooltipType="none"
                    />
                    <Area
                      type="monotone"
                      dataKey="projects"
                      fill="url(#panel-gradProjects)"
                      stroke="none"
                      fillOpacity={1}
                      legendType="none"
                      tooltipType="none"
                    />
                    {growthData.some((p) => p.publications !== 0) && (
                      <Area
                        type="monotone"
                        dataKey="publications"
                        fill={CHART_COLORS.purple}
                        stroke="none"
                        fillOpacity={0.08}
                        legendType="none"
                        tooltipType="none"
                      />
                    )}
                    <Line
                      type="monotone"
                      dataKey="patents"
                      stroke={CHART_COLORS.blue}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="projects"
                      stroke={CHART_COLORS.orange}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                    {growthData.some((p) => p.publications !== 0) && (
                      <Line
                        type="monotone"
                        dataKey="publications"
                        stroke={CHART_COLORS.purple}
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4 }}
                      />
                    )}
                    {dataCompleteYear && growthData.length > 0 &&
                      growthData[growthData.length - 1].year > dataCompleteYear && (
                        <ReferenceArea
                          x1={dataCompleteYear}
                          x2={growthData[growthData.length - 1].year}
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

          {/* Top CPC Codes */}
          {data.top_cpc_codes.length > 0 && (
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                Top CPC-Klassen
              </h3>
              <ul className="space-y-1" aria-label="Top CPC-Codes">
                {data.top_cpc_codes.slice(0, 5).map((cpc) => (
                  <li
                    key={cpc.code}
                    className="flex items-center justify-between text-xs"
                  >
                    <span className="font-mono text-[var(--color-text-secondary)]">
                      {cpc.code}
                    </span>
                    <span className="text-[var(--color-text-muted)]">
                      {cpc.count.toLocaleString("de-DE")}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </PanelCard>
  );
}
