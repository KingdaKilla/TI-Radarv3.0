# API-Referenz

Der Orchestrator stellt eine REST/JSON-API auf Port 8000 bereit. Alle Analyse-Endpunkte erfordern einen `X-API-Key`-Header (konfigurierbar). Rate Limiting: 100 Requests/Minute pro IP.

## Endpunkte

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/api/v1/radar` | Komplette Radar-Analyse (alle 13 UC-Services parallel) |
| `GET` | `/api/v1/suggestions` | Autocomplete-Vorschläge für das Suchfeld |
| `GET` | `/health` | Health Check (shallow oder deep) |
| `GET` | `/metrics` | Prometheus-Metriken (OpenMetrics-Format) |
| `POST` | `/api/v1/import/epo` | EPO-Patent-Bulk-Import |
| `POST` | `/api/v1/import/cordis` | CORDIS-Projekt-Import |
| `POST` | `/api/v1/import/euroscivoc` | EuroSciVoc-Taxonomie-Import |
| `POST` | `/api/v1/import/refresh-views` | Materialized Views aktualisieren |
| `GET` | `/api/v1/import/status` | Import-Status abfragen |

---

## POST /api/v1/radar

Führt eine Technology-Radar-Analyse durch. Der Orchestrator verteilt die Anfrage parallel via gRPC an alle 13 UC-Services und aggregiert die Ergebnisse.

### Request

```bash
curl -X POST http://localhost:8000/api/v1/radar \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <api-key>" \
  -d '{
    "technology": "solid-state batteries",
    "years": 10,
    "european_only": false,
    "cpc_codes": [],
    "top_n": 0,
    "use_cases": []
  }'
```

### Request-Parameter

| Feld | Typ | Pflicht | Default | Beschreibung |
|---|---|---|---|---|
| `technology` | `string` | ja | -- | Technologie-Suchbegriff (1-200 Zeichen) |
| `years` | `int` | nein | `10` | Analysezeitraum in Jahren (3-30, rückblickend ab heute) |
| `european_only` | `bool` | nein | `false` | Nur EU-27 + assoziierte Länder |
| `cpc_codes` | `string[]` | nein | `[]` | CPC-Codes zur Einschränkung (max. 50, Format: `[A-H]\d+`) |
| `top_n` | `int` | nein | `0` | Max. Top-N-Einträge pro Panel (0 = Service-Default) |
| `use_cases` | `string[]` | nein | `[]` | Selektive UC-Ausführung (leer = alle 13 UCs) |

**Erlaubte `use_cases`-Werte:**
`landscape`, `maturity`, `competitive`, `funding`, `cpc_flow`, `geographic`, `research_impact`, `temporal`, `tech_cluster`, `actor_type`, `patent_grant`, `euroscivoc`, `publication`

### Response (Erfolg -- 200)

```json
{
  "technology": "solid-state batteries",
  "analysis_period": "2016-2026",
  "landscape": { ... },
  "maturity": { ... },
  "competitive": { ... },
  "funding": { ... },
  "cpc_flow": { ... },
  "geographic": { ... },
  "research_impact": { ... },
  "temporal": { ... },
  "tech_cluster": { ... },
  "actor_type": { ... },
  "patent_grant": { ... },
  "euroscivoc": { ... },
  "publication": { ... },
  "uc_errors": [],
  "explainability": {
    "data_sources": [
      {
        "name": "EPO DOCDB",
        "type": "patent",
        "record_count": 12345,
        "last_updated": "2026-01-15"
      }
    ],
    "methods": [],
    "deterministic": true,
    "warnings": []
  },
  "total_processing_time_ms": 3421,
  "successful_uc_count": 13,
  "total_uc_count": 13,
  "request_id": "a1b2c3d4-e5f6-...",
  "timestamp": "2026-03-22T14:30:00.000000"
}
```

Jedes UC-Panel (`landscape`, `maturity`, etc.) enthält die service-spezifische Analyse als JSON-Objekt. Die genaue Struktur wird durch die jeweilige Protobuf-Definition bestimmt (siehe `proto/uc*.proto`).

### Graceful Degradation

Wenn ein UC-Service fehlschlägt (Timeout, Unavailable, etc.), liefert das betroffene Panel ein leeres Objekt `{}`. Der Fehler wird in `uc_errors` gemeldet:

```json
{
  "landscape": {},
  "uc_errors": [
    {
      "use_case": "landscape",
      "error_code": "TIMEOUT",
      "error_message": "UC1 Landscape: Timeout nach 30s",
      "retryable": true,
      "elapsed_ms": 30012
    }
  ],
  "successful_uc_count": 12,
  "total_uc_count": 13
}
```

**Fehler-Codes:**

| Code | Beschreibung | Retryable |
|---|---|---|
| `TIMEOUT` | Service hat nicht innerhalb des Timeouts geantwortet | ja |
| `UNAVAILABLE` | Service nicht erreichbar | ja |
| `RESOURCE_EXHAUSTED` | Service überlastet | ja |
| `INTERNAL` | Interner Serverfehler | nein |
| `NOT_FOUND` | Keine Daten gefunden | nein |
| `UNIMPLEMENTED` | RPC nicht implementiert | nein |
| `STUBS_UNAVAILABLE` | gRPC-Stubs nicht generiert | nein |

### Selektive UC-Ausführung

Über das `use_cases`-Feld können einzelne UCs angefordert werden:

```bash
curl -X POST http://localhost:8000/api/v1/radar \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <api-key>" \
  -d '{
    "technology": "CRISPR",
    "use_cases": ["landscape", "funding", "geographic"]
  }'
```

Nicht angeforderte Panels werden in der Response als leere Objekte `{}` zurückgegeben.

---

## GET /api/v1/suggestions

Liefert Autocomplete-Vorschläge basierend auf Patent- und Projekt-Titeln aus der Datenbank.

### Request

```bash
# Kuratierte Default-Vorschläge (leerer Query)
curl "http://localhost:8000/api/v1/suggestions"

# Suche nach Prefix
curl "http://localhost:8000/api/v1/suggestions?q=quantum&limit=5"
```

### Query-Parameter

| Parameter | Typ | Default | Beschreibung |
|---|---|---|---|
| `q` | `string` | `null` | Suchbegriff (min. 2 Zeichen für DB-Suche) |
| `limit` | `int` | `8` | Max. Anzahl Vorschläge (1-20) |

### Response (200)

```json
["Quantum Computing", "Quantum Dots", "Quantum Sensing", "Quantum Cryptography"]
```

Bei leerem oder kurzem Suchbegriff werden kuratierte Default-Vorschläge zurückgegeben (z.B. "Artificial Intelligence", "Battery Technology", "CRISPR", etc.).

---

## GET /health

Aggregierter Health Check über den Orchestrator und optional alle UC-Services.

### Request

```bash
# Shallow (nur Orchestrator)
curl http://localhost:8000/health

# Deep (alle UC-Services prüfen)
curl "http://localhost:8000/health?deep=true"
```

### Query-Parameter

| Parameter | Typ | Default | Beschreibung |
|---|---|---|---|
| `deep` | `bool` | `false` | Deep Check: Konnektivität zu allen UC-Services prüfen |

### Response -- Shallow (200)

```json
{
  "healthy": true,
  "services": [],
  "version": "2.0.0",
  "timestamp": "2026-03-22T14:30:00.000000",
  "database_healthy": true
}
```

### Response -- Deep (200)

```json
{
  "healthy": true,
  "services": [
    {
      "service_name": "landscape-svc (UC1)",
      "use_case": "landscape",
      "healthy": true,
      "latency_ms": 12,
      "error": "",
      "version": ""
    },
    {
      "service_name": "maturity-svc (UC2)",
      "use_case": "maturity",
      "healthy": true,
      "latency_ms": 8,
      "error": "",
      "version": ""
    }
  ],
  "version": "2.0.0",
  "timestamp": "2026-03-22T14:30:00.000000",
  "database_healthy": true
}
```

---

## GET /metrics

Prometheus-Metriken im OpenMetrics-Format. Dieser Endpunkt ist nicht in der OpenAPI-Dokumentation enthalten (`include_in_schema=False`).

### Request

```bash
curl http://localhost:8000/metrics
```

### Response (200, text/plain)

```
# HELP ti_radar_grpc_calls_total gRPC-Aufrufe an UC-Services
# TYPE ti_radar_grpc_calls_total counter
ti_radar_grpc_calls_total{uc="landscape",status="success"} 42.0
ti_radar_grpc_calls_total{uc="landscape",status="timeout"} 1.0
...
```

---

## Import-Endpunkte

Der Import-Service (`import-svc`) stellt Endpunkte zum Befüllen und Aktualisieren der Datenbank bereit.

### POST /api/v1/import/epo

Startet einen Bulk-Import von EPO-Patentdaten (DOCDB). Die Patente werden geparst und in die `patent_schema`-Tabellen geschrieben.

```bash
curl -X POST http://localhost:8000/api/v1/import/epo \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <api-key>"
```

### POST /api/v1/import/cordis

Importiert CORDIS-Projektdaten (EU-Forschungsprojekte) in die `project_schema`-Tabellen.

```bash
curl -X POST http://localhost:8000/api/v1/import/cordis \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <api-key>"
```

### POST /api/v1/import/euroscivoc

Importiert die EuroSciVoc-Taxonomie (European Science Vocabulary) für die Klassifikation von Forschungsthemen.

```bash
curl -X POST http://localhost:8000/api/v1/import/euroscivoc \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <api-key>"
```

### POST /api/v1/import/refresh-views

Aktualisiert alle Materialized Views in der Datenbank. Dies sollte nach einem Import ausgeführt werden, damit die Analyse-Services auf aktuelle, vorberechnete Daten zugreifen.

```bash
curl -X POST http://localhost:8000/api/v1/import/refresh-views \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <api-key>"
```

### GET /api/v1/import/status

Gibt den aktuellen Import-Status zurück (laufende und abgeschlossene Imports, Anzahl importierter Datensätze, Fehler).

```bash
curl http://localhost:8000/api/v1/import/status \
  -H "X-API-Key: <api-key>"
```

### Auto-Seeding (Demo-Daten)

Beim ersten Datenbankstart werden automatisch CORDIS-Demo-Daten geladen. Das System ist dadurch sofort nach `docker compose up` für Tests und Demos nutzbar, ohne manuelle Imports durchführen zu müssen.

---

## API-Caching

Externe API-Aufrufe (OpenAIRE, Semantic Scholar) werden in der Datenbank gecacht, um Latenz zu reduzieren und die Rate Limits der externen APIs zu schonen.

### Cache-Strategie

Alle externen API-Zugriffe folgen demselben Ablauf:

1. **Cache prüfen** -- Ist ein gültiger (nicht abgelaufener) Cache-Eintrag vorhanden, wird dieser direkt zurückgegeben.
2. **API aufrufen** -- Kein Cache-Hit: die externe API wird live abgefragt.
3. **Ergebnis speichern** -- Die API-Antwort wird mit Zeitstempel in der Datenbank persistiert.
4. **Stale Cache bei API-Ausfall** -- Ist die externe API nicht erreichbar, wird ein abgelaufener Cache-Eintrag als Fallback genutzt (besser veraltete Daten als gar keine).

> **Hinweis:** Die erste Abfrage für eine neue Technologie dauert länger (Live-API-Call), alle Folgeabfragen innerhalb der TTL werden sofort aus dem Cache bedient.

### Cache-Konfiguration

| Datenquelle | TTL | Cache-Tabellen |
|---|---|---|
| OpenAIRE (Publikationsdaten) | 7 Tage | `research_schema.openaire_cache` |
| Semantic Scholar | 30 Tage | `research_schema.papers`, `research_schema.authors`, `research_schema.query_cache` |

---

## HTTP-Status-Codes

| Code | Beschreibung |
|---|---|
| `200` | Erfolg |
| `400` | Ungültige Anfrage (Validierungsfehler: ungültige CPC-Codes, unbekannte use_cases, etc.) |
| `401` | Fehlender oder ungültiger API-Key |
| `422` | Pydantic-Validierungsfehler (z.B. `technology` zu lang, `years` außerhalb 3-30) |
| `429` | Rate Limit überschritten (100 Requests/Minute) |
| `500` | Interner Serverfehler |

### Fehler-Response (422)

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "use_cases", 0],
      "msg": "Value error, Unknown use_cases: ['invalid']. Allowed: ['actor_type', 'cpc_flow', ...]",
      "input": "invalid"
    }
  ]
}
```

### Fehler-Response (429)

```json
{
  "detail": "Rate limit exceeded. Max 100 requests per 60 seconds."
}
```
