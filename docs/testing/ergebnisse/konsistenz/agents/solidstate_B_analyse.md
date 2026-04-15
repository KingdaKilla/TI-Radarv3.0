# Konsistenz-Audit Solid State Battery - Rolle B (Analysierer)

**Input:** `raw3_solidstate.json` · **Datum:** 2026-04-14 · **Tech:** solid state battery

## Header-Fingerprint

358 Patente · 113 EU-Projekte · 0 Publikationen · Phase „Reife Stagnation" · „Wettbewerbsintensiver Markt" · EUR 297M Förderung · „Sehr hoher Forschungsimpact".

---

## Befunde nach Severity

### CRITICAL

#### C1 - Header „0 Publikationen" widerspricht UC7 mit 200 Publikationen
- **Quelle:** Header vs. UC7 Forschungsimpact
- **Snippet Header:** „358 Patente 113 EU-Projekte **0 Publikationen**"
- **Snippet UC7:** „Forschungsimpact Info **200 Publikationen** 196.4 Zitate/Pub. 15 Institutionen"
- **Widerspruch:** Kopfzeile meldet keine Publikationen, UC7 liefert 200 Publikationen mit 196,4 Zitaten/Pub.; identische Zahl muss in beiden Datenquellen erscheinen.
- **Fix-Hypothese:** Header zieht `publications_count` aus einer leeren Tabelle (Join-Miss oder CORDIS-only), während UC7 die OpenAlex-Quelle nutzt. Header-KPI auf dieselbe Pipeline wie UC7 umstellen.

#### C2 - Phase „Reife Stagnation" widerspricht CAGR +35,5 %
- **Quelle:** Header vs. UC1 Aktivitätstrends
- **Snippet:** Header „Phase: Reife Stagnation" vs. UC1 „Patente CAGR: **35.5%** Projekte CAGR: **30.7%**"
- **Widerspruch:** Eine reife, stagnierende Technologie kann nicht gleichzeitig einen zweistelligen zweistelligen Patent- und Projekt-CAGR haben; +35 % ist klassischer Wachstumsmodus.
- **Fix-Hypothese:** Das Label „Reife Stagnation" ist ein Header-Compound aus UC2-Phase + Zusatz-Heuristik. Heuristik auf CAGR-Konsistenz prüfen oder Zusatz komplett fallen lassen - UC2 selbst sagt schlicht „Reife".

#### C3 - Header „Wettbewerbsintensiver Markt" widerspricht UC3 „Niedrige Konzentration"
- **Quelle:** Header vs. UC3 Wettbewerb & HHI
- **Snippet Header:** „Wettbewerbsintensiver Markt"
- **Snippet UC3:** „UC3 Wettbewerbsanalyse Info **Niedrige Konzentration**"
- **Widerspruch:** „Niedrige Konzentration" bedeutet fragmentierter Markt ohne dominanten Player, nicht automatisch „wettbewerbsintensiv". Aus identischem HHI-Wert wird im Header eine gegenteilig klingende Aussage geformt.
- **Fix-Hypothese:** Header-Label direkt aus HHI-Bucket mappen („fragmentiert" / „mittel" / „konzentriert") statt aus ungeprüfter Sprach-Synthese.

#### C4 - UC10 EuroSciVoc: Feld „law" dominiert Solid State Battery
- **Quelle:** UC10 EuroSciVoc
- **Snippet:** „UC10 Wissenschaftsdisziplinen Info **1 Feld** 106 Projekte ... **law** 106 Projekte zugeordnet · Shannon-Index: 4.77"
- **Widerspruch:** „law" (Rechtswissenschaft) ist inhaltlich für Festkörperbatterien unsinnig; die Taxonomie erwartet z.B. materials science, electrochemistry, energy engineering. Zusätzlich widerspricht „1 Feld" dem Shannon-Index 4,77 (nur bei mehreren gleichverteilten Feldern möglich).
- **Fix-Hypothese:** EuroSciVoc-Mapping ist kaputt - entweder falscher Top-Level-Knoten (z.B. Wurzel „natural sciences / law / ..." wird als „law" geparst) oder Hierarchie-Level falsch aggregiert. Mapping-Fix inkl. Plausibilitäts-Alert, wenn die Fläche mit hoher Entropie auf ein Single-Label kollabiert.

#### C5 - UC13 Pub/Projekt × Projekte widerspricht UC7 um Faktor ~6
- **Quelle:** UC13 Publikationen vs. UC7 Forschungsimpact vs. Header
- **Rechnung:** UC13 meldet „11.2 Pub/Projekt", UC4/Header 113 Projekte → **113 × 11,2 = 1.266 Publikationen**. UC7 liefert aber nur 200, Header 0.
- **Widerspruch:** Drei verschiedene Publikationszahlen im selben Dashboard (0 / 200 / rechnerisch 1.266). Keine Angabe lässt sich aus einer anderen rekonstruieren.
- **Fix-Hypothese:** UC13 rechnet vermutlich auf CORDIS-Publikationsliste (inkl. Konferenzbeiträge, Dissertationen, Berichten), UC7 auf OpenAlex-Journal-Papers. Definitions-Disambiguierung („wissenschaftl. Outputs" vs. „peer-reviewed Publikationen") und identische Grundgesamtheit für Pub/Projekt-Quotient verlangt.

### MAJOR

#### M1 - Projekt-Zählerei: 113 (Header/UC4) vs. 106 (UC10)
- **Quelle:** Header, UC4 Förderung, UC10 EuroSciVoc
- **Snippet:** Header „113 EU-Projekte" · UC4 „113 Projekte" · UC10 „106 Projekte"
- **Widerspruch:** Differenz von 7 Projekten zwischen EuroSciVoc- und Förder-Panel. Projekte entweder unkategorisiert (kein EuroSciVoc-Label) oder durch Taxonomie-Filter verloren.
- **Fix-Hypothese:** UC10 muss „ohne Zuordnung"-Bucket zeigen oder Footnote „7 Projekte ohne Taxonomie-Zuordnung", damit die Gesamtmenge konsistent bleibt.

#### M2 - UC8 „Schrumpfend -97 netto" widerspricht hohen CAGRs und Phase „Reife"
- **Quelle:** UC8 Dynamik & Persistenz
- **Snippet:** „22 Akteure Schrumpfend (-97 netto)"
- **Widerspruch:** Patent-CAGR +35,5 % + Projekt-CAGR +30,7 % erfordern eigentlich wachsende oder konstante Akteurs-Basis. Gleichzeitiges „Schrumpfen von 97 Akteuren netto" passt weder zum Wachstum noch zur Phase „Reife". Wahrscheinlich Ursache: unvollständige 2025/2026-Daten werden als „Ausscheiden" interpretiert.
- **Fix-Hypothese:** Aktoren, die in den letzten 12-18 Monaten keinen neuen Output haben, dürfen bei unvollständigem Beobachtungsfenster nicht als „Ausgeschieden" gelabelt werden. Censoring-Fenster einführen (z.B. nur bis Cutoff-Jahr - 2).

#### M3 - Jahresachse reicht bis 2026, fließt ungekennzeichnet in Fit ein
- **Quelle:** UC1, UC2, UC8, UC12
- **Snippet UC2:** „2016 2017 ... 2024 2025 2026 ... Wendepunkt **2024**" · R² = 0,982 · Konfidenz 94 %
- **Widerspruch:** Aktuelles Datum 2026-04-14 bedeutet nur ~3,5 Monate von 2026 liegen in den Daten - Patente werden 18 Monate embargoed publiziert, d.h. 2025/2026 sind strukturell unvollständig. Sigmoid-Fit mit diesen Punkten produziert künstlichen Sättigungsverlauf → daher der plausibel-klingende, aber überverfrühte Wendepunkt 2024 und das unangebracht hohe R² = 0,982.
- **Fix-Hypothese:** Fit nur auf Jahre bis „Cutoff - 2", laufendes + Vorjahr als Prognose-Marker darstellen, Warnhinweis in UC2 ergänzen (bisher nur bei UC1/UC2/UC8/UC12 - OK, aber Konfidenz separat entwerten).

#### M4 - UC12 Quote/Zahlen widersprüchlich zu 358 Header-Patenten
- **Quelle:** UC12 Patenterteilung vs. Header
- **Snippet:** „Quote: 13.2 % · 12.074 Anmeldungen · 1.592 Erteilungen"
- **Widerspruch:** Header nennt „358 Patente", UC12 arbeitet mit 12.074 Anmeldungen (Faktor 34). Nachrechnung: 1.592 / 12.074 = 13,2 % passt zu sich selbst, aber die 358 ist eine völlig andere Grundgesamtheit - wahrscheinlich „Patentfamilien" oder „relevante Patente nach CPC-Filter" vs. UC12 „alle Anmeldungen aller Anmelder in Roh-EPO-Dump".
- **Fix-Hypothese:** Header-Definition („Patente") klarstellen (Patentfamilien? gewährte? nach Filter?) und in UC12 gleichen Filter anwenden oder beide Zahlen nebeneinander zeigen („358 gewährte / 12.074 Anmeldungen roh").

#### M5 - UC7 Jahresachse bis 2025, UC13 bis 2024, UC1/UC2 bis 2026
- **Quelle:** UC7, UC13 vs. UC1, UC2, UC8, UC12
- **Snippet UC7:** „2016 ... 2024 **2025**" · UC13: „2016 ... **2024**" · UC1/UC2: „... 2025 **2026**"
- **Widerspruch:** Drei verschiedene Endjahre im selben Dashboard. Impliziert inkonsistente ETL-Stände pro Datenquelle.
- **Fix-Hypothese:** Global einheitliches `data_cutoff`-Feld pro Quelle, UI rendert nur Jahre ≤ `min(cutoffs)` oder zeigt cutoff-Badge pro Panel.

### MINOR

#### m1 - UC7 „Sehr hoher Forschungsimpact" bei nur 200 Publikationen / 15 Institutionen
- **Quelle:** Header vs. UC7
- **Snippet:** Header „Sehr hoher Forschungsimpact" · UC7 „200 Publikationen · 196.4 Zitate/Pub. · 15 Institutionen"
- **Widerspruch:** 196 Zitate/Pub. ist tatsächlich hoch, aber Kombination aus 200 Pubs und 15 Institutionen ist eine schmale Basis; das Label „sehr hoch" verspricht mehr Breite als geliefert.
- **Fix-Hypothese:** Impact-Label an Sample-Size koppeln; unter N<500 maximal „hoch".

#### m2 - UC5 „10 Whitespace-Lücken" ohne aufgelistete Lücken
- **Quelle:** UC5 Technologiekonvergenz
- **Snippet:** „10 CPC-Klassen Ø Jaccard: 0.328 Info **10 Whitespace-Lücken** Y02E H01M Y02P H01B C01P C01B C01G Y02T C08F C08L"
- **Widerspruch:** Das Versprechen „Whitespace-Lücken" wird zur Zahl 10 reduziert; die Liste der Classes (Y02E … C08L) sind die 10 *vorhandenen* CPCs, nicht die Lücken. Lücken sind damit nicht ablesbar.
- **Fix-Hypothese:** Whitespace-Liste explizit rendern („CPC-Paar A↔B: Jaccard-Erwartung vs. beobachtet").

#### m3 - UC9 „3 Cluster, 44 Akteure" widerspricht UC11 „365 Akteure"
- **Quelle:** UC9 Tech-Cluster vs. UC11 Akteurs-Typen
- **Snippet UC9:** „3 Cluster 44 Akteure 119 CPC-Klassen" · UC11: „365 Akteure"
- **Widerspruch:** Differenz 365 vs. 44 Akteure - vermutlich unterschiedliche Definitionen (Patent-Anmelder vs. alle Akteurstypen), aber ohne Erläuterung irritierend.
- **Fix-Hypothese:** Tooltips „44 Patent-Anmelder in Cluster-Profil" vs. „365 Akteure gesamt (Patent + Projekt + Pub)" klar benennen.

#### m4 - UC11 Prozent-Summen nicht sichtbar
- **Quelle:** UC11 Akteurs-Typen
- **Snippet:** „365 Akteure Dominiert: KMU / Unternehmen KMU / Unternehmen Higher Education Research Organisation Other Public Body"
- **Widerspruch:** Keine Prozentzahlen im Text-Dump sichtbar; Verteilung nicht prüfbar auf Summe = 100 %.
- **Fix-Hypothese:** Anteile explizit als numerische Labels neben die Kategorien rendern.

### INFO

#### i1 - UC13 DOI-Anteil 83 % im plausiblen Bereich
- **Quelle:** UC13 Publikationen
- **Snippet:** „DOI: 83 %"
- **Anmerkung:** 83 % DOI-Quote ist für CORDIS-Linked-Publications realistisch. Keine Beanstandung.

#### i2 - UC2 R² = 0,982 bei breiter Datenbasis plausibel
- **Quelle:** UC2
- **Anmerkung:** Anders als bei Nischen-Techs (z.B. N=8 Patente) ist bei 358 Patenten + 113 Projekten ein Sigmoid-Fit statistisch belastbar; R² = 0,982 nicht per se verdächtig, aber siehe M3 zu Jahres-Cutoff.

---

## Zusammenfassende Severity-Matrix

| Severity | Anzahl | IDs |
|---|---|---|
| Critical | 5 | C1, C2, C3, C4, C5 |
| Major | 5 | M1, M2, M3, M4, M5 |
| Minor | 4 | m1, m2, m3, m4 |
| Info | 2 | i1, i2 |

**Blocker für Budget-Entscheidung:** C1 (Pub-Zahl), C2 (Phase-CAGR-Widerspruch), C3 (Wettbewerbs-Label), C4 (EuroSciVoc-Müll), C5 (drei Pub-Wahrheiten).
