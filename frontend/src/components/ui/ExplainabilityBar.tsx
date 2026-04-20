"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- ExplainabilityBar
 * Collapsible transparency bar for EU AI Act
 * compliance. Shows data sources, methodology,
 * and processing time.
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
} from "lucide-react";
import clsx from "clsx";

export interface ExplainabilityBarProps {
  dataSources: string[];
  queryTimeSeconds: number;
  methodology: string;
  /**
   * @deprecated Seit v3.4.10: Konfidenz-Sektion wurde entfernt (nicht
   * einheitlich ableitbar pro UC). Prop bleibt als No-Op erhalten für
   * Abwärtskompat, wird aber nicht mehr dargestellt.
   */
  confidence?: number;
  warnings?: string[];
  deterministic?: boolean;
}

export default function ExplainabilityBar({
  dataSources,
  queryTimeSeconds,
  methodology,
  // confidence-Prop absichtlich nicht destructured — siehe @deprecated oben
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
          {/* Bug v3.4.10/α-D: Konfidenz-Sektion wurde entfernt, weil eine
              belastbare Konfidenz-Metrik pro UC nicht einheitlich ableitbar
              war — die Anzeige "Nicht verfügbar" stand häufig da und hat
              das Vertrauen in die Transparenz-Bar eher geschwächt. Die
              bestehenden drei Sektionen (Datenquellen / Methodik /
              Verarbeitungszeit) reichen für EU-AI-Act-Transparenz aus. */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
