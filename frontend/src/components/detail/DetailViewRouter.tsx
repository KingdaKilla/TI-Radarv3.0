"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v2 -- Detail View Router
 * Maps active UC key to the correct detail
 * component and wraps it in DetailOverlay
 * ────────────────────────────────────────────── */

import type { RadarResponse, UseCaseKey } from "@/lib/types";
import DetailOverlay from "./DetailOverlay";
import {
  LandscapeDetail,
  MaturityDetail,
  CompetitiveDetail,
  FundingDetail,
  CpcFlowDetail,
  GeographicDetail,
  ResearchImpactDetail,
  TemporalDetail,
  TechClusterDetail,
  EuroSciVocDetail,
  ActorTypeDetail,
  PatentGrantDetail,
  PublicationDetail,
} from "./details";

interface DetailViewRouterProps {
  activeDetail: UseCaseKey;
  data: RadarResponse;
  onClose: () => void;
}

export default function DetailViewRouter({
  activeDetail,
  data,
  onClose,
}: DetailViewRouterProps) {
  const detailComponents: Record<UseCaseKey, React.ReactNode | null> = {
    landscape:       data.landscape       ? <LandscapeDetail data={data.landscape} dataCompleteYear={data.maturity?.data_complete_year ?? 2025} /> : null,
    maturity:        data.maturity        ? <MaturityDetail data={data.maturity} />                : null,
    competitive:     data.competitive     ? <CompetitiveDetail data={data.competitive} />          : null,
    funding:         data.funding         ? <FundingDetail data={data.funding} />                  : null,
    cpc_flow:        data.cpc_flow        ? <CpcFlowDetail data={data.cpc_flow} />                : null,
    geographic:      data.geographic      ? <GeographicDetail data={data.geographic} />            : null,
    research_impact: data.research_impact ? <ResearchImpactDetail data={data.research_impact} />  : null,
    temporal:        data.temporal        ? <TemporalDetail data={data.temporal} />                : null,
    tech_cluster:    data.tech_cluster    ? <TechClusterDetail data={data.tech_cluster} />        : null,
    euroscivoc:      data.euroscivoc      ? <EuroSciVocDetail data={data.euroscivoc} />            : null,
    actor_type:      data.actor_type      ? <ActorTypeDetail data={data.actor_type} />            : null,
    patent_grant:    data.patent_grant    ? <PatentGrantDetail data={data.patent_grant} />        : null,
    publication:     data.publication     ? <PublicationDetail data={data.publication} />          : null,
  };

  const content = detailComponents[activeDetail];
  if (!content) return null;

  return (
    <DetailOverlay ucKey={activeDetail} onClose={onClose}>
      {content}
    </DetailOverlay>
  );
}
