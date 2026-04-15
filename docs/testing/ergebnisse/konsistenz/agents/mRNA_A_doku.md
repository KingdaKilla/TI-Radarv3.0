# Konsistenz-Audit TI-Radar v3 — mRNA (Rolle A · Dokumentierer)

**Datum:** 2026-04-14
**Input:** `raw3_mRNA.json`
**Rolle:** A · Dokumentierer (strukturiertes Protokoll des Dashboard-Outputs)

---

## Header-KPIs (Executive Summary)

| KPI | Wert |
|---|---|
| Technologie | MRNA |
| Patente | 742 |
| EU-Projekte | 307 |
| Publikationen | 311.5K |
| Phase | **Reife + Rückläufige Entwicklung** (Doppel-Phase) |
| Wettbewerbsstatus | Wettbewerbsintensiver Markt |
| Förderung (gesamt) | €446 Mio. |
| Forschungsimpact-Label | Sehr hoher Forschungsimpact |
| Aktive Cluster-Info | UC6 Geographische Verteilung (als Einleitung im Header-Snippet) |

---

## UC-Metriken im Überblick

| UC | Tab | Kern-Metriken (beobachtet) | Jahresachse |
|---|---|---|---|
| UC1 | Aktivitätstrends | Patente CAGR **5.6 %**, Projekte CAGR **0.8 %**, Publikationen CAGR **1.8 %**; Top-CPC: A61K2039/53 (1.179), A61P35/00 (870), A61K9/5123 (778), A61K39/12 (761), A61K48/005 (698) | **2017–2026** |
| UC2 | S-Kurve & Reife | Phase **Reife**, R² = **0.998**, Wendepunkt **2022**, Konfidenz **95 %**; Y-Skala 0–380 | **2016–2026** |
| UC5 | Technologiekonvergenz | **10 CPC-Klassen**, Ø Jaccard **0.382**, **6 Whitespace-Lücken**; Klassen: C12N, A61K, A61P, C07K, C12Q, C12Y, Y02A, C07H, G01N, C12P | (keine) |
| UC3 | Wettbewerb & HHI | **Niedrige Konzentration** (Widerspruch zum Header-Label „Wettbewerbsintensiver Markt"); Top-Anmelder: FUNDACIO CENTRE…, FORSCHUNGSINSTITU…, UNI ZURICH, MAX DELBRUECK, UNI MÜNCHEN, FRAUNHOFER AUSTRIA, STICHTING AMSTERDAM, AGENCIA ESTATAL; Skala 0–12 | (keine) |
| UC8 | Dynamik & Persistenz | **34 Akteure**, **Schrumpfend (−97 netto)**; Skala 0–160 | **2016–2026** |
| UC11 | Akteurs-Typen | **363 Akteure**, dominiert von **Higher Education**; weitere Kategorien: KMU/Unternehmen, Research Organisation, Other, Public Body (keine %-Werte sichtbar) | (keine) |
| UC4 | Förderung | **€446.1 Mio.**, **307 Projekte**; Instrumente: HORIZON-RIA, HORIZON-ERC, ERC-COG, RIA, ERC-STG, ERC-ADG, HORIZON-ERC-…, MSCA-IF/ITN, HORIZON-EIC u. a. | (keine) |
| UC7 | Forschungsimpact | **197 Publikationen**, **610.1 Zitate/Pub.**, **15 Institutionen**; Doppel-Y-Achse (Pub 0–60, Zitationen 0–38 000) | **2016–2024** |
| UC13 | Publikationen | **8.0 Pub/Projekt**, **DOI 78 %**; Y-Skala 0–260 | **2016–2024** |
| UC6 | Geographie | **10 Länder**, Top: **Deutschland**; Reihenfolge: Deutschland, Niederlande, Frankreich, Belgien, Schweiz, Polen, Schweden, UK, Italien, Spanien; Skala 0–300 | (keine) |
| UC9 | Tech-Cluster | **5 Cluster**, **29 Akteure**, **208 CPC-Klassen**; Profil-Dimensionen: Patente, Akteure, Dichte, Kohärenz, Wachstum; CPC-Sections A/B/C/G/Y | (keine) |
| UC10 | EuroSciVoc | **1 Feld**, **387 Projekte**, Shannon-Index **4.89**; dominant: **nanotechnology** (!), Rest: je 0–1 % | (keine) |
| UC12 | Patenterteilung | Quote **13.9 %**, **44.2 Monate** bis Erteilung, **4.024 Anmeldungen**, **558 Erteilungen**; Skala 0–1000 / 0–100 % | **2016–2026** |

---

## Panels mit Warnhinweis „Daten ggf. unvollständig"

Ausdrücklich sichtbar in:

- **UC1 / Aktivitätstrends** (Jahresachse bis 2026)
- **UC2 / S-Kurve & Reife** (Jahresachse bis 2026)
- **UC8 / Dynamik & Persistenz** (Jahresachse bis 2026)

Nicht sichtbar, obwohl Jahresachse ebenfalls bis 2026 läuft:

- **UC12 / Patenterteilung** (2016–2026, kein Warnhinweis im extrahierten Text)

Keine Jahresachse oder nur bis 2024 (daher Warnhinweis nicht anwendbar):

- UC7 (2016–2024), UC13 (2016–2024), UC3, UC5, UC6, UC9, UC10, UC11, UC4.

---

## Auffällige Beobachtungen (reine Dokumentation, keine Wertung)

1. **Publikations-Mismatch Header ↔ UC7:** Header „311.5K Publikationen" vs. UC7 „197 Publikationen". Differenz ca. Faktor **1 581**.
2. **Phase-Doppelung:** Header nennt „Reife + Rückläufige Entwicklung", UC2 hingegen nur „Reife" (R² 0.998, Wendepunkt 2022).
3. **Wettbewerbs-Widerspruch:** Header-Label „Wettbewerbsintensiver Markt" vs. UC3 „Niedrige Konzentration".
4. **Projektzahl-Divergenz Header vs. UC10:** Header 307 Projekte, UC10 **387 Projekte** (Δ +80). UC4 nennt ebenfalls 307 — UC10 weicht ab.
5. **UC10 Taxonomie-Plausibilität:** Einziges / dominantes Feld ist **„nanotechnology"** für mRNA — inhaltlich fragwürdig, da mRNA primär eine biomedizinisch/molekularbiologische Disziplin ist.
6. **Jahresachsen-Inkonsistenz:** UC1/UC2/UC8/UC12 bis **2026**, UC7/UC13 bis **2024** — unterschiedliche Endjahre im selben Dashboard.
7. **UC12 Nachrechnung:** 558 / 4 024 = 13.87 % → gerundet 13.9 % (Quote plausibel).
8. **UC13 Nachrechnung:** 8.0 Pub/Projekt × 307 Projekte = 2 456 Pub — weder 197 (UC7) noch 311.5K (Header) entsprechen diesem Wert.
9. **UC2 R²:** 0.998 auf 2016–2026-Achse mit Y-Skala bis 380 — ungewöhnlich hoch, Warnhinweis „Daten ggf. unvollständig" trotzdem aktiv (2025/2026 offen).
10. **UC8 Netto-Bewegung:** „Schrumpfend (−97 netto)" bei nur 34 Akteuren im Panel — unklar, auf welche Basismenge sich „−97" bezieht; passt nicht zur sichtbaren Akteurszahl.
11. **UC11 vs. UC8:** UC11 meldet 363 Akteure, UC8 nur 34; zudem UC9 29 Akteure. Drei verschiedene Akteurszahlen je Panel.
12. **UC5 Whitespace-Angabe:** „6 Whitespace-Lücken" bei 10 CPC-Klassen — Lückenkonzept (in welchen Kookkurrenzen?) aus Panel-Text nicht herleitbar.
13. **Nachvollziehbarkeit:** Alle Panels zeigen einheitlich **29.5 s** Antwortzeit (identisch — möglicherweise Cache-Wert oder aggregierter Header-Wert, nicht panel-individuell).

---

## Zusammenfassung Dokumentation

Das mRNA-Dashboard liefert auf allen 13 Tabs Inhalte; Werte sind durchweg präsent. Auffällig ist jedoch die **Inkonsistenz zwischen Header-Aggregaten und UC-Detail-Panels** (Publikationen, Phase, Wettbewerb, Projekte) sowie die **wissenschaftlich unplausible EuroSciVoc-Zuordnung „nanotechnology"** als einziges Feld. Jahresachsen reichen in 4 Panels bis ins laufende, unvollständige Jahr 2026 — Warnhinweis nur in 3 davon.
