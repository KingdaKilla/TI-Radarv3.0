/* ──────────────────────────────────────────────
 * TI-Radar v3 -- UC Insight Descriptions
 * Erklärt dem Nutzer per Tooltip, welche
 * Erkenntnisse jeder Use Case liefert.
 * ────────────────────────────────────────────── */

import type { UseCaseKey } from "./types";

export const UC_INSIGHTS: Record<UseCaseKey, string> = {
  landscape:
    "Zeigt die Entwicklung von Patent-, Projekt- und Publikationsanzahlen im Zeitverlauf. " +
    "Erkennen Sie Wachstumstrends (CAGR) und ob eine Technologie an Dynamik gewinnt oder verliert.",
  maturity:
    "Bestimmt den Reifegrad einer Technologie anhand der S-Kurve (Emerging, Growth, Mature, Declining). " +
    "Hilft bei der Einschätzung, ob der optimale Einstiegszeitpunkt bereits erreicht ist.",
  competitive:
    "Analysiert die Marktkonzentration (HHI) und identifiziert die dominanten Akteure. " +
    "Erfahren Sie, ob der Markt von wenigen Playern dominiert wird oder breit aufgestellt ist.",
  funding:
    "Zeigt EU-Fördervolumen nach Forschungsgebiet und zeitlichem Verlauf. " +
    "Identifizieren Sie, welche Bereiche aktuell am stärksten gefördert werden.",
  cpc_flow:
    "Visualisiert technologische Konvergenz zwischen CPC-Patentklassen. " +
    "Entdecken Sie Whitespace-Innovationslücken — Technologiefelder, die noch kaum kombiniert wurden.",
  geographic:
    "Zeigt die globale Verteilung von Patentanmeldern und Forschungsorganisationen. " +
    "Erkennen Sie regionale Schwerpunkte und internationale Kooperationsmuster.",
  research_impact:
    "Bewertet den wissenschaftlichen Impact über h-Index, Zitationsraten und Top-Institutionen. " +
    "Finden Sie die einflussreichsten Forschungseinrichtungen in Ihrem Technologiefeld.",
  temporal:
    "Analysiert die Akteursdynamik: Welche Unternehmen sind neu eingestiegen, welche persistent " +
    "und welche ausgeschieden? Erkennen Sie Marktveränderungen frühzeitig.",
  tech_cluster:
    "Erstellt ein 5-dimensionales Technologieprofil aus Patentaktivität, Akteursvielfalt, " +
    "CPC-Dichte, Kohärenz und Wachstum. Vergleichen Sie Technologien multidimensional.",
  euroscivoc:
    "Ordnet Forschungsprojekte wissenschaftlichen Disziplinen zu (EuroSciVoc-Taxonomie). " +
    "Erkennen Sie, wie interdisziplinär eine Technologie erforscht wird.",
  actor_type:
    "Schlüsselt die beteiligten Organisationen nach Typ auf: Hochschule, Forschung, Industrie, " +
    "öffentlich. Verstehen Sie das Innovationsökosystem rund um eine Technologie.",
  patent_grant:
    "Analysiert Erteilungsquoten und die durchschnittliche Zeit bis zur Patenterteilung. " +
    "Schätzen Sie die Erfolgsaussichten und Zeitrahmen für eigene Patentanmeldungen ein.",
  publication:
    "Verknüpft CORDIS-Publikationen mit geförderten Projekten. Messen Sie die " +
    "Publikationseffizienz (Publications per Project) und den Return on Investment.",
};
