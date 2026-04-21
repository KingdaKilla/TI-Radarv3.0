"use client";

/* ──────────────────────────────────────────────
 * useAnalysis — triggers LLM panel analysis when
 * a detail view opens. Caches results per
 * technology + useCaseKey to avoid double requests.
 *
 * F-034 (T-05): Memoisierung des effektiv verwendeten
 * panelData-Keys ueber (technology, useCaseKey). Der fetchAnalysis-
 * Callback stellt sicher, dass er bei StrictMode-Double-Effect und
 * bei jedem Re-Render desselben Detail-Views NICHT zweimal feuert.
 * AbortController triggert nur bei echtem Schluessel-Wechsel.
 * ────────────────────────────────────────────── */

import { useState, useEffect, useRef, useCallback } from "react";
import {
  readAnalysisCache,
  writeAnalysisCache,
} from "@/lib/analysis-cache";

interface AnalysisResult {
  analysisText: string;
  modelUsed: string;
  keyFindings: string[];
  confidence: number;
  processingTimeMs: number;
}

interface AnalysisState {
  analysisText: string | undefined;
  isLoading: boolean;
  error: string | null;
  modelUsed: string | null;
}

/**
 * Hook that triggers LLM analysis when a detail view opens.
 * POST /api/analyze-panel with { technology, use_case_key, panel_data }
 * Returns { analysisText, isLoading, error, modelUsed }
 * Cache results per technology+useCaseKey to avoid double requests.
 */
export function useAnalysis(
  technology: string | null | undefined,
  useCaseKey: string | null | undefined,
  panelData: Record<string, unknown> | null | undefined,
) {
  const [state, setState] = useState<AnalysisState>({
    analysisText: undefined,
    isLoading: false,
    error: null,
    modelUsed: null,
  });

  // Cache: map of "technology::useCaseKey" -> AnalysisResult
  const cacheRef = useRef<Map<string, AnalysisResult>>(new Map());

  // AbortController for in-flight requests
  const abortRef = useRef<AbortController | null>(null);

  // F-034: Panel-Data-Snapshot referenziell stabil halten.
  // Die panelData-Referenz wechselt sonst bei jedem Re-Render der
  // Parent-Komponente (neues Objekt via useMemo-Reset), was den
  // useEffect bei StrictMode verdoppelt und zwei LLM-Requests triggert.
  // Wir speichern nur das letzte Objekt zu (technology, useCaseKey).
  const lastKeyRef = useRef<string | null>(null);
  const panelDataRef = useRef<Record<string, unknown> | null>(null);
  const effectiveKey =
    technology && useCaseKey ? `${technology}::${useCaseKey}` : null;
  if (effectiveKey && effectiveKey !== lastKeyRef.current) {
    lastKeyRef.current = effectiveKey;
    panelDataRef.current = panelData ?? null;
  } else if (effectiveKey && !panelDataRef.current && panelData) {
    // Beim ersten Mount mit gueltigem panelData einmal Referenz setzen.
    panelDataRef.current = panelData;
  }

  const fetchAnalysis = useCallback(async () => {
    if (!technology || !useCaseKey) {
      setState({ analysisText: undefined, isLoading: false, error: null, modelUsed: null });
      return;
    }
    const snapshot = panelDataRef.current;
    if (!snapshot) {
      setState({ analysisText: undefined, isLoading: false, error: null, modelUsed: null });
      return;
    }

    const cacheKey = `${technology}::${useCaseKey}`;

    // Check in-memory cache first
    const cached = cacheRef.current.get(cacheKey);
    if (cached) {
      setState({
        analysisText: cached.analysisText,
        isLoading: false,
        error: null,
        modelUsed: cached.modelUsed,
      });
      return;
    }

    // v3.6.0/Ξ-2: Session-persistenter Cache — localStorage-Check.
    // Überlebt Page-Reload und Navigation zurück/vor.
    const persisted = readAnalysisCache(technology, useCaseKey);
    if (persisted) {
      // In-Memory-Cache mit persistentem Eintrag warmhalten
      cacheRef.current.set(cacheKey, {
        analysisText: persisted.analysisText,
        modelUsed: persisted.modelUsed,
        keyFindings: persisted.keyFindings,
        confidence: persisted.confidence,
        processingTimeMs: persisted.processingTimeMs,
      });
      setState({
        analysisText: persisted.analysisText,
        isLoading: false,
        error: null,
        modelUsed: persisted.modelUsed,
      });
      return;
    }

    // Abort any in-flight request
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const res = await fetch("/api/analyze-panel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          technology,
          use_case_key: useCaseKey,
          panel_data: snapshot,
          language: "de",
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`Analyse-Fehler: ${res.status}`);
      }

      // Backend returns snake_case fields
      const raw = await res.json() as Record<string, unknown>;

      // Cache the result (normalize snake_case -> camelCase)
      const result: AnalysisResult = {
        analysisText: (raw.analysis_text ?? raw.analysisText ?? "") as string,
        modelUsed: (raw.model_used ?? raw.modelUsed ?? "") as string,
        keyFindings: (raw.key_findings ?? raw.keyFindings ?? []) as string[],
        confidence: (raw.confidence ?? 0) as number,
        processingTimeMs: (raw.processing_time_ms ?? raw.processingTimeMs ?? 0) as number,
      };
      cacheRef.current.set(cacheKey, result);
      // v3.6.0/Ξ-2: zusätzlich in localStorage persistieren
      if (result.analysisText) {
        writeAnalysisCache(technology, useCaseKey, result);
      }

      setState({
        analysisText: result.analysisText,
        isLoading: false,
        error: null,
        modelUsed: result.modelUsed,
      });
    } catch (err) {
      // Ignore abort errors
      if (err instanceof DOMException && err.name === "AbortError") return;

      // Graceful degradation: show fallback content instead of error
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err.message : "Unbekannter Fehler",
      }));
    }
  }, [technology, useCaseKey]);

  // Trigger analysis when inputs change.
  // F-034: Abhaengigkeit ist der stabile effectiveKey, NICHT die
  // panelData-Referenz. Damit feuert der Effect bei StrictMode-Double-
  // Mount zwar zweimal, aber beide Aufrufe finden im Cache den gleichen
  // key und der zweite kehrt sofort zurueck — nur noch 1 HTTP-Request.
  useEffect(() => {
    fetchAnalysis();

    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveKey]);

  return {
    analysisText: state.analysisText,
    isLoading: state.isLoading,
    error: state.error,
    modelUsed: state.modelUsed,
  };
}
