# Konsistenz-Analyse (Rolle B) — autonomous driving

Severity-gewichtete Befunde basierend auf `raw3_autonomous.json`. Quellen: Header-String (Executive Summary) vs. einzelne UC-Panels.

---

## CRITICAL

### C1 — Header „0 Publikationen" widerspricht UC7 (199 Publikationen)
- **Quelle:** Header vs. UC7 (Forschungsimpact)
- **Snippet Header:** „734 Patente 235 EU-Projekte **0 Publikationen** … Sehr hoher Forschungsimpact"
- **Snippet UC7:** „**199 Publikationen** 319.5 Zitate/Pub. 15 Institutionen"
- **Widerspruch:** Header behauptet 0 Publikationen, gleichzeitig wird ein „Sehr hoher Forschungsimpact" ausgewiesen — UC7 nennt jedoch 199 Publikationen mit 319,5 Zitaten/Pub.
- **Fix-Hypothese:** Header-KPI greift auf eine andere (leere) Aggregation zu als UC7; Publikationszähler müssen auf dieselbe View (`mv_publications_by_tech`) gesyncht werden.

### C2 — UC13-Rechnung kollabiert: Pub/Projekt × Projekte ≠ UC7-Publikationen
- **Quelle:** UC13 (Publikationen) × Header-Projekte vs. UC7
- **Snippet:** UC13 „**60.0 Pub/Projekt** DOI: 27%"; Header „235 EU-Projekte"; UC7 „199 Publikationen"
- **Widerspruch:** 60,0 × 235 = **14.100 rechnerische Publikationen** — UC7 zeigt aber nur 199. Abweichung um Faktor ~70.
- **Fix-Hypothese:** „Pub/Projekt" misst kumulativ über alle CORDIS-verknüpften Publikationen (inkl. Mehrfachzuordnung über Projekte), UC7 zählt deduplizierte Tech-Publikationen. Dimensionierung bzw. Benennung der Kennzahl muss korrigiert werden.

### C3 — Wettbewerbs-Widerspruch: Header „Wettbewerbsintensiver Markt" vs. UC3 „Niedrige Konzentration"
- **Quelle:** Header vs. UC3
- **Snippet Header:** „**Wettbewerbsintensiver Markt**"
- **Snippet UC3:** „**Niedrige Konzentration**"
- **Widerspruch:** Header-Label und UC3-Panel-Label widersprechen sich direkt — inhaltlich sind sie jedoch kompatibel (niedriger HHI = viele Wettbewerber = wettbewerbsintensiv). Semantisches Mapping Header↔UC3 ist gegenläufig.
- **Fix-Hypothese:** Label-Mapping zwischen HHI-Score und Header-Textbaustein invertieren oder Labels vereinheitlichen („Fragmentierter Markt" statt „Wettbewerbsintensiver Markt" wenn HHI niedrig).

### C4 — Doppel-Phase im Header vs. klare Einzelphase in UC2
- **Quelle:** Header vs. UC2
- **Snippet Header:** „Phase: **Reife Rückläufige Entwicklung**"
- **Snippet UC2:** „**Phase: Reife** … R² = 0.999 … Wendepunkt: 2021"
- **Widerspruch:** Header kombiniert zwei Phasenlabels, UC2 nennt eindeutig nur „Reife". Die zusätzliche „Rückläufige Entwicklung" stammt vermutlich aus UC8 („Schrumpfend -293 netto"), wird aber als Teil der Reifephase präsentiert.
- **Fix-Hypothese:** Header-Phase strikt aus UC2 übernehmen; Dynamik-Status (UC8) separat als zweites Label ausweisen, nicht verkettet.

---

## MAJOR

### M1 — Projektzahl Header vs. UC10 (234 vs. 235)
- **Quelle:** Header vs. UC10 (EuroSciVoc)
- **Snippet:** Header „**235 EU-Projekte**"; UC10 „**234 Projekte** zugeordnet"; UC4 „235 Projekte"
- **Widerspruch:** Off-by-one zwischen Header/UC4 (235) und UC10 (234). Nicht fatal, aber reproduzierbares Zählerei-Delta.
- **Fix-Hypothese:** 1 Projekt ohne EuroSciVoc-Zuordnung — entweder explizit ausweisen („234 von 235 klassifiziert") oder auf Gesamtzahl harmonisieren.

### M2 — UC10: „0 Felder" trotz gelisteter Taxonomie-Begriffe
- **Quelle:** UC10
- **Snippet:** „**0 Felder** 234 Projekte 0% 4% 8% 12% 16% sensors autonomous vehicles automation optical sensors software radar drones … Shannon-Index: 5.26"
- **Widerspruch:** KPI „0 Felder" kontrastiert mit mindestens 7 sichtbaren EuroSciVoc-Labels und einem Shannon-Index von 5,26 (der nur bei vielen Kategorien >0 ist).
- **Fix-Hypothese:** „Felder"-Zähler zählt falsche Taxonomie-Ebene (Top-Level statt angezeigtes Level) oder Aggregationsbug — Shannon-Diversität und Label-Count müssen auf derselben Grundmenge rechnen.

### M3 — UC8 „Schrumpfend -293 netto" vs. CAGR +11,7 % (Patente) / +8,4 % (Projekte)
- **Quelle:** UC1 vs. UC8
- **Snippet UC1:** „Patente CAGR: 11.7% … Projekte CAGR: 8.4%"
- **Snippet UC8:** „12 Akteure **Schrumpfend (-293 netto)**"
- **Widerspruch:** Beide Aktivitätsmaße wachsen zweistellig — die Akteursdynamik zeigt trotzdem einen massiven Netto-Rückgang von 293 Akteuren und nennt nur „12 Akteure" (gegen UC11: „1.274 Akteure").
- **Fix-Hypothese:** UC8 vergleicht vermutlich Zeitfenster inkl. unvollständiger 2025/2026-Jahre — Rückgang ist Artefakt der Jahresabschneidung. Filter auf abgeschlossene Jahre setzen oder Warnhinweis verschärfen.

### M4 — Jahresachsen-Inkonsistenz 2024 vs. 2025 vs. 2026
- **Quelle:** UC1/UC2/UC8/UC12 vs. UC7 vs. UC13
- **Snippet:** UC1, UC2, UC8, UC12 reichen bis **2026**; UC7 bis **2025**; UC13 bis **2024**.
- **Widerspruch:** Drei unterschiedliche Endjahre im gleichen Dashboard bei Stichtag 2026-04-14. UC13 endet vor UC7, UC7 vor den übrigen Trendpanels.
- **Fix-Hypothese:** Einheitliche Jahresspanne dashboardweit, oder pro UC begründete Endjahre (CORDIS-Latency bei Pub/DOI explizit im Panel notieren).

### M5 — „Daten ggf. unvollständig"-Warnung inkonsistent verteilt
- **Quelle:** Panels
- **Betroffen:** Warnung vorhanden in UC1, UC2, UC7, UC8, UC12. **Fehlt** in UC13 (endet 2024), UC3, UC4, UC11, UC5, UC6, UC9, UC10.
- **Widerspruch:** Nur 5 von 13 Panels warnen, obwohl zumindest UC13 (2024) ebenfalls abgeschnittene/unvollständige Datengrundlage hat.
- **Fix-Hypothese:** Warnhinweis regelbasiert an jedes Panel hängen, das Trenddaten nach 2024 zeigt oder CORDIS-Daten mit Delay verarbeitet.

### M6 — UC12 Grant-Rate-Nachrechnung stimmt, aber Basis ≫ Header-Patente
- **Quelle:** UC12 vs. Header
- **Snippet UC12:** „Quote: 40.8% … 6.336 Anmeldungen 2.586 Erteilungen"
- **Snippet Header:** „**734 Patente**"
- **Nachrechnung:** 2.586 / 6.336 = 40,81 % — Quote intern konsistent. Aber 6.336 Anmeldungen im UC12 vs. 734 Patente im Header = Faktor ~8,6.
- **Widerspruch:** Header zählt offenbar eine Familien-/Distinct-Ebene (z. B. INPADOC-Familien), UC12 zählt Einzelanmeldungen. Nutzer versteht das nicht.
- **Fix-Hypothese:** Header-KPI klar als „Patentfamilien" labeln; UC12 als „Einzelanmeldungen/-erteilungen"; oder auf einer Ebene vereinheitlichen.

---

## MINOR

### m1 — UC7 Zitate/Pub. auf kleiner Basis sehr hoch
- **Quelle:** UC7
- **Snippet:** „199 Publikationen **319.5 Zitate/Pub.** 15 Institutionen"
- **Anmerkung:** 319,5 Zitate/Publikation sind außergewöhnlich hoch; plausibel nur bei wenigen hochzitierten Ausreißern. Dürftige Basis (199) + Header „Sehr hoher Forschungsimpact" → irreführend, weil Median vermutlich deutlich niedriger.
- **Fix-Hypothese:** Median + Perzentile zusätzlich zum Mittelwert ausweisen; „Sehr hoher Impact"-Label an Robustheitsschwelle koppeln.

### m2 — R² = 0,999 bei 734 Patenten über 10 Jahre ist auffällig perfekt
- **Quelle:** UC2
- **Snippet:** „R² = 0.999 … Wendepunkt: 2021 … Konfidenz: 95%"
- **Anmerkung:** Ein derart idealer Sigmoid-Fit ist selten; möglicherweise Overfitting oder Monotonisierung in der Vorverarbeitung.
- **Fix-Hypothese:** Fit-Residuen prüfen, ggf. Cross-Validation-R² statt In-Sample ausweisen.

### m3 — UC4 Förderungsbetrag leicht abweichend vom Header
- **Quelle:** Header vs. UC4
- **Snippet Header:** „**€755M Förderung**"; UC4: „**754.8 Mio. EUR**"
- **Anmerkung:** Rundungsdifferenz €200k — akzeptabel, aber konsistente Rundungsregel fehlt (Header rundet auf, UC4 rundet ab).

### m4 — UC11 Prozentsummen nicht darstellbar prüfbar
- **Quelle:** UC11
- **Snippet:** „1.274 Akteure Dominiert: KMU / Unternehmen **KMU / UnternehmenHigher EducationResearch OrganisationOtherPublic Body**"
- **Anmerkung:** Panel-Text liefert keine numerischen Anteile — Prozentsummen-Validierung (≤100 %) nicht möglich. Texttransfer aus Chart-Legende unvollständig.
- **Fix-Hypothese:** Tooltip-/Legenden-Werte in Accessibility-Pfad ausschreiben.

---

## INFO

- **i1 — Top-CPC-Labels plausibel:** B60W60/001, G05D1/0088, B60W2420/403 passen inhaltlich zu autonomem Fahren — UC1/UC5 fachlich kohärent.
- **i2 — EuroSciVoc-Labels plausibel:** „sensors, autonomous vehicles, automation, optical sensors, software, radar, drones" sind inhaltlich stimmig (anders als der „law"-Fehler bei Solid State Battery).
- **i3 — Geographie plausibel:** DE/FR/SE/IT/UK/NL/CH/ES/BE/AT ist konsistent mit europäischen AD-Forschungsclustern.
- **i4 — Tech-Cluster-Werte nicht vollständig auswertbar:** UC9 liefert „5 Cluster, 52 Akteure, 238 CPC-Klassen" ohne numerische Ausprägung der 5-dim-Profilachsen; Plausibilitätscheck auf Ampelniveau daher nicht möglich.

---

## Gesamt-Severity-Verteilung
- Critical: 4
- Major: 6
- Minor: 4
- Info: 4

Der Tech-Dump zeigt alle prototypischen Inkonsistenzmuster aus der ersten Welle (Header-Publikationen = 0, Doppel-Phase, Wettbewerbs-Widerspruch, Jahresachsen-Drift) plus eine neue Major-Klasse (UC13 × Projekte ≠ UC7 um Faktor 70).
