"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- ExplainabilityBar
 * Collapsible transparency bar for EU AI Act
 * compliance. Shows data sources, methodology,
 * confidence and processing time.
 * ────────────────────────────────────────────── */

import { useState, useCallback } from "react";
import {
  ChevronDown,
  ChevronUp,
  Database,
  Clock,
  FlaskConical,
  ShieldCheck,
  AlertTriangle,
  Info,
} from "lucide-react";
import clsx from "clsx";

export interface ExplainabilityBarProps {
  dataSources: string[];
  queryTimeSeconds: number;
  methodology: string;
  confidence?: number;
  warnings?: string[];
  deterministic?: boolean;
}

/** Confidence level label and color mapping. */
function getConfidenceDisplay(confidence: number): {
  label: string;
  colorClass: string;
} {
  if (confidence >= 0.8) {
    return { label: "Hoch", colorClass: "text-[var(--color-success)]" };
  }
  if (confidence >= 0.5) {
    return { label: "Mittel", colorClass: "text-[var(--color-warning)]" };
  }
  return { label: "Niedrig", colorClass: "text-[var(--color-error)]" };
}

export default function ExplainabilityBar({
  dataSources,
  queryTimeSeconds,
  methodology,
  confidence,
  warnings = [],
  deterministic = true,
}: ExplainabilityBarProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const toggle = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  const hasWarnings = warnings.length > 0;

  return (
    <div
      className={clsx(
        "rounded-xl border transition-colors duration-200",
        "border-[var(--color-border)] bg-[var(--color-bg-panel)]"
      )}
      role="region"
      aria-label="Transparenz und Nachvollziehbarkeit"
    >
      {/* ── Collapsed Header ── */}
      <button
        type="button"
        onClick={toggle}
        className={clsx(
          "flex w-full items-center justify-between px-4 py-3",
          "text-sm text-[var(--color-text-secondary)]",
          "hover:bg-[var(--color-bg-secondary)] transition-colors",
          "rounded-xl focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/30"
        )}
        aria-expanded={isExpanded}
        aria-controls="explainability-details"
      >
        <div className="flex items-center gap-3">
          <ShieldCheck
            className="h-4 w-4 text-[var(--color-accent)]"
            aria-hidden="true"
          />
          <span className="font-medium text-[var(--color-text-primary)]">
            Nachvollziehbarkeit
          </span>

          {/* Compact summary in collapsed state */}
          <span className="hidden sm:inline-flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
            <span className="inline-flex items-center gap-1">
              <Database className="h-3 w-3" aria-hidden="true" />
              {dataSources.length} Quelle{dataSources.length !== 1 ? "n" : ""}
            </span>
            <span aria-hidden="true">|</span>
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3 w-3" aria-hidden="true" />
              {queryTimeSeconds.toFixed(1)}s
            </span>
            {confidence !== undefined && (
              <>
                <span aria-hidden="true">|</span>
                <span
                  className={clsx(
                    "inline-flex items-center gap-1",
                    getConfidenceDisplay(confidence).colorClass
                  )}
                >
                  {getConfidenceDisplay(confidence).label}
                </span>
              </>
            )}
            {hasWarnings && (
              <>
                <span aria-hidden="true">|</span>
                <span className="inline-flex items-center gap-1 text-[var(--color-warning)]">
                  <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                  {warnings.length}
                </span>
              </>
            )}
          </span>
        </div>

        {isExpanded ? (
          <ChevronUp className="h-4 w-4" aria-hidden="true" />
        ) : (
          <ChevronDown className="h-4 w-4" aria-hidden="true" />
        )}
      </button>

      {/* ── Expanded Details ── */}
      {isExpanded && (
        <div
          id="explainability-details"
          className="border-t border-[var(--color-border)] px-4 py-4"
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* Datenquellen */}
            <div>
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                <Database className="h-3.5 w-3.5" aria-hidden="true" />
                Datenquellen
              </div>
              <ul className="space-y-1">
                {dataSources.map((source) => (
                  <li
                    key={source}
                    className="text-sm text-[var(--color-text-secondary)]"
                  >
                    {source}
                  </li>
                ))}
              </ul>
            </div>

            {/* Methodik */}
            <div>
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
                Methodik
              </div>
              <p className="text-sm text-[var(--color-text-secondary)]">
                {methodology}
              </p>
              {deterministic && (
                <span className="mt-1.5 inline-flex items-center gap-1 rounded-full bg-[var(--color-success)]/10 px-2 py-0.5 text-xs font-medium text-[var(--color-success)]">
                  <ShieldCheck className="h-3 w-3" aria-hidden="true" />
                  Deterministisch
                </span>
              )}
            </div>

            {/* Konfidenz */}
            <div>
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                <Info className="h-3.5 w-3.5" aria-hidden="true" />
                Konfidenz
              </div>
              {confidence !== undefined ? (
                <div>
                  {/* Progress bar */}
                  <div className="mb-1.5 h-2 w-full overflow-hidden rounded-full bg-[var(--color-bg-secondary)]">
                    <div
                      className={clsx(
                        "h-full rounded-full transition-all duration-500",
                        confidence >= 0.8
                          ? "bg-[var(--color-success)]"
                          : confidence >= 0.5
                            ? "bg-[var(--color-warning)]"
                            : "bg-[var(--color-error)]"
                      )}
                      style={{ width: `${Math.round(confidence * 100)}%` }}
                      role="progressbar"
                      aria-valuenow={Math.round(confidence * 100)}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label="Konfidenz"
                    />
                  </div>
                  <span
                    className={clsx(
                      "text-sm font-medium",
                      getConfidenceDisplay(confidence).colorClass
                    )}
                  >
                    {Math.round(confidence * 100)}% &mdash;{" "}
                    {getConfidenceDisplay(confidence).label}
                  </span>
                </div>
              ) : (
                <span className="text-sm text-[var(--color-text-muted)]">
                  Nicht verfügbar
                </span>
              )}
            </div>

            {/* Verarbeitungszeit */}
            <div>
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                Verarbeitungszeit
              </div>
              <span className="text-sm text-[var(--color-text-secondary)]">
                {queryTimeSeconds < 1
                  ? `${Math.round(queryTimeSeconds * 1000)} ms`
                  : `${queryTimeSeconds.toFixed(2)} s`}
              </span>
            </div>
          </div>

          {/* Warnungen */}
          {hasWarnings && (
            <div className="mt-4 rounded-lg border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/5 p-3">
              <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[var(--color-warning)]">
                <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
                Hinweise
              </div>
              <ul className="space-y-1">
                {warnings.map((warning, idx) => (
                  <li
                    key={idx}
                    className="text-sm text-[var(--color-text-secondary)]"
                  >
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* EU AI Act Hinweis */}
          <p className="mt-3 text-xs text-[var(--color-text-muted)]">
            Gemäß EU AI Act (Verordnung 2024/1689) — Alle Analysen basieren
            auf öffentlich zugänglichen Datenquellen und deterministischen
            Berechnungsverfahren. Keine generativen KI-Modelle werden für die
            Kernergebnisse eingesetzt.
          </p>
        </div>
      )}
    </div>
  );
}
