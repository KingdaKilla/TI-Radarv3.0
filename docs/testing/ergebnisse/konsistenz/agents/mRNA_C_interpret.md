# mRNA · Rolle C (Interpreter) — UC-Versprechen vs. Lieferung

**Tech:** mRNA
**Datum:** 2026-04-14
**Input:** `raw3_mRNA.json`
**Header-KPIs:** 742 Patente · 307 EU-Projekte · 311.5K Publikationen · Phase „Reife · Rückläufige Entwicklung" · Wettbewerbsintensiver Markt · €446M · Sehr hoher Forschungsimpact

---

## Bewertung je Use Case

| UC | Tab | Versprechen | Tatsächliche Lieferung | Ampel | Begründung |
|---|---|---|---|---|---|
| UC1 | Aktivitätstrends | Patent-/Projekt-/Publikationstrend + CAGR | Patente-CAGR 5.6 %, Projekte 0.8 %, Publikationen 1.8 %; Top-CPCs A61K2039/53 (1.179), A61P35/00 (870), A61K9/5123 (778), A61K39/12, A61K48/005; Achse 2017–2026 | 🟡 | Zahlen konkret und plausibel, aber Achse reicht bis 2026 (nur 3,5 Monate des laufenden Jahres erfasst) — CAGR-Rechnung enthält fast leeres 2025/2026 und wird dadurch verzerrt. Warnhinweis vorhanden, aber Wert trotzdem rechnerisch unsauber. |
| UC2 | S-Kurve & Reife | Sigmoid-Fit, R², Wendepunkt, Konfidenz | Phase „Reife", R² = 0.998, Wendepunkt 2022, Konfidenz 95 % | 🟡 | Technisch exzellenter Fit (R² = 0.998) — aber Panel liefert nur „Reife", während Header „Reife · Rückläufige Entwicklung" kombiniert. Die zweite Phase ist im Panel nicht belegt; zudem Achse bis 2026 inkl. unvollständiger Jahre. Entscheider sieht im Header eine andere Story als im Detail. |
| UC5 | Technologiekonvergenz | CPC-Kookkurrenz + Whitespace-Lücken | 10 CPC-Klassen, Ø Jaccard 0.382, 6 Whitespace-Lücken; Klassen C12N, A61K, A61P, C07K, C12Q, C12Y, Y02A, C07H, G01N, C12P | 🟢 | Konkrete Metrik, plausible CPCs für mRNA-Feld (C12N, A61K, A61P, C07K), Whitespace benannt. Einzig Lücken nicht qualitativ aufgeschlüsselt — aber Versprechen gehalten. |
| UC3 | Wettbewerb & HHI | HHI + Top-Anmelder | „Niedrige Konzentration", Top-Liste (FUNDACIO CENTRED…, MAX DELBRUECK CEN…, UNIVERSITÄT ZÜRICH, FRAUNHOFER AUSTRIA, STICHTING AMSTERDAM, …) | 🔴 | Direkter Widerspruch zum Header „Wettbewerbsintensiver Markt". HHI-Zahlenwert fehlt komplett — nur Label. Top-Anmelder-Namen abgeschnitten („FUNDACIO CENTRED…") — Vergleich mit BioNTech/Moderna/Pfizer/CureVac nicht möglich. Für einen mRNA-Markt ist das Fehlen der großen Industrie-Player ein riesiges Plausibilitäts-Problem. |
| UC8 | Dynamik & Persistenz | Neue / Persistente / Ausgeschiedene | 34 Akteure, „Schrumpfend (–97 netto)", Achse 2016–2026 | 🟡 | KPI „34 Akteure" widersprüchlich zu UC11 (363) und UC3-Tops — wahrscheinlich anderer Scope (nur Patente?). Netto –97 plausibel, aber ohne Kontext kaum deutbar. Achse bis 2026 übernimmt Unvollständigkeit. |
| UC11 | Akteurs-Typen | HES/PRC/PUB/KMU-Breakdown | 363 Akteure, „Dominiert: Higher Education"; Kategorien Higher Education, KMU/Unternehmen, Research Organisation, Other, Public Body | 🟡 | Qualitatives Label vorhanden, aber **keine Prozentwerte** im Panel-Text sichtbar. Ohne Share-Werte ist der Breakdown nicht interpretierbar — „dominiert" ist keine Zahl. |
| UC4 | Förderung | EU-Fördervolumen + Instrumente | €446.1 Mio., 307 Projekte; HORIZON-RIA, HORIZON-ERC, ERC-COG/STG/ADG, MSCA-IF/ITN, HORIZON-EIC | 🟢 | Solide: Volumen, Projekte, Instrumenten-Mix, alles konsistent mit Header (€446M, 307 Projekte). Einziger Makel: keine Top-Beneficiaries im Panel-Ausschnitt, aber Versprechen erfüllt. |
| UC7 | Forschungsimpact | h-Index, Zitationen, Top-Institutionen | 197 Publikationen, 610.1 Zitate/Pub., 15 Institutionen; Achse 2016–2024 | 🔴 | **h-Index fehlt komplett** (Versprechen). Stattdessen Pub-Anzahl + Zitate/Pub. 197 Publikationen stehen in frontalem Widerspruch zum Header-Wert 311.5K — 1.580-facher Unterschied. Zitate/Pub 610 für „sehr hoher Impact" sind zwar imposant, aber auf 197 Pubs nicht robust. |
| UC13 | Publikationen | Pub/Projekt + DOI-Anteil | 8.0 Pub/Projekt, DOI 78 %; Achse 2016–2024 | 🟡 | KPIs da, Rechnung 8.0 × 307 = 2.456 Publikationen — passt weder zu UC7 (197) noch zu Header (311.5K). Drei sich widersprechende Publikations-Zahlen im selben Dashboard. |
| UC6 | Geographie | Länderverteilung + Kollaboration | 10 Länder, Top: Deutschland, dann NL/FR/BE/CH/PL/SE/UK/IT/ES | 🟡 | Länder plausibel für EU-gefärbte Sicht, aber **USA und China fehlen** — für einen mRNA-Markt (Moderna, Pfizer, Chinas Pharma-Szene) extrem verzerrt. Kollaborationsmuster nicht sichtbar (nur Balkenliste). |
| UC9 | Tech-Cluster | 5-dim Profil (Aktivität/Vielfalt/Dichte/Kohärenz/Wachstum) | 5 Cluster, 29 Akteure, 208 CPC-Klassen; CPC-Sektionen A/B/C/G/Y genannt | 🔴 | Die **5 versprochenen Dimensionen werden als Labels genannt, aber ohne Zahlenwerte** im Panel-Text. Ein Radar ohne Werte ist nicht interpretierbar. 29 Akteure vs. 363 (UC11) vs. 34 (UC8) — dritte, ebenfalls widersprüchliche Akteurs-Zählung. |
| UC10 | EuroSciVoc | Wissenschaftsdisziplin-Taxonomie | **1 Feld**, 387 Projekte, Top „nanotechnology", Shannon-Index 4.89 | 🔴 | Inhaltlich nicht plausibel: mRNA primär unter „nanotechnology" statt „biotechnology/medical biotechnology/immunology/pharmacology" ist fachlich falsch. Shannon-Index 4.89 bei nur 1 Feld ist mathematisch unmöglich (Shannon einer 1-Kategorie-Verteilung = 0). Zusätzlich: 387 Projekte ≠ 307 (Header/UC4). |
| UC12 | Patenterteilung | Grant-Rate + Time-to-Grant | Quote 13.9 %, 44.2 Monate, 4.024 Anmeldungen, 558 Erteilungen; Achse 2016–2026 | 🔴 | Rechen-Check: 558 / 4.024 = 13,87 % ✓ — in sich stimmig. **Aber:** 4.024 Anmeldungen widersprechen dem Header-Wert von 742 Patenten um den Faktor 5,4. Entweder meint Header „erteilte Patente" (≠ 558) oder „Familien" (unklar) — UC1-CPC-Counts liegen im Bereich 700–1.200, was weder zu 742 noch zu 4.024 passt. Drei unterschiedliche Patent-Zahlen im selben Dashboard. |

---

## Summary · Für welche Entscheidungen brauchbar, für welche gefährlich?

### Brauchbar (mittleres Vertrauen)
- **Förderlandschaft (UC4):** €446M + Instrumenten-Mix (HORIZON-RIA, ERC-COG/STG/ADG) sind intern konsistent und passen zur mRNA-Realität nach 2020. Budget-Entscheidungen zur EU-Förderpositionierung möglich.
- **Technologiekonvergenz (UC5):** CPC-Nachbarschaften (C12N, A61K, A61P, C07K, C12Q) sind fachlich plausibel — R&D-Portfolio-Entscheidungen mit CPC-Bezug tragfähig.
- **Reifegrad-Signal (UC2):** Wendepunkt 2022 + R² 0.998 + Phase „Reife" ist fachlich schlüssig (COVID-Push 2020–2022, danach Normalisierung).

### Gefährlich (darf nicht ohne Quellenprüfung in eine Entscheidung einfließen)
- **Wettbewerbsanalyse (UC3):** „Niedriger HHI" widerspricht Header „wettbewerbsintensiv"; Top-Liste enthält keinen einzigen der globalen mRNA-Marktführer (BioNTech, Moderna, Pfizer, CureVac). Eine Markteintrittsentscheidung auf dieser Basis wäre riskant.
- **Geographie (UC6):** USA/China fehlen — jede internationale Standortentscheidung auf diesem Panel wäre verzerrt.
- **EuroSciVoc (UC10):** mRNA als „nanotechnology" + Shannon 4.89 bei 1 Feld = mathematisch unmöglich. Panel hat einen Datenbug, nicht interpretierbar.
- **Tech-Cluster-Profil (UC9):** 5 Dimensionen genannt, aber keine Werte geliefert — ein Strategie-Radar ohne Werte ist Deko.
- **Publikations-Story (UC7 + UC13 + Header):** Drei Zahlen (197 / 2.456 / 311.5K) für dieselbe Größe. Impact-/Outreach-Aussagen („sehr hoher Forschungsimpact") sind nicht belegbar, solange nicht klar ist, welcher Scope stimmt.
- **Patent-Story (Header + UC1 + UC12):** 742 vs. 4.024 vs. CPC-Klassen mit 1.179 — ohne Definition von „Patent" (Familie? Anmeldung? Erteilung?) ist keine quantitative Aussage tragfähig.

### Kernurteil
Für einen Budget-Entscheider ist das mRNA-Dashboard **nur mit roten Warnflaggen** nutzbar: Fördervolumen, CPC-Struktur und Reife­signal tragen; jede Aussage zu **Wettbewerb, Publikations-Output, Geographie, Disziplin-Zuordnung und Patent­zählung** muss außerhalb des Dashboards verifiziert werden.
