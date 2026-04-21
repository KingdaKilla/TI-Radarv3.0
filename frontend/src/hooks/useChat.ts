"use client";

import { useState, useCallback } from "react";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
}

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
}

export interface PanelContext {
  active_panel?: string | null;
  data?: Record<string, unknown> | null;
  panels?: Record<string, Record<string, unknown>> | null;
}

/**
 * Chat hook — sends messages to /api/chat (Next.js proxy -> orchestrator).
 * Maintains conversation history for multi-turn RAG context.
 * Optionally includes panel analysis data for analysis-aware responses.
 */
export function useChat(
  technology: string | null,
  panelContext?: PanelContext | null,
) {
  const [state, setState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    error: null,
  });

  const sendMessage = useCallback(
    async (message: string) => {
      if (!technology || !message.trim()) return;

      const userMsg: ChatMessage = { role: "user", content: message };
      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, userMsg],
        isLoading: true,
        error: null,
      }));

      try {
        const body: Record<string, unknown> = {
          technology,
          message,
          history: state.messages.map((m) => ({
            role: m.role,
            content: m.content,
          })),
        };

        // Include panel context if available (Hybrid Architecture: optional)
        if (panelContext && Object.keys(panelContext).length > 0) {
          body.panel_context = panelContext;
        }

        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });

        if (!res.ok) throw new Error(`Chat-Fehler: ${res.status}`);
        const data = await res.json();

        const assistantMsg: ChatMessage = {
          role: "assistant",
          content: data.answer,
          sources: data.sources,
        };

        setState((prev) => ({
          ...prev,
          messages: [...prev.messages, assistantMsg],
          isLoading: false,
        }));
      } catch (err) {
        setState((prev) => ({
          ...prev,
          isLoading: false,
          error: err instanceof Error ? err.message : "Unbekannter Fehler",
        }));
      }
    },
    [technology, state.messages, panelContext],
  );

  const reset = useCallback(() => {
    setState({ messages: [], isLoading: false, error: null });
  }, []);

  return { ...state, sendMessage, reset };
}
