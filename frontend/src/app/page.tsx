"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Main Radar Dashboard Page
 * Progressive disclosure with 4 thematic clusters
 * Landing carousel → Dashboard carousel + panels
 * ────────────────────────────────────────────── */

import { useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { Radar, Activity, Clock, GitCompareArrows, Home } from "lucide-react";
import SearchBar from "@/components/SearchBar";
import { useRadarQuery } from "@/hooks/useRadarQuery";
import { useDetailView } from "@/hooks/useDetailView";
import DetailViewRouter from "@/components/detail/DetailViewRouter";
import ExecutiveSummary from "@/components/dashboard/ExecutiveSummary";
import ClusterCarousel from "@/components/dashboard/ClusterCarousel";
import ClusterContent from "@/components/dashboard/ClusterContent";
import { buildClusterData } from "@/lib/clusters";
import type { Cluster } from "@/lib/clusters";
import type { RadarRequest } from "@/lib/types";

export default function DashboardPage() {
  const [params, setParams] = useState<RadarRequest | null>(null);
  const [activeClusterIndex, setActiveClusterIndex] = useState(0);

  const { data, isLoading, error, isFetching } = useRadarQuery(params);
  const { activeDetail, openDetail, closeDetail } = useDetailView();

  const handleSubmit = useCallback((newParams: RadarRequest) => {
    setParams(newParams);
  }, []);

  const handleReset = useCallback(() => {
    setParams(null);
    setActiveClusterIndex(0);
  }, []);

  /** Panel loading state: global loading or fetching */
  const panelLoading = isLoading || isFetching;

  /** Datenvollstaendigkeit: ab welchem Jahr sind Daten moeglicherweise unvollstaendig */
  const dataCompleteYear = data?.maturity?.data_complete_year ?? 2024;

  /** Build cluster data from radar response */
  const clusterData = useMemo(
    () => (data ? buildClusterData(data) : null),
    [data],
  );

  /** Landing clusters for pre-search state (static placeholders) */
  const landingClusters: Cluster[] = useMemo(
    () => [
      {
        id: "technology",
        title: "Technologie & Reife",
        subtitle: "",
        description:
          "Patentlandschaft, S-Kurven-Reife und CPC-Technologiekonvergenz",
        image: "/images/clusters/technology.png",
        metrics: [],
        ucKeys: [] as Cluster["ucKeys"],
      },
      {
        id: "market",
        title: "Marktakteure",
        subtitle: "",
        description: "Wettbewerber, Marktkonzentration und Akteurs-Dynamik",
        image: "/images/clusters/market.png",
        metrics: [],
        ucKeys: [] as Cluster["ucKeys"],
      },
      {
        id: "research",
        title: "Forschung & Förderung",
        subtitle: "",
        description:
          "EU-Förderung, Forschungsimpact und Publikationsanalyse",
        image: "/images/clusters/research.png",
        metrics: [],
        ucKeys: [] as Cluster["ucKeys"],
      },
      {
        id: "geography",
        title: "Geographische Perspektive",
        subtitle: "",
        description:
          "Länderverteilung, Technologie-Cluster und Klassifikation",
        image: "/images/clusters/geography.png",
        metrics: [],
        ucKeys: [] as Cluster["ucKeys"],
      },
    ],
    [],
  );

  /** Derived state: which clusters to show and which layout mode */
  const displayClusters = clusterData?.clusters ?? landingClusters;
  const isDashboard = !!clusterData && !!data;

  return (
    <div className="flex min-h-screen flex-col bg-hero-gradient">
      {/* Header */}
      <header className="border-b border-[var(--color-border)] bg-[var(--color-bg-glass)] backdrop-blur-md">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <Radar
              className="h-7 w-7 text-[var(--color-accent)]"
              aria-hidden="true"
            />
            <div>
              <h1 className="text-lg font-bold text-[var(--color-text-primary)]">
                TI-Radar <span className="text-gold">v3</span>
              </h1>
              <p className="text-xs text-[var(--color-text-muted)]">
                Technologie-Intelligence Dashboard
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Zurück zum Start */}
            {data && (
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 rounded-lg border border-[var(--color-accent-gold)] px-3 py-1.5 text-xs font-medium text-[var(--color-accent-gold)] transition-colors hover:bg-[var(--color-accent-gold)]/10"
                aria-label="Zurück zum Startbildschirm"
              >
                <Home className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="hidden sm:inline">Neue Analyse</span>
              </button>
            )}

            {/* Vergleich-Navigation */}
            <Link
              href="/compare"
              className="flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-secondary)] transition-colors hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
              aria-label="Technologie-Vergleich öffnen"
            >
              <GitCompareArrows className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="hidden sm:inline">Vergleichen</span>
            </Link>

            {/* Metadata Indicator */}
            {data?.metadata && (
              <div className="hidden items-center gap-4 text-xs text-[var(--color-text-muted)] sm:flex">
                <span className="flex items-center gap-1">
                  <Activity className="h-3.5 w-3.5" aria-hidden="true" />
                  {data.metadata.data_sources.join(", ")}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                  {data.metadata.query_time_seconds.toFixed(1)}s
                </span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto flex flex-1 flex-col w-full max-w-[1600px] px-4 py-6 sm:px-6">
        {/* ── Landing State (no data) ── */}
        {!isDashboard && (
          <div className="flex flex-col items-center justify-center gap-10 min-h-[calc(100vh-8rem)]">
            {/* Large Carousel — fills available space */}
            <div className="w-full flex-1 flex items-center">
              <ClusterCarousel
                clusters={displayClusters}
                activeIndex={activeClusterIndex}
                onSelect={setActiveClusterIndex}
                compact={false}
              />
            </div>

            {/* Glassmorphism Search Bar */}
            <div className="glass rounded-2xl p-5 w-[80%] max-w-5xl mb-4">
              <SearchBar onSubmit={handleSubmit} isLoading={panelLoading} />
            </div>
          </div>
        )}

        {/* Error State */}
        {error && !data && params && (
          <div
            className="flex flex-col items-center justify-center py-24 text-center"
            role="alert"
            aria-live="assertive"
          >
            <p className="text-sm font-medium text-[var(--color-error)]">
              Fehler bei der Analyse
            </p>
            <p className="mt-2 max-w-md text-xs text-[var(--color-text-muted)]">
              {error.message}
            </p>
          </div>
        )}

        {/* Loading State (before first data) */}
        {panelLoading && !data && params && !error && (
          <div
            className="flex flex-col items-center justify-center py-24"
            role="status"
            aria-live="polite"
            aria-label="Daten werden geladen..."
          >
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-[var(--color-border)] border-t-[var(--color-accent)]" />
            <p className="mt-4 text-sm text-[var(--color-text-muted)]">
              Analyse wird durchgeführt...
            </p>
          </div>
        )}

        {/* ── Dashboard State (has data) ── */}
        {isDashboard && (
          <div
            className="max-w-6xl mx-auto flex flex-1 flex-col items-center pb-[5px]"
            role="region"
            aria-label="Radar-Analyse Ergebnisse"
          >
            {/* Glassmorphism Executive Summary */}
            <div className="glass rounded-2xl p-4 mb-6 w-full">
              <ExecutiveSummary data={clusterData.summary} />
            </div>

            {/* Compact Carousel */}
            <ClusterCarousel
              clusters={displayClusters}
              activeIndex={activeClusterIndex}
              onSelect={setActiveClusterIndex}
              compact={isDashboard}
            />

            {/* Active Cluster Content Panels — key forces remount on cluster change */}
            <div className="panel-card p-4 mt-6 w-full flex-1 min-h-0 overflow-auto flex flex-col">
              <ClusterContent
                key={displayClusters[activeClusterIndex].id}
                cluster={displayClusters[activeClusterIndex]}
                data={data}
                dataCompleteYear={dataCompleteYear}
                onDetailClick={openDetail}
              />
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="shrink-0 border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)] py-3 text-center text-xs text-[var(--color-text-muted)]">
        TI-Radar v3 &mdash; Bachelorarbeit Technologie-Intelligence &mdash; HWR
        Berlin
      </footer>

      {/* Detail View Overlay */}
      {activeDetail && data && (
        <DetailViewRouter
          activeDetail={activeDetail}
          data={data}
          onClose={closeDetail}
        />
      )}
    </div>
  );
}
