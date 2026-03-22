# Mock-Datenbank: Quantum Computing

Abgespeckte Datenbank mit allen Datensaetzen fuer die Technologie "quantum computing".
Dient als Demo-/Entwicklungsdatenbank ohne die vollstaendige 590 GB PostgreSQL.

## Inhalt

| Datei | Entitaet | Zeilen | Groesse |
|-------|----------|--------|---------|
| patents.csv | EPO-Patente | 6.019 | 1,7 MB |
| projects.csv | CORDIS-Projekte | 4.814 | 2,7 MB |
| organizations.csv | CORDIS-Organisationen | 4.034 | 455 KB |
| publications.csv | CORDIS-Publikationen | 17.900 | 9,3 MB |
| euroscivoc.csv | EuroSciVoc-Taxonomie | 1.062 | 55 KB |
| project_euroscivoc.csv | Projekt-EuroSciVoc-Zuordnungen | 3.249 | 39 KB |
| **Gesamt** | | **~37.000** | **~15 MB** |

## Nutzung

```bash
# Schema initialisieren (einmalig)
psql -U tip_admin -d ti_radar -f db/sql/001_extensions.sql
psql -U tip_admin -d ti_radar -f db/sql/002_schema.sql

# Mock-Daten laden
psql -U tip_admin -d ti_radar -f db/mock_data/seed_mock.sql
```

## Quelle

Extrahiert aus der produktiven TI-Radar v3 PostgreSQL-Datenbank am 2026-03-06.
Filter: `search_vector @@ plainto_tsquery('english', 'quantum computing')`
