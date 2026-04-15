# Agent C · Interpreter · autonomous driving

**Tech:** autonomous driving
**Datum:** 2026-04-14
**Input:** `raw3_autonomous.json`
**Rolle:** C (Interpreter) — Versprechen-vs-Lieferung pro UC

## Header-Kontext (Kurzüberblick)

- 734 Patente | 235 EU-Projekte | **0 Publikationen** (Header) | Phase: **Reife + Rückläufige Entwicklung** (Doppelphase!) | Wettbewerbsintensiver Markt | €755M Förderung | Sehr hoher Forschungsimpact.
- Der Header kombiniert widersprüchliche Signale (0 Pub. laut Header vs. 199 Pub. in UC7; Phase-Doppelung; "wettbewerbsintensiv" vs. UC3 "Niedrige Konzentration").

## Bewertung pro Use Case

| UC | Versprechen | Liefert laut Panel | Ampel | Begründung |
|---|---|---|---|---|
| UC1 Aktivitätstrends | Patent/Projekt/Pub-Trend + CAGR | Patente CAGR 11.7 %, Projekte CAGR 8.4 %, 5 Top-CPC (B60W60/001 mit 2.077 Treffern u. a.), Jahresachse 2017–2026, Warnhinweis vorhanden | 🟢 | Konkrete Zahlen, plausible Kernklassen (Fahrerassistenz/Autopilot), Warnhinweis korrekt gesetzt. Nur Publikations-Trend fehlt im Panel. |
| UC2 S-Kurve & Reife | Reifephase per Sigmoid-Fit (R², Wendepunkt, Konfidenz) | Phase **Reife**, R² = 0,999, Wendepunkt 2021, Konfidenz 95 %, Jahresachse 2016–2026 inkl. 2025/26 | 🟡 | R² 0,999 ist "zu gut" — bei 734 Patenten plausibel, aber Header widerspricht sich selbst mit "Reife + Rückläufige Entwicklung". UC2 selbst nennt nur "Reife" → Doppelphase ist Header-Artefakt. |
| UC5 Technologiekonvergenz | CPC-Kookkurrenz + Whitespace-Lücken | 10 CPC-Klassen, Ø Jaccard 0,224, 3 Whitespace-Lücken, CPC-Liste (B60W, G05D, G06V, G08G, G01C, G06F, G06N, B60Y, G01S, B60K) | 🟢 | Alle versprochenen Dimensionen geliefert; CPC-Auswahl inhaltlich stimmig für autonomes Fahren (Fahrzeugführung + Sensorik + ML). |
| UC3 Wettbewerb & HHI | HHI + Top-Anmelder | "Niedrige Konzentration", 8 Top-Anmelder sichtbar (Fraunhofer, TU-Austrian, KTH, Virtual Vehicle, Chalmers, NXP, RWTH, Lund) | 🟡 | HHI-Wert fehlt numerisch; Label "Niedrige Konzentration" widerspricht direkt dem Header-Etikett "Wettbewerbsintensiver Markt". Top-Anmelder sind EU-Forschungseinrichtungen — für einen Tech-Markt mit Tesla/Waymo/Bosch inhaltlich auffällig schief (nur CORDIS-Projekt-Koordinatoren, keine globalen Patent-Assignees). |
| UC8 Dynamik & Persistenz | Akteursdynamik | 12 Akteure, "Schrumpfend (−293 netto)", Jahresachse 2016–2026, Warnhinweis vorhanden | 🟡 | Widerspruch: 12 Akteure → aber −293 Netto-Veränderung macht bei Basis 12 keinen Sinn. Hier vermischen sich vermutlich zwei Aggregationsebenen (Gesamt-Akteurs-Delta vs. Snapshot); nicht entscheidungstauglich ohne Erklärung. |
| UC11 Akteurs-Typen | HES/PRC/PUB/KMU-Breakdown | 1.274 Akteure, Dominiert: **KMU / Unternehmen**, 5 Kategorien gelistet | 🟢 | Versprechen geliefert; 1.274 Akteure kontrastieren jedoch mit UC8 "12 Akteure" — Versprechen innerhalb UC11 erfüllt, aber cross-UC fragwürdig. |
| UC4 Förderung | EU-Fördervolumen + Instrumentenverteilung | 754,8 Mio. EUR, 235 Projekte, 16 Instrumente aufgelistet (IA, RIA, HORIZON-RIA/JU-IA/IA/ERC, SME-2, MSCA-ITN, ERC-ADG/COG/STG, …) | 🟢 | Beste Lieferung des Dashboards — konsistent mit Header (€755M ≈ €754,8M), Instrumentenvielfalt plausibel für EU-Projekt mit breitem Mandat. |
| UC7 Forschungsimpact | h-Index / Zitationen / Top-Institutionen | **199 Publikationen**, 319,5 Zitate/Pub., 15 Institutionen, Warnhinweis vorhanden | 🟡 | h-Index fehlt explizit; 319,5 Zitate/Pub. ist außergewöhnlich hoch (im Schnitt 50–100 üblich) → entweder Top-Paper-Bias oder Rechenfehler. Widerspruch zu Header "0 Publikationen". |
| UC13 Publikationen | Pub/Projekt + DOI-Anteil | 60,0 Pub/Projekt, DOI 27 %, Jahresachse 2016–2024 (endet 2024!) | 🔴 | Rechnung: 60 × 235 Projekte = 14.100 Publikationen — steht in krassem Widerspruch zu UC7 (199 Pub.) und Header (0 Pub.). Drei sich gegenseitig ausschließende Publikations-Zahlen im selben Dashboard. Kein Warnhinweis, obwohl Achse nur bis 2024 reicht. |
| UC6 Geographie | Länderverteilung + Kollaboration | 10 Länder, Top DE, Liste (DE/FR/SE/IT/UK/NL/CH/ES/BE/AT) | 🟡 | Länder-Top-Liste geliefert, Kollaborationsmuster (Versprechen!) fehlt komplett. Zudem: kein einziges außereuropäisches Land — reflektiert CORDIS-Scope, nicht den globalen AD-Markt (US/CN/JP fehlen). |
| UC9 Tech-Cluster | 5-dim Profil (Aktivität/Vielfalt/Dichte/Kohärenz/Wachstum) | 5 Cluster, 52 Akteure, 238 CPC-Klassen; 5 Radar-Dimensionen benannt; CPC-Sections A/B/E/G/H | 🟡 | Dimensionen aufgeführt, aber **keine numerischen Werte** je Dimension sichtbar → Radar-Chart nicht interpretierbar aus Paneltext. Versprechen "5-dim Profil" formal erfüllt, praktisch unlesbar. |
| UC10 EuroSciVoc | Wissenschaftsdisziplin-Taxonomie | **0 Felder**, 234 Projekte, Shannon 5,26, gelistet: sensors, autonomous vehicles, automation, optical sensors, software, radar, drones | 🔴 | "0 Felder" ist inkonsistent zu 7 sichtbaren Feldern und Shannon-Index 5,26 (Shannon > 0 setzt >1 Feld voraus). Projektzahl 234 ≠ Header-235 ≠ UC4-235. Inhaltlich stimmen die Felder für AD — aber der Zähler-Widerspruch macht das Panel unverlässlich. |
| UC12 Patenterteilung | Grant-Rate + Time-to-Grant | Quote 40,8 %, 30,8 Monate, **6.336 Anmeldungen**, 2.586 Erteilungen, Jahresachse 2016–2026, Warnhinweis vorhanden | 🔴 | Rechenkontrolle: 2.586/6.336 = 40,8 % ✓ — aber 6.336 Anmeldungen widerspricht Header "734 Patente" um Faktor 8,6. Entweder sind im UC12-Universum Family-Member/EP+WO mitgezählt oder der Header unterzählt massiv. Budget-Entscheider bekämen hier falsche Marktgröße. |

## Zusammenfassung: Brauchbarkeit für Entscheidungen

### Brauchbar (🟢):
- **UC4 Förderung**: €754,8M / 235 Projekte / Instrumenten-Mix — solide für "Welche EU-Instrumente greifen bei AD?".
- **UC1 Aktivitätstrends & UC5 Konvergenz**: Patent-Dynamik und Technologie-Nachbarschaften sind inhaltlich stimmig und erlauben qualitative Einschätzung der CPC-Landschaft.
- **UC11 Akteurs-Typen**: KMU-Dominanz ist plausibel kommunizierbar.

### Mit Vorsicht (🟡):
- **UC2 Reife**: Phase "Reife" ist in sich ok, aber Header-Doppelphase "Reife + Rückläufig" untergräbt die Botschaft.
- **UC3 Wettbewerb**: Top-Anmelder-Liste ist CORDIS-Koordinatoren-lastig — repräsentiert nicht den globalen Patentmarkt, was bei "autonomous driving" strategisch irreführend ist.
- **UC7 Impact**: 319,5 Zitate/Pub. so hoch, dass ein Entscheider vor Nutzung eine Methoden-Validierung bräuchte.
- **UC6 Geographie, UC8 Dynamik, UC9 Tech-Cluster**: Teilfunktional, aber Kern-Dimensionen fehlen oder sind widersprüchlich.

### Gefährlich (🔴):
- **UC13 Publikationen**: 60 Pub/Projekt × 235 ≈ 14.100 Publikationen — Header sagt 0, UC7 sagt 199. Drei-Wege-Widerspruch bei einer Kernmetrik.
- **UC10 EuroSciVoc**: "0 Felder" mit Shannon 5,26 und 7 gelisteten Feldern gleichzeitig — der Zähler ist kaputt, Projektzahl 234 ≠ 235.
- **UC12 Patenterteilung**: 6.336 Anmeldungen widersprechen Header-Patentzahl 734 um fast eine Größenordnung. Für "Wie groß ist der Patentmarkt?" hochgefährlich.

### Fazit für Budget-Entscheider

Ein Budget-Entscheider sollte dem Dashboard **nicht** blind vertrauen. Sicher nutzbar sind Förderung (UC4) und Aktivitäts-/Konvergenz-Signale (UC1/UC5). Alles was mit **Publikationen und Patent-Volumina** zu tun hat, ist durch drei verschiedene, sich widersprechende Zählungen (Header 0 / 734, UC7 199, UC12 6.336, UC13 implizit 14.100) inkonsistent und würde bei Investment-Entscheidungen ein massives Reputationsrisiko darstellen. Besonders kritisch: Der Header verkauft "0 Publikationen + sehr hoher Forschungsimpact" in einem Atemzug — das ist logisch unmöglich und wäre in einer Vorstands­präsentation ein sofortiger Glaubwürdigkeitsverlust.

## Brauchbarkeitsmatrix (verdichtet)

| Entscheidungsfrage | Brauchbar? |
|---|---|
| Wie groß ist das EU-Förderbudget für AD? | **Ja** (UC4) |
| Welche Forschungsakteure in der EU sind führend? | Ja, aber nur EU-Sicht (UC3/UC11) |
| Wie reif ist die Technologie? | Eingeschränkt — widersprüchliche Phase im Header |
| Wie viele Patente gibt es global? | **Nein** — Header 734 vs. UC12 6.336 |
| Wie stark ist die Publikationstätigkeit? | **Nein** — 0 vs. 199 vs. 14.100 |
| Welche Wissenschaftsdisziplinen dominieren? | Inhaltlich ja, Zähler kaputt (UC10 "0 Felder") |
| Wer sind die Top-Patent-Player weltweit? | **Nein** — Panel listet nur EU-Forschungseinrichtungen |
