# Konsistenz-Bugfixes TI-Radar v3 — Abschlussbericht

**Datum:** 2026-04-14 · **Basis-Audit:** `KONSOLIDIERUNG.md` (12 Bugs aus 6 Techs × 18 Agenten)
**Plan:** `~/.claude/plans/iridescent-petting-rabin.md` · **Umsetzung:** 10 Arbeitspakete via 10 Claude-Subagenten

---

## Test-Gesamtbilanz

| Bereich | Tests | Status |
|---|---:|:-:|
| `packages/shared/tests/` | 469 | ✅ |
| `services/landscape-svc/tests/` | 39 (+4 AP2, +4 AP8, +4 AP5) | ✅ |
| `services/maturity-svc/tests/` | 11 (+9 AP6, +2 AP8) | ✅ |
| `services/euroscivoc-svc/tests/` | 22 (+14 AP4, +2 AP9) | ✅ |
| `services/patent-grant-svc/tests/` | 10 (+8 AP5, +2 AP8) | ✅ |
| `services/temporal-svc/tests/` | 3 (+2 AP3, +1 AP8) | ✅ |
| `services/actor-type-svc/tests/` | 2 (+2 AP3) | ✅ |
| `services/tech-cluster-svc/tests/` | 2 (+2 AP3) | ✅ |
| `services/publication-svc/tests/` | 19 (+1 AP2, +2 AP8) | ✅ |
| `services/research-impact-svc/tests/` | 6 (+4 AP2, +2 AP8) | ✅ |
| `services/orchestrator-svc/tests/` | 6 (+6 AP3) | ✅ |
| `tests/integration/` (neu: 3 Dateien) | 14 | ✅ |
| `frontend/` (Vitest, 4 Dateien) | 27 | ✅ |
| `frontend/` TypeScript | 0 Errors | ✅ |
| **Gesamt neu geschrieben** | **~120 Tests** | ✅ |

---

## Bug-Matrix (Vorher/Nachher)

| ID | Severity | Bug | AP | Fix-Kern | Status |
|---|---|---|---|---|:-:|
| CRIT-1 | Critical | Publikationen Header ≠ UC7 ≠ UC13 (Faktor bis 1580) | AP2 | Gemeinsame `CORDIS_LINKED`-Query für Header + UC13; UC7 relabelt als „Top-Autor-Publikationen"; Integrationstest | ✅ |
| CRIT-2 | Critical | Shannon > 0 bei 1 Feld + „law" als Disziplin für Batterien | AP4 | Aggregation nur auf `FIELD`-Level; `shannon_index([1])=0`; `ts_rank_cd ≥ 0.05`-Filter | ✅ |
| CRIT-3 | Critical | Akteurs-Zählbasis UC8/UC9/UC11 divergiert bis Faktor 100 | AP3 | `ActorScope`-Enum; pro UC ein kanonisches Label; UI-Labels „aktive Akteure (im Zeitfenster)" / „klassifizierte Akteure (CORDIS)" / „Cluster-Mitglieder" + InfoTooltips | ✅ |
| CRIT-4 | Critical | Patent-Population Header vs. UC12 Faktor bis 54 | AP5 | `PatentScope`-Enum; Shared-Konstanten für `APPLICATION_KIND_CODES` + `GRANT_KIND_CODES`; neue Methode `total_patent_counts()` atomar | ✅ |
| MAJ-5 | Major | Header-Doppel-Phase „Reife + Rückläufige Entwicklung" | AP7 | Phase und Trend in zwei separate Badge-Slots; Phase-Label aus UC2, Trend aus CAGR | ✅ |
| MAJ-6 | Major | „Wettbewerbsintensiver Markt" als Fake-Fallback | AP7 | `concentrationBadge()` nutzt `competitive.concentration` (Backend); kein Hardcode-Fallback mehr | ✅ |
| MAJ-7 | Major | Jahresachsen 2024↔2026 inkonsistent | AP8 | Alle 6 Services liefern `data_complete_year`; UC13-ReferenceArea neu, UC1/UC2/UC7/UC8/UC12 harmonisiert | ✅ |
| MAJ-8 | Major | Unvollständiges 2026 in CAGR/S-Kurve-Fit | AP1+AP8 | `last_complete_year()`-Helper in `packages/shared/domain/year_completeness.py`; Backend cuttoff + Frontend-Warning | ✅ |
| MAJ-9 | Major | R² = 0.000 + 80 % Konfidenz + Phase gleichzeitig | AP1+AP6 | `s_curve_confidence` gibt 0 zurück bei R² < 0.5 (strukturell); `fit_reliability_flag` im Proto; UI graut Phase bei `!fit_reliability_flag` | ✅ |
| MIN-10 | Minor | UC10 Projekt-Zahl ≠ Header (387 vs. 307) | AP9 | `COUNT(DISTINCT project_id)` + Jahres-Filter in `total_mapped_projects` | ✅ |
| MIN-11 | Minor | UC13 Gesamtsumme ohne Rechnung | AP9 | Explizite Zeile „X Pub/Projekt × Y Projekte ≈ Z Publikationen" unter Badges | ✅ |
| INFO-12 | Info | h-Index-Schwellen undokumentiert | AP9 | Badge-Text erweitert („Sehr hoher Impact (h=120)") + InfoTooltip mit Schwellen | ✅ |

---

## Strukturelle Verbesserungen (über einzelne Fixes hinaus)

1. **Shared-Domain-Master-Definitionen** (`packages/shared/domain/`):
   - `publication_definitions.py` — `PublicationScope`-Enum, `canonical_publication_label()`
   - `actor_definitions.py` — `ActorScope`-Enum, `canonical_actor_label()`
   - `patent_definitions.py` — `PatentScope`-Enum, `APPLICATION_KIND_CODES`, `GRANT_KIND_CODES`, `canonical_patent_label()`
   - `year_completeness.py` — `last_complete_year()`, `is_year_complete()`, `clip_to_complete_years()`
   - `metrics.py` erweitert: Konstante `R2_RELIABILITY_THRESHOLD = 0.5`, `s_curve_confidence` mit strukturellem R²-Gate

2. **Proto-Erweiterungen**:
   - `proto/uc2_maturity.proto` — neues Feld `fit_reliability_flag`
   - `proto/uc8_temporal.proto`, `uc9_tech_cluster.proto`, `uc11_actor_type.proto` — Kommentare zum `ActorScope` dokumentiert

3. **Frontend-Neue-Module**:
   - `frontend/src/lib/year-completeness.ts` — Mirror des Python-Helpers
   - `frontend/src/lib/publication-calc.ts` — Pure-Logic-Helper für UC13-Rechnung

4. **Vitest-Setup** — das Frontend hat jetzt eine laufende Test-Suite (`npm run test` → 27 Tests).

---

## Noch offen (außerhalb der 12 Bugs)

**Architektur-Schulden, die der Konsistenz-Audit sichtbar gemacht hat, aber nicht Teil der 12 Bugs sind:**

1. **Pre-existing kaputte Test-Module** (nicht von uns verursacht):
   - `services/publication-svc/tests/test_mappers.py`, `services/research-impact-svc/tests/test_mappers.py` und weitere — importieren nicht-existente Module (`src.use_case.*Result`, `src.mappers.dict_response`). Diese wurden bei unseren pytest-Läufen per `--ignore` ausgeklammert. **Empfehlung:** In einem Cleanup-Ticket anfassen.

2. **Docker-Stack-Build** scheiterte in früheren Tests an `deb.debian.org` (transient). Für das Live-Deployment der Fixes ist ein Rebuild nötig.

---

## Nächste Schritte (AP10 — Live-Verifikation)

Die Fixes sind im Code, alle Tests grün. Für den Live-System-Nachweis auf `app.drakain.de`:

```bash
# 1. Commit + Push
git add -A
git commit -m "fix(consistency): Resolve 12 metric divergences from audit

- CRIT-1 Publications: unify Header + UC13 via CORDIS_LINKED scope
- CRIT-2 EuroSciVoc: Shannon field-level only, ts_rank filter
- CRIT-3 Actors: scope-labeled (ACTIVE_IN_WINDOW/CLASSIFIED/CLUSTER_MEMBER)
- CRIT-4 Patents: shared kind-code constants
- MAJ-5/6: Header badges split (Phase/Trend/Concentration)
- MAJ-7/8: year_completeness helper, data_complete_year everywhere
- MAJ-9: R²-coupled confidence, fit_reliability_flag proto field
- MIN-10/11 + INFO-12: UC10 DISTINCT count, UC13 explicit calc, h-index tooltip

~120 new tests across shared/, services/, tests/integration/, frontend/"
git push

# 2. Rebuild + Deploy (produktionsabhängig)
cd deploy && make docker && make up  # lokal
# oder via CI/CD-Pipeline für app.drakain.de

# 3. Re-Verifikation via Playwright MCP (analog zur ersten Welle):
#    6 Techs erneut durchlaufen → raw4_*.json
#    Diff gegen raw3_*.json muss zeigen:
#    - Header.publications == UC13.total_publications
#    - Shannon > 0 ⇒ active_fields ≥ 2
#    - R² < 0.5 ⇒ Konfidenz = 0
#    - Kein „Wettbewerbsintensiv" bei HHI < 1500
#    - data_complete_year in jedem Panel sichtbar
```

---

## Audit-Trail

| Phase | Dauer | Agenten | Output |
|---|---|---:|---|
| Phase A (AP1) | ~8 min | 1 | 4 neue Domain-Module, 65 neue Tests |
| Phase B (AP2–AP5) | ~30 min parallel | 4 | 8 Services modifiziert, ~40 neue Tests |
| Phase C (AP6–AP9) | ~23 min parallel | 4 | 6 Services + 8 Frontend-Dateien, ~50 neue Tests |
| Phase D (Tests + Doku) | ~5 min | — | Gesamtverifikation, dieser Report |

**Gesamtdauer Implementation:** ca. 70 Minuten (bei sequentieller Ausführung wäre es 3–4 Stunden gewesen).
