# TI-Radar v3.0 — Testprotokolle (Agenten-Suite)

> **Ziel:** 100 % technische **und** inhaltliche Testabdeckung durch 4 komplementäre Testläufe mit Technologien, die noch nicht im bestehenden Test-Stack (pytest, pact-python, ruff, mypy, Next-ESLint, GitHub Actions) verwendet werden.

---

## 1. Beteiligte

| Rolle | Ausführung | Technologie | Warum diese Technologie |
|---|---|---|---|
| **Agent 1 / „Person A"** | Claude-Code-Subagent | **Cypress 13** (E2E, TypeScript) | Deckt Browser-basierte User-Journeys ab, die pytest nicht sieht |
| **Agent 2 / „Person B"** | Claude-Code-Subagent | **k6** (Load, JavaScript) | Lasttests + Fan-Out-Chaos — kein Performance-Check bisher |
| **Agent 3 / „Person C"** | Claude-Code-Subagent | **Schemathesis** (Property-Based API-Fuzzing, Python) | Automatisiert erschöpfendes API-Fuzzing aus OpenAPI — weder pact noch pytest machen das |
| **Claude (ich)** | Direkte MCP-Sitzung | **Playwright MCP** (Browser-Automation) | End-User-Sicht: inhaltliche Plausibilität & visuelle Verifikation |

---

## 2. Protokolle

1. [`test_protokoll_agent1_cypress.md`](./test_protokoll_agent1_cypress.md) — Agent 1 · Cypress · Frontend-E2E
2. [`test_protokoll_agent2_k6.md`](./test_protokoll_agent2_k6.md) — Agent 2 · k6 · Performance/Chaos
3. [`test_protokoll_agent3_schemathesis.md`](./test_protokoll_agent3_schemathesis.md) — Agent 3 · Schemathesis · API-Fuzzing
4. [`test_protokoll_claude_playwright.md`](./test_protokoll_claude_playwright.md) — Claude · Playwright MCP · visuelle Plausibilität

Jedes Protokoll ist **self-contained** und so geschrieben, dass ein frisch gespawnter Claude-Code-Subagent ohne Rückfrage arbeiten kann.

---

## 3. Abdeckungs-Matrix (Feature × Agent)

Legende: ✅ = primär getestet · ◻ = indirekt berührt · – = nicht im Scope

### 3.1 Use Cases (inhaltliche Dimension)

| # | Use Case | Service | Cypress | k6 | Schemathesis | Playwright MCP |
|---|---|---|:-:|:-:|:-:|:-:|
| UC1 | Technologie-Landschaft (CAGR, Trend) | `landscape-svc` | ✅ | ✅ | ✅ | ✅ |
| UC2 | Reifegrad-Analyse (S-Kurve) | `maturity-svc` | ✅ | ✅ | ✅ | ✅ |
| UC3 | Wettbewerbslandschaft (HHI, Netzwerk) | `competitive-svc` | ✅ | ✅ | ✅ | ✅ |
| UC4 | EU-Förderanalyse (Treemap) | `funding-svc` | ✅ | ◻ | ✅ | ✅ |
| UC5 | CPC-Technologiekonvergenz (Chord) | `cpc-flow-svc` | ✅ | ✅ | ✅ | ✅ |
| UC6 | Geographische Verteilung | `geographic-svc` | ✅ | ◻ | ✅ | ✅ |
| UC7 | Forschungswirkung (h-Index) | `research-impact-svc` | ✅ | ◻ | ✅ | ✅ |
| UC8 | Zeitliche Trends (New Entrants) | `temporal-svc` | ✅ | ◻ | ✅ | ✅ |
| UC9 | Themencluster (NLP) | `tech-cluster-svc` | ✅ | ✅ | ✅ | ✅ |
| UC10 | EuroSciVoc-Taxonomie | `euroscivoc-svc` | ✅ | ◻ | ✅ | ✅ |
| UC11 | Akteurstypen (HES/PRC/PUB/OTH) | `actor-type-svc` | ✅ | ◻ | ✅ | ✅ |
| UC12 | Patenterteilung (Grant-Rate) | `patent-grant-svc` | ✅ | ◻ | ✅ | ✅ |
| UC-C | Publikationen (Open Access) | `publication-svc` | ✅ | ◻ | ✅ | ✅ |

### 3.2 Cross-Cutting Features (technische Dimension)

| Feature | Quelle | Cypress | k6 | Schemathesis | Playwright MCP |
|---|---|:-:|:-:|:-:|:-:|
| POST `/api/v1/radar` (Fan-Out) | `router_radar.py` | ◻ | ✅ | ✅ | ◻ |
| GET `/api/v1/suggestions` (Autocomplete) | `router_suggestions.py` | ✅ | ✅ | ✅ | ✅ |
| GET `/health` shallow/deep | `router_health.py` | – | ✅ | ✅ | – |
| GET `/metrics` (Prometheus) | `router_health.py` | – | ✅ | ✅ | – |
| X-API-Key Auth | `auth.py` | ◻ | ✅ | ✅ | – |
| Rate-Limit 100 req/min | `middleware.py` | ✅ (UI-Toast) | ✅ | ✅ | – |
| Timeout-Handling (UC2/3/5/9 = 60 s, sonst 30 s) | `grpc_clients.py` | – | ✅ | – | – |
| Graceful Degradation (UC-Ausfall → `warnings[]`) | `router_radar.py` | ✅ | ✅ | – | ◻ |
| Export CSV / XLSX / JSON / PDF | `frontend/src/app/api/export/` | ✅ | – | ◻ | ✅ |
| Compare-Seite (2 Techs parallel) | `frontend/src/app/compare/` | ✅ | – | – | ✅ |
| Filter (Zeitraum / Länder / CPC) | Panels + Orchestrator | ✅ | ◻ | ✅ | ✅ |
| Error-Scenarios (4xx / 5xx) | global | ✅ | ◻ | ✅ | ◻ |
| SQL-Injection-Smoke | `entity_schema` Lookups | – | – | ✅ | – |
| Responsiveness (3 Viewports) | Layout | ✅ | – | – | ◻ |

### 3.3 Schichten-Abdeckung (aus `docs/ARCHITEKTUR.md`)

| Schicht | Cypress | k6 | Schemathesis | Playwright MCP |
|---|:-:|:-:|:-:|:-:|
| Präsentation (Next.js, React, TSX) | ✅ | – | – | ✅ |
| API-Gateway (FastAPI Orchestrator) | ◻ | ✅ | ✅ | ◻ |
| Business-Logik (UC-Services gRPC) | ◻ | ✅ | ◻ | ◻ |
| Data Access (asyncpg, SQL) | – | ◻ | ◻ | – |
| Datenbank (PostgreSQL 17) | – | – | – | – |
| Externe Integrations (EPO/CORDIS/…) | – | ◻ | – | – |
| Infrastruktur (Docker, gRPC) | – | ✅ (Chaos) | – | – |

> **Anmerkung zur DB-/Externe-Integrations-Schicht:** Bereits durch bestehende `tests/integration/` (pytest + testcontainers) abgedeckt — kein Neu-Scope für diese Suite.

---

## 4. Gesamt-Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. `make up` → Stack hochfahren (Dauer: ~1–2 min)           │
│    docker compose ps → alle Container `Up (healthy)`         │
├─────────────────────────────────────────────────────────────┤
│ 2. Parallel (in 3 separaten Claude-Code-Sessions):          │
│    - Subagent A liest test_protokoll_agent1_cypress.md      │
│    - Subagent B liest test_protokoll_agent2_k6.md           │
│    - Subagent C liest test_protokoll_agent3_schemathesis.md │
│    Jeder Agent schreibt sein Ergebnis in ergebnisse/*.md    │
├─────────────────────────────────────────────────────────────┤
│ 3. Claude (ich) führt eigenen Playwright-MCP-Lauf durch     │
│    → ergebnisse/claude_playwright_bericht.md                │
├─────────────────────────────────────────────────────────────┤
│ 4. Gesamt-Review: ergebnisse/ zusammenfassen, offene        │
│    Bugs in GitHub-Issues überführen.                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Voraussetzungen (gelten für alle Agenten)

- macOS / Linux mit Docker Desktop ≥ 4.30
- `make` (GNU Make)
- Python 3.12+ (bereits Projekt-Standard)
- Node.js 20+ (bereits Projekt-Standard)
- Freie Ports: `3000` (Frontend), `8000` (Orchestrator), `5432` (DB)
- Arbeitsverzeichnis: Repo-Root (`mvp_v3.0_new/`)

### Stack-Start

```bash
cd deploy && make up
# oder
docker compose -f deploy/docker-compose.yml up -d
```

### Health-Check (muss vor jedem Test grün sein)

```bash
curl -fsS http://localhost:8000/health | jq '.status'   # → "ok"
curl -fsS http://localhost:3000 | head -1                # → <!DOCTYPE html>
```

### Demo-Technologien (vorhanden in `database/mock_data/`)

- `quantum computing` (hoher Trefferraum, geeignet für alle UCs)
- `CRISPR` (Life-Science, anderes CPC-Spektrum)
- `hydrogen fuel cell` (Energie, EU-lastige Förderung)
- `xyz_unknown_tech_9999` (Empty-State-Test)

---

## 6. Ergebnis-Dokumentation

Jeder Agent schreibt seinen Abschlussbericht nach `docs/testing/ergebnisse/` mit:

- Pass/Fail-Tabelle pro Testfall-ID
- Reproduzierbare Bug-Beschreibungen (Titel, Severity, Steps-to-Reproduce, Expected vs. Actual, Screenshot/Log)
- Coverage-Wert (% abgearbeiteter Testfälle)
- Meta: Dauer, verwendete Tool-Version, Stack-Commit-SHA

**Bug-Severity-Skala** (einheitlich über alle 4 Berichte):

| Severity | Kriterium |
|---|---|
| **Critical** | UC liefert falsche KPIs / API stürzt ab / Datenverlust |
| **Major** | Panel zeigt Fehlermeldung / Fan-Out-Graceful-Degradation bricht |
| **Minor** | UI-Darstellungsfehler / Off-by-one in Ranking |
| **Trivial** | Kosmetik, Typo, Tooltip-Text |
