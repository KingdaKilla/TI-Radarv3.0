# Deployment

## Voraussetzungen

| Komponente | Version | Prüfung |
|---|---|---|
| Docker Desktop | >= 4.x | `docker --version` |
| Docker Compose Plugin | >= 2.x | `docker compose version` |
| Festplattenspeicher | >= 5 GB | Docker-Images + Demo-Datenbank. Für Vollimport (EPO + CORDIS): ~450 GB inkl. Junction-Tabellen + WAL-Headroom |
| RAM | >= 16 GB empfohlen | PostgreSQL benötigt 8 GB (konfiguriert) |

## Schritt-für-Schritt-Setup

### 1. Repository klonen

```bash
git clone https://github.com/KingdaKilla/TI-Radarv3.0.git
cd TI-Radarv3.0
```

### 2. Umgebungskonfiguration erstellen

```bash
cp .env.example .env
```

Folgende Werte müssen in `.env` eingetragen werden:

| Variable | Pflicht | Beschreibung | Beispiel |
|---|---|---|---|
| `POSTGRES_PASSWORD` | ja | Datenbank-Passwort | `mein_sicheres_pw` |
| `EPO_OPS_CONSUMER_KEY` | nein | EPO API Key (für Live-Abfragen) | |
| `EPO_OPS_CONSUMER_SECRET` | nein | EPO API Secret | |
| `IMPORT_SCHEDULE` | nein | Cron-Ausdruck fuer woechentlichen Bulk-Import | `0 2 * * 0` |
| `SCHEDULER_ENABLED` | nein | Import-Scheduler aktivieren/deaktivieren | `true` |
| `GLEIF_ENABLED` | nein | GLEIF LEI Lookup im Actor-Type-Service | `true` |
| `TI_RADAR_ADMIN_KEY` | nein | Admin-Key fuer Import-Endpunkte (leer = kein Auth) | |
| `GRAFANA_ADMIN_PASSWORD` | nein | Grafana-Passwort (nur mit Monitoring-Profil) | `admin` |
| `GEMINI_API_KEY` | nein (v3.5.0+) | Google-Gemini-API-Key für LLM-Features; ohne Key läuft das Tool, zeigt aber keine Panel-Analysen | `AIzaSy...` |
| `LLM_PROVIDER` | nein (v3.5.0+) | LLM-Backend: `gemini` (Default) / `anthropic` / `openai` / `ollama` | `gemini` |
| `LLM_MODEL_NAME` | nein (v3.5.0+) | Modell-ID; Default passt zu Gemini | `gemini-2.0-flash` |
| `ANTHROPIC_API_KEY` | nein | Nur wenn `LLM_PROVIDER=anthropic` | `sk-ant-...` |
| `OPENAI_API_KEY` | nein | Nur wenn `LLM_PROVIDER=openai` | `sk-...` |
| `EMBEDDING_PROVIDER` | nein (v3.6.0+) | `local` (im embedding-svc) oder `remote` (TEI-Host) | `local` |
| `EMBEDDING_DEVICE` | nein (v3.6.0+) | `cpu` oder `cuda` | `cpu` |
| `FAITHFULNESS_ENABLED` | nein (v3.6.0+) | Chat-Antwort-Überprüfung (Sufficiency + Faithfulness-Check); +2-5s Latenz | `false` |

> **Details zu LLM/Chat/RAG:** siehe [`docs/LLM.md`](./LLM.md) — komplette Architektur, Konfiguration, Incremental-Pre-Computation, Betrieb.

### 3. Stack starten

**Lokale Entwicklung** (baut Images lokal):

```bash
docker compose -f deploy/docker-compose.yml --env-file .env up -d
```

**Server-Deployment** (zieht vorgefertigte GHCR-Images):

```bash
docker compose -f deploy/docker-compose.server.yml --env-file .env up -d
```

`docker-compose.server.yml` unterscheidet sich von der lokalen Variante:
- Alle Service-Images werden aus `ghcr.io/${GHCR_OWNER}/ti-radar-*:${IMAGE_TAG}` gezogen statt lokal gebaut.
- Die Datenbank nutzt das Custom-Image `ghcr.io/${GHCR_OWNER}/ti-radar-db:${IMAGE_TAG}` (statt `pgvector/pgvector:pg17`), in das die Init-Skripte (`database/sql/`, `database/mock_data/`) eingebrannt sind.

**Hinweis:** Die Init-Skripte (`/docker-entrypoint-initdb.d/`) werden nur beim ersten Start ausgefuehrt (leeres pgdata-Volume). Bei bestehenden Datenbanken muessen Schema-Aenderungen und Grants manuell angewandt werden.

Beim ersten Start werden automatisch das Datenbankschema angelegt und CORDIS-Demodaten geladen.

### 4. Erreichbarkeit prüfen

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs (Debug) | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

## Datenbankspeicher

Die PostgreSQL-Daten werden in einem Docker-Volume am Projektstandort gespeichert.

**Hinweise:**
- Das Volume wird beim ersten Start automatisch erstellt
- Die Datenbank belegt ca. 363 GB mit voller Datenlage (156M Patents, gefuellte
  Junction-Tabellen, `cross_schema.document_chunks` mit pgvector-Embeddings)
- Ohne EPO-Import (nur CORDIS-Demodaten) ca. 50 MB
- **Backup:** `./database/create_split_dump.sh` (partitionierter Split-Dump,
  siehe Abschnitt [Split-Dump Backup & Restore](#split-dump-backup--restore-production-grade))

## Bulk-Daten-Import (optional)

Für den Erst-Import der Patent- und CORDIS-Daten stehen Bulk-Import-Pfade zur Verfügung.

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

## Repo-less Server Deployment (nur GHCR-Images)

Fuer Produktions-Server, auf denen **kein git-Checkout** des Repos gewuenscht
ist. Zwei Kategorien von Dateien werden benoetigt:

**Aus dem `ti-radar-db`-Image unter `/opt/restore/`** (Runtime-Artefakte,
werden entweder direkt im Container ausgefuehrt oder per `docker cp`
extrahiert und auf dem Host gestartet):

| Datei | Zweck |
|---|---|
| `restore_split_dump.sh` | Restore-Wrapper fuer partitionierte Dumps (9 Phasen, auf Host ausgefuehrt) |
| `restore_on_server.sh` | Alternativer Wrapper fuer monolithische Dumps (auf Host ausgefuehrt) |
| `seed_junctions_production.sql` | Junction-Ableitung (Phase `[7/9]` findet es automatisch im Image) |
| `refresh_cross_schema_mvs.sql` | MV-Refresh (Phase `[8/9]` findet es automatisch im Image) |
| `restore_dump.sql` | Truncate + Sequence-Reset (Phase `[3/9]` nutzt es) |

**Aus GitHub per `curl`** (Deployment-Vorlagen, keine Runtime-Artefakte):

| Datei | Raw-URL |
|---|---|
| `docker-compose.server.yml` | `https://raw.githubusercontent.com/KingdaKilla/TI-Radarv3.0/master/deploy/docker-compose.server.yml` |
| `.env.example` | `https://raw.githubusercontent.com/KingdaKilla/TI-Radarv3.0/master/.env.example` |

Warum die Trennung: Runtime-Artefakte (Bash-Wrapper, SQL-Skripte) werden
beim Release automatisch mitversioniert und passen damit exakt zum Image.
Deployment-Vorlagen (Compose, Env) sind keine Runtime-Artefakte — sie
aendern sich selten und koennen unabhaengig vom Image gezogen werden.

Voraussetzungen: Docker Engine + Compose-Plugin, `curl`, Login bei ghcr.io
falls das Image privat ist.

### 1. Arbeitsverzeichnis und Image-Pull

```bash
# Einmaliges Arbeitsverzeichnis
mkdir -p ~/ti-radar && cd ~/ti-radar

# Optional: bei ghcr.io einloggen (nur noetig wenn Images privat sind)
# echo $GHCR_PAT | docker login ghcr.io -u kingdakilla --password-stdin

# DB-Image ziehen — enthaelt alle Setup-Dateien unter /opt/restore/
docker pull ghcr.io/kingdakilla/ti-radar-db:latest
# ...oder gepinnt auf einen Tag:
# docker pull ghcr.io/kingdakilla/ti-radar-db:v3.3.4
```

### 2. Bash-Wrapper aus dem Image extrahieren

Ein temporaerer, niemals gestarteter Container dient nur als File-Quelle
fuer die Bash-Wrapper:

```bash
docker create --name ti-radar-extract ghcr.io/kingdakilla/ti-radar-db:latest
docker cp ti-radar-extract:/opt/restore/restore_split_dump.sh ./restore_split_dump.sh
docker cp ti-radar-extract:/opt/restore/restore_on_server.sh  ./restore_on_server.sh
docker rm ti-radar-extract

chmod +x restore_split_dump.sh restore_on_server.sh
```

### 2b. Compose-File und Env-Vorlage von GitHub holen

```bash
BRANCH=master   # oder ein konkreter Tag wie v3.2.9

curl -fsSL -o docker-compose.yml \
    "https://raw.githubusercontent.com/KingdaKilla/TI-Radarv3.0/${BRANCH}/deploy/docker-compose.server.yml"
curl -fsSL -o .env.example \
    "https://raw.githubusercontent.com/KingdaKilla/TI-Radarv3.0/${BRANCH}/.env.example"

ls -la
```

**Hinweis:** `docker-compose.yml` ist hier der umbenannte `server.yml`-Inhalt.
Dadurch findet `docker compose` es automatisch im CWD und du brauchst kein
`-f` Flag. Falls du den Namen behalten willst, verwende im Folgenden
`docker compose -f docker-compose.server.yml ...`.

### 3. `.env` konfigurieren

```bash
cp .env.example .env
nano .env
```

Pflicht-Variablen:

```
POSTGRES_DB=ti_radar
POSTGRES_USER=tip_admin
POSTGRES_PASSWORD=<sicheres_passwort>
GHCR_OWNER=kingdakilla       # fuer ghcr.io/${GHCR_OWNER}/ti-radar-* Image-Refs
IMAGE_TAG=v3.3.4             # oder latest
SCHEDULER_ENABLED=false      # waehrend Restore aus, spaeter auf true
```

Dateirechte absichern: `chmod 600 .env`

### 4. Nur DB-Container starten (Restore-Vorbereitung)

```bash
# Nur die DB zuerst (Restore braucht keine UC-Services)
docker compose --env-file .env pull db
docker compose --env-file .env up -d db

# Auf PostgreSQL-Ready warten
until docker exec ti-radar-db pg_isready -U tip_admin -d ti_radar >/dev/null 2>&1; do
    echo "warte auf DB..."; sleep 3
done
```

Beim ersten Start laeuft automatisch das Mock-Seeding (~50 MB Demo-Daten).
Das ist OK — Phase `[3/9]` des Restore-Skripts leert alle Tabellen wieder.

### 5. Split-Dump Restore ausfuehren

```bash
# Mit DELETE_DUMPS_AFTER_RESTORE=1 auf knappem Plattenplatz
COMPOSE_FILE=docker-compose.yml \
DELETE_DUMPS_AFTER_RESTORE=1 \
    ./restore_split_dump.sh /home/ben/ti_radar_dump_2026-04-08
```

Was passiert:
- Phase `[1/9]` startet die DB (laeuft schon)
- Phase `[3/9]` truncated alle Tabellen, holt `restore_dump.sql` aus `/opt/restore/`
- Phase `[7/9]` ruft `seed_junctions_production.sql` auf — Fallback-Kette:
  1. `./database/sql/seed_junctions_production.sql` (nicht vorhanden im repo-less Setup)
  2. `/opt/restore/seed_junctions_production.sql` **im Container** ← greift hier
- Phase `[8/9]` analog mit `refresh_cross_schema_mvs.sql`

Das Skript laeuft `docker compose -f $COMPOSE_FILE up -d db` — deshalb muss
`docker-compose.yml` im aktuellen Verzeichnis liegen. Idealerweise startest du
den Restore in `screen`/`tmux`:

```bash
screen -S restore
COMPOSE_FILE=docker-compose.yml DELETE_DUMPS_AFTER_RESTORE=1 \
    ./restore_split_dump.sh /home/ben/ti_radar_dump_2026-04-08
# Ctrl+A, D zum Detachen, "screen -r restore" zum Wiederanhaengen
```

### 6. Restlichen Stack hochfahren

Nach erfolgreichem Restore (ca. 7–9 Stunden bei 156 M Patents) kann der
Rest der Services gestartet werden:

```bash
# Scheduler wieder aktivieren
sed -i 's/^SCHEDULER_ENABLED=false/SCHEDULER_ENABLED=true/' .env

# Alle Services ziehen + starten
docker compose --env-file .env pull
docker compose --env-file .env up -d
```

### 7. Health Check

```bash
sleep 30
curl http://localhost:8000/health | python3 -m json.tool
curl "http://localhost:8000/health?deep=true" | python3 -m json.tool
curl -I http://localhost:3000
```

Unter der Server-IP erreichbar:
- Port 3000 — Frontend
- Port 8000 — API
- Port 8000/docs — Swagger

**Einschraenkung:** Das Monitoring-Profil (`prometheus` + `grafana`) benoetigt
zusaetzlich die Dateien unter `deploy/infra/prometheus/prometheus.yml` und
`deploy/infra/grafana/*`. Diese sind NICHT im Image. Wenn du Monitoring
willst, musst du diese Dateien entweder manuell anlegen oder das `infra/`-
Verzeichnis aus GitHub einzeln per `curl` laden:

```bash
mkdir -p infra/prometheus infra/grafana/dashboards infra/grafana/provisioning
curl -o infra/prometheus/prometheus.yml \
    https://raw.githubusercontent.com/KingdaKilla/TI-Radarv3.0/master/deploy/infra/prometheus/prometheus.yml
# ... analog fuer grafana-Dateien
```

Danach `docker compose --profile monitoring up -d`.

### Updates auf eine neue Version

```bash
cd ~/ti-radar

# Neues DB-Image ziehen (enthaelt ggf. aktualisierte Skripte)
docker pull ghcr.io/kingdakilla/ti-radar-db:latest

# Neue Bash-Wrapper aus dem Image extrahieren (ueberschreiben die alten)
docker create --name ti-radar-extract ghcr.io/kingdakilla/ti-radar-db:latest
docker cp ti-radar-extract:/opt/restore/restore_split_dump.sh ./restore_split_dump.sh
docker rm ti-radar-extract
chmod +x restore_split_dump.sh

# Optional: auch die Compose-Vorlage aus GitHub refreshen (selten noetig)
# curl -fsSL -o docker-compose.yml \
#     https://raw.githubusercontent.com/KingdaKilla/TI-Radarv3.0/master/deploy/docker-compose.server.yml

# Alle Images refreshen und Services neu starten
docker compose --env-file .env pull
docker compose --env-file .env up -d
```

Deine `.env`, dein `docker-compose.yml` und deine Dump-Dateien bleiben
unangetastet.

---

## Split-Dump Backup & Restore (Production-Grade)

Fuer den produktiven Datenaustausch zwischen Entwicklungs- und Zielumgebung
steht ein partitionierter Split-Dump-Workflow zur Verfuegung. Er ist dem
monolithischen `pg_dump` vorzuziehen, weil einzelne Patent-Dekaden individuell
kopiert, geprueft und ggf. neu uebertragen werden koennen.

### Dump erstellen

```bash
# Erzeugt D:\ti_radar_dump_YYYY-MM-DD\ mit 29 Dateien (~73 GB bei voller DB)
./database/create_split_dump.sh
```

**Struktur des Dump-Verzeichnisses:**

```
ti_radar_dump_YYYY-MM-DD/
├── 00_schema_only.sql                  # DDL (Schema, Partitions, Indexe, MVs)
├── cordis_schema.backup                # data-only, custom format
├── cross_schema.backup                 # data-only (document_chunks + MVs)
├── entity_schema.backup
├── export_schema.backup
├── research_schema.backup
├── dump.sha256                         # sha256sum fuer jede Datei
└── patent_schema/
    ├── patents_pre1980.backup          # Patent-Dekaden (data-only)
    ├── patents_1980s.backup
    ├── patents_1990s.backup
    ├── patents_2000s.backup
    ├── patents_2010s.backup
    ├── patents_2020s.backup
    ├── patent_cpc_pre1980.backup       # Junction-Partitionen (data-only)
    ├── ... (weitere Junction-Partitionen)
    ├── applicants.backup
    └── cpc_descriptions.backup
```

Das Skript schreibt jede Datei zunaechst nach `/tmp/dump_split/` **im
Container**, kopiert sie sofort nach Host und loescht die Container-Version
(pro-Datei copy+delete). Dadurch bleibt der Container-Tempspace auf maximal
eine Datei begrenzt -- wichtig unter Docker Desktop/Windows, wo die dynamisch
wachsende VHDX sonst C: vollschreibt.

**Windows-Besonderheit:** Das Skript setzt intern `MSYS_NO_PATHCONV=1` und
nutzt `cygpath -m` fuer die `docker cp`-Destinations, weil Git Bash POSIX-
Pfade wie `/d/...` sonst falsch zu `C:\d\...` konvertiert.

### Transfer zum Server

```bash
# z.B. via SFTP
sftp user@server
sftp> mkdir ti_radar_dump_YYYY-MM-DD
sftp> put -r ti_radar_dump_YYYY-MM-DD
```

Nach dem Transfer die Checksums auf dem Server verifizieren:

```bash
ssh user@server 'cd ti_radar_dump_YYYY-MM-DD && sha256sum -c dump.sha256'
```

Jede Datei muss `OK` zeigen. Bei Fehlern: gezielt die betroffene Datei neu
uebertragen.

### Restore auf dem Zielserver

```bash
# Voraussetzung: Repo geclonet, Docker Compose gestartet (db-Container laeuft)
cd /pfad/zu/TI-Radarv3.0
./database/restore_split_dump.sh /pfad/zu/ti_radar_dump_YYYY-MM-DD
```

Das Skript liest zwei optionale Environment-Variablen:

| Variable | Default | Beschreibung |
|---|---|---|
| `COMPOSE_FILE` | `deploy/docker-compose.yml` | Compose-File fuer den `docker compose up -d db` Aufruf in Phase `[1/9]`. Auf dem Server `deploy/docker-compose.server.yml` setzen. |
| `DELETE_DUMPS_AFTER_RESTORE` | `0` | Wenn `1`, wird jede `.backup`-Datei auf dem Host sofort nach ihrem erfolgreichen `pg_restore` geloescht (pro-Datei Platzsparen). `00_schema_only.sql` und `dump.sha256` bleiben erhalten. **Destruktiv** -- nach Abbruch ist kein Retry ohne erneuten Dump-Transfer moeglich. |

**Aufruf auf knappem Plattenplatz** (z.B. 400 GB Server mit 73 GB Dump + ~400 GB DB):

```bash
COMPOSE_FILE=deploy/docker-compose.server.yml \
DELETE_DUMPS_AFTER_RESTORE=1 \
    ./database/restore_split_dump.sh /home/ben/ti_radar_dump_YYYY-MM-DD
```

Mit `DELETE_DUMPS_AFTER_RESTORE=1` verlaeuft der Speicherbedarf so:
- **Peak waehrend eines Restores**: max 2x Dateigroesse (Host-Datei + Container-Kopie) + DB-Wachstum
- **Nach jedem Restore**: die Host-Datei wird frei, Peak sinkt bis zum naechsten Restore
- **Kritische Phase**: `patents_2010s.backup` (20 GB -> ~100 GB DB) und `cross_schema.backup` (37 GB -> ~65 GB DB) brauchen temporaer ~140 GB bzw. ~102 GB freien Speicher

`pg_restore` Exit-Code wird streng geprueft: rc=0 (Erfolg) und rc=1 (Warnings wie "already exists") fuehren zum Loeschen; rc>1 (fataler Fehler) bricht das Skript ab, der Host-Dump bleibt fuer einen Retry erhalten.

Das Skript laeuft in 9 Phasen:

| Phase | Beschreibung |
|---|---|
| `[1/9]` | DB-Container starten, Ready-Check |
| `[2/9]` | Postgres Performance-Tuning fuer Import (`max_wal_size=10GB`, `fsync=off`, `synchronous_commit=off`, `autovacuum=off`) |
| `[3/9]` | Alle Tabellen leeren, Sequenzen zuruecksetzen, `document_chunks.embedding` von vector(384) auf vector(1024) anpassen |
| `[4/9]` | Nicht-Patent-Schemas restaurieren (cordis, research, entity, export, cross) |
| `[5/9]` | Patent-Schema Referenztabellen (applicants, cpc_descriptions, citations, metadata, enrichment_progress) |
| `[6/9]` | Patent-Dekaden restaurieren (pre1980 bis 2020s) -- laengste Phase |
| `[7/9]` | **Junction-Tabellen ableiten** aus denormalisierten `patents.cpc_codes` / `applicant_names` (idempotent, siehe DATENMODELL.md) |
| `[8/9]` | Materialized Views refreshen (`REFRESH CONCURRENTLY` mit `statement_timeout=0`) |
| `[9/9]` | Performance-Settings zuruecksetzen, Container-Restart |

Phase `[7/9]` laeuft das Skript `database/sql/seed_junctions_production.sql`
aus. Es ist idempotent (alle INSERTs mit `ON CONFLICT DO NOTHING`) und kann
gefahrlos erneut ausgefuehrt werden, wenn das Restore unterbrochen wird. Auf
dem DB-Image ist das Skript zusaetzlich unter `/opt/restore/
seed_junctions_production.sql` eingebacken, sodass Phase `[7/9]` auch ohne
Repo-Checkout funktioniert.

**Geschaetzte Gesamtzeit fuer einen vollen Restore (156M Patents):**
- Patent-Dekaden-Restore: 2-3 Stunden
- Junction-Derivation: 4-5 Stunden (primaer 2010s/2020s Decades)
- MV-Refresh: 30-60 Minuten
- **Total: ca. 7-9 Stunden**

### Automatische Junction-Ableitung nach Imports

Ausserhalb von Restores sorgt der **Scheduler** (`services/import-svc/src/
scheduler.py`) dafuer, dass nach jedem woechentlichen EPO-Bulk-Import die
Junction-Derivation ueber `junction_deriver.derive_junctions()` laeuft. Fuer
den manuellen Einsatz gegen eine laufende DB:

```bash
docker cp database/sql/seed_junctions_production.sql \
  ti-radar-db:/tmp/seed_junctions_production.sql
docker exec ti-radar-db psql -U tip_admin -d ti_radar \
  -f /tmp/seed_junctions_production.sql
```

Oder, wenn das Skript im Image liegt:

```bash
docker exec ti-radar-db psql -U tip_admin -d ti_radar \
  -f /opt/restore/seed_junctions_production.sql
```

## Auto-Seeding (Demo-Daten)

Beim ersten `docker compose up` werden automatisch CORDIS-Demo-Daten geladen. Dies ermöglicht eine funktionsfähige Demo-Umgebung ohne manuellen Import.

| Datensatz | Anzahl |
|---|---|
| Projekte | 4.815 |
| Organisationen | 4.034 |
| Publikationen | 17.900 |
| EuroSciVoc-Einträge | 1.062 |

Nach dem Seed-Vorgang werden die Materialized Views automatisch aktualisiert. Der gesamte Prozess läuft im Hintergrund ab und erfordert keinen Benutzereingriff.

## CI/CD & Container Registry

Docker-Images werden über GitHub Actions automatisch gebaut und in der GitHub Container Registry veröffentlicht:

- **Registry:** `ghcr.io/kingdakilla/ti-radar-*`
- **Images:** 18 Docker-Images (17 Service-Images + 1 Datenbank-Image `ti-radar-db`)
- **Trigger:** Versionstags (`v*`), z. B. `v3.0.0`
- **Nutzung vorgefertigter Images:** Statt lokal zu bauen, können die Images direkt aus GHCR gezogen werden:

```bash
docker pull ghcr.io/kingdakilla/ti-radar-orchestrator:latest
docker pull ghcr.io/kingdakilla/ti-radar-frontend:latest
# ... analog für alle weiteren Services
```

## Secret Management

| Umgebung | Methode |
|---|---|
| Lokale Entwicklung | `.env`-Datei (siehe Abschnitt Umgebungskonfiguration) |
| CI/CD (GitHub Actions) | GitHub Actions Secrets & Variables (automatisch injiziert) |

Für den produktiven Betrieb werden Secrets ausschließlich über GitHub Actions Secrets verwaltet. Lokale `.env`-Dateien dürfen nicht ins Repository eingecheckt werden (`.gitignore`).

## API-Caching

Externe API-Antworten werden in der Datenbank zwischengespeichert, um Rate-Limits einzuhalten und die Antwortzeiten zu verbessern:

| API | Cache-Tabelle | TTL |
|---|---|---|
| OpenAIRE | `research_schema.openaire_cache` | 7 Tage |
| Semantic Scholar | `research_schema.papers` | 30 Tage |

Abgelaufene Cache-Einträge werden bei der nächsten Abfrage automatisch aktualisiert.

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

## Service-Übersicht

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

Docker Desktop unter Windows kann instabil werden. Lösung:

1. Alle Docker-Prozesse im Task-Manager beenden
2. WSL herunterfahren: `wsl --shutdown`
3. Docker Desktop manuell neu starten

### Datenbank-Verbindung fehlgeschlagen

```bash
# Prüfen ob DB-Container läuft
docker ps | grep ti-radar-db

# Manuell testen
docker exec -i ti-radar-db psql -U tip_admin -d ti_radar -c "SELECT 1"

# Logs prüfen
docker logs ti-radar-db --tail 50
```

### Port-Konflikte

Falls Port 5432 bereits belegt ist (lokale PostgreSQL-Installation):

```bash
# Prüfen welcher Prozess den Port belegt
# Windows:
netstat -ano | findstr :5432
# Linux:
ss -tlnp | grep 5432
```

Die Datenbank ist nur auf `127.0.0.1:5432` gebunden. Bei Konflikten kann der Port in `docker-compose.yml` geändert werden.

### UC-Service antwortet nicht

```bash
# Deep Health Check: alle Services prüfen
curl http://localhost:8000/health?deep=true | python -m json.tool

# Logs eines bestimmten Service prüfen
docker logs ti-radar-uc1 --tail 50
```

### Datenbank-Volume zurücksetzen

Falls die Datenbank komplett neu aufgesetzt werden soll:

```bash
docker compose -f deploy/docker-compose.yml --env-file .env down -v
docker compose -f deploy/docker-compose.yml --env-file .env up -d
```

Das `-v` Flag löscht das Volume. Beim nächsten Start werden Schema und Demodaten neu angelegt.

### Fehlende DB-Berechtigungen nach Dump-Restore (permission denied)

Nach dem Restore eines Split-Dumps fehlen haeufig die GRANT-Statements fuer die
Service-Rollen (`svc_patent_grant`, `svc_tech_cluster`, `svc_euroscivoc`,
`svc_research_impact`, `svc_export`). In den Logs erscheint dann
`permission denied for table patents` bzw. `permission denied for schema ...`.

Ursache: `pg_dump` ohne `--no-acl` sichert die Grants **auf Objekten die im
Dump enthalten sind**, aber Service-Rollen, die spaeter per Migration
hinzukamen (UC7/UC9/UC10/UC12), verlieren ihre Privilegien beim Restore.

Hotfix als `tip_admin` auf dem laufenden Container anwenden:

```bash
docker exec -i ti-radar-db psql -U tip_admin -d ti_radar < database/sql/fix_grants.sql
```

Das Skript ist idempotent und kann mehrfach ausgefuehrt werden. Es re-granted
USAGE auf alle Schemas und SELECT auf alle Tabellen fuer alle 13 Service-
Rollen. Details siehe `database/sql/fix_grants.sql`.

### Orchestrator crasht mit `NameError: Fields must not use names with leading underscores`

Pydantic v2 verbietet Feldnamen mit fuehrendem Underscore. Der Fehler wurde
in `v3.3.2` behoben (HATEOAS-Feld `_links` → `links` mit Alias, sodass
JSON-Ausgabe unveraendert bleibt). Upgrade auf `v3.3.2` oder hoeher via:

```bash
docker compose --env-file .env pull orchestrator-svc
docker compose --env-file .env up -d orchestrator-svc
```

### Export-Service loggt `permission denied for schema export_schema`

Der Export-Service versucht beim Startup `CREATE SCHEMA IF NOT EXISTS
export_schema` auszufuehren. Die Service-Rolle `svc_export` hat aber kein
`CREATE`-Recht auf der Datenbank. Seit `v3.3.2` faengt der Service den
Fehler ab und faehrt weiter (Schema existiert bereits aus `002_schema.sql`).

Die Warnung `export_schema_fehler` ist kosmetisch, solange `fix_grants.sql`
ausgefuehrt wurde. Caching bleibt nutzbar.

### UC8 Temporal: `function unnest(text) does not exist`

Behoben in `v3.3.4`. Die Spalte `patents.applicant_names` ist ein
Semikolon-getrennter `TEXT`-String, kein `TEXT[]`-Array. Der Temporal-
Service nutzte faelschlicherweise `unnest()` statt `string_to_table(...,
'; ')`. Upgrade auf `v3.3.4` oder hoeher.

### Orchestrator-Suggestions: `relation "patents" does not exist`

Behoben in `v3.3.4`. Der Autocomplete-Endpoint hatte die Tabellenreferenzen
`patents` und `projects` ohne Schema-Prefix. Korrigiert zu
`patent_schema.patents` und `cordis_schema.projects`.

### UC11 Actor-Type: `column "entity_status" does not exist`

Behoben in `v3.3.3`. Der GLEIF-Adapter referenzierte eine Spalte
`entity_status`, die tatsaechliche Spalte in `entity_schema.gleif_cache`
heisst `registration_status`. Umbenannt in allen SQL-Queries und der
`GLEIFResult`-Dataclass.

### GLEIF API 404 (fuzzy-completions)

Die URL `https://api.gleif.org/api/v1/fuzzy-completions` liefert derzeit 404.
Der Actor-Type-Service faengt den Fehler graceful ab und nutzt stale Cache
als Fallback. Eine Anpassung auf den aktuellen GLEIF-API-Endpoint steht
noch aus — LEI-Anreicherung ist waehrenddessen optional.

### OpenAIRE 403 Forbidden

Der OpenAIRE-Access-Token in `.env` kann ablaufen (Hinweis
`openaire_token_refresh_fehlgeschlagen` im UC1-Log). Siehe
[OpenAIRE-Token erneuern](#openaire-token-erneuern).

UC1 faellt bei ungueltigem Token automatisch auf die CORDIS-Zeitreihen
zurueck. Ab Version `v3.3.5` wird nur noch eine einzige Warning geloggt;
die nachfolgende 403-Kaskade (22+ Zeilen pro Analyse) laeuft auf
`debug`-Level, bis der naechste Refresh erfolgreich ist.

### OpenAIRE-Token erneuern

1. Einloggen auf <https://www.openaire.eu/user-management> (bzw. das
   Personal-Dashboard unter <https://graph.openaire.eu>) und unter
   **Personal Access Token** einen neuen **Refresh-Token** erzeugen.
   Der Token ist ueblicherweise 1 Jahr gueltig; der aus ihm abgeleitete
   Access-Token wird vom Adapter automatisch alle paar Stunden erneuert.
2. Werte in `.env` aktualisieren (nur `OPENAIRE_REFRESH_TOKEN` ist
   zwingend, `OPENAIRE_ACCESS_TOKEN` darf leer bleiben — der Adapter
   holt sich das Access-Token beim ersten Request selbst):

   ```env
   OPENAIRE_REFRESH_TOKEN=eyJhbGciOiJIUzI1...<neuer_token>
   OPENAIRE_ACCESS_TOKEN=
   ```

3. Nur den UC1-Landscape-Service neu starten (die Modul-Level-
   Token-Caches leben im Prozess):

   ```bash
   docker compose -f deploy/docker-compose.yml --env-file .env \
       up -d --force-recreate ti-radar-uc1
   ```

4. Im Log pruefen, dass der Refresh funktioniert. Erwartet wird genau
   eine `openaire_token_erneuert`-Zeile mit `gueltig_min`-Feld,
   *keine* `openaire_token_refresh_fehlgeschlagen`-Warnings mehr:

   ```bash
   docker compose logs ti-radar-uc1 --since 5m | \
       grep -E "openaire_token_(erneuert|refresh_fehlgeschlagen)"
   ```

   Zusaetzlicher Smoke-Test: einmal UC1 via Orchestrator ansprechen
   (z.B. Analyse "quantum computing" im Frontend starten) und im Log
   nach `openaire_request status=200` suchen. Bei Erfolg werden die
   Jahreszaehlungen wieder aus OpenAIRE geliefert statt aus dem
   CORDIS-Fallback.

Danach `docker compose restart landscape-svc`.
