# Agent C (Interpreter) – post-quantum cryptography

**Rolle:** C · Interpreter
**Tech:** post-quantum cryptography (PQC)
**Input:** `raw3_pqc.json`
**Datum:** 2026-04-14

## Kontext

Header-Zeile des Dashboards:

> 8 Patente · 33 EU-Projekte · **0 Publikationen** · Phase: **Entstehung + Stagnation** · **Wettbewerbsintensiver Markt** · €99 M Förderung · Moderater Forschungsimpact

Dieses Briefing bewertet für jedes UC-Panel, ob es sein Versprechen (siehe Agent-Briefing) für PQC einlöst. Kernfrage: **Kann ein Budget-Entscheider diesem Dashboard für PQC trauen?**

## Bewertung je UC

| UC | Versprechen | Was das Panel liefert | Ampel | Begründung |
|---|---|---|---|---|
| **UC1 Aktivitätstrends** | Patent/Projekt/Publikations-Trend + CAGR | Patente-CAGR 50,0 %, Projekte-CAGR 18,9 %, TOP CPCs (H04L9/0852 etc.), Achse 2017-2026, Warnhinweis vorhanden | 🟡 | CAGR numerisch greifbar, doch 50 % auf Basis von nur **8 Patenten** ist statistisch nahezu bedeutungslos; **Publikations-Trend fehlt** trotz versprochener Dimension. |
| **UC2 S-Kurve & Reife** | Reifephase per Sigmoid-Fit (R², Wendepunkt, Konfidenz) | Phase: Entstehung, **R² = 0,000**, Konfidenz 80 %, Achse 2016-2026, Warnhinweis vorhanden | 🔴 | R² = 0,000 heißt: **kein Fit**. Trotzdem wird Phase „Entstehung" mit 80 % Konfidenz ausgegeben — die Konfidenzzahl ist bei R² = 0 **mathematisch nicht begründbar**. Kein Wendepunkt ausgewiesen. |
| **UC5 Technologiekonvergenz** | CPC-Kookkurrenz + Whitespace-Lücken | 10 CPC-Klassen, Ø Jaccard 0,122, 10 Whitespace-Lücken, Liste H04L/G06F/G06N/G09C/H04W/H10D/B82Y | 🟢 | Liefert genau die versprochenen Dimensionen; CPC-Liste (H04L dominant, G06N Quanten-KI-Bezug) ist inhaltlich **plausibel für PQC**. |
| **UC3 Wettbewerb & HHI** | Marktkonzentration (HHI) + Top-Anmelder | Label „Niedrige Konzentration", Top-Liste (Telefonica, Red Hat Czech, Univ. Carlos, Fraunhofer Austria, …), Skala 0-4 | 🔴 | **HHI-Zahl fehlt komplett** (nur Label). Dazu harter Widerspruch: Header „**Wettbewerbsintensiver Markt**" ↔ Panel „**Niedrige Konzentration**". Top-Liste mischt offenbar Patent- und Projekt-Anmelder ohne Trennschärfe. |
| **UC8 Dynamik & Persistenz** | Akteursdynamik (Neue/Persistente/Ausgeschiedene) | 17 Akteure, „Schrumpfend (-67 netto)", Achse 2016-2026, Warnhinweis vorhanden | 🟡 | Aussage „-67 netto" bei nur 17 aktuellen Akteuren wirkt arithmetisch **unlogisch** (mehr Ausgeschiedene als je vorhanden). Dynamik-Label „Schrumpfend" widerspricht CAGR +50 % aus UC1. |
| **UC11 Akteurs-Typen** | Breakdown HES/PRC/PUB/KMU | 172 Akteure, Dominanz „KMU/Unternehmen", Kategorien-Liste sichtbar | 🟡 | Kategorien da, aber **Prozentwerte fehlen** im Text. 172 Akteure in UC11 vs. 17 in UC8 — dieselbe Tech, zwei völlig verschiedene Akteurs-Grundgesamtheiten: Aggregationslogik intransparent. |
| **UC4 Förderung** | EU-Fördervolumen (CORDIS) + Instrumenten-Verteilung | Gesamt 98,6 Mio. EUR, 33 Projekte, Instrumente HORIZON-RIA/ERC/IA/CSA/JU-RIA/EIC-ACC | 🟢 | Versprechen erfüllt; Summe kongruent mit Header (99 M ≈ 98,6 M) und Projektzahl matcht Header (33). Instrumenten-Mix plausibel für Grundlagenforschung. |
| **UC7 Forschungsimpact** | h-Index / Zitationen / Top-Institutionen | 100 Publikationen, 53,9 Zitate/Pub, 15 Institutionen, Achse 2016-2024 (ohne 2018!) | 🔴 | **h-Index fehlt** (im Versprechen zentral). **Institutionen-Liste nicht ausgewiesen**, nur Zahl. Harter Konflikt zum Header („0 Publikationen" vs. 100 hier). Jahr 2018 fehlt in der Achse — Lücke ohne Erklärung. |
| **UC13 Publikationen** | Pub/Projekt + DOI-Anteil (CORDIS Linked) | 48,5 Pub/Projekt, DOI 35 %, Achse 2016-2025 (ohne 2024, ohne 2026) | 🔴 | 48,5 Pub/Projekt × 33 Projekte ≈ **1.600 Publikationen**, Panel nennt aber kein Total; UC7 zeigt 100, Header 0 — **drei verschiedene Publikationszahlen** im selben Dashboard. Jahresachse irregulär (2024 & 2026 fehlen). |
| **UC6 Geographie** | Länderverteilung + Kollaborationsmuster | 10 Länder, Top: Deutschland, Liste (FR/NL/ES/CH/IT/UK/GR/CZ/AT) | 🟡 | Länderverteilung sauber, aber **Kollaborationsmuster/Netz fehlt** — nur Balkenliste. Für strategische EU-Lokalisierungsentscheidung grenzwertig. |
| **UC9 Tech-Cluster** | 5-dim Profil (Aktivität/Vielfalt/Dichte/Kohärenz/Wachstum) | 2 Cluster, 6 Akteure, 21 CPC-Klassen, Labels „CPC Section G"/„CPC Section H" | 🔴 | Die **5 Dimensionswerte fehlen als Zahlen**, nur Dimensions-Namen gelistet. Cluster-Labels sind bloße CPC-Section-Namen statt inhaltlicher Tech-Cluster. 6 Akteure vs. 172 in UC11 — drastische Diskrepanz. |
| **UC10 EuroSciVoc** | Wissenschaftsdisziplin-Taxonomie | **0 Felder** / 35 Projekte, Labels cryptography/quantum computers/software/iot/internet/geometry/e-commerce, Shannon 3,12 | 🔴 | Widerspruch in sich: „**0 Felder**" neben 35 Projekten und konkreter Taxonomie-Liste. **35 Projekte** in UC10 vs. **33** in Header/UC4 — Kopf-vs-Detail-Abweichung. „geometry" und „e-commerce" bei PQC inhaltlich fragwürdig. |
| **UC12 Patenterteilung** | Grant-Rate + Time-to-Grant | Quote 78,3 %, 23,8 Mon., **83 Anmeldungen / 65 Erteilungen**, Achse 2019-2026 | 🔴 | 65/83 = **78,3 %** → Rechnung in sich korrekt. Aber: Header nennt **8 Patente**, UC12 spricht von **83 Anmeldungen und 65 Erteilungen**. Das ist ein Faktor-10-Widerspruch; vermutlich unterschiedliche Zähllogiken (Familien vs. Einzelanmeldungen), für den Nutzer aber nicht erkennbar. |

**Ampel-Bilanz:** 2× 🟢 · 4× 🟡 · 7× 🔴.

## Panels mit Warnhinweis „Daten ggf. unvollständig"

UC1, UC2, UC8, UC12 — also die Panels mit Zeitachse bis 2026. UC7 (bis 2024) und UC13 (bis 2025) haben **keinen Warnhinweis**, obwohl deren Achsen enden, ohne das laufende Jahr abzudecken; Nutzer erkennt nicht, dass hier aktiv abgeschnitten wurde.

## Für welche Entscheidungen brauchbar, für welche gefährlich?

**Brauchbar (bedingt):**
- **UC4 Förderung** — harte Zahl 98,6 M € über 33 Projekte, klare Instrumenten-Verteilung. Für Förderlandschafts-Screening tragfähig.
- **UC5 Technologiekonvergenz** — CPC-Nachbarklassen (G06N Quanten-KI, H04L Netzwerksicherheit) sind inhaltlich überzeugend und für F&E-Nachbarschaftsanalyse nutzbar.
- **UC6 Geographie** — Top-Länder-Reihung glaubhaft (DE/FR/NL/ES dominant), für grobe Standortfrage geeignet.

**Gefährlich:**
- **UC2 Reife** — Phase-Label „Entstehung" mit **R² = 0,000**, aber „Konfidenz 80 %" suggeriert Verlässlichkeit. Ein CISO-Investment-Case auf dieser Basis wäre statistisch unbegründet.
- **UC3 Wettbewerb** — Label-Widerspruch Header ↔ Panel; ohne HHI-Zahl kein belastbares Marktbild. Eine Make-or-Buy-Entscheidung auf diesem Panel ist riskant.
- **UC7/UC13 Publikationen/Impact** — Drei verschiedene Publikations-Zahlen (0 Header / 100 UC7 / 48,5 × 33 ≈ 1.600 UC13) machen jede Impact-Story für Gremien unhaltbar.
- **UC12 Grant-Rate** — 78,3 % wirkt exzellent, basiert aber auf 83 Anmeldungen — das widerspricht den **8 Patenten** im Header um Faktor 10. Ein Patentstrategie-Briefing auf dieser Zahl wäre Augenwischerei.
- **UC8 Dynamik** — „-67 netto schrumpfend" bei nur 17 aktuell aktiven Akteuren lässt sich plausibel nicht belegen; als Reifeindikator für PQC irreführend (Technologie ist real im starken Aufwind durch NIST-Finalisierung 2024).
- **UC10 Taxonomie** — „0 Felder" + e-commerce/geometry-Einträge bei PQC: falsch-plausibel, Nutzer sieht eine Zahl wo keine sein sollte.

**Gesamturteil:** Das PQC-Dashboard hat **zwei verlässliche Anker** (Förderung & CPC-Konvergenz) und **ein solides Geografie-Bild**. In allen anderen Dimensionen produziert es interne Widersprüche oder statistisch untragfähige Aussagen (besonders R² = 0,000 neben Phasen-Label und der Faktor-10-Sprung zwischen Header-Patenten und UC12-Anmeldungen). Für eine PQC-Investitions­entscheidung ist das Dashboard in seiner jetzigen Form **nicht belastbar** — es suggeriert Quantifizierbarkeit, wo tatsächlich nur sehr dünne Datenbasis (8 Patente, teils 17 Akteure) vorliegt.

---

## Executive-Summary

Von 13 Use Cases erfüllen nur UC4 (Förderung) und UC5 (Konvergenz) ihr Versprechen für PQC vollständig, während 7 UCs rote Ampeln bekommen — dominiert von R²-=-0-Fit mit 80 %-Konfidenz, drei widersprüchlichen Publikationszahlen (0/100/≈1.600) und einem Faktor-10-Sprung zwischen 8 Patenten im Header und 83 Anmeldungen in UC12. Das Dashboard ist für Förderlandschafts-Screening brauchbar, für Reife-, Wettbewerbs- oder Patentstrategie-Entscheidungen zu PQC jedoch irreführend.

**Kritischster Befund:** UC2 liefert Phase „Entstehung" mit **R² = 0,000** bei gleichzeitig ausgewiesener **Konfidenz 80 %** — Phasen-Label ohne jede statistische Grundlage, verkauft aber als hochkonfidente Aussage.
