"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Detail View Overlay Shell
 * Full-viewport CSS overlay with sticky header,
 * scrollable content area, and print support
 * ────────────────────────────────────────────── */

import type { ReactNode } from "react";
import { X, Printer } from "lucide-react";
import type { UseCaseKey } from "@/lib/types";
import { USE_CASE_LABELS, UC_NUMBERS } from "@/lib/types";

interface DetailOverlayProps {
  ucKey: UseCaseKey;
  onClose: () => void;
  children: ReactNode;
}

export default function DetailOverlay({ ucKey, onClose, children }: DetailOverlayProps) {
  const title = USE_CASE_LABELS[ucKey];
  const ucNum = UC_NUMBERS[ucKey];
  const badgeText = `UC${ucNum.label ?? ucNum.number}`;

  return (
    <div
      className="detail-overlay fixed inset-0 z-50 flex flex-col bg-[var(--color-bg-primary)]"
      role="dialog"
      aria-modal="true"
      aria-label={`Detailansicht: ${title}`}
    >
      {/* Sticky Header */}
      <header className="sticky top-0 z-10 flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-6 py-3">
        <div className="flex items-center gap-3">
          <span className="badge-info text-xs font-bold">{badgeText}</span>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
            {title}
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => window.print()}
            className="no-print rounded-lg p-2 text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-primary)] hover:text-[var(--color-text-primary)]"
            aria-label="Drucken"
          >
            <Printer className="h-4 w-4" />
          </button>
          <button
            onClick={onClose}
            className="no-print rounded-lg p-2 text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-primary)] hover:text-[var(--color-text-primary)]"
            aria-label="Detailansicht schließen"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </header>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-6 py-6">
          {children}
        </div>
      </div>
    </div>
  );
}
