"use client";

/* ──────────────────────────────────────────────
 * ChatInput — text input + send button
 * ────────────────────────────────────────────── */

import { useState, useCallback } from "react";
import { Send } from "lucide-react";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");

  const handleSubmit = useCallback(() => {
    if (value.trim() && !disabled) {
      onSend(value.trim());
      setValue("");
    }
  }, [value, disabled, onSend]);

  return (
    <div className="flex gap-2 border-t border-[var(--color-border)] p-3">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        placeholder="Frage stellen..."
        disabled={disabled}
        className="flex-1 rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--color-accent)]"
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !value.trim()}
        className="rounded-md bg-[var(--color-accent)] px-3 py-2 text-sm text-white disabled:opacity-50"
        aria-label="Nachricht senden"
      >
        <Send size={16} />
      </button>
    </div>
  );
}
