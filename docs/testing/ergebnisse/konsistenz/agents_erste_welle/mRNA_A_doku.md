# mRNA — Rolle A · Dokumentation

Quelle: `docs/testing/ergebnisse/konsistenz/raw/raw_mRNA.json`
Audit-Datum: 2026-04-14

## Header (Executive Summary)

| Feld | Wert |
|---|---|
| Technologie | **mRNA** (Label: `MRNA Technologie-Intelligence Analyse`) |
| Patente | **742** |
| EU-Projekte | **307** |
| Publikationen | **311,5K** |
| Phase-Badge | **Reife** |
| Trend-Label | **Rückläufige Entwicklung** |
| Wettbewerb-Label | **Wettbewerbsintensiver Markt** |
| Förderung | **€446M** |
| Impact-Label | **Sehr hoher Forschungsimpact** |

## Methodischer Hinweis zum Dump

Für alle 13 Tabs ist `activeTab = "Neue Analyse"` und der `mainText` ist für jedes Panel **byteidentisch** (2 500 Zeichen). Der Dump zeigt damit ausschließlich den Landing-/Overlay-Zustand der Analyse-Seite: Executive-Summary-Kopfzeile + die vier Cluster-Beschreibungs-Blöcke („Geographische Perspektive / Technologie & Reife / Marktakteure / Forschung & Förderung", jeweils mit dem Hinweis `Dieser Analysebereich umfasst:` und generischem UC-Beschreibungstext).

Es sind **keine Panel-Nutzdaten** (Chart-Labels, KPIs, Top-Listen, Jahreszahlen, Länder-Flags, CPC-Codes, HHI-Werte, h-Index, CAGR, R², Grant-Rate, Zeiträume etc.) aus dem JSON extrahierbar. Die einzigen harten Zahlen stammen aus der pro Tab wiederholten Header-Zeile.

## UC × beobachtete Kern-Metriken

| UC | Tab | Beobachtbare Kern-Metriken im Dump |
|---|---|---|
| UC1 Technologie-Landschaft | Aktivitätstrends | keine (nur Header: 742 Pat. / 307 Proj. / 311,5K Pub.) |
| UC2 Reifegrad-Analyse | S-Kurve & Reife | nur Phase-Badge aus Header: **Reife**; kein R², keine Zeitreihe, kein Fit-Endjahr |
| UC5 Cross-Tech Intelligence | Technologiekonvergenz | keine CPC-Klassen, keine Konvergenz-Paare, keine Whitespaces |
| UC3 Wettbewerbsanalyse | Wettbewerb & HHI | nur Label „Wettbewerbsintensiver Markt"; **kein HHI-Wert**, keine Top-Akteure |
| UC8 Zeitliche Entwicklung | Dynamik & Persistenz | keine Neueinstiege/Persistente/Ausgeschiedene, keine Counts |
| UC11 Akteurs-Typen | Akteurs-Typen | keine Aufteilung Hochschule/Forschung/Industrie/öffentlich, keine Prozente |
| UC4 Förderungsanalyse | Förderung | nur Header-Summe **€446M**; keine Jahresverteilung, keine Forschungsgebiete, keine Projektzahl auf Panel-Ebene |
| UC7 Forschungsimpact | Forschungsimpact | nur Label „Sehr hoher Forschungsimpact"; **kein h-Index**, keine Zitationsrate, keine Top-Institutionen |
| UC13 Publikations-Impact | Publikationen | nur Header-Volumen **311,5K**; keine Pub/Project-Ratio, keine CORDIS-Aufschlüsselung |
| UC6 Geographische Verteilung | Geographie | **keine Länder-Top3**, kein EU-Anteil, keine Shares |
| UC9 Technologie-Cluster | Tech-Cluster | keine 5-Dim-Werte (Aktivität/Vielfalt/Dichte/Kohärenz/Wachstum) |
| UC10 Wissenschaftsdisziplinen | EuroSciVoc | keine Disziplin-Top-Liste, keine EuroSciVoc-Knoten |
| UC12 Erteilungsquoten | Patenterteilung | **keine Grant-Rate**, keine Time-to-Grant |

## Warnung-Liste („keine Daten" / leer / 0 sichtbar im Dump)

Die folgenden Panels liefern im erfassten Dump **keine panel-spezifischen Nutzdaten** — der Dump zeigt nur das Landing-Overlay. Ob das am Dashboard selbst oder am Aufzeichnungsvorgang liegt, lässt sich aus der JSON allein nicht unterscheiden; dokumentiert wird der beobachtete Zustand:

- UC1 Aktivitätstrends — leer (kein CAGR, keine Zeitreihe)
- UC2 S-Kurve & Reife — leer (kein R², kein Fit, nur Badge „Reife" aus Header)
- UC5 Technologiekonvergenz — leer (keine CPC-Paare)
- UC3 Wettbewerb & HHI — leer (kein HHI-Wert, keine Akteursliste)
- UC8 Dynamik & Persistenz — leer
- UC11 Akteurs-Typen — leer (keine Breakdown-Prozente)
- UC4 Förderung — Panel-Detailebene leer (nur Header-€446M)
- UC7 Forschungsimpact — leer (kein h-Index)
- UC13 Publikationen — Panel-Detailebene leer (nur Header-311,5K)
- UC6 Geographie — leer (keine Länder, kein EU-Share)
- UC9 Tech-Cluster — leer (keine 5-Dim-Werte)
- UC10 EuroSciVoc — leer (keine Disziplinen)
- UC12 Patenterteilung — leer (keine Grant-Rate)

## Beobachtete Header-Konsistenz über Tabs

Header-Zeile (742 Patente / 307 EU-Projekte / 311,5K Publikationen / Phase: Reife / €446M / Sehr hoher Forschungsimpact) ist in allen 13 Tab-Dumps **identisch und stabil**. Das Schlagwort-Cluster der Labels „Rückläufige Entwicklung" + Phase „Reife" + „Wettbewerbsintensiver Markt" + „Sehr hoher Forschungsimpact" erscheint ebenfalls unverändert.
