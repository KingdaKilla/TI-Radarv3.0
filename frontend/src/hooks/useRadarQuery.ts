/* ──────────────────────────────────────────────
 * TI-Radar v2 -- TanStack Query Hook
 * Wraps the radar analysis endpoint
 * ────────────────────────────────────────────── */

import { useQuery } from "@tanstack/react-query";
import { analyzeRadar, getSuggestions } from "@/lib/api";
import type { RadarRequest, RadarResponse } from "@/lib/types";
import { USE_CASES } from "@/lib/types";

/** Stable query-key factory */
const radarKeys = {
  all: ["radar"] as const,
  analyze: (params: RadarRequest) => [...radarKeys.all, "analyze", params] as const,
  suggestions: (query: string) => [...radarKeys.all, "suggestions", query] as const,
};

/**
 * useRadarQuery -- triggers the full radar analysis.
 * Only fires when `enabled` is true (i.e., the user submitted a search).
 */
export function useRadarQuery(params: RadarRequest | null) {
  return useQuery<RadarResponse, Error>({
    queryKey: radarKeys.analyze(
      params ?? {
        technology: "",
        time_range: 10,
        european_only: false,
        use_cases: [...USE_CASES],
        top_n: 10,
      }
    ),
    queryFn: () => {
      if (!params) {
        throw new Error("Keine Suchparameter angegeben");
      }
      return analyzeRadar(params);
    },
    enabled: params !== null && params.technology.trim().length > 0,
    staleTime: 5 * 60 * 1000, // 5 Minuten
    gcTime: 15 * 60 * 1000, // 15 Minuten im Cache
    retry: 1,
  });
}

/**
 * useSuggestions -- debounced autocomplete suggestions.
 */
export function useSuggestions(query: string) {
  return useQuery<string[], Error>({
    queryKey: radarKeys.suggestions(query),
    queryFn: () => getSuggestions(query),
    enabled: query.trim().length >= 2,
    staleTime: 2 * 60 * 1000, // 2 Minuten
    placeholderData: (previousData) => previousData,
  });
}
