"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Search Bar Component
 * Technology input with autocomplete, time range
 * selector and European-only toggle
 * ────────────────────────────────────────────── */

import { useState, useCallback, useRef, useEffect } from "react";
import { Search, Globe, ToggleLeft, ToggleRight } from "lucide-react";
import clsx from "clsx";
import { useSuggestions } from "@/hooks/useRadarQuery";
import { TIME_RANGE_OPTIONS } from "@/lib/types";
import type { RadarRequest } from "@/lib/types";
import { USE_CASES } from "@/lib/types";

interface SearchBarProps {
  onSubmit: (params: RadarRequest) => void;
  isLoading: boolean;
}

export default function SearchBar({ onSubmit, isLoading }: SearchBarProps) {
  const [technology, setTechnology] = useState("");
  const [timeRange, setTimeRange] = useState(10);
  const [europeanOnly, setEuropeanOnly] = useState(true);
  const [useMock, setUseMock] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("ti-radar-mock") === "true";
    }
    return false;
  });
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [debouncedQuery, setDebouncedQuery] = useState("");

  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce the query for suggestions
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => {
      setDebouncedQuery(technology);
    }, 300);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [technology]);

  const { data: suggestions = [] } = useSuggestions(debouncedQuery);

  // Close suggestions when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSubmit = useCallback(
    (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!technology.trim() || isLoading) return;

      setShowSuggestions(false);
      onSubmit({
        technology: technology.trim(),
        years: timeRange,
        european_only: europeanOnly,
        use_cases: [...USE_CASES],
        top_n: 10,
        use_mock: useMock,
      });
    },
    [technology, timeRange, europeanOnly, useMock, isLoading, onSubmit]
  );

  const handleSuggestionClick = useCallback(
    (suggestion: string) => {
      setTechnology(suggestion);
      setShowSuggestions(false);
      // Auto-submit on suggestion click
      onSubmit({
        technology: suggestion,
        years: timeRange,
        european_only: europeanOnly,
        use_cases: [...USE_CASES],
        top_n: 10,
        use_mock: useMock,
      });
    },
    [timeRange, europeanOnly, useMock, onSubmit]
  );

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full rounded-xl border border-transparent bg-transparent p-4"
      role="search"
      aria-label="Technologie-Suche"
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
        {/* Technology Input — takes majority of space */}
        <div className="relative flex-[3]">
          <label
            htmlFor="technology-input"
            className="mb-1.5 block text-sm font-medium text-[var(--color-text-secondary)]"
          >
            Technologie
          </label>
          <div className="relative">
            <Search
              className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]"
              aria-hidden="true"
            />
            <input
              ref={inputRef}
              id="technology-input"
              type="text"
              value={technology}
              onChange={(e) => {
                setTechnology(e.target.value);
                setShowSuggestions(true);
              }}
              onFocus={() => setShowSuggestions(true)}
              placeholder="z.B. Quantencomputing, Solid-State Batterien, mRNA..."
              className="input-field bg-[var(--color-bg-panel)]/50 pl-10 text-base"
              autoComplete="off"
              aria-autocomplete="list"
              aria-controls="suggestions-list"
              aria-expanded={showSuggestions && suggestions.length > 0}
            />
          </div>

          {/* Autocomplete Suggestions */}
          {showSuggestions && suggestions.length > 0 && (
            <div
              ref={suggestionsRef}
              id="suggestions-list"
              role="listbox"
              aria-label="Vorschläge"
              className="absolute z-50 mt-1 w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-panel)] py-1 shadow-lg"
            >
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  role="option"
                  aria-selected={false}
                  className="w-full px-4 py-2 text-left text-sm text-[var(--color-text-primary)] hover:bg-[var(--color-bg-secondary)] transition-colors"
                  onClick={() => handleSuggestionClick(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Time Range Selector */}
        <div className="shrink-0">
          <label
            htmlFor="time-range"
            className="mb-1.5 block text-sm font-medium text-[var(--color-text-secondary)]"
          >
            Zeitraum
          </label>
          <select
            id="time-range"
            value={timeRange}
            onChange={(e) => setTimeRange(Number(e.target.value))}
            className="input-field bg-[var(--color-bg-panel)]/50 w-full lg:w-36"
            aria-label="Zeitraum wählen"
          >
            {TIME_RANGE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* European-Only Toggle */}
        <div className="shrink-0">
          <span className="mb-1.5 block text-sm font-medium text-[var(--color-text-secondary)]">
            Nur Europa
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={europeanOnly}
            aria-label="Nur europaeische Daten anzeigen"
            onClick={() => setEuropeanOnly((prev) => !prev)}
            className={clsx(
              "flex items-center gap-2 rounded-lg border px-3 py-2.5 text-sm transition-colors",
              europeanOnly
                ? "border-[var(--color-accent)] bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
                : "border-[var(--color-border)] text-[var(--color-text-secondary)]"
            )}
          >
            <Globe className="h-4 w-4" aria-hidden="true" />
            {europeanOnly ? (
              <ToggleRight className="h-5 w-5" aria-hidden="true" />
            ) : (
              <ToggleLeft className="h-5 w-5" aria-hidden="true" />
            )}
            <span className="hidden sm:inline">EU</span>
          </button>
        </div>

        {/* Mock-DB Toggle */}
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

        {/* Submit Button */}
        <div className="shrink-0">
          <label className="mb-1.5 block text-sm font-medium text-transparent select-none lg:block hidden">
            Aktion
          </label>
          <button
            type="submit"
            disabled={!technology.trim() || isLoading}
            className="btn-primary hover:glow-accent w-full lg:w-auto"
            aria-label="Radar-Analyse starten"
          >
            {isLoading ? (
              <>
                <svg
                  className="mr-2 h-4 w-4 animate-spin"
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden="true"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Analysiere...
              </>
            ) : (
              "Analyse starten"
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
