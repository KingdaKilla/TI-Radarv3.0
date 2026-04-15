# Rolle C · Interpreter — Technologie: perovskite solar cell

**Datum:** 2026-04-14
**Quelle:** `docs/testing/ergebnisse/konsistenz/raw/raw_perovskite.json`

## Header (Executive-Summary, laut Dashboard)

| Feld | Wert |
|---|---|
| Patente | **101** |
| EU-Projekte | **140** |
| Publikationen | **0** |
| Phase | **Reife** |
| Trend | **Rückläufige Entwicklung** |
| Markt | **Wettbewerbsintensiver Markt** |
| Förderung | **€222M** |
| Impact-Label | **Hoher Forschungsimpact** |

## Vorbemerkung — Kritischer Befund zum Rohmaterial

In der Input-JSON ist für **alle 13 Panels** `activeTab = "Neue Analyse"` und `mainText` zu 100 % **identisch** — nämlich die Executive-Summary-Kopfzeile plus die statischen Cluster-Info-Boilerplate-Texte (`UC6 … UC9 … UC10 … UC12 … UC1 … UC2 … UC5 … UC3 … UC8 … UC11 … UC4 Förderungsanalyse`, jeweils mit "Dieser Analysebereich umfasst:" und "Klicken zum Zurueck").

**Konsequenz:** Beim Live-Dashboard-Durchlauf wurde für perovskite solar cell **kein einziges Detail-Panel** tatsächlich gerendert. Sichtbar waren ausschließlich die 4 Cluster-Kacheln der Landing-Seite (Geographische Perspektive, Technologie & Reife, Marktakteure, Forschung & Förderung) mit ihren generischen UC-Beschreibungen. Der Nutzer hat dadurch de facto **keinen** der 13 UCs betreten — oder das Dashboard hat die Panels für diese Tech nicht geladen.

Für diese Interpreter-Analyse bedeutet das: Die Bewertung "liefert" bezieht sich auf **das, was an sichtbaren Daten zur Technologie übrig bleibt**, nämlich die Header-KPIs. Alle tiefergehenden UC-Versprechen (HHI, CAGR, R², h-Index, Top-Länder, Grant-Rate, S-Kurven-Fit …) sind **nicht beobachtbar**.

## UC-für-UC Bewertung

| UC | Versprechen (Cluster-Info) | Was das Dashboard liefert | Ampel | Begründung |
|---|---|---|---|---|
| **UC1** Technologie-Landschaft | Patent-/Projekt-/Publikations-Zeitreihen, CAGR, Dynamik-Urteil | Nur Header: "101 Patente · 140 EU-Projekte · 0 Publikationen · Rückläufige Entwicklung". Keine Zeitreihe, kein CAGR-Wert, kein Jahresraster sichtbar. | 🔴 | Kerndimension (Zeitverlauf) fehlt vollständig; "Rückläufig" als Floskel ohne Zahl. |
| **UC2** Reifegrad-Analyse | S-Kurven-Fit, Reife-Phase (Emerging/Growth/Mature/Declining), Einstiegszeitpunkt | Header-Badge "Phase: Reife" + "Rückläufige Entwicklung". Kein R², keine Fit-Kurve, kein Saturation-Level, kein Endjahr. | 🔴 | Phase-Label ohne statistische Basis — für eine Technologie, die 2020–2024 real im Labor einen PCE-Boom hatte, ist das Label "Reife + rückläufig" nicht nachvollziehbar gemacht. |
| **UC5** Cross-Tech Intelligence | CPC-Konvergenz, Whitespace-Lücken | Nichts. Panel nicht gerendert. | 🔴 | Kerndimension komplett fehlend. |
| **UC3** Wettbewerb & HHI | HHI-Wert, dominante Akteure | Header-Claim "Wettbewerbsintensiver Markt" (typisch HHI < 1500) ohne HHI-Zahl oder Top-Anmelderliste. | 🔴 | Label ohne Beleg; für Budgetentscheidung wertlos. |
| **UC8** Dynamik & Persistenz | Neue Einsteiger / Persistente / Ausgeschiedene | Nichts. Panel nicht gerendert. | 🔴 | Kerndimension komplett fehlend. |
| **UC11** Akteurs-Typen | Breakdown Hochschule/Forschung/Industrie/öffentlich | Nichts. Panel nicht gerendert. | 🔴 | Kerndimension komplett fehlend. |
| **UC4** Förderungsanalyse | EU-Fördervolumen nach Forschungsgebiet + Zeitverlauf | Header: "€222M Förderung" + "140 EU-Projekte". Kein Zeitverlauf, keine Forschungsgebiet-Aufteilung, keine Top-Projekt-/Programm-Liste. | 🟡 | Gesamtvolumen und Projektzahl sind nennbare Zahlen — Durchschnitt ≈ €1,6 M/Projekt ist plausibel für Horizon. Versprochene Detaildimensionen (Gebiet, Zeit) fehlen aber komplett. |
| **UC7** Forschungsimpact | h-Index, Zitationsraten, Top-Institutionen | Nur Header-Label "Hoher Forschungsimpact". Kein h-Index-Wert, keine Zitationsrate, keine Instituts-Top-Liste. | 🔴 | Selbstwiderspruch mit Publikations-Zahl (siehe UC13): Impact ohne Publikationen ist nicht belegbar. |
| **UC13** Publikations-Impact | CORDIS-Publikationen × Projekte, Pub/Project-Effizienz | Header: **"0 Publikationen"**. Panel selbst nicht gerendert. | 🔴 | Kritisch: 0 Publikationen bei 140 EU-Projekten und "Hohem Forschungsimpact" ist entweder ein Datenlücken-Artefakt (CORDIS-Pubs nicht verlinkt) oder ein echtes Defizit — so wie dargestellt: wertlos und widersprüchlich. |
| **UC6** Geographie | Globale Verteilung Anmelder/Organisationen, Top-Länder | Nichts. Panel nicht gerendert. | 🔴 | Kerndimension komplett fehlend — keine Länder, kein EU-Share. |
| **UC9** Tech-Cluster | 5-dim Profil (Aktivität, Vielfalt, Dichte, Kohärenz, Wachstum) | Nichts. Panel nicht gerendert. | 🔴 | Kerndimension komplett fehlend. |
| **UC10** EuroSciVoc | Wissenschaftsdisziplinen-Mapping | Nichts. Panel nicht gerendert. | 🔴 | Kerndimension komplett fehlend. |
| **UC12** Erteilungsquoten | Grant-Rate + Time-to-Grant | Nichts. Panel nicht gerendert. Header sagt nur "101 Patente" ohne Erteilungs-Status. | 🔴 | Kerndimension komplett fehlend; bei 101 Patenten wäre eine Grant-Rate technisch berechenbar. |

**Bilanz:** 12 × 🔴 · 1 × 🟡 · 0 × 🟢

## Logische Widersprüche im Header selbst (auch ohne Detail-Panels erkennbar)

1. **"Hoher Forschungsimpact" vs. "0 Publikationen"**: Impact ohne Publikationen ist definitorisch nicht messbar (h-Index, Zitationen setzen Pubs voraus). Entweder ist "Hoher Forschungsimpact" eine generische Floskel unabhängig von der tatsächlichen Datenlage, oder "0 Publikationen" ist ein Datenpipeline-Bug (fehlende CORDIS-Pub-Verknüpfung bei Perovskite).
2. **"Phase: Reife" + "Rückläufige Entwicklung"** bei einer Technologie mit 140 aktiven EU-Projekten und €222 M Förderung ist fachlich schwer haltbar — Perovskit-Solarzellen sind 2024/2025 einer der aktivsten Förderbereiche (PCE-Rekorde, Tandemzellen-Kommerzialisierung). Das passt eher zu einem artifakt-behafteten Fit (siehe Briefing-Hinweis: unvollständige Jahre 2025/2026 verzerren S-Kurve massiv).
3. **"Wettbewerbsintensiver Markt"** bei nur 101 Patenten ist ein niedriger Grundwert — die Aussage ist ohne HHI-Zahl nicht falsifizierbar.

## Entscheider-Urteil — Wofür ist dieses Radar bei perovskite solar cell brauchbar?

**Brauchbar für … (mit Vorsicht):**
- Grobe Größenordnung des EU-Förder-Engagements: €222 M / 140 Projekte als Orientierung, dass das Feld aktiv gefördert wird.

**Gefährlich / unbrauchbar für … :**
- **Jede Investitions- oder Portfolio-Entscheidung.** Das Phase-Label "Reife + rückläufig" ist in der öffentlichen Wahrnehmung ein starkes Negativsignal ("aussteigen") — ohne statistische Belege (S-Kurve, R², Zeitreihe) wäre das aber eine gefährliche Fehlleitung. Reale Entwicklung der Technologie (Rekord-Effizienzen 2024, Tandem-Zellen Richtung Markt) ist im Dashboard nicht abgebildet.
- **Wettbewerbs-Screening:** Kein HHI, keine Top-Anmelder, keine Länder — man weiß nicht, ob man gegen chinesische Konzerne, EU-Konsortien oder Start-ups antreten würde.
- **Partner-Suche / Clustering:** Kein Akteurs-Typen-Breakdown, keine Top-Institutionen, keine Geo-Top-3.
- **Patent-Strategie:** Keine Grant-Rate, keine Time-to-Grant, keine CPC-Klassen — keine Basis für Anmeldeentscheidung.
- **Forschungsimpact-Nachweis:** Header-Label "Hoch" ohne h-Index bei gleichzeitig "0 Publikationen" — unglaubwürdig.

## Gesamtfazit

Für **perovskite solar cell** ist das Radar in der aktuellen Form **nicht entscheidungsreif**. Das Dashboard liefert beobachtbar nur die Executive-Summary-Zeile; sämtliche 13 Detail-Panels sind im Dump nicht gerendert (entweder Dashboard-Lade-Fehler oder der Erfassungs-Durchlauf hat die Panels nicht aktiviert). Selbst wenn nur der Header betrachtet wird, sind 3 Header-Felder in sich widersprüchlich ("Hoher Impact" ↔ "0 Publikationen", "Reife + rückläufig" ↔ €222 M + 140 aktive Projekte). Empfehlung: Vor jeder Nutzung dieser Kachel muss (a) die Panel-Rendering-Pipeline für Perovskite-Tech verifiziert, (b) die Publikations-Verknüpfung zu CORDIS geprüft, und (c) die S-Kurven-Berechnung auf Endjahr-Cutoff (nur vollständige Jahre ≤ 2024) geprüft werden.
