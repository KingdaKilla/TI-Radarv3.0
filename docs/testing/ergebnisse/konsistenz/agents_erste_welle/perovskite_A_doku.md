# Konsistenz-Audit A (Dokumentation): perovskite solar cell

_Rolle A — reines Protokoll, keine Interpretation. Datenquelle: `docs/testing/ergebnisse/konsistenz/raw/raw_perovskite.json`._

## Header (Executive-Summary-Kopfzeile)

| Feld | Wert |
|---|---|
| Technologie | PEROVSKITE SOLAR CELL |
| Patente | **101** |
| EU-Projekte | **140** |
| Publikationen | **0** |
| Phase | **Reife** |
| Entwicklung | Rückläufige Entwicklung |
| Markt | Wettbewerbsintensiver Markt |
| Förderung | **€222M** |
| Forschungsimpact | Hoher Forschungsimpact |

## Allgemeiner Befund zum Dump

Alle 13 Panels im JSON liefern **identischen** `mainText` (~2.500 Zeichen): Kopfzeile + die Cluster-Info-Boilerplate („Dieser Analysebereich umfasst: … Klicken zum Zurueck …"). Das `activeTab`-Feld lautet in **jedem** Panel `"Neue Analyse"` statt des erwarteten Tab-Namens. Es wurden für perovskite solar cell **keine panel-spezifischen Nutzdaten** erfasst (keine HHI-Zahlen, keine CAGR-Werte, keine Länder-Rankings, keine h-Index-/Zitations-Werte, keine CPC-Klassen, keine Jahreszeiträume, keine Akteurs-Typ-Prozente, keine Grant-Rate, keine EuroSciVoc-Zuordnungen, keine Konvergenz-Whitespaces).

Das bedeutet: Der Snapshot zeigt die **Landing-/Intro-Ansicht** eines jeden Tabs, nicht den tatsächlich gerenderten Panel-Inhalt. Inhaltlich ist pro UC nur ablesbar, was ohnehin schon in der Header-Zeile steht (Patent-/Projekt-/Publikationszahl, Phase-Badge, Förderungs-Summe, Impact-Label).

## Tabelle: UC × beobachtete Kern-Metrik(en)

| UC | Tab | Beobachtete panelspezifische Metriken im Dump |
|---|---|---|
| UC1 Technologie-Landschaft | Aktivitätstrends | Keine (nur Header-Zahlen 101 Patente / 140 EU-Projekte / 0 Publikationen; keine Zeitreihe, kein CAGR-Wert) |
| UC2 Reifegrad-Analyse | S-Kurve & Reife | Nur Phase-Badge aus Header: **„Reife / Rückläufige Entwicklung"**. Kein R², keine Kurven-Parameter, keine Jahresspanne |
| UC5 Cross-Tech Intelligence | Technologiekonvergenz | Keine CPC-Paare, keine Whitespace-Liste, keine Konvergenz-Werte |
| UC3 Wettbewerbsanalyse | Wettbewerb & HHI | Nur Textbaustein „Wettbewerbsintensiver Markt" aus Header. **Kein HHI-Wert, keine Akteurs-Top-Liste** |
| UC8 Zeitliche Entwicklung | Dynamik & Persistenz | Keine Einsteiger-/Persistent-/Ausgeschieden-Zahlen |
| UC11 Akteurs-Typen | Akteurs-Typen | Keine Anteile Hochschule/Forschung/Industrie/öffentlich |
| UC4 Förderungsanalyse | Förderung | Nur Gesamtsumme aus Header: **€222M**. Keine Gebiets-/Jahr-Breakdowns, keine Projekt-Budget-Liste |
| UC7 Forschungsimpact | Forschungsimpact | Nur Label „Hoher Forschungsimpact" aus Header. **Kein h-Index, keine Zitationsrate, keine Top-Institutionen** |
| UC13 Publikations-Impact | Publikationen | Header meldet **0 Publikationen**. Keine Pub/Project-Kennzahl, keine CORDIS-Liste |
| UC6 Geographische Verteilung | Geographie | Keine Länder-Top3, keine EU-Anteile, keine Share-Prozente |
| UC9 Technologie-Cluster | Tech-Cluster | Keine 5-dim Radar-Werte (Aktivität/Vielfalt/Dichte/Kohärenz/Wachstum) |
| UC10 EuroSciVoc | EuroSciVoc | Keine Disziplin-Zuordnungen, keine Interdisziplinaritäts-Kennzahl |
| UC12 Erteilungsquoten | Patenterteilung | Keine Grant-Rate, keine Time-to-Grant, kein Ziel-/Vergleichsjahr |

## Warnungen — Panels ohne Nutzdaten / „Keine Daten" / nur 0

Im vorliegenden Dump gilt dies **für alle 13 Panels**: Keines liefert panel-spezifische Zahlen über das hinaus, was bereits im Executive-Summary-Header steht.

Spezifische, belastbare Nullsignale direkt aus dem Header:

- **UC13 Publikations-Impact:** Header nennt **0 Publikationen** — Panel ist de facto datenleer (konsistent mit Header).
- **UC1 / UC2 / UC4:** Header liefert Aggregate (101 / 140 / €222M, Phase „Reife"), aber das zugehörige Panel-Detail (Zeitreihe, S-Kurve-Fit, Fördergebiete) ist im Dump **nicht enthalten**.
- **UC3 / UC6 / UC7 / UC9 / UC10 / UC11 / UC12 / UC5 / UC8:** Keine konkreten Zahlen aus dem Panel selbst erfasst.

## Hinweis zur Daten-Erhebung

Da jedes Panel `activeTab: "Neue Analyse"` trägt und der `mainText` in allen 13 Einträgen byteidentisch ist, stammt der Dump offenbar aus einem Zustand, in dem die Tab-Inhalte noch nicht gerendert waren (z. B. Analyse-Intro / Cluster-Auswahlebene). Für einen sauberen Konsistenz-Vergleich muss der Durchlauf mit tatsächlich aktivierten Tabs wiederholt werden. Alle Aussagen oben beziehen sich ausschließlich auf die protokollierten Inhalte — nicht auf das, was das Live-System beim Öffnen der jeweiligen Tabs möglicherweise darstellen würde.
