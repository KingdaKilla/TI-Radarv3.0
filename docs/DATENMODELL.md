# Datenmodell

## Uebersicht

TI-Radar nutzt eine einzelne PostgreSQL-17-Instanz mit 6 isolierten Schemas. Die Datenbank enthaelt ca. 555M Zeilen bei einer Gesamtgroesse von ~590 GB. Fuer Vektoraehnlichkeitssuche ist pgvector installiert, fuer unscharfe Textsuche pg_trgm.

## Datenquellen

| Quelle | Beschreibung | Volumen | Schema |
|---|---|---|---|
| EPO DOCDB | Europaeisches Patentamt, weltweite Patentpublikationen | 154.8M Patente | `patent_schema` |
| CORDIS | EU-Forschungsprojekte (FP7, H2020, Horizon Europe) | 80.5K Projekte, 438K Organisationen, 529K Publikationen | `cordis_schema` |
| OpenAIRE | Open-Access-Publikationen | via API | `research_schema` |
| Semantic Scholar | Zitations- und Autorendaten | Cache-basiert | `research_schema` |
| GLEIF | Legal Entity Identifier fuer Akteurs-Matching | Cache | `entity_schema` |

## Datenbankschemas

### patent_schema

EPO-Patentdaten und patentspezifische Analysen. Genutzt von: UC2 (Maturity), UC5 (CPC-Flow), UC12 (Patent-Grant).

| Tabelle | Zeilen | Beschreibung |
|---|---|---|
| `patents` | 154.8M | Haupttabelle, range-partitioned nach `publication_year` |
| `applicants` | 15.5M | Normalisierte Patentanmelder |
| `patent_applicants` | 147M | N:M-Zuordnung Patent-Anmelder, co-partitioned |
| `patent_cpc` | 237M | N:M-Zuordnung Patent-CPC-Klasse, co-partitioned |
| `cpc_descriptions` | ~670 | CPC-Subclass-Beschreibungen (Referenzdaten) |
| `import_metadata` | variabel | Tracking verarbeiteter EPO-DOCDB-ZIP-Dateien |

**Design-Entscheidungen:**
- Range-Partitionierung nach `publication_year`: Partition Pruning eliminiert ganze Dekaden
- BRIN-Indexe auf Datumsspalten (100-1000x kleiner als B-Tree)
- tsvector-Spalten mit GIN-Index ersetzen SQLite FTS5
- TEXT[]-Arrays mit GIN-Index fuer Laender- und CPC-Abfragen

### cordis_schema

CORDIS-EU-Forschungsprojektdaten. Genutzt von: UC4 (Funding), UC11 (Actor-Type), UC10 (EuroSciVoc).

| Tabelle | Zeilen | Beschreibung |
|---|---|---|
| `projects` | 80.5K | EU-Forschungsprojekte (FP7, H2020, HORIZON) |
| `organizations` | 438K | Projektbeteiligte mit Typ (HES, PRC, REC, PUB, OTH) |
| `publications` | 529K | Projektpublikationen mit DOI-Deduplizierung |
| `euroscivoc` | ~220K | EuroSciVoc-Taxonomie (hierarchisch, self-referencing) |
| `project_euroscivoc` | variabel | Zuordnung Projekte zu EuroSciVoc-Kategorien |
| `import_metadata` | variabel | Tracking verarbeiteter CORDIS-Dateien |

### research_schema

Semantic-Scholar-Cache fuer Forschungswirkungsanalyse. Genutzt von: UC7 (Research-Impact).

| Tabelle | Beschreibung |
|---|---|
| `papers` | Gecachte Paper-Metadaten (Zitationen, Venue, Open Access) |
| `authors` | Gecachte Autorendaten (h-Index, Affiliations) |
| `paper_authors` | N:M-Zuordnung Paper-Autoren |

- 30-Tage-TTL: Daten werden nach Ablauf von `stale_after` neu abgerufen

### entity_schema

Entity Resolution fuer quellenuebergreifendes Akteurs-Matching (EPO + CORDIS + GLEIF).

| Tabelle | Zeilen | Beschreibung |
|---|---|---|
| `unified_actors` | 129.8K | Vereinheitlichte Akteure mit UUID |
| `actor_source_mappings` | variabel | Zuordnung zu Quellsystem-IDs |
| `gleif_cache` | variabel | GLEIF Legal Entity Identifier Cache |
| `resolution_runs` | variabel | Audit-Log der Entity-Resolution-Laeufe |

- pg_trgm Fuzzy-Matching fuer Namensabgleich

### cross_schema

Quellenuebergreifende Materialized Views fuer OLAP-Analysen. Genutzt von: UC1 (Landscape), UC3 (Competitive), UC6 (Geographic), UC8 (Temporal).

| Materialized View | Beschreibung |
|---|---|
| `mv_patent_counts_by_cpc_year` | Patentanzahl pro CPC-Klasse und Jahr |
| `mv_cpc_cooccurrence` | CPC-Paar-Kookkurrenz (Jaccard-Koeffizienten) |
| `mv_yearly_tech_counts` | Jaehrliche Technologie-Zaehler (Patent + Projekt) |
| `mv_top_applicants` | Top-Patentanmelder mit Jahresverteilung |
| `mv_patent_country_distribution` | Laenderverteilung der Patente |
| `mv_project_counts_by_year` | CORDIS-Projekte pro Jahr |
| `mv_cordis_country_pairs` | Laenderpaare in CORDIS-Kooperationen |
| `mv_top_cordis_orgs` | Top-Organisationen in CORDIS |
| `mv_funding_by_instrument` | Foerdervolumen pro Instrument und Jahr |

Refresh: `REFRESH MATERIALIZED VIEW CONCURRENTLY` via Datenbank-Funktionen nach jedem Bulk-Import.

### export_schema

Export-Service-Cache und Report-Templates. Genutzt von: Export-Service.

| Tabelle | Beschreibung |
|---|---|
| `analysis_cache` | Gecachte Analyseergebnisse (JSON) |
| `report_templates` | Vorlagen fuer PDF/CSV-Reports |
| `export_log` | Audit-Log der Exporte |

## ER-Diagramm (vereinfacht)

```mermaid
erDiagram
    patents ||--o{ patent_applicants : "hat"
    patents ||--o{ patent_cpc : "hat"
    applicants ||--o{ patent_applicants : "ist"
    cpc_descriptions ||--o{ patent_cpc : "beschreibt"

    projects ||--o{ organizations : "beteiligt"
    projects ||--o{ publications : "produziert"
    projects ||--o{ project_euroscivoc : "klassifiziert"
    euroscivoc ||--o{ project_euroscivoc : "ist"
    euroscivoc ||--o| euroscivoc : "parent"

    papers ||--o{ paper_authors : "hat"
    authors ||--o{ paper_authors : "ist"

    unified_actors ||--o{ actor_source_mappings : "hat"

    patents {
        bigint id PK
        text publication_number
        char country
        text title
        date publication_date
        smallint publication_year
        text family_id
        tsvector search_vector
    }

    projects {
        int id PK
        varchar framework
        text title
        text objective
        numeric total_cost
        numeric ec_max_contribution
        varchar funding_scheme
        tsvector search_vector
    }

    organizations {
        int id PK
        int project_id FK
        text name
        char country
        varchar activity_type
        boolean sme
    }

    unified_actors {
        uuid id PK
        text canonical_name
        varchar actor_type
        char primary_country
    }
```

## Indexierungsstrategie

| Index-Typ | Einsatz | Vorteil |
|---|---|---|
| BRIN | Datumsspalten (publication_date, start_date) | 100-1000x kleiner als B-Tree bei chronologisch importierten Daten |
| GIN (tsvector) | Volltextsuche auf Titeln und Beschreibungen | Ersetzt SQLite FTS5, unterstuetzt gewichtete Suche |
| GIN (pg_trgm) | Fuzzy-Suche und Autocomplete | Trigramm-basiert, toleriert Tippfehler |
| GIN (Array) | TEXT[]-Spalten (applicant_countries, cpc_codes) | Containment-Operatoren (@>, &&) statt LIKE-Scans |
| B-Tree | Fremdschluessel, Family-IDs | Standard-Lookups |
