"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Detail Analysis Section
 * Zeigt LLM-generierte Analyse-Texte oder
 * Placeholder wenn kein Text vorhanden ist.
 * ────────────────────────────────────────────── */

import type { ReactNode } from "react";

interface DetailAnalysisSectionProps {
  children?: ReactNode;
  /** Markdown-ähnlicher Analysetext vom LLM Service. */
  analysisText?: string;
  /** Zeigt Skeleton-Animation während der LLM-Analyse läuft. */
  isLoading?: boolean;
}

/**
 * Einfaches Inline-Rendering von Markdown-ähnlichem Text.
 * Unterstützt **fett**, Zeilenumbrüche und Aufzählungszeichen.
 */
function renderAnalysisText(text: string): ReactNode[] {
  const lines = text.split("\n");
  return lines.map((line, idx) => {
    // Leerzeile → Abstand
    if (!line.trim()) {
      return <br key={idx} />;
    }

    // Aufzählungszeichen (- oder •)
    const isBullet = /^[\s]*[-•]\s+/.test(line);
    const content = isBullet ? line.replace(/^[\s]*[-•]\s+/, "") : line;

    // **fett** ersetzen
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

/** Skeleton-Platzhalter während LLM-Analyse läuft. */
function AnalysisSkeleton() {
  return (
    <div className="animate-pulse space-y-3" aria-label="Analyse wird geladen">
      <div className="h-3 w-full rounded bg-[var(--color-border)]" />
      <div className="h-3 w-5/6 rounded bg-[var(--color-border)]" />
      <div className="h-3 w-4/6 rounded bg-[var(--color-border)]" />
      <div className="h-3 w-3/4 rounded bg-[var(--color-border)]" />
    </div>
  );
}

export default function DetailAnalysisSection({
  children,
  analysisText,
  isLoading,
}: DetailAnalysisSectionProps) {
  // Inhalt bestimmen: Loading → analysisText → children → Placeholder
  let content: ReactNode;

  if (isLoading) {
    content = <AnalysisSkeleton />;
  } else if (analysisText && analysisText.trim()) {
    // Prüfen ob Aufzählungspunkte vorhanden → <ul> verwenden
    const hasListItems = /^[\s]*[-•]\s+/m.test(analysisText);
    const rendered = renderAnalysisText(analysisText);

    content = hasListItems ? (
      <ul className="space-y-1">{rendered}</ul>
    ) : (
      <div className="space-y-2">{rendered}</div>
    );
  } else if (children) {
    content = children;
  } else {
    content = (
      <p className="text-sm italic text-[var(--color-text-muted)]">
        Textuelle Analyse wird in einer zukünftigen Version hinzugefügt.
      </p>
    );
  }

  return (
    <section
      className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)] p-6"
      aria-label="Analyse"
    >
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
        Analyse
      </h3>
      {content}
    </section>
  );
}
