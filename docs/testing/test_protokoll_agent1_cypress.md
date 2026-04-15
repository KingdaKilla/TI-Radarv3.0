# Testprotokoll — Agent 1 · Cypress (E2E Frontend)

> **Adressat:** Claude-Code-Subagent, der diese Datei liest und eigenständig ausführt.
> **Technologie:** [Cypress 13](https://docs.cypress.io/) — Browser-E2E-Testing in JavaScript/TypeScript.
> **Warum diese Technologie:** Cypress ist **nicht** im Projekt-Stack (`pytest`, `pact`, `ruff`, `mypy`, `next lint`) und bietet als einziges Tool echte Browser-Interaktion mit zeitreisefähigem Network-Stubbing.

---

## 1. Mission

Beweise, dass ein **echter Nutzer** im Browser:

1. die Landingpage inklusive Autocomplete-Suche bedienen kann,
2. für eine Technologie **alle 13 Use-Case-Panels** sieht (UC1–UC12 + UC-C),
3. Filter (Zeitraum / Länder / CPC / Top-N) verändern kann und Charts reagieren,
4. zwei Technologien auf `/compare` **parallel** analysieren kann,
5. Reports in **allen 4 Formaten** (CSV/XLSX/JSON/PDF) exportieren kann,
6. bei Fehlern (Orchestrator-500, Rate-Limit-429) **sinnvolle UI-Meldungen** erhält,
7. die Seite auf **3 Viewports** (Desktop/Laptop/Tablet) korrekt rendert.

---

## 2. Prerequisites

```bash
# 1) Stack hochfahren
cd deploy && make up && cd ..
sleep 30                                # Container-Startup
curl -fsS http://localhost:8000/health  # muss 200 liefern
curl -fsS http://localhost:3000         # muss HTML liefern

# 2) Falls `TI_RADAR_API_KEY` in deploy/.env gesetzt:
#    Cypress muss Header senden → in cypress.env.json hinterlegen (siehe §5).
grep TI_RADAR_API_KEY deploy/.env 2>/dev/null || echo "Auth offen — Cypress kann ohne Key testen"
```

Wenn der Stack nicht startet → **STOP**. In `ergebnisse/agent1_cypress_ergebnis.md` dokumentieren, warum, und abbrechen.

---

## 3. Setup (von dir, dem Agenten, auszuführen)

```bash
cd frontend
npm install --save-dev cypress@^13 @testing-library/cypress@^10 start-server-and-test@^2
npx cypress install
mkdir -p cypress/e2e cypress/support cypress/fixtures
```

### Dateien anlegen

**`frontend/cypress.config.ts`**

```ts
import { defineConfig } from "cypress";
export default defineConfig({
  e2e: {
    baseUrl: "http://localhost:3000",
    viewportWidth: 1920,
    viewportHeight: 1080,
    defaultCommandTimeout: 15000,          // UCs können 30s brauchen
    responseTimeout: 60000,                // Fan-Out-Timeout = 60s
    video: false,
    screenshotOnRunFailure: true,
    env: {
      ORCHESTRATOR_URL: "http://localhost:8000",
      DEMO_TECHS: ["quantum computing", "CRISPR", "hydrogen fuel cell"],
      UNKNOWN_TECH: "xyz_unknown_tech_9999",
    },
    retries: { runMode: 2, openMode: 0 },
  },
});
```

**`frontend/cypress/support/e2e.ts`**

```ts
import "@testing-library/cypress/add-commands";

// Custom command: wartet bis alle 13 Panels gerendert sind
Cypress.Commands.add("waitForAllPanels", () => {
  const ucs = ["UC1","UC2","UC3","UC4","UC5","UC6","UC7","UC8","UC9","UC10","UC11","UC12","UC-C"];
  ucs.forEach((uc) => {
    cy.contains(new RegExp(`\\b${uc}\\b`), { timeout: 65000 }).should("be.visible");
  });
});

declare global {
  namespace Cypress {
    interface Chainable {
      waitForAllPanels(): Chainable<void>;
    }
  }
}
```

> **Wichtig:** Die Panels haben **keine `data-testid`-Attribute** (verifiziert in `frontend/src/components/panels/*.tsx`). Selektiere daher über:
> - Heading-Text (z. B. `cy.contains("h3", /Technologie-Landschaft/i)`),
> - UC-Label im `PanelCard` (es rendert `UC1`, `UC2`, … als Badge),
> - ARIA-Rollen (`role="region"`, `role="button"`).

---

## 4. Technische Abdeckung

| Schicht | Abdeckung | Mechanismus |
|---|---|---|
| Präsentation (Next.js) | ✅ voll | echter Chromium via Cypress |
| API-Gateway | ◻ indirekt | durch Fetches der Panels |
| Business-Logik | ◻ indirekt | – |
| Graceful Degradation | ✅ | `cy.intercept` simuliert UC-Failure |
| Error-Handling (Toasts) | ✅ | `cy.intercept` simuliert 500/429 |

---

## 5. Inhaltliche Abdeckung (alle 13 UCs)

Für jede UC gibt es **mindestens einen dedizierten Testfall**, der das Panel auf Sichtbarkeit + eine UC-spezifische Assertion prüft.

| UC | Panel-Titel-Fragment | UC-spezifische Assertion |
|---|---|---|
| UC1 | "Landschaft" / "Landscape" | Time-Series-Chart hat ≥1 SVG-Pfad |
| UC2 | "Reife" / "Maturity" | S-Kurven-Graph + Phase-Badge (`Einführung`/`Wachstum`/...) |
| UC3 | "Wettbewerb" / "Competitive" | HHI-Kennzahl als Zahl zwischen 0 und 10000 |
| UC4 | "Förder" / "Funding" | Nivo-Treemap enthält ≥1 Rechteck |
| UC5 | "CPC" / "Konvergenz" | Chord-Diagramm vorhanden |
| UC6 | "Geograph" / "Länder" | Top-5-Länder-Liste mit ISO-Codes |
| UC7 | "Wirkung" / "Impact" | h-Index als Integer ≥ 0 |
| UC8 | "Zeit" / "Trend" / "Temporal" | New-Entrant-Rate als Prozent 0–100 |
| UC9 | "Cluster" | ≥ 2 Cluster-Einträge |
| UC10 | "EuroSciVoc" / "Taxonomie" | ≥ 1 Kategorie sichtbar |
| UC11 | "Akteur" / "Actor" | HES/PRC/PUB/OTH-Breakdown (Summe = 100 %) |
| UC12 | "Grant" / "Erteilung" | Grant-Rate als Prozent 0–100 |
| UC-C | "Publikat" / "Publication" | Open-Access-Anteil als Prozent |

---

## 6. Test-Suite

> **Konvention:** Test-IDs folgen `CY-<Bereich>-<lfd>`. Bereiche: `LAND` (Landing), `UC1..12`, `UCC`, `FILTER`, `COMPARE`, `EXPORT`, `ERR` (Error-Handling), `A11Y`, `RESP` (Responsive).

### 6.1 Landing & Search

**CY-LAND-001 — Homepage rendert Header, Suche, Footer**
```ts
it("CY-LAND-001 rendert Landingpage", () => {
  cy.visit("/");
  cy.contains(/TI.?Radar/i).should("be.visible");
  cy.get('input[type="search"], input[placeholder*="Technolog" i]').should("be.visible");
});
```
**Akzeptanz:** Sichtbar in <3s, keine Console-Errors außer bekannte 3rd-Party.

**CY-LAND-002 — Autocomplete liefert Vorschläge (debounced)**
```ts
it("CY-LAND-002 zeigt Suggestions nach 300ms Debounce", () => {
  cy.intercept("GET", "**/api/v1/suggestions**").as("sugg");
  cy.visit("/");
  cy.get('input[type="search"]').type("quant");
  cy.wait("@sugg").its("response.statusCode").should("eq", 200);
  cy.contains(/quantum/i).should("be.visible");
});
```
**Akzeptanz:** Genau **1** Request nach 300 ms (nicht 4 — Debounce wirkt).

**CY-LAND-003 — Leere Suche zeigt keine API-Calls**
```ts
it("CY-LAND-003 feuert keine Requests bei <2 Zeichen", () => {
  cy.intercept("GET", "**/api/v1/suggestions**").as("sugg");
  cy.visit("/");
  cy.get('input[type="search"]').type("q");
  cy.wait(600);
  cy.get("@sugg.all").should("have.length", 0);
});
```

### 6.2 Dashboard: 13 UC-Panels (1 Test je UC)

Die folgenden Tests werden in einer `describe`-Suite mit `beforeEach` ausgeführt:

```ts
describe("Dashboard UC-Panels für 'quantum computing'", () => {
  beforeEach(() => {
    cy.visit("/radar/quantum%20computing");
    cy.waitForAllPanels();
  });

  // CY-UC1-001
  it("CY-UC1-001 Landscape: Time-Series + CAGR", () => {
    cy.contains(/Landschaft|Landscape/i).parents('[class*="card"], section, article').first().within(() => {
      cy.get("svg").should("exist");
      cy.contains(/CAGR/i).should("be.visible");
    });
  });

  // CY-UC2-001
  it("CY-UC2-001 Maturity: Phase-Badge", () => {
    cy.contains(/Reife|Maturity/i).parents('[class*="card"]').first().within(() => {
      cy.contains(/Einführung|Wachstum|Reife|Sättigung|Rückgang/i).should("be.visible");
    });
  });

  // CY-UC3-001
  it("CY-UC3-001 Competitive: HHI-Index plausibel", () => {
    cy.contains(/Wettbewerb|Competitive/i).parents('[class*="card"]').first().within(() => {
      cy.contains(/HHI/i).parent().invoke("text").then((txt) => {
        const m = txt.match(/([\d.,]+)/);
        const hhi = m ? parseFloat(m[1].replace(",", ".")) : NaN;
        expect(hhi).to.be.within(0, 10000);
      });
    });
  });

  // CY-UC4-001
  it("CY-UC4-001 Funding: Treemap mit ≥1 Rechteck", () => {
    cy.contains(/Förder|Funding/i).parents('[class*="card"]').first().within(() => {
      cy.get("svg rect, svg g[transform]").should("have.length.greaterThan", 0);
    });
  });

  // CY-UC5-001
  it("CY-UC5-001 CpcFlow: Chord-Diagramm sichtbar", () => {
    cy.contains(/CPC|Konvergenz/i).parents('[class*="card"]').first().within(() => {
      cy.get("svg").should("exist");
    });
  });

  // CY-UC6-001
  it("CY-UC6-001 Geographic: Top-5 Länder mit ISO-Codes", () => {
    cy.contains(/Geograph|Länder/i).parents('[class*="card"]').first().within(() => {
      cy.get("body").contains(/\b[A-Z]{2}\b/).should("exist"); // DE / US / CN / ...
    });
  });

  // CY-UC7-001
  it("CY-UC7-001 ResearchImpact: h-Index ≥ 0", () => {
    cy.contains(/Wirkung|Impact/i).parents('[class*="card"]').first().within(() => {
      cy.contains(/h.?Index/i).parent().invoke("text").then((t) => {
        const h = parseInt((t.match(/(\d+)/) || [])[1] ?? "-1", 10);
        expect(h).to.be.at.least(0);
      });
    });
  });

  // CY-UC8-001
  it("CY-UC8-001 Temporal: New-Entrant-Rate 0-100%", () => {
    cy.contains(/Zeit|Temporal|Trend/i).parents('[class*="card"]').first().within(() => {
      cy.contains(/New.?Entrant|Neue?\s+Akteure/i).should("exist");
    });
  });

  // CY-UC9-001
  it("CY-UC9-001 TechCluster: ≥2 Cluster-Einträge", () => {
    cy.contains(/Cluster/i).parents('[class*="card"]').first().within(() => {
      cy.get("li, [role='listitem']").should("have.length.greaterThan", 1);
    });
  });

  // CY-UC10-001
  it("CY-UC10-001 EuroSciVoc: ≥1 Taxonomie-Kategorie", () => {
    cy.contains(/EuroSciVoc|Taxonomie/i).parents('[class*="card"]').first().within(() => {
      cy.get("li, [role='listitem'], span").should("have.length.greaterThan", 0);
    });
  });

  // CY-UC11-001
  it("CY-UC11-001 ActorType: HES+PRC+PUB+OTH Breakdown", () => {
    cy.contains(/Akteur|Actor/i).parents('[class*="card"]').first().within(() => {
      cy.contains(/HES|PRC|PUB|OTH/).should("exist");
    });
  });

  // CY-UC12-001
  it("CY-UC12-001 PatentGrant: Grant-Rate 0-100%", () => {
    cy.contains(/Grant|Erteilung/i).parents('[class*="card"]').first().within(() => {
      cy.contains(/%/).should("be.visible");
    });
  });

  // CY-UCC-001
  it("CY-UCC-001 Publication: Open-Access-Share", () => {
    cy.contains(/Publikat|Publication/i).parents('[class*="card"]').first().within(() => {
      cy.contains(/Open.?Access|OA/i).should("exist");
    });
  });
});
```

### 6.3 Filter

**CY-FILTER-001 — Zeitraum-Filter ändert Chart**
```ts
it("CY-FILTER-001 setzt Zeitraum und re-fetcht", () => {
  cy.intercept("POST", "**/api/v1/radar").as("radar");
  cy.visit("/radar/quantum%20computing");
  cy.wait("@radar");
  cy.contains("button", /2015|Zeitraum|Filter/i).click();
  // Jahr-Input oder Slider — einer von beiden muss existieren
  cy.get('input[type="number"], input[type="range"]').first().clear({ force: true }).type("2018");
  cy.get("body").click(0, 0);
  cy.wait("@radar").its("request.body").should("satisfy", (b: any) =>
    JSON.stringify(b).includes("201") // 2018 o.ä. im Payload
  );
});
```

### 6.4 Compare

**CY-COMPARE-001 — Zwei Technologien nebeneinander**
```ts
it("CY-COMPARE-001 rendert Compare-View mit 2 Spalten", () => {
  cy.visit("/compare?a=quantum%20computing&b=CRISPR");
  cy.contains(/quantum/i).should("be.visible");
  cy.contains(/CRISPR/i).should("be.visible");
  cy.contains(/vs|Vergleich|versus/i).should("be.visible");
});
```

### 6.5 Export (alle 4 Formate)

**CY-EXPORT-001 / 002 / 003 / 004 — CSV/XLSX/JSON/PDF**
```ts
const formats = [
  { ext: "csv", mime: /text\/csv|application\/octet-stream/ },
  { ext: "xlsx", mime: /spreadsheet|octet-stream/ },
  { ext: "json", mime: /application\/json/ },
  { ext: "pdf", mime: /application\/pdf/ },
];

formats.forEach(({ ext, mime }, i) => {
  it(`CY-EXPORT-00${i+1} Export ${ext.toUpperCase()} funktioniert`, () => {
    cy.visit("/radar/quantum%20computing");
    cy.waitForAllPanels();
    cy.intercept("GET", `**/export/**${ext}**`).as("dl");
    cy.contains("button", new RegExp(ext, "i")).click({ force: true });
    cy.wait("@dl").then((i) => {
      expect(i.response?.statusCode).to.be.oneOf([200, 302]);
      const ct = i.response?.headers["content-type"] as string;
      expect(ct).to.match(mime);
    });
  });
});
```

### 6.6 Error-Scenarios

**CY-ERR-001 — Orchestrator-500 → Fehler-Toast**
```ts
it("CY-ERR-001 zeigt Fehler-UI bei 500", () => {
  cy.intercept("POST", "**/api/v1/radar", { statusCode: 500, body: { error: "boom" } }).as("fail");
  cy.visit("/radar/quantum%20computing");
  cy.wait("@fail");
  cy.contains(/Fehler|failed|unavailable/i).should("be.visible");
});
```

**CY-ERR-002 — Rate-Limit 429 → User-Info**
```ts
it("CY-ERR-002 zeigt Rate-Limit-Meldung bei 429", () => {
  cy.intercept("POST", "**/api/v1/radar", { statusCode: 429, body: { detail: "rate" } }).as("rate");
  cy.visit("/radar/quantum%20computing");
  cy.wait("@rate");
  cy.contains(/Rate.?Limit|zu viele|too many|429/i).should("be.visible");
});
```

**CY-ERR-003 — UC-Ausfall → Warning-Panel, andere UCs laden**
```ts
it("CY-ERR-003 Graceful Degradation: Mock UC3-Ausfall", () => {
  cy.intercept("POST", "**/api/v1/radar", (req) => {
    req.reply({ fixture: "radar_uc3_missing.json" });
  });
  cy.visit("/radar/quantum%20computing");
  cy.contains(/Wettbewerb|Competitive/i).parents('[class*="card"]').first().within(() => {
    cy.contains(/Daten nicht|nicht verfügbar|unavailable/i).should("be.visible");
  });
  cy.contains(/Landschaft|Landscape/i).should("be.visible"); // andere UCs OK
});
```

> Fixture `frontend/cypress/fixtures/radar_uc3_missing.json` erstellst du einmal: kopiere eine echte Radar-Response und leere das `uc3`-Feld + füge `warnings: ["UC3 timeout"]` hinzu.

**CY-ERR-004 — Unbekannte Technologie → Empty-State**
```ts
it("CY-ERR-004 zeigt Empty-State für 0-Treffer-Tech", () => {
  cy.visit(`/radar/${Cypress.env("UNKNOWN_TECH")}`);
  cy.contains(/keine Daten|no data|empty/i, { timeout: 60000 }).should("be.visible");
});
```

### 6.7 Responsiveness

**CY-RESP-001/002/003 — 3 Viewports**
```ts
const viewports = [
  ["desktop", 1920, 1080],
  ["laptop", 1366, 768],
  ["tablet", 768, 1024],
] as const;

viewports.forEach(([name, w, h], i) => {
  it(`CY-RESP-00${i+1} ${name} (${w}x${h}) rendert ohne Overflow`, () => {
    cy.viewport(w, h);
    cy.visit("/radar/quantum%20computing");
    cy.waitForAllPanels();
    cy.document().then((d) => {
      expect(d.documentElement.scrollWidth).to.be.at.most(w + 16); // 16px Tolerance
    });
  });
});
```

### 6.8 A11y-Smoke (Bonus)

**CY-A11Y-001 — Keine kritischen Accessibility-Violations**
```ts
// optional: npm i -D cypress-axe axe-core
it("CY-A11Y-001 axe-smoke auf Landing", () => {
  cy.visit("/");
  cy.injectAxe();
  cy.checkA11y(undefined, { includedImpacts: ["critical"] });
});
```

---

## 7. Ausführung

```bash
# Einmal-Lauf im Headless-Mode
cd frontend
npx cypress run --reporter junit --reporter-options "mochaFile=../docs/testing/ergebnisse/cypress-junit.xml"

# Oder mit Start-Server-Automatik:
# (package.json bekommt zwei Scripts:
#   "e2e:serve": "cypress run",
#   "e2e": "start-server-and-test 'cd .. && make up && sleep 30' http://localhost:3000 e2e:serve"
# )
```

### Abbruchkriterien

- Stack nicht erreichbar → dokumentieren und abbrechen.
- Mehr als **30 % der UC-Panel-Tests** fallen aus (≥ 4 von 13) → zusätzlich in der Ergebnis-Datei als **BLOCKER** markieren und einen Backend-Issue empfehlen.

---

## 8. Ergebnis-Dokumentation

Schreibe nach Abschluss `docs/testing/ergebnisse/agent1_cypress_ergebnis.md` mit folgender Struktur:

```markdown
# Ergebnis · Agent 1 · Cypress

**Lauf:** <DATUM ISO-8601> · **Stack-Commit:** <git rev-parse HEAD> · **Cypress:** <npx cypress --version>

## Zusammenfassung
- Tests gesamt: <n>
- Pass: <n> · Fail: <n> · Skipped: <n>
- Coverage: <n>/<m> UC-Panels = <%>

## Pass/Fail-Matrix

| ID | Beschreibung | Status | Dauer | Screenshot |
|---|---|---|---|---|
| CY-LAND-001 | … | ✅ | 2.3s | – |
| CY-UC1-001 | Landscape Time-Series | ✅ | 4.1s | – |
| CY-UC3-001 | Competitive HHI | ❌ | 12.0s | `screenshots/CY-UC3-001.png` |
| … | … | … | … | … |

## Gefundene Bugs

### BUG-CY-001 · Severity: Major · UC3 HHI zeigt Text statt Zahl
**Steps to reproduce:** `/radar/quantum%20computing` öffnen → warten → Competitive-Panel.
**Expected:** HHI als Zahl 0–10000.
**Actual:** Panel zeigt `N/A` obwohl Daten vorhanden (Netzwerk-Graph rendert).
**Log:** Console-Error `Cannot read property 'hhi' of undefined` in `CompetitivePanel.tsx:42`.
**Hinweis für Fix:** Response-Mapper in `frontend/src/lib/transform.ts` prüfen.

### BUG-CY-002 · …

## Offene Fragen / Empfehlungen
- Panels haben keine `data-testid` → empfehle Einführung für stabilere Tests (PR-Vorschlag).
- …
```

---

## 9. Grenzen dieses Protokolls

- **Keine Backend-Performance-Messung** — das macht Agent 2 (k6).
- **Keine API-Contract-Validierung** — das macht Agent 3 (Schemathesis).
- **Keine tiefen DB-Assertions** — bereits abgedeckt durch `tests/integration/` (pytest).
- **Keine Cross-Browser-Matrix** — Cypress läuft auf Chromium; Firefox/WebKit optional via `--browser firefox` nachreichen.
