"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- Detail Chart Section
 * Enlarged chart container for detail views
 * ────────────────────────────────────────────── */

import type { ReactNode } from "react";

interface DetailChartSectionProps {
  children: ReactNode;
  heightPx?: number;
  ariaLabel: string;
}

export default function DetailChartSection({
  children,
  heightPx = 500,
  ariaLabel,
}: DetailChartSectionProps) {
  return (
    <section
      className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)] p-6"
      style={{ height: heightPx }}
      aria-label={ariaLabel}
    >
      {children}
    </section>
  );
}
