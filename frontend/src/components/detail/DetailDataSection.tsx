"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Detail Data Section
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
      // Bug v3.4.9/R: `overflow-x-auto` + `min-w-0` — lange Tabellen-Zeilen
      // (z.B. "CENTRE NATIONAL DE LA RECHERCHE SCIENTIFIQUE CNRS") sprengen
      // sonst die Box-Breite in Grid-Layouts.
      className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)] p-6 min-w-0 overflow-x-auto"
      aria-label={title}
    >
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
        {title}
      </h3>
      {children}
    </section>
  );
}
