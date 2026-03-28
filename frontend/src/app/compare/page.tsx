"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Technologie-Vergleich
 * Zwei Technologien nebeneinander analysieren
 * und Kennzahlen in Tabelle + Radar vergleichen
 * ────────────────────────────────────────────── */

import { useState, useCallback } from "react";
import Link from "next/link";
import {
  Radar as RadarIcon,
  ArrowLeft,
  Search,
  Loader2,
  AlertTriangle,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import clsx from "clsx";
import { useRadarQuery } from "@/hooks/useRadarQuery";
import ComparisonTable from "@/components/compare/ComparisonTable";
import ComparisonRadar from "@/components/compare/ComparisonRadar";
import type { RadarRequest } from "@/lib/types";
import { USE_CASES } from "@/lib/types";

/** Baut ein RadarRequest aus einem Technologienamen */
function buildRequest(technology: string, useMock: boolean): RadarRequest {
  return {
    technology: technology.trim(),
    time_range: 10,
    european_only: false,
    use_cases: [...USE_CASES],
    top_n: 10,
    use_mock: useMock,
  };
}

export default function ComparePage() {
  // Eingabefelder
  const [inputA, setInputA] = useState("");
  const [inputB, setInputB] = useState("");
  const [useMock, setUseMock] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("ti-radar-mock") === "true";
    }
    return false;
  });

  // Abfrage-Parameter (null = noch nicht gesucht)
  const [paramsA, setParamsA] = useState<RadarRequest | null>(null);
  const [paramsB, setParamsB] = useState<RadarRequest | null>(null);

  // TanStack Query Hooks
  const queryA = useRadarQuery(paramsA);
  const queryB = useRadarQuery(paramsB);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (inputA.trim()) setParamsA(buildRequest(inputA, useMock));
      if (inputB.trim()) setParamsB(buildRequest(inputB, useMock));
    },
    [inputA, inputB, useMock]
  );

  const isAnyLoading =
    queryA.isLoading || queryA.isFetching || queryB.isLoading || queryB.isFetching;
  const bothLoaded = queryA.data && queryB.data;

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
        <div className="mx-auto flex max-w-[1200px] items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="rounded-md p-1.5 text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-panel)] hover:text-[var(--color-accent)]"
              aria-label="Zurück zum Dashboard"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <RadarIcon
              className="h-6 w-6 text-[var(--color-accent)]"
              aria-hidden="true"
            />
            <div>
              <h1 className="text-lg font-bold text-[var(--color-text-primary)]">
                Technologie-Vergleich
              </h1>
              <p className="text-xs text-[var(--color-text-muted)]">
                Zwei Technologien nebeneinander analysieren
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Hauptinhalt */}
      <main className="mx-auto max-w-[1200px] px-4 py-6 sm:px-6">
        {/* Suchformular: Zwei Eingabefelder nebeneinander */}
        <form
          onSubmit={handleSubmit}
          className="mb-8 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)] p-4 shadow-sm"
          role="search"
          aria-label="Technologie-Vergleich Suche"
        >
          <div className="flex flex-col gap-4 md:flex-row md:items-end">
            {/* Technologie A */}
            <div className="flex-1">
              <label
                htmlFor="tech-a-input"
                className="mb-1.5 block text-sm font-medium text-[var(--color-chart-1)]"
              >
                Technologie A
              </label>
              <div className="relative">
                <Search
                  className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]"
                  aria-hidden="true"
                />
                <input
                  id="tech-a-input"
                  type="text"
                  value={inputA}
                  onChange={(e) => setInputA(e.target.value)}
                  placeholder="z.B. Quantencomputing"
                  className="input-field pl-10"
                  autoComplete="off"
                />
              </div>
            </div>

            {/* Technologie B */}
            <div className="flex-1">
              <label
                htmlFor="tech-b-input"
                className="mb-1.5 block text-sm font-medium text-[var(--color-chart-2)]"
              >
                Technologie B
              </label>
              <div className="relative">
                <Search
                  className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]"
                  aria-hidden="true"
                />
                <input
                  id="tech-b-input"
                  type="text"
                  value={inputB}
                  onChange={(e) => setInputB(e.target.value)}
                  placeholder="z.B. Solid-State Batterien"
                  className="input-field pl-10"
                  autoComplete="off"
                />
              </div>
            </div>

            {/* Mock-Toggle */}
            <div className="shrink-0">
              <span className="mb-1.5 block text-sm font-medium text-[var(--color-text-secondary)]">
                Datenquelle
              </span>
              <button
                type="button"
                role="switch"
                aria-checked={useMock}
                aria-label="Mock-Datenbank verwenden"
                onClick={() => setUseMock((prev) => {
                  const next = !prev;
                  localStorage.setItem("ti-radar-mock", String(next));
                  return next;
                })}
                className={clsx(
                  "flex items-center gap-2 rounded-lg border px-3 py-2.5 text-sm transition-colors",
                  useMock
                    ? "border-[var(--color-accent-gold)] bg-[var(--color-accent-gold)]/10 text-[var(--color-accent-gold)]"
                    : "border-[var(--color-border)] text-[var(--color-text-secondary)]"
                )}
              >
                {useMock ? (
                  <ToggleRight className="h-5 w-5" aria-hidden="true" />
                ) : (
                  <ToggleLeft className="h-5 w-5" aria-hidden="true" />
                )}
                <span className="hidden sm:inline">{useMock ? "Mock" : "Live"}</span>
              </button>
            </div>

            {/* Absenden */}
            <div className="shrink-0">
              <label className="mb-1.5 hidden text-sm font-medium text-transparent select-none md:block">
                Aktion
              </label>
              <button
                type="submit"
                disabled={
                  !inputA.trim() || !inputB.trim() || isAnyLoading
                }
                className="btn-primary w-full md:w-auto"
                aria-label="Vergleich starten"
              >
                {isAnyLoading ? (
                  <>
                    <Loader2
                      className="mr-2 h-4 w-4 animate-spin"
                      aria-hidden="true"
                    />
                    Analysiere...
                  </>
                ) : (
                  "Vergleichen"
                )}
              </button>
            </div>
          </div>
        </form>

        {/* Leerzustand */}
        {!paramsA && !paramsB && (
          <div
            className="flex flex-col items-center justify-center py-24 text-center"
            role="status"
          >
            <RadarIcon
              className="mb-4 h-16 w-16 text-[var(--color-text-muted)] opacity-40"
              aria-hidden="true"
            />
            <h2 className="mb-2 text-xl font-semibold text-[var(--color-text-secondary)]">
              Technologien vergleichen
            </h2>
            <p className="max-w-md text-sm text-[var(--color-text-muted)]">
              Geben Sie zwei Technologien ein, um deren Kennzahlen in einer
              Vergleichstabelle und einem Radar-Diagramm gegenueberzustellen.
            </p>
          </div>
        )}

        {/* Ladezustand: Skeleton */}
        {(paramsA || paramsB) && isAnyLoading && !bothLoaded && (
          <div className="space-y-6">
            {/* Skeleton-Tabelle */}
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)] p-4">
              <div className="space-y-3">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="flex gap-4">
                    <div className="h-4 w-1/3 animate-pulse rounded bg-[var(--color-border)] opacity-40" />
                    <div className="h-4 w-1/4 animate-pulse rounded bg-[var(--color-border)] opacity-30" />
                    <div className="h-4 w-1/4 animate-pulse rounded bg-[var(--color-border)] opacity-30" />
                  </div>
                ))}
              </div>
            </div>
            {/* Skeleton-Radar */}
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)] p-4">
              <div className="mx-auto h-64 w-64 animate-pulse rounded-full bg-[var(--color-border)] opacity-20" />
            </div>
          </div>
        )}

        {/* Fehler */}
        {(queryA.error || queryB.error) && (
          <div
            className="mb-6 flex items-start gap-3 rounded-lg border border-[var(--color-error)]/30 bg-[var(--color-error)]/5 p-4"
            role="alert"
          >
            <AlertTriangle
              className="mt-0.5 h-5 w-5 shrink-0 text-[var(--color-error)]"
              aria-hidden="true"
            />
            <div className="text-sm">
              {queryA.error && (
                <p className="text-[var(--color-error)]">
                  <strong>Technologie A:</strong> {queryA.error.message}
                </p>
              )}
              {queryB.error && (
                <p className="text-[var(--color-error)]">
                  <strong>Technologie B:</strong> {queryB.error.message}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Ergebnisse */}
        {bothLoaded && (
          <div className="space-y-6">
            <ComparisonTable
              techA={{
                name: paramsA!.technology,
                data: queryA.data!,
              }}
              techB={{
                name: paramsB!.technology,
                data: queryB.data!,
              }}
            />
            <ComparisonRadar
              techA={{
                name: paramsA!.technology,
                data: queryA.data!,
              }}
              techB={{
                name: paramsB!.technology,
                data: queryB.data!,
              }}
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)] py-4 text-center text-xs text-[var(--color-text-muted)]">
        TI-Radar v3 &mdash; Bachelorarbeit Technologie-Intelligence &mdash; HWR
        Berlin
      </footer>
    </div>
  );
}
