# Perovskite Solar Cell – Agent B (Analyse)

**Scope:** Severity-gewichtete numerische Inkonsistenzen im Live-Dashboard-Dump (`raw3_perovskite.json`). Stichtag Daten-Pull: 2026-04-14.

---

## Header-Snapshot (zur Referenz)

> „101 Patente · 140 EU-Projekte · 0 Publikationen · Phase: Reife Rückläufige Entwicklung · Wettbewerbsintensiver Markt · €222M Förderung · Hoher Forschungsimpact"

---

## Befunde

### CRITICAL

#### C1 · Header „0 Publikationen" vs. UC7 „100 Publikationen / 363.5 Zitate/Pub."
- **Quelle:** Header + `Forschungsimpact`
- **Snippet:** Header: „**0 Publikationen**" — UC7: „**100 Publikationen** 363.5 Zitate/Pub. 15 Institutionen"
- **Widerspruch:** Der Executive-Header behauptet, es gäbe keine Publikationen, während UC7 gleichzeitig 100 Papers mit einem extrem hohen Impact (363.5 Zitationen/Publikation) ausweist und UC13 diese Basis implizit bestätigt (s. C2). Für einen Budget-Entscheider ist das ein fataler Widerspruch — entweder stimmt die Kopfzeile nicht oder das Impact-Panel.
- **Fix-Hypothese:** Header-KPI zieht aus einem anderen Aggregat (vermutlich DOI-verlinkte CORDIS-Pubs mit Nullwert oder fehlgeschlagener Join) als UC7 (OpenAlex-/Scopus-basiert). Header-Query auf dieselbe Quelle wie UC7 umstellen.

#### C2 · UC13 Pub/Projekt-Rechnung ergibt ein Vielfaches der UC7-Publikationen
- **Quelle:** `Publikationen` (UC13) + `Forschungsimpact` (UC7) + Header
- **Snippet:** UC13: „**21.3 Pub/Projekt** DOI: 56%" · Header: „140 EU-Projekte" · UC7: „100 Publikationen"
- **Widerspruch:** 21.3 × 140 = **2.982 implizierte Publikationen**, UC7 zeigt nur 100, Header behauptet 0. Drei unverträgliche Publikationszahlen im selben Dashboard (0 / 100 / ~2.982).
- **Fix-Hypothese:** UC13 multipliziert CORDIS-linked-DOI-Publikationen über alle Projekte auf, während UC7 nur eine deduplizierte Top-15-Institutions-Aggregation zeigt. Entweder UC7-Scope auf „alle Projekte" erweitern oder UC13-KPI beschriften als „21.3 DOI-Matches pro Projekt (mit Duplikaten)".

#### C3 · Phase „Reife + Rückläufige Entwicklung" vs. UC2 „Phase: Reife, R² = 1.000, Konfidenz 82%"
- **Quelle:** Header + `S-Kurve & Reife`
- **Snippet:** Header: „Phase: **Reife Rückläufige Entwicklung**" — UC2: „Phase: **Reife** R² = 1.000 Wendepunkt: 2021 Konfidenz: 82%"
- **Widerspruch:** Das UC2-Panel kennt nur eine einzige Phase (Reife). Der Header konkateniert zwei Zustände (Reife UND Rückgang), die in UC2 explizit als getrennte Phasen visualisiert sind. Plus: CAGR Patente +4.1 %, CAGR Projekte +9.8 % (UC1) — positives Wachstum ist inkompatibel mit dem Label „Rückläufige Entwicklung".
- **Fix-Hypothese:** Header-Phase-Builder nutzt eine zweite Heuristik (z. B. „letzte 2 Jahre Aktivitätstrend"), die durch die unvollständigen 2025/2026-Daten einen künstlichen Rückgang erkennt. Header auf die UC2-Primärphase reduzieren oder sekundäre Heuristik unterdrücken, wenn CAGR > 0.

#### C4 · Wettbewerbs-Widerspruch: Header „Wettbewerbsintensiver Markt" vs. UC3 „Niedrige Konzentration"
- **Quelle:** Header + `Wettbewerb & HHI`
- **Snippet:** Header: „**Wettbewerbsintensiver Markt**" — UC3: „**Niedrige Konzentration**"
- **Widerspruch:** Die Aussagen sind logisch äquivalent (niedriger HHI = viele Spieler = wettbewerbsintensiv), werden aber als gegensätzlich wahrgenommen, weil die Top-8-Patenthalter jeweils nur im einstelligen Bereich liegen (0–16 Patente/Projekte). Das Label „Wettbewerbsintensiv" suggeriert einen „hart umkämpften Markt", tatsächlich liegt eine fragmentierte Frühphase-Landschaft ohne Leader vor.
- **Fix-Hypothese:** Header-Label umformulieren zu „Fragmentierter Markt" / „Niedrige Konzentration" (konsistent mit UC3), da „wettbewerbsintensiv" bei so kleinen Einzelzählungen irreführend ist.

#### C5 · R² = 1.000 bei UC2 ist statistisch unplausibel (Overfit-Verdacht)
- **Quelle:** `S-Kurve & Reife`
- **Snippet:** „**R² = 1.000** Wendepunkt: 2021 Konfidenz: 82%"
- **Widerspruch:** Ein R² von exakt 1.000 auf einer Sigmoid-Anpassung über 10 Jahrespunkte (2016–2026, davon 2025/2026 unvollständig) ist mathematisch nur bei ≤ 3 Datenpunkten oder bei Fit auf bereits geglätteten/kumulierten Werten möglich. Gleichzeitig nur 82% Konfidenz zu zeigen ist inkonsistent (perfekter Fit → hohe Konfidenz).
- **Fix-Hypothese:** Sigmoid wird vermutlich auf kumulativer Patentkurve gefittet (monoton → R² → 1.000), nicht auf Jahreswerten. Auf Inkremente umstellen oder R²-Kennzahl klar als „R² cum." beschriften; Konfidenz-Formel überprüfen.

---

### MAJOR

#### M1 · UC10 Shannon-Index 4.87 bei nur „1 Feld"
- **Quelle:** `EuroSciVoc`
- **Snippet:** „**1 Feld** 134 Projekte 0% 0% 1% 1% 1% nanotechnology 134 Projekte zugeordnet · **Shannon-Index: 4.87**"
- **Widerspruch:** Shannon-Diversität bei nur einer Kategorie muss rechnerisch 0 sein (H = −Σp·log p mit p=1 → H=0). 4.87 ist unmöglich. Zusätzlich listet das Panel fünf Prozente (0/0/1/1/1 %), was bei 1 Feld unsinnig ist.
- **Fix-Hypothese:** Aggregation zählt nur Top-1-Level-Klassifikation („nanotechnology"), der Shannon-Index wird aber auf feingranularerer Unterkategorie berechnet. Entweder Shannon-Index auf dieselbe Granularität wie die Feld-Zählung ziehen oder zwei getrennte KPIs ausweisen („Top-Felder: 1 · Subfield-Diversität: 4.87").

#### M2 · Header 140 Projekte vs. UC10 134 Projekte
- **Quelle:** Header + `EuroSciVoc` + `Förderung`
- **Snippet:** Header: „**140 EU-Projekte**" · UC4 Förderung: „**140 Projekte**" · UC10: „**134 Projekte**"
- **Widerspruch:** 6 Projekte (ca. 4 %) sind in CORDIS nicht mit EuroSciVoc-Taxonomie verknüpft. Ohne Fußnote entsteht der Eindruck eines Zählfehlers.
- **Fix-Hypothese:** UC10 mit Badge/Tooltip versehen („6 Projekte ohne EuroSciVoc-Tag"), damit der Delta nicht als Inkonsistenz wirkt.

#### M3 · UC8 „Schrumpfend −70 netto" bei nur 9 Akteuren
- **Quelle:** `Dynamik & Persistenz`
- **Snippet:** „**9 Akteure** Schrumpfend (**−70 netto**)"
- **Widerspruch:** Ein Netto-Schrumpfen um 70 ist mathematisch nicht mit einer Gesamtbasis von 9 Akteuren vereinbar. Zusätzlich zeigt UC11 „280 Akteure" — zwei komplett unterschiedliche Akteursmengen (9 vs. 280) im selben Dashboard ohne Erklärung.
- **Fix-Hypothese:** UC8 zählt vermutlich nur Patentanmelder aktueller Periode, UC11 alle jemals gesehenen Akteure (Patent+Projekt). Scope-Bezeichnung differenzieren: „9 aktive Patentanmelder letzte 2 Jahre" vs. „280 Gesamt-Akteure (kumuliert)". Das „−70 netto" mit einer anderen Bezugsmenge (Kumulativ-Basis) nachvollziehbar machen.

#### M4 · UC12 Grant-Rate-Widerspruch: 506 / 5.462 = 9.26 %, Panel „Quote: 9.3 %" — aber Anmeldezahl passt nicht zu Header-Patenten
- **Quelle:** `Patenterteilung` + Header
- **Snippet:** Header „**101 Patente**" — UC12 „**5.462 Anmeldungen** 506 Erteilungen Quote: 9.3 %"
- **Widerspruch:** Die Quote selbst ist rechnerisch korrekt (506/5462 ≈ 9.26 %). Aber Header behauptet „101 Patente", UC12 hat 5.462 Anmeldungen und 506 Erteilungen. Welche Zahl bezieht sich worauf? 101 ist weder Anmeldungen noch Erteilungen.
- **Fix-Hypothese:** Header „101 Patente" misst vermutlich nur Patente von EU-Akteuren (UC11-Scope), UC12 misst globale Patentfamilien. Header-Label präzisieren als „101 EU-Patente" und UC12 als „global". Gefahr: aktuell wirkt Dashboard um Faktor ~50 inkonsistent.

#### M5 · UC7 Jahresachse 2016–2024, UC1/UC2/UC8/UC12 bis 2026
- **Quelle:** Mehrere Panels
- **Snippet:** UC7: „…2023 2024" — UC1/UC2/UC8/UC12: „…2025 2026"
- **Widerspruch:** Inkonsistenter Beobachtungszeitraum. UC7 stoppt 2 Jahre früher, UC13 auch (2016–2024). Nutzer sieht unterschiedliche Endjahre ohne Begründung.
- **Fix-Hypothese:** OpenAlex/Scopus-Lag unterschiedlich zu EPO/CORDIS; einheitlich auf 2024 (wo Daten vollständig) zurückschneiden oder konsistent bis 2026 mit Warnhinweis zeigen.

---

### MINOR

#### m1 · Warnhinweis „Daten ggf. unvollständig" fehlt in UC7 / UC13 / UC12 trotz 2025/2026-Bezug
- **Quelle:** UC1, UC2, UC8 haben Hinweis; UC12 trotz Achse bis 2026 ohne Hinweis.
- **Fix:** Hinweis über zentrales Policy-Flag in allen Panels mit 2025/2026-Achse einspielen.

#### m2 · UC3 Akteurslabels abgeschnitten („FRAUNHOFERAUSTRI…", „UNIVERSITATJAUME…", „SAULE SPOLKAAKCY…")
- **Quelle:** `Wettbewerb & HHI`
- **Fix:** Label-Width erhöhen oder Tooltip mit Vollname einblenden; aktuell keine eindeutige Zuordnung möglich.

#### m3 · UC1 CPC-Zahlen deutlich größer als Patentbasis (Y02E10/549: 5.076 bei 101 Patenten Header)
- **Quelle:** `Aktivitätstrends`
- **Widerspruch:** 5.076 CPC-Einträge bei 101 Patenten bedeuten ~50 CPC-Codes pro Patent — unplausibel hoch außer Daten stammen aus globaler Patentbasis (s. M4).
- **Fix:** Bezugsscope klarstellen (global vs. EU-Scope).

#### m4 · UC4 Gesamtförderung 221.8 Mio. EUR vs. Header „€222M"
- **Quelle:** Header + UC4
- **Widerspruch:** Nur Rundungs-Delta, konsistent. ✔

---

### INFO

- UC5 Konvergenz: 10 CPC-Klassen, Ø Jaccard 0.198 — plausibel, Top-Klassen Y02E/H10K kohärent zu UC1.
- UC6 Länder: 10 Länder, Top Deutschland — plausibel für perovskite.
- UC10: „nanotechnology" als einziges Feld ist für Perovskite inhaltlich **plausibel** (besser als „law" bei Solid State) — keine Taxonomie-Fehlzuordnung.
- UC9: 5 Cluster / 39 Akteure / 118 CPC — Akteurszahl (39) erneut unterschiedlich zu UC11 (280) und UC8 (9). Scope-Dokumentation dringend erforderlich.

---

## Zusammenfassung Severity-Verteilung

| Severity | Anzahl | Themen |
|---|---|---|
| Critical | 5 | Publikationen-Widerspruch (3×), Phase/CAGR, Wettbewerbs-Label, R²-Plausibilität |
| Major | 5 | Shannon-Index, Projekt-Zählerei, Akteurs-Scopes, Patent-Scope, Jahresachsen |
| Minor | 4 | Warnhinweis, Labels, CPC-Scope, Förderungs-Rundung |
| Info | 4 | UC5/6/10/9-Plausibilität |

**Kernrisiko:** Drei widerstreitende Publikationszahlen (0 / 100 / ~2.982) machen jede Forschungs-Impact-Aussage für diese Technologie unbelastbar. Das ist Showstopper für Budget-Entscheidungen im Bereich Research-Förderung.
