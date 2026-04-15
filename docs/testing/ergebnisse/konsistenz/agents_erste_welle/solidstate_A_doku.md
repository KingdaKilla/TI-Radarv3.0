# Konsistenz-Dokumentation · Solid State Battery (Rolle A)

**Tech:** solid state battery
**Input:** `docs/testing/ergebnisse/konsistenz/raw/raw_solidstate.json`
**Datum Audit:** 2026-04-14

---

## 1 Header (Executive Summary aus Dashboard-Kopfzeile)

| Feld | Wert |
|---|---|
| Technologie | SOLID STATE BATTERY |
| Patente | **358** |
| EU-Projekte | **113** |
| Publikationen | **0** |
| Phase-Badge | **Reife · Stagnation** |
| Markt-Label | Wettbewerbsintensiver Markt |
| EU-Förderung | **€297 Mio.** |
| Impact-Label | Sehr hoher Forschungsimpact |

Rohtext: `SOLID STATE BATTERY | Technologie-Intelligence Analyse | 358 | Patente | 113 | EU-Projekte | 0 | Publikationen | Phase: Reife | Stagnation | Wettbewerbsintensiver Markt | €297M Förderung | Sehr hoher Forschungsimpact`

---

## 2 UC × beobachtete Kern-Metrik(en)

> **Wichtiger Befund zur Datenaufnahme:** Für Solid State Battery wurden alle 13 Tab-Dumps mit `activeTab = "Neue Analyse"` aufgezeichnet. Sämtliche `mainText`-Felder (13/13) sind **byte-identisch** (2500 Zeichen) und enthalten nur die Executive-Summary-Kopfzeile plus die vier Cluster-Info-Overlays (`Dieser Analysebereich umfasst: …`). **Kein einziger Panel-spezifischer Nutzdaten-Inhalt** (keine Chart-Labels, keine KPI-Zahlen, keine Top-Listen, keine Jahreszahlen aus Trends, keine HHI-/CAGR-/R²-/h-Index-Werte, keine Länder-Top-Listen, keine CPC-Klassen, keine Akteurs-Typ-Shares) wurde in der JSON festgehalten. Der Dump wurde offenbar aufgenommen, während noch die Cluster-Auswahl-/Intro-Ansicht aktiv war und die eigentlichen Panels nicht gerendert/geladen waren.

Daraus folgt für die UC-Tabelle: aus der JSON **ableitbar sind ausschließlich Header-Aggregate**, nicht die UC-spezifischen Detail-Metriken.

| Tab | UC | Beobachtete Kern-Metrik(en) in JSON | Status |
|---|---|---|---|
| Aktivitätstrends | UC1 Technologie-Landschaft | Nur Header-Zähler (358 Patente, 113 EU-Projekte, 0 Publikationen); kein CAGR-Wert, keine Jahresreihe, kein Zeitraum | Keine Paneldaten |
| S-Kurve & Reife | UC2 Reifegrad-Analyse | Nur Phase-Badge aus Header: `Reife · Stagnation`; kein R², keine S-Kurven-Parameter, keine Jahresspanne | Keine Paneldaten |
| Technologiekonvergenz | UC5 Cross-Tech Intelligence | Keine CPC-Klassen, keine Konvergenz-Zahlen, keine Whitespace-Liste | Keine Paneldaten |
| Wettbewerb & HHI | UC3 Wettbewerbsanalyse | Nur Markt-Label aus Header: `Wettbewerbsintensiver Markt`; kein HHI-Zahlenwert, keine Top-Akteure | Keine Paneldaten |
| Dynamik & Persistenz | UC8 Zeitliche Entwicklung | Keine Werte für Neue Einstiege / Persistente / Ausgeschiedene | Keine Paneldaten |
| Akteurs-Typen | UC11 Akteurs-Typen | Kein Breakdown (Hochschule / Forschung / Industrie / öffentlich) | Keine Paneldaten |
| Förderung | UC4 Förderungsanalyse | Nur Header-Summe: `€297M Förderung`; keine Budget-Reihe pro Jahr, keine Forschungsgebiete | Keine Paneldaten |
| Forschungsimpact | UC7 Forschungsimpact | Nur Header-Label: `Sehr hoher Forschungsimpact`; kein h-Index, keine Zitationsrate, keine Top-Institutionen | Keine Paneldaten |
| Publikationen | UC13 Publikations-Impact | Nur Header: `0 Publikationen`; keine Pub/Project-Ratio | Keine Paneldaten |
| Geographie | UC6 Geographische Verteilung | Keine Länder-Top-3, kein EU-Anteil, keine Anmelder-Verteilung | Keine Paneldaten |
| Tech-Cluster | UC9 Technologie-Cluster | Keine 5-dim-Werte (Aktivität/Vielfalt/Dichte/Kohärenz/Wachstum) | Keine Paneldaten |
| EuroSciVoc | UC10 Wissenschaftsdisziplinen | Keine Disziplinen-Liste, keine Projektzuordnungen | Keine Paneldaten |
| Patenterteilung | UC12 Erteilungsquoten | Keine Grant-Rate, keine Time-to-Grant | Keine Paneldaten |

---

## 3 Warnungen — Panels die leer / ohne Detaildaten sind

Aufgrund der Capture-Situation betrifft die Warnung **alle 13 Tabs**. Einordnung:

### 3.1 Hart beobachtbar aus Header (nicht aus Panel)

- `0 Publikationen` (Header) → UC13 Publikations-Impact müsste erwartungsgemäß leer / nur Nullen anzeigen. Selbst ohne Panel-Daten ist dieser 0-Wert ein Warnsignal im Zusammenspiel mit `113 EU-Projekten` (UC13 misst Publikations-Effizienz als Pub/Project — mit 0 Publikationen nicht sinnvoll berechenbar).
- `Phase: Reife · Stagnation` ist ein **Textlabel** im Header — in der JSON kein numerisches R² oder Jahresspanne hinterlegt, mit dem sich die Phase validieren ließe.

### 3.2 Nicht beurteilbar (weil Panel-Payload fehlt)

Alle 13 UC-spezifischen Detaildaten sind in diesem Capture **nicht vorhanden**. Das ist entweder
- ein **Capture-Artefakt** (Overlay war aktiv, Tabs wurden nicht tatsächlich geöffnet) — in diesem Fall sagt der Dump nichts über die echte Panel-Qualität aus, oder
- ein **Render-/Ladeproblem** der Live-App für diese Tech (Panels blieben leer und zeigten nur das Cluster-Info-Overlay) — dann wäre es ein harter UX-Bug.

Aus der vorliegenden JSON **ist beide Hypothesen nicht zu unterscheiden**. Die Inkonsistenz-Analyse (Rolle B) und das Gap-Urteil (Rolle C) müssen darauf hinweisen, dass für Solid State Battery kein aussagekräftiges Panel-Protokoll vorliegt.

### 3.3 Auffällige Header-Kombination (aus den vorhandenen Feldern)

| Beobachtung | Begründung Warnhinweis |
|---|---|
| 358 Patente + 113 EU-Projekte + 0 Publikationen | Extremer Ausreißer — 113 EU-geförderte Projekte ohne eine einzige erfasste CORDIS-Publikation ist ungewöhnlich und sollte in UC4/UC13 geprüft werden. |
| €297 Mio. Förderung bei 113 EU-Projekten | Ø ~€2,6 Mio./Projekt — plausible Horizon-Größenordnung, aber ohne Panel-Aufschlüsselung nicht validierbar. |
| Phase `Reife · Stagnation` | Wenn Patentanzahl 358 und Phase „Stagnation": die S-Kurven-Fit-Güte (R²) sowie das End-Jahr (2024/2025/2026?) sind kritisch — mit heutigem Stichtag 2026-04-14 ist das Jahr 2026 unvollständig. Ohne Paneldaten nicht prüfbar. |

---

## 4 Zusammenfassung für Rolle B / C

- Aus der JSON stehen für UC-Detailprüfungen **keine** numerischen Werte zur Verfügung.
- Verwertbar sind nur die sechs Header-Aggregate: 358 / 113 / 0 / Reife·Stagnation / €297M / Sehr hoher Forschungsimpact.
- Der Haupt-Konsistenz-Befund auf Header-Ebene ist die Kombination `113 EU-Projekte` ↔ `0 Publikationen`, die UC13 (Pub/Project) strukturell unterläuft.
