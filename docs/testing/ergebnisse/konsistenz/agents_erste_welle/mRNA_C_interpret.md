# mRNA · Agent C (Interpreter) · UC-Versprechen vs. Lieferung

**Technologie:** mRNA
**Datenquelle:** `docs/testing/ergebnisse/konsistenz/raw/raw_mRNA.json`
**Audit-Datum:** 14.04.2026
**Header-Kopfzeile (einziger verwertbarer Content):** 742 Patente | 307 EU-Projekte | 311,5 K Publikationen | Phase: Reife / Rückläufige Entwicklung | Wettbewerbsintensiver Markt | €446 M Förderung | Sehr hoher Forschungsimpact

---

## Vorbemerkung: Datenqualität des Dumps

Alle 13 Panels haben im Dump **identischen `mainText`** und als `activeTab` jeweils `"Neue Analyse"` (statt des erwarteten Tab-Namens). Der Text besteht ausschließlich aus:
1. der Executive-Summary-Kopfzeile, und
2. den statischen Cluster-Info-Beschreibungen ("Dieser Analysebereich umfasst …") der vier UI-Cluster.

Nach ~2500 Zeichen bricht der Text mitten im Cluster "Forschung & Förderung / UC4 Förderungsanalyse Zeigt " ab. **Keine panelspezifischen Nutzdaten** (kein HHI, keine CAGR, keine Top-Listen, keine Länder, keine Jahreszahlen, keine R²-Werte, keine Akteurs-Typen-Prozente, keine CPC-Klassen) wurden erfasst.

Das bedeutet für die Interpretation: Entweder (a) die Tabs wurden beim Scrape nicht geöffnet und das Dashboard verharrte auf der Cluster-Auswahl, oder (b) die Tabs laden ihre Inhalte asynchron nach und der Scrape griff zu früh zu. Für die **Gap-Bewertung** gilt: Was im `mainText` nicht steht, kann ein Entscheider in dieser Session nicht sehen. Die Bewertung erfolgt konsequent auf Basis des tatsächlich gelieferten Textes.

---

## UC-Bewertung (Versprechen · Lieferung · Ampel)

| UC | Tab | Versprechen (Cluster-Info) | Liefert laut Dump | Ampel | Begründung |
|---|---|---|---|---|---|
| **UC1** | Aktivitätstrends | Entwicklung von Patent-/Projekt-/Publikationszahlen im Zeitverlauf, CAGR, Dynamik | Nur Header-Aggregat (742/307/311,5 K) und Phrase "Rückläufige Entwicklung". Keine Zeitreihe, kein CAGR-Wert, keine Jahresachse. | 🔴 | Kern-Promise (Zeitverlauf + CAGR) fehlt komplett. Ein Label "rückläufig" ohne Zahl ist nicht auditierbar. |
| **UC2** | S-Kurve & Reife | Reifegrad per S-Kurve (Emerging/Growth/Mature/Declining) | Nur Phase-Badge "Reife" aus Header. Keine S-Kurven-Visualisierung, kein R², kein Wendepunkt, keine Sättigungsschätzung. | 🔴 | Phase-Label ohne Modell-Fit und ohne Datenjahre ist eine Behauptung, kein Nachweis. |
| **UC3** | Wettbewerb & HHI | Marktkonzentration (HHI) + dominante Akteure | Nur Header-Phrase "Wettbewerbsintensiver Markt". Kein HHI-Zahlenwert, keine Top-N-Akteursliste. | 🔴 | "Wettbewerbsintensiv" ohne HHI-Zahl ist pseudoquantitativ. Kein Abgleich gegen andere Techs möglich. |
| **UC4** | Förderung | EU-Fördervolumen nach Forschungsgebiet und Zeitverlauf | Nur Header-Gesamtsumme €446 M. Keine Aufschlüsselung nach Gebiet, kein Zeitverlauf, keine Projekt-Top-Liste. | 🔴 | Einzige vorhandene Zahl (€446 M) ist auf Header-Ebene; das versprochene Breakdown fehlt. |
| **UC5** | Technologiekonvergenz | Konvergenz zwischen CPC-Patentklassen + Whitespace-Lücken | Gar nichts – nur Header + Cluster-Info. | 🔴 | Kernelement (CPC-Matrix, Whitespace-Liste) fehlt vollständig. |
| **UC6** | Geographie | Globale Verteilung der Anmelder/Organisationen | Gar nichts – keine Länder-Top-Liste, kein EU-Share, keine Karte. | 🔴 | Ohne Länder-Daten nicht bewertbar. |
| **UC7** | Forschungsimpact | h-Index, Zitationsraten, Top-Institutionen | Nur Header-Label "Sehr hoher Forschungsimpact". Keine h-Index-Zahl, keine Zitationsrate, keine Institutionen. | 🔴 | Qualitatives Adjektiv ohne Metrik. "Sehr hoch" ist nicht vergleichbar oder verteidigbar. |
| **UC8** | Dynamik & Persistenz | Neue Einstiege, Persistente, Ausgeschiedene | Gar nichts. | 🔴 | Dynamik-Analyse komplett abwesend. |
| **UC9** | Tech-Cluster | 5-dim Profil (Aktivität, Vielfalt, Dichte, Kohärenz, Wachstum) | Gar nichts – kein Radar-Chart-Werte. | 🔴 | Kein Zahlenvektor, kein Peer-Vergleich. |
| **UC10** | EuroSciVoc | Zuordnung zu Wissenschaftsdisziplinen | Gar nichts. | 🔴 | Keine Disziplinen-Liste oder Interdisziplinaritäts-Score. |
| **UC11** | Akteurs-Typen | Breakdown Hochschule/Forschung/Industrie/öffentlich | Gar nichts – keine Prozent-Aufteilung. | 🔴 | Prozent-Summe nicht prüfbar, da gar keine Prozente erfasst. |
| **UC12** | Patenterteilung | Grant-Rate + Time-to-Grant | Gar nichts. | 🔴 | Keine Quote, keine durchschnittliche Zeit. |
| **UC13** | Publikationen | CORDIS-Publikationen × Projekte, Publikationseffizienz | Nur Header-Zahl 311,5 K Publikationen. Kein Pub/Project-Quotient, keine Projekt-Verknüpfung, keine Effizienz-Kennzahl. | 🔴 | Gesamtzahl ist aggregiert; versprochene Effizienz-Sicht fehlt. Außerdem: 311,5 K scheint ein unplausibel hoher Wert für mRNA-spezifische CORDIS-Publikationen – ohne Detail-Panel nicht verifizierbar. |

**Ampel-Bilanz:** 0 × 🟢 · 0 × 🟡 · 13 × 🔴

---

## Metakritik: Ist die "Reife/Rückläufig"-Aussage für mRNA überhaupt plausibel?

Selbst wenn der Dump vollständig wäre, wäre die Kennzeichnung "Phase: Reife · Rückläufige Entwicklung" für mRNA ein Alarmzeichen:
- mRNA-Therapeutika/-Impfstoffe sind seit der COVID-Welle 2020–2022 in einer **Post-Peak-Konsolidierung** – eine einzelne Ausreißerkurve 2020/21 kann eine Logistik-S-Kurve fälschlich als "Declining" klassifizieren, obwohl die Technologieplattform strukturell erst am Anfang der Anwendung außerhalb von Infektiologie steht (Onkologie, Protein-Replacement).
- Ohne R²-, Jahresachsen- und Zeitraum-Angabe ist dieses Urteil für einen Entscheider nicht nachvollziehbar, aber hochgradig **handlungsrelevant** (Investitions-vs-Desinvestitions-Signal).

---

## Entscheider-Perspektive: "Würde ich diesem Panel trauen?"

**Für welche Entscheidungen ist das TI-Radar bei mRNA brauchbar?**
- *Aktuell (auf Basis dieses Dumps): für keine Entscheidung.* Ein Entscheider sieht einen Header mit fünf Aggregatzahlen und fünf Qualitäts-Labels ohne eine einzige nachlesbare Detail-Metrik. Er kann weder HHI noch Top-Akteure, Länder, Disziplinen, Grant-Rate oder h-Index prüfen.

**Für welche Entscheidungen ist das Radar gefährlich?**
- **Hochgradig gefährlich für Portfolio-Entscheidungen:** Das Label "Reife / Rückläufige Entwicklung" + "€446 M Förderung" + "Sehr hoher Forschungsimpact" liest sich als "etabliert, aber schrumpft – abwickeln oder Position verteidigen". Für eine Plattform-Technologie mit großem Anwendungspotenzial außerhalb von Impfstoffen (Onkologie, Autoimmun, seltene Erkrankungen) ist dieses Narrativ potenziell *strategisch irreführend* – und es wird im Dashboard *ohne* statistische Belege (R², Jahresspanne, Fit-Qualität) prominent ausgestellt.
- **Gefährlich für Förder-/Grant-Entscheidungen:** "€446 M" Gesamtvolumen ohne zeitliche oder thematische Aufschlüsselung verleitet zur Extrapolation ("Markt gesättigt mit Förderung"), während die eigentlich interessanten Sub-Schwerpunkte (Onkologie-mRNA, Delivery-Systeme/LNPs, Self-Amplifying mRNA) im Detail-UC4 verborgen bleiben.

**Technische Ursache-Hypothese für den leeren Dump:** Die `activeTab: "Neue Analyse"`-Markierung in **allen 13** Panels legt nahe, dass der Scrape jeweils die Cluster-Auswahlseite erfasste, statt die aktivierten Tab-Inhalte – entweder durch einen Navigations-Bug (Tab-Klick wurde nicht registriert), einen Race mit asynchronem Datenladen, oder weil mRNA-Panels für einige UCs serverseitig tatsächlich leer zurückkommen und die UI auf die Cluster-Landingpage zurückfällt. Ohne zweiten Scrape-Durchlauf lässt sich (a) vs. (b) vs. (c) nicht entscheiden – diese Differenzierung ist aber für die Gesamtbewertung des Radars entscheidend.

---

## Kurzfazit

Für mRNA liefert das TI-Radar im vorliegenden Dump **ausschließlich die Executive-Summary-Kopfzeile**; alle 13 UC-Panels sind inhaltlich leer. Damit erfüllt **kein einziger** UC sein Versprechen, und das prominente Header-Narrativ ("Reife / Rückläufige Entwicklung") ist nicht auditierbar und für eine strategisch wichtige Plattform-Technologie potenziell irreführend.
