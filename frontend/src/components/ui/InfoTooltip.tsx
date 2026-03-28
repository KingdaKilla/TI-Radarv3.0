"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- InfoTooltip
 * Reusable tooltip component that shows an info
 * icon with explanatory text on hover/focus.
 * ────────────────────────────────────────────── */

import { useState, useCallback, useId } from "react";
import { Info } from "lucide-react";
import clsx from "clsx";

export interface InfoTooltipProps {
  /** Tooltip text to display on hover/focus. */
  text: string;
  /** Additional CSS classes for the wrapper. */
  className?: string;
}

export default function InfoTooltip({ text, className }: InfoTooltipProps) {
  const [visible, setVisible] = useState(false);
  const tooltipId = useId();

  const show = useCallback(() => setVisible(true), []);
  const hide = useCallback(() => setVisible(false), []);

  return (
    <span
      className={clsx("relative inline-flex items-center", className)}
      onMouseEnter={show}
      onMouseLeave={hide}
    >
      <button
        type="button"
        onFocus={show}
        onBlur={hide}
        aria-describedby={visible ? tooltipId : undefined}
        className={clsx(
          "inline-flex items-center justify-center rounded-full",
          "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]",
          "focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/30",
          "transition-colors duration-150"
        )}
      >
        <Info className="h-3.5 w-3.5" aria-hidden="true" />
        <span className="sr-only">Info</span>
      </button>

      {/* Tooltip popover */}
      <span
        id={tooltipId}
        role="tooltip"
        className={clsx(
          "pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2",
          "w-max max-w-xs rounded-lg px-3 py-2",
          "bg-[var(--color-bg-primary)] border border-[var(--color-border)]",
          "text-xs leading-relaxed text-[var(--color-text-secondary)]",
          "shadow-lg z-50",
          "transition-all duration-150",
          visible
            ? "opacity-100 translate-y-0"
            : "opacity-0 translate-y-1 invisible"
        )}
      >
        {text}
        {/* Arrow */}
        <span
          className={clsx(
            "absolute top-full left-1/2 -translate-x-1/2",
            "border-4 border-transparent border-t-[var(--color-border)]"
          )}
          aria-hidden="true"
        />
      </span>
    </span>
  );
}
