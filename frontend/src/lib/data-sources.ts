/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Data Source Mappings
 * UC-Key → data source attribution for
 * ExplainabilityBar panel footer.
 * ────────────────────────────────────────────── */

import type { UseCaseKey } from "./types";

export const DATA_SOURCES: Record<UseCaseKey, string> = {
  landscape: "EPO DOCDB · CORDIS",
  maturity: "EPO DOCDB",
  competitive: "EPO DOCDB · Entity Resolution",
  funding: "CORDIS",
  cpc_flow: "EPO DOCDB (CPC-Codes)",
  geographic: "EPO DOCDB · CORDIS",
  research_impact: "Semantic Scholar · CORDIS",
  temporal: "EPO DOCDB · CORDIS",
  tech_cluster: "EPO DOCDB (CPC-Codes)",
  euroscivoc: "CORDIS EuroSciVoc",
  actor_type: "CORDIS",
  patent_grant: "EPO DOCDB",
  publication: "CORDIS Publikationen",
};
