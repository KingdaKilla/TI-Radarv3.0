# Konsistenz-Analyse · internal combustion engine (Agent B)

## Ausgangslage der Rohdaten

**Kritische Eingangs-Beobachtung:** In `raw_ice.json` ist für **alle 13 Tabs** `activeTab = "Neue Analyse"` und der `mainText` ist in allen 13 Panels **byte-identisch**. Der aufgezeichnete `mainText` enthält ausschliesslich die Executive-Summary-Kopfzeile sowie die vier Cluster-Info-Beschreibungen ("Dieser Analysebereich umfasst: UC6 … UC12 … UC1 … UC5 … UC3 … UC8 … UC11 … UC4 …"). Es wurden **keine echten Panel-Nutzdaten** (keine HHI-Werte, keine CAGR-Zahlen, keine Top-Länder, keine h-Index-Werte, keine Grant-Rate, keine Jahresreihen, keine CPC-Klassen) aufgezeichnet.

Damit ist ein **Kopf-vs-Detail-Vergleich auf Zahlen-Ebene nicht möglich** — die unten aufgeführten Befunde konzentrieren sich auf (a) Inkonsistenzen im Header selbst und (b) strukturelle Widersprüche zwischen Header-Aussage und fehlender Detail-Evidenz.

### Header-Fakten (Quelle: `summary` + identischer `mainText`-Anfang)

| Feld | Wert |
|---|---|
| Patente | 10.2K (≈ 10.200) |
| EU-Projekte | 48 |
| Publikationen | **0** |
| Phase | Reife |
| Dynamik-Label | Rückläufige Entwicklung |
| Wettbewerbs-Label | Wettbewerbsintensiver Markt |
| Förderung | €160M |
| Impact-Label | Moderater Forschungsimpact |

---

## Befunde

### CRITICAL

#### C1 · Publikationen-Header vs. Impact-Label (Widerspruch innerhalb der Kopfzeile)
- **Quelle:** `summary` / Header aller Panels.
- **Snippet:** `"… 0 Publikationen … Moderater Forschungsimpact …"`
- **Widerspruch:** Der Header meldet **0 Publikationen**, labelt gleichzeitig aber den Forschungsimpact als **"Moderater Forschungsimpact"**. Ohne jede Publikation kann es definitionsgemäss weder Zitationen, h-Index noch einen messbaren Impact geben — das Label ist entweder aus anderer Quelle (Patent-Zitationen?) gespeist und unsauber kommuniziert, oder schlicht falsch. Für UC7 (Forschungsimpact) und UC13 (Publikations-Impact) ist das ein Blocker.

#### C2 · Publikationen-Header vs. UC13-Versprechen nicht prüfbar (aber strukturell auffällig)
- **Quelle:** `Publikationen`-Panel.
- **Snippet:** *(kein UC13-Detail im Dump; activeTab = "Neue Analyse")*
- **Widerspruch:** Header sagt `0 Publikationen`. UC13 verspricht "CORDIS-Publikationen × Projekte, Publikationseffizienz (Pub/Project)". Bei 48 Projekten und 0 Publikationen wäre die Effizienz 0/48 = 0 — eine Panel-Darstellung eines 0-Werts wäre definitionsgemäss inhaltsleer. Header ist damit konsistent zur **Abwesenheit** von UC13-Daten, aber UC13 müsste das explizit als "Keine Daten" ausweisen.

#### C3 · Header-Phase "Reife" ohne Fit-Evidenz
- **Quelle:** `S-Kurve & Reife`-Panel.
- **Snippet:** *(kein UC2-Detail im Dump)*
- **Widerspruch:** Der Header deklariert `Phase: Reife` ex cathedra. UC2 verspricht S-Kurven-Fit mit Emerging/Growth/Mature/Declining-Klassifikation — ohne R²-Wert, Kurvenparameter oder Stützpunkte im Dump lässt sich die Phasenangabe weder bestätigen noch falsifizieren. Bei 10.2K Patenten und "Rückläufige Entwicklung" wäre "Declining" konsistenter als "Reife" — die beiden Labels im Header ("Phase: Reife" + "Rückläufige Entwicklung") wirken zusammen inkonsistent (Reife = Plateau; Declining = Rückgang).

### MAJOR

#### M1 · Header-Paradox "Reife" + "Rückläufige Entwicklung"
- **Quelle:** `summary` / Header.
- **Snippet:** `"Phase: Reife Rückläufige Entwicklung"`.
- **Widerspruch:** In der S-Kurven-Nomenklatur sind "Mature" (Plateau, hohes Niveau, geringes Wachstum) und "Declining" (Rückgang vom Peak) **zwei verschiedene Phasen**. Der Header verschmilzt beide zu einem Etikett, das sich selbst widerspricht. Entweder ist ICE bereits in der Declining-Phase (dann ist das Phase-Badge falsch), oder noch Mature (dann ist das Trend-Label zu stark).

#### M2 · CAGR-Endjahr-Risiko (strukturell, nicht direkt prüfbar)
- **Quelle:** `Aktivitätstrends`-Panel (UC1).
- **Snippet:** *(kein UC1-Detail im Dump)*
- **Widerspruch:** Heute ist 2026-04-14. Wenn UC1 ein CAGR "2015–2024" oder "2015–2025" anzeigt, dann ist 2025 noch jung (publizierte Patent-Daten haben 18–24 Monate Lag, CORDIS-Projekte sogar mehr). Ein CAGR-Endjahr ≥ 2024 verzerrt den Trend systematisch nach unten und erklärt das Label "Rückläufige Entwicklung" möglicherweise technisch, nicht fachlich. Dieser Befund ist für ICE besonders sensibel, weil das gesamte Storytelling "Phase: Reife / rückläufig" auf diesem Trend hängt.

#### M3 · "€160M Förderung" bei 48 Projekten — Plausibilität nicht prüfbar
- **Quelle:** `summary`, `Förderung`-Panel (UC4).
- **Snippet:** `"48 EU-Projekte … €160M Förderung"`.
- **Widerspruch:** 160 Mio € / 48 Projekte ≈ 3,3 Mio €/Projekt Durchschnittsbudget — für H2020/Horizon-Europe-Projekte zu ICE plausibel, aber ohne UC4-Detail (Zeitverlauf, Forschungsgebiet, Projektliste) nicht verifizierbar. Kein Widerspruch, aber Unverifiziert-Flag.

### MINOR

#### m1 · Patentzahl-Rundung "10.2K"
- **Quelle:** Header.
- **Snippet:** `"10.2K Patente"`.
- **Widerspruch:** Der Header zeigt eine gerundete Grösse "10.2K", während die Panel-Detailansichten (UC3 HHI, UC6 Länder, UC12 Erteilungsquoten) üblicherweise auf exakte Patent-Counts aufsetzen. Sobald UC3/UC6/UC12 sichtbar sind, ist zu prüfen, ob Summen der Länder-/Akteurs-Shares ≈ 10.200 ergeben (±200 ok, sonst Basis-Mismatch).

#### m2 · Alle 13 Tabs zeigen identischen "Neue Analyse"-Überblicksinhalt
- **Quelle:** alle Panels.
- **Snippet:** `"activeTab": "Neue Analyse"` × 13, `mainText` byte-identisch.
- **Widerspruch:** Entweder (a) das Capture wurde vor dem eigentlichen Tab-Klick gezogen, oder (b) die Tab-Navigation im Live-System hat für ICE nicht geschaltet (SPA-Routing-Bug?). In Fall (b) wäre das ein **CRITICAL** Produkt-Bug. Ohne zweite Capture-Runde nicht entscheidbar — wird hier nur als Minor gelogged, weil Ursache unklar ist. Empfehlung: einmal erneut capturen und prüfen, ob `activeTab` pro Tab tatsächlich dem Tab-Namen entspricht.

---

## Was nicht geprüft werden konnte (Daten-Lücke)

Folgende UC-Kernprüfungen aus dem Briefing sind mangels Detail-Evidenz im Dump **nicht durchführbar**:

- **UC3 HHI numerisch** + dominante Akteure (keine HHI-Zahl im Text).
- **UC6 EU-Share-Paradox** (keine Top-Länder, kein EU-Share).
- **UC11 Akteurs-Typen ±100 %** (keine Breakdown-Prozente).
- **UC12 Grant-Rate 0–100 % plausibel** (kein Wert).
- **UC7 h-Index / Top-Institutionen** (kein Wert — zusätzlich durch C1 ohnehin fragwürdig).
- **UC4 Projektzahl == 48 konsistent zu Detail** (kein Detail).
- **UC2 R² < 0,5 trotzdem Phase?** (kein R² — aber M1 signalisiert bereits Label-Inkonsistenz).
- **UC5 Whitespace / Konvergenz-Matrix** (nichts).
- **UC1 CAGR-Endjahr** (nichts, nur M2-Risiko).
- **UC9 5-dim Profil** (nichts).
- **UC10 EuroSciVoc-Zuordnung** (nichts).
- **UC13 Pub/Project-Effizienz** (nichts — aber durch `0 Publikationen` implizit 0).
- **UC8 Akteurs-Dynamik (New/Persistent/Exit)** (nichts).

## Zusammenfassung der Befund-Severities

| Severity | Count | Befunde |
|---|---|---|
| CRITICAL | 3 | C1 (Header-Impact-Label bei 0 Pubs), C2 (UC13 strukturell leer), C3 (Phase ohne Fit-Evidenz) |
| MAJOR | 3 | M1 (Reife + Rückläufig Doppelstempel), M2 (CAGR-Endjahr-Risiko), M3 (€/Projekt Plausi) |
| MINOR | 2 | m1 (10.2K-Rundung), m2 (activeTab-Capture-Problem) |
