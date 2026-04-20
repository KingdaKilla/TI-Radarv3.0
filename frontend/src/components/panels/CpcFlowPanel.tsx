"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC5: CPC-Technologiefluss
 * Chord diagram showing CPC code relationships
 * with fallback to combination list
 * ────────────────────────────────────────────── */

import { useState, useMemo } from "react";
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
  // Bug v3.4.10/α-E: Dynamischer Slider für die Anzahl der dargestellten
  // CPC-Klassen. Der Backend-Response liefert bis zu N Nodes (Standardmäßig
  // 10-15). Nutzer kann per Slider live zwischen 3 und data.nodes.length
  // variieren. Links werden entsprechend gefiltert (beide Endpunkte müssen
  // in der Auswahl sein).
  const maxNodes = data?.nodes.length ?? 10;
  const [displayCount, setDisplayCount] = useState<number>(() =>
    Math.min(10, maxNodes)
  );

  // Wenn Daten sich ändern (neue Radar-Query), Slider an neuen Max-Wert
  // klammern — React useMemo mit dependency auf maxNodes sorgt dafür.
  const effectiveCount = useMemo(
    () => Math.min(displayCount, Math.max(2, maxNodes)),
    [displayCount, maxNodes]
  );

  // Top-N-Nodes + passende Links berechnen.
  const { visibleNodes, visibleLinks } = useMemo(() => {
    if (!data) return { visibleNodes: [], visibleLinks: [] };
    const nodes = data.nodes.slice(0, effectiveCount);
    const nodeIds = new Set(nodes.map((n) => n.id));
    const links = data.links.filter(
      (l) => nodeIds.has(l.source) && nodeIds.has(l.target)
    );
    return { visibleNodes: nodes, visibleLinks: links };
  }, [data, effectiveCount]);

  const hasChordData = visibleNodes.length >= 2 && visibleLinks.length > 0;

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
              {visibleNodes.length} / {maxNodes} CPC-Klassen
            </span>
            {data.top_combinations.length > 0 && (() => {
              const jaccards = data.top_combinations.map((c) => c.jaccard).filter((j) => j > 0);
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

          {/* Slider: Anzahl CPC-Klassen (v3.4.10/α-E) */}
          {maxNodes > 3 && (
            <div className="flex items-center gap-3 px-2 no-print">
              <label
                htmlFor="cpc-flow-slider"
                className="shrink-0 text-xs font-medium text-[var(--color-text-secondary)]"
              >
                Anzahl CPC-Klassen:
              </label>
              <input
                id="cpc-flow-slider"
                type="range"
                min={3}
                max={maxNodes}
                step={1}
                value={effectiveCount}
                onChange={(e) => setDisplayCount(Number(e.target.value))}
                className="flex-1 accent-[var(--color-accent)]"
                aria-label="Anzahl dargestellter CPC-Klassen einstellen"
              />
              <span className="shrink-0 w-8 text-right font-mono text-xs text-[var(--color-accent)]">
                {effectiveCount}
              </span>
            </div>
          )}

          {/* Chord Diagram (when link data is available) */}
          {hasChordData ? (
            <div
              className="h-[clamp(16rem,45vh,32rem)]"
              aria-label="Chord-Diagramm: CPC-Technologiefluss"
            >
              <CpcChordDiagram nodes={visibleNodes} links={visibleLinks} />
            </div>
          ) : (
            <div className="flex h-48 items-center justify-center">
              <p className="text-xs text-[var(--color-text-muted)] italic">
                Für {effectiveCount} CPC-Klassen gibt es keine nennenswerten
                Querverbindungen. Slider erhöhen für mehr Datenpunkte.
              </p>
            </div>
          )}
        </div>
      )}
    </PanelCard>
  );
}
