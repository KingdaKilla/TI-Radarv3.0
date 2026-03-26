/* ──────────────────────────────────────────────
 * TI-Radar v2 -- Methodology Tooltip Mappings
 * UC-Key → methodology description for
 * ExplainabilityBar panel footer tooltips.
 * ────────────────────────────────────────────── */

import type { UseCaseKey } from "./types";

export const METHODOLOGY_TOOLTIPS: Record<UseCaseKey, string> = {
  landscape:
    "Zeitreihenanalyse der jährlichen Patent-, Projekt- und Publikationsanzahlen mit CAGR-Berechnung.",
  maturity:
    "Logistische S-Kurve (Bass-Modell) wird an kumulative Patentdaten angepasst. Modellselektion via AICc.",
  competitive:
    "HHI und CR4 berechnet aus Patentanteilen der Top-Akteure. Optional mit Entity Resolution.",
  funding:
    "Aggregation der EC Max Contribution aus CORDIS-Projekten nach Forschungsgebiet und Jahr.",
  cpc_flow:
    "Jaccard-Ähnlichkeit zwischen CPC-Code-Paaren. Hohe Ähnlichkeit = häufige Kombination in Patenten.",
  geographic:
    "Verteilung der Patentanmelder und CORDIS-Organisationen nach Ländern.",
  research_impact:
    "h-Index, Zitationsmetriken und Top-Institutionen aus Semantic Scholar und CORDIS.",
  temporal:
    "Analyse der Akteursdynamik: Neuzugänge, persistente und ausgeschiedene Akteure pro Jahr.",
  tech_cluster:
    "5-dimensionales Profil aus Patentanzahl, Akteursanzahl, CPC-Dichte, Kohärenz und CAGR.",
  euroscivoc:
    "Zuordnung der CORDIS-Projekte zu EuroSciVoc-Wissenschaftsdisziplinen mit Interdisziplinaritätsindex.",
  actor_type:
    "Verteilung der CORDIS-Organisationen nach Typ: Hochschule, Forschung, Industrie, Öffentlich, Sonstige.",
  patent_grant:
    "Erteilungsquote = Erteilte Patente / Anmeldungen. Time-to-Grant aus filing_date → publication_date.",
  publication:
    "CORDIS-Publikationen verknüpft mit geförderten Projekten. Publications per Project und per Million EUR.",
};
