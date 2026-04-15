# mRNA · Rolle B · Analyse harter Inkonsistenzen

Kontext: Header-KPIs = 742 Patente · 307 EU-Projekte · 311.5K Publikationen · Phase „Reife Rückläufige Entwicklung" · Wettbewerbsintensiver Markt · €446M Förderung · Sehr hoher Forschungsimpact. Heutiges Datum: 2026-04-14. Fit-/Trend-Panels ziehen 2025 und 2026 in die Kurve, obwohl unvollständig.

Befunde sind nach Severity sortiert (Critical → Info). Jede Zeile: ID · Titel · Quelle · Snippet · Widerspruch · Fix.

---

## Critical

### C1 · Publikationen Header vs. UC7/UC13 — Faktor ~1.580×
- **Quelle:** Header („311.5K Publikationen") vs. UC7 Forschungsimpact („197 Publikationen") vs. UC13 Publikationen („8.0 Pub/Projekt").
- **Snippet Header:** `742 Patente 307 EU-Projekte 311.5K Publikationen`
- **Snippet UC7:** `Forschungsimpact Info 197 Publikationen 610.1 Zitate/Pub. 15 Institutionen`
- **Snippet UC13:** `Publikationen 8.0 Pub/Projekt DOI: 78%`
- **Widerspruch:** Header behauptet 311 500 Publikationen, UC7 zeigt 197 (Faktor ~1 580); selbst UC13-Kalkulation 8.0 × 307 ≈ 2 456 liegt drei Größenordnungen unter dem Header.
- **Fix:** Header muss aus derselben Quelle speisen wie UC7 (CORDIS-linked Publikationen); vermutlich verwechselt er einen Zitations- oder externen Pub-Index mit Publikationen. Zusätzlich UC13-Berechnung (Pub/Projekt × Projekte) gegen UC7 validieren.

### C2 · Wettbewerbsintensiver Markt (Header) vs. Niedrige Konzentration (UC3)
- **Quelle:** Header vs. UC3 Wettbewerb & HHI.
- **Snippet Header:** `Wettbewerbsintensiver Markt`
- **Snippet UC3:** `UC3 Wettbewerbsanalyse Info Niedrige Konzentration`
- **Widerspruch:** Niedrige HHI-Konzentration bedeutet fragmentierte, nicht „wettbewerbsintensive" Lage im HHI-Sinne; Header-Label widerspricht direkt dem UC3-Label.
- **Fix:** Header-Regel „wenn HHI < Schwelle → fragmentiert/kompetitiv" sauber umformulieren und mit dem UC3-Wording synchronisieren (z. B. beide sagen „fragmentiert / niedrige Konzentration").

### C3 · Phase „Reife Rückläufige Entwicklung" (Header) vs. UC2 „Reife, Wendepunkt 2022" + positive CAGR
- **Quelle:** Header vs. UC2 S-Kurve & Reife vs. UC1 Aktivitätstrends.
- **Snippet Header:** `Phase: Reife Rückläufige Entwicklung`
- **Snippet UC2:** `Phase: Reife … Wendepunkt: 2022 … Konfidenz: 95%`
- **Snippet UC1:** `Patente CAGR: 5.6% … Projekte CAGR: 0.8% … Publikationen CAGR: 1.8%`
- **Widerspruch:** Header kombiniert „Reife" mit „Rückläufig", UC2 nennt ausschließlich „Reife". Zudem sind alle drei CAGR-Werte positiv (Patente sogar +5.6 %) — „rückläufig" ist durch keine Zeitreihe gedeckt. Ein Wendepunkt 2022 ist in einer Sigmoid-Kurve bis heute noch nicht im Rückgang.
- **Fix:** Header-Label auf genau eine Phase aus UC2 beschränken; „rückläufig" nur setzen, wenn CAGR auf vollen Jahren < 0. Alternativ Header-Teil „Rückläufig" aus UC8-Dynamik (siehe C4) abgrenzen und klar als Akteursdynamik deklarieren, nicht als Technologie-Phase.

### C4 · Akteursdynamik -97 netto bei gleichzeitig +5.6 % Patent-CAGR
- **Quelle:** UC8 Dynamik & Persistenz vs. UC1 Aktivitätstrends.
- **Snippet UC8:** `34 Akteure Schrumpfend (-97 netto)`
- **Snippet UC1:** `Patente CAGR: 5.6%`
- **Widerspruch:** „Schrumpfend −97 netto" bei 34 aktuellen Akteuren impliziert, dass mehr Akteure ausgeschieden sind als aktuell aktiv, während Patent-Output weiterhin positiv wächst. Entweder ist die Zählbasis (Fenster) unpassend oder das Label irreführend.
- **Fix:** UC8-Zählfenster (Rolling vs. kumuliert) klarer ausweisen; bei einem derart großen Delta Warnhinweis oder Kontext („COVID-Welle 2020–2022 → Normalisierung 2023–2024").

### C5 · EuroSciVoc: nur 1 Feld „nanotechnology" für mRNA
- **Quelle:** UC10 EuroSciVoc.
- **Snippet:** `1 Feld 387 Projekte 0% 0% 0% 1% 1% nanotechnology 387 Projekte zugeordnet · Shannon-Index: 4.89`
- **Widerspruch:** mRNA-Projekte werden erwartet als „medical biotechnology / molecular biology / immunology / pharmacology". „Nanotechnology" ist lediglich ein Aspekt (LNP-Delivery). Gleichzeitig widerspricht sich das Panel selbst: „1 Feld" vs. Shannon-Index 4,89 (setzt viele Felder voraus) und Prozentleiste „0% 0% 0% 1% 1%" (summiert ≠ 100 %).
- **Fix:** Taxonomie-Mapping prüfen (vermutlich defaultet auf erstbestes Label); Shannon-Index gegen „1 Feld"-Zähler konsistent machen; Balken-Summe auf 100 % normalisieren.

---

## Major

### M1 · Projekt-Zahl Header 307 ≠ UC10 387
- **Quelle:** Header vs. UC10 EuroSciVoc. (UC4 Förderung zeigt 307, also Header==UC4.)
- **Snippet Header/UC4:** `307 EU-Projekte` / `Gesamt: 446.1 Mio. EUR Info 307 Projekte`
- **Snippet UC10:** `387 Projekte`
- **Widerspruch:** UC10 zählt 80 Projekte mehr als UC4/Header. Entweder zieht UC10 einen breiteren Scope (inkl. H2020/FP7-Altprojekte?) oder es gibt Doppelzählungen via Projekt-Topic-Joins.
- **Fix:** Gemeinsame Projektbasis (dieselbe View) für UC4, UC10 und Header; Dokumentation, welches Filterkriterium pro UC gilt.

### M2 · UC12 Grant-Rate vs. nachgerechneter Wert
- **Quelle:** UC12 Patenterteilung.
- **Snippet:** `Quote: 13.9% … 4.024 Anmeldungen 558 Erteilungen`
- **Widerspruch:** 558 / 4024 = 13,87 % — stimmt (gerundet OK). Aber: 4 024 Anmeldungen stehen in massivem Kontrast zu den 742 Patenten im Header. Der Header zählt offensichtlich „granted + Familien-Heads" oder nur DE/EP-Scope, UC12 das EPO-Rohvolumen — ohne Erklärung.
- **Fix:** Header präzisieren: „742 Patentfamilien (EPO-Scope)" oder „erteilte Patente"; UC12 erklärt „4 024 Anmeldungen weltweit". Sonst verwirrt die 5,4-fache Diskrepanz.

### M3 · Unvollständige Jahre (2025, 2026) in S-Kurve/CAGR
- **Quelle:** UC1, UC2, UC8, UC12 zeigen Achse bis 2026.
- **Snippet UC1:** `2017 … 2024 2025 2026 … Daten ggf. unvollständig`
- **Snippet UC2:** `2016 … 2024 2025 2026 … Daten ggf. unvollständig`
- **Widerspruch:** Heute ist 2026-04-14. 2026 ist zu 28 % erfasst, 2025 publikationsseitig (Indexing-Lag 12–18 Monate) ebenfalls nicht geschlossen. CAGR 5.6 % / 0.8 % / 1.8 % werden inkl. dieser Jahre gerechnet → Unterzeichnung des tatsächlichen Trends. Sigmoid-Fit R²=0.998 mit rechter Flanke auf unvollständigen Jahren ist zu optimistisch.
- **Fix:** Fit/CAGR auf abgeschlossene Jahre (≤ 2024) begrenzen, aktuelle Jahre ausgegraut mit „unvollständig"-Badge in allen Panels, nicht nur in einigen.

### M4 · Jahresachse inkonsistent zwischen UCs
- **Quelle:** UC7/UC13 vs. UC1/UC2/UC8/UC12.
- **Snippet UC7:** `2016 2017 … 2024` (kein 2025/2026)
- **Snippet UC1/UC2/UC8/UC12:** bis 2026
- **Widerspruch:** Innerhalb desselben Dashboards unterschiedliche Endjahre erzeugen optische Inkonsistenz und verhindern UC-übergreifenden Vergleich (z. B. Trend-Zacken 2024 sieht in UC7 wie Peak aus, in UC1 wie Nachlauf).
- **Fix:** Gemeinsame Jahresachse (2016–aktuelles Jahr) über alle Zeitreihen-UCs; einheitlich mit „unvollständig"-Schraffur für letzte(n) 1–2 Jahre.

### M5 · Pub/Projekt × Projekte ≠ UC7-Publikationen
- **Quelle:** UC13 vs. UC7.
- **Snippet UC13:** `8.0 Pub/Projekt DOI: 78%`
- **Snippet UC7:** `197 Publikationen`
- **Widerspruch:** 8.0 × 307 Projekte = 2 456 erwartete CORDIS-Linked-Publikationen; UC7 meldet 197. Entweder (a) UC7 zählt nur Top-Impact-Publikationen mit Zitationen (dann Label schärfen), oder (b) die 8.0 sind aus anderer Grundmenge (z. B. aller wissenschaftlichen Outputs, nicht nur CORDIS-Link).
- **Fix:** UC13-„Pub/Projekt" klar als „CORDIS-linked Pub pro Projekt" deklarieren; Rechnung im UI ausschreiben, damit User die Ableitung sieht.

### M6 · UC11 Akteurs-Breakdown ohne Prozente
- **Quelle:** UC11 Akteurs-Typen.
- **Snippet:** `363 Akteure Dominiert: Higher Education Higher EducationKMU / UnternehmenResearch OrganisationOtherPublic Body`
- **Widerspruch:** Prozentwerte pro Typ fehlen im Text komplett; keine Prüfung auf Summe = 100 % möglich. „Dominiert: Higher Education" ist nicht quantifiziert.
- **Fix:** Explizite Prozentlabels (z. B. HES 45 % · PRC 25 % · KMU 18 % · PUB 7 % · OTH 5 %) und numerische Summenprüfung im Renderer.

---

## Minor

### m1 · UC5 Whitespace-Aussage vs. Top-CPC-Liste
- **Quelle:** UC5 Technologiekonvergenz.
- **Snippet:** `10 CPC-Klassen Ø Jaccard: 0.382 Info 6 Whitespace-Lücken C12N A61K A61P C07K C12Q C12Y Y02A C07H G01N C12P`
- **Widerspruch:** Keine Kennzeichnung, welche der 10 Klassen „Whitespace" sind bzw. welches Paar die Lücken bildet — 6 Lücken sind rein numerisch.
- **Fix:** Top-Whitespace-Paare explizit auflisten („A61K × Y02A: 0 gemeinsame Familien").

### m2 · UC9 Tech-Cluster: nur 29 Akteure, aber 363 in UC11
- **Quelle:** UC9 vs. UC11.
- **Snippet UC9:** `5 Cluster 29 Akteure 208 CPC-Klassen`
- **Snippet UC11:** `363 Akteure`
- **Widerspruch:** UC9 betrachtet nur 8 % der UC11-Akteure ohne Erklärung (vermutlich Top-Patent-Akteure). Das sollte der User wissen, um die Dichte- und Kohärenz-Kennzahlen richtig einzuordnen.
- **Fix:** UC9-Untertitel „Top 29 Patent-aktive Akteure" o. ä.

### m3 · UC6 Geographie fokussiert ausschließlich auf Europa
- **Quelle:** UC6 Geographie.
- **Snippet:** `10 Länder Top: Deutschland … Niederlande Frankreich Belgien Schweiz Polen Schweden Vereinigtes K… Italien Spanien`
- **Widerspruch:** Bei mRNA mit US-Dominanz (Moderna, Pfizer/BioNTech USA-Site) fehlen USA, China, Japan — Panel liest sich wie „EU-only". Passt zu CORDIS-Fokus, aber nicht zu Patenten (EPO-Scope inkl. US-Anmelder).
- **Fix:** UC6 als „EU-Projektgeographie" labeln ODER Patent-Geographie und Projekt-Geographie trennen.

### m4 · UC3 Top-Anmelder fast ausschließlich öffentliche europäische Institute
- **Quelle:** UC3 Wettbewerb & HHI.
- **Snippet:** `FUNDACIO CENTRED… FORSCHUNGSINSTITU… UNIVERSITATZURICH MAX DELBRUECKCEN… UNIVERSITAETMUEN… FRAUNHOFERAUSTRI… STICHTINGAMSTERD… AGENCIA ESTATALC…`
- **Widerspruch:** Keine BioNTech, CureVac, Moderna, Pfizer in der Top-Liste — unplausibel für mRNA-Markt. Balken-Skala reicht nur bis 12, also sehr kleine Counts → Panel bildet wohl EU-Projektpartner (UC4-Rohdaten) ab statt Patent-Anmelder.
- **Fix:** UC3 klar als „Top-Patentanmelder nach EPO-Familien" scopen, nicht mit CORDIS-Akteuren mischen.

### m5 · UC7 Institutionen-Zahl 15 vs. UC3 gelistete 8
- **Quelle:** UC7 vs. UC3.
- **Snippet UC7:** `15 Institutionen`
- **Snippet UC3:** 8 Balken sichtbar.
- **Widerspruch:** Keine direkte Kontradiktion (unterschiedliche Dimension), aber Nutzer könnten die Zahlen verwechseln. Sauberes Labeling „Publizierende Institutionen" vs. „Anmelder/Projekt-Koordinatoren" fehlt.
- **Fix:** Dimensions-Labels in Panel-Untertiteln.

### m6 · UC2 R² = 0.998 auf nur 10-Jahres-Fit mit offenem Rand
- **Quelle:** UC2 S-Kurve.
- **Snippet:** `R² = 0.998 … Wendepunkt: 2022 … 2016 … 2026`
- **Widerspruch:** R² = 0.998 ist extrem hoch und suggeriert Überanpassung bei ~10 Jahresdatenpunkten inkl. 2 unvollständiger Jahre. Realistisch ist bei Sigmoid-Fits auf so kurzen Zeitreihen R² 0,85–0,95 — 0,998 riecht nach Fit auf geglätteten Summenkurven.
- **Fix:** Fit-Metrik auf Original-Jahreszahlen (nicht kumulativ) berechnen; zusätzlich AIC/BIC anzeigen.

---

## Info

### I1 · CPC-Top-Klassen inhaltlich plausibel für mRNA
- **Quelle:** UC1.
- **Snippet:** `A61K2039/53, A61P35/00, A61K9/5123, A61K39/12, A61K48/005`
- **Beobachtung:** Vakzin-Formulierungen (A61K2039), Onkologie (A61P35), LNP-Delivery (A61K9/51), Vaccines (A61K39/12), Gen-Therapie (A61K48/005) — passt. Kein Befund, nur Positiv-Ping.

### I2 · Förderungsvolumen 446.1 Mio. EUR über 307 Projekte → Ø 1.45 Mio./Projekt
- **Quelle:** UC4.
- **Beobachtung:** Plausibel für HORIZON-RIA/ERC-Instrumentenmix. Kein Widerspruch — aber Header sollte Ø-Wert ebenfalls ausweisen, um Größenordnung zu vermitteln.

### I3 · Zitate/Pub 610.1 — sehr hoher Impact, plausibel
- **Quelle:** UC7.
- **Beobachtung:** mRNA-COVID-Papiere haben extreme Zitationsraten (Pardi, Karikó, Weissman); 610 Ø-Zitationen auf 197 Top-Publikationen passt. „Sehr hoher Forschungsimpact" im Header dadurch abgedeckt — einziger Header-Claim, der vollständig durch UC-Daten gestützt wird.

---

## Severity-Ranking (Top 3)
1. **C1** – Publikationen-Faktor 1 580× zwischen Header und UC7.
2. **C2** – Header „wettbewerbsintensiv" vs. UC3 „niedrige Konzentration".
3. **C3** – Header-Phase „Reife + Rückläufig" trotz positiver CAGRs und Wendepunkt 2022 in UC2.
