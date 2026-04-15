# Testprotokoll — Agent 3 · Schemathesis (Property-Based API-Fuzzing)

> **Adressat:** Claude-Code-Subagent, der diese Datei liest und eigenständig ausführt.
> **Technologie:** [Schemathesis](https://schemathesis.readthedocs.io/) (+ Hypothesis) — Property-Based-API-Fuzzing direkt aus OpenAPI-Schema.
> **Warum diese Technologie:** Weder `pytest` noch `pact-python` generieren automatisch tausende Edge-Case-Requests aus der API-Spezifikation. Schemathesis findet Klassen von Bugs, die manuelle Tests nie finden: Pydantic-Validation-Bypasses, 500er-Crashes bei unüblichen Typen, Schema-Drift zwischen Doku und Implementierung, Content-Type-Ignoranz etc.

---

## 1. Mission

Beweise mit automatisch generierten Requests, dass:

1. **keine** Eingabe einen **HTTP-500** auf `/api/v1/radar`, `/api/v1/suggestions`, `/health` oder `/metrics` erzeugt,
2. jede Response dem OpenAPI-deklarierten Schema entspricht (keine undokumentierten Felder),
3. die **Authorization** korrekt greift (kein Key → 401, falscher Key → 401, richtiger Key → 200) — oder im offenen Modus dokumentiert,
4. der **Rate-Limiter** im wiederholten Lauf **429** mit `Retry-After`-Header zurückgibt,
5. **Content-Type-Varianten** sauber abgelehnt werden (XML gegen JSON-Endpoint → 415, nicht 500),
6. Header-Injection, extrem große Payloads, Unicode-Grenzfälle die API nicht crashen,
7. **Security-Smoke** für SQLi-Payloads (`tech`-Feld → `entity_schema.unified_actors`-Lookup) und Path-Traversal (Export-Pfade) harmlos bleibt.

---

## 2. Prerequisites

```bash
cd deploy && make up && cd ..
sleep 30
curl -fsS http://localhost:8000/openapi.json | jq '.info.title' # muss "TI-Radar Orchestrator" o.ä. liefern
```

Wenn `/openapi.json` fehlt oder leer ist → **STOP**. Im Ergebnis-File dokumentieren: „OpenAPI-Schema nicht erreichbar, Fuzzing nicht möglich — Orchestrator-Startup prüfen."

### API-Key-Situation

```bash
grep TI_RADAR_API_KEY deploy/.env 2>/dev/null && echo "AUTH AKTIV" || echo "AUTH OFFEN"
```

Merke dir den Modus — dein Protokoll schreibt unterschiedliche Assertions je nach Modus.

---

## 3. Setup

```bash
python3.12 -m venv .venv_schemathesis
source .venv_schemathesis/bin/activate
pip install --upgrade pip
pip install "schemathesis[all]==3.*" hypothesis==6.*

mkdir -p tests/fuzzing
```

### Version-Check

```bash
schemathesis --version   # >= 3.30 erwartet
```

### Schema herunterladen (Snapshot für Reproduzierbarkeit)

```bash
curl -fsS http://localhost:8000/openapi.json \
  | python -m json.tool > tests/fuzzing/openapi_snapshot.json
```

---

## 4. Technische Abdeckung

| Schicht | Abdeckung | Mechanismus |
|---|---|---|
| API-Gateway (FastAPI) | ✅ voll | alle Endpunkte gefuzzt |
| Request-Validation (Pydantic) | ✅ | negative payloads |
| Auth-Middleware | ✅ | Key-Varianten |
| Rate-Limit-Middleware | ✅ | Repeat-Run |
| Response-Serialization | ✅ | `response_schema_conformance` |
| Business-Logik (UC-Services) | ◻ indirekt | via Fan-Out-Latenz-Beobachtung |
| DB (SQLi-Smoke) | ◻ | Security-Checks |

---

## 5. Inhaltliche Abdeckung

Jeder UC wird indirekt berührt, weil jede `POST /api/v1/radar`-Anfrage alle UCs fan-outet. Dedizierte UC-spezifische Fuzz-Strategien:

| UC | Beobachtung | Strategie |
|---|---|---|
| UC1–UC12, UC-C | Fan-Out-Stabilität bei beliebigem `tech` | Hypothesis erzeugt Strings (Unicode, leer, sehr lang, Emoji, Quotes) |
| Filter `countries` | ISO-2-Validierung | Nicht-ISO-Codes, Arrays mit Duplikaten |
| Filter `cpc_codes` | Format-Validierung | Müll-Strings, echte CPCs, Mix |
| Filter `timerange` | end < start, out-of-range | Hypothesis-Integer-Strategien |
| Filter `top_n` | Grenzwerte (0, 1, 1 000 000, -1) | Hypothesis-Integer |

---

## 6. Test-Suite

### 6.1 T1 — Full-Sweep All-Checks

```bash
schemathesis run http://localhost:8000/openapi.json \
  --checks all \
  --hypothesis-max-examples=200 \
  --hypothesis-deadline=30000 \
  --workers=4 \
  --show-errors-tracebacks \
  --junit-xml=docs/testing/ergebnisse/schemathesis_full.xml \
  --cassette-path=docs/testing/ergebnisse/schemathesis_full.yaml \
  --report
```

**Aktivierte Checks:**
- `not_a_server_error` — keine 5xx
- `status_code_conformance` — Status-Codes laut Spec
- `content_type_conformance` — Content-Type laut Spec
- `response_schema_conformance` — Response-Body laut Schema
- `response_headers_conformance` — Header laut Spec

**Akzeptanz:** 0 Failures. Jedes Failure landet im Junit-XML + Ergebnis-MD.

### 6.2 T2 — Stateful Fuzzing (Links / Redirects)

```bash
schemathesis run http://localhost:8000/openapi.json \
  --stateful=links \
  --hypothesis-max-examples=100 \
  --checks all
```

### 6.3 T3 — Dediziert POST /api/v1/radar (höhere Intensität)

`tests/fuzzing/radar_config.py`:

```python
import schemathesis
from hypothesis import strategies as st

schema = schemathesis.from_uri("http://localhost:8000/openapi.json")

@schema.parametrize(endpoint="/api/v1/radar")
@schemathesis.hooks.register("before_generate_case")
def tweak(context, strategy):
    return strategy

# In CI/CLI:
#   schemathesis run --include-endpoint='/api/v1/radar' \
#                    --hypothesis-max-examples=500 \
#                    --hypothesis-derandomize \
#                    http://localhost:8000/openapi.json
```

```bash
schemathesis run http://localhost:8000/openapi.json \
  --include-endpoint='/api/v1/radar' \
  --hypothesis-max-examples=500 \
  --checks all \
  --junit-xml=docs/testing/ergebnisse/schemathesis_radar.xml
```

### 6.4 T4 — Auth-Matrix

Lege drei Läufe an (Bash-Skript `tests/fuzzing/auth_matrix.sh`):

```bash
#!/usr/bin/env bash
set -euo pipefail

KEY_REAL="${TI_RADAR_API_KEY:-}"
KEY_FAKE="deadbeef"

run() {
  local label="$1"; shift
  echo "=== $label ==="
  schemathesis run http://localhost:8000/openapi.json \
    --include-endpoint='/api/v1/radar' \
    --hypothesis-max-examples=20 \
    --checks not_a_server_error,status_code_conformance \
    "$@" \
    --junit-xml="docs/testing/ergebnisse/schemathesis_auth_${label}.xml" \
    || true
}

# (a) ohne Key — erwartet 401 wenn Auth aktiv, sonst 200
run "nokey"

# (b) falscher Key — erwartet immer 401 wenn Auth aktiv
run "fakekey" --header "X-API-Key: ${KEY_FAKE}"

# (c) echter Key — erwartet 200 / 422 / 429 (aber nie 401)
if [ -n "$KEY_REAL" ]; then
  run "realkey" --header "X-API-Key: ${KEY_REAL}"
fi
```

**Akzeptanz:**

| Modus | Kein Key | Falscher Key | Echter Key |
|---|---|---|---|
| `TI_RADAR_API_KEY` gesetzt | alle 401 | alle 401 | keine 401 |
| `TI_RADAR_API_KEY` leer/ungesetzt | 200 möglich | 200 möglich | n/a |

### 6.5 T5 — Rate-Limit-Regression

```bash
# Schnell-Loop der Suggestions ohne Pause → muss irgendwann 429 liefern
for i in $(seq 1 150); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    "http://localhost:8000/api/v1/suggestions?q=q${i}"
done | sort | uniq -c > docs/testing/ergebnisse/ratelimit_distribution.txt
grep 429 docs/testing/ergebnisse/ratelimit_distribution.txt \
  || echo "FAIL: Kein 429 erhalten" >> docs/testing/ergebnisse/ratelimit_distribution.txt
```

**Zusätzlich:** Beim ersten 429 prüfen, ob `Retry-After`-Header gesetzt ist:

```bash
curl -sI "http://localhost:8000/api/v1/radar" -X POST \
  -H "Content-Type: application/json" -d '{"tech":"x"}' \
  | grep -i "retry-after" || echo "WARN: Retry-After fehlt"
```

### 6.6 T6 — Content-Type-Sabotage

```bash
# XML gegen JSON-Endpoint → muss 415, nicht 500
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Content-Type: application/xml" \
  -d '<tech>quantum</tech>' \
  http://localhost:8000/api/v1/radar
# Erwartet: 415 oder 422; 500 = FAIL

# Riesiger Body (10 MB)
python3 -c "print('{\"tech\":\"' + 'a'*10_000_000 + '\"}')" \
  | curl -s -o /dev/null -w "%{http_code}\n" \
      -H "Content-Type: application/json" \
      --data-binary @- \
      http://localhost:8000/api/v1/radar
# Erwartet: 413/422/400 — niemals 500
```

### 6.7 T7 — Security-Smoke (SQLi + Path-Traversal)

**SQLi über `tech`-Feld:**

```bash
for payload in \
  "' OR 1=1 --" \
  "\"; DROP TABLE patents; --" \
  "' UNION SELECT NULL,NULL --" \
  "1' AND (SELECT COUNT(*) FROM pg_tables) > 0 --"
do
  code=$(curl -s -o /tmp/body -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -d "{\"tech\":\"${payload}\"}" \
    http://localhost:8000/api/v1/radar)
  echo "[$code] $payload"
  # FAIL-Kriterium: 500 oder Response leakt SQL-Error-Text
  grep -iE "syntax error|pg_|psql|asyncpg" /tmp/body && echo "⚠ Leak: $payload"
done | tee docs/testing/ergebnisse/sqli_smoke.log
```

**Path-Traversal im Export-Endpoint** (`frontend/src/app/api/export/`):

```bash
for path in "../../../etc/passwd" "..\\..\\windows\\win.ini" "%2e%2e%2fetc%2fpasswd"; do
  code=$(curl -s -o /tmp/body -w "%{http_code}" \
    "http://localhost:3000/api/export?path=${path}&format=csv")
  echo "[$code] ${path}"
done | tee docs/testing/ergebnisse/pathtraversal_smoke.log
# FAIL-Kriterium: 200 mit Passwort-/Config-Inhalt. OK: 400/403/404.
```

> **Hinweis:** Falls der Export-Endpoint den `path`-Parameter nicht akzeptiert (wahrscheinlich), dokumentiere dies als „nicht anwendbar — Export empfängt keine Pfad-Parameter".

### 6.8 T8 — Schema-Drift-Check

Am Ende des Laufs:

```bash
curl -s http://localhost:8000/openapi.json > /tmp/openapi_now.json
diff <(jq -S . tests/fuzzing/openapi_snapshot.json) \
     <(jq -S . /tmp/openapi_now.json) \
  > docs/testing/ergebnisse/openapi_diff.txt || true
```

**Akzeptanz:** Diff dokumentiert (Info), keine harte Assertion — nur Bewusstsein schaffen.

---

## 7. Ausführung (End-to-End)

```bash
# Aktivieren
source .venv_schemathesis/bin/activate

# 1) Snapshot
curl -fsS http://localhost:8000/openapi.json | python -m json.tool > tests/fuzzing/openapi_snapshot.json

# 2) T1 Full-Sweep
schemathesis run http://localhost:8000/openapi.json \
  --checks all --hypothesis-max-examples=200 --workers=4 \
  --junit-xml=docs/testing/ergebnisse/schemathesis_full.xml

# 3) T3 intensiv /radar
schemathesis run http://localhost:8000/openapi.json \
  --include-endpoint='/api/v1/radar' --hypothesis-max-examples=500 --checks all \
  --junit-xml=docs/testing/ergebnisse/schemathesis_radar.xml

# 4) T4 Auth
bash tests/fuzzing/auth_matrix.sh

# 5) T5 Rate-Limit (siehe oben)
# 6) T6 Content-Type (siehe oben)
# 7) T7 Security-Smoke (siehe oben)
# 8) T8 Schema-Drift
```

### Timeout-Budget

Gesamtlauf < 45 min. Wenn `--hypothesis-max-examples=500` zu lange dauert, auf 200 reduzieren.

---

## 8. Ergebnis-Dokumentation

Schreibe `docs/testing/ergebnisse/agent3_schemathesis_ergebnis.md`:

```markdown
# Ergebnis · Agent 3 · Schemathesis

**Lauf:** <ISO-Datum> · **Stack-Commit:** <SHA> · **Schemathesis:** <version>
**Auth-Modus:** <OFFEN | GESCHÜTZT mit TI_RADAR_API_KEY>

## Zusammenfassung

| Block | Tests erzeugt | Failures | Status |
|---|---|---|---|
| T1 Full-Sweep All-Checks | ~<n> | <n> | ✅/❌ |
| T2 Stateful | ~<n> | <n> | ✅/❌ |
| T3 Radar intensiv (500 Beispiele) | ~500 | <n> | ✅/❌ |
| T4 Auth-Matrix (nokey/fake/real) | <n> | <n> | ✅/❌ |
| T5 Rate-Limit | 150 sequentielle | 429 gesehen: <y/n> | ✅/❌ |
| T6 Content-Type | 2 Fälle | 5xx: <n> | ✅/❌ |
| T7 SQLi-Smoke | 4 Payloads | Leaks: <n> | ✅/❌ |
| T7 Path-Traversal | 3 Payloads | 200 mit Secret: <n> | ✅/❌ |
| T8 Schema-Drift | 1 | Diff: <zeilen> | ℹ |

## Gefundene Bugs

### BUG-SC-001 · Severity: Critical · 500 bei Unicode-Emoji in `tech`
**Endpoint:** `POST /api/v1/radar`
**Payload:** `{"tech": "🚀🚀🚀"}`
**Response:** 500 Internal Server Error
**Stack (aus Logs):** …
**Reproduzieren:** `curl -H "Content-Type: application/json" -d '{"tech":"🚀"}' http://localhost:8000/api/v1/radar`
**Hinweis:** Encoding in `entity_schema.unified_actors`-Lookup prüfen (Postgres `LIKE` vs. bytea).

### BUG-SC-002 · …

## Coverage

- OpenAPI-Endpunkte gesamt: <n>
- davon durch Schemathesis besucht: <n> (<%>)
- Response-Schema-Konformität: <%>

## Offene Empfehlungen
- <z.B.: Retry-After-Header bei 429 einführen>
- <z.B.: Pydantic-Limit für `tech`-Länge auf 200 chars>
```

---

## 9. Grenzen dieses Protokolls

- **Keine UI-Prüfung** → Agent 1 (Cypress).
- **Keine Lasttests** → Agent 2 (k6).
- **Security-Smoke** ist oberflächlich — tiefe Pen-Tests (OWASP ZAP, Burp) sind Follow-up-Scope.
- **Schemathesis ist so gut wie das OpenAPI-Schema** — Endpunkte ohne Schema-Einträge werden nicht gefunden.
