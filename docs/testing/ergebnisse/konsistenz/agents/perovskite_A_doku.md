# Konsistenz-Audit Agent A (Dokumentierer) - Perovskite Solar Cell

**Technologie:** perovskite solar cell
**Datum:** 2026-04-14
**Input:** `raw3_perovskite.json`

## Header-Kern-KPIs (Executive Summary)

| KPI | Wert laut Header |
|---|---|
| Patente | 101 |
| EU-Projekte | 140 |
| Publikationen | 0 |
| Phase | Reife Rückläufige Entwicklung (Doppel-Phase) |
| Wettbewerb | Wettbewerbsintensiver Markt |
| Förderung | €222M |
| Impact-Label | Hoher Forschungsimpact |

Header-Originalzeile: „PEROVSKITE SOLAR CELL Technologie-Intelligence Analyse 101 Patente 140 EU-Projekte 0 Publikationen Phase: Reife Rückläufige Entwicklung Wettbewerbsintensiver Markt €222M Förderung Hoher Forschungsimpact …"

Der Header beginnt danach unmittelbar mit der UC6-Panel-Beschreibung („Geographische Perspektive …"), d. h. der sichtbare Kopfbereich führt direkt in den aktuell aktiven Tab über.

## UC-Tabelle: Kern-Metriken je Panel

| UC | Tab | Kern-Metriken (Panel-Text) | Jahresachse |
|---|---|---|---|
| UC1 | Aktivitätstrends | Patente CAGR 4.1 %; Projekte CAGR 9.8 %; TOP CPC: Y02E10/549 (5.076), H10K30/50 (2.035), H10K71/12 (1.750), H10K85/50 (1.708), H10K30/40 (1.281); y-Achse -120 % … +120 % | 2017-2026 |
| UC2 | S-Kurve & Reife | Phase: Reife; R² = 1.000; Wendepunkt 2021; Konfidenz 82 %; y-Achse 0-80 | 2016-2026 |
| UC5 | Technologiekonvergenz | 10 CPC-Klassen; Ø Jaccard 0.198; 10 Whitespace-Lücken; CPC: Y02E, H10K, Y02P, H10F, H01G, C07F, C23C, C07D, B82Y, C07C | - |
| UC3 | Wettbewerb & HHI | „Niedrige Konzentration"; Top-Anmelder (ohne HHI-Zahl): Fraunhofer Austria, Saule Spolka Akcyjna, Universitat Jaume, Agencia Estatal CSIC, Fundacio Institut, University of Stuttgart, Dyenamo AB, Solaveni GmbH; Patente+Projekte dargestellt | - |
| UC8 | Dynamik & Persistenz | 9 Akteure; „Schrumpfend (-70 netto)"; Reihen: Persistente/Neue/Ausgeschieden; y-Achse 0-100 | 2016-2026 |
| UC11 | Akteurs-Typen | 280 Akteure; dominiert: Higher Education; Kategorien: HES, KMU/Unternehmen, Research Organisation, Other, Public Body | - |
| UC4 | Förderung | Gesamt 221.8 Mio. EUR; 140 Projekte; Instrumente: HORIZON-RIA, RIA, HORIZON-IA, HORIZON-ERC, ERC-STG, IA, HORIZON-EIC, HORIZON-…, MSCA-IF, ERC-COG, MSCA-ITN, HORIZON-…, ERC-ADG | - |
| UC7 | Forschungsimpact | 100 Publikationen; 363.5 Zitate/Pub.; 15 Institutionen; Doppelachse Pubs (0-20) + Zitationen (0-8000) | 2016-2024 |
| UC13 | Publikationen | 21.3 Pub/Projekt; DOI 56 %; y-Achse 0-800 | 2016-2024 |
| UC6 | Geographie | 10 Länder; Top: Deutschland; danach Schweiz, UK, Italien, Spanien, Frankreich, Niederlande, Polen, Belgien, Schweden; x-Achse 0-60 | - |
| UC9 | Tech-Cluster | 5 Cluster; 39 Akteure; 118 CPC-Klassen; 5-dim-Profil: Patente, Akteure, Dichte, Kohärenz, Wachstum; Sections B, C, G, H, Y | - |
| UC10 | EuroSciVoc | 1 Feld; 134 Projekte; Shannon-Index 4.87; dominant „nanotechnology 134 Projekte" (100 %), restliche Einträge 0 %/1 % | - |
| UC12 | Patenterteilung | Quote 9.3 %; 28.1 Monate bis Erteilung; 5.462 Anmeldungen; 506 Erteilungen; Doppelachse Anmeldungen/Erteilungen (0-1200) + Quote 0-100 % | 2016-2026 |

## Panels mit Warnhinweis „Daten ggf. unvollständig"

- UC1 (Aktivitätstrends)
- UC2 (S-Kurve & Reife)
- UC8 (Dynamik & Persistenz)

Kein Warnhinweis (trotz Jahresachse bis 2026) in UC12 (Patenterteilung); kein Hinweis in UC7/UC13, dort endet die Achse jedoch bereits 2024.

## Auffällige Beobachtungen (nur deskriptiv)

- Header nennt **„0 Publikationen"**, UC7 meldet hingegen **100 Publikationen** mit 363.5 Zitaten/Pub. und UC13 meldet **21.3 Pub/Projekt bei 140 Projekten** (rechnerisch ≈ 2.982 Publikationen). Drei voneinander abweichende Publikationszahlen im selben Dashboard.
- Header nennt **„Phase: Reife Rückläufige Entwicklung"** (zwei Phasen), UC2 selbst zeigt nur eine Phase: **„Reife"**.
- Header-KPI **101 Patente** vs. UC12 **5.462 Anmeldungen / 506 Erteilungen** - Größenordnungen weichen deutlich voneinander ab.
- Header-Label **„Wettbewerbsintensiver Markt"** vs. UC3 **„Niedrige Konzentration"**.
- UC2 **R² = 1.000** bei gleichzeitig nur 82 % Konfidenz und Hinweis „Daten ggf. unvollständig" - mathematisch grenzwertig (perfekter Fit trotz Unsicherheitswarnung).
- Header **140 EU-Projekte** vs. UC10 **134 Projekte** - Differenz von 6 Projekten zwischen Kopf und Taxonomie-Panel.
- UC10 zeigt **nur ein einziges Feld** („nanotechnology"), dennoch wird **Shannon-Index 4.87** ausgewiesen (bei 1 Feld wäre Shannon = 0). Zusätzlich stehen Platzhalterzeilen mit „0 %" und „1 %" ohne zugehörigen Feldnamen.
- UC8 meldet **9 Akteure** mit Nettoabfluss -70 - die Größenordnung ist inkonsistent, ein Nettoverlust von 70 aus einer Basis von 9 ist unplausibel.
- UC11 meldet **280 Akteure**, UC9 meldet **39 Akteure**, UC8 meldet **9 Akteure**, UC3 zeigt **8 Top-Anmelder** - je nach Panel stark variierende Akteurszahlen.
- Jahresachsen uneinheitlich: UC1/UC2/UC8/UC12 bis **2026**, UC7/UC13 nur bis **2024**.
- UC4: Instrumenten-Label „HORIZON-…" erscheint zweimal als abgeschnittener Text - Listendarstellung unvollständig.
- UC5 listet **10 CPC-Klassen und gleichzeitig 10 Whitespace-Lücken** - Zahlen identisch, was auf ein Labeling-Artefakt hindeuten könnte.

## Meta

- Alle Panels meldeten Nachvollziehbarkeit (1-2 Quellen, durchgehend 5.9 s Ladezeit).
- Aktiver Tab laut JSON: UC6 Geographie (Header-Text geht direkt in UC6-Panel über).
