# Testprotokoll — Claude (ich) · Playwright MCP (visuelle Plausibilität)

> **Adressat:** Ich selbst (Claude Code in dieser Sitzung), ausgeführt über das MCP-Plugin `plugin_playwright_playwright` (`browser_navigate`, `browser_snapshot`, `browser_take_screenshot`, `browser_evaluate`).
> **Warum diese Technologie:** Playwright MCP gibt mir eine **echte Browser-Sicht** ohne Test-Framework-Overhead. Ideal für inhaltliche Plausibilitätsprüfungen und visuelle Verifikation, die kein automatisierter Agent (Cypress/k6/Schemathesis) leisten kann.

---

## 1. Mission

Aus End-Nutzer-Perspektive alle **13 Use-Case-Panels** für drei diverse Technologien visuell durchsehen und prüfen, ob die dargestellten KPIs **inhaltlich plausibel** sind.

Der Fokus liegt auf **Interpretation**, nicht Automatisierung:
- Sind die Zahlen in realistischen Bereichen?
- Passen Chart-Formen zur erwarteten Semantik (S-Kurve monoton steigend, Treemap nicht-überlappend)?
- Sind Labels sinnvoll übersetzt (DE/EN)?
- Bleibt die UI auch bei Edge-Case-Techs (0 Treffer) nutzbar?

---

## 2. Prerequisites

```bash
# Stack läuft?
docker compose -f deploy/docker-compose.yml ps
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:3000 | head -c 200
```

Falls nicht: `cd deploy && make up && sleep 40`.

---

## 3. Referenz-Technologien

| Tech | Erwartete Charakteristik | Warum? |
|---|---|---|
| `quantum computing` | Wachstumstech mit EU + US + CN, mittlere Konzentration | Breit, Daten in allen UCs |
| `CRISPR` | Life-Science, USPTO-lastig, konzentriertes Feld | Anderer CPC-Cluster, andere Akteurstypen |
| `hydrogen fuel cell` | Energie, EU-Förderdominanz (Horizon Europe) | Aktiviert UC4-Funding deutlich |
| `xyz_unknown_tech_9999` | 0 Treffer | Empty-State, kein Crash |

---

## 4. Technische Abdeckung

| Schicht | Abdeckung |
|---|:-:|
| Frontend (Next.js + React) | ✅ voll (echter Browser) |
| API-Gateway (indirekt) | ◻ |
| Business-Logik (indirekt) | ◻ |
| Chart-Libraries (Recharts, Nivo, react-force-graph) | ✅ visuell |

---

## 5. Inhaltliche Abdeckung (Plausibilitätskriterien pro UC)

| UC | Panel | Plausibilitätskriterium | Rote Flagge |
|---|---|---|---|
| UC1 | Landschaft | Time-Series steigt bei Wachstumstech; CAGR numerisch | Alle Jahre 0; CAGR als Text |
| UC2 | Reife | S-Kurve monoton; Phase-Badge aus {Einführung, Wachstum, Reife, Sättigung, Rückgang} | Kurve zickzackt; Phase fehlt |
| UC3 | Wettbewerb | HHI ∈ [0, 10 000]; Top-5-Anmelder namentlich sinnvoll; Netzwerk-Graph vorhanden | HHI = NaN / negativ; Namen leer |
| UC4 | Förderung | Treemap-Rechtecke summieren zu Budget; Top-Programm erkennbar (Horizon Europe etc.) | Leere Fläche trotz Daten |
| UC5 | CPC-Konvergenz | Chord verbindet plausible CPC-Paare (z. B. G06N + H04L für Quantencrypto) | Graph leer / nur Diagonale |
| UC6 | Geographie | Top-5 Länder mit ISO-2-Codes; Kollaborations-Paare plausibel (DE-FR, US-CN) | Länder nur als 3-Zeichen-Müll |
| UC7 | Wirkung | h-Index ≥ 0; Top-Papers mit Titel + Jahr + Zitationen | h-Index als Komma-Zahl; Titel leer |
| UC8 | Zeitliche Trends | New-Entrant-Rate 0-100 %; Persistence-Kurve | Prozentwert > 100 |
| UC9 | Themencluster | ≥ 3 Cluster mit prägnanten Labels | Nur „Cluster 1", „Cluster 2" |
| UC10 | EuroSciVoc | Taxonomie-Baum mit mind. 2 Ebenen | Nur ID-Codes, keine Klartexte |
| UC11 | Akteurstypen | Breakdown HES+PRC+PUB+OTH summiert zu ~100 % | Summe > 100 % oder < 50 % |
| UC12 | Patent-Erteilung | Grant-Rate 0-100 %; Time-to-Grant in Jahren | Werte > 20 Jahre Median |
| UC-C | Publikationen | OA-Share 0-100 %; Publikationsliste | OA-Share als Dezimal > 1 |

---

## 6. Ablauf (Script, das ich selbst ausführe)

### Phase A · Smoke

1. `Bash: docker compose -f deploy/docker-compose.yml ps` — verifiziere alle Container `Up (healthy)`.
2. `browser_navigate: http://localhost:3000` — erwartet: Landing rendert.
3. `browser_snapshot` — Landing festhalten.
4. `browser_take_screenshot(filename="00_landing.png")`.

### Phase B · Happy Path je Referenz-Tech

**Für jede Tech in [`quantum computing`, `CRISPR`, `hydrogen fuel cell`]:**

5. Navigate zu `/radar/<urlencoded tech>`.
6. Warte bis alle 13 Panels sichtbar sind:
   ```js
   // via browser_wait_for oder browser_evaluate
   await new Promise(r => setTimeout(r, 60000)); // Fan-Out-Max-Timeout
   ```
7. `browser_snapshot` (ARIA-Struktur) — prüfe auf „UC1"-„UC-C" als Text.
8. Screenshots scrollen:
   - `NN_<tech>_top.png` (above fold)
   - `NN_<tech>_mid.png` (scroll 50 %)
   - `NN_<tech>_bot.png` (scroll 100 %)
9. `browser_evaluate` — KPI-Extraktion, Rückgabe als JSON:
   ```js
   () => {
     const find = (re) => {
       const el = Array.from(document.querySelectorAll("*")).find(n => re.test(n.textContent ?? ""));
       return el?.textContent ?? null;
     };
     return {
       CAGR: find(/CAGR\s*[:=]?\s*[-+]?\d/),
       HHI:  find(/HHI\s*[:=]?\s*\d/),
       hIndex: find(/h.?Index\s*[:=]?\s*\d/),
       oaShare: find(/Open.?Access\s*[:=]?\s*\d/),
       phase: find(/Einführung|Wachstum|Reife|Sättigung|Rückgang|Introduction|Growth|Maturity|Saturation|Decline/),
       panelHeadings: Array.from(document.querySelectorAll("h2,h3,[role='heading']")).map(n => n.textContent?.trim()),
     };
   }
   ```
10. Werte gegen Plausibilitätsmatrix (§ 5) abgleichen — Ergebnis pro Panel in `TECH_<tech>_plausibility.md`-Fragment notieren.

### Phase C · Filter-Interaktion

11. Zurück auf `/radar/quantum%20computing`.
12. Wenn ein Zeitraum-Filter sichtbar ist: Startjahr auf `2020` setzen.
13. `browser_network_requests` — prüfe, dass `/api/v1/radar` erneut feuert.
14. Screenshot `10_filter_2020.png`.

### Phase D · Compare

15. Navigate `/compare?a=quantum%20computing&b=CRISPR`.
16. Warte, Screenshot `20_compare.png`.
17. Verifiziere via Snapshot: „quantum computing" und „CRISPR" beide sichtbar.

### Phase E · Export-Stichprobe

18. Zurück auf `/radar/quantum%20computing`.
19. Suche Export-Button (Regex „CSV" o. ä.), klicke.
20. `browser_network_requests` — prüfe Download-URL.
21. `Bash: curl -sS "<URL>" -o /tmp/radar_export.csv && head -20 /tmp/radar_export.csv` — stichprobenartige Inhaltsprüfung.

### Phase F · Empty State / Fehlerfall

22. Navigate `/radar/xyz_unknown_tech_9999`.
23. Warte, Screenshot `30_empty.png`.
24. Snapshot prüfen: Keine React-Error-Boundary, stattdessen Empty-State-Meldung.

### Phase G · Bericht schreiben

25. Konsolidiere alle Erkenntnisse in `docs/testing/ergebnisse/claude_playwright_bericht.md` (Template siehe § 8).
26. Mindestens 13 Screenshots (1 je UC, bevorzugt von `quantum computing`-Lauf) ablegen unter `docs/testing/ergebnisse/screenshots/`.

---

## 7. Stop- und Fehlerkriterien

| Beobachtung | Aktion |
|---|---|
| `/api/v1/radar` liefert 500/504 | Abbruch, Bug-Notiz, Stack-Logs in Bericht aufnehmen |
| Page-Load > 90 s | Abbruch der aktuellen Tech, nächste probieren |
| React-Error-Boundary sichtbar | Screenshot, Console-Log via `browser_console_messages` einsammeln |
| > 3 Panels zeigen „Keine Daten" bei Wachstumstech | In Bericht als Major-Befund markieren |

---

## 8. Ergebnis-Dokumentation (Template)

Schreibe `docs/testing/ergebnisse/claude_playwright_bericht.md`:

```markdown
# Ergebnis · Claude · Playwright MCP

**Lauf:** <ISO-Datum> · **Browser:** Chromium (Playwright MCP default) · **Stack-Commit:** <SHA>

## Setup-Smoke

| Check | Status |
|---|---|
| Stack `Up (healthy)` | ✅/❌ |
| `/health` 200 | ✅/❌ |
| Landing rendert | ✅/❌ |

## Pro Tech: UC-Panel × Plausibilität

### quantum computing

| UC | Panel sichtbar | KPI plausibel | Kommentar | Screenshot |
|---|:-:|:-:|---|---|
| UC1 | ✅ | ✅ | CAGR 14,2 % – realistisch | `ss/01_uc1_quantum.png` |
| UC2 | ✅ | ⚠ | Phase-Badge fehlt (Graph aber da) | `ss/02_uc2_quantum.png` |
| UC3 | ✅ | ✅ | HHI = 1837 | `ss/03_uc3_quantum.png` |
| UC4 | ⚠ | – | Treemap leer obwohl EU-Förderung erwartet | `ss/04_uc4_quantum.png` |
| … | | | | |

### CRISPR

*(gleiche Tabelle)*

### hydrogen fuel cell

*(gleiche Tabelle)*

## Filter-Interaktion

- Zeitraum 2020+: <Beobachtung>
- Re-Fetch ausgelöst: ✅/❌

## Compare

- quantum vs. CRISPR nebeneinander: ✅/❌ (Screenshot `ss/20_compare.png`)

## Export-Stichprobe

- Format CSV: <Dateigröße>, <erste 5 Zeilen plausibel ja/nein>
- Kopf: `"tech","year","count",...`

## Empty State

- `xyz_unknown_tech_9999`: <Verhalten>

## Gefundene Auffälligkeiten (Severity, Steps, Vorschlag)

### OBS-PW-001 · Severity: Major · UC4 Treemap leer bei hydrogen fuel cell
**Kontext:** Treemap erwartet Horizon-Europe-Budget-Breakdown. Actual: Panel zeigt „Keine Daten".
**Screenshot:** `ss/04_uc4_hydrogen.png`.
**Vermutung:** Cordis-Mock-Daten decken Hydrogen nicht ab — **kein Produkt-Bug**, sondern Daten-Scope.
**Empfehlung:** Mock-Daten erweitern ODER Empty-State-Copy präzisieren (Daten-Disclaimer statt „Keine Daten").

### OBS-PW-002 · …

## Coverage

- 13 UC-Panels · 3 Techs = 39 Panel-Checks
- Davon ✅ visuell + KPI plausibel: <n>/39 (<%>)
- ⚠ sichtbar aber KPI-Anomalie: <n>
- ❌ Panel nicht gerendert: <n>

## Empfehlungen

- <z.B.: `data-testid` in Panels einführen — stabilisiert Cypress-Tests>
- <z.B.: Empty-State-Copy je UC differenzieren>
- <z.B.: Export-Button-Label zweisprachig>
```

---

## 9. Grenzen dieses Protokolls

- **Ich fälle Inhaltsurteile**, keine Automatisierung — nächste Person sieht evtl. anderes.
- **Keine Cross-Browser-Matrix** (nur Chromium via MCP).
- **Keine Latenz-Messung** — das macht Agent 2.
- **Keine API-Edge-Cases** — das macht Agent 3.
- **Nur Spot-Checks je UC** — Vollregression macht Agent 1.
