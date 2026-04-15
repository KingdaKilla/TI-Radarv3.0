# Konsistenz-Audit mRNA – Rolle B (Analyse)

**Technologie:** mRNA
**Input:** `docs/testing/ergebnisse/konsistenz/raw/raw_mRNA.json`
**Datum:** 2026-04-14

---

## Zusammenfassung der Datenlage

Der Dump für mRNA enthält **in allen 13 Panels identischen Text**: ausschließlich die Executive-Summary-Kopfzeile plus die generischen Cluster-Info-Beschreibungen ("Dieser Analysebereich umfasst: UC6 … UC9 … UC10 … UC12 …"). Für **alle 13 Panels** zeigt `activeTab` den Wert `"Neue Analyse"` statt des eigentlichen Analyse-Tabs. Es existieren **keinerlei Panel-Nutzdaten** (keine HHI-Zahl, kein CAGR-Wert, keine Länder-Top-Liste, kein h-Index, keine Grant-Rate, keine CPC-Klassen, keine Akteurs-Typ-Prozente, keine S-Kurven-Kennzahlen, keine Jahresreihen).

Eine inhaltliche Konsistenzprüfung zwischen Header und Detailpanels (Kern-Auftrag von Rolle B, Briefing-Punkte 1–8) ist deshalb **technisch unmöglich**. Die folgende Befundliste dokumentiert das als zentralen Critical-Defekt und führt zusätzlich die internen Widersprüche auf, die bereits im Header selbst nachweisbar sind.

---

## Befundliste

### CRITICAL

#### C-1 · Kein Panel hat Analysedaten geladen – Dashboard-Audit nicht durchführbar
- **Quelle:** alle 13 Panels (`Aktivitätstrends`, `S-Kurve & Reife`, `Technologiekonvergenz`, `Wettbewerb & HHI`, `Dynamik & Persistenz`, `Akteurs-Typen`, `Förderung`, `Forschungsimpact`, `Publikationen`, `Geographie`, `Tech-Cluster`, `EuroSciVoc`, `Patenterteilung`).
- **Original-Snippet (repräsentativ, alle 13 Panels identisch):** `"activeTab": "Neue Analyse"` sowie `"mainText": "MRNA Technologie-Intelligence Analyse 742 Patente 307 EU-Projekte 311.5K Publikationen … Dieser Analysebereich umfasst: UC6 Geographische Verteilung … UC9 Technologie-Cluster … UC10 Wissenschaftsdisziplinen … UC12 Erteilungsquoten …"` (ab hier bis zum Abschnitt schneidet der Dump ab).
- **Widerspruch:** Jeder Tab zeigt nur Header + Cluster-Übersicht – die eigentlich versprochenen UC-Panels (HHI, CAGR, S-Kurve, Länderverteilung etc.) sind offenbar nicht gerendert worden. Kopf-vs-Detail-Abgleich (Briefing-Punkte 1, 2, 3, 4, 5, 6, 7, 8) ist deshalb nicht prüfbar – es gibt kein "Detail".

#### C-2 · `activeTab` = "Neue Analyse" widerspricht Tab-Name
- **Quelle:** alle 13 Panels.
- **Original-Snippet:** z. B. Panel `Wettbewerb & HHI` → `"activeTab": "Neue Analyse"`.
- **Widerspruch:** Der Dumper hat als Panel-Key den Ziel-Tab (`Wettbewerb & HHI`) gespeichert, aber das aktive Tab im DOM heißt `Neue Analyse`. Entweder wurde der Tab-Wechsel nie vollzogen oder die jeweilige Analyse-Route ist durch einen globalen "Neue Analyse"-State überblendet worden → **das Dashboard liefert den Endnutzern bei mRNA vermutlich ebenfalls nur die Cluster-Landing-Page ohne Panel-Inhalte.**

### MAJOR

#### M-1 · "Phase: Reife" + "Rückläufige Entwicklung" im Header – ohne prüfbare S-Kurven-/CAGR-Basis
- **Quelle:** Header (sichtbar in allen 13 Panels).
- **Original-Snippet:** `"… Phase: Reife | Rückläufige Entwicklung | Wettbewerbsintensiver Markt …"`.
- **Widerspruch:** Der Header deklariert gleichzeitig "Reife" und "Rückläufige Entwicklung". Laut UC2-Versprechen sind *Mature* und *Declining* **zwei getrennte S-Kurven-Phasen**. Die Kombination ist fachlich uneindeutig (entweder Plateau oder Abstieg – nicht beides als Badge) und kann nicht gegen die S-Kurven-Detailwerte (R², Inflection-Year, CAGR 2015–2024) geprüft werden, weil das UC2-Panel keine Zahlen liefert (siehe C-1). Besonders kritisch, weil aktuelles Datum = 2026-04-14: ein CAGR-Fenster bis 2024/2025 würde unvollständige Jahre einrechnen und den Decline-Befund für eine Pandemie-getriebene Technologie wie mRNA künstlich verstärken (Briefing-Punkt 4 & 5).

#### M-2 · Publikations-Header 311.5K ist für einen einzelnen Technologie-Begriff unplausibel hoch
- **Quelle:** Header (`summary` + alle Panels).
- **Original-Snippet:** `"… 311.5K | Publikationen …"`.
- **Widerspruch:** 311 500 Publikationen für "mRNA" übersteigen die Größenordnung vergleichbarer CORDIS-Publikations-Pools um 2–3 Größenordnungen (zum Vergleich: gesamtes CORDIS hat nur ~1 Mio Publikationen). Ohne UC13-Detail (Pub/Project-Quote, Jahresreihe) lässt sich der Wert nicht verifizieren; Briefing-Punkt 8 verlangt genau diesen Abgleich – mangels UC13-Panel nicht möglich, aber die Zahl ist per se Major-verdächtig.

#### M-3 · "Wettbewerbsintensiver Markt" ohne HHI-Wert prüfbar
- **Quelle:** Header; UC3-Panel `Wettbewerb & HHI`.
- **Original-Snippet:** `"… Wettbewerbsintensiver Markt …"` (Header); UC3-Panel zeigt nur Cluster-Info `"UC3 Wettbewerbsanalyse Analysiert die Marktkonzentration (HHI) …"`.
- **Widerspruch:** Das Label "wettbewerbsintensiv" impliziert niedrigen HHI (< ~1500). Der zugehörige HHI-Zahlenwert wird im UC3-Panel nicht ausgegeben – Header-Aussage ist unverifizierbar. Briefing-Punkt 1 (Kopf-vs-Detail) nicht prüfbar.

#### M-4 · "€446M Förderung" nicht gegen UC4-Projektzahl/Budget-Breakdown abgleichbar
- **Quelle:** Header; UC4-Panel `Förderung`.
- **Original-Snippet:** Header `"… €446M Förderung …"`; UC4-Panel enthält nur `"UC4 Förderungsanalyse Zeigt "` (Text schneidet nach "Zeigt" ab).
- **Widerspruch:** Briefing-Punkt 1 + 7 verlangt Abgleich: Entspricht €446M dem Summenwert aus UC4-Breakdown? Stimmt die Projekt-Zahl mit Header-"307 EU-Projekte" überein? Der UC4-Text bricht bei `"Zeigt "` ab – es gibt keinen numerischen Nachweis, ob 307 Projekte tatsächlich €446M tragen oder ob 0-Projekt-Budget-Inkonsistenzen vorliegen.

#### M-5 · "Sehr hoher Forschungsimpact" ohne h-Index / Zitations-Beleg
- **Quelle:** Header; UC7-Panel `Forschungsimpact`.
- **Original-Snippet:** Header `"… Sehr hoher Forschungsimpact …"`; UC7-Panel zeigt keinerlei Zahlen.
- **Widerspruch:** Die qualitative Einstufung hat im Panel keine numerische Entsprechung (kein h-Index, keine mittlere Zitationsrate, keine Top-Institutionen). Briefing-Punkt 1 nicht prüfbar.

### MINOR

#### m-1 · Tech-Label "MRNA" (Großbuchstaben) inkonsistent zum Input-Key "mRNA"
- **Quelle:** `summary` + Header in allen Panels.
- **Original-Snippet:** `"tech": "mRNA"` (JSON-Root) vs. Header-Text `"MRNA | Technologie-Intelligence Analyse …"`.
- **Widerspruch:** Rendering-/CSS-Uppercase oder Daten-Inkonsistenz; rein kosmetisch, aber irritierend, da mRNA fachsprachlich klein-m/groß-RNA geschrieben wird.

#### m-2 · Header-Phrase "Geographische Perspektive" doppelt hintereinander
- **Quelle:** `summary` + alle Panels.
- **Original-Snippet:** `"… Sehr hoher Forschungsimpact Geographische Perspektive Geographische Perspektive Dieser Analysebereich umfasst: …"`.
- **Widerspruch:** Rendering-Glitch – Cluster-Titel wird doppelt ausgegeben. Kein numerisches Problem, aber Symptom dafür, dass der Dump denselben DOM-Baum für alle Panels eingefroren hat (passt zu C-2).

#### m-3 · Abgeschnittene UC4-Beschreibung
- **Quelle:** `Förderung`-Panel (und alle anderen, identisch).
- **Original-Snippet:** `"… Forschung & Förderung Dieser Analysebereich umfasst: UC4 Förderungsanalyse Zeigt "` (Text endet hier).
- **Widerspruch:** Die 2500-Zeichen-Begrenzung des Dumps schneidet mitten im UC4-Satz ab. Kein Konsistenzfehler des Dashboards an sich, aber Hinweis, dass unterhalb dieses Punktes auch keine UC4-Zahlen mehr folgen – was zu C-1 passt.

---

## Gesamt-Urteil (B)

- **1 × Critical (C-1/C-2 kombiniert):** Für mRNA liefert das Dashboard im aufgezeichneten Durchlauf **keinerlei Panel-Daten**. Damit fällt die komplette Rolle-B-Prüfliste (8 Checks) aus, weil es keinen "Detail"-Teil gibt, der den Header widerlegen oder bestätigen könnte.
- **5 × Major:** Der Header allein enthält eine fachlich uneindeutige Phase-Aussage (Reife + Rückläufig), eine unplausible Publikationszahl (311.5K) und drei qualitative Labels ("wettbewerbsintensiv", "€446M Förderung", "sehr hoher Forschungsimpact"), die keinen nachgelieferten Zahlenbeleg haben.
- **3 × Minor:** Rendering-Kosmetik (Uppercase, Doppel-Text, Dump-Cut).

**Empfehlung:** Vor jeder weiteren Konsistenzanalyse muss der Erfassungslauf für mRNA wiederholt werden – mit korrektem Tab-Wechsel, sodass die UC-Panels tatsächlich Nutzdaten rendern. Andernfalls ist der einzig belastbare Eindruck: **der Anwender, der im Live-System `app.drakain.de` das mRNA-Dashboard öffnet, sieht möglicherweise denselben leeren Zustand** (reine Cluster-Landing statt Zahlen) – was an sich bereits ein Produkt-Critical wäre.
