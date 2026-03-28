/* ──────────────────────────────────────────────
 * TI-Radar v3 -- API Client
 * Communicates with the FastAPI backend
 * ────────────────────────────────────────────── */

import type { RadarRequest, RadarResponse, HealthResponse } from "./types";
import { transformRadarResponse } from "./transform";

// Client-side calls go through Next.js API proxy routes (/api/*)
// to avoid CORS issues and keep the backend URL internal.
const API_URL = "";

/** Generic fetch wrapper with error handling */
async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_URL}${path}`;

  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.text().catch(() => "Unbekannter Fehler");
    throw new Error(
      `API-Fehler ${res.status}: ${errorBody}`
    );
  }

  return res.json() as Promise<T>;
}

/** POST /api/radar -- Full radar analysis (via Next.js proxy) */
export async function analyzeRadar(
  params: RadarRequest
): Promise<RadarResponse> {
  const raw = await apiFetch<unknown>("/api/radar", {
    method: "POST",
    body: JSON.stringify(params),
  });
  return transformRadarResponse(raw);
}

/** GET /api/suggestions?q=... -- Autocomplete suggestions (via Next.js proxy) */
export async function getSuggestions(
  query: string
): Promise<string[]> {
  if (!query || query.trim().length < 2) {
    return [];
  }

  return apiFetch<string[]>(
    `/api/suggestions?q=${encodeURIComponent(query.trim())}`
  );
}

/** GET /health -- Backend health check */
export async function checkHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}
