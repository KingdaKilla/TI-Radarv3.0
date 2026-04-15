# Konsistenz-Audit · Rolle A (Dokumentierer) · internal combustion engine

**Datum:** 2026-04-14  
**Quelle:** `docs/testing/ergebnisse/konsistenz/raw/raw_ice.json`  
**Live-System:** https://app.drakain.de

---

## 1 · Header (Executive-Summary-Kopfzeile)

| Feld | Wert (wie angezeigt) |
|---|---|
| Technologie | INTERNAL COMBUSTION ENGINE |
| Patente | **10.2K** |
| EU-Projekte | **48** |
| Publikationen | **0** |
| Phase | **Reife** |
| Trend-Label | Rückläufige Entwicklung |
| Wettbewerb-Label | Wettbewerbsintensiver Markt |
| Förderung | **€160M** |
| Impact-Label | Moderater Forschungsimpact |

Originalzeile:
> `INTERNAL COMBUSTION ENGINE | Technologie-Intelligence Analyse | 10.2K | Patente | 48 | EU-Projekte | 0 | Publikationen | Phase: Reife | Rückläufige Entwicklung | Wettbewerbsintensiver Markt | €160M Förderung | Moderater Forschungsimpact`

---

## 2 · UC × beobachtete Kern-Metriken

**Wichtige Vorbemerkung:** Für alle 13 Panels ist im Dump `"activeTab": "Neue Analyse"` gesetzt, und der `mainText` ist in allen 13 Panels **zeichengleich identisch**. Das heißt: Das Dashboard hat beim Capture die jeweiligen Tab-Inhalte **nicht geladen** — stattdessen wurde 13 mal derselbe Landing-/Overview-Text (Header + Cluster-Beschreibungstexte "Dieser Analysebereich umfasst: …") erfasst. Es liegt daher **keine einzige UC-spezifische Nutzdaten-Zeile** vor.

| UC | Tab | Beobachtete Kern-Metrik(en) im Dump |
|---|---|---|
| UC1  Technologie-Landschaft | Aktivitätstrends | **keine** (kein CAGR, keine Jahreszeitreihe, nur Cluster-Intro) |
| UC2  Reifegrad-Analyse | S-Kurve & Reife | Nur Header-Phase-Badge: **Reife** / "Rückläufige Entwicklung"; keine R², keine S-Kurven-Parameter, kein Fit-Zeitraum |
| UC5  Cross-Tech Intelligence | Technologiekonvergenz | **keine** CPC-Klassen, keine Konvergenz-Matrix, keine Whitespace-Lücken |
| UC3  Wettbewerbsanalyse | Wettbewerb & HHI | Nur Header-Label: "Wettbewerbsintensiver Markt"; **kein HHI-Wert**, keine Top-Anmelder |
| UC8  Zeitliche Entwicklung | Dynamik & Persistenz | **keine** Einstiege/Persistente/Ausstiege, keine Zahlen |
| UC11 Akteurs-Typen | Akteurs-Typen | **keine** Prozent-Breakdowns (Hochschule/Forschung/Industrie/öffentlich) |
| UC4  Förderungsanalyse | Förderung | Nur Header-Wert: **€160M**; keine Fördergebiete, keine Zeitreihe, keine Projekt-Zuordnung |
| UC7  Forschungsimpact | Forschungsimpact | Nur Header-Label: "Moderater Forschungsimpact"; **kein h-Index**, keine Zitationsraten, keine Top-Institutionen |
| UC13 Publikations-Impact | Publikationen | Nur Header-Wert: **0 Publikationen**; keine Pub/Project-Effizienz |
| UC6  Geographische Verteilung | Geographie | **keine** Länder-Top-Liste, keine EU-Anteile, keine Shares |
| UC9  Technologie-Cluster | Tech-Cluster | **keine** 5-Dim-Werte (Aktivität / Vielfalt / Dichte / Kohärenz / Wachstum) |
| UC10 EuroSciVoc | EuroSciVoc | **keine** Disziplinen-Zuordnung, keine Taxonomie-Knoten |
| UC12 Erteilungsquoten | Patenterteilung | **keine** Grant-Rate, kein Time-to-Grant |

---

## 3 · Warnung-Liste (Panels mit „Keine Daten" / leer / nur 0)

Alle 13 Panels sind im Dump **inhaltlich leer** (keine Panel-Nutzdaten erfasst):

- **Aktivitätstrends (UC1)** — keine Jahres-/CAGR-Werte
- **S-Kurve & Reife (UC2)** — kein R², keine Phasen-Parameter (nur Header-Badge)
- **Technologiekonvergenz (UC5)** — keine CPC-Konvergenz-Daten
- **Wettbewerb & HHI (UC3)** — kein HHI-Wert, keine Akteure
- **Dynamik & Persistenz (UC8)** — keine Akteursdynamik
- **Akteurs-Typen (UC11)** — kein Breakdown
- **Förderung (UC4)** — nur Header-€-Wert, keine Detailstruktur
- **Forschungsimpact (UC7)** — nur Header-Label, kein h-Index
- **Publikationen (UC13)** — Header zeigt **0 Publikationen** (Null-Wert mit Label)
- **Geographie (UC6)** — keine Länder / Shares
- **Tech-Cluster (UC9)** — keine 5-Dim-Werte
- **EuroSciVoc (UC10)** — keine Disziplinen
- **Patenterteilung (UC12)** — keine Grant-Rate / Time-to-Grant

### Zusätzliche auffällige Null-/Widerspruchsbefunde im Header

- **Publikationen = 0** bei gleichzeitig angezeigtem "Moderater Forschungsimpact" — Impact-Label trotz 0 Publikationen ist begründungsbedürftig.
- **Phase: Reife** + "Rückläufige Entwicklung" ist plausibel für ICE, aber ohne hinterlegte UC2-Daten (R², Fit-Zeitraum) im Dump nicht verifizierbar.
- **48 EU-Projekte** und **€160M Förderung** stehen im Header; da UC4 keine Detailzahlen liefert, ist keine Kopf-vs-Detail-Verifikation möglich.

### Methodischer Hinweis

Da `activeTab` durchgängig "Neue Analyse" zeigt, ist aus dem Dump **nicht unterscheidbar**, ob:

1. die Panels live **tatsächlich leer** gerendert wurden (echtes „keine Daten"), oder
2. die Capture-Automation die Tabs nicht korrekt aktiviert hat (Tool-Artefakt).

Für belastbare Aussagen zur UC-Konsistenz bei ICE müsste der Capture mit erzwungenem Tab-Wechsel wiederholt werden.
