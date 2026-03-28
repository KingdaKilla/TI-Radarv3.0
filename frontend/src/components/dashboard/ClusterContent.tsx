"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Cluster Content Renderer
 * Tab navigation within each cluster, renders
 * existing UC panel components
 * ────────────────────────────────────────────── */

import { useState } from "react";
import type { Cluster } from "@/lib/clusters";
import type { RadarResponse, UseCaseKey } from "@/lib/types";

import {
  LandscapePanel,
  MaturityPanel,
  CompetitivePanel,
  FundingPanel,
  CpcFlowPanel,
  GeographicPanel,
  ResearchImpactPanel,
  TemporalPanel,
  TechClusterPanel,
  EuroSciVocPanel,
  ActorTypePanel,
  PatentGrantPanel,
  PublicationPanel,
} from "@/components/panels";

const UC_TAB_LABELS: Record<UseCaseKey, string> = {
  landscape: "Aktivit\u00E4tstrends",
  maturity: "S-Kurve & Reife",
  cpc_flow: "Technologiekonvergenz",
  competitive: "Wettbewerb & HHI",
  temporal: "Dynamik & Persistenz",
  actor_type: "Akteurs-Typen",
  funding: "F\u00F6rderung",
  research_impact: "Forschungsimpact",
  publication: "Publikationen",
  geographic: "Geographie",
  tech_cluster: "Tech-Cluster",
  euroscivoc: "EuroSciVoc",
  patent_grant: "Patenterteilung",
};

interface ClusterContentProps {
  cluster: Cluster;
  data: RadarResponse;
  dataCompleteYear: number;
  onDetailClick?: (ucKey: UseCaseKey) => void;
}

export default function ClusterContent({
  cluster,
  data,
  dataCompleteYear,
  onDetailClick,
}: ClusterContentProps) {
  const [activeTab, setActiveTab] = useState<UseCaseKey>(cluster.ucKeys[0]);

  /** Helper: get the panel-level error from uc_errors if available */
  const panelError = (ucKey: string): string | null => {
    if (data?.uc_errors?.[ucKey]) return data.uc_errors[ucKey];
    return null;
  };

  function renderPanel(ucKey: UseCaseKey) {
    const err = panelError(ucKey);
    const detail = onDetailClick ? () => onDetailClick(ucKey) : undefined;
    const qts = data.metadata?.query_time_seconds;

    switch (ucKey) {
      case "landscape":
        return (
          <LandscapePanel
            data={data.landscape ?? null}
            isLoading={false}
            error={err}
            onDetailClick={detail}
            dataCompleteYear={dataCompleteYear}
            queryTimeSeconds={qts}
          />
        );
      case "maturity":
        return (
          <MaturityPanel
            data={data.maturity ?? null}
            isLoading={false}
            error={err}
            onDetailClick={detail}
            queryTimeSeconds={qts}
          />
        );
      case "cpc_flow":
        return (
          <CpcFlowPanel
            data={data.cpc_flow ?? null}
            isLoading={false}
            error={err}
            onDetailClick={detail}
            queryTimeSeconds={qts}
          />
        );
      case "competitive":
        return (
          <CompetitivePanel
            data={data.competitive ?? null}
            isLoading={false}
            error={err}
            onDetailClick={detail}
            queryTimeSeconds={qts}
          />
        );
      case "temporal":
        return (
          <TemporalPanel
            data={data.temporal ?? null}
            isLoading={false}
            error={err}
            onDetailClick={detail}
            dataCompleteYear={dataCompleteYear}
            queryTimeSeconds={qts}
          />
        );
      case "actor_type":
        return (
          <ActorTypePanel
            data={data.actor_type ?? null}
            isLoading={false}
            error={err}
            onDetailClick={detail}
            queryTimeSeconds={qts}
          />
        );
      case "funding":
        return (
          <FundingPanel
            data={data.funding ?? null}
            isLoading={false}
            error={err}
            onDetailClick={detail}
            queryTimeSeconds={qts}
          />
        );
      case "research_impact":
        return (
          <ResearchImpactPanel
            data={data.research_impact ?? null}
            isLoading={false}
            error={err}
            onDetailClick={detail}
            dataCompleteYear={dataCompleteYear}
            queryTimeSeconds={qts}
          />
        );
      case "publication":
        return (
          <PublicationPanel
            data={data.publication ?? null}
            isLoading={false}
            error={err}
            onDetailClick={detail}
            queryTimeSeconds={qts}
          />
        );
      case "geographic":
        return (
          <GeographicPanel
            data={data.geographic ?? null}
            isLoading={false}
            error={err}
            onDetailClick={detail}
            queryTimeSeconds={qts}
          />
        );
      case "tech_cluster":
        return (
          <TechClusterPanel
            data={data.tech_cluster ?? null}
            isLoading={false}
            error={err}
            onDetailClick={detail}
            queryTimeSeconds={qts}
          />
        );
      case "euroscivoc":
        return (
          <EuroSciVocPanel
            data={data.euroscivoc ?? null}
            isLoading={false}
            error={err}
            onDetailClick={detail}
            queryTimeSeconds={qts}
          />
        );
      case "patent_grant":
        return (
          <PatentGrantPanel
            data={data.patent_grant ?? null}
            isLoading={false}
            error={err}
            onDetailClick={detail}
            dataCompleteYear={dataCompleteYear}
            queryTimeSeconds={qts}
          />
        );
      default:
        return null;
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-2 mb-4 shrink-0">
        {cluster.ucKeys.map((key) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === key
                ? "bg-[var(--color-accent)] text-white"
                : "bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-border)]"
            }`}
          >
            {UC_TAB_LABELS[key] ?? key}
          </button>
        ))}
      </div>

      {/* Active Panel — fills remaining height */}
      <div className="flex-1 min-h-0">
        {renderPanel(activeTab)}
      </div>
    </div>
  );
}
