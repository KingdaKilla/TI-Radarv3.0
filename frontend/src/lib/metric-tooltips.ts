/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Metric Tooltip Mappings
 * Central mapping of metric keys to German
 * tooltip descriptions for InfoTooltip usage.
 * ────────────────────────────────────────────── */

export const METRIC_TOOLTIPS: Record<string, string> = {
  hhi: "Herfindahl-Hirschman Index — Misst die Marktkonzentration. 0 = vollständig fragmentiert, 1 = Monopol. >0,25 gilt als hoch konzentriert (DOJ-Skala: >2.500).",
  cagr: "Compound Annual Growth Rate — Durchschnittliche jährliche Wachstumsrate über den betrachteten Zeitraum.",
  r_squared:
    "Bestimmtheitsmaß (R²) — Gibt an, wie gut das statistische Modell die Daten erklärt. 1,0 = perfekte Anpassung.",
  phase:
    "Reifephase nach S-Kurven-Modell: Aufkommend (<10%), Wachstum (10–50%), Ausgereift (50–90%), Sättigung (>90%).",
  h_index:
    "Hirsch-Index — h Publikationen wurden jeweils mindestens h-mal zitiert. Misst den wissenschaftlichen Impact.",
  // INFO-12: Schwellen, die der Header-Badge "… Impact (h=…)" verwendet.
  // Werden in clusters.ts als badgeTooltips["Sehr hoher Impact (h=…)"] etc.
  // referenziert (Single Source of Truth).
  h_index_thresholds:
    "h-Index-Schwellen f\u00FCr den Header-Badge: \u2265 100 = Sehr hoch \u00B7 \u2265 50 = Hoch \u00B7 \u2265 20 = Moderat \u00B7 < 20 = Gering. Quelle: clusters.ts.",
  cr4: "Concentration Ratio — Marktanteil der 4 größten Akteure. >60% = oligopolistisch.",
  jaccard:
    "Jaccard-Ähnlichkeitsindex — Misst die Überlappung zweier CPC-Code-Mengen (0 = keine, 1 = identisch).",
  shannon:
    "Shannon-Entropie — Misst die Diversität der Technologie-Codes. Höher = breiter gestreut.",
  aicc: "Akaike-Informationskriterium (korrigiert) — Vergleicht Modellgüte unter Berücksichtigung der Komplexität. Niedriger = besser.",
  grant_rate:
    "Anteil der erteilten Patente an allen Anmeldungen in Prozent.",
  funding_volume:
    "Gesamtsumme der EU-Fördermittel (EC Max Contribution) für relevante CORDIS-Projekte.",
  saturation_level:
    "Geschätzte maximale kumulative Patentanzahl laut S-Kurven-Modell.",
  inflection_year:
    "Jahr der maximalen Wachstumsrate — Wendepunkt der S-Kurve.",
  churn_rate:
    "Anteil der Akteure, die im Folgejahr nicht mehr aktiv sind.",
  persistence_ratio:
    "Anteil der Akteure, die auch im Folgejahr aktiv bleiben.",
  patents: "Patentanmeldungen aus der EPO DOCDB-Datenbank.",
  patent_scope:
    "Der Header zählt ALLE Patente (EPO DOCDB, ungefiltert). UC12 trennt Anmeldungen (Kind-Codes A*) und Erteilungen (B*). Gesamtzahl ≥ Anmeldungen + Erteilungen, da u. a. Utility Models (U) und Korrekturen zusätzlich zählen.",
  patent_applications:
    "Patent-Anmeldungen (EPO Kind-Codes A, A1, A2, A3, A4, A8, A9). Offenlegungsschrift vor Erteilung.",
  patent_grants:
    "Erteilte Patente (EPO Kind-Codes B, B1, B2, B3, B4, B8, B9). Positiv geprüft und gewährt.",
  projects: "EU-Forschungsprojekte aus der CORDIS-Datenbank.",
  publications:
    "Wissenschaftliche Publikationen aus CORDIS-Projektdaten.",
};
