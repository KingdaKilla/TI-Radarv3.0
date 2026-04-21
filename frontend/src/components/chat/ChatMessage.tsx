"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v4 -- Chat Message
 * Rendert eine einzelne Chat-Nachricht (User oder
 * Assistent) mit optionaler Quellenangabe und
 * KI-generiert-Kennzeichnung (EU AI Act Art. 50(2)).
 * ────────────────────────────────────────────── */

import type { ReactNode } from "react";

export interface ChatMessageProps {
  /** Rolle der Nachricht: "user" oder "assistant". */
  role: "user" | "assistant";
  /** Nachrichteninhalt (Markdown-Text). */
  content: string;
  /** Quellenverweise (source_ids der verwendeten Kontext-Dokumente). */
  sources?: string[];
  /** Name des verwendeten LLM-Modells. */
  modelUsed?: string;
}

/**
 * Einzelne Chat-Nachricht mit Quellenangabe und KI-Kennzeichnung.
 *
 * Assistenten-Nachrichten erhalten automatisch das "KI-generiert"-Badge
 * sowie eine optionale Quellen-Sektion (EU AI Act Transparenz).
 */
export default function ChatMessage({
  role,
  content,
  sources,
  modelUsed,
}: ChatMessageProps) {
  const isAssistant = role === "assistant";

  return (
    <div
      className={`flex ${isAssistant ? "justify-start" : "justify-end"} mb-4`}
    >
      <div
        className={`max-w-[80%] rounded-xl px-4 py-3 ${
          isAssistant
            ? "bg-[var(--color-bg-panel)] border border-[var(--color-border)]"
            : "bg-blue-600 text-white"
        }`}
      >
        {/* Nachrichteninhalt */}
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>

        {/* --- Assistenten-spezifische Transparenz-Elemente --- */}
        {isAssistant && (
          <div className="mt-2 space-y-2">
            {/* EU AI Act Art. 50(2): KI-generierte Inhalte kennzeichnen */}
            <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
              <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                KI-generiert
              </span>
              {modelUsed && <span>Modell: {modelUsed}</span>}
            </div>

            {/* Quellenangaben (Source Attribution) */}
            {sources && sources.length > 0 && (
              <div className="border-t border-[var(--color-border)] pt-2">
                <p className="text-xs font-medium text-[var(--color-text-muted)]">
                  Quellen:
                </p>
                <ul className="mt-1 flex flex-wrap gap-1">
                  {sources.map((src) => (
                    <li
                      key={src}
                      className="inline-flex items-center rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                    >
                      {src}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
