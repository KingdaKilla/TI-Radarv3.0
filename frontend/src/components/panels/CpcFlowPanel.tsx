"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC5: CPC-Technologiefluss
 * Chord diagram showing CPC code relationships
 * with fallback to combination list
 * ────────────────────────────────────────────── */

import PanelCard from "./PanelCard";
import CpcChordDiagram from "@/components/charts/CpcChordDiagram";
import InfoTooltip from "@/components/ui/InfoTooltip";
import { METRIC_TOOLTIPS } from "@/lib/metric-tooltips";
import type { CpcFlowPanel as CpcFlowPanelData } from "@/lib/types";

interface CpcFlowPanelProps {
  data: CpcFlowPanelData | null;
  isLoading: boolean;
  error: string | null;
  onDetailClick?: () => void;
  queryTimeSeconds?: number;
}

export default function CpcFlowPanel({
  data,
  isLoading,
  error,
  onDetailClick,
  queryTimeSeconds,
}: CpcFlowPanelProps) {
  const hasChordData =
    data && data.nodes.length >= 2 && data.links.length > 0;

  return (
    <PanelCard
      title="Cross-Tech Intelligence"
      ucNumber={5}
      ucKey="cpc_flow"
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
              {data.nodes.length} CPC-Klassen
            </span>
            {data.top_combinations.length > 0 && (() => {
              const jaccards = data.top_combinations.map(c => c.jaccard).filter(j => j > 0);
              const avg = jaccards.length > 0 ? jaccards.reduce((a, b) => a + b, 0) / jaccards.length : 0;
              return avg > 0 ? (
                <span className="badge bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                  &#216; Jaccard: {avg.toFixed(3)}
                  <InfoTooltip text={METRIC_TOOLTIPS.jaccard} />
                </span>
              ) : null;
            })()}
            {data.whitespace_opportunities.length > 0 && (
              <span className="badge bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
                {data.whitespace_opportunities.length} Whitespace-Lücken
              </span>
            )}
          </div>

          {/* Chord Diagram (when link data is available) */}
          {hasChordData && (
            <div className="h-[clamp(16rem,45vh,32rem)]" aria-label="Chord-Diagramm: CPC-Technologiefluss">
              <CpcChordDiagram nodes={data.nodes} links={data.links} />
            </div>
          )}

        </div>
      )}
    </PanelCard>
  );
}
