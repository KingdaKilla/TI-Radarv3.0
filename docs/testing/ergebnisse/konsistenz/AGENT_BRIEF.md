# Agent-Briefing (2. Welle) für Konsistenz-Audit TI-Radar v3

Du bist einer von **18 parallel laufenden Agenten** (3 Rollen × 6 Technologien). Deine Rolle und deine Input-Datei werden dir im Prompt genannt. Lies diese Briefing-Datei komplett, dann mach dein Spezial-Werk.

## Situation

TI-Radar v3 analysiert Technologien in 13 Use Cases, gruppiert in 4 UI-Cluster. Ich habe am Live-System `https://app.drakain.de` pro Technologie einen vollen Dashboard-Durchlauf gemacht. Die ersten Rohdaten (`raw_*.json` / `raw2_*.json`) waren buggy — deren Agent-Auswertung liegt archiviert in `agents_erste_welle/`, deren Header-Befunde bleiben gültig, aber die Panel-Inhalte fehlten.

**Deine Input-Datei ist jetzt `raw3_<tech>.json`** — diese enthält **echte Panel-Inhalte** (observedActive + panelText), extrahiert via `lastIndexOf(tabName)` und anschließend 1800 Zeichen Kontext.

### Input-Struktur (`raw3_<tech>.json`)

```json
{
  "tech": "…",
  "header": "Executive-Summary-Kopfzeile (ca. 400 Zeichen, enthält Header-KPIs + Beginn der Cluster-Info)",
  "panels": {
    "Aktivitätstrends":      { "observedActive": "Aktivitätstrends",      "panelText": "..." },
    "S-Kurve & Reife":       { "observedActive": "S-Kurve & Reife",       "panelText": "..." },
    "Technologiekonvergenz": { "observedActive": "Technologiekonvergenz", "panelText": "..." },
    "Wettbewerb & HHI":      { "observedActive": "Wettbewerb & HHI",      "panelText": "..." },
    "Dynamik & Persistenz":  { "observedActive": "Dynamik & Persistenz",  "panelText": "..." },
    "Akteurs-Typen":         { "observedActive": "Akteurs-Typen",         "panelText": "..." },
    "Förderung":             { "observedActive": "Förderung",             "panelText": "..." },
    "Forschungsimpact":      { "observedActive": "Forschungsimpact",      "panelText": "..." },
    "Publikationen":         { "observedActive": "Publikationen",         "panelText": "..." },
    "Geographie":            { "observedActive": "Geographie",            "panelText": "..." },
    "Tech-Cluster":          { "observedActive": "Tech-Cluster",          "panelText": "..." },
    "EuroSciVoc":            { "observedActive": "EuroSciVoc",            "panelText": "..." },
    "Patenterteilung":       { "observedActive": "Patenterteilung",       "panelText": "..." }
  }
}
```

`panelText` enthält: Tab-Leiste (benachbarte Tabs), dann den aktiven UC-Titel, dann die **Panel-Nutzdaten** (KPIs, Chart-Labels, Jahresachsen, Listen), am Ende `Nachvollziehbarkeit X Quellen | Ys`.

### Zuordnung Tab → Use Case (für Interpretation)

| Tab | UC | Versprechen |
|---|---|---|
| Aktivitätstrends | UC1 | Patent/Projekt/Publikation-Trend + CAGR |
| S-Kurve & Reife | UC2 | Reifephase per Sigmoid-Fit (R², Wendepunkt, Konfidenz) |
| Technologiekonvergenz | UC5 | CPC-Kookkurrenz + Whitespace-Lücken |
| Wettbewerb & HHI | UC3 | Marktkonzentration (HHI) + Top-Anmelder |
| Dynamik & Persistenz | UC8 | Akteursdynamik (Neue / Persistente / Ausgeschiedene) |
| Akteurs-Typen | UC11 | Breakdown HES/PRC/PUB/KMU |
| Förderung | UC4 | EU-Fördervolumen (CORDIS) + Instrumenten-Verteilung |
| Forschungsimpact | UC7 | h-Index / Zitationen / Top-Institutionen |
| Publikationen | UC13 | Pub/Projekt + DOI-Anteil (CORDIS Linked) |
| Geographie | UC6 | Länderverteilung + Kollaborationsmuster |
| Tech-Cluster | UC9 | 5-dim Profil (Aktivität/Vielfalt/Dichte/Kohärenz/Wachstum) |
| EuroSciVoc | UC10 | Wissenschaftsdisziplin-Taxonomie |
| Patenterteilung | UC12 | Grant-Rate + Time-to-Grant |

## Bekannte Auffälligkeiten (aus erster Welle, global für alle Techs)

- **Header-vs-Panel-Mismatch**: „0 Publikationen" im Header obwohl UC7 konkrete Publikationszahlen + Zitationen zeigt; „311.5K Publikationen" im Header (mRNA) vs. nur ~200 in UC7.
- **Doppel-Phase**: Header kombiniert mehrere Phasen (z. B. „Reife + Rückläufige Entwicklung", „Entstehung + Stagnation") — UC2 selbst nennt nur eine einzige Phase.
- **Wettbewerbs-Widerspruch**: Header „Wettbewerbsintensiver Markt" vs. UC3 „Niedrige Konzentration".
- **CAGR vs. Phase**: Header-Phase „Reife Stagnation" bei CAGR von +35 % (Solid State Battery) — passt nicht zusammen.
- **Unvollständige Jahre**: S-Kurve und Aktivitätstrends zeigen Jahre **bis 2026** (heute: 2026-04-14), obwohl 2025 und 2026 unvollständig sind. Der Warnhinweis `"Daten ggf. unvollständig"` ist in einigen, aber nicht allen Panels sichtbar.
- **Inkonsistente Projekt-Zahlen**: Header 307 vs. UC10 387 (mRNA); Header 113 vs. UC10 106 (Solid State) — Projekte-Kopfzahl stimmt nicht mit EuroSciVoc-Projektzahl überein.
- **EuroSciVoc-Fehldaten**: „law" als dominantes Feld für `solid state battery` — inhaltlich nicht plausibel.
- **Jahresachsen-Inkonsistenz**: UC7/UC13 zeigen 2016–2024, UC1/UC2/UC8/UC12 zeigen 2016–2026. Unterschiedliche Endjahre im selben Dashboard.

Prüfe, ob sich **diese** (und ähnliche) Phänomene auch in deinem Tech-Dump zeigen.

## Deine Rolle

### Rolle A · Dokumentierer
- **Ziel:** Strukturiertes, nüchternes Protokoll dessen, was das Dashboard für diese Tech liefert.
- **Methode:** Extrahiere pro UC die beobachtbaren Werte/Labels.
- **Output:** `docs/testing/ergebnisse/konsistenz/agents/<tech>_A_doku.md`
  - Header-Zeile mit Kern-KPIs (Patente/Projekte/Publikationen/Phase/Förderung/Impact-Label)
  - Tabelle: UC · Kern-Metriken (CAGR, HHI, R², Wendepunkt, Phase, Länder-Top, h-Index, Pub/Projekt, Quote, CPCs, …) · Beobachtete Jahresachse
  - Liste Panels mit Warnhinweisen (`"Daten ggf. unvollständig"`)

### Rolle B · Analysierer
- **Ziel:** Harte numerische Inkonsistenzen finden, **Severity-gewichtet**.
- **Methode:** Prüfe
  1. **Kopf-vs-Detail-Abgleich**: Header-KPI X stimmt mit UC-Panel-KPI Y überein? (Publikationen, Projekte, Förderung, Phase)
  2. **Wettbewerbs-Widerspruch**: Header vs. UC3.
  3. **CAGR vs. Phase-Konsistenz**: hohe positive CAGR + Phase „Reife/Stagnation" = widersprüchlich.
  4. **Prozent-Summen**: Akteurs-Typen, EU-Share, Grant-Rate ∈ [0, 100].
  5. **Unvollständige Jahre**: Welche Jahresachse reicht bis wohin? Wird 2025 oder 2026 in Fit/CAGR einbezogen? Ist Warnhinweis vorhanden?
  6. **R²-Confidence**: R² < 0,5 → Phase-Label unzuverlässig. Ist R² auf so niedriger Datenbasis (z. B. 8 Patente) überhaupt valide?
  7. **Projekt-Zählerei über UCs**: Header-Projekte vs. UC4-Projekte vs. UC10-Projekte. Müssten gleich sein.
  8. **UC10-Taxonomie-Plausibilität**: Ist das zugeordnete Feld inhaltlich sinnvoll?
  9. **UC12-Zählerei**: Grant-Rate = Erteilungen/Anmeldungen. Nachrechnen.
  10. **UC13-Rechnung**: Pub/Projekt × Projekte = Gesamt-Publikationen — stimmt das mit Header- oder UC7-Wert?
- **Output:** `docs/testing/ergebnisse/konsistenz/agents/<tech>_B_analyse.md` als Liste von Befunden je **Severity (Critical / Major / Minor / Info)**. Jeder Befund: ID, Titel, Quelle (welches Panel / Header), Original-Text-Snippet (kurz), Widerspruch in einem Satz, Fix-Hypothese.

### Rolle C · Interpreter
- **Ziel:** Hält jeder UC sein Versprechen für **diese Tech**?
- **Methode:** Pro UC → (a) Versprechen (siehe Tabelle oben), (b) tatsächliche Lieferung laut Panel, (c) Gap-Urteil.
- **Bewertung je UC** mit Ampel:
  - 🟢 **Versprechen erfüllt** (konkrete Zahlen, interpretierbar, stimmig)
  - 🟡 **Teilweise** (Daten da aber dürftig/missverständlich/auf zu kleiner Basis)
  - 🔴 **Nicht erfüllt** (Panel leer, Werte widerspruchs­behaftet, versprochene Dimension fehlt)
- **Kernfrage:** Würde ein Budget-Entscheider bei dieser Tech dem Panel trauen?
- **Output:** `docs/testing/ergebnisse/konsistenz/agents/<tech>_C_interpret.md` mit Tabelle (UC · Versprechen · Liefert · Ampel · Begründung) und Kurzzusammenfassung „Für welche Entscheidungen brauchbar, für welche gefährlich?".

## Output-Regeln

- **Nur** deine Markdown-Datei schreiben (`Write` Tool).
- Maximal 1× `Read` pro Input-Datei + 1× `Read` des Briefings. Keine Extra-Recherche.
- **Deutsch**, 2–3 A4-Seiten.
- **Rückgabe in deiner Nachricht**: 2-Satz-Executive-Summary + 1 Zeile „Kritischster Befund:" (für Konsolidierung).
