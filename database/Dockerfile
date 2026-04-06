FROM pgvector/pgvector:pg17

# Schema-Initialisierung (nur bei erstem Start, alphabetische Reihenfolge)
COPY database/sql/001_extensions.sql        /docker-entrypoint-initdb.d/
COPY database/sql/002_schema.sql            /docker-entrypoint-initdb.d/
COPY database/sql/003_postgresql_tuning.sql /docker-entrypoint-initdb.d/

# Seed-Skripte: 100er-Nummern -> laufen nach Schema-Init
COPY database/sql/seed_mock.sh              /docker-entrypoint-initdb.d/100_seed_mock.sh
COPY database/sql/seed_junctions.sql        /docker-entrypoint-initdb.d/101_seed_junctions.sql
COPY database/mock_data/                    /docker-entrypoint-initdb.d/mock_data/

# Restore-Werkzeuge (nicht bei Init)
COPY database/sql/restore_dump.sql          /opt/restore/restore_dump.sql
COPY database/restore_on_server.sh          /opt/restore/restore_on_server.sh

RUN chmod +x /docker-entrypoint-initdb.d/100_seed_mock.sh \
    && chmod +x /opt/restore/restore_on_server.sh
