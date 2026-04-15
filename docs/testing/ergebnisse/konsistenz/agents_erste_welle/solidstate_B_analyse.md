# Konsistenz-Audit · Solid State Battery · Rolle B (Analysierer)

**Technologie:** solid state battery
**Datum:** 2026-04-14
**Input:** `docs/testing/ergebnisse/konsistenz/raw/raw_solidstate.json`

---

## Meta-Befund (Datenbasis)

> **Kritisch für die gesamte Analyse:** In der Input-JSON ist `activeTab` in **allen 13 Panels** durchgehend `"Neue Analyse"`, und `mainText` ist in allen 13 Panels **wortidentisch** — es enthält ausschließlich die Executive-Summary-Kopfzeile plus die generischen Cluster-Info-Texte (`Dieser Analysebereich umfasst: UC6 … UC9 … UC10 …`). **Es wurde also kein einziger UC-Detail-Panel tatsächlich aktiviert bzw. dessen Nutzdaten erfasst.** Damit sind harte Kopf-vs-Detail-Prüfungen (Header-Patente vs. UC1-Chart, Header-Förderung vs. UC4-Breakdown, HHI-Wert, CAGR-Wert, R², Top-Länder, Akteurs-Typen-Prozente, Grant-Rate, Zeiträume) **technisch nicht durchführbar** — die Rohdaten enthalten sie schlicht nicht.
>
> Alle weiter unten gelisteten Befunde beruhen daher ausschließlich auf der **Executive-Summary-Kopfzeile**, die in jedem Panel wiederholt wird:
>
> `"SOLID STATE BATTERY … 358 Patente | 113 EU-Projekte | 0 Publikationen | Phase: Reife | Stagnation | Wettbewerbsintensiver Markt | €297M Förderung | Sehr hoher Forschungsimpact"`

---

## Befunde

### Critical

#### C1 · Publikations-Widerspruch Kopf vs. Label "Sehr hoher Forschungsimpact"
- **Quelle:** Executive-Summary-Header (in allen 13 Panels wiederholt).
- **Snippet:** `358 Patente | 113 EU-Projekte | 0 Publikationen | … | Sehr hoher Forschungsimpact`.
- **Widerspruch:** Der Header weist **0 Publikationen** aus, gleichzeitig vergibt das Label-System aber **"Sehr hoher Forschungsimpact"**. Ein h-Index / Zitationen / Impact-Metriken setzen Publikationen voraus — bei 0 Publikationen ist ein "sehr hoher Forschungsimpact" logisch nicht ableitbar. Entweder ist die Publikationszahl falsch (Datenlücke CORDIS-Join) oder das Impact-Label wird ohne Publikationsgrundlage generiert.

#### C2 · UC13 Publikations-Impact strukturell unerfüllbar
- **Quelle:** Header + Tab "Publikationen".
- **Snippet:** `0 Publikationen` (Header) — Panel-Detail fehlt vollständig (s. Meta-Befund).
- **Widerspruch:** UC13 verspricht laut Cluster-Info "CORDIS-Publikationen × Projekte, Publikationseffizienz (Pub/Project)". Mit 0 Publikationen und 113 EU-Projekten wäre die Effizienz 0 Pub/Project — die Aussage des Panels ist damit entweder leer oder trivial-falsch. Bei einer reifen, hochgeförderten Technologie (€297M) sind 0 CORDIS-Publikationen hochgradig unplausibel und deuten auf ein ETL-Join-Problem (CORDIS-Publikationstabelle ↔ Technologie-Mapping).

### Major

#### M1 · Phase-Widerspruch "Reife" ∧ "Stagnation" bei verfügbaren 358 Patenten
- **Quelle:** Header (alle Panels).
- **Snippet:** `Phase: Reife | Stagnation`.
- **Widerspruch:** "Reife" und "Stagnation" sind zwei separate Phase-Kategorien im UC2-Schema (Emerging/Growth/Mature/Declining bzw. Stagnation). Der Header führt beide gleichzeitig — unklar, welche die kanonische Label-Zuordnung ist. Ohne den S-Kurven-R²-Wert (nicht im Input) kann nicht beurteilt werden, ob der Fit überhaupt belastbar ist. Für Solid State Battery ist "Reife/Stagnation" zusätzlich fachlich fragwürdig: die Technologie gilt in der Industrie als Pre-Commercial / Growth-Phase (Samsung SDI, Toyota, QuantumScape etc. sind erst in Pilotproduktion).

#### M2 · Unvollständige Jahre 2025/2026 potenziell in Reife-Klassifikation
- **Quelle:** Header — "Phase: Reife | Stagnation".
- **Snippet:** kein Zeitraum im Header sichtbar (Panel-Detail fehlt).
- **Widerspruch:** Heutiges Datum ist **2026-04-14**. Ob die S-Kurve Jahre 2024/2025/2026 einbezieht, ist aus dem Input nicht ersichtlich. Wenn ja — Patentdaten haben typisch 18 Monate Publikationslag, 2025/2026 sind quasi-leer und verzerren jede Reife-Klassifikation in Richtung "Stagnation/Decline". Das könnte die "Stagnation"-Nebenlabel-Vergabe direkt erklären und wäre ein systematischer Artefakt.

#### M3 · Header-Kennzahlen vs. UC-Detail nicht verifizierbar (Test-Vorbehalt)
- **Quelle:** alle UC-Panels.
- **Snippet:** `activeTab: "Neue Analyse"` durchgängig.
- **Widerspruch:** Die Testautomatik hat offensichtlich den Klick in die jeweiligen UC-Panels nicht ausgeführt — stattdessen wurde 13× die Landing-/Cluster-Overview-Seite abgegriffen. Header-Konsistenz (358 Patente ↔ UC1-Trend-Summe, 113 Projekte ↔ UC4-Projekt-Count, €297M ↔ UC4-Budget-Summe) ist damit **unprüfbar**. Das ist ein schwerer Test-Fehler, aber kein Dashboard-Bug im engen Sinn — die Konsistenz *könnte* intakt sein, ist aber nicht belegt.

### Minor

#### m1 · Header-Formatierung mit Pipe-Trennern uneindeutig
- **Quelle:** `summary`-Feld.
- **Snippet:** `… | 0 | Publikationen | Phase: Reife | Stagnation | Wettbewerbsintensiver Markt | €297M Förderung | …`
- **Beobachtung:** Im `summary` wird zwischen Zahl und Label jeweils ein Pipe gesetzt (`0 | Publikationen`), während `mainText` kompakt liest (`0 Publikationen`). Zwei Phase-Attribute werden durch Pipe getrennt (`Reife | Stagnation`) — optisch kaum von eigenständigen KPIs unterscheidbar. Das erschwert sowohl automatisches Parsing als auch Nutzerlesung. Kein Datenfehler, aber ein Konsistenzbruch im Ausgabeformat.

#### m2 · Keine Zahlen zur Impact-Aussage
- **Quelle:** Header.
- **Snippet:** `Sehr hoher Forschungsimpact`.
- **Beobachtung:** Qualitatives Label ohne Zahl (h-Index? Zitationsrate? Perzentil?). Nicht prüfbar, nicht vergleichbar. Kombiniert mit C1 (0 Publikationen) ist die Aussage nicht nachvollziehbar.

---

## Zusammenfassung der harten Widersprüche (kurz)

| # | Sev | Widerspruch |
|---|-----|---|
| C1 | Critical | 0 Publikationen vs. "Sehr hoher Forschungsimpact" (Impact ohne Publikationsgrundlage) |
| C2 | Critical | UC13 Pub/Project ist mit 0 Publikationen + 113 Projekten strukturell leer/trivial |
| M1 | Major | Doppelphase "Reife | Stagnation" ohne R²/Zeitraum-Kontext; fachlich fragwürdig für SSB |
| M2 | Major | Wahrscheinliche Verzerrung durch unvollständige Jahre 2025/2026 (Patent-Publikationslag) |
| M3 | Major | Kopf-vs-Detail nicht verifizierbar — Input enthält keine UC-Panel-Nutzdaten (`activeTab: Neue Analyse` überall) |
| m1 | Minor | Pipe-Formatierung des Summary mischt KPI-Werte, Labels und Phase-Nebenattribute |
| m2 | Minor | Impact-Label qualitativ, keine verifizierbare Zahl |

## Nicht prüfbar (wegen fehlender Panel-Daten)

- Kopf-vs-Detail-Integrität: 358 Patente ↔ UC1 Zeitreihe, 113 Projekte ↔ UC4, €297M ↔ UC4-Budget.
- EU-Share-Paradox (UC6): Top-Länder nicht extrahierbar.
- Prozent-Summen: UC11 Akteurs-Typen nicht einsehbar.
- CAGR-Zeitraum (UC1): Zeitraum-Labels fehlen.
- R²-Confidence (UC2): Wert fehlt.
- Grant-Rate-Plausibilität (UC12): nicht einsehbar.
- Top-Länder/Top-Anmelder (UC3/UC6): nicht einsehbar.

> **Empfehlung für den Rerun:** Der Scraper muss pro Panel tatsächlich den Tab klicken und auf Render (Chart/KPI-Bereich sichtbar) warten, nicht nur die Landingpage 13× serialisieren. Erst dann werden die in der Briefing-Liste (Ziffer 1–8) geforderten Konsistenzprüfungen zugänglich.
