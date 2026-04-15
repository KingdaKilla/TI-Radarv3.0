# Testprotokoll — Agent 2 · k6 (Performance & Chaos)

> **Adressat:** Claude-Code-Subagent, der diese Datei liest und eigenständig ausführt.
> **Technologie:** [Grafana k6](https://k6.io/) — Performance-Testing mit JavaScript-DSL, Go-Runtime.
> **Warum diese Technologie:** k6 ist **nicht** im Stack; bestehende Tests prüfen Korrektheit, nicht Latenz/Durchsatz/Robustheit. k6 füllt genau diese Lücke und kann zusätzlich Chaos-Szenarien (UC-Ausfall) messen.

---

## 1. Mission

Beweise unter Last, dass:

1. der Orchestrator bei **realistischer Last** (10 parallele Nutzer × 5 min) stabil bleibt (p95 < 3 s, Fehlerrate < 1 %),
2. der **Rate-Limiter** (100 req/min pro IP, `services/orchestrator-svc/src/middleware.py:223`) in einem Spike-Szenario sauber 429 zurückgibt,
3. bei **Soak-Lasten** (30 min) keine Memory-Leaks / degradierenden Latenzen auftreten,
4. **Graceful Degradation** funktioniert: stoppe einen UC-Service während des Tests → Requests liefern weiterhin 200 OK mit `warnings[]`,
5. die dokumentierten **Timeout-Grenzen** (UC2/3/5/9 = 60 s, sonst 30 s aus `grpc_clients.py`) auch unter Last eingehalten werden,
6. `/api/v1/suggestions` Autocomplete-Performance-Ziel erreicht (p95 < 200 ms).

---

## 2. Prerequisites

```bash
cd deploy && make up && cd ..
sleep 45
for url in http://localhost:8000/health http://localhost:8000/metrics http://localhost:3000; do
  curl -fsS "$url" -o /dev/null && echo "OK: $url" || echo "FAIL: $url"
done
```

Wenn ein Check fehlschlägt → **STOP**, Ergebnis dokumentieren, abbrechen.

### API-Key

Prüfe: `grep TI_RADAR_API_KEY deploy/.env 2>/dev/null` — falls gesetzt, in Script als `__ENV.TI_RADAR_API_KEY` verwenden.

---

## 3. Setup

### 3.1 k6 installieren (eine der folgenden Methoden)

```bash
# macOS
brew install k6

# Linux (Debian/Ubuntu)
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt update && sudo apt install -y k6

# Docker (plattformunabhängig, keine Installation)
alias k6="docker run --rm -i --network host grafana/k6 run -"
```

### 3.2 Projekt-Struktur

```bash
mkdir -p tests/performance/{scripts,fixtures,reports}
```

### 3.3 Realistische Test-Technologien

Extrahiere aus `database/mock_data/patents.csv` die 20 häufigsten Titel-Keywords:

```bash
python3 - <<'PY' > tests/performance/fixtures/techs.json
import csv, json, re, collections
words = collections.Counter()
with open("database/mock_data/patents.csv") as f:
    for row in csv.DictReader(f):
        for w in re.findall(r"[A-Za-z]{4,}", (row.get("title") or "").lower()):
            words[w] += 1
top = [w for w, _ in words.most_common(20)]
json.dump(top, open("/dev/stdout", "w"))
PY
```

---

## 4. Technische Abdeckung

| Schicht | Abdeckung | Mechanismus |
|---|---|---|
| API-Gateway (Orchestrator) | ✅ voll | alle Szenarien |
| gRPC-Fan-Out | ✅ | Timing pro Request + Chaos-Szenario |
| Business-Logik (UC-Services) | ◻ indirekt | Latenz-Breakdown via `timings` im Response |
| Rate-Limit-Middleware | ✅ | Spike-Szenario |
| Graceful Degradation | ✅ | Fan-Out-Chaos-Szenario |
| Prometheus-Metriken | ✅ | vor/nach Lauf `/metrics` scrapen |

---

## 5. Inhaltliche Abdeckung

| UC | Prim | Wie geprüft |
|---|:-:|---|
| UC1, UC2, UC3, UC5, UC9 | ✅ | explizit im Payload + Timing-Assertion |
| UC4, UC6, UC7, UC8, UC10, UC11, UC12, UC-C | ◻ | werden als Teil des Fan-Out abgerufen, aber nicht einzeln gemessen |
| Fehlertoleranz | ✅ | Chaos stoppt `ti-radar-uc1` → Assertion: 200 + warnings |
| Autocomplete | ✅ | eigenes Szenario |

---

## 6. Test-Szenarien

### 6.1 Szenario BASELINE — `tests/performance/scripts/radar_baseline.js`

```js
import http from "k6/http";
import { check, sleep } from "k6";
import { Trend, Rate } from "k6/metrics";
import { SharedArray } from "k6/data";

const TECHS = new SharedArray("techs", () => JSON.parse(open("../fixtures/techs.json")));
const BASE = __ENV.BASE_URL || "http://localhost:8000";
const API_KEY = __ENV.TI_RADAR_API_KEY || "";

const ucTrend = new Trend("radar_uc_latency_ms", true);
const fanoutOk = new Rate("radar_fanout_ok");

export const options = {
  scenarios: {
    baseline: { executor: "constant-vus", vus: 10, duration: "5m", gracefulStop: "30s" },
  },
  thresholds: {
    "http_req_duration{endpoint:radar}": ["p(95)<3000", "p(99)<8000"],
    "http_req_failed{endpoint:radar}":    ["rate<0.01"],
    "radar_fanout_ok":                    ["rate>0.98"],
  },
};

export default function () {
  const tech = TECHS[Math.floor(Math.random() * TECHS.length)];
  const res = http.post(
    `${BASE}/api/v1/radar`,
    JSON.stringify({
      tech,
      timerange: { start_year: 2015, end_year: 2024 },
      filter: { top_n: 10 },
    }),
    {
      headers: {
        "Content-Type": "application/json",
        ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
      },
      tags: { endpoint: "radar" },
      timeout: "120s",
    }
  );
  check(res, {
    "200": (r) => r.status === 200,
    "enthält uc1": (r) => r.body.includes("uc1") || r.body.includes("landscape"),
    "<= 13 warnings": (r) => {
      try {
        const j = r.json();
        return !j.warnings || j.warnings.length <= 13;
      } catch { return false; }
    },
  });
  fanoutOk.add(res.status === 200);
  try {
    const j = res.json();
    if (j.timings) for (const [uc, ms] of Object.entries(j.timings)) ucTrend.add(ms, { uc });
  } catch {}
  sleep(1);
}
```

**Akzeptanzkriterien:** alle 3 Thresholds `green`. Bei rot: Bug-Report.

### 6.2 Szenario SPIKE — Rate-Limit verifizieren

```js
// tests/performance/scripts/radar_spike.js
export const options = {
  scenarios: {
    spike: {
      executor: "ramping-arrival-rate",
      startRate: 10, timeUnit: "1s",
      preAllocatedVUs: 200,
      stages: [
        { target: 10, duration: "10s" },
        { target: 200, duration: "30s" },  // explodieren
        { target: 10, duration: "20s" },
      ],
    },
  },
  thresholds: {
    "http_reqs{status:429}": ["count>0"],     // MUSS 429 erzwingen
    "http_reqs{status:500}": ["count<5"],     // KEINE Crashes
  },
};
```

**Akzeptanz:** Im Peak fliegen 429er; Server-Logs zeigen keine ungebremsten 5xx.

### 6.3 Szenario SOAK — Memory-/Latenz-Drift

```js
// tests/performance/scripts/radar_soak.js
export const options = {
  scenarios: {
    soak: { executor: "constant-vus", vus: 5, duration: "30m" },
  },
  thresholds: {
    "http_req_duration": ["p(95)<3500"],  // Drift-Toleranz +500ms
  },
};
```

**Zusatz:** Vor und nach dem Lauf `/metrics` scrapen; `process_resident_memory_bytes` sollte nicht um > 25 % wachsen.

```bash
curl -s http://localhost:8000/metrics | grep -E 'process_resident_memory_bytes|python_gc' \
  > tests/performance/reports/metrics_before.txt
k6 run tests/performance/scripts/radar_soak.js
curl -s http://localhost:8000/metrics | grep -E 'process_resident_memory_bytes|python_gc' \
  > tests/performance/reports/metrics_after.txt
diff tests/performance/reports/metrics_before.txt tests/performance/reports/metrics_after.txt
```

### 6.4 Szenario CHAOS — Graceful Degradation

Parallel zum k6-Lauf einen UC-Service stoppen:

```bash
# Terminal 1: k6 starten
k6 run --duration 3m tests/performance/scripts/radar_baseline.js &
K6_PID=$!

# Terminal 2 (oder inline nach 30s):
sleep 30
docker stop ti-radar-uc1     # UC1 = landscape-svc
echo "--- UC1 down ---"
sleep 60
docker start ti-radar-uc1
wait $K6_PID
```

**Modifizierte Script-Assertion** in `radar_baseline.js` (Chaos-Variante):

```js
check(res, {
  "200 trotz UC-Ausfall": (r) => r.status === 200,
  "warnings erwähnen uc1 im Chaos-Fenster": (r) => {
    try {
      const j = r.json();
      // Akzeptanz: entweder uc1 liefert Daten ODER warnings enthält "landscape"/"uc1"
      return (j.uc1 && Object.keys(j.uc1).length) ||
             (j.warnings || []).some(w => /uc1|landscape/i.test(w));
    } catch { return false; }
  },
});
```

**Akzeptanzkriterium:** Fehlerrate (status ≠ 200) im Chaos-Fenster < 5 % (GRACEFUL, kein totaler Ausfall).

### 6.5 Szenario TIMEOUTS — 60-s-UCs respektieren

```js
// tests/performance/scripts/uc_timeout_check.js
import http from "k6/http";
import { Trend } from "k6/metrics";

const ucTimings = new Trend("uc_observed_ms", true);
export const options = { vus: 3, duration: "2m" };

export default function () {
  const res = http.post(`${__ENV.BASE_URL || "http://localhost:8000"}/api/v1/radar`,
    JSON.stringify({ tech: "quantum computing" }),
    { headers: { "Content-Type": "application/json" }, timeout: "120s" });
  try {
    const t = res.json("timings");
    Object.entries(t).forEach(([uc, ms]) => ucTimings.add(ms, { uc }));
  } catch {}
}

export function handleSummary(data) {
  // Assertions ENFORCED via Thresholds bei Bedarf.
  return { "reports/timeouts.json": JSON.stringify(data.metrics.uc_observed_ms.values, null, 2) };
}
```

**Akzeptanz:** Kein UC überschreitet sein Timeout-Limit (UC2/3/5/9 < 60s, sonst < 30s).

### 6.6 Szenario SUGGESTIONS — Autocomplete p95 < 200 ms

```js
// tests/performance/scripts/suggestions.js
export const options = {
  scenarios: {
    sugg: { executor: "constant-vus", vus: 50, duration: "2m" },
  },
  thresholds: { "http_req_duration{endpoint:sugg}": ["p(95)<200"] },
};

const QUERIES = ["qu","qua","quan","quant","crispr","hydro","solar","neural","carbon","mrna"];

export default function () {
  const q = QUERIES[Math.floor(Math.random()*QUERIES.length)];
  http.get(`${__ENV.BASE_URL}/api/v1/suggestions?q=${q}`, { tags: { endpoint: "sugg" } });
}
```

### 6.7 Szenario HEALTH-UNDER-LOAD

Sekundärer VU prüft während Baseline-Last, ob `/health` und `/metrics` < 100 ms bleiben:

```js
// zu radar_baseline.js hinzufügen:
scenarios: {
  baseline: { /* wie oben */ },
  health_probe: {
    executor: "constant-vus", vus: 1, duration: "5m",
    exec: "probeHealth",
  },
},
// ...
export function probeHealth() {
  const r = http.get(`${__ENV.BASE_URL}/health`, { tags: { endpoint: "health" } });
  check(r, { "health 200": (x) => x.status === 200, "health fast": (x) => x.timings.duration < 100 });
  sleep(1);
}
```

---

## 7. Ausführung

```bash
export BASE_URL=http://localhost:8000

# Baseline
k6 run --summary-export=docs/testing/ergebnisse/k6_baseline.json \
       tests/performance/scripts/radar_baseline.js

# Spike
k6 run --summary-export=docs/testing/ergebnisse/k6_spike.json \
       tests/performance/scripts/radar_spike.js

# Chaos (manuell kombiniert, s.o.)

# Soak (nur bei Bedarf – 30 min!)
k6 run --summary-export=docs/testing/ergebnisse/k6_soak.json \
       tests/performance/scripts/radar_soak.js

# Suggestions
k6 run --summary-export=docs/testing/ergebnisse/k6_sugg.json \
       tests/performance/scripts/suggestions.js

# Timeouts
k6 run tests/performance/scripts/uc_timeout_check.js
```

### HTML-Report (optional)

```bash
npm i -g k6-reporter
# Szenarien mit --summary-export=... produzieren JSON → k6-reporter generiert HTML
```

---

## 8. Ergebnis-Dokumentation

Schreibe `docs/testing/ergebnisse/agent2_k6_ergebnis.md`:

```markdown
# Ergebnis · Agent 2 · k6

**Lauf:** <ISO-Datum> · **Stack-Commit:** <SHA> · **k6:** <k6 version>

## Szenario-Zusammenfassung

| Szenario | Thresholds | Ergebnis | Dauer |
|---|---|---|---|
| Baseline 10 VU × 5m | p95<3s, fail<1% | ✅ | 5m |
| Spike 200 VU | 429 erzwungen, 5xx<5 | ✅ | 1m |
| Chaos UC1-Stop | 200-Rate > 95% im Fenster | ❌ | 3m |
| Soak 30m | p95<3.5s, RSS-Drift<25% | ⏭ | – |
| Suggestions 50 VU × 2m | p95<200ms | ✅ | 2m |
| Timeouts | UCs im Limit | ✅ | 2m |

## Latenz-Details (Baseline)

- http_req_duration p50 / p95 / p99: `<ms>` / `<ms>` / `<ms>`
- http_req_failed rate: `<%>`
- radar_fanout_ok rate: `<%>`

### Pro-UC-Latenz (aus `timings`)

| UC | p50 | p95 | p99 | Timeout-Budget |
|---|---|---|---|---|
| UC1 | … | … | … | 30 000 |
| UC2 | … | … | … | 60 000 |
| … | | | | |

## Chaos-Beobachtung

- Fenster: `t=30s..90s` (UC1 down)
- 200-Rate im Fenster: <%>
- Anteil Responses mit `warnings[] ⊇ {uc1}`: <%>
- Recovery nach `docker start`: <Sekunden bis 200 ohne warnings>

## Gefundene Bugs

### BUG-K6-001 · Severity: <…> · <Titel>
**Szenario:** …
**Metric:** <name=wert>
**Beobachtung:** …
**Hinweis für Fix:** …

## Offene Empfehlungen
- <Empfehlung>
```

---

## 9. Grenzen dieses Protokolls

- **Keine UI-Tests** → Agent 1 (Cypress).
- **Keine Input-Fuzzing-Edge-Cases** → Agent 3 (Schemathesis).
- **Keine Datenbank-Isolations-Tests** — pytest/integration deckt das ab.
- **Messen, nicht korrigieren:** Dieses Protokoll berichtet nur; Performance-Fixes sind Follow-up-Tickets.
