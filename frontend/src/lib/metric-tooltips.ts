/* ──────────────────────────────────────────────
 * TI-Radar v2 -- Metric Tooltip Mappings
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
  projects: "EU-Forschungsprojekte aus der CORDIS-Datenbank.",
  publications:
    "Wissenschaftliche Publikationen aus CORDIS-Projektdaten.",
};
