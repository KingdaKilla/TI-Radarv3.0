# Konsistenz-Audit TI-Radar v3 — Rolle C (Interpreter)

**Technologie:** autonomous driving
**Datenquelle:** `docs/testing/ergebnisse/konsistenz/raw/raw_autonomous.json`
**Datum:** 2026-04-14

## Ausgangslage

Header-Kennzahlen (Executive-Summary):

- 734 Patente
- 235 EU-Projekte
- 0 Publikationen
- Phase: **Reife**, Label "Rückläufige Entwicklung"
- Wettbewerbsintensiver Markt
- €755M Förderung
- Sehr hoher Forschungsimpact

**Kritische Beobachtung zum Rohdatensatz:** Alle 13 Panel-Einträge zeigen `activeTab: "Neue Analyse"` und liefern in `mainText` ausschließlich die Cluster-Landing-Overview-Texte (`Dieser Analysebereich umfasst: …`) plus den stets identischen Executive-Summary-Kopf. **Es sind keine panelspezifischen Nutzdaten im Dump enthalten** — weder HHI-Werte, CAGR-Zahlen, Top-Listen, h-Index, Grant-Rate noch CPC-Klassen. Das bedeutet: Entweder wurde beim Live-Durchlauf nie wirklich in einen Tab hineingeklickt (die Karten der Landing-Overview wurden nicht aufgelöst), oder die Panels rendern für "autonomous driving" tatsächlich keinen Inhalt. Für das Urteil "hält jeder UC sein Versprechen?" zählt beides gleich schwer: **der Entscheider sieht für keinen UC eine einzelne konkrete Kennzahl.**

## Bewertung je UC

| UC | Versprechen | Tatsächliche Lieferung im Dump | Ampel | Begründung |
|---|---|---|---|---|
| **UC1** Technologie-Landschaft | Patent-/Projekt-/Publikations-Zeitreihe, CAGR, Dynamik | Nur Summen im Header (734 / 235 / 0). Keine Zeitreihe, kein CAGR-Wert, keine Jahres-Labels. | 🔴 | Dynamik-Aussage "Rückläufige Entwicklung" steht isoliert ohne Chart oder Prozentwert. Nicht interpretierbar. |
| **UC2** Reifegrad-Analyse | S-Kurven-Fit, Phase, R²-Confidence | "Phase: Reife" im Header — ohne Kurve, ohne R², ohne Inflection-Year. | 🔴 | Phase wird behauptet, aber die Evidenz (S-Kurve) fehlt komplett. Klassisches Black-Box-Label. |
| **UC3** Wettbewerbsanalyse | HHI + dominante Akteure | Kein HHI-Wert, keine Akteursliste. Nur Floskel "Wettbewerbsintensiver Markt" im Header. | 🔴 | Ohne HHI-Zahl ist die Aussage reine Etikettierung. |
| **UC4** Förderungsanalyse | EU-Fördervolumen nach Gebiet + Zeitverlauf | €755M Gesamt im Header. Keine Aufteilung nach Thema/Jahr/Programm. | 🔴 | Zahl ist da, aber ohne Struktur — 755M über 10+ Jahre, ohne Top-Programme, ist nicht entscheidungstauglich. |
| **UC5** Cross-Tech Intelligence | CPC-Konvergenz + Whitespace-Lücken | Nichts. Keine CPC-Klasse, keine Matrix, keine Whitespace-Kandidaten. | 🔴 | Komplett leer. |
| **UC6** Geographische Verteilung | Globale Verteilung der Anmelder/Orgs | Nichts. Keine Länder, kein EU-Share, keine Top-3. | 🔴 | Komplett leer. |
| **UC7** Forschungsimpact | h-Index, Zitationsraten, Top-Institutionen | Nur Label "Sehr hoher Forschungsimpact" im Header. | 🔴 | Bei 0 Publikationen (!) ist das Label "Sehr hoher Forschungsimpact" inhaltlich unhaltbar — welche Impact-Basis wird genutzt? |
| **UC8** Zeitliche Entwicklung | Neue/Persistente/Ausgeschiedene Akteure | Nichts. Keine Zahlen zu Entries/Exits. | 🔴 | Komplett leer. |
| **UC9** Technologie-Cluster | 5-dim Profil (Aktivität/Vielfalt/Dichte/Kohärenz/Wachstum) | Nichts. Kein Radar, keine Dimensions-Werte. | 🔴 | Komplett leer. |
| **UC10** EuroSciVoc | Wissenschaftsdisziplinen-Zuordnung | Nichts. Keine Disziplin-Labels. | 🔴 | Komplett leer. |
| **UC11** Akteurs-Typen | Breakdown Hochschule/Forschung/Industrie/öffentlich | Nichts. Keine Prozentsätze, keine Typ-Summe. | 🔴 | Komplett leer. |
| **UC12** Erteilungsquoten | Grant-Rate + Time-to-Grant | Nichts. Keine Rate, keine Jahresangabe. | 🔴 | Komplett leer. |
| **UC13** Publikations-Impact | CORDIS-Publikationen × Projekte, Pub/Project | Header zeigt **0 Publikationen**. Kein Detail-Panel geladen. | 🔴 | 0 Publikationen macht Publikations-Impact-Analyse per Definition unmöglich — dennoch bleibt UC13 als Tab angeboten. Ehrlicher wäre eine "Keine Daten verfügbar"-Meldung. |

## Quer-Widersprüche (Header-Ebene)

Auch ohne Panel-Detaildaten fallen drei Header-Inkonsistenzen auf, die der Interpreter dem Entscheider nicht verschweigen darf:

1. **"0 Publikationen" + "Sehr hoher Forschungsimpact"** — semantisch unvereinbar. Impact setzt zitierte Arbeiten voraus; bei 0 Publikationen gibt es keinen messbaren Impact-Kanal.
2. **"Phase: Reife" + "Rückläufige Entwicklung"** — in der UC2-Taxonomie ist "Declining" eine **eigene** Phase neben "Mature". Die Kombination "Reife **und** rückläufig" ist inkonsistent mit der im Cluster-Info versprochenen 4-Phasen-Systematik (Emerging/Growth/Mature/Declining).
3. **"235 EU-Projekte" + "€755M Förderung"** entspricht rund €3,2M pro Projekt — plausibel für H2020/Horizon-Europe-Großprojekte, aber die Zahl ist nicht im Dump verifizierbar (UC4-Detail fehlt).

## Fazit: Für welche Entscheidungen ist das Radar bei `autonomous driving` brauchbar / gefährlich?

**Brauchbar (wenn überhaupt):**
- Grober Sanity-Check der Technologie-Größenordnung (Patente ~700, Projekte ~200, Fördervolumen hunderte Millionen Euro).
- Hinweis, dass es sich nicht um eine Emerging-Technologie handelt.

**Gefährlich / nicht entscheidungsreif:**
- **Investitions-/Markteintritts-Entscheidungen:** Ohne HHI-Wert, Top-Akteure, CAGR, Reifegrad-Evidenz (R²) ist keine fundierte Go/No-Go-Aussage möglich.
- **Forschungsstrategische Entscheidungen:** UC7-Label "Sehr hoher Forschungsimpact" bei 0 Publikationen ist irreführend — wer diesem Label vertraut, trifft Entscheidungen auf einem inkonsistenten Signal.
- **Portfolio-Positionierung:** UC5 (Konvergenz/Whitespace) und UC9 (5-dim Profil) liefern nichts — gerade die beiden UCs, für die das Radar sein Alleinstellungs-Versprechen reklamiert.
- **Patent-Strategie:** UC12 (Grant-Rate) komplett leer → keine Aussage zu Erteilungschancen/Zeitrahmen möglich.

**Gesamtampel: 🔴 für alle 13 UCs.** Das Radar liefert bei `autonomous driving` im aktuellen Dump **ausschließlich Landing-Page-Schlagworte** — und mindestens zwei dieser Schlagworte (Publikations-Impact bei 0 Pubs, Phase+Declining-Kombination) sind bereits auf Header-Ebene widersprüchlich. Ein Entscheider mit Budget sollte diesem Panel in der vorliegenden Form **nicht** trauen, ohne vorher direkt in die UC-Detail-Views zu klicken und dort Evidenz zu verifizieren.

**Empfehlung an das Produkt:** Entweder wurde der Live-Durchlauf technisch unsauber aufgezeichnet (Tabs wurden nicht aktiviert), oder die Tabs rendern tatsächlich keine Inhalte — in beiden Fällen muss (a) geprüft werden, warum `activeTab` für alle 13 Tabs auf `"Neue Analyse"` klemmt, und (b) die Header-Ampeln ("Sehr hoher Forschungsimpact" bei 0 Pubs) an die tatsächliche Datenlage gekoppelt werden.
