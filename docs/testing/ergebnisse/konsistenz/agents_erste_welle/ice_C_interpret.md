# Konsistenz-Audit – Rolle C (Interpreter)
## Technologie: **internal combustion engine (ICE)**

> Stand: 2026-04-14 · Quelle: `raw_ice.json` · Rolle: Interpreter (Versprechen vs. Lieferung)

---

## Kopfzeile (Executive-Summary des Dashboards)

`INTERNAL COMBUSTION ENGINE | 10.2K Patente | 48 EU-Projekte | 0 Publikationen | Phase: Reife | Rückläufige Entwicklung | Wettbewerbsintensiver Markt | €160M Förderung | Moderater Forschungsimpact`

## Kritischer Befund vorweg (Struktur-Problem des Dumps)

Für **alle 13 Tabs** enthält das Input-JSON **denselben `mainText`** — und dieser Text ist ausschließlich der **Landing-/Cluster-Overview** (Executive-Header + Cluster-Beschreibungstexte „Dieser Analysebereich umfasst …"). `activeTab` meldet für jeden Tab `"Neue Analyse"` statt des jeweiligen UC-Tabs.

**Interpretation:** Der Dashboard-Drilldown hat beim Erfassungslauf für ICE **nicht stattgefunden** — entweder hat der Tab-Switch nicht gegriffen, oder die UC-Panels sind für diese Technologie grundsätzlich nicht aufrufbar (z. B. weil die Cluster-Startseite nicht verlassen wurde). In keinem Panel-Text finden sich Panel-spezifische Nutzdaten (keine HHI-Zahl, keine CAGR, keine Länderliste, keine Top-Akteure, keine CPC-Klassen, keine h-Index-Werte, keine Jahresreihe, kein R², keine Grant-Rate).

Das macht eine belastbare „Versprechen-erfüllt"-Bewertung pro UC **unmöglich**. Die untenstehende Ampel-Tabelle bewertet daher konsequent **den ausgelieferten Inhalt** (nicht die theoretische Fähigkeit des Radars für andere Techs).

---

## Bewertung je Use Case

| UC | Versprechen (Cluster-Info) | Tatsächliche Lieferung im Dump | Ampel | Begründung |
|---|---|---|---|---|
| **UC1** Aktivitätstrends | Zeitreihe Patente/Projekte/Publikationen, CAGR, Dynamik | Kein Chart, keine Jahreszahlen, kein CAGR-Wert; nur Kopf „10.2K Patente / 48 EU-Projekte / 0 Publikationen" und Phrase „Rückläufige Entwicklung" | 🔴 | Kein einziger Jahres- oder Wachstumswert zu ICE im Panel — CAGR-Versprechen nicht eingelöst. |
| **UC2** S-Kurve & Reife | Phase (Emerging/Growth/Mature/Declining), S-Kurven-Fit, R² | Nur Label `Phase: Reife` im Header — kein S-Kurven-Chart-Text, kein R², kein Wendepunkt, keine Gleichung | 🔴 | Phase als bloßer Badge ohne Evidenz. Für eine Entscheidung „einsteigen/aussteigen" unbrauchbar. Bei rückläufigem Trend + Phase „Reife" fehlt jede Fit-Qualität. |
| **UC5** Technologiekonvergenz | CPC-Konvergenz-Matrix, Whitespace-Lücken | Keine CPC-Klassen, keine Konvergenz-Paare, keine Whitespace-Liste | 🔴 | Panel liefert nichts — das Whitespace-Versprechen, das für ICE (alternative Kraftstoffe, Hybrid-Brücken) strategisch entscheidend wäre, ist leer. |
| **UC3** Wettbewerb & HHI | HHI-Wert, Top-Akteure | Nur Badge „Wettbewerbsintensiver Markt" — weder HHI-Zahl noch Top-N-Liste sichtbar | 🔴 | Bei 10.2K Patenten wäre hier die wichtigste Aussage (HHI, Bosch/Toyota/Denso/…) — komplett nicht geliefert. |
| **UC8** Dynamik & Persistenz | Neue Einstiege, Persistente, Ausgeschiedene Akteure | Keine Akteursbewegungen, keine Periodenvergleiche | 🔴 | Gerade bei einer reifen, rückläufigen Technologie (ICE) wäre „Wer steigt aus?" die Kernfrage — null Evidenz. |
| **UC11** Akteurs-Typen | Breakdown Hochschule/Forschung/Industrie/öffentlich | Keine Prozentwerte, keine Balken, keine Typ-Liste | 🔴 | Kein Mix-Wert — Versprechen nicht eingelöst. |
| **UC4** Förderung | EU-Fördervolumen nach Gebiet und Zeit | Nur Kopf-Zahl „€160 M Förderung" — keine Jahresreihe, keine Gebietsaufteilung, kein Projekt-Budget-Mapping | 🟡 | Gesamtsumme existiert, aber die versprochene Zeit- und Gebiets-Dimension fehlt vollständig. Für 48 Projekte ist die Aggregatzahl kaum handlungsleitend. |
| **UC7** Forschungsimpact | h-Index, Zitationsraten, Top-Institutionen | Nur Label „Moderater Forschungsimpact" im Header — kein h-Index-Wert, keine Institutsliste, keine Zitationsrate | 🔴 | Qualitatives Label ohne jede Zahl. Bei `0 Publikationen` im Header ohnehin zweifelhaft (siehe UC13). |
| **UC13** Publikationen | CORDIS-Pubs × Projekte, Publikationseffizienz | Header meldet `0 Publikationen`; keine Effizienz-Matrix | 🔴 | Harter Konflikt: 0 Publikationen, aber UC7 deklariert „moderaten Impact" — mindestens eines der beiden Panels ist widersprüchlich oder leer. Versprechen nicht erfüllt. |
| **UC6** Geographie | Globale Verteilung, EU-Anteil, Top-Länder | Keine Länder, keine Prozente, keine Karte-Daten im Text | 🔴 | Für eine automotive-dominierte Technologie (DE/JP/US-Cluster erwartbar) ist das Fehlen jeder Länderliste ein Totalausfall. |
| **UC9** Tech-Cluster | 5-dim Profil (Aktivität, Vielfalt, Dichte, Kohärenz, Wachstum) | Keine der 5 Dimensionen als Wert vorhanden | 🔴 | Radar-Chart-Daten komplett nicht geliefert. |
| **UC10** EuroSciVoc | Zuordnung zu Wissenschaftsdisziplinen | Keine Taxonomie-Pfade, keine Prozente | 🔴 | Versprechen nicht eingelöst. |
| **UC12** Patenterteilung | Grant-Rate + Time-to-Grant | Weder Grant-Rate-Prozent noch Median-Monate | 🔴 | Bei 10.2K Patenten wäre das die belastbarste Kennzahl der ganzen Analyse — fehlt. |

**Ampel-Summe:** 0× 🟢 · 1× 🟡 (UC4, nur weil Kopfzahl existiert) · 12× 🔴

---

## Querlesen: Widersprüche im Header selbst

- **„0 Publikationen" vs. „Moderater Forschungsimpact":** Ohne Publikationen ist ein nicht-trivialer Impact-Score kaum begründbar. Entweder die Publikations-Zählung greift für ICE nicht (Mapping-Lücke CORDIS ↔ Tech-Keyword), oder das Impact-Label ist heuristisch aus Patentzitationen erzeugt — in beiden Fällen Interpretationsfalle.
- **„Phase: Reife" + „Rückläufige Entwicklung":** Konsistent — eine reife, deklinierende Technologie. Aber ohne S-Kurve und R² ist das ein Label, keine Evidenz.
- **„10.2K Patente" vs. nur „€160 M Förderung" und „48 EU-Projekte":** Plausibel (ICE ist historisch industriegetrieben, EU-Forschungsgeld fließt primär in E-Mobility/H2), aber ohne UC4-Detail nicht belegt.

---

## Kurzzusammenfassung – Für welche Entscheidungen ist dieses Radar bei ICE brauchbar / gefährlich?

### Brauchbar

- **Als Ampel-Signal auf oberster Ebene**: Header-Etiketten („Reife", „rückläufig", „€160 M EU-Förderung", „10.2K Patente") liefern eine grobe, plausibel wirkende Positionierung. Für einen ersten Sortier-Blick („ICE ist keine Wachstums-Wette") reicht das.

### Gefährlich / unbrauchbar

- **Für jede konkrete Investitions-, Förder- oder F&E-Entscheidung**: Kein einziges der 13 Panels liefert im vorliegenden Dump belastbare Detail-Zahlen zu ICE. Wer auf Basis dieser Ansicht Budget allokiert (z. B. „in welches CPC-Feld einsteigen?", „welcher Wettbewerber dominiert?", „welche Region aufbauen?"), hat **keine Datengrundlage**, sondern nur die Kopf-Slogans.
- **Besonders kritisch**: S-Kurven-Phase („Reife") ohne R² und Fit-Qualität, Impact-Label ohne h-Index, „wettbewerbsintensiv" ohne HHI. Das sind genau die Stellen, an denen ein Entscheider mit Budget Vertrauen fassen würde — und sie sind unbelegt.
- **Dump-Hinweis**: Da `activeTab = "Neue Analyse"` in allen Panels steht und der `mainText` durchgängig der Cluster-Overview ist, ist das Erfassungsproblem **entweder ein Capture-Bug** (Tab-Switch nicht ausgeführt) **oder ein echtes UI-Problem** (UC-Panels öffnen für ICE nicht). In beiden Fällen ist das Dashboard für ICE im aktuellen Zustand **nicht entscheidungsfähig** — und die bloße Existenz von Header-Kennzahlen suggeriert fälschlich, es sei eine Analyse vorhanden.

### Empfehlung

1. Erfassungslauf für ICE wiederholen und verifizieren, dass die Tabs aktiv geschaltet werden (`activeTab` darf nicht `"Neue Analyse"` bleiben).
2. Header-Label „Moderater Forschungsimpact" bei `0 Publikationen` suppressen oder explizit auf Patentzitationen zurückführen.
3. Mindestens UC3 (HHI) und UC12 (Grant-Rate) sollten für eine Tech mit 10.2K Patenten hart gefüllt sein — wenn das Panel leer ist, ist ein „Keine Daten"-Hinweis ehrlicher als ein leerer Chart-Container.
