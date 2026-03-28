"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Export / Download Button
 * Triggers backend export endpoint and saves
 * the response as a file download
 * ────────────────────────────────────────────── */

import { useState, useCallback } from "react";
import { Download, Loader2 } from "lucide-react";
import clsx from "clsx";

interface DownloadButtonProps {
  format: "csv" | "pdf" | "xlsx";
  technology: string;
  disabled?: boolean;
}

const FORMAT_LABELS: Record<DownloadButtonProps["format"], string> = {
  csv: "CSV",
  pdf: "PDF",
  xlsx: "Excel",
};

const FORMAT_MIME: Record<DownloadButtonProps["format"], string> = {
  csv: "text/csv",
  pdf: "application/pdf",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
};

export default function DownloadButton({
  format,
  technology,
  disabled = false,
}: DownloadButtonProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleDownload = useCallback(async () => {
    if (!technology.trim() || isLoading) return;

    setIsLoading(true);
    try {
      const res = await fetch("/api/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ technology, format }),
      });

      if (!res.ok) {
        throw new Error(`Export fehlgeschlagen (${res.status})`);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(
        new Blob([blob], { type: FORMAT_MIME[format] })
      );

      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `ti-radar_${technology.replace(/\s+/g, "-")}.${format}`;
      document.body.appendChild(anchor);
      anchor.click();

      // Cleanup
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download-Fehler:", err);
    } finally {
      setIsLoading(false);
    }
  }, [technology, format, isLoading]);

  return (
    <button
      type="button"
      onClick={handleDownload}
      disabled={disabled || isLoading || !technology.trim()}
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] px-3 py-1.5",
        "text-xs font-medium text-[var(--color-text-secondary)] transition-colors",
        "hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text-primary)]",
        "disabled:cursor-not-allowed disabled:opacity-50"
      )}
      aria-label={`Als ${FORMAT_LABELS[format]} exportieren`}
    >
      {isLoading ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
      ) : (
        <Download className="h-3.5 w-3.5" aria-hidden="true" />
      )}
      {FORMAT_LABELS[format]}
    </button>
  );
}
