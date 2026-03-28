"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Detail Chart Section
 * Enlarged chart container for detail views
 * with optional PNG export
 * ────────────────────────────────────────────── */

import { useRef, useCallback } from "react";
import type { ReactNode } from "react";
import { Camera } from "lucide-react";
import { exportChartAsPng } from "@/utils/export";

interface DetailChartSectionProps {
  children: ReactNode;
  heightPx?: number;
  ariaLabel: string;
  exportFilename?: string;
}

export default function DetailChartSection({
  children,
  heightPx = 500,
  ariaLabel,
  exportFilename,
}: DetailChartSectionProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  const handleExportPng = useCallback(async () => {
    if (!chartRef.current || !exportFilename) return;
    await exportChartAsPng(chartRef.current, exportFilename);
  }, [exportFilename]);

  return (
    <section
      className="relative rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)] p-6"
      style={{ height: heightPx }}
      aria-label={ariaLabel}
    >
      {exportFilename && (
        <button
          onClick={handleExportPng}
          className="no-print absolute top-3 right-3 rounded-md p-1.5 text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text-primary)]"
          aria-label="Chart als PNG exportieren"
          title="Als PNG exportieren"
        >
          <Camera className="h-4 w-4" />
        </button>
      )}
      <div ref={chartRef} className="h-full w-full">
        {children}
      </div>
    </section>
  );
}
