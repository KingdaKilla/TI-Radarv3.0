"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Reusable Panel Card Wrapper
 * Provides consistent styling, loading, and
 * error states for all UC panels
 * ────────────────────────────────────────────── */

import { AlertTriangle, Loader2, Maximize2 } from "lucide-react";
import type { ReactNode } from "react";
import type { UseCaseKey } from "@/lib/types";
import ExplainabilityBar from "@/components/ui/ExplainabilityBar";
import InfoTooltip from "@/components/ui/InfoTooltip";
import { DATA_SOURCES } from "@/lib/data-sources";
import { METHODOLOGY_TOOLTIPS } from "@/lib/methodology-tooltips";
import { UC_INSIGHTS } from "@/lib/uc-insights";

interface PanelCardProps {
  title: string;
  ucNumber: number;
  ucLabel?: string;
  isLoading: boolean;
  error: string | null;
  children: ReactNode;
  className?: string;
  onDetailClick?: () => void;
  ucKey?: UseCaseKey;
  queryTimeSeconds?: number;
  warnings?: string[];
  /**
   * Bug v3.4.7/C-013: Wenn gesetzt, zeigt die ExplainabilityBar diese
   * Liste statt des hardcoded `DATA_SOURCES`-Mappings. Erwartet Namen
   * der `panel.metadata.data_sources[]` aus der API-Response — damit
   * EU-AI-Act-Transparenz gewährleistet ist und die UI wirklich zeigt
   * welche Quellen tatsächlich genutzt wurden.
   */
  dataSourcesOverride?: string[];
}

export default function PanelCard({
  title,
  ucNumber,
  ucLabel,
  isLoading,
  error,
  children,
  className = "",
  onDetailClick,
  ucKey,
  queryTimeSeconds,
  warnings,
  dataSourcesOverride,
}: PanelCardProps) {
  return (
    <section
      className={`panel-card hover:glow-border flex flex-col ${className}`}
      aria-label={title}
    >
      {/* Header */}
      <div className="panel-card-header">
        <div className="flex items-center gap-2">
          <span
            className="badge-info text-[10px] font-bold"
            aria-label={`Use Case ${ucLabel ?? ucNumber}`}
          >
            UC{ucLabel ?? ucNumber}
          </span>
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
            {title}
          </h2>
          {ucKey && UC_INSIGHTS[ucKey] && (
            <InfoTooltip text={UC_INSIGHTS[ucKey]} />
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {isLoading && (
            <Loader2
              className="h-4 w-4 animate-spin text-[var(--color-accent)]"
              aria-label="Laden..."
            />
          )}
          {onDetailClick && !isLoading && !error && (
            <button
              onClick={onDetailClick}
              className="no-print rounded-md p-1 text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-accent)]"
              aria-label={`${title} Detailansicht öffnen`}
              title="Detailansicht"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="panel-card-body flex-1">
        {isLoading ? (
          <div
            className="h-48 space-y-3 p-2"
            role="status"
            aria-live="polite"
            aria-label="Daten werden geladen..."
          >
            {/* Skeleton-Badges */}
            <div className="flex gap-2">
              <div className="h-5 w-20 animate-pulse rounded-full bg-[var(--color-border)]" />
              <div className="h-5 w-16 animate-pulse rounded-full bg-[var(--color-border)]" />
              <div className="h-5 w-24 animate-pulse rounded-full bg-[var(--color-border)]" />
            </div>
            {/* Skeleton-Diagrammbereich */}
            <div className="h-32 animate-pulse rounded-lg bg-[var(--color-border)] opacity-40" />
            {/* Skeleton-Textzeilen */}
            <div className="space-y-1.5">
              <div className="h-3 w-3/4 animate-pulse rounded bg-[var(--color-border)] opacity-30" />
              <div className="h-3 w-1/2 animate-pulse rounded bg-[var(--color-border)] opacity-30" />
            </div>
          </div>
        ) : error ? (
          <div
            className="flex h-48 items-center justify-center"
            role="alert"
            aria-live="assertive"
          >
            <div className="flex flex-col items-center gap-2 text-center">
              <AlertTriangle
                className="h-8 w-8 text-[var(--color-error)]"
                aria-hidden="true"
              />
              <p className="text-sm font-medium text-[var(--color-error)]">
                Fehler beim Laden
              </p>
              <p className="max-w-xs text-xs text-[var(--color-text-muted)]">
                {error}
              </p>
            </div>
          </div>
        ) : (
          children
        )}
      </div>

      {/* Explainability / Transparency Footer */}
      {ucKey && !isLoading && !error && (
        <div className="mt-auto px-4 pb-4">
          <ExplainabilityBar
            dataSources={
              dataSourcesOverride && dataSourcesOverride.length > 0
                ? dataSourcesOverride
                : DATA_SOURCES[ucKey].split(" · ")
            }
            queryTimeSeconds={queryTimeSeconds ?? 0}
            methodology={METHODOLOGY_TOOLTIPS[ucKey]}
            deterministic={true}
            warnings={warnings}
          />
        </div>
      )}
    </section>
  );
}
