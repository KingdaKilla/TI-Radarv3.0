"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Reusable KPI Metric Card
 * Displays a single key metric with optional
 * trend indicator
 * ────────────────────────────────────────────── */

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import clsx from "clsx";

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  trend?: "up" | "down" | "neutral";
  className?: string;
}

const TREND_ICON = {
  up: TrendingUp,
  down: TrendingDown,
  neutral: Minus,
} as const;

const TREND_COLOR = {
  up: "text-[var(--color-success)]",
  down: "text-[var(--color-error)]",
  neutral: "text-[var(--color-text-muted)]",
} as const;

export default function MetricCard({
  label,
  value,
  unit,
  trend,
  className,
}: MetricCardProps) {
  const TrendIcon = trend ? TREND_ICON[trend] : null;

  return (
    <div
      className={clsx(
        "flex flex-col gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-4 py-3",
        className
      )}
      aria-label={`${label}: ${value}${unit ? ` ${unit}` : ""}`}
    >
      <span className="text-xs font-medium text-[var(--color-text-muted)]">
        {label}
      </span>
      <div className="flex items-baseline gap-2">
        <span className="text-xl font-bold text-[var(--color-text-primary)]">
          {typeof value === "number" ? value.toLocaleString("de-DE") : value}
        </span>
        {unit && (
          <span className="text-xs text-[var(--color-text-muted)]">{unit}</span>
        )}
        {TrendIcon && trend && (
          <TrendIcon
            className={clsx("h-4 w-4", TREND_COLOR[trend])}
            aria-label={
              trend === "up"
                ? "steigend"
                : trend === "down"
                  ? "fallend"
                  : "stabil"
            }
          />
        )}
      </div>
    </div>
  );
}
