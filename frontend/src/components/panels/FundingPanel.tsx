"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- UC4: Förderungsanalyse
 * Funding by program, total funding, trends
 * ────────────────────────────────────────────── */

import { Euro } from "lucide-react";
import FundingTreemap from "@/components/charts/FundingTreemap";
import PanelCard from "./PanelCard";
import type { FundingPanel as FundingPanelData } from "@/lib/types";

interface FundingPanelProps {
  data: FundingPanelData | null;
  isLoading: boolean;
  error: string | null;
  onDetailClick?: () => void;
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)} Mrd. EUR`;
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)} Mio. EUR`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(0)} Tsd. EUR`;
  }
  return `${value.toFixed(0)} EUR`;
}

export default function FundingPanel({
  data,
  isLoading,
  error,
  onDetailClick,
}: FundingPanelProps) {
  return (
    <PanelCard
      title="Förderungsanalyse"
      ucNumber={4}
      isLoading={isLoading}
      error={error}
      onDetailClick={data ? onDetailClick : undefined}
    >
      {data && (
        <div className="flex flex-col items-center gap-4">
          {/* Summary Badges */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className="badge-success flex items-center gap-1">
              <Euro className="h-3 w-3" aria-hidden="true" />
              Gesamt: {formatCurrency(data.total_funding)}
            </span>
            <span className="badge bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
              {data.total_projects.toLocaleString("de-DE")} Projekte
            </span>
          </div>

          {/* Funding Treemap */}
          <div className="h-[clamp(13rem,40vh,28rem)] w-full" aria-label="Förderung nach Programm">
            <FundingTreemap data={data.by_program} />
          </div>
        </div>
      )}
    </PanelCard>
  );
}
