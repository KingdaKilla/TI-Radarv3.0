# Konsistenz-Audit TI-Radar v3 · Autonomous Driving · Rolle A (Dokumentierer)

**Technologie:** autonomous driving
**Erhebung:** Live-Dashboard `app.drakain.de`, Dump `raw3_autonomous.json`
**Stand:** 2026-04-14

## Header-Kern-KPIs (Executive Summary)

| KPI | Wert |
|---|---|
| Patente | **734** |
| EU-Projekte | **235** |
| Publikationen (Header) | **0** |
| Phase (Header) | **Reife + Rückläufige Entwicklung** (Doppel-Phase) |
| Wettbewerb | **Wettbewerbsintensiver Markt** |
| Förderung | **€755 Mio.** |
| Forschungsimpact | **Sehr hoher Forschungsimpact** |
| Aktiver UC beim Dump | UC6 Geographische Verteilung |

## UC-Übersicht · Kern-Metriken und Jahresachse

| UC | Tab | Kern-Metriken (Observed) | Jahresachse |
|---|---|---|---|
| UC1 | Aktivitätstrends | Patente CAGR **11,7 %**; Projekte CAGR **8,4 %**; Top-CPCs: B60W60/001 (2.077), G05D1/0088 (1.788), B60W2420/403 (1.342), B60W40/02 (1.285), B60W50/14 (1.215) | **2017–2026** |
| UC2 | S-Kurve & Reife | Phase **Reife**; **R² = 0,999**; Wendepunkt **2021**; Konfidenz **95 %** | **2016–2026** |
| UC5 | Technologiekonvergenz | **10 CPC-Klassen**; Ø **Jaccard 0,224**; **3 Whitespace-Lücken**; Top-Klassen: B60W, G05D, G06V, G08G, G01C, G06F, G06N, B60Y, G01S, B60K | – |
| UC3 | Wettbewerb & HHI | **Niedrige Konzentration**; Skala 0–24; Top-Anmelder: Fraunhofer Austria, TU (Wien/TU), KTH Stockholm, Virtual Vehicle Research, Chalmers, NXP Semiconductors, RWTH, Lunds Universitet | – |
| UC8 | Dynamik & Persistenz | **12 Akteure**; **Schrumpfend (-293 netto)**; Skala 0–380 | **2016–2026** |
| UC11 | Akteurs-Typen | **1.274 Akteure**; Dominanz **KMU / Unternehmen**; weitere: HES, PRC, Other, Public Body | – |
| UC4 | Förderung | Gesamt **754,8 Mio. EUR**; **235 Projekte**; Instrumente: IA, RIA, HORIZON-RIA, HORIZON-JU-IA, HORIZON-IA, HORIZON-ERC, SME-2, MSCA-ITN, ERC-ADG, HORIZON-JU-RIA, ERC-COG, ERC-STG, PCP | – |
| UC7 | Forschungsimpact | **199 Publikationen**; **319,5 Zitate/Pub.**; **15 Institutionen** | **2016–2025** |
| UC13 | Publikationen | **60,0 Pub/Projekt**; **DOI-Anteil 27 %** | **2016–2024** |
| UC6 | Geographie | **10 Länder**; Top **Deutschland** (~360er-Skala); weitere: Frankreich, Schweden, Italien, UK, Niederlande, Schweiz, Spanien, Belgien, Österreich | – |
| UC9 | Tech-Cluster | **5 Cluster**, **52 Akteure**, **238 CPC-Klassen**; 5-dim Radar (Patente/Akteure/Dichte/Kohärenz/Wachstum); CPC Sections A, B, E, G, H | – |
| UC10 | EuroSciVoc | **0 Felder** (Zähler), **234 Projekte** zugeordnet; Shannon-Index **5,26**; Top-Terms: sensors, autonomous vehicles, automation, optical sensors, software, radar, drones | – |
| UC12 | Patenterteilung | Quote **40,8 %**; **30,8 Mon.** bis Erteilung; **6.336 Anmeldungen**; **2.586 Erteilungen** | **2016–2026** |

## Panels mit Warnhinweis „Daten ggf. unvollständig"

- UC1 Aktivitätstrends
- UC2 S-Kurve & Reife
- UC8 Dynamik & Persistenz
- UC7 Forschungsimpact
- UC12 Patenterteilung

**Ohne Warnhinweis** (obwohl Achse teilweise bis 2024/2025 reicht): UC13 Publikationen, UC5 Technologiekonvergenz, UC3 Wettbewerb & HHI, UC11 Akteurs-Typen, UC4 Förderung, UC6 Geographie, UC9 Tech-Cluster, UC10 EuroSciVoc.

## Auffällige Beobachtungen (dokumentarisch, ohne Bewertung)

1. **Header „0 Publikationen"** steht neben UC7 „199 Publikationen" und UC13 „60,0 Pub/Projekt × 235 Projekte" (= ~14.100 rechnerisch).
2. **Doppel-Phase im Header**: „Reife Rückläufige Entwicklung" — UC2 selbst weist jedoch nur die Phase **„Reife"** aus.
3. **Wettbewerbs-Widerspruch**: Header „Wettbewerbsintensiver Markt" vs. UC3 „Niedrige Konzentration".
4. **Patent-Zählerei widerspricht sich**: Header **734 Patente** vs. UC12 **6.336 Anmeldungen / 2.586 Erteilungen** — die Größenordnung ist nicht kompatibel.
5. **Projekt-Zählerei**: Header 235 = UC4 235, aber UC10 zeigt **234 Projekte** (nahe, aber nicht identisch). UC10-Zähler „0 Felder" widerspricht der gleichzeitig angezeigten Feld-Liste (sensors, autonomous vehicles …) und dem Shannon-Index 5,26.
6. **R² = 0,999** bei UC2 ist auffällig hoch — Phasenlabel „Reife" mit Wendepunkt **2021** bei gleichzeitig **positiver CAGR 11,7 %** (UC1) wirkt spannungsgeladen.
7. **UC8 „12 Akteure" vs. UC11 „1.274 Akteure"** — unterschiedliche Akteurs-Zählmengen pro Panel.
8. **Jahresachsen-Inkonsistenz**: UC1/UC2/UC8/UC12 bis **2026**; UC7 bis **2025**; UC13 bis **2024** — innerhalb desselben Dashboards.
9. **UC11 Prozent-Summen** nicht explizit im Dump ausgewiesen — nur Reihung der Typen (KMU > HES > PRC > Other > Public Body).
10. **Dump-Zeitpunkt**: Nachvollziehbarkeit durchgängig **11,8 s** (einheitlich, plausibel).

## Nachvollziehbarkeit (Quellen / Latenz)

| UC | Quellen | Latenz |
|---|---|---|
| UC1, UC3, UC6, UC7, UC8 | 2 Quellen | 11,8 s |
| UC2, UC4, UC5, UC9, UC10, UC11, UC12, UC13 | 1 Quelle | 11,8 s |

---

*Erhebungsform: `lastIndexOf(tabName)` + 1.800 Zeichen Kontext aus Live-Dashboard. Keine externe Recherche; reine Dokumentation der beobachteten Panel-Inhalte.*
