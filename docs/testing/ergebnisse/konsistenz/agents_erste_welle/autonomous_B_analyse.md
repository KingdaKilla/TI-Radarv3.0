# Konsistenz-Analyse · Agent B · Tech: `autonomous driving`

**Input:** `docs/testing/ergebnisse/konsistenz/raw/raw_autonomous.json`
**Rolle:** B (Analysierer — Metriken/Statistik-Inkonsistenzen)
**Audit-Datum:** 2026-04-14

## Header-Werte (Executive Summary)

| Feld | Wert |
|---|---|
| Patente | **734** |
| EU-Projekte | **235** |
| Publikationen | **0** |
| Phase | Reife |
| Trend | Rückläufige Entwicklung |
| Wettbewerb | Wettbewerbsintensiver Markt |
| EU-Förderung | **€755M** |
| Forschungsimpact | Sehr hoher Forschungsimpact |

## Zentrale Vorbemerkung — Datenqualität des Dumps

**Alle 13 Panel-Einträge sind in diesem Dump identisch** und zeigen `activeTab: "Neue Analyse"` (= Cluster-Landingpage, keine Panel-Detailansicht). Der geflattete `mainText` jedes Panels enthält ausschließlich:
1. Executive-Summary-Header (Zahlen oben),
2. Cluster-Info-Beschreibungen (`Dieser Analysebereich umfasst: UC6 … UC9 … UC10 … UC12 …` etc.),
3. den abgeschnittenen Beginn des UC4-Info-Texts (`Forschung & Förderung … UC4 Förderungsanaly`).

**Konsequenz für Rolle B:** Es gibt in diesem Dump **keine Detail-Panel-Zahlen** (keine HHI-Werte, kein CAGR, keine Top-Länder, keine Akteurs-Typ-Prozente, kein h-Index, keine Grant-Rate, keine R²-Werte, keine Jahreszahl-Achsen). Klassische Kopf-vs-Detail-Prüfungen sind daher **nicht durchführbar** — die Detailseite wurde nie geöffnet oder nie gerendert. Das ist der schwerwiegendste Befund selbst.

---

## Befunde nach Severity

### CRITICAL

**C-1 · Dashboard-Dump enthält keine Panel-Nutzdaten (alle Panels)**
- **Quelle:** alle 13 `panels[*].activeTab == "Neue Analyse"`, `mainText` pro Panel identisch.
- **Snippet:** `"activeTab": "Neue Analyse"` (13×) + identischer Body: `"… 734 Patente 235 EU-Projekte 0 Publikationen Phase: Reife … UC6 Geographische Verteilung Zeigt die globale Verteilung … UC4 Förderungsanaly"`.
- **Widerspruch:** Das Dashboard hat für `autonomous driving` beim Durchlauf nie die Detail-Tabs geladen — der Nutzer/Tester sieht statt UC-spezifischer Charts nur den Cluster-Info-Platzhaltertext. Für den Endanwender ist das Radar bei dieser Tech de facto **nicht nutzbar**; eine numerische Konsistenzprüfung zwischen Header und UC-Details ist unmöglich, weil kein einziges UC-Detail geliefert wurde.

**C-2 · Header behauptet „0 Publikationen" bei gleichzeitig „Sehr hoher Forschungsimpact"**
- **Quelle:** Executive-Summary (alle Panels).
- **Snippet:** `"… 0 Publikationen Phase: Reife Rückläufige Entwicklung Wettbewerbsintensiver Markt €755M Förderung Sehr hoher Forschungsimpact …"`.
- **Widerspruch:** Forschungsimpact (UC7) wird klassischerweise über h-Index/Zitationsraten von Publikationen gebildet. „0 Publikationen" + „Sehr hoher Forschungsimpact" ist logisch nicht vereinbar — entweder ist der Publikations-Count falsch (Join/Mapping-Fehler auf CORDIS-Publikationen für diese Tech), oder das Label „Sehr hoher Forschungsimpact" wird ohne Publikationsbasis vergeben (Default-/Fallback-Label). Ohne UC7-Detail ist nicht entscheidbar, welcher Ast falsch ist; beide Varianten sind kritisch.

**C-3 · Header „0 Publikationen" vs. UC13-Versprechen (Publikations-Impact)**
- **Quelle:** Header vs. Tab `Publikationen` (UC13).
- **Snippet:** Header: `"0 Publikationen"`; UC13-Panel liefert keinen Detail-Inhalt (siehe C-1).
- **Widerspruch:** UC13 verspricht laut Cluster-Info-Text „CORDIS-Publikationen × Projekte, Publikationseffizienz (Pub/Project)". Bei 0 Publikationen ist Pub/Project zwingend = 0 für alle 235 EU-Projekte — der gesamte UC13-Tab ist damit entweder leer oder liefert nur Nullen, was das UC-Versprechen faktisch nicht erfüllbar macht. Kombiniert mit C-2 (hoher Impact) deutet das auf **fehlerhafte Publikations-Verknüpfung** (Tech-Zuordnung zu CORDIS-Pubs bricht) hin.

### MAJOR

**M-1 · „Rückläufige Entwicklung" + „Phase: Reife" ohne nachvollziehbare Zeitbasis**
- **Quelle:** Header (alle Panels).
- **Snippet:** `"Phase: Reife Rückläufige Entwicklung"`.
- **Widerspruch:** Heute ist 2026-04-14; UC1/UC2 verwenden typischerweise CAGR-Zeiträume `2015–2024` oder `2015–2025`. 2025 ist zum Audit-Zeitpunkt abgeschlossen, 2026 aber nur zu ~28 % verstrichen. Wenn die „rückläufige Entwicklung" 2025 oder 2026 als Endjahr einschließt (unvollständig), ist sowohl CAGR als auch die S-Kurven-Phase `Reife` potentiell verzerrt (Einbruch am Rand). UC2-Detail (S-Kurve + R²) wäre nötig zur Validierung — fehlt hier komplett (siehe C-1), daher kann die Phase-Zuweisung aus dem Header **nicht belegt** werden.

**M-2 · „235 EU-Projekte" vs. „€755M Förderung" — Plausibilität ohne UC4-Beleg**
- **Quelle:** Header.
- **Snippet:** `"235 EU-Projekte … €755M Förderung"`.
- **Widerspruch:** Durchschnittliches Projektbudget ≈ €3.21M — grundsätzlich plausibel für Horizon/H2020-Projekte, aber nicht durch UC4-Detail validierbar, weil das Förderungs-Panel im Dump kein Detail geliefert hat (siehe C-1). Kein harter Widerspruch, aber ungeprüft — vergleichbar mit einer Kopfzahl ohne Quellennachweis.

**M-3 · Label „Wettbewerbsintensiver Markt" ohne HHI-Wert im Dump**
- **Quelle:** Header vs. Tab `Wettbewerb & HHI` (UC3).
- **Snippet:** `"Wettbewerbsintensiver Markt"`; UC3-Panel: kein Detail (nur Cluster-Info).
- **Widerspruch:** Das Label „wettbewerbsintensiv" impliziert niedrigen HHI (< ~1500). Ohne den HHI-Zahlenwert und ohne Top-Akteure-Liste kann nicht geprüft werden, ob die qualitative Aussage zum quantitativen Kennwert passt. Klassisches Symptom eines Kopf-vs-Detail-Gaps.

### MINOR

**m-1 · Identischer `mainText` über alle 13 Tabs — Scrape/Render-Artefakt**
- **Quelle:** `panels.*.mainText` byte-gleich.
- **Snippet:** identischer 2.5-KB-Block ab `"AUTONOMOUS DRIVING Technologie-Intelligence Analyse 734 …"` bis `"… UC4 Förderungsanaly"`.
- **Widerspruch:** Jede Tab-Umschaltung müsste ein neues Panel laden; hier hat das Dashboard (oder der Scraper) 13× denselben Frame aufgezeichnet. Als statistische Fundgrube für UC-Details nicht brauchbar; dokumentiert, dass der Tab-Wechsel bei dieser Tech ins Leere lief.

**m-2 · Executive-Summary enthält doppelte Segmente**
- **Quelle:** `summary`-Feld.
- **Snippet:** `"… Geographische Perspektive | Geographische Perspektive | Dieser Analysebereich umfasst: …"` (Dopplung).
- **Widerspruch:** Reiner UI-/Rendering-Bug (dupliziertes Label), kein Zahlenwiderspruch; aber Indiz, dass der Header-Generator den Cluster-Namen zweimal einblendet.

---

## Zusammenfassung — was **dieser Dump** prüfen konnte

| Prüfung (laut Briefing) | Durchführbar? | Ergebnis |
|---|---|---|
| 1. Kopf-vs-Detail | Nein | Details fehlen komplett → C-1 |
| 2. EU-Share-Paradox (Top-Länder vs. 0 % EU) | Nein | UC3/UC6 ohne Daten |
| 3. Prozent-Summen (Akteurs-Typen, Geo, Grant-Rate) | Nein | UC11/UC6/UC12 ohne Daten |
| 4. CAGR-Zeitraum / Endjahr | Teilweise | Header-Label „rückläufig" → Zeitraum-Hinweis siehe M-1 |
| 5. Unvollständige Jahre (S-Kurve) | Nein | UC2-Detail fehlt |
| 6. R²-Confidence vs. Phase | Nein | UC2-Detail fehlt; Phase „Reife" ungeprüft |
| 7. 0-Werte mit Label | **Ja** | **C-2** (0 Pub + hoher Impact), **C-3** (0 Pub + UC13-Versprechen) |
| 8. Publikations-Header vs. UC13 | **Ja** | **C-3** (0 Pub → UC13 leer/Null) |

## Gesamturteil Rolle B

Der Dashboard-Durchlauf für `autonomous driving` hat keine Panel-Details geliefert — damit ist das schwerste Konsistenzproblem ein **Render-/Interaktions-Fehler** (C-1), nicht ein reiner Metrikenbruch. Die beiden belegbaren inhaltlichen Widersprüche betreffen die **Publikationsseite**: „0 Publikationen" im Header kollidiert direkt mit „Sehr hoher Forschungsimpact" (C-2) und mit dem UC13-Versprechen einer Pub/Project-Effizienz (C-3). Empfehlung: Publikations-Join (Tech → CORDIS) prüfen; vermutlich bricht das Mapping für diese Tech, weswegen UC7-Label über einen Fallback trotzdem vergeben wird.
