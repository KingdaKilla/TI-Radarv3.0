# Konsistenz-Audit TI-Radar v3 — Post-Quantum Cryptography (Rolle A · Dokumentierer)

**Tech:** `post-quantum cryptography`
**Datum Live-Capture:** kurz vor 2026-04-14
**Quelle:** `docs/testing/ergebnisse/konsistenz/raw/raw3_pqc.json`

## Header-Zeile (Executive Summary des Dashboards)

| KPI | Wert laut Header |
|---|---|
| Patente | **8** |
| EU-Projekte | **33** |
| Publikationen | **0** |
| Phase | **Entstehung + Stagnation** (Doppellabel) |
| Wettbewerbs-Label | **Wettbewerbsintensiver Markt** |
| Förderung | **€99M** |
| Impact-Label | **Moderater Forschungsimpact** |

> Der anschließende Fließtext in `header` ist nicht PQC-spezifisch, sondern erklärt UC6 (Geographische Perspektive) — das deutet auf einen generischen/gelisteten Cluster-Einstiegstext hin.

## UC-Tabelle · Kern-Metriken und Jahresachsen

| Tab (UC) | Aktiv | Kern-Metriken laut Panel | Beobachtete Jahresachse | Quellen · Latenz |
|---|---|---|---|---|
| Aktivitätstrends (UC1) | ja | Patente CAGR **50.0 %**, Projekte CAGR **18.9 %**; Top-CPC: H04L9/0852 (97), H04L9/3247 (52), H04L9/3093 (50), H04L9/0825 (36), H04L9/0861 (34) | **2017–2026** (Y-Achse −90 % … +270 %) | 2 / 5.5 s |
| S-Kurve & Reife (UC2) | ja | Phase **Entstehung**, **R² = 0.000**, Konfidenz **80 %**, Skala 0–8 | **2016–2026** | 1 / 5.5 s |
| Technologiekonvergenz (UC5) | ja | **10 CPC-Klassen**, Ø Jaccard **0.122**, **10 Whitespace-Lücken**; Klassen: H04L, G06F, G06N, G09C, G06Q, H04W, H10D, H04B, Y02D, B82Y | — (keine Zeitachse) | 1 / 5.5 s |
| Wettbewerb & HHI (UC3) | ja | **Niedrige Konzentration**; Top-Akteure: Telefónica Innova…, Agencia Estatal C…, Red Hat Czech SR…, Univ. Carlos…, Fraunhofer Austria, Narodni Urad…, Univ. Luxembourg, Fondazione Links…; Skala Patente/Projekte 0–4 | — | 2 / 5.5 s |
| Dynamik & Persistenz (UC8) | ja | **17 Akteure**, Status **Schrumpfend (−67 netto)**; Legende Persistente / Neue / Ausgeschieden | **2016–2026** | 2 / 5.5 s |
| Akteurs-Typen (UC11) | ja | **172 Akteure**; Dominiert: **KMU / Unternehmen**; weitere Kategorien: Higher Education, Research Organisation, Public Body, Other | — | 1 / 5.5 s |
| Förderung (UC4) | ja | **98.6 Mio. EUR Gesamt**, **33 Projekte**; Instrumente: HORIZON-RIA, HORIZON-ERC, HORIZON-IA, ERC-ADG, RIA, HORIZON-CSA, HORIZON-JU-RIA, ERC-COG, ERC-STG, HORIZON-EIC-ACC… | — | 1 / 5.5 s |
| Forschungsimpact (UC7) | ja | **100 Publikationen**, **53.9 Zitate/Pub.**, **15 Institutionen** | **2016, 2017, 2019–2026** (2018 fehlt in Ticks) | 2 / 5.5 s |
| Publikationen (UC13) | ja | **48.5 Pub/Projekt**, **DOI 35 %** | **2016–2023, 2025** (2024 + 2026 fehlen in Ticks) | 1 / 5.5 s |
| Geographie (UC6) | ja | **10 Länder**, Top: **Deutschland**; Ranking: DE, FR, NL, ES, CH, IT, UK, GR, CZ, AT | — | 2 / 5.5 s |
| Tech-Cluster (UC9) | ja | **2 Cluster**, **6 Akteure**, **21 CPC-Klassen**; Cluster-Labels: CPC Section G, CPC Section H; Achsen: Patente, Akteure, Dichte, Kohärenz, Wachstum | — | 1 / 5.5 s |
| EuroSciVoc (UC10) | ja | **0 Felder**, **35 Projekte**; Top-Begriffe: cryptography, quantum computers, software, internet of things, internet, geometry, e-commerce; Shannon-Index **3.12** | — | 1 / 5.5 s |
| Patenterteilung (UC12) | ja | Quote **78.3 %**, **23.8 Monate** bis Erteilung, **83 Anmeldungen**, **65 Erteilungen** | **2019–2026** | 1 / 5.5 s |

## Panels mit Warnhinweis „Daten ggf. unvollständig"

- UC1 Aktivitätstrends
- UC2 S-Kurve & Reife
- UC8 Dynamik & Persistenz
- UC12 Patenterteilung

Fehlt (obwohl Jahresachse bis 2026 reicht bzw. Jahre fehlen): UC7 Forschungsimpact, UC13 Publikationen.

## Auffällige Beobachtungen (nur dokumentierend, Bewertung in Rolle B/C)

- **Header widerspricht UC7:** Header meldet „0 Publikationen", UC7 zeigt „100 Publikationen / 53.9 Zitate/Pub." und UC13 „48.5 Pub/Projekt, DOI 35 %". Klassischer Header-vs-Panel-Mismatch.
- **Doppel-Phasen-Label im Header:** „Entstehung **+** Stagnation". UC2 selbst listet nur „Entstehung".
- **Wettbewerbs-Widerspruch:** Header „Wettbewerbsintensiver Markt" vs. UC3 „Niedrige Konzentration". Top-Akteure zeigen Patentzahlen im Bereich 0–4 — sehr dünne Basis.
- **R² = 0.000 bei UC2**, trotzdem Konfidenz 80 % und Phase „Entstehung" gesetzt. Bei 8 Patenten ist ein Sigmoid-Fit ohnehin nicht sinnvoll.
- **Projekt-Zählerei inkonsistent:** Header 33 · UC4 33 · UC10 35 · EuroSciVoc-Fließtext „35 Projekte zugeordnet". Zwei voneinander abweichende Werte (33 vs. 35).
- **UC10 „0 Felder" trotz 35 zugeordneter Projekte und Shannon-Index 3.12** — widerspricht sich direkt im selben Panel. Inhaltlich taucht „cryptography" und „quantum computers" als Top-Felder korrekt auf, also inhaltlich plausibel, aber die Feld-Zählung ist kaputt.
- **UC8 „Schrumpfend −67 netto" bei 17 Akteuren** — negativer Nettowert größer als Gesamtakteurszahl; Saldo bezieht sich mutmaßlich auf kumulierte Ausschüttung, nicht auf Bestand, ist aber ohne Kontext irreführend.
- **UC12-Arithmetik bricht:** 65 Erteilungen / 83 Anmeldungen = **78.3 %** (rechnet durch). Aber: Header zeigt nur 8 Patente, UC12 spricht von 83 Anmeldungen und 65 Erteilungen — Header-Zahl und UC12-Zähler driften um eine Größenordnung auseinander.
- **Jahresachsen-Inkonsistenz:** UC1/UC2/UC8/UC12 bis 2026; UC7 zeigt 2016–2026 mit Lücke 2018; UC13 zeigt 2016–2023 und 2025 (2024 und 2026 fehlen).
- **Förderung:** Header €99M vs. UC4 98.6 Mio. EUR — gerundet konsistent.
- **UC13 Pub/Projekt × Projekte:** 48.5 × 33 ≈ **1600 Publikationen** theoretisch — steht im Widerspruch sowohl zu Header (0) als auch zu UC7 (100). Das heißt: die drei Publikations-Kennzahlen (Header 0 / UC7 100 / UC13 impliziert ~1600) kommen aus drei verschiedenen Quellen.
- **UC9 nur 6 Akteure** — steht im Widerspruch zu UC11 (172 Akteure) und UC3 (8 gelistete Top-Akteure). Cluster-Definition zählt offenbar anders.

## Rohdaten-Notiz

Alle 13 erwarteten Panels sind mit `observedActive = Tab-Name` korrekt aktiv registriert. Latenz ist in jedem Panel 5.5 s — verdächtig gleichförmig, spricht für einheitliche Upstream-Timeouts oder eine gemeinsame Latenz-Reported-Quelle.
