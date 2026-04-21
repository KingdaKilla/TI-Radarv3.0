"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Detail Analysis Section
 * Rendert die vom LLM-Service generierte Analyse.
 * Ab v3.6.6 ist dies der einzige Analyse-Block im Detail-Overlay;
 * statische/deterministische Inline-Narrative wurden entfernt.
 * ────────────────────────────────────────────── */

import type { ReactNode } from "react";

interface DetailAnalysisSectionProps {
  /** Markdown-ähnlicher Analysetext vom LLM Service. */
  analysisText?: string;
  /** Zeigt Skeleton-Animation während der LLM-Analyse läuft. */
  isLoading?: boolean;
  /** Zusätzlicher Footer (z.B. Modell-Name, vom Parent gesteuert). */
  children?: ReactNode;
}

/**
 * Einfaches Inline-Rendering von Markdown-ähnlichem Text.
 * Unterstützt **fett**, Zeilenumbrüche und Aufzählungszeichen.
 */
function renderAnalysisText(text: string): ReactNode[] {
  const lines = text.split("\n");
  return lines.map((line, idx) => {
    if (!line.trim()) {
      return <br key={idx} />;
    }

    const isBullet = /^[\s]*[-•]\s+/.test(line);
    const content = isBullet ? line.replace(/^[\s]*[-•]\s+/, "") : line;

    const parts: ReactNode[] = [];
    const boldRegex = /\*\*(.+?)\*\*/g;
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = boldRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(content.slice(lastIndex, match.index));
      }
      parts.push(
        <strong key={`${idx}-b-${match.index}`} className="font-semibold">
          {match[1]}
        </strong>
      );
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < content.length) {
      parts.push(content.slice(lastIndex));
    }

    if (isBullet) {
      return (
        <li key={idx} className="ml-4 list-disc text-sm leading-relaxed text-[var(--color-text)]">
          {parts}
        </li>
      );
    }

    return (
      <p key={idx} className="text-sm leading-relaxed text-[var(--color-text)]">
        {parts}
      </p>
    );
  });
}

function AnalysisSkeleton() {
  return (
    <div className="animate-pulse space-y-3" aria-label="KI-Analyse wird geladen">
      <div className="h-3 w-full rounded bg-[var(--color-border)]" />
      <div className="h-3 w-5/6 rounded bg-[var(--color-border)]" />
      <div className="h-3 w-4/6 rounded bg-[var(--color-border)]" />
      <div className="h-3 w-3/4 rounded bg-[var(--color-border)]" />
    </div>
  );
}

/** Transparentes "KI-generiert"-Badge im Section-Header. */
function AiBadge() {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border border-[var(--color-accent)]/40 bg-[var(--color-accent)]/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-[var(--color-accent)]"
      aria-label="Von KI generiert"
      title="Dieser Text wurde vollständig von einem Sprachmodell erzeugt."
    >
      <svg
        width="10"
        height="10"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M12 3l1.9 4.6L18.5 9.5l-4.6 1.9L12 16l-1.9-4.6L5.5 9.5l4.6-1.9z" />
        <path d="M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z" />
      </svg>
      KI-generiert
    </span>
  );
}

export default function DetailAnalysisSection({
  analysisText,
  isLoading,
  children,
}: DetailAnalysisSectionProps) {
  const hasText = Boolean(analysisText && analysisText.trim());

  let content: ReactNode;
  if (isLoading) {
    content = <AnalysisSkeleton />;
  } else if (hasText) {
    const hasListItems = /^[\s]*[-•]\s+/m.test(analysisText!);
    const rendered = renderAnalysisText(analysisText!);
    content = hasListItems ? (
      <ul className="space-y-1">{rendered}</ul>
    ) : (
      <div className="space-y-2">{rendered}</div>
    );
  } else {
    content = (
      <p className="text-sm italic text-[var(--color-text-muted)]">
        KI-Analyse derzeit nicht verfügbar. Bitte später erneut öffnen.
      </p>
    );
  }

  return (
    <section
      className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)] p-6"
      aria-label="KI-Analyse"
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
          KI-Analyse
        </h3>
        <AiBadge />
      </div>

      {content}

      {(hasText || isLoading) && (
        <p className="mt-4 border-t border-[var(--color-border)] pt-3 text-[11px] leading-relaxed text-[var(--color-text-muted)]">
          Automatisch von einem Sprachmodell erzeugt auf Basis der gezeigten
          Panel-Daten. Inhalte können ungenau, unvollständig oder falsch sein
          (Halluzinationen) und ersetzen keine fachliche Prüfung.
          {children ? <span className="block mt-1">{children}</span> : null}
        </p>
      )}
    </section>
  );
}
