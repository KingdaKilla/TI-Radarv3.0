# Agent C (Interpreter) – Internal Combustion Engine

**Input:** `raw3_ice.json` · **Rolle:** Interpreter · **Datum:** 2026-04-14

## Header-Kern (Ausgangslage)

`10.2K Patente · 48 EU-Projekte · 0 Publikationen · Phase: Reife Rückläufige Entwicklung · Wettbewerbsintensiver Markt · €160M Förderung · Moderater Forschungsimpact`

Doppel-Phase („Reife" + „Rückläufige Entwicklung"), „0 Publikationen" im Header trotz konkreter Pub-Zahlen in UC7/UC13 und Widerspruch „Wettbewerbsintensiv" (Header) vs. „Niedrige Konzentration" (UC3) sind schon hier klar erkennbar.

## UC-by-UC – Versprechen vs. Lieferung

| UC | Versprechen | Tatsächlich geliefert | Ampel | Begründung |
|---|---|---|---|---|
| UC1 Aktivitätstrends | Patent/Projekt/Pub-Trend + CAGR | Patente CAGR −7,6 %, Projekte CAGR −8,3 %, Achse 2017–2026 mit „Daten ggf. unvollständig", Top-CPCs inkl. Y02T10/12 (13.115) | 🟡 | Zahlen da, aber CAGR bezieht angebrochene Jahre 2025/2026 mutmaßlich ein → verzerrt negativ; Publikationstrend fehlt hier (nur Patente/Projekte). |
| UC2 S-Kurve & Reife | Sigmoid-Fit mit R², Wendepunkt, Konfidenz, einer Phase | Phase „Reife", R²=0,999, Wendepunkt 2014, Konfidenz 95 %, Achse bis 2026 | 🟢 | Solider Fit auf 10K-Patente-Basis; Phase hier eindeutig (nur „Reife"), also Header-Doppel-Phase ist reiner Header-Artefakt. |
| UC5 Technologiekonvergenz | CPC-Kookkurrenz + Whitespace | 10 CPC-Klassen, Ø Jaccard 0,234, 9 Whitespace-Lücken, Klassen Y02T…F01P | 🟢 | Konkrete Zahlen + plausible CPC-Liste (Motor-Verbrennungs-Familie), interpretierbar. |
| UC3 Wettbewerb & HHI | HHI + Top-Anmelder | „Niedrige Konzentration", Top-Liste mit Fraunhofer, Agencia Estatal, Uniresearch … (bis max ~36) | 🔴 | Widerspruch zum Header („Wettbewerbsintensiv"); zudem Top-Liste wirkt wie EU-Projekt-Konsortien, nicht wie klassische ICE-Patentanmelder (Bosch, Toyota, Denso fehlen). HHI-Zahl selbst wird nicht ausgewiesen. |
| UC8 Dynamik & Persistenz | Neue/Persistente/Ausgeschiedene | 30 Akteure, „Schrumpfend (−320 netto)", Achse 2016–2026 | 🟡 | Netto-Zahl plausibel zur Rückgangsphase, aber „30 Akteure" steht im krassen Missverhältnis zu „−320 netto" – Skala unklar; 2025/2026 zählt mit. |
| UC11 Akteurs-Typen | HES/PRC/PUB/KMU-Breakdown | 270 Akteure, „Dominiert: KMU / Unternehmen", Kategorien gelistet | 🟡 | Nur Dominanz-Label, keine Prozentanteile/Summenprüfung möglich; 270 ≠ 30 (UC8) ≠ 92 (UC9) – Akteurs­zahlen divergieren über die UCs. |
| UC4 Förderung | CORDIS-Fördervolumen + Instrumente | 159,6 Mio. €, 48 Projekte, Instrumente RIA/IA/HORIZON-IA/MSCA-ITN/SME-2 | 🟢 | Stimmig mit Header (€160M, 48 Projekte), Instrumentenmix nachvollziehbar. |
| UC7 Forschungsimpact | h-Index/Zitationen/Top-Institutionen | 100 Publikationen, 71,6 Zit./Pub., 15 Institutionen, Achse 2018–2025 | 🟡 | Zitate/Pub hoch (71,6) → Impact-Label „Moderat" passt nicht; h-Index wird nicht genannt; 100 Pubs widersprechen Header-„0 Publikationen". |
| UC13 Publikationen | Pub/Projekt + DOI-Anteil | 57,7 Pub/Projekt, DOI 13 %, Achse 2016–2024 | 🔴 | Rechnung: 57,7 × 48 ≈ 2.770 Publikationen – widerspricht sowohl UC7 (100) als auch Header (0). Pub/Projekt-Kennzahl unplausibel hoch. |
| UC6 Geographie | Länderverteilung + Kollaboration | 10 Länder, Top Deutschland, Liste DE/SE/IT/UK/FR/AT/DK/CH/FI/PL | 🟢 | Plausibel (ICE-Heartland Deutschland/Schweden), Kollaborationsmuster selbst wird aber nicht gezeigt. |
| UC9 Tech-Cluster | 5-dim Profil | 3 Cluster, 92 Akteure, 187 CPC-Klassen, CPC Section B/F/Y | 🟡 | Dimensionen (Aktivität/Vielfalt/Dichte/Kohärenz/Wachstum) werden benannt, aber keine Zahlenwerte dazu im Panel-Snippet. |
| UC10 EuroSciVoc | Disziplin-Taxonomie | **1 Feld**, 58 Projekte, „chemical engineering", Shannon 5,15 | 🔴 | Nur 1 Feld zugeordnet + Shannon 5,15 ist mathematisch unmöglich (ln(1)=0). „chemical engineering" ist zudem unpassend für Verbrennungsmotor (erwartet: mechanical/automotive engineering). Auch: 58 Projekte ≠ 48 Header-Projekte. |
| UC12 Patenterteilung | Grant-Rate + Time-to-Grant | Quote 27,6 %, 37,9 Mon., 30.554 Anmeldungen, 8.435 Erteilungen, Achse bis 2026 | 🔴 | Nachrechnung: 8.435/30.554 = **27,6 %** ✓ – aber 30.554 Anmeldungen widersprechen Header-„10.2K Patente" um Faktor ~3. Entweder Header zählt Familien, UC12 Einzelanmeldungen – ohne Kennzeichnung irreführend. |

## Zählerei-Quercheck (drei Zahlen, die gleich sein müssten)

| Kennzahl | Wert |
|---|---|
| Header Patente | 10.200 |
| UC12 Anmeldungen | 30.554 |
| UC12 Erteilungen | 8.435 |
| Header Projekte | 48 |
| UC4 Projekte | 48 ✓ |
| UC10 Projekte | 58 ✗ |
| Header Publikationen | 0 |
| UC7 Publikationen | 100 |
| UC13 implizit (57,7 × 48) | ≈ 2.770 |
| Akteure UC8 | 30 |
| Akteure UC9 | 92 |
| Akteure UC11 | 270 |

Drei getrennte Akteurs-Zählungen, drei getrennte Publikations-Zählungen, zwei getrennte Projekt-Zählungen, zwei getrennte Patent-Zählungen. Jede UC-Metrik ist für sich plausibel, aber die Bezugssysteme werden nirgends offengelegt.

## Für welche Entscheidungen brauchbar, für welche gefährlich?

**Brauchbar (🟢):**
- **Reife-Einschätzung** (UC2): R²=0,999, Wendepunkt 2014 – ICE ist klar in Reifephase, hervorragende Datenbasis für Strategie-Entscheidungen „Exit vs. Defensive".
- **Förderlandschaft** (UC4): €159,6M auf 48 Projekte, Instrumentenmix – solide Grundlage für Horizon-Europe-Anträge.
- **CPC-Landscape** (UC5, UC9): Cross-Tech-Verbindungen und Cluster-Struktur nachvollziehbar, brauchbar für Patent-Freedom-to-Operate und Whitespace-Scouting.
- **Geographische Top-10** (UC6): Passt zum Industriebild, nutzbar für Lokations-Screening.

**Gefährlich (🔴):**
- **Wettbewerbs-Bewertung** (UC3): Header sagt „wettbewerbsintensiv", Panel sagt „niedrige Konzentration" – ein Budget-Entscheider, der auf den Header schaut, trifft die entgegengesetzte Markteintritts-Entscheidung wie einer, der ins Panel klickt. Top-Anmelder-Liste wirkt zudem EU-förder-verzerrt (fehlende OEM-Giganten Bosch/Toyota/Denso).
- **Publikationsbasis** (UC7/UC13 vs. Header): Diskrepanz 0 / 100 / 2.770 – jede Impact- oder Forschungskollaborations-Entscheidung auf Basis des Dashboards ist Lotterie.
- **Wissenschaftsdisziplin** (UC10): „chemical engineering" mit Shannon 5,15 bei 1 Feld ist schlicht falsch – wer auf EuroSciVoc-Klassifikation vertraut, landet im falschen Programm.
- **Patent-Volumen** (Header 10,2K vs. UC12 30,5K): Faktor 3 ohne Erklärung – für Portfolio-Due-Diligence unbrauchbar.
- **CAGR** (UC1): −7,6 %/−8,3 % sind mit unvollständigem 2025/2026 vermutlich überzeichnet; Investitionsentscheidungen sollten auf bereinigter Reihe basieren.

## Fazit

Das ICE-Dashboard liefert **technisch saubere Einzelpanels** (S-Kurve, Förderung, Geographie sind Spitze), aber **die Integrationsebene kollabiert**: Header-KPIs, Akteurszahlen und Projekt-/Publikations-Zählungen stammen aus unverbundenen Pipelines. Für strategisches Screening „Ist ICE reif?" absolut brauchbar; für jede Entscheidung, die **konsistente absolute Zahlen** benötigt (Wettbewerb, Publikations-Impact, Patent-Volumen), irreführend.

**Budget-Entscheider-Urteil:** Vertrauen in Einzelpanels ja, Vertrauen in den Header nein – und ohne Querverweis zwischen UCs produziert das Dashboard widersprüchliche Narrative.
