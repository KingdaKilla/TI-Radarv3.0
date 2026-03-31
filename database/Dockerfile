FROM pgvector/pgvector:pg17

# Initialisierungsskripte in den PostgreSQL-Entrypoint kopieren
COPY database/sql/001_extensions.sql        /docker-entrypoint-initdb.d/
COPY database/sql/002_schema.sql            /docker-entrypoint-initdb.d/
COPY database/sql/003_postgresql_tuning.sql /docker-entrypoint-initdb.d/
COPY database/sql/004_query_translation.sql /docker-entrypoint-initdb.d/
COPY database/sql/005_import_log.sql        /docker-entrypoint-initdb.d/
COPY database/sql/006_citation_schema.sql   /docker-entrypoint-initdb.d/
COPY database/sql/007_publication_role.sql   /docker-entrypoint-initdb.d/
COPY database/sql/008_seed_cordis.sh        /docker-entrypoint-initdb.d/
COPY database/sql/009_api_cache.sql         /docker-entrypoint-initdb.d/
COPY database/sql/010_fix_vector_dims_and_missing_tables.sql /docker-entrypoint-initdb.d/
COPY database/mock_data/                    /docker-entrypoint-initdb.d/mock_data/

RUN chmod +x /docker-entrypoint-initdb.d/008_seed_cordis.sh
