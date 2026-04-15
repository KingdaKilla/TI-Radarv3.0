# Konsistenz-Audit · Rolle A (Dokumentierer) · post-quantum cryptography

**Datum:** 2026-04-14  
**Quelle:** `docs/testing/ergebnisse/konsistenz/raw/raw_pqc.json`  
**Live-System:** https://app.drakain.de

---

## 1 · Header (Executive-Summary-Kopfzeile)

| Feld | Wert (wie angezeigt) |
|---|---|
| Technologie | POST-QUANTUM CRYPTOGRAPHY |
| Patente | **8** |
| EU-Projekte | **33** |
| Publikationen | **0** |
| Phase | **Entstehung** |
| Trend-Label | Stagnation |
| Wettbewerb-Label | Wettbewerbsintensiver Markt |
| Förderung | **€99M** |
| Impact-Label | Moderater Forschungsimpact |

Originalzeile:
> `POST-QUANTUM CRYPTOGRAPHY | Technologie-Intelligence Analyse | 8 | Patente | 33 | EU-Projekte | 0 | Publikationen | Phase: Entstehung | Stagnation | Wettbewerbsintensiver Markt | €99M Förderung | Moderater Forschungsimpact`

---

## 2 · UC × beobachtete Kern-Metriken

**Wichtige Vorbemerkung:** Für alle 13 Panels ist im Dump `"activeTab": "Neue Analyse"` gesetzt, und der `mainText` ist in allen 13 Panels **zeichengleich identisch**. Das heißt: Das Dashboard hat beim Capture die jeweiligen Tab-Inhalte **nicht geladen** — stattdessen wurde 13 mal derselbe Landing-/Overview-Text (Header + Cluster-Beschreibungstexte „Dieser Analysebereich umfasst: …") erfasst. Es liegt daher **keine einzige UC-spezifische Nutzdaten-Zeile** vor.

| UC | Tab | Beobachtete Kern-Metrik(en) im Dump |
|---|---|---|
| UC1  Technologie-Landschaft | Aktivitätstrends | **keine** (kein CAGR, keine Jahreszeitreihe, nur Cluster-Intro) |
| UC2  Reifegrad-Analyse | S-Kurve & Reife | Nur Header-Phase-Badge: **Entstehung** / „Stagnation"; keine R², keine S-Kurven-Parameter, kein Fit-Zeitraum |
| UC5  Cross-Tech Intelligence | Technologiekonvergenz | **keine** CPC-Klassen, keine Konvergenz-Matrix, keine Whitespace-Lücken |
| UC3  Wettbewerbsanalyse | Wettbewerb & HHI | Nur Header-Label: „Wettbewerbsintensiver Markt"; **kein HHI-Wert**, keine Top-Anmelder |
| UC8  Zeitliche Entwicklung | Dynamik & Persistenz | **keine** Einstiege/Persistente/Ausstiege, keine Zahlen |
| UC11 Akteurs-Typen | Akteurs-Typen | **keine** Prozent-Breakdowns (Hochschule/Forschung/Industrie/öffentlich) |
| UC4  Förderungsanalyse | Förderung | Nur Header-Wert: **€99M** bei **33 EU-Projekten**; keine Fördergebiete, keine Zeitreihe, keine Projekt-Zuordnung |
| UC7  Forschungsimpact | Forschungsimpact | Nur Header-Label: „Moderater Forschungsimpact"; **kein h-Index**, keine Zitationsraten, keine Top-Institutionen |
| UC13 Publikations-Impact | Publikationen | Nur Header-Wert: **0 Publikationen**; keine Pub/Project-Effizienz |
| UC6  Geographische Verteilung | Geographie | **keine** Länder-Top-Liste, keine EU-Anteile, keine Shares |
| UC9  Technologie-Cluster | Tech-Cluster | **keine** 5-Dim-Werte (Aktivität / Vielfalt / Dichte / Kohärenz / Wachstum) |
| UC10 EuroSciVoc | EuroSciVoc | **keine** Disziplinen-Zuordnung, keine Taxonomie-Knoten |
| UC12 Erteilungsquoten | Patenterteilung | **keine** Grant-Rate, kein Time-to-Grant |

---

## 3 · Warnung-Liste (Panels mit „Keine Daten" / leer / nur 0)

Alle 13 Panels sind im Dump **inhaltlich leer** (keine Panel-Nutzdaten erfasst):

- **Aktivitätstrends (UC1)** — keine Jahres-/CAGR-Werte
- **S-Kurve & Reife (UC2)** — kein R², keine Phasen-Parameter (nur Header-Badge „Entstehung")
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

- **Patente = 8** ist für eine als strategisch relevant eingestufte Technologie (PQC, NIST-Standardisierung seit 2016) extrem niedrig — möglicher Hinweis auf Abdeckungslücke im Patent-Dataset oder sehr enge CPC-Abgrenzung. Ohne UC1/UC12-Detail nicht verifizierbar.
- **Publikationen = 0** bei gleichzeitig angezeigtem „Moderater Forschungsimpact" ist inkonsistent: Ein Forschungsimpact-Label ohne zugrundeliegende Publikationen ist begründungsbedürftig (h-Index / Zitationen basieren typischerweise auf Publikationen).
- **Phase: Entstehung** + Trend-Label **„Stagnation"** ist eine semantisch spannungsreiche Kombination: „Entstehung" suggeriert frühe Wachstumsphase, „Stagnation" das Gegenteil. Ohne UC1/UC2-Detaildaten (Jahres-Verlauf, R², CAGR) nicht aufzulösen.
- **€99M Förderung** bei nur **33 EU-Projekten** ergibt ein rechnerisches Mittel von ~€3M/Projekt — plausibel, aber mangels UC4-Detailaufschlüsselung nicht belegt.
- **Wettbewerbsintensiver Markt** bei nur **8 Patenten** ist konzeptionell fragwürdig: Ein HHI auf 8 Anmeldern hat extrem geringe statistische Aussagekraft, und ein „intensiver" Wettbewerb bei 8 Patenten erscheint überinterpretiert. Kein HHI-Wert im Dump zur Prüfung.

### Methodischer Hinweis

Da `activeTab` durchgängig „Neue Analyse" zeigt, ist aus dem Dump **nicht unterscheidbar**, ob:

1. die Panels live **tatsächlich leer** gerendert wurden (echtes „keine Daten", plausibel bei nur 8 Patenten / 0 Publikationen), oder
2. die Capture-Automation die Tabs nicht korrekt aktiviert hat (Tool-Artefakt).

Für belastbare Aussagen zur UC-Konsistenz bei PQC müsste der Capture mit erzwungenem Tab-Wechsel wiederholt werden. Angesichts der niedrigen Basis-Datenlage (8 Patente, 0 Publikationen) ist allerdings zu erwarten, dass mehrere UCs auch bei erfolgreichem Tab-Load strukturell dünn bleiben.
