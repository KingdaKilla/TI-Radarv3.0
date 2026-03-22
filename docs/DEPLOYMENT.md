# Deployment

## Voraussetzungen

| Komponente | Version | Pruefung |
|---|---|---|
| Docker Desktop | >= 4.x | `docker --version` |
| Docker Compose Plugin | >= 2.x | `docker compose version` |
| Externes Laufwerk | >= 600 GB | fuer PostgreSQL-Datenverzeichnis |
| RAM | >= 16 GB empfohlen | PostgreSQL benoetigt 8 GB (konfiguriert) |

## Schritt-fuer-Schritt-Setup

### 1. Repository klonen

```bash
git clone https://github.com/<org>/ti-radar.git
cd ti-radar
```

### 2. Umgebungskonfiguration erstellen

```bash
cp .env.example .env
```

Folgende Werte muessen in `.env` eingetragen werden:

| Variable | Pflicht | Beschreibung | Beispiel |
|---|---|---|---|
| `POSTGRES_PASSWORD` | ja | Datenbank-Passwort | `mein_sicheres_pw` |
| `TI_RADAR_DB_PATH` | ja | Pfad zum DB-Verzeichnis (externes Laufwerk) | `D:/ti-radar-db` |
| `EPO_OPS_CONSUMER_KEY` | nein | EPO API Key (fuer Live-Abfragen) | |
| `EPO_OPS_CONSUMER_SECRET` | nein | EPO API Secret | |
| `GRAFANA_ADMIN_PASSWORD` | nein | Grafana-Passwort (nur mit Monitoring-Profil) | `admin` |

### 3. Setup-Skript ausfuehren

```bash
bash scripts/setup.sh
```

Das Skript:
1. Prueft Docker-Installation
2. Erstellt `.env` falls nicht vorhanden
3. Prueft `TI_RADAR_DB_PATH`
4. Generiert Protobuf-Stubs (falls grpcio-tools installiert)
5. Baut alle Docker-Images

### 4. Stack starten

```bash
bash scripts/start.sh
```

Das Skript prueft, ob das externe Laufwerk angeschlossen ist, und startet alle 18 Services.

### 5. Erreichbarkeit pruefen

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs (Debug) | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

## Datenbank auf externem Laufwerk

Die PostgreSQL-Daten liegen standardmaessig auf einem externen Laufwerk. Der Pfad wird ueber `TI_RADAR_DB_PATH` in `.env` konfiguriert.

**Wichtig:**
- Das Verzeichnis wird beim ersten Start automatisch erstellt
- Beim Starten muss das externe Laufwerk angeschlossen sein
- Bei Wechsel des Laufwerksbuchstabens (Windows) muss `TI_RADAR_DB_PATH` angepasst werden
- Das Datenverzeichnis enthaelt die komplette PostgreSQL-Instanz (~590 GB)

```bash
# Beispiel Windows
TI_RADAR_DB_PATH=D:/ti-radar-db

# Beispiel Linux
TI_RADAR_DB_PATH=/mnt/external/ti-radar-db
```

## Bulk-Daten-Import (optional)

Fuer den Erst-Import der Patent- und CORDIS-Daten stehen Bulk-Import-Pfade zur Verfuegung.

### EPO DOCDB

1. DOCDB-Bulk-Daten herunterladen: https://www.epo.org/searching-for-patents/data/bulk-data-sets/docdb.html
2. Pfad in `.env` konfigurieren:
   ```bash
   EPO_BULK_PATH=./data/bulk/EPO
   ```
3. Import-Service nutzt den konfigurierten Pfad als Read-Only-Volume

### CORDIS

1. CORDIS-Referenzdaten herunterladen: https://data.europa.eu/data/datasets/cordisref-data
2. Pfad in `.env` konfigurieren:
   ```bash
   CORDIS_BULK_PATH=./data/bulk/CORDIS
   ```

## Docker Compose Befehle

Alle Compose-Befehle verwenden die Konfiguration aus `deploy/docker-compose.yml`:

```bash
# Stack starten (detached)
docker compose --env-file .env -f deploy/docker-compose.yml up -d

# Stack stoppen
docker compose --env-file .env -f deploy/docker-compose.yml down

# Logs folgen
docker compose --env-file .env -f deploy/docker-compose.yml logs -f

# Einzelnen Service neustarten
docker compose --env-file .env -f deploy/docker-compose.yml restart landscape-svc

# Images neu bauen
docker compose --env-file .env -f deploy/docker-compose.yml build
```

Alternativ via Makefile aus dem `deploy/`-Verzeichnis:

```bash
cd deploy
make up       # Stack starten
make down     # Stack stoppen
make logs     # Logs folgen
make docker   # Images bauen
```

## Monitoring (optional)

Prometheus und Grafana werden nur mit dem Monitoring-Profil gestartet:

```bash
docker compose --env-file .env -f deploy/docker-compose.yml --profile monitoring up -d
```

| Service | URL | Beschreibung |
|---|---|---|
| Prometheus | http://localhost:9090 | Metriken-Sammlung |
| Grafana | http://localhost:3001 | Dashboards |
| pgAdmin | http://localhost:5050 | Datenbank-Administration |

Prometheus scraped automatisch den `/metrics`-Endpunkt des Orchestrators (OpenMetrics-Format). Grafana-Dashboards und Provisioning-Dateien liegen in `deploy/infra/grafana/`.

## Service-Uebersicht

| Container | Port | Beschreibung |
|---|---|---|
| `ti-radar-db` | 5432 | PostgreSQL 17 + pgvector |
| `ti-radar-orchestrator` | 8000 | FastAPI REST Gateway |
| `ti-radar-frontend` | 3000 | Next.js Frontend |
| `ti-radar-import` | 8030 | Bulk-Import-Service |
| `ti-radar-export` | 8020 | Export-Service |
| `ti-radar-uc1` bis `ti-radar-uc12` | 50051 (intern) | UC-Services |
| `ti-radar-uc-c` | 50051 (intern) | Publication-Service |

## Ressourcen-Limits

| Service | RAM | CPUs |
|---|---|---|
| PostgreSQL | 8 GB | 2.0 |
| Import-Service | 2 GB | 2.0 |
| CPC-Flow-Service | 1 GB | 1.0 |
| Export-Service | 1 GB | 1.0 |
| Alle anderen Services | 512 MB | 0.5 |

## Troubleshooting

### Docker Desktop startet nicht (Windows)

Docker Desktop unter Windows kann instabil werden. Loesung:

1. Alle Docker-Prozesse im Task-Manager beenden
2. WSL herunterfahren: `wsl --shutdown`
3. Docker Desktop manuell neu starten

### Datenbank-Verbindung fehlgeschlagen

```bash
# Pruefen ob DB-Container laeuft
docker ps | grep ti-radar-db

# Manuell testen
docker exec -i ti-radar-db psql -U tip_admin -d ti_radar -c "SELECT 1"

# Logs pruefen
docker logs ti-radar-db --tail 50
```

### Port-Konflikte

Falls Port 5432 bereits belegt ist (lokale PostgreSQL-Installation):

```bash
# Pruefen welcher Prozess den Port belegt
# Windows:
netstat -ano | findstr :5432
# Linux:
ss -tlnp | grep 5432
```

Die Datenbank ist nur auf `127.0.0.1:5432` gebunden. Bei Konflikten kann der Port in `docker-compose.yml` geaendert werden.

### UC-Service antwortet nicht

```bash
# Deep Health Check: alle Services pruefen
curl http://localhost:8000/health?deep=true | python -m json.tool

# Logs eines bestimmten Service pruefen
docker logs ti-radar-uc1 --tail 50
```

### Externes Laufwerk nicht erreichbar

```
FEHLER: Datenbank-Verzeichnis nicht gefunden: D:/ti-radar-db
Ist das externe Laufwerk angeschlossen?
```

Pruefen, ob das externe Laufwerk gemountet ist und der in `TI_RADAR_DB_PATH` konfigurierte Pfad existiert.
