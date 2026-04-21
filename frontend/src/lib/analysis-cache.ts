"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3.6.0 — Analysis-Cache (localStorage)
 *
 * Persistiert LLM-Analysen über Page-Reloads hinaus. Schlüssel:
 * `technology + useCaseKey`. TTL: 24h (gleich wie Backend-Cache).
 *
 * Warum localStorage statt IndexedDB:
 * - Synchron (einfacher API), LLM-Analysen sind klein (~2 KB JSON)
 * - 5-10 MB-Quota pro Origin — für ~1000 Einträge ausreichend
 *
 * Auto-Evict: Bei QuotaExceededError werden die ältesten Einträge gelöscht.
 * ────────────────────────────────────────────── */

export interface CachedAnalysis {
  analysisText: string;
  modelUsed: string;
  keyFindings: string[];
  confidence: number;
  processingTimeMs: number;
  /** UNIX-ms beim Schreiben — für TTL-Check. */
  cachedAt: number;
}

const STORAGE_KEY_PREFIX = "ti-radar:analysis:v1:";
const TTL_MS = 24 * 60 * 60 * 1000; // 24h
const MAX_ENTRIES = 200;

function isBrowser(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function storageKey(technology: string, useCaseKey: string): string {
  return `${STORAGE_KEY_PREFIX}${technology}::${useCaseKey}`;
}

/** Liest einen gecachten Eintrag oder `null` bei Miss / Expired / Parse-Fehler. */
export function readAnalysisCache(
  technology: string,
  useCaseKey: string,
): CachedAnalysis | null {
  if (!isBrowser()) return null;
  try {
    const raw = window.localStorage.getItem(storageKey(technology, useCaseKey));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CachedAnalysis;
    if (!parsed.cachedAt || Date.now() - parsed.cachedAt > TTL_MS) {
      // Abgelaufen — still entfernen und Miss zurückgeben
      window.localStorage.removeItem(storageKey(technology, useCaseKey));
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

/** Schreibt einen Eintrag; bei QuotaExceeded werden älteste Einträge evict. */
export function writeAnalysisCache(
  technology: string,
  useCaseKey: string,
  value: Omit<CachedAnalysis, "cachedAt">,
): void {
  if (!isBrowser()) return;
  const payload: CachedAnalysis = { ...value, cachedAt: Date.now() };
  const key = storageKey(technology, useCaseKey);
  try {
    window.localStorage.setItem(key, JSON.stringify(payload));
    return;
  } catch (err) {
    // Quota voll — älteste Analyse-Einträge evict und erneut versuchen
    if (err instanceof DOMException && (err.name === "QuotaExceededError" || err.code === 22)) {
      evictOldest(Math.max(10, Math.floor(MAX_ENTRIES * 0.1)));
      try {
        window.localStorage.setItem(key, JSON.stringify(payload));
      } catch {
        // Bei wiederholter Fehlern: aufgeben, Read-Only-Fallback
      }
    }
  }
}

/** Sammelt alle Analysis-Keys + cachedAt und löscht die N ältesten. */
function evictOldest(count: number): void {
  if (!isBrowser()) return;
  const entries: Array<{ key: string; cachedAt: number }> = [];
  for (let i = 0; i < window.localStorage.length; i++) {
    const k = window.localStorage.key(i);
    if (!k || !k.startsWith(STORAGE_KEY_PREFIX)) continue;
    try {
      const raw = window.localStorage.getItem(k);
      if (!raw) continue;
      const parsed = JSON.parse(raw) as { cachedAt?: number };
      entries.push({ key: k, cachedAt: parsed.cachedAt ?? 0 });
    } catch {
      // Bei Parse-Fehler: als uralt behandeln, zuerst evict
      entries.push({ key: k, cachedAt: 0 });
    }
  }
  entries.sort((a, b) => a.cachedAt - b.cachedAt);
  for (const e of entries.slice(0, count)) {
    try {
      window.localStorage.removeItem(e.key);
    } catch {
      // Ignore
    }
  }
}

/** Testutility / manueller Reset-Button: Clear komplett. */
export function clearAnalysisCache(): void {
  if (!isBrowser()) return;
  const keysToRemove: string[] = [];
  for (let i = 0; i < window.localStorage.length; i++) {
    const k = window.localStorage.key(i);
    if (k && k.startsWith(STORAGE_KEY_PREFIX)) keysToRemove.push(k);
  }
  keysToRemove.forEach((k) => window.localStorage.removeItem(k));
}
