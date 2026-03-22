"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Executive Summary
 * Hero gradient title + 3 metric cards +
 * KPI badge row. Premium "Tech Dashboard" look.
 * ────────────────────────────────────────────── */

import { FileText, FlaskConical, BookOpen } from "lucide-react";
import type { ClusterData } from "@/lib/clusters";

interface ExecutiveSummaryProps {
  data: ClusterData["summary"];
}

/** Format large numbers with K/M suffix */
function fmtNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString("de-DE");
}

const METRICS = [
  { key: "totalPatents", label: "Patente", icon: FileText, color: "var(--color-chart-1)" },
  { key: "totalProjects", label: "EU-Projekte", icon: FlaskConical, color: "var(--color-chart-2)" },
  { key: "totalPublications", label: "Publikationen", icon: BookOpen, color: "var(--color-chart-7)" },
] as const;

export default function ExecutiveSummary({ data }: ExecutiveSummaryProps) {
  return (
    <div className="flex flex-col items-center text-center">
      {/* Hero Title */}
      <h2
        className="text-3xl sm:text-4xl font-extrabold uppercase tracking-widest"
        style={{
          background: "linear-gradient(135deg, var(--color-accent-gold) 0%, var(--color-accent) 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
        }}
      >
        {data.technology}
      </h2>
      <p className="mt-1 text-xs sm:text-sm text-[var(--color-text-muted)]">
        Technologie-Intelligence Analyse
      </p>

      {/* 3 Metric Cards */}
      <div className="mt-6 grid grid-cols-3 gap-3 sm:gap-5 w-full max-w-2xl">
        {METRICS.map(({ key, label, icon: Icon, color }) => {
          const value = data[key];
          return (
            <div
              key={key}
              className="relative overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)] p-4 sm:p-5 transition-shadow hover:shadow-lg"
            >
              {/* Colored top accent line */}
              <div
                className="absolute top-0 left-0 right-0 h-1"
                style={{ background: color }}
              />
              <Icon
                className="mx-auto h-6 w-6 sm:h-7 sm:w-7 mb-2"
                style={{ color }}
                strokeWidth={1.5}
              />
              <p className="text-2xl sm:text-3xl font-bold text-[var(--color-text-primary)]">
                {fmtNum(value)}
              </p>
              <p className="mt-0.5 text-xs sm:text-sm text-[var(--color-text-secondary)]">
                {label}
              </p>
            </div>
          );
        })}
      </div>

      {/* KPI Badges */}
      <div className="mt-5 flex flex-wrap justify-center gap-2">
        {data.badges.map((badge, i) => {
          return (
            <span
              key={i}
              className="inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium border border-[var(--color-accent)]/20 bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
            >
              {badge}
            </span>
          );
        })}
      </div>
    </div>
  );
}
