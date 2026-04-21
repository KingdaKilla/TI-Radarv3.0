"use client";

/* ──────────────────────────────────────────────
 * ChatSidebar — slide-in panel for RAG chat
 * ────────────────────────────────────────────── */

import { useEffect, useRef } from "react";
import { MessageSquare, X } from "lucide-react";
import ChatMessage from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { useChat, type PanelContext } from "@/hooks/useChat";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  technology: string | null;
  panelContext?: PanelContext | null;
}

export function ChatSidebar({ isOpen, onClose, technology, panelContext }: Props) {
  const { messages, isLoading, error, sendMessage, reset } =
    useChat(technology, panelContext);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  // Reset chat when technology changes
  useEffect(() => {
    reset();
  }, [technology, reset]);

  if (!isOpen) return null;

  return (
    <div className="fixed right-0 top-0 z-50 flex h-full w-[380px] flex-col border-l border-[var(--color-border)] bg-[var(--color-bg)]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3">
        <div className="flex items-center gap-2">
          <MessageSquare size={18} />
          <span className="text-sm font-medium">Chat</span>
          {technology && (
            <span className="text-xs text-[var(--color-text-muted)]">
              &mdash; {technology}
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
          aria-label="Chat schliessen"
        >
          <X size={18} />
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 && (
          <p className="text-center text-sm text-[var(--color-text-muted)]">
            Stelle Fragen zu {technology || "der Technologie"}
          </p>
        )}
        {messages.map((msg, i) => (
          <ChatMessage
            key={i}
            role={msg.role}
            content={msg.content}
            sources={msg.sources}
          />
        ))}
        {isLoading && (
          <div className="mb-3 flex justify-start">
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-glass)] px-3 py-2 text-sm text-[var(--color-text-muted)]">
              Denke nach...
            </div>
          </div>
        )}
        {error && (
          <p className="text-center text-sm text-red-400">{error}</p>
        )}
      </div>

      {/* Input */}
      <ChatInput onSend={sendMessage} disabled={isLoading || !technology} />
    </div>
  );
}
