"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Report-Button (Header)
 * Oeffnet den ReportDialog zur Report-Generierung
 * ────────────────────────────────────────────── */

import { useState } from "react";
import { FileText } from "lucide-react";
import ReportDialog from "./ReportDialog";
import type { UseCaseKey } from "@/lib/types";

interface ReportButtonProps {
  technology: string;
  availableUcs: UseCaseKey[];
}

export default function ReportButton({
  technology,
  availableUcs,
}: ReportButtonProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-secondary)] transition-colors hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
        aria-label="Report generieren"
      >
        <FileText className="h-3.5 w-3.5" aria-hidden="true" />
        <span className="hidden sm:inline">Report</span>
      </button>

      <ReportDialog
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        technology={technology}
        availableUcs={availableUcs}
      />
    </>
  );
}
