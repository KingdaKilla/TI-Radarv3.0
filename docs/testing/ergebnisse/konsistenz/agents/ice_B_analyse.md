# Analyse-Befunde: internal combustion engine (Agent B, 2. Welle)

**Input:** `raw3_ice.json` · **Tech:** internal combustion engine · **Datum:** 2026-04-14

## Header-Kern-KPIs (Referenz)
- Patente: 10.2K
- EU-Projekte: 48
- Publikationen: **0** (laut Header)
- Phase: **Reife + Rückläufige Entwicklung** (Doppel-Phase)
- Wettbewerb: **Wettbewerbsintensiver Markt**
- Förderung: €160 Mio.
- Impact: Moderater Forschungsimpact

---

## Befunde nach Severity

### CRITICAL

#### C1 – Header „0 Publikationen" vs. UC7 „100 Publikationen"
- **Quelle:** Header (`"0 Publikationen"`) vs. UC7 Forschungsimpact (`"100 Publikationen 71.6 Zitate/Pub."`)
- **Snippet Header:** „10.2K Patente 48 EU-Projekte **0 Publikationen**"
- **Snippet UC7:** „**100 Publikationen** 71.6 Zitate/Pub. 15 Institutionen"
- **Widerspruch:** Header behauptet Null, während UC7 konkrete 100 Publikationen mit Zitations­werten und UC13 sogar 57,7 Pub/Projekt (≈ 2.770 Publikationen hochgerechnet) ausweist.
- **Fix-Hypothese:** Header-Zähler liest eine leere Spalte (z. B. `publications_count` aus Patent-Schema) statt der aus CORDIS-Linked/OpenAIRE geladenen Pub-Daten, die in UC7/UC13 verwendet werden. Quelle für Header-KPI vereinheitlichen.

#### C2 – UC13-Hochrechnung widerspricht UC7 massiv (Faktor 27×)
- **Quelle:** UC13 Publikationen (`"57.7 Pub/Projekt"`) + Förderung (`"48 Projekte"`) vs. UC7 (`"100 Publikationen"`)
- **Snippet:** „57.7 Pub/Projekt DOI: 13%" · „48 Projekte"
- **Rechnung:** 57,7 × 48 ≈ **2.770 Publikationen** – UC7 nennt nur **100**. Abweichung ≈ 27-fach.
- **Widerspruch:** Entweder ist die Pub/Projekt-Rate fehlerhaft (Zähler enthält Nicht-Projekt-Publikationen oder doppelt verknüpfte Publikationen) oder UC7 filtert deutlich strenger. So oder so ist eine der beiden Zahlen unbrauchbar.
- **Fix-Hypothese:** Definitions-Divergenz zwischen UC7 (Top-15-Institutionen-Publikationen) und UC13 (CORDIS-Linked inkl. Co-Publikationen). Kennzahl klar labeln oder vereinheitlichen.

#### C3 – Wettbewerbs-Widerspruch Header vs. UC3
- **Quelle:** Header (`"Wettbewerbsintensiver Markt"`) vs. UC3 (`"Niedrige Konzentration"`)
- **Snippet:** „**Wettbewerbsintensiver Markt**" · UC3: „Info **Niedrige Konzentration** Info 0 9 18 27 36 FRAUNHOFERAUSTRI… …"
- **Widerspruch:** Der Header deutet intensiven Wettbewerb (hohes HHI? viele Akteure?) – UC3 sagt aber ausdrücklich *niedrige* Konzentration. Beides gleichzeitig ist nur dann unwidersprüchlich, wenn Header-Label „intensiv" exakt „niedriges HHI = viele kleine Spieler" meint; die Nutzer­intuition geht jedoch entgegengesetzt.
- **Fix-Hypothese:** Header-Label-Mapping invertieren oder präziser formulieren („Fragmentierter Markt" statt „Wettbewerbsintensiv").

#### C4 – UC10 EuroSciVoc: nur 1 Feld mit 0-%-Werten und widersprüchlicher Projektzahl
- **Quelle:** UC10 (`"1 Feld 58 Projekte 0% 0% 1% 1% 1% chemical engineering 58 Projekte zugeordnet · Shannon-Index: 5.15"`)
- **Snippet:** „**1 Feld** 58 Projekte 0% 0% 1% 1% 1% chemical engineering … Shannon-Index: **5.15**"
- **Widerspruch:** (a) Nur 1 dominantes Feld aber Shannon-Index **5,15** ist mathematisch unmöglich – Shannon bei 1 Feld = 0. (b) Prozent-Verteilung „0% 0% 1% 1% 1%" summiert nicht annähernd auf 100 %. (c) 58 Projekte in UC10 ≠ 48 Projekte im Header / UC4. (d) „chemical engineering" als einziges Feld für ICE ist inhaltlich nur eingeschränkt plausibel (primäre Disziplin wäre mechanical/automotive engineering).
- **Fix-Hypothese:** Shannon-Berechnung greift auf andere (tiefere) Taxonomie-Ebene zu als die angezeigte Top-5; Prozent-Labels sind gerundet/abgeschnitten; Projekt-Zähler bezieht ESV-verknüpfte Mehrfachzuordnungen ein. UC10 komplett durchrechnen.

### MAJOR

#### M1 – CAGR −7,6 % vs. R² = 0,999 / Phase „Reife"
- **Quelle:** UC1 (`"Patente CAGR: -7.6% … Projekte CAGR: -8.3%"`) · UC2 (`"Phase: Reife … R² = 0.999 Wendepunkt: 2014"`)
- **Widerspruch:** Aktivität schrumpft seit Jahren zweistellig (Patent und Projekt), aber UC2 meldet saubere Sigmoid-Reife mit R² = 0,999 – Wendepunkt 2014 liegt 12 Jahre zurück, Kurve müsste längst „Sättigung"/„Rückgang" sein. Header kombiniert zu „Reife + Rückläufige Entwicklung" (klassische Doppel-Phase aus 1. Welle). UC2 liefert nur „Reife".
- **Fix-Hypothese:** Phase-Klassifikator sollte bei negativer CAGR nicht „Reife" sondern „Sättigung/Rückgang" setzen; R² ≥ 0,99 beweist nur, dass *ein* Sigmoid passt – nicht, dass die Phase „Reife" statt „Rückgang" ist.

#### M2 – Doppel-Phase im Header, UC2 einphasig
- **Quelle:** Header „Phase: Reife Rückläufige Entwicklung" vs. UC2 „Phase: Reife"
- **Widerspruch:** Zwei Phase-Labels im Header, nur eines im Panel. Identisch zum globalen 1.-Welle-Muster.
- **Fix-Hypothese:** Header-Label-Komposition aus zwei Quellen (Sigmoid-Phase + Trend-Direction) zu einem eindeutigen Label verschmelzen oder klar trennen.

#### M3 – Jahresachsen-Inkonsistenz innerhalb desselben Dashboards
- **Quelle:** UC1/UC2/UC8/UC12 (2016/2017–**2026**) vs. UC7 (2018–**2025**) vs. UC13 (2016–**2024**)
- **Snippets:** UC1 „2017 2018 … 2025 2026"; UC7 „2018 … 2025"; UC13 „2016 2017 … 2024"
- **Widerspruch:** Drei unterschiedliche Endjahre in einem einzigen Dashboard. CAGR in UC1 (−7,6 %) läuft bis 2026 (nur 3,5 Monate verfügbar!) und verzerrt den Trend nach unten. UC7/UC13 schneiden ab 2024/2025.
- **Fix-Hypothese:** Einheitliches Cutoff-Jahr (z. B. 2024 = letztes vollständiges Jahr) bei CAGR-/Sigmoid-Fit; unvollständige Jahre nur als „outlook"-Layer anzeigen.

#### M4 – Warnhinweis fehlt in UC7 und UC13 teilweise
- **Quelle:** UC7 enthält `"Daten ggf. unvollständig"`, UC13 (Publikationen-Tab) **nicht**, obwohl Achse nur bis 2024 läuft und 2025/26 fehlen; UC3/UC5/UC6/UC9/UC10/UC11 haben den Hinweis ebenfalls nicht.
- **Widerspruch:** Inkonsistente Warnhinweis-Darstellung – Nutzer kann Datenvollständigkeit nicht verlässlich einschätzen.
- **Fix-Hypothese:** Warnhinweis an alle Panels mit Zeitachse knüpfen, sofern letzte ≥ 2 Jahre unvollständig.

#### M5 – Projekt-Zahl divergiert zwischen Header/UC4 und UC10
- **Quelle:** Header (`"48 EU-Projekte"`) = UC4 Förderung (`"48 Projekte"`) ≠ UC10 (`"58 Projekte"`)
- **Widerspruch:** +10 Projekte in UC10. EuroSciVoc müsste eine Teilmenge der CORDIS-Projekte sein, kann nicht größer sein.
- **Fix-Hypothese:** UC10 zählt ESV-Zuordnungen statt distincter Projekte (ein Projekt mit 2 ESV-Tags wird doppelt gezählt) – entweder `DISTINCT` oder Label anpassen („58 ESV-Zuordnungen aus 48 Projekten").

#### M6 – UC8 Dynamik-Diagnose „Schrumpfend (-320 netto)" bei 30 Akteuren
- **Quelle:** UC8 (`"30 Akteure Schrumpfend (-320 netto)"`)
- **Widerspruch:** Netto-Abfluss von 320 Akteuren, aber Gesamt-Akteurs-Zahl nur 30? Das ist mathematisch nur möglich, wenn „30" die *aktuell* verbleibenden und „−320" die *kumulierten Abflüsse über die gesamte Zeitachse* bezeichnet. Label-Beschriftung ist irreführend. UC11 nennt zusätzlich **270 Akteure**, UC9 **92 Akteure**. Drei Zahlen, drei Quellen, keine klare Abgrenzung.
- **Fix-Hypothese:** UC8-Label eindeutig machen („30 aktive, -320 netto über 10 Jahre"). Akteurs-Zählung über UC8/UC9/UC11 zueinander definieren.

#### M7 – UC12 Grant-Rate plausibilisierbar, aber 2025/2026 ist Time-to-Grant-Statistik verzerrt
- **Quelle:** UC12 (`"Quote: 27.6% 37.9 Mon. bis Erteilung 30.554 Anmeldungen 8.435 Erteilungen"`)
- **Nachrechnung:** 8.435 / 30.554 = **27,6 %** ✓ mathematisch korrekt.
- **Widerspruch (Minor-Major):** Anmeldungen aus 2023–2026 haben die 37,9-Monats-Schwelle gar nicht erreichen können – Grant-Rate ist strukturell zu niedrig angesetzt. Achse läuft bis 2026 mit `Daten ggf. unvollständig`.
- **Fix-Hypothese:** Grant-Rate nur auf abgeschlossene Kohorten (Anmeldung ≥ 4 Jahre zurück) rechnen.

### MINOR

#### m1 – UC3 Achsenbeschriftung fehlt Einheit / Y-Achse endet bei 36
- **Snippet:** „0 9 18 27 36 FRAUNHOFERAUSTRI…"
- **Befund:** Top-Player mit maximal ~36 Patenten/Projekten – bei 10.2K Gesamt-Patenten macht der Spitzenakteur somit <0,4 % aus. Das stützt zwar UC3-Aussage „niedrige Konzentration", macht den Header-Widerspruch (C3) aber noch stärker.

#### m2 – UC5 Whitespace-Ausweis unklar
- **Snippet:** „10 CPC-Klassen Ø Jaccard: 0.234 Info **9 Whitespace-Lücken**"
- **Befund:** Bei 10 CPC-Klassen maximale paarweise Anzahl = 45 Kanten → 9 Lücken heißt 36 Kookkurrenzen vorhanden; bei Ø Jaccard 0,234 eher unplausibel hoch. Keine unmittelbare Inkonsistenz, aber Erklärung fehlt.

#### m3 – UC13 DOI-Quote 13 % extrem niedrig
- **Snippet:** „57.7 Pub/Projekt **DOI: 13%**"
- **Befund:** Bei 2.770 hochgerechneten Publikationen nur 13 % mit DOI – für EU-CORDIS-Pub­likationen ungewöhnlich niedrig. Deutet auf schlechte CORDIS-Link-Qualität oder Einschluss von grauer Literatur hin.

#### m4 – UC11 Prozent-Verteilung nicht sichtbar
- **Snippet:** „270 Akteure Dominiert: KMU / Unternehmen KMU/Unternehmen Higher Education Research Organisation Other Public Body"
- **Befund:** Nur Label, keine Prozent-Werte im extrahierten Text – Plausibilisierung `Σ = 100 %` nicht möglich.

### INFO

- **i1:** UC2 Wendepunkt 2014 + R² 0,999 ist bei monoton fallender Kurve seit 2017 mathematisch möglich (Sigmoid schon gesättigt), aber die Phase-Klassifikation „Reife" ist Auslegungs­sache – korrekter wäre „Post-Peak/Rückgang".
- **i2:** Nachvollziehbarkeits-Zeile **31.2s** ist in allen 13 Panels identisch – vermutlich globaler Lade-Timer, nicht Panel-spezifisch.
- **i3:** UC4 Förderung 159,6 Mio. EUR vs. Header „€160M" konsistent (gerundet).
- **i4:** UC6 „Top: Deutschland" mit Achse bis 8.000 Patenten plausibel für ICE (DE = Automotive-Hochburg).

---

## Zusammenfassung (Befunde-Zähler)
- CRITICAL: 4 (Publikations-Zähler-Null, UC13×UC7-Faktor 27, Wettbewerbs-Label-Widerspruch, UC10 Shannon/Prozent/Feld-Anzahl)
- MAJOR: 7 (Phase×CAGR, Doppel-Phase, Jahresachsen-Inkonsistenz, Warnhinweise, Projekt-Zahlen, Dynamik-Label, Grant-Rate-Kohorte)
- MINOR: 4
- INFO: 4
