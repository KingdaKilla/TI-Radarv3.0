# Agent B · Analyse · post-quantum cryptography

**Rolle:** Analysierer (2. Welle) · **Input:** `raw3_pqc.json` · **Datum:** 2026-04-14

Header-Kurzfassung laut Dashboard:
`8 Patente · 33 EU-Projekte · 0 Publikationen · Phase: Entstehung Stagnation · Wettbewerbsintensiver Markt · €99M Förderung · Moderater Forschungsimpact`

---

## Befunde nach Severity

### CRITICAL

#### C1 · Header „0 Publikationen" vs. UC7 „100 Publikationen"
- **Quelle:** Header (`0 Publikationen`) vs. UC7 Forschungsimpact (`100 Publikationen 53.9 Zitate/Pub. 15 Institutionen`) vs. UC13 (`48.5 Pub/Projekt`).
- **Snippet Header:** „8 Patente 33 EU-Projekte **0 Publikationen**".
- **Snippet UC7:** „Forschungsimpact Info **100 Publikationen** 53.9 Zitate/Pub."
- **Widerspruch:** Das Executive-Summary behauptet null Publikationen, die Detail-Panels zeigen 100 (UC7) bzw. implizit ~1.601 (UC13: 48,5 × 33 Projekte).
- **Fix-Hypothese:** Header-Aggregator zieht aus falscher Quelle (nur Patent-bezogene Pubs/Scopus-Shortcut), während UC7/UC13 aus CORDIS-linked-Publikationen kommen. Header muss die gleiche Quelle nutzen oder das Label präzisieren („0 Patent-Publikationen").

#### C2 · UC13-Rechnung sprengt UC7 um Faktor 16
- **Quelle:** UC13 (`48.5 Pub/Projekt`) · Förderung (`33 Projekte`) · UC7 (`100 Publikationen`).
- **Rechnung:** 48,5 × 33 = **1.600,5 Publikationen** — UC7 liefert aber nur 100.
- **Widerspruch:** Pub/Projekt-Ratio passt zu keiner der gemeldeten Gesamtsummen (weder Header 0 noch UC7 100).
- **Fix-Hypothese:** „Pub/Projekt" mischt alle CORDIS-Linked-Publikationen (ohne DOI-Filter, inkl. Konferenz/Preprint), UC7 filtert nur peer-reviewed + mit Zitationen. Definition der beiden Metriken vereinheitlichen oder Nenner offenlegen.

#### C3 · R² = 0,000 bei „Konfidenz: 80 %" — Reifephase nicht belastbar
- **Quelle:** UC2 S-Kurve (`Phase: Entstehung · R² = 0.000 · Konfidenz: 80%`).
- **Widerspruch:** Ein Sigmoid-Fit mit R² = 0 bedeutet keinerlei Modell-Erklärung. Eine Konfidenz von 80 % dazu auszugeben ist in sich widersprüchlich; bei 8 Patenten ist die Datenbasis ohnehin zu dünn.
- **Fix-Hypothese:** Fit bei n < 15 oder R² < 0,3 komplett unterdrücken, stattdessen „nicht fittbar" anzeigen. Konfidenz-Score darf R² nicht ignorieren.

#### C4 · Header „Wettbewerbsintensiver Markt" vs. UC3 „Niedrige Konzentration"
- **Quelle:** Header (`Wettbewerbsintensiver Markt`) vs. UC3 (`Niedrige Konzentration`).
- **Widerspruch:** Header-Narrativ und UC3-Einordnung sind semantisch entgegengesetzt. Niedriger HHI = fragmentierter Markt ≠ intensiver Wettbewerb im Sinne der Header-Semantik, die typischerweise Konzentration kommuniziert.
- **Fix-Hypothese:** Entweder Header-Label an HHI-Schwellen koppeln („fragmentierter Markt") oder klar trennen zwischen „viele Akteure" und „starker Wettbewerb".

### MAJOR

#### M1 · Projekt-Zählerei inkonsistent (33 vs. 35)
- **Quelle:** Header (`33 EU-Projekte`) · UC4 Förderung (`33 Projekte`) · UC10 EuroSciVoc (`35 Projekte`).
- **Widerspruch:** UC10 meldet 2 Projekte mehr als Header/UC4. Die drei Panels müssten denselben Nenner haben.
- **Fix-Hypothese:** UC10 zählt auch Projekte ohne Fördersumme/mit nachträglicher EuroSciVoc-Zuordnung. Vereinheitlichen oder Differenz im Footer dokumentieren.

#### M2 · EuroSciVoc „0 Felder" trotz 7 angezeigter Disziplinen
- **Quelle:** UC10 (`Info 0 Felder 35 Projekte`), aber Liste: `cryptography · quantum computers · software · internet of things · internet · geometry · e-commerce`.
- **Widerspruch:** KPI „0 Felder" steht im harten Widerspruch zu den angezeigten 7 Top-Labels und einem Shannon-Index von 3,12 (≠ 0 nur möglich bei > 1 Feld).
- **Fix-Hypothese:** Aggregationsbug — KPI-Zähler liest vermutlich `distinct level_1`, Chart rendert `level_3`. Zählung an die angezeigte Granularität koppeln.

#### M3 · Taxonomie-Plausibilität: „e-commerce" und „geometry" für PQC
- **Quelle:** UC10 Top-Felder `cryptography · quantum computers · software · internet of things · internet · geometry · e-commerce`.
- **Widerspruch:** „e-commerce", „internet", „geometry" sind für post-quantum cryptography inhaltlich fragwürdig; vermutet werden falsch propagierte Parent-Classes aus dem EuroSciVoc-Baum.
- **Fix-Hypothese:** Ranking nach Term-Frequenz statt Pfad-Expansion; Level-2/Level-3-Terme bevorzugen.

#### M4 · Akteurs-Typ-Dominanz „KMU" bei nur 8 Patenten / 33 Projekten
- **Quelle:** UC11 (`172 Akteure · Dominiert: KMU / Unternehmen`) vs. UC3-Top-Anmelder (fast ausschließlich Universitäten, Forschungszentren, staatliche Agenturen: „UNIVERSIDAD CARLOS…", „FRAUNHOFER…", „NARODNI URAD…", „UNIVERSITE DU LUX…").
- **Widerspruch:** Top-8 in UC3 sind mehrheitlich PRC/HES/PUB, nicht KMU; Dominanz-Label kollidiert mit sichtbarer Akteursverteilung.
- **Fix-Hypothese:** Gewichtung nach Count vs. Aktivität klären; Label „Dominiert" verlangt eindeutige Mehrheitsregel (> 50 % oder klarer Spitzenreiter).

#### M5 · Dynamik „Schrumpfend -67 netto" vs. UC11 „172 Akteure"
- **Quelle:** UC8 (`17 Akteure · Schrumpfend (-67 netto)`) vs. UC11 (`172 Akteure`).
- **Widerspruch:** Gleiches Thema, ungleicher Nenner: UC8 zählt 17, UC11 172 Akteure. Ein Netto-Saldo von −67 bei Bestand 17 ist arithmetisch nur möglich, wenn verschiedene Populationen gemeinsam abgebildet werden.
- **Fix-Hypothese:** UC8 zählt wahrscheinlich nur „zuletzt aktive Patent-Applicants", UC11 alle Projekt- + Patent-Akteure. Definitionen vereinheitlichen oder in Tooltip sauber trennen.

#### M6 · UC12 Quote passt nicht zu gezeigten Zahlen
- **Quelle:** UC12 (`Quote: 78.3% · 83 Anmeldungen · 65 Erteilungen`).
- **Rechnung:** 65 / 83 = **78,3 %** (stimmt). Aber: Header meldet `8 Patente`, UC12 arbeitet mit 83 Anmeldungen — Faktor 10 Abweichung.
- **Widerspruch:** Entweder sind „8 Patente" im Header eine andere Definition (z. B. nur granted in DE/EU priority) oder UC12 zählt Familien-/Equivalent-Filings mit. So oder so: Header-KPI und UC12-Universum klaffen um eine Größenordnung auseinander.
- **Fix-Hypothese:** Header-Zahl klar als „Patentfamilien" / UC12 als „Einzelanmeldungen (EPO/USPTO/WIPO)" deklarieren; ansonsten auf eine Zählweise vereinheitlichen.

#### M7 · CAGR-Patente +50 % bei gleichzeitig „Entstehung Stagnation"
- **Quelle:** Header-Phase (`Entstehung Stagnation`) vs. UC1 (`Patente CAGR: 50.0%`, `Projekte CAGR: 18.9%`).
- **Widerspruch:** Zweigliedriges Phase-Label „Entstehung + Stagnation" kombiniert zwei gegensätzliche Zustände; zugleich 50 % p.a. Patentwachstum → de facto Wachstums­phase, nicht Stagnation.
- **Fix-Hypothese:** Zweitlabel („Stagnation") ist Artefakt einer Fallback-Regel (R² = 0 → „Stagnation" angehängt). Bei R² = 0 nur primäres Label zeigen und CAGR als Plausibilitätscheck einziehen.

### MINOR

#### m1 · Unvollständige Jahre bis 2026 — Warnhinweis uneinheitlich
- **Quelle:** UC1, UC2, UC8, UC12 zeigen Achsen bis 2026 und tragen `Daten ggf. unvollständig`; UC7, UC13 zeigen Achsen bis 2024/2025 **ohne** Warnhinweis.
- **Widerspruch:** Einheit der Warnkennzeichnung fehlt; UC13 zeigt bemerkenswert die Jahreslücke 2024 → 2025 (2024 fehlt in der Achsenliste `2016 2017 … 2023 2025`).
- **Fix-Hypothese:** Warnhinweis global auf allen Panels mit Enddatum ≥ aktuelles Jahr anzeigen; fehlende Jahre im Achsenmodell schließen.

#### m2 · UC7 Jahresliste überspringt 2018
- **Quelle:** UC7 Jahresachse `2016 2017 2019 2020 2021 2022 2023 2024 2025 2026`.
- **Widerspruch:** 2018 fehlt. Bei einer kontinuierlichen Zeitachse sollten Lücken mit 0 aufgefüllt statt ausgelassen werden.
- **Fix-Hypothese:** X-Achse gegen vollständigen Jahresbereich rendern (dense axis), nicht gegen `DISTINCT year`.

#### m3 · UC13 Jahresachse springt von 2023 direkt auf 2025
- **Quelle:** UC13 (`2016 2017 2018 2019 2020 2021 2022 2023 2025`).
- **Widerspruch:** 2024 fehlt, 2026 fehlt; Inkonsistenz zum Zitations-Panel, das 2024 zeigt.
- **Fix-Hypothese:** Identische Achsenquelle wie UC7 verwenden.

#### m4 · Förderung rundet €98,6M → €99M inkonsistent
- **Quelle:** Header (`€99M Förderung`) vs. UC4 (`Gesamt: 98.6 Mio. EUR`).
- **Widerspruch:** Rundung im Header erzeugt Differenz von 0,4 Mio. €.
- **Fix-Hypothese:** Entweder überall eine Nachkommastelle oder konsistent runden (gleicher Rundungsmodus in allen Formatierern).

#### m5 · UC5 „10 CPC-Klassen" vs. UC9 „21 CPC-Klassen"
- **Quelle:** UC5 (`10 CPC-Klassen · Ø Jaccard: 0.122`) vs. UC9 (`2 Cluster · 6 Akteure · 21 CPC-Klassen`).
- **Widerspruch:** Zwei verschiedene CPC-Populationen für dieselbe Tech.
- **Fix-Hypothese:** Vermutlich Top-10-Filter in UC5 vs. Gesamtmenge in UC9; als „Top-N" kennzeichnen.

### INFO

#### i1 · Prozent-Summen im gültigen Bereich
- UC12-Quote 78,3 %, DOI-Anteil 35 %, Konfidenz 80 % — alle in [0,100]. Keine Prozent-Verletzung feststellbar.

#### i2 · Datenbasis generell klein
- 8 Patente · 33 Projekte · 100 Publikationen · 17–172 Akteure. Selbst bei technisch korrekter Berechnung sind Aussagen wie „Ø Jaccard 0,122", „Shannon 3,12", „HHI niedrig" auf dieser Basis nur explorativ.

---

## Kurz-Synthese

Die Panels liefern Daten, aber der **Header-Aggregator** ist an mehreren Stellen entkoppelt: Publikationen (C1), Wettbewerbs-Narrativ (C4), Phase-Label (M7), Projekt-Zählerei (M1), Förderrundung (m4). Dazu kommen **zwei handfeste Rechen-/Modell­fehler** (C2 UC13-Ratio, C3 R² = 0 mit 80 % Konfidenz) und ein **Taxonomie-Qualitätsproblem** (M2/M3). Für eine Investitions­entscheidung auf Basis dieses Dashboards ist die Kombination aus R² = 0 und gleichzeitiger 80-%-Konfidenz­ausgabe besonders gefährlich.
