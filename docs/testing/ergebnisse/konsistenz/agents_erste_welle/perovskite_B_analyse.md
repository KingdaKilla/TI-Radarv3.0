# Konsistenz-Analyse (Rolle B) — Technologie: **perovskite solar cell**

Quelle: `docs/testing/ergebnisse/konsistenz/raw/raw_perovskite.json`
Stichtag der Analyse: 2026-04-14

## Vorbemerkung zum Input (wichtig!)

Im vorliegenden JSON ist für **alle 13 Panels** identisches Verhalten festgestellt worden:

- `activeTab` = **"Neue Analyse"** (nicht der jeweilige UC-Tab)
- `mainText` enthält in **allen 13 Fällen** ausschließlich Executive-Summary-Kopfzeile + Cluster-Info-Text (Landing-/Home-Screen), **keinerlei panel-spezifische Nutzdaten** (keine HHI-Werte, keine CAGR-Zahlen, keine Länder-Listen, keine CPC-Klassen, keine h-Index-Werte, keine Grant-Rate, kein R², keine Jahreslabels).

Das ist entweder ein Capture-Fehler (Dashboard nicht tatsächlich in den Tab gewechselt) **oder** das Live-Dashboard rendert für `perovskite solar cell` tatsächlich keine Detail-Panels und zeigt stattdessen nur die Landing-Seite. In beiden Fällen ist das **selbst der gravierendste Befund**. Die folgende Befundliste stützt sich daher auf die nur einmal pro Tab sichtbare Header-Zeile und auf die Lücke "Detail fehlt".

Header-Zeile (wörtlich, aus allen 13 `mainText`-Einträgen und aus `summary`):

> "PEROVSKITE SOLAR CELL · 101 Patente · 140 EU-Projekte · 0 Publikationen · Phase: Reife · Rückläufige Entwicklung · Wettbewerbsintensiver Markt · €222M Förderung · Hoher Forschungsimpact"

---

## Befunde

### Critical

**C1 · Alle 13 UC-Tabs liefern keine Detaildaten (Tab-Wechsel nicht wirksam bzw. Panel leer)**
- Quelle: jeder einzelne Tab im JSON (`Aktivitätstrends`, `S-Kurve & Reife`, …, `Patenterteilung`)
- Snippet: `"activeTab": "Neue Analyse"` + Landing-Text "Dieser Analysebereich umfasst: …"
- Widerspruch: Das Briefing verspricht pro UC konkrete Kennzahlen (HHI, CAGR, Phase/R², h-Index, Grant-Rate, CPC-Top-Listen, Länder-Shares). Geliefert wird für **keinen** UC ein Wert; alle Versprechen aus UC1–UC13 sind auf Rohdatenebene nicht einlösbar.

**C2 · Widerspruch "Phase: Reife" ↔ "Rückläufige Entwicklung"**
- Quelle: Header (alle Tabs), Summary
- Snippet: `"Phase: Reife | Rückläufige Entwicklung"`
- Widerspruch: Laut UC2-Taxonomie gilt das Kontinuum Emerging → Growth → **Mature** → **Declining**. Der Header deklariert gleichzeitig "Reife" (Mature) **und** "Rückläufige Entwicklung" (Declining) — das sind zwei unterschiedliche S-Kurven-Phasen, die sich im selben Badge widersprechen. Ohne sichtbaren R²- oder Wendepunkt-Wert (UC2-Detail fehlt, s. C1) ist nicht entscheidbar, welche Phase gilt.

**C3 · Publikationen-Widerspruch Header ↔ UC7/UC13-Label**
- Quelle: Header + UC7/UC13-Titel
- Snippet: `"0 Publikationen"` **und zugleich** `"Hoher Forschungsimpact"`
- Widerspruch: Ein "hoher Forschungsimpact" (UC7) und Aussagen zur "Publikationseffizienz" (UC13, Pub/Project) setzen eine Publikationsmenge > 0 voraus. Mit **0 Publikationen** kann weder ein h-Index berechnet noch ein Pub/Project-Quotient gebildet werden (Division durch 140 Projekte ergibt 0 Pub/Project). Das Label "Hoher Forschungsimpact" ist damit faktisch nicht belegt.

### Major

**M1 · Header-Kennzahlen sind nirgends im Dashboard rückverifizierbar**
- Quelle: Header vs. UC1/UC3/UC4/UC13-Detailpanels (nicht befüllt)
- Snippet: `"101 Patente | 140 EU-Projekte | 0 Publikationen | €222M Förderung"`
- Widerspruch: Die vier Header-Zahlen müssten in UC1 (Zeitreihe Patente/Projekte/Publikationen), UC4 (Förderung €-Summe) und UC13 (Publikationen) wieder auftauchen. Da keinerlei Detail-Zahlen vorliegen (s. C1), ist die **Konsistenz Kopf-vs-Detail prinzipiell nicht prüfbar** — ein gravierender Mangel für ein Audit-System.

**M2 · "€222M Förderung" bei 140 Projekten — Plausibilität nicht prüfbar**
- Quelle: Header + UC4-Panel (leer)
- Snippet: `"140 EU-Projekte · €222M Förderung"`
- Widerspruch: €222 Mio / 140 Projekte ≈ **€1,59 Mio Ø** pro Projekt — für Horizon-2020/HE-Solar-Projekte grundsätzlich niedrig, aber plausibel, wenn viele Teil-/SME-Projekte enthalten sind. Da UC4 keine Detailverteilung (Förderlinie, Zeitraum) liefert, kann nicht geprüft werden, ob "€222M" tatsächlich das Mitbewirkte (coordinator share) oder das Gesamt-Konsortialbudget ist. Inconsistency-Risiko.

**M3 · "Wettbewerbsintensiver Markt" (UC3-Label) ohne HHI-Nachweis**
- Quelle: Header + UC3-Panel (leer)
- Snippet: `"Wettbewerbsintensiver Markt"`
- Widerspruch: Die UC3-Aussage basiert per Definition auf dem HHI-Wert. Im Raw-Dump ist **kein HHI-Wert** (z. B. "HHI: 812") sichtbar. Das Label wird also abgesetzt, ohne dass der zugrundeliegende numerische Wert dem Nutzer gezeigt wird. Nicht falsifizierbar → nicht auditierbar.

**M4 · UC6 EU-Share-Paradox formal nicht prüfbar, aber Header suggeriert EU-Lastigkeit**
- Quelle: Header + UC6-Panel (leer)
- Snippet: `"140 EU-Projekte"` (impliziert starken EU-Anteil) vs. fehlendes UC6-Detail
- Widerspruch: Bei 140 CORDIS-Projekten wäre zu erwarten, dass UC6 (Geographie) einen signifikanten EU-Share > 0 % und mehrere EU-Länder im Top-3 zeigt. Da UC6 leer ist, kann das klassische EU-Paradox (Top-Land DE/FR/IT trotz 0 % EU-Anteil) weder bestätigt noch widerlegt werden — der Audit-Checkpunkt aus dem Briefing greift ins Leere.

### Minor

**m1 · "Rückläufige Entwicklung" impliziert CAGR < 0, CAGR-Fenster unbekannt**
- Quelle: Header + UC1-Panel (leer)
- Snippet: `"Rückläufige Entwicklung"`
- Widerspruch: Ohne angegebenes Zeitfenster (z. B. CAGR 2015–2024) lässt sich nicht prüfen, ob 2025/2026 (unvollständig) in die Berechnung eingeflossen sind. Stichtag ist 2026-04-14 — Publikations-/Patentmeldungen für 2025 und 2026 sind per Definition unvollständig und würden einen CAGR künstlich negativ ziehen. Konkretes Zeitfenster im Dashboard fehlt.

**m2 · Phase-Badge "Reife" ohne R²-Transparenz**
- Quelle: UC2-Panel (leer)
- Snippet: `"Phase: Reife"` (nur im Header)
- Widerspruch: Briefing-Audit-Punkt 6 ("R² < 0,5 → Phase trotzdem deklariert?") kann nicht beantwortet werden, weil kein R²-Wert gezeigt wird. Dashboard liefert eine kategorische Phase ohne Confidence-Indikator.

**m3 · UC5/UC9/UC10/UC12-Metriken komplett abwesend**
- Quelle: Tabs `Technologiekonvergenz`, `Tech-Cluster`, `EuroSciVoc`, `Patenterteilung`
- Snippet: kein CPC-Paar, kein 5-dim Profil, keine EuroSciVoc-Disziplin, keine Grant-Rate
- Widerspruch: Keine harte Metrik-Inkonsistenz messbar — aber schon das Fehlen der versprochenen Dimensionen ist ein leiser Konsistenz-Befund: Cluster-Info kündigt Inhalt an, der nicht geliefert wird.

**m4 · Redundanz im Header-String "Geographische Perspektive | Geographische Perspektive"**
- Quelle: Summary (`raw_perovskite.json`, Zeile 3) und jeder `mainText`
- Snippet: `"Geographische Perspektive | Geographische Perspektive | Dieser Analysebereich umfasst: | UC6 …"`
- Widerspruch: Doppelte Ausgabe desselben Clusterlabels deutet auf einen Render-Bug (Label + Überschrift) hin — kosmetisch, aber konsistent über alle Tabs.

---

## Zusammenfassung der Severity-Verteilung

| Severity | Anzahl | Kern |
|---|---:|---|
| Critical | 3 | C1 Detail-Panels leer · C2 Phase widerspricht sich intern · C3 0 Pubs vs. "Hoher Forschungsimpact" |
| Major    | 4 | Kopf-vs-Detail nicht prüfbar, €/Projekt unbelegt, HHI unsichtbar, UC6 nicht falsifizierbar |
| Minor    | 4 | CAGR-Fenster, R²-Transparenz, fehlende UC5/9/10/12-Inhalte, Render-Doppelung |

---

## Executive-Summary

Für `perovskite solar cell` liefert das Dashboard auf der Raw-Ebene **keine einzige UC-Detailmetrik** — alle 13 Panels zeigen nur den Landing-Screen —, sodass die Header-Kennzahlen (101 Patente, 140 EU-Projekte, 0 Publikationen, Phase: Reife, €222M Förderung, Hoher Forschungsimpact) **prinzipiell nicht gegen Detaildaten verifizierbar** sind. Zwei unmittelbar aus dem Header ablesbare harte Widersprüche bleiben: "Phase: Reife" kollidiert mit "Rückläufige Entwicklung" (zwei getrennte S-Kurven-Phasen im selben Badge), und "0 Publikationen" ist unvereinbar mit dem gleichzeitig ausgewiesenen Label "Hoher Forschungsimpact".
