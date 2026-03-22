"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- UC2: Reifegrad-Analyse
 * S-Curve visualization with maturity phase
 * indicator and R-squared confidence score
 * ────────────────────────────────────────────── */

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
} from "recharts";
import clsx from "clsx";
import PanelCard from "./PanelCard";
import type { MaturityPanel as MaturityPanelData } from "@/lib/types";

interface MaturityPanelProps {
  data: MaturityPanelData | null;
  isLoading: boolean;
  error: string | null;
  onDetailClick?: () => void;
}

const PHASE_CONFIG: Record<
  MaturityPanelData["phase"],
  { label: string; color: string; bgClass: string }
> = {
  emergence: {
    label: "Entstehung",
    color: "#3b82f6",
    bgClass: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  },
  growth: {
    label: "Wachstum",
    color: "#22c55e",
    bgClass: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  },
  maturity: {
    label: "Reife",
    color: "#f59e0b",
    bgClass: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  },
  saturation: {
    label: "Sättigung",
    color: "#f97316",
    bgClass: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400",
  },
  decline: {
    label: "Rückgang",
    color: "#ef4444",
    bgClass: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  },
};

export default function MaturityPanel({
  data,
  isLoading,
  error,
  onDetailClick,
}: MaturityPanelProps) {
  const phaseInfo = data ? PHASE_CONFIG[data.phase] : null;

  return (
    <PanelCard
      title="Reifegrad-Analyse"
      ucNumber={2}
      isLoading={isLoading}
      error={error}
      onDetailClick={data ? onDetailClick : undefined}
    >
      {data && phaseInfo && (
        <div className="flex flex-col gap-4">
          {/* Phase and Confidence Indicators */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span
              className={clsx("badge font-semibold", phaseInfo.bgClass)}
              aria-label={`Reifephase: ${phaseInfo.label}`}
            >
              Phase: {phaseInfo.label}
            </span>
            <span
              className="badge bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
              aria-label={`R-Quadrat: ${data.r_squared.toFixed(3)}`}
            >
              R² = {data.r_squared.toFixed(3)}
            </span>
            {data.inflection_year && (
              <span className="badge bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                Wendepunkt: {data.inflection_year}
              </span>
            )}
          </div>

          {/* S-Curve Chart */}
          <div className="h-[clamp(13rem,40vh,28rem)]" aria-label="S-Kurve: Technologie-Reifegrad">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={data.s_curve_data}
                margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
              >
                <defs>
                  <linearGradient id="panel-gradientFitted" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={phaseInfo.color} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={phaseInfo.color} stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis
                  dataKey="year"
                  tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
                />
                <YAxis
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
                    name === "fitted"
                      ? "S-Kurve (Fit)"
                      : name === "cumulative"
                        ? "Kumuliert"
                        : name,
                  ]}
                />
                {data.inflection_year && (
                  <ReferenceLine
                    x={data.inflection_year}
                    stroke="var(--color-text-muted)"
                    strokeDasharray="5 5"
                    label={{
                      value: "Wendepunkt",
                      position: "top",
                      fontSize: 10,
                      fill: "var(--color-text-muted)",
                    }}
                  />
                )}
                {data.data_complete_year &&
                  data.s_curve_data.length > 0 &&
                  data.s_curve_data[data.s_curve_data.length - 1].year >
                    data.data_complete_year && (
                    <ReferenceArea
                      x1={data.data_complete_year}
                      x2={data.s_curve_data[data.s_curve_data.length - 1].year}
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
                <Area
                  type="monotone"
                  dataKey="fitted"
                  stroke={phaseInfo.color}
                  strokeWidth={2}
                  fill="url(#panel-gradientFitted)"
                />
                <Area
                  type="monotone"
                  dataKey="cumulative"
                  stroke="var(--color-text-muted)"
                  strokeWidth={1}
                  strokeDasharray="4 4"
                  fill="none"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Phase Progress Bar */}
          <div aria-label="Phasen-Fortschritt">
            <div className="flex justify-between text-[10px] text-[var(--color-text-muted)] mb-1">
              <span>Entstehung</span>
              <span>Wachstum</span>
              <span>Reife</span>
              <span>Sättigung</span>
              <span>Rückgang</span>
            </div>
            <div className="flex h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
              {(["emergence", "growth", "maturity", "saturation", "decline"] as const).map(
                (phase) => (
                  <div
                    key={phase}
                    className={clsx(
                      "h-full flex-1 transition-opacity",
                      data.phase === phase ? "opacity-100" : "opacity-20"
                    )}
                    style={{ backgroundColor: PHASE_CONFIG[phase].color }}
                  />
                )
              )}
            </div>
          </div>
        </div>
      )}
    </PanelCard>
  );
}
