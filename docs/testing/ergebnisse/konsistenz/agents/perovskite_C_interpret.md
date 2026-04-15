# Agent C · Interpreter · Perovskite Solar Cell

**Tech:** perovskite solar cell
**Stichtag Audit:** 2026-04-14
**Header-KPIs:** 101 Patente · 140 EU-Projekte · 0 Publikationen · Phase „Reife Rückläufige Entwicklung" · €222 M Förderung · Hoher Forschungsimpact · Wettbewerbsintensiver Markt

## Versprechen vs. Lieferung je Use Case

| UC | Tab | Versprechen | Tatsächliche Lieferung | Ampel | Begründung |
|----|-----|-------------|-----------------------|-------|------------|
| UC1 | Aktivitätstrends | Patent-/Projekt-/Pub-Trend + CAGR | Patente CAGR 4,1 % · Projekte CAGR 9,8 % · Top-CPCs mit Counts (Y02E10/549: 5.076 …) · Achse 2017–2026 · Warnhinweis vorhanden | 🟡 | CAGRs und CPC-Top-Liste interpretierbar, aber Publikations-CAGR fehlt komplett trotz Versprechen „Patent/Projekt/Publikation". CPC-Zahl 5.076 passt nicht zu nur 101 Header-Patenten — die CPC-Liste scheint aus globalem Patent-Pool gezogen. |
| UC2 | S-Kurve & Reife | Reifephase per Sigmoid-Fit | Phase „Reife" · R² = 1,000 · Wendepunkt 2021 · Konfidenz 82 % · Achse 2016–2026 · Warnhinweis vorhanden | 🔴 | R² = 1,000 ist praktisch unmöglich bei realen Zeitreihen und deutet auf Overfitting oder zu wenige Stützpunkte. Außerdem widerspricht das Panel-Label „Reife" dem Header „Reife Rückläufige Entwicklung" — der Rückgang-Teil fehlt im Panel. |
| UC5 | Technologiekonvergenz | CPC-Kookkurrenz + Whitespace | 10 CPC-Klassen · Ø Jaccard 0,198 · 10 Whitespace-Lücken · Codes Y02E, H10K, Y02P … | 🟢 | Konkrete Zahlen, plausibler Jaccard, inhaltlich passende CPC-Codes (Photovoltaik/Halbleiter). Hält sein Versprechen. |
| UC3 | Wettbewerb & HHI | HHI + Top-Anmelder | „Niedrige Konzentration" · Balkenliste mit 8 sichtbaren Akteuren (Fraunhofer, Saule, Uni Jaume I, Dyenamo, Solaveni …) — **kein HHI-Wert ausgewiesen** | 🔴 | HHI-Zahl fehlt. Zusätzlich widerspricht Panel-Label „Niedrige Konzentration" dem Header „Wettbewerbsintensiver Markt" direkt. Entscheider bekommen zwei entgegengesetzte Signale. |
| UC8 | Dynamik & Persistenz | Neue / Persistente / Ausgeschiedene | 9 Akteure · „Schrumpfend (-70 netto)" · Achse 2016–2026 · Warnhinweis vorhanden | 🟡 | Netto-Wert erklärt, aber „9 Akteure" vs. -70 netto ist irritierend (Verhältnis nicht erkennbar) und UC11 nennt 280 Akteure — die Basis für die Dynamik ist unklar definiert. |
| UC11 | Akteurs-Typen | Breakdown HES/PRC/PUB/KMU | 280 Akteure · Dominiert: Higher Education · Legenden-Labels sichtbar | 🟡 | Qualitativ OK („Higher Education dominiert"), **aber keine Prozentwerte oder absolute Zahlen je Typ** — nur Kategorie-Labels. Plausi-Check auf 100 % unmöglich. |
| UC4 | Förderung | EU-Volumen + Instrumente | 221,8 Mio EUR · 140 Projekte · Instrumenten-Liste HORIZON-RIA / IA / ERC / MSCA … | 🟢 | Summe und Projektzahl konsistent zum Header (€222 M / 140). Instrumenten-Aufschlüsselung breit und plausibel. |
| UC7 | Forschungsimpact | h-Index / Zitationen / Top-Institutionen | 100 Publikationen · 363,5 Zitate/Pub · 15 Institutionen · Achse 2016–2024 | 🔴 | **h-Index fehlt**, Top-Institutionen nicht gelistet (nur Anzahl 15). Außerdem steht Header „0 Publikationen" gegen 100 im Panel — direkter Widerspruch. 363,5 Zitate/Pub ist extrem hoch und müsste belegt sein. |
| UC13 | Publikationen | Pub/Projekt + DOI | 21,3 Pub/Projekt · DOI 56 % · Achse 2016–2024 | 🔴 | 21,3 × 140 Projekte = 2.982 Publikationen — das widerspricht UC7 (100) und Header (0) fundamental. Drei inkompatible Publikationszahlen im selben Dashboard. |
| UC6 | Geographie | Länderverteilung | 10 Länder · Top: Deutschland · Ranking DE/CH/UK/IT/ES/FR/NL/PL/BE/SE | 🟢 | Top-Land und Rangliste klar. Für Perovskit mit europäischem Forschungsschwerpunkt plausibel. |
| UC9 | Tech-Cluster | 5-dim Profil | 5 Cluster · 39 Akteure · 118 CPC · Radar-Dimensionen Patente/Akteure/Dichte/Kohärenz/Wachstum · CPC-Sections B/C/G/H/Y | 🟡 | Dimensionen genannt, **keine numerischen Werte** je Dimension sichtbar. Außerdem: 39 Akteure hier vs. 280 (UC11) vs. 9 (UC8) — drei verschiedene Akteurs-Populationen. |
| UC10 | EuroSciVoc | Wissenschafts-Taxonomie | **1 Feld** „nanotechnology" · 134 Projekte · Shannon 4,87 | 🔴 | Nur 1 Feld für eine 140-Projekt-Domäne ist Taxonomie-Kollaps. Dazu: Shannon 4,87 bei nur 1 Feld ist mathematisch unmöglich (Shannon ≤ log₂(k), bei k=1 → 0). Außerdem 134 ≠ 140 Header-Projekte. |
| UC12 | Patenterteilung | Grant-Rate + Time-to-Grant | Quote 9,3 % · 28,1 Mon. · **5.462 Anmeldungen** · 506 Erteilungen · Achse 2016–2026 | 🔴 | 506 / 5.462 = 9,26 % → die Grant-Rechnung selbst stimmt. **Aber 5.462 Anmeldungen widersprechen dem Header-Wert 101 Patente um Faktor 54** — entweder ist das Header-KPI völlig falsch oder UC12 zieht aus einem anderen Patent-Pool. |

## Gesamturteil — Wem kann man trauen?

**Brauchbar für:** Erste qualitative Orientierung zu Geographie (UC6), Förder-Landschaft (UC4) und Konvergenz-Topologie (UC5). Diese Panels liefern kohärente, plausible Zahlen, die mit der öffentlichen Wahrnehmung der Perovskit-Forschung (Europa-stark, HORIZON-getrieben, Photovoltaik-CPC-Cluster) zusammenpassen.

**Gefährlich für:**
- **Publikations-/Impact-Entscheidungen**: Header 0, UC7 100, UC13-impliziert 2.982 — jede Budget-Aussage auf dieser Basis wäre Roulette.
- **Patent-Volumen-Entscheidungen**: Header 101 Patente vs. UC12 5.462 Anmeldungen — Größenordnung unklar.
- **Reifegrad-Entscheidungen**: R² = 1,000 + Header-Doppelphase „Reife Rückläufige Entwicklung" vs. Panel „Reife" allein. Der Widerspruch zwischen CAGR (+4,1 % Patente, +9,8 % Projekte) und „Rückläufiger Entwicklung" im Header macht die Phasenaussage unbrauchbar.
- **Wettbewerbs-Entscheidungen**: Header „wettbewerbsintensiv" vs. Panel „niedrige Konzentration" — widersprüchliches Framing, HHI-Wert fehlt.
- **Taxonomie-/Förderfokus-Entscheidungen**: UC10 mit nur 1 Feld und mathematisch unmöglichem Shannon-Wert ist nicht belastbar.

**Ampel-Bilanz:** 3× 🟢 · 4× 🟡 · 6× 🔴 → Mehrheit der UCs liefert nicht das versprochene Paket. Ein Budget-Entscheider würde auf dieser Dashboard-Grundlage mehrfach in widersprüchliche Richtungen gelenkt.

## Kern-Gap-Muster

1. **Populationsgröße-Inkonsistenz** quer durch UCs: 9 / 39 / 280 Akteure, 101 / 5.462 Patente, 0 / 100 / 2.982 Publikationen, 140 / 134 Projekte — jede UC zieht aus einem anderen Pool.
2. **Header ist Zweit-Layer, nicht Summary**: Header-Labels („0 Publikationen", „Rückläufige Entwicklung", „wettbewerbsintensiv") widersprechen den Panel-Daten direkt, statt sie zu verdichten.
3. **Metrik-Placeholder ohne Wert**: HHI ohne Zahl (UC3), h-Index ohne Zahl (UC7), Radar-Dimensionen ohne Zahlen (UC9) — Versprechen angekündigt, nicht geliefert.
4. **Mathematisch unmögliche Werte**: R² = 1,000 (UC2), Shannon 4,87 bei k=1 (UC10) — Signal, dass die Fit-/Diversitäts-Berechnung nicht abgesichert ist.
