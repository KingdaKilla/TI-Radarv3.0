"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- InfoTooltip
 * Reusable tooltip component that shows an info
 * icon with explanatory text on hover/focus.
 * Uses fixed positioning to escape overflow:hidden.
 * ────────────────────────────────────────────── */

import { useState, useCallback, useId, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
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
  const [mounted, setMounted] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0 });
  const tooltipId = useId();
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => setMounted(true), []);

  const show = useCallback(() => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPos({
        top: rect.top - 8,
        left: rect.left + rect.width / 2,
      });
    }
    setVisible(true);
  }, []);

  const hide = useCallback(() => setVisible(false), []);

  return (
    <span
      className={clsx("relative inline-flex items-center", className)}
      onMouseEnter={show}
      onMouseLeave={hide}
    >
      <button
        ref={triggerRef}
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

      {/* Tooltip rendered via portal to escape overflow:hidden */}
      {mounted && visible && createPortal(
        <span
          id={tooltipId}
          role="tooltip"
          className="pointer-events-none fixed w-max max-w-xs rounded-lg px-3 py-2 bg-[var(--color-bg-primary)] border border-[var(--color-border)] text-xs leading-relaxed text-[var(--color-text-secondary)] shadow-lg z-[9999]"
          style={{
            top: pos.top,
            left: pos.left,
            transform: "translate(-50%, -100%)",
          }}
        >
          {text}
        </span>,
        document.body,
      )}
    </span>
  );
}
