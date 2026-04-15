# Agent C · Interpreter · Post-Quantum Cryptography

**Datum:** 2026-04-14
**Technologie:** `post-quantum cryptography`
**Input:** `docs/testing/ergebnisse/konsistenz/raw/raw_pqc.json`

## Header-KPIs (Executive-Summary)

| Feld | Wert |
|---|---|
| Patente | **8** |
| EU-Projekte | **33** |
| Publikationen | **0** |
| Phase | **Entstehung / Stagnation** |
| Wettbewerb | **Wettbewerbsintensiver Markt** |
| Förderung | **€99M** |
| Forschungsimpact | **Moderater Forschungsimpact** |

## Globaler Befund (vor der UC-Tabelle)

Für diese Tech ist **kein** UC-Panel tatsächlich gerendert worden. In allen 13 Panel-Dumps steht `activeTab: "Neue Analyse"`, und der `mainText` jedes Tabs ist **byte-identisch**: Executive-Summary-Kopf, gefolgt von den statischen Cluster-Info-Beschreibungen ("Dieser Analysebereich umfasst: …"). Es gibt keinen einzigen Chart-Label, keine Top-Liste, keinen HHI-Wert, keinen CAGR, keine Länder-Shares, keine Jahre, keinen h-Index, keinen Reifegrad-Score, keine CPC-Klassen und keine EuroSciVoc-Disziplinen.

Das heißt: der Dashboard-Durchlauf ist bei PQC auf der **Landing-/Cluster-Übersicht** steckengeblieben und die Tab-Klicks haben nie ein UC-Panel geöffnet — oder die UC-Panels haben bei dieser Tech keinen Inhalt geladen und sind auf einen leeren Default-State zurückgefallen. Für Rolle C ist das Urteil damit über alle 13 UCs im Kern identisch und trivial: das Versprechen wird nicht eingelöst.

## UC × Versprechen × Liefert × Ampel

| UC | Versprechen | Geliefert laut Dashboard | Ampel | Begründung |
|---|---|---|---|---|
| **UC1** Technologie-Landschaft | Patent-/Projekt-/Pub-Verlauf, CAGR, Dynamik | Nur Header-Zahlen (8 Patente, 33 Projekte, 0 Pubs). Kein Zeitverlauf, keine CAGR, keine Jahresreihe. | 🔴 | Panel nicht gerendert; keine Trend-Aussage möglich. |
| **UC2** Reifegrad / S-Kurve | S-Kurve-Fit, Phase (Emerging/Growth/Mature/Declining), R² | Phase-Badge "Entstehung / Stagnation" existiert im Kopf, aber **keine S-Kurve, kein R², kein Fit-Diagramm**. Badge ist unbelegt. | 🔴 | Label ohne jede Evidenz — Phase-Deklaration ist für einen Entscheider wertlos, da nicht nachvollziehbar. |
| **UC5** Cross-Tech Intelligence | CPC-Konvergenz + Whitespace-Lücken | Keine CPC-Klassen, keine Konvergenzmatrix, keine Whitespaces. | 🔴 | Komplett leer. |
| **UC3** Wettbewerb & HHI | HHI-Zahl + dominante Akteure | Header-Phrase "Wettbewerbsintensiver Markt", aber **kein HHI-Wert, keine Akteursliste**. | 🔴 | Prosa ohne Zahl; bei 8 Patenten ist jede HHI-Aussage ohnehin statistisch fragil. |
| **UC8** Dynamik & Persistenz | Neue / Persistente / Ausgeschiedene Akteure | Kein Panel, keine Listen, keine Kohorten. | 🔴 | Nicht geliefert. |
| **UC11** Akteurs-Typen | Breakdown Hochschule/Forschung/Industrie/öffentlich, summiert ~100 % | Kein Breakdown, keine Prozente. | 🔴 | Nicht geliefert. |
| **UC4** Förderung | EU-Fördervolumen nach Gebiet + Zeitverlauf | Nur Header "€99M Förderung"; keine Aufschlüsselung nach Jahr, Projekt oder Forschungsgebiet; keine Verknüpfung zu den 33 EU-Projekten. | 🔴 | Aggregat-Zahl ohne Detailsicht — reicht nicht für eine Förder-Strategieentscheidung. |
| **UC7** Forschungsimpact | h-Index, Zitationsraten, Top-Institutionen | Nur Header-Phrase "Moderater Forschungsimpact"; bei 0 Publikationen ohnehin nicht berechenbar. | 🔴 | Phrase widerspricht dem Header-KPI 0 Publikationen (Moderater Impact worauf?). Panel leer. |
| **UC13** Publikations-Impact | CORDIS-Pubs × Projekte, Pub/Project-Effizienz | Header: 0 Publikationen — UC13 hat keine Grundlage. Kein Detail-Panel. | 🔴 | Konsistent null, aber auch keinerlei Detailsicht zur Einordnung (z. B. Pub/Projekt = 0/33). |
| **UC6** Geographie | Globale Verteilung, Top-Länder, EU-Share | Keine Länderliste, keine Karte, kein EU-Share. | 🔴 | Nicht geliefert. |
| **UC9** Tech-Cluster | 5-dim Profil (Aktivität, Vielfalt, Dichte, Kohärenz, Wachstum) | Kein Radar, keine 5 Dimensionen. | 🔴 | Nicht geliefert. |
| **UC10** EuroSciVoc | Zuordnung zu Wissenschaftsdisziplinen | Keine Disziplinen-Tags. | 🔴 | Nicht geliefert. |
| **UC12** Patenterteilung | Grant-Rate + Time-to-Grant | Keine Grant-Rate, keine Zeit-Spanne; bei n=8 Patenten ohnehin stark limitierte Aussagekraft. | 🔴 | Nicht geliefert. |

**Score: 0 × 🟢 · 0 × 🟡 · 13 × 🔴.**

## Zusätzliche Beobachtungen (Kohärenz der Header-Aussagen)

Selbst wenn man nur die Header-Kopfzeile als "Aussage" akzeptiert, ist sie intern widersprüchlich:

- **"Moderater Forschungsimpact" bei 0 Publikationen** — Impact woran gemessen? Ohne Pubs kein h-Index, keine Zitationen. Die Aussage ist bei diesem Pub-Stand nicht begründbar.
- **"Wettbewerbsintensiver Markt" bei 8 Patenten** — HHI auf so kleiner Basis ist statistisch instabil; die Qualifizierung ist riskant und nicht durch eine sichtbare Zahl belegt.
- **"Phase: Entstehung / Stagnation"** — zwei semantisch unterschiedliche Labels nebeneinander (Emerging ≠ Declining). Ohne S-Kurve/R² bleibt unklar, welcher Label-Teil statistisch trägt.
- **Förderung €99M für 33 EU-Projekte bei 0 CORDIS-Publikationen** — plausibel möglich (viele Projekte ohne publizierten Output in CORDIS), aber UC13 und UC4 müssten die Diskrepanz erklären; sie tun es nicht.

## Für welche Entscheidungen ist dieses Radar bei PQC brauchbar?

**Brauchbar:**
- Als **Existenzindikator** ("Es gibt EU-Aktivität rund um PQC — 33 Projekte, €99M Budget, 8 Patente"). Das ist für einen Erst-Screening-Blick nutzbar.

**Nicht brauchbar / gefährlich:**
- **Jede Strategieentscheidung**, die auf Reifegrad, Wettbewerbsstruktur, geografischen Schwerpunkten, Akteurs-Landschaft, Wissenschaftsdisziplinen oder Fördertrends beruht — die Panels liefern dafür **null Evidenz**. Ein Entscheider mit Budget würde auf Basis dieser Seite nichts verantwortungsvoll entscheiden können.
- **Gefährlich** sind die qualitativen Header-Labels ("Wettbewerbsintensiver Markt", "Moderater Forschungsimpact", "Entstehung / Stagnation"): Sie suggerieren eine belastbare Analyse, die das Dashboard in keinem UC-Panel offenlegt. Für PQC in v3 sind diese Labels **nicht durch Detailsicht hinterlegt** und sollten bis zur Korrektur ausgeblendet oder mit Datenbasis-Hinweis versehen werden.

## Empfehlung für v3.4

1. Prüfen, warum bei PQC alle Tabs im Zustand "Neue Analyse" gedumpt wurden (UI-Bug? Datenladefehler? Test-Artefakt?). Wenn UI: Tab-Wechsel triggert den UC-Fetch nicht. Wenn Datenbasis: n=8 Patente + 0 Pubs könnten unter einem Minimum-Threshold fallen, der das Panel-Rendering unterdrückt — dann explizit als "Datenbasis zu klein" kommunizieren, nicht mit qualitativen Labels übertünchen.
2. Header-Labels wie "Moderater Forschungsimpact" nur zeigen, wenn das zugehörige Detail-Panel (UC7) tatsächlich eine Zahl (z. B. h-Index) liefert.
3. Für Technologien mit Publikationen = 0: UC13-Panel aktiv als "0 Pubs bei 33 Projekten → Pub/Projekt-Effizienz = 0" ausweisen, statt leer zu lassen.
