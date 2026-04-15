# Konsistenz-Audit TI-Radar v3 — Konsolidierung über 6 Technologien × 3 Agentenrollen

**Stand:** 2026-04-14 · **Zielsystem:** `https://app.drakain.de` · **Auftrag:** Prüfung, ob jeder UC hält, was er verspricht; Suche nach inkonsistenten Metriken, unvollständigen Jahren, Kreuz-UC-Widersprüchen.

**Methodik:** Live-Durchlauf für 6 Technologien, Text-Dump aller 13 Tab-Panels, 3 Claude-Agenten pro Tech (Dokumentierer A, Analysierer B, Interpreter C) = 18 Agenten parallel → hier aggregiert.

---

## 0. Executive Summary (für Entscheider)

| Frage | Antwort |
|---|---|
| Hält jeder UC sein Versprechen? | **Nein.** Nur UC4 (Förderung) und UC5 (CPC-Konvergenz) sind über alle 6 Techs 🟢 grün. 6 UCs sind systematisch 🔴 rot. |
| Sind die Metriken zwischen Panels konsistent? | **Nein.** Systemweite Mehrfachzählungen von Publikationen (Faktor 10–1580), Patenten (Faktor 3–54), Akteuren (Faktor 2–100) und Projekten (bis Δ 80). |
| Werden unvollständige Jahre einbezogen? | **Ja.** 2025 (vollständig vor Zukunft) und besonders **2026** (heute der 3,5. Monat) werden in CAGR, S-Kurve und Akteurs-Dynamik einbezogen. Warnhinweis „Daten ggf. unvollständig" ist inkonsistent gesetzt. |
| Darf man dem Dashboard Budget-Entscheidungen anvertrauen? | **Nur eingeschränkt** — Förderlandschaft ja, Marktreife/Wettbewerbsintensität/Forschungsimpact nein. |

---

## 1. Systematische Bugs (bei allen 6 Techs reproduziert)

### CRIT-1 · Publikations-Triplet — drei sich widersprechende Zahlen im selben Dashboard

Header (Executive Summary) · UC7 Forschungsimpact · UC13 Publikations-Impact liefern drei **unvereinbare** Publikationszahlen:

| Tech | Header | UC7 direkt | UC13 implizit (Pub/Projekt × Projekte) | Faktor |
|---|---:|---:|---:|---:|
| mRNA | **311.500** | 197 | 8,0 × 307 ≈ **2.456** | 1 580× |
| Solid State Battery | **0** | 200 | 11,2 × 113 ≈ **1.266** | ∞ |
| Autonomous Driving | **0** | 199 | 60 × 235 ≈ **14.100** | ∞ |
| Internal Combustion Engine | **0** | 100 | 57,7 × 48 ≈ **2.770** | ∞ |
| Perovskite Solar Cell | **0** | 100 | 21,3 × 140 ≈ **2.982** | ∞ |
| Post-Quantum Cryptography | **0** | 100 | 48 × 33 ≈ **1.600** | ∞ |

**Root-Cause-Hypothese:** Drei verschiedene Datenquellen / Joins:
- Header speist vermutlich aus einer aggregierten OpenAIRE-Kennzahl (für mRNA: Query-Treffer auf den String „mRNA", überzählt wegen unscharfer String-Matches)
- UC7 aus Semantic-Scholar (präzise author-basiert, kleiner Scope)
- UC13 aus CORDIS-Publications (Pub-pro-Projekt), mit implizitem × Projektzahl

Keine Cross-UC-Konsistenzprüfung greift, es gibt kein „Single Source of Truth" für „Publikationen".

**Fix-Richtung:** Eine kanonische Publications-Query, gegen die Header, UC7 und UC13 gebaut werden. ODER: unterschiedliche Publikations-Begriffe klar labeln (z. B. „Publikationen im Tech-Feld" vs „Publikationen von Top-Autoren" vs „CORDIS-Projekt-Publikationen").

### CRIT-2 · UC10 EuroSciVoc — Shannon-Index mathematisch unmöglich

Jeder Tech liefert UC10 den Eintrag „**N Feld(er)**" + „**Shannon-Index X**".

| Tech | N Felder angegeben | Shannon | Inhalt |
|---|---:|---:|---|
| mRNA | 1 | **4,89** | nanotechnology |
| Solid State | 1 | **4,77** | law |
| Autonomous Driving | – | – | – |
| ICE | 1 | **5,15** | chemical engineering |
| Perovskite | 1 | **4,87** | (1 Feld) |
| PQC | 0 | – | „0 Felder" trotz 7 gelisteter Disziplinen inkl. e-commerce/geometry |

`Shannon(X)` bei genau **einer** Kategorie ist mathematisch gleich **0** (Definition: −Σpᵢ ln pᵢ; bei p=1 → −1·ln1 = 0). Die Plattform zeigt für fünf Techs Shannon-Werte > 4 bei angeblich 1 Feld — das ist **ein Berechnungsbug** (entweder das „1 Feld" ist Label-Bug — in Wirklichkeit gibt es mehr Felder —, oder Shannon wird aus einer anderen Population berechnet).

**Dazu kommt der fachliche Fehler:** Solid State Battery als „law", PQC mit „e-commerce/geometry" statt Kryptographie, mRNA als „nanotechnology" statt Biotech/Immunologie. Die EuroSciVoc-Zuordnung ist nicht nur mathematisch, sondern auch inhaltlich unbrauchbar.

**Fix-Richtung:** SQL-Query in `euroscivoc-svc` prüfen — vermutlich fällt die `GROUP BY`-Aggregation auf den falschen Level (Root-Code der EuroSciVoc-Hierarchie statt Leaf). Shannon-Berechnung separat validieren; im Frontend Fallback „n/a" wenn N < 2.

### CRIT-3 · Akteurs-Zählbasis divergiert stark zwischen UCs

Drei UCs zählen „Akteure" unterschiedlich:

| Tech | UC8 Dynamik | UC9 Tech-Cluster | UC11 Akteurs-Typen | Spread |
|---|---:|---:|---:|---:|
| mRNA | 34 | 29 | **363** | 12× |
| Solid State | 22 | 44 | **365** | 17× |
| Autonomous | 12 | ? | **1.274** | >100× |
| ICE | 30 | 92 | 270 | 9× |
| Perovskite | 9 | 39 | 280 | 31× |
| PQC | 17 | 6 | 172 | 29× |

**Root-Cause:** UC8 zählt vermutlich nur Akteure mit Aktivität im Jahresfenster; UC9 nur Akteure innerhalb identifizierter Cluster; UC11 zählt alle Akteure inklusive CORDIS-Organisationen. **Keine UI-Klarstellung**, welcher Scope gemeint ist.

**Fix-Richtung:** UI-Labels präzisieren (z. B. „aktive Patentanmelder letzter 10 J", „Cluster-Mitglieder", „alle assoziierten Organisationen"). Oder eine Master-Definition „Akteur" und alle UCs zählen gleich.

### CRIT-4 · Patent-Population Header vs. UC12 divergiert

| Tech | Header „Patente" | UC12 Anmeldungen | Faktor |
|---|---:|---:|---:|
| mRNA | 742 | 4.024 | 5,4× |
| Solid State | 358 | 12.074 | 33× |
| Autonomous | 734 | 6.336 | 8,6× |
| ICE | 10.200 | 30.500 | 3× |
| Perovskite | 101 | **5.462** | **54×** |
| PQC | 8 | 83 | 10× |

**Root-Cause-Hypothese:** Header zählt vermutlich Patentfamilien mit eigenem Filter (z. B. EU-only / letzter 10 J), UC12 zählt alle Anmeldungen über die ganze Zeit. Aber: Perovskite Header 101 vs. UC12 5.462 ist ein Faktor 54 — das kann nicht nur Zeitraumlogik sein, das ist ein echter Query-Mismatch.

**Fix-Richtung:** Header-KPI „Patente" einheitlich definieren (Veröffentlichungen / Anmeldungen / Familien?), gleiche Query für Header und UC12-Summe.

### MAJ-5 · Header-Doppel-Phase vs. UC2-Einzelphase

Der Header „Phase:" zeigt durchweg **zwei S-Kurven-Phasen** kombiniert, die semantisch unverträglich sind:

| Tech | Header | UC2 intern | Kommentar |
|---|---|---|---|
| mRNA | **Reife + Rückläufige Entwicklung** | Reife | 2 Phasen verkettet |
| Solid State | **Reife + Stagnation** | Reife (CAGR +35,5 %!) | Stagnation widerspricht CAGR |
| Autonomous | **Reife + Rückläufige Entwicklung** | Reife | 2 Phasen |
| ICE | **Reife + Rückläufig** | Reife (R²=0,999, CAGR −7,6 %) | Reife passt nicht zu −7,6 % |
| Perovskite | **Reife + Rückläufig** | Reife (R²=1,000) | R²=1 bei wachsendem Feld |
| PQC | **Entstehung + Stagnation** | Entstehung (R²=0,000!) | Stagnation unbegründet |

Die UI scheint einen zweiten Label-Slot im Header mit einer **CAGR-basierten Phrase** zu befüllen, die vom S-Kurven-Phase-Label unabhängig ist und oft widerspricht. Beide werden ohne Trennung konkateniert.

**Fix-Richtung:** Header entweder nur die S-Kurven-Phase zeigen oder ein zweites, klar beschriftetes Feld („Trend:").

### MAJ-6 · Wettbewerbs-Widerspruch Header vs. UC3

Header zeigt für **alle sechs Techs** das Label **„Wettbewerbsintensiver Markt"**. UC3 selbst zeigt für alle sechs Techs **„Niedrige Konzentration"** mit HHI-Werten, die tatsächlich auf einen fragmentierten Markt hinweisen.

**Root-Cause:** „Wettbewerbsintensiv" ist offenbar ein hart kodierter Fallback-Text, der **immer** gerendert wird, unabhängig vom tatsächlichen HHI-Wert. Das entwertet das Label und täuscht den Nutzer.

**Fix-Richtung:** Label aus dem HHI ableiten:
- HHI > 2500 → „Hohe Konzentration / wenige dominante Player"
- HHI 1500–2500 → „Mittlere Konzentration"
- HHI < 1500 → „Niedrige Konzentration / fragmentiert"

### MAJ-7 · Jahresachsen-Inkonsistenz innerhalb eines Dashboards

| UC | Jahresachse (Endjahr) |
|---|---|
| UC1 Aktivitätstrends | 2026 |
| UC2 S-Kurve | 2026 |
| UC8 Dynamik & Persistenz | 2026 |
| UC12 Patenterteilung | 2026 |
| UC7 Forschungsimpact | **2024** |
| UC13 Publikationen | **2024** |

Forschungs-Panels reichen zwei Jahre weniger weit als Patent-/Aktivitäts-Panels. **Kein Hinweis** in der UI, dass die Zeiträume unterschiedlich sind. Ein Nutzer, der „Veränderung 2024→2025" sehen will, kriegt UC13-null aber UC2-sehr-aktiv.

**Root-Cause:** Semantic-Scholar / CORDIS-Publications-Daten kommen verzögert, aber die Zeitraumfilter in allen UCs sollten sich dasselbe Enddatum teilen, egal ob Daten da sind.

**Fix-Richtung:** Gleiche Enddatumsklammer in allen UCs. Fehlende Jahre explizit als „null" einblenden.

### MAJ-8 · Unvollständige Jahre in S-Kurve / CAGR

Heute ist **2026-04-14**. 2026 ist zu 28,3 % abgelaufen. 2025 ist vollständig.

S-Kurve (UC2) und Aktivitätstrends (UC1) zeigen bei mehreren Techs Jahre bis **2026** ohne erkennbare Extrapolation. Dadurch:

- S-Kurven-Fit zieht Endjahr-Daten mit Teilmenge → ggf. **falsches R²** (oft unrealistisch hoch: 0,998, 0,999, 1,000).
- CAGR 2017–2026 ist eine „9-Jahre-CAGR", die wegen des unvollständigen Endjahrs ~9 % unterschätzt.

Der Warnhinweis **„Daten ggf. unvollständig"** existiert in UC1, UC2, UC8 — aber **nicht** in UC7, UC12, UC13, wo er ebenso nötig wäre.

**Fix-Richtung:**
- Default-Endjahr = **letztes vollständiges Kalenderjahr** (2025).
- Wenn 2026 explizit gezeigt wird, annotieren als „bis $TODAY (Teiljahr)".
- CAGR auf vollständige Jahre beschränken, alternativ als „YoY-Trend" explizit labeln.
- Warnhinweis überall ergänzen wo Jahre-Teilaggregation passiert.

### MAJ-9 · R² und Konfidenz entkoppelt — statistisch unsinnig

**PQC** zeigt UC2 „R² = 0.000" **und** „Konfidenz: 80 %" **und** „Phase: Entstehung". R² = 0 bedeutet: Das Sigmoid-Fit-Modell erklärt null Prozent der Varianz. Ein Phase-Label mit 80 % Konfidenz ist dann **Scheinsicherheit**.

**mRNA** zeigt R² = 0,998. **Perovskite** R² = 1,000. Solche R²-Werte sind in realen, verrauschten Patentdaten über 10 Jahre extrem verdächtig — sie deuten auf Overfitting oder auf einen **degenerierten Fit** (z. B. wenn die Kurve monoton auf einen einzigen Peak geht).

**Fix-Richtung:**
- R² < 0,5 → Phase-Label ausgrauen und Konfidenz auf „niedrig" setzen.
- R² > 0,98 bei < 30 Datenpunkten → Overfitting-Warnung.
- Konfidenz-Berechnung muss R² einbeziehen, nicht unabhängig sein.

### MIN-10 · Projekt-Zählbasis Header vs. UC4 vs. UC10 leicht abweichend

| Tech | Header „EU-Projekte" | UC4 Projekte | UC10 Projekte |
|---|---:|---:|---:|
| mRNA | 307 | 307 ✅ | 387 |
| Solid State | 113 | 113 ✅ | 106 |
| ICE | 48 | 48 ✅ | 58 |

Header und UC4 stimmen immer überein (beide zählen CORDIS-Projekte mit Technologie-Match). UC10 zeigt eine andere Zahl — vermutlich werden Projekte nach EuroSciVoc-Feld aggregiert und einige haben keinen Tag, andere haben mehrere (Doppelzählung).

---

## 2. UC-Ampel-Matrix (Konsolidiert über 3 Interpreter-Agenten × 6 Techs)

Legende: 🟢 = Versprechen erfüllt · 🟡 = teilweise · 🔴 = nicht erfüllt / irreführend

| UC | Versprechen | mRNA | SSB | AD | ICE | Per | PQC | Konsens |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| UC1 Aktivitätstrends | CAGR-Trends, Dynamik | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 Teilweise (Chart ok, CAGR-Fenster fragwürdig) |
| UC2 S-Kurve & Reife | Phase per Sigmoid-Fit | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 Rot (R²-Chaos, Phase-Label unstabil) |
| UC3 Wettbewerb | HHI-Konzentration | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 (UC3 selbst korrekt, aber Header-Label lügt) |
| UC4 Förderung | EU-Fördervolumen | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | **🟢 Grün** (beste UC) |
| UC5 CPC-Konvergenz | CPC-Kookkurrenz | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | **🟢 Grün** |
| UC6 Geographie | Länder-Verteilung | 🟢 | 🟢 | 🟡 | 🟢 | 🟢 | 🟡 | 🟡 (meist ok) |
| UC7 Forschungsimpact | h-Index, Zitationen | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 Rot (widerspricht Header) |
| UC8 Dynamik | Akteursdynamik | 🟡 | 🟡 | 🔴 | 🟡 | 🟡 | 🔴 | 🟡/🔴 (Jahre-Fenster, Akteurszählung) |
| UC9 Tech-Cluster | 5-dim Profil | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 (Radar-Chart da, Herkunft unklar) |
| UC10 EuroSciVoc | Wissenschaftsdisziplin | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | **🔴 Rot** (Shannon-Bug + fachlich falsch) |
| UC11 Akteurs-Typen | HES/PRC/PUB/KMU | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 (Zahlen da, Zählbasis unklar) |
| UC12 Patenterteilung | Grant-Rate / Time-to-Grant | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 (Population ≠ Header) |
| UC13 Publikations-Impact | Pub/Projekt, DOI | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 (Publikations-Triplet-Bug) |

**Score:** 2 🟢 / 5 🟡 / 6 🔴 = **UC-Qualität im Durchschnitt 31 %**.

---

## 3. Priorisierte Bug-Liste mit Fix-Richtung

| # | ID | Severity | Wo | Kurzbeschreibung | Fix-Richtung |
|---|---|---|---|---|---|
| 1 | CRIT-1 | Critical | Header × UC7 × UC13 | Publikationszahl 3× widersprüchlich | Single-Source-of-Truth Publikations-Query |
| 2 | CRIT-2 | Critical | UC10 | Shannon > 0 bei 1 Feld + fachlich falsche Disziplin | EuroSciVoc-Query-Level korrigieren, Shannon-Definition prüfen |
| 3 | CRIT-3 | Critical | UC8/UC9/UC11 | Akteurs-Zählung divergiert bis Faktor 100 | Scope-Labels klarstellen ODER einheitliche Master-Definition |
| 4 | CRIT-4 | Critical | Header × UC12 | Patent-Population divergiert bis Faktor 54 | Header-KPI-Definition harmonisieren |
| 5 | MAJ-5 | Major | Header | Doppel-Phase vermischt 2 Konzepte | Phase-Label + separates „Trend:"-Feld |
| 6 | MAJ-6 | Major | Header | „Wettbewerbsintensiv" als Fallback-Lüge | Label aus HHI ableiten |
| 7 | MAJ-7 | Major | Cross-UC | Jahresachsen 2024 vs. 2026 inkonsistent | Gemeinsame Endjahr-Klammer; fehlende Jahre = null |
| 8 | MAJ-8 | Major | UC1/UC2 | Unvollständige Jahre 2025/2026 in CAGR & S-Kurve-Fit | Default-Endjahr = letztes vollständiges Jahr; Warnhinweis überall |
| 9 | MAJ-9 | Major | UC2 | R² = 0 mit 80 % Konfidenz ist Scheinsicherheit | Konfidenz an R² koppeln; R² < 0,5 → Label ausgrauen |
| 10 | MIN-10 | Minor | UC10 | Projekt-Zahl vs. Header leicht abweichend | Aggregationslogik prüfen (Doppel-Tags) |
| 11 | MIN-11 | Minor | UC13 | Pub/Projekt-Kennzahl nicht ins Gesamt umgerechnet | Im Panel explizite Gesamtzahl + Methodik ausweisen |
| 12 | INFO-12 | Info | Header | „Sehr hoher Forschungsimpact" ohne Zahlen-Beleg | Qualitative Labels mit expliziten Schwellen hinterlegen |

---

## 4. Nutzbarkeits-Fazit pro Entscheidungsklasse

| Entscheidungsbereich | TI-Radar heute brauchbar? | Begründung |
|---|:-:|---|
| **Fördermittel-Landschaft** (welche Instrumente, welches Volumen, wie verteilt) | ✅ | UC4 ist der stärkste UC, Zahlen konsistent |
| **Technologie-Konvergenz / CPC-Whitespace** | ✅ | UC5 + Jaccard + Whitespace-Analyse glaubwürdig |
| **Geographische Schwerpunkte** | ✅ | UC6 in 4/6 Fällen 🟢 |
| **Partner-Scouting** (wer sind die Top-Akteure) | ⚠ | UC3 Top-N korrekt, aber HHI-Interpretation im Header falsch |
| **Reifegrad / S-Kurven-Phase** | ❌ | UC2 liefert unglaubwürdige R²-Werte (0,000 ↔ 1,000), Phase-Label oft widersprüchlich |
| **Forschungs-Impact** (h-Index, Zitationsraten) | ❌ | UC7 widerspricht Header-Claim systematisch |
| **Marktgröße / Anzahl Akteure** | ❌ | Drei UCs zählen je unterschiedlich, keine Erklärung |
| **Publikations-Volumen** | ❌ | Drei-fach widersprüchliche Zahlen |
| **Wissenschaftsdisziplin / Interdisziplinarität** | ❌ | UC10 fachlich & mathematisch fehlerhaft |
| **Patent-Erteilungschancen** | ❌ | Population widersprüchlich zum Header |

**Gesamt:** Das Radar ist ein **Scouting-Werkzeug** (Förderung + Konvergenz + Geographie), aber **kein Entscheidungsinstrument** für Marktanalyse, Wettbewerb oder Reifegrad — solange diese Bugs offen sind.

---

## 5. Empfohlene Sofortmaßnahmen (priorisiert)

1. **Pressing:** Header-Publikationszahl deaktivieren bis Single-Source-of-Truth etabliert ist. Aktuell irreführt er Budget-Entscheider mehr als er hilft.
2. **Pressing:** UC10 komplett auf „preview"-Status setzen. Shannon-Bug + falsche Disziplinzuordnung machen das Panel gerade gefährlich.
3. **Wichtig:** UC2 S-Kurven-Konfidenz an R² koppeln, Phase-Label bei R² < 0,5 ausgrauen.
4. **Wichtig:** Default-Endjahr aller Zeitreihen = **2025** (letztes vollständiges Kalenderjahr). 2026 nur auf expliziten User-Wunsch.
5. **Wichtig:** Header „Wettbewerbsintensiver Markt" als Fallback-Label entfernen; stattdessen aus HHI ableiten.
6. **Wichtig:** Single-Source-Definitionen für „Patent", „Projekt", „Akteur", „Publikation" in `packages/shared/domain/` zentralisieren; alle Panels darauf umstellen.
7. **Mittel:** UI-Warning „Daten ggf. unvollständig" in **allen** Zeitreihen-Panels (nicht nur UC1/UC2/UC8).
8. **Mittel:** Akteurs-Scope-Labels in UC8/UC9/UC11 präzisieren (z. B. „aktive Akteure im Fenster" vs. „Cluster-Mitglieder" vs. „alle Organisationen").

---

## 6. Nachweisführung

- **Rohdaten** (18 JSONs): `docs/testing/ergebnisse/konsistenz/raw/raw3_<tech>.json`
- **Agent-Berichte** (18 MDs): `docs/testing/ergebnisse/konsistenz/agents/`
- **Erste-Welle-Berichte** (leere Extraktion, nur Header-Befunde): `docs/testing/ergebnisse/konsistenz/agents_erste_welle/`
- **Dashboard-Screenshots**: `docs/testing/ergebnisse/konsistenz/raw/raw_*_dashboard.png` (6 × Full-Page)
- **Briefing**: `docs/testing/ergebnisse/konsistenz/AGENT_BRIEF.md`
