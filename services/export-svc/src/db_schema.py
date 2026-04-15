"""Schema-Bootstrap fuer den Export-Service.

Stellt sicher, dass `export_schema` mit `analysis_cache` und `export_log`
existiert. **Read-first**-Strategie: vor jeder DDL wird via
`information_schema` geprueft, ob das Objekt bereits existiert. Nur dann,
wenn es wirklich fehlt, wird ein CREATE versucht.

Hintergrund: Im Production-Deploy stammt das Schema aus
`database/sql/002_schema.sql` (vom DB-Init). `svc_export` hat dort USAGE
+ DML, aber **kein OWNER**-Recht. Ein blindes `CREATE TABLE IF NOT EXISTS`
loest in PostgreSQL trotzdem einen ERROR-Eintrag im DB-Log aus
("permission denied" / "must be owner"), weil der Server zwar nichts tut,
aber die Anfrage prueft. Dieser Modul-Pfad vermeidet das.

Reine Funktionen ohne FastAPI/uvicorn-Abhaengigkeit, damit isoliert
testbar.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# DDL-Definitionen als Modul-Konstanten — testbar referenzierbar.
DDL_TABLE_ANALYSIS_CACHE = """
    CREATE TABLE export_schema.analysis_cache (
        id              BIGSERIAL PRIMARY KEY,
        cache_key       TEXT UNIQUE NOT NULL,
        technology      TEXT NOT NULL,
        start_year      INTEGER NOT NULL,
        end_year        INTEGER NOT NULL,
        european_only   BOOLEAN NOT NULL DEFAULT FALSE,
        use_cases       TEXT[] NOT NULL DEFAULT '{}',
        result_json     JSONB NOT NULL,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        expires_at      TIMESTAMPTZ NOT NULL
    );
"""

DDL_TABLE_EXPORT_LOG = """
    CREATE TABLE export_schema.export_log (
        id              BIGSERIAL PRIMARY KEY,
        technology      TEXT NOT NULL,
        export_format   TEXT NOT NULL,
        use_cases       TEXT[] NOT NULL DEFAULT '{}',
        row_count       INTEGER NOT NULL DEFAULT 0,
        file_size_bytes BIGINT NOT NULL DEFAULT 0,
        duration_ms     INTEGER NOT NULL DEFAULT 0,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        client_ip       TEXT DEFAULT '',
        request_id      TEXT DEFAULT ''
    );
"""

DDL_INDEX_CACHE_KEY = (
    "CREATE INDEX idx_cache_key "
    "ON export_schema.analysis_cache (cache_key);"
)

DDL_INDEX_CACHE_EXPIRES = (
    "CREATE INDEX idx_cache_expires "
    "ON export_schema.analysis_cache (expires_at);"
)


async def ensure_schema(pool: Any) -> None:
    """Stellt sicher, dass export_schema + Tabellen existieren — ohne DB-Log-Spam.

    Args:
        pool: asyncpg.Pool-aehnliches Objekt mit `.acquire()`-Context-Manager.
    """
    async with pool.acquire() as conn:
        # 1. Schema existiert?
        schema_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.schemata "
            "WHERE schema_name = 'export_schema')"
        )

        if not schema_exists:
            try:
                await conn.execute("CREATE SCHEMA export_schema;")
                logger.info("export_schema_erstellt")
            except Exception as exc:
                logger.warning(
                    "export_schema_create_fehlgeschlagen",
                    reason=str(exc),
                    hint="DB-Init-Skript hat das Schema nicht angelegt und "
                         "svc_export hat kein CREATE-Recht. Caching deaktiviert.",
                )
                return

        # 2. Welche Tabellen existieren?
        rows = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'export_schema'"
        )
        existing_tables: set[str] = {row["table_name"] for row in rows}

        # 3. analysis_cache (mit Indizes) — nur wenn Tabelle fehlt.
        # Wenn sie existiert (i.d.R. tip_admin owned), werden die Indizes
        # vom DB-Init bereits angelegt sein — wir versuchen sie nicht erneut.
        if "analysis_cache" not in existing_tables:
            try:
                await conn.execute(DDL_TABLE_ANALYSIS_CACHE)
                await conn.execute(DDL_INDEX_CACHE_KEY)
                await conn.execute(DDL_INDEX_CACHE_EXPIRES)
                logger.info("export_table_erstellt", table="analysis_cache")
            except Exception as exc:
                logger.warning(
                    "export_table_create_fehlgeschlagen",
                    table="analysis_cache",
                    reason=str(exc),
                )

        # 4. export_log analog
        if "export_log" not in existing_tables:
            try:
                await conn.execute(DDL_TABLE_EXPORT_LOG)
                logger.info("export_table_erstellt", table="export_log")
            except Exception as exc:
                logger.warning(
                    "export_table_create_fehlgeschlagen",
                    table="export_log",
                    reason=str(exc),
                )

        logger.info(
            "export_schema_check_abgeschlossen",
            existing_tables=sorted(existing_tables),
        )
