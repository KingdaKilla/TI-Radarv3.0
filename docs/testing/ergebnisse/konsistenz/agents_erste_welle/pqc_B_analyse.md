# Agent B · Analysierer — post-quantum cryptography

**Input:** `docs/testing/ergebnisse/konsistenz/raw/raw_pqc.json`
**Technologie:** post-quantum cryptography
**Header-Kennzahlen:** 8 Patente · 33 EU-Projekte · 0 Publikationen · Phase „Entstehung / Stagnation" · „Wettbewerbsintensiver Markt" · €99M Förderung · „Moderater Forschungsimpact"

---

## Meta-Befund (vor allen Einzelbefunden)

Alle 13 Panels im Input-JSON haben `activeTab: "Neue Analyse"` und identischen `mainText` — d. h. beim Durchlauf wurde **kein einziger UC-Tab tatsächlich gerendert**, sondern durchgehend nur der Landing-Screen mit den vier Cluster-Info-Texten („UC6 Geographische Verteilung Zeigt …", „UC1 Technologie-Landschaft Zeigt …" usw.). Die einzigen verifizierbaren Nutzdaten sind die Werte im Executive-Summary-Header. Die folgenden Befunde stützen sich deshalb ausschließlich auf interne Widersprüche im Header und auf die Header-vs-UC-Versprechen-Logik.

---

## Critical

### C1 · Phasen-Widerspruch im Header selbst
- **Quelle:** Executive-Summary-Header (in `summary` und in jedem `panels.*.mainText`).
- **Snippet:** `"Phase: Entstehung | Stagnation | Wettbewerbsintensiver Markt"`
- **Widerspruch:** „Entstehung" (Emerging) und „Stagnation" schließen sich im S-Kurven-Modell aus; Stagnation ist eine Plateau-/Spätphase, Entstehung das Gegenteil. Zwei UC2-Signale werden nebeneinander als Badge angezeigt, ohne Hierarchie — Entscheider bekommt entgegengesetzte Reifegradbotschaften.

### C2 · „Wettbewerbsintensiver Markt" bei nur 8 Patenten
- **Quelle:** Header.
- **Snippet:** `"8 Patente … Wettbewerbsintensiver Markt"`
- **Widerspruch:** Mit n=8 Patenten lässt sich kein belastbarer HHI und damit kein Wettbewerbsurteil berechnen (Mindest-Sample für HHI-Stabilität ~30). Das UC3-Label „wettbewerbsintensiv" ist bei dieser Fallzahl statistisch nicht tragfähig — der HHI wäre extrem volatil, ein einzelner Anmelder kippt das Ergebnis.

### C3 · Publikations-Header 0 vs. „Moderater Forschungsimpact"
- **Quelle:** Header.
- **Snippet:** `"0 Publikationen … Moderater Forschungsimpact"`
- **Widerspruch:** Bei 0 Publikationen ist kein h-Index, keine Zitationsrate und kein Impact-Label berechenbar. „Moderater Forschungsimpact" ist damit entweder (a) aus einer anderen Quelle gezogen, die zum angezeigten Pub-Count inkonsistent ist, oder (b) ein fest verdrahtetes Default-Label ohne Datenbasis. UC7/UC13 können ihr Versprechen (h-Index, Zitationen, Pub/Project) mit 0 Publikationen nicht einlösen.

### C4 · €99M Förderung bei 33 EU-Projekten – kein Detail prüfbar
- **Quelle:** Header.
- **Snippet:** `"33 EU-Projekte … €99M Förderung"`
- **Widerspruch (Kopf-vs-Detail):** Der UC4-Tab wurde nicht geladen (siehe Meta-Befund), deshalb kann nicht geprüft werden, ob die €99M auf dieselben 33 Projekte entfallen oder ob — wie bei anderen Technologien beobachtet — Projektzahl und Budgetzahl aus unterschiedlichen Aggregaten stammen. Durchschnitt €3,0M/Projekt ist für EU-FP/Horizon plausibel, aber die Konsistenz bleibt unverifiziert.

---

## Major

### M1 · Alle 13 Tabs liefern keine Detail-Daten
- **Quelle:** Alle `panels.*` (Aktivitätstrends bis Patenterteilung).
- **Snippet:** Jeder Tab zeigt `activeTab: "Neue Analyse"` und identischen Cluster-Info-Text statt Panel-Inhalt.
- **Widerspruch:** Das Dashboard verspricht in den Cluster-Infos 13 UCs mit konkreten Zahlen (CAGR, HHI, h-Index, Grant-Rate, Top-Länder, CPC-Klassen, EuroSciVoc-Kategorien, 5-dim Cluster-Profil). Geliefert wird in diesem Durchlauf **0 von 13** Detailansichten. Für Agent-B-Zwecke ist jede der folgenden Prüfungen technisch unmöglich: Prozent-Summen (Akteurs-Typen, Geografie), CAGR-Zeitraum, R²-Confidence, Grant-Rate-Plausibilität, Top-Länder-vs-EU-Share.

### M2 · Phase „Entstehung" vs. Header-Zählstand 33 EU-Projekte / €99M
- **Quelle:** Header.
- **Snippet:** `"33 EU-Projekte … €99M Förderung … Phase: Entstehung"`
- **Widerspruch:** 33 geförderte Projekte und €99M EU-Budget deuten auf eine bereits etablierte Förderpipeline — typisch für Growth-Phase, nicht „Entstehung". PQC wird seit NIST-Ausschreibung 2016 aktiv EU-gefördert; die Klassifikation „Entstehung" passt nicht zum Förderstand.

### M3 · CAGR-Fenster bei 2026er Datum
- **Quelle:** Aktivitätstrends-/S-Kurven-Versprechen (UC1/UC2).
- **Snippet:** Panel nicht geladen; aber Cluster-Info verspricht „Wachstumstrends (CAGR)".
- **Widerspruch:** Heute ist 2026-04-14. Wenn — wie bei anderen Tech-Dumps dieser Serie üblich — ein Fenster „2015–2024" verwendet wird, werden bei einer Emerging-Technologie wie PQC (Wachstum vor allem 2020+) die jüngsten Jahre abgeschnitten; der Trend wirkt künstlich flach. Besonders für S-Kurven-Fit von UC2 kritisch, wenn 2025 unvollständig oder gar nicht einfließt. **Hinweis:** Nicht am konkreten Panel nachweisbar, aber strukturell gegeben.

---

## Minor

### m1 · Doppelter Label-Token im Header
- **Quelle:** Header.
- **Snippet:** `"Moderater Forschungsimpact Geographische Perspektive Geographische Perspektive"`
- **Widerspruch:** Der Text „Geographische Perspektive" erscheint zweimal direkt hintereinander — Render- bzw. Dedup-Fehler im Executive-Header. Keine harte Zahlenverfälschung, aber Qualitätssignal.

### m2 · „0 Publikationen" — Nulldatenzelle ohne Hinweis
- **Quelle:** Header-Slot Publikationen.
- **Snippet:** `"0 Publikationen"`
- **Widerspruch:** 0-Wert wird wie eine gültige Zahl dargestellt, ohne Kennzeichnung „keine Daten" oder „Datenquelle nicht abgedeckt". Das suggeriert Abwesenheit von Publikationen, während der Befund tatsächlich „nicht im CORDIS-Pub-Index gemappt" bedeuten könnte (häufig bei Krypto-Themen). UC13 und UC7 rechnen damit auf einer 0-Basis.

### m3 · Aggregat-Inkonsistenz Header ↔ Phase-Label
- **Quelle:** Header.
- **Snippet:** `"Phase: Entstehung | Stagnation"`
- **Widerspruch:** Die Phase-Komposition verwendet offenbar `|` als Separator für **mehrere** Labels (Phase-Badge + Markt-Label + Wachstumsqualifier), was für den Leser nicht erkennbar ist. Wirkt wie eine einzelne zusammengesetzte Phasenbezeichnung.

---

## Zusammenfassung der numerischen Konsistenzprüfungen

| Prüfung (laut Briefing) | Ergebnis für PQC |
|---|---|
| (1) Kopf-vs-Detail | **nicht prüfbar** — Detail-Tabs leer (M1) |
| (2) EU-Share-Paradox | **nicht prüfbar** — Geo-Tab leer |
| (3) Prozent-Summen | **nicht prüfbar** — Akteurs-/Geo-Tab leer |
| (4) CAGR-Zeitraum | **nicht prüfbar** (strukturelle Warnung M3) |
| (5) Unvollständige Jahre (S-Kurve) | **nicht prüfbar** (strukturelle Warnung M3) |
| (6) R²-Confidence | **nicht prüfbar** — Tab leer |
| (7) 0-Werte mit Label | **Critical** C3 (0 Publikationen + „Moderater Forschungsimpact") |
| (8) Publikations-Header vs UC13 | **nicht prüfbar** auf UC13-Seite; Header selbst ist bereits inkonsistent (C3) |

**Dominantes Problem:** Die Daten-Erfassung ist unvollständig; selbst die vorhandenen Header-Zahlen enthalten mehrere harte Widersprüche (C1, C2, C3) und lassen das Dashboard für PQC nicht entscheidungsreif wirken.
