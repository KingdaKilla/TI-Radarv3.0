"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- Detail Data Section
 * Container for additional data tables/lists
 * ────────────────────────────────────────────── */

import type { ReactNode } from "react";

interface DetailDataSectionProps {
  title?: string;
  children: ReactNode;
}

export default function DetailDataSection({
  title = "Weitere Daten",
  children,
}: DetailDataSectionProps) {
  return (
    <section
      className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)] p-6"
      aria-label={title}
    >
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
        {title}
      </h3>
      {children}
    </section>
  );
}
