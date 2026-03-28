"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC11: Akteurs-Typverteilung
 * Pie chart showing organisation type distribution
 * (HES, PRC, REC, OTH, PUB) with coverage badges
 * ────────────────────────────────────────────── */

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import PanelCard from "./PanelCard";
import { CHART_COLORS, PALETTE } from "@/lib/chart-colors";
import type { ActorTypePanel as ActorTypePanelData } from "@/lib/types";

interface ActorTypePanelProps {
  data: ActorTypePanelData | null;
  isLoading: boolean;
  error: string | null;
  onDetailClick?: () => void;
  queryTimeSeconds?: number;
}

const TYPE_COLORS: Record<string, string> = {
  "Higher Education": CHART_COLORS.blue,
  "Private Company": CHART_COLORS.orange,
  "Research Organisation": CHART_COLORS.green,
  "Other": CHART_COLORS.skyBlue,
  "Public Body": CHART_COLORS.purple,
};

const FALLBACK_COLORS = PALETTE.slice(0, 5);

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatEur(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)} Mrd. EUR`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)} Mio. EUR`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)} Tsd. EUR`;
  return `${value.toFixed(0)} EUR`;
}

export default function ActorTypePanel({
  data,
  isLoading,
  error,
  onDetailClick,
  queryTimeSeconds,
}: ActorTypePanelProps) {
  const chartData = data?.type_breakdown.map((entry) => ({
    name: entry.label,
    value: entry.actor_count,
    share: entry.actor_share,
    funding: entry.funding_eur,
  }));

  return (
    <PanelCard
      title="Akteurs-Typverteilung"
      ucNumber={11}
      ucKey="actor_type"
      isLoading={isLoading}
      error={error}
      onDetailClick={data ? onDetailClick : undefined}
      queryTimeSeconds={queryTimeSeconds}
    >
      {data && (
        <div className="flex flex-col gap-4">
          {/* Badges */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className="badge-info">
              {data.total_classified_actors.toLocaleString("de-DE")} Akteure
            </span>
            {data.type_breakdown.length > 0 && (() => {
              const dominant = data.type_breakdown.reduce((best, t) => t.actor_count > best.actor_count ? t : best, data.type_breakdown[0]);
              return (
                <span className="badge bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                  Dominiert: {dominant.label}
                </span>
              );
            })()}
          </div>

          {/* Donut Chart */}
          <div className="h-[clamp(13rem,40vh,28rem)]" aria-label="Verteilung nach Organisationstyp">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius="35%"
                  outerRadius="60%"
                  dataKey="value"
                  nameKey="name"
                  paddingAngle={2}
                >
                  {chartData?.map((entry, idx) => (
                    <Cell
                      key={entry.name}
                      fill={TYPE_COLORS[entry.name] ?? FALLBACK_COLORS[idx % FALLBACK_COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  content={({ payload }) => {
                    if (!payload || payload.length === 0) return null;
                    const d = payload[0];
                    return (
                      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-3 py-2 text-xs shadow-lg">
                        <p className="font-semibold text-[var(--color-text-primary)]">{d.name}</p>
                        <p className="text-[var(--color-text-muted)]">
                          {(d.value as number).toLocaleString("de-DE")} Akteure
                        </p>
                      </div>
                    );
                  }}
                />
                <Legend
                  wrapperStyle={{ fontSize: "11px" }}
                  formatter={(value: string) => (
                    <span className="text-[var(--color-text-secondary)]">{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

        </div>
      )}
    </PanelCard>
  );
}
