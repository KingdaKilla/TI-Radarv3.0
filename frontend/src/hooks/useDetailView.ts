"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- Detail View State Hook
 * Manages overlay state, URL params, keyboard
 * and browser-back support for UC detail views
 * ────────────────────────────────────────────── */

import { useState, useCallback, useEffect } from "react";
import type { UseCaseKey, USE_CASES } from "@/lib/types";

interface UseDetailViewReturn {
  activeDetail: UseCaseKey | null;
  openDetail: (ucKey: UseCaseKey) => void;
  closeDetail: () => void;
}

const VALID_KEYS = new Set<string>([
  "landscape", "maturity", "competitive", "funding",
  "cpc_flow", "geographic", "research_impact", "temporal",
  "tech_cluster", "euroscivoc", "actor_type", "patent_grant",
  "publication",
]);

function isValidUCKey(value: string | null): value is UseCaseKey {
  return value !== null && VALID_KEYS.has(value);
}

export function useDetailView(): UseDetailViewReturn {
  const [activeDetail, setActiveDetail] = useState<UseCaseKey | null>(null);

  const openDetail = useCallback((ucKey: UseCaseKey) => {
    setActiveDetail(ucKey);
    const url = new URL(window.location.href);
    url.searchParams.set("detail", ucKey);
    window.history.pushState({}, "", url.toString());
    document.body.style.overflow = "hidden";
  }, []);

  const closeDetail = useCallback(() => {
    setActiveDetail(null);
    const url = new URL(window.location.href);
    url.searchParams.delete("detail");
    window.history.pushState({}, "", url.toString());
    document.body.style.overflow = "";
  }, []);

  // Browser-Back Button
  useEffect(() => {
    function handlePopState() {
      const params = new URLSearchParams(window.location.search);
      const detail = params.get("detail");
      if (isValidUCKey(detail)) {
        setActiveDetail(detail);
        document.body.style.overflow = "hidden";
      } else {
        setActiveDetail(null);
        document.body.style.overflow = "";
      }
    }
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  // URL-Initialisierung beim Mount (Deep-Link)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const detail = params.get("detail");
    if (isValidUCKey(detail)) {
      setActiveDetail(detail);
      document.body.style.overflow = "hidden";
    }
  }, []);

  // Escape-Taste
  useEffect(() => {
    if (!activeDetail) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setActiveDetail(null);
        const url = new URL(window.location.href);
        url.searchParams.delete("detail");
        window.history.pushState({}, "", url.toString());
        document.body.style.overflow = "";
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeDetail]);

  return { activeDetail, openDetail, closeDetail };
}
