"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- UC8: Zeitliche Entwicklung
 * Actor entrant/persistence trend chart +
 * emerging/declining topics
 * ────────────────────────────────────────────── */

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceArea,
} from "recharts";
import { TrendingUp, TrendingDown } from "lucide-react";
import PanelCard from "./PanelCard";
import { CHART_COLORS } from "@/lib/chart-colors";
import type { TemporalPanel as TemporalPanelData } from "@/lib/types";

interface TemporalPanelProps {
  data: TemporalPanelData | null;
  isLoading: boolean;
  error: string | null;
  onDetailClick?: () => void;
  dataCompleteYear?: number;
  queryTimeSeconds?: number;
}

export default function TemporalPanel({
  data,
  isLoading,
  error,
  onDetailClick,
  dataCompleteYear,
  queryTimeSeconds,
}: TemporalPanelProps) {
  return (
    <PanelCard
      title="Zeitliche Entwicklung"
      ucNumber={8}
      ucKey="temporal"
      isLoading={isLoading}
      error={error}
      onDetailClick={data ? onDetailClick : undefined}
      queryTimeSeconds={queryTimeSeconds}
    >
      {data && (
        <div className="flex flex-col items-center justify-center gap-4 h-full">
          {/* Badges */}
          {data.entrant_trend.length > 0 && (() => {
            // Use multi-year net change for trend label (last 3 years or all available)
            const recentYears = data.entrant_trend.slice(-3);
            const netRecent = recentYears.reduce((s, p) => s + p.new_entrants - p.exited_actors, 0);
            const last = data.entrant_trend[data.entrant_trend.length - 1];
            const trend = netRecent > 0 ? "Wachsend" : netRecent < 0 ? "Schrumpfend" : "Stabil";
            const trendClass = netRecent > 0 ? "badge-success" : netRecent < 0 ? "badge-error" : "badge bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300";
            return (
              <div className="flex flex-wrap items-center justify-center gap-2">
                <span className="badge-info">
                  {last.total_active.toLocaleString("de-DE")} Akteure
                </span>
                <span className={trendClass}>
                  {trend} ({netRecent > 0 ? "+" : ""}{netRecent.toLocaleString("de-DE")} netto)
                </span>
              </div>
            );
          })()}

          {/* Entrant/Persistence Trend Chart */}
          {data.entrant_trend.length > 0 && (
            <div
              className="h-[clamp(12rem,38vh,26rem)] w-full"
              aria-label="Akteur-Dynamik: Neue und persistente Akteure pro Jahr"
            >
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={data.entrant_trend}
                  margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
                >
                  <defs>
                    <linearGradient id="gradPersistent" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.blue} stopOpacity={0.6} />
                      <stop offset="95%" stopColor={CHART_COLORS.blue} stopOpacity={0.1} />
                    </linearGradient>
                    <linearGradient id="gradNew" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.orange} stopOpacity={0.6} />
                      <stop offset="95%" stopColor={CHART_COLORS.orange} stopOpacity={0.1} />
                    </linearGradient>
                    <linearGradient id="gradExited" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.vermillion} stopOpacity={0.4} />
                      <stop offset="95%" stopColor={CHART_COLORS.vermillion} stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="var(--color-border)"
                  />
                  <XAxis
                    dataKey="year"
                    tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                    width={35}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--color-bg-panel)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                    formatter={(value: number, name: string) => {
                      const labels: Record<string, string> = {
                        new_entrants: "Neue Akteure",
                        persistent_actors: "Persistente",
                        exited_actors: "Ausgeschieden",
                      };
                      return [
                        value.toLocaleString("de-DE"),
                        labels[name] ?? name,
                      ];
                    }}
                  />
                  <Legend
                    iconSize={8}
                    wrapperStyle={{ fontSize: "11px" }}
                    formatter={(value: string) => {
                      const labels: Record<string, string> = {
                        new_entrants: "Neue Akteure",
                        persistent_actors: "Persistente",
                        exited_actors: "Ausgeschieden",
                      };
                      return labels[value] ?? value;
                    }}
                  />
                  <Area
                    dataKey="persistent_actors"
                    stackId="actors"
                    type="monotone"
                    fill="url(#gradPersistent)"
                    stroke={CHART_COLORS.blue}
                    fillOpacity={0.6}
                  />
                  <Area
                    dataKey="new_entrants"
                    stackId="actors"
                    type="monotone"
                    fill="url(#gradNew)"
                    stroke={CHART_COLORS.orange}
                    fillOpacity={0.6}
                  />
                  <Area
                    dataKey="exited_actors"
                    type="monotone"
                    fill="url(#gradExited)"
                    stroke={CHART_COLORS.vermillion}
                    fillOpacity={0.3}
                  />
                  {dataCompleteYear &&
                    data.entrant_trend.length > 0 &&
                    data.entrant_trend[data.entrant_trend.length - 1].year > dataCompleteYear && (
                      <ReferenceArea
                        x1={dataCompleteYear}
                        x2={data.entrant_trend[data.entrant_trend.length - 1].year}
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
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Emerging Topics */}
          {data.emerging_topics.length > 0 && (
            <div>
              <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-green-600 dark:text-green-400">
                <TrendingUp className="h-3.5 w-3.5" aria-hidden="true" />
                Aufkommende Themen
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {data.emerging_topics.map((topic) => (
                  <span key={topic} className="badge-success">
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Declining Topics */}
          {data.declining_topics.length > 0 && (
            <div>
              <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-red-500 dark:text-red-400">
                <TrendingDown className="h-3.5 w-3.5" aria-hidden="true" />
                Abnehmende Themen
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {data.declining_topics.map((topic) => (
                  <span key={topic} className="badge-error">
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </PanelCard>
  );
}
