"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Report-Dialog
 * Modal zur Auswahl von Format und Use Cases
 * fuer den kombinierten Report-Export
 * ────────────────────────────────────────────── */

import { useState, useCallback, useEffect } from "react";
import { createPortal } from "react-dom";
import { X, Loader2, Download, FileText, Sheet, FileSpreadsheet } from "lucide-react";
import clsx from "clsx";
import {
  USE_CASES,
  USE_CASE_LABELS,
  type UseCaseKey,
} from "@/lib/types";

type ExportFormat = "pdf" | "xlsx" | "csv";

interface ReportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  technology: string;
  availableUcs: UseCaseKey[];
}

const FORMAT_OPTIONS: { value: ExportFormat; label: string; icon: typeof FileText }[] = [
  { value: "pdf", label: "PDF-Report", icon: FileText },
  { value: "xlsx", label: "Excel", icon: Sheet },
  { value: "csv", label: "CSV", icon: FileSpreadsheet },
];

const FORMAT_MIME: Record<ExportFormat, string> = {
  pdf: "application/pdf",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  csv: "text/csv",
};

export default function ReportDialog({
  isOpen,
  onClose,
  technology,
  availableUcs,
}: ReportDialogProps) {
  const [format, setFormat] = useState<ExportFormat>("pdf");
  const [selectedUcs, setSelectedUcs] = useState<Set<UseCaseKey>>(
    () => new Set(availableUcs),
  );
  const [isLoading, setIsLoading] = useState(false);

  const toggleUc = useCallback((uc: UseCaseKey) => {
    setSelectedUcs((prev) => {
      const next = new Set(prev);
      if (next.has(uc)) {
        next.delete(uc);
      } else {
        next.add(uc);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelectedUcs(new Set(availableUcs));
  }, [availableUcs]);

  const selectNone = useCallback(() => {
    setSelectedUcs(new Set());
  }, []);

  const handleDownload = useCallback(async () => {
    if (!technology.trim() || selectedUcs.size === 0 || isLoading) return;

    setIsLoading(true);
    try {
      const res = await fetch("/api/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          technology,
          format,
          use_cases: Array.from(selectedUcs),
        }),
      });

      if (!res.ok) {
        throw new Error(`Export fehlgeschlagen (${res.status})`);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(
        new Blob([blob], { type: FORMAT_MIME[format] }),
      );

      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `ti-radar_report_${technology.replace(/\s+/g, "-")}.${format}`;
      document.body.appendChild(anchor);
      anchor.click();

      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
      onClose();
    } catch (err) {
      console.error("Report-Download-Fehler:", err);
    } finally {
      setIsLoading(false);
    }
  }, [technology, format, selectedUcs, isLoading, onClose]);

  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!isOpen || !mounted) return null;

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Dialog */}
      <div
        className="relative z-10 w-full max-w-lg rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)] p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-[var(--color-text-primary)]">
              Report generieren
            </h2>
            <p className="mt-0.5 text-xs text-[var(--color-text-muted)]">
              Technologie: <strong>{technology}</strong>
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text-primary)]"
            aria-label="Dialog schliessen"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Format-Auswahl */}
        <div className="mb-5">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
            Format
          </h3>
          <div className="flex gap-2">
            {FORMAT_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              return (
                <button
                  key={opt.value}
                  onClick={() => setFormat(opt.value)}
                  className={clsx(
                    "flex flex-1 items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
                    format === opt.value
                      ? "border-[var(--color-accent)] bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
                      : "border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-accent)] hover:text-[var(--color-text-primary)]",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* UC-Auswahl */}
        <div className="mb-5">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
              Use Cases ({selectedUcs.size}/{availableUcs.length})
            </h3>
            <div className="flex gap-2 text-xs">
              <button
                onClick={selectAll}
                className="text-[var(--color-accent)] hover:underline"
              >
                Alle
              </button>
              <button
                onClick={selectNone}
                className="text-[var(--color-text-muted)] hover:underline"
              >
                Keine
              </button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {USE_CASES.filter((uc) => availableUcs.includes(uc)).map((uc) => (
              <label
                key={uc}
                className={clsx(
                  "flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-xs transition-colors",
                  selectedUcs.has(uc)
                    ? "border-[var(--color-accent)]/40 bg-[var(--color-accent)]/5 text-[var(--color-text-primary)]"
                    : "border-[var(--color-border)] text-[var(--color-text-muted)]",
                )}
              >
                <input
                  type="checkbox"
                  checked={selectedUcs.has(uc)}
                  onChange={() => toggleUc(uc)}
                  className="accent-[var(--color-accent)]"
                />
                {USE_CASE_LABELS[uc]}
              </label>
            ))}
          </div>
        </div>

        {/* Download-Button */}
        <button
          onClick={handleDownload}
          disabled={isLoading || selectedUcs.size === 0}
          className={clsx(
            "flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors",
            "bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent)]/90",
            "disabled:cursor-not-allowed disabled:opacity-50",
          )}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          {isLoading ? "Wird generiert ..." : "Report herunterladen"}
        </button>
      </div>
    </div>,
    document.body,
  );
}
