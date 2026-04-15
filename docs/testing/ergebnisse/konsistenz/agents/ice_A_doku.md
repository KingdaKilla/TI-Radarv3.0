# Konsistenz-Audit TI-Radar v3 · Rolle A (Dokumentierer)

**Technologie:** internal combustion engine
**Input:** `docs/testing/ergebnisse/konsistenz/raw/raw3_ice.json`
**Datum:** 2026-04-14

---

## Header-KPIs (Executive Summary, wörtlich)

| KPI | Wert laut Header |
|---|---|
| Patente | **10.2K** |
| EU-Projekte | **48** |
| Publikationen | **0** |
| Phase | **Reife + Rückläufige Entwicklung** (Doppel-Label) |
| Wettbewerb | **Wettbewerbsintensiver Markt** |
| Förderung | **€160M** |
| Forschungsimpact | **Moderater Forschungsimpact** |
| Aktiver Cluster (sichtbarer Teil) | „Geographische Perspektive" (UC6) |

Header-Auszug (wörtlich):
> „INTERNAL COMBUSTION ENGINE Technologie-Intelligence Analyse 10.2K Patente 48 EU-Projekte 0 Publikationen Phase: Reife Rückläufige Entwicklung Wettbewerbsintensiver Markt €160M Förderung Moderater Forschungsimpact …"

---

## UC-Metriken-Tabelle

| Tab | UC | Kern-Metriken (aus `panelText`) | Jahresachse | Warnhinweis |
|---|---|---|---|---|
| Aktivitätstrends | UC1 | Patente-CAGR **-7,6 %**; Projekte-CAGR **-8,3 %**; Top-CPC: Y02T10/12 (13.115), Y02T10/40 (6.826), Y02T10/30 (2.425), F02D41/0007 (2.110), F02D2200/101 (1.617) | 2017–2026 | ja |
| S-Kurve & Reife | UC2 | Phase: **Reife**; **R² = 0,999**; Wendepunkt **2014**; Konfidenz **95 %** | 2016–2026 | ja |
| Technologiekonvergenz | UC5 | **10 CPC-Klassen**; Ø Jaccard **0,234**; **9 Whitespace-Lücken**; CPC-Set: Y02T, F02D, F02B, F02M, F01N, F02F, F01L, F02P, F01M, F01P | — | nein |
| Wettbewerb & HHI | UC3 | **Niedrige Konzentration**; Top-Anmelder: Fraunhofer Austria, Agencia Estatal C…, Uniresearch BV, TU …, Sveuciliste u Zag…, NRG Pallas BV, Scandinaos AB, FEV Europe GmbH; Skala 0–36 | — | nein |
| Dynamik & Persistenz | UC8 | **30 Akteure**; **Schrumpfend (-320 netto)**; Reihen: Persistente / Neue / Ausgeschiedene; Skala 0–1000 | 2016–2026 | ja |
| Akteurs-Typen | UC11 | **270 Akteure**; Dominiert: **KMU/Unternehmen**; Typen: KMU/Unternehmen, Higher Education, Research Organisation, Other, Public Body | — | nein |
| Förderung | UC4 | **Gesamt: 159,6 Mio. EUR**; **48 Projekte**; Instrumente: RIA, IA, HORIZON-IA, HORIZON-RIA, MSCA-ITN, SME-2, HORIZON-EIC-A…, HORIZON-TMA-M… | — | nein |
| Forschungsimpact | UC7 | **100 Publikationen**; **71,6 Zitate/Pub.**; **15 Institutionen**; Skalen 0–24 (Pub.) / 0–2600 (Zit.) | 2018–2025 | ja |
| Publikationen | UC13 | **57,7 Pub/Projekt**; **DOI 13 %**; Skala 0–600 | 2016–2024 | nein |
| Geographie | UC6 | **10 Länder**; Top: **Deutschland**; Reihenfolge: DE, SE, IT, UK, FR, AT, DK, CH, FI, PL; Skala 0–8000 | — | nein |
| Tech-Cluster | UC9 | **3 Cluster**; **92 Akteure**; **187 CPC-Klassen**; Sections B, F, Y | — | nein |
| EuroSciVoc | UC10 | **1 Feld**; **58 Projekte**; Dominantes Feld: **chemical engineering**; Shannon-Index **5,15** | — | nein |
| Patenterteilung | UC12 | **Quote 27,6 %**; **37,9 Monate bis Erteilung**; **30.554 Anmeldungen**; **8.435 Erteilungen**; Skala 0–6000 | 2016–2026 | ja |

---

## Panels mit Warnhinweis „Daten ggf. unvollständig"

- UC1 (Aktivitätstrends) – Achse bis 2026
- UC2 (S-Kurve & Reife) – Achse bis 2026
- UC8 (Dynamik & Persistenz) – Achse bis 2026
- UC7 (Forschungsimpact) – Achse bis 2025
- UC12 (Patenterteilung) – Achse bis 2026

## Panels **ohne** Warnhinweis (trotz ggf. unvollständiger Jahre)

- UC13 (Publikationen) – Achse bis 2024, kein Hinweis
- UC5, UC3, UC11, UC4, UC6, UC9, UC10 – keine Zeitachse bzw. ohne Warnhinweis

---

## Auffällige Jahresachsen-Inkonsistenz

| Panel | Endjahr |
|---|---|
| UC1, UC2, UC8, UC12 | **2026** |
| UC7 | **2025** |
| UC13 | **2024** |

Drei unterschiedliche Endjahre im selben Dashboard.

---

## Beobachtete Doppelphase / widersprüchliche Labels

- **Header:** „Phase: Reife Rückläufige Entwicklung" (zwei Phasen kombiniert)
- **UC2-Panel:** nur „Phase: **Reife**" (einzelne Phase)
- **Header:** „Wettbewerbsintensiver Markt"
- **UC3-Panel:** „**Niedrige Konzentration**" (gegenteilige Aussage)

---

## Zahlen-Divergenzen (Header ↔ UC-Panel, ohne Bewertung)

| Größe | Header | UC-Detail |
|---|---|---|
| Publikationen | 0 | 100 (UC7) |
| Projekte | 48 | 48 (UC4) · **58 (UC10)** |
| Förderung | €160M | 159,6 Mio. EUR (UC4) |
| Phase | Reife + Rückläufig | Reife (UC2) |
| Wettbewerb | intensiv | niedrige Konzentration (UC3) |

---

## Quellen-/Latenz-Stempel

Alle 13 Panels tragen den Stempel **„Nachvollziehbarkeit … | 31,2 s"** (1 bzw. 2 Quellen) – identische Latenz über sämtliche UCs.

---

## Kuriositäten

- **UC13 „57,7 Pub/Projekt"** bei gleichzeitigem Header „0 Publikationen" und UC7 „100 Publikationen": 57,7 × 48 ≈ 2.770 erwartete Publikationen – passt weder zu 0 noch zu 100.
- **UC10** mit nur **1 Feld** („chemical engineering") erreicht trotzdem einen **Shannon-Index 5,15** – bei einem einzigen Feld mathematisch = 0, also plausibilitätsfragwürdig.
- **UC10 Projektzahl 58** vs. Header/UC4 **48** – Abweichung 10 Projekte.
- **UC2 Wendepunkt 2014** bei Achse 2016–2026: Wendepunkt liegt vor Beginn der Zeitreihe.
- **UC3 Top-Liste** enthält mit „Fraunhofer Austria", „Uniresearch BV", „NRG Pallas BV", „Scandinaos AB" überwiegend kleine/mittlere Forschungseinrichtungen – für 10.200 Patente eher unerwartet (deutet auf Projekt-Teilnehmer statt Patentanmelder hin).
- **UC1 CAGR -7,6 %** + **UC2 Phase „Reife"** + Header „Rückläufige Entwicklung" stimmen untereinander überein, aber Header-Doppellabel widerspricht UC2-Einzellabel.

---

## Zusammenfassung der Beobachtung

Das Dashboard liefert für ICE reichhaltige UC-Zahlen, doch die Header-Kachel weicht in **Publikationen (0 vs. 100)**, **Phase (Doppel vs. Einzel)** und **Wettbewerb (intensiv vs. niedrig)** vom Detail ab. Zusätzlich existieren **drei verschiedene Jahresend-Achsen** (2024/2025/2026), ein **UC10-Shannon-Index von 5,15 bei nur einem Feld** und eine **Projekt-Divergenz 48 vs. 58** zwischen Header/UC4 und UC10.
