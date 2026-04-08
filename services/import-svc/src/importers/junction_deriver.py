"""Junction-Derivation fuer patent_schema.

Leitet die Junction-Tabellen aus den denormalisierten Feldern der patents
Tabelle ab:

    patents.applicant_names (TEXT, ';'-separiert)
        -> patent_schema.applicants (DISTINCT raw_names)
        -> patent_schema.patent_applicants (N:M junction)

    patents.cpc_codes (TEXT[])
        -> patent_schema.patent_cpc (Jaccard junction, nur Patents mit >=2 CPCs)

Wird vom Scheduler nach jedem Bulk-Import (weekly_import_job) aufgerufen.
Idempotent durch ON CONFLICT DO NOTHING — kann gefahrlos re-run werden.

Die SQL-Logik ist identisch zu database/sql/seed_junctions_production.sql.
Hier als Python-embedded-SQL, damit der Scheduler unabhaengig vom
Filesystem-Pfad ist und auf asyncpg statt psql operiert.

Performance-Hinweis: Bei 156 M Patents dauert der Full-Scan der drei Stages
zusammen ~30-90 Minuten. Inkrementelle Ableitung (nur neue Patents via
Wasserstand-Marker) ist ein Follow-up — siehe TODO.md.
"""

from __future__ import annotations

import time
from typing import Any

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


# ----------------------------------------------------------------------------
# SQL Statements (identisch zu database/sql/seed_junctions_production.sql)
# ----------------------------------------------------------------------------

_STAGE_1_APPLICANTS = """
INSERT INTO patent_schema.applicants (raw_name, normalized_name)
SELECT DISTINCT
    trim(applicant_name)                                     AS raw_name,
    upper(regexp_replace(trim(applicant_name),
          '\\s+(GMBH|AG|SA|SAS|SRL|LTD|LLC|INC|CORP|BV|NV|SE|PLC|CO\\.)\\.?$',
          '', 'i'))                                          AS normalized_name
FROM patent_schema.patents p,
     LATERAL unnest(string_to_array(p.applicant_names, ';')) AS applicant_name
WHERE p.applicant_names IS NOT NULL
  AND trim(applicant_name) <> ''
ON CONFLICT (raw_name) DO NOTHING
"""

_STAGE_2_PATENT_APPLICANTS = """
INSERT INTO patent_schema.patent_applicants (patent_id, patent_year, applicant_id)
SELECT DISTINCT
    sub.patent_id,
    sub.patent_year,
    a.id
FROM (
    SELECT
        p.id                          AS patent_id,
        p.publication_year            AS patent_year,
        trim(applicant_name)          AS raw_name
    FROM patent_schema.patents p,
         LATERAL unnest(string_to_array(p.applicant_names, ';')) AS applicant_name
    WHERE p.applicant_names IS NOT NULL
      AND p.publication_year IS NOT NULL
      AND trim(applicant_name) <> ''
) sub
JOIN patent_schema.applicants a ON a.raw_name = sub.raw_name
ON CONFLICT DO NOTHING
"""

_STAGE_3_PATENT_CPC = """
INSERT INTO patent_schema.patent_cpc (patent_id, cpc_code, pub_year)
SELECT DISTINCT
    p.id                             AS patent_id,
    substring(code, 1, 4)           AS cpc_code,
    p.publication_year              AS pub_year
FROM patent_schema.patents p,
     LATERAL unnest(p.cpc_codes) AS code
WHERE p.cpc_codes IS NOT NULL
  AND array_length(p.cpc_codes, 1) >= 2
  AND p.publication_year IS NOT NULL
  AND substring(code, 1, 4) ~ '^[A-HY][0-9]{2}[A-Z]$'
ON CONFLICT DO NOTHING
"""

# Performance-Tuning-Statements, session-scoped.
# statement_timeout=0 deaktiviert das Production-Default-Limit (10 min),
# das fuer die langen Junction-Sort+Insert-Operationen zu klein ist.
_TUNING_ON = (
    "SET statement_timeout = 0",
    "SET idle_in_transaction_session_timeout = 0",
    "SET lock_timeout = 0",
    "SET work_mem = '512MB'",
    "SET maintenance_work_mem = '2GB'",
    "SET synchronous_commit = OFF",
    "SET temp_buffers = '256MB'",
)
_TUNING_OFF = (
    "RESET statement_timeout",
    "RESET idle_in_transaction_session_timeout",
    "RESET lock_timeout",
    "RESET work_mem",
    "RESET maintenance_work_mem",
    "RESET synchronous_commit",
    "RESET temp_buffers",
)


async def derive_junctions(pool: asyncpg.Pool) -> dict[str, Any]:
    """Junction-Tabellen aus denormalisierten Patent-Daten ableiten.

    Fuehrt drei Stages sequenziell aus:
      1. patent_schema.applicants (DISTINCT aus patents.applicant_names)
      2. patent_schema.patent_applicants (N:M junction)
      3. patent_schema.patent_cpc (Jaccard junction)

    Jede Stage ist eine eigene Query, die asyncpg implizit als eigene
    Transaction ausfuehrt. Kein Wrap in BEGIN/COMMIT, damit wir nicht in
    die MV-Refresh-Falle laufen.

    Performance-Tuning (work_mem, synchronous_commit, temp_buffers) wird
    session-scoped gesetzt und am Ende zurueckgesetzt.

    Args:
        pool: Aktiver asyncpg-Pool zur Produktiv-DB.

    Returns:
        Stats-Dict mit Dauer pro Stage und resultierenden Row-Counts.
    """
    stats: dict[str, Any] = {}
    t_total = time.monotonic()

    async with pool.acquire() as conn:
        # Session-Tuning aktivieren
        for stmt in _TUNING_ON:
            await conn.execute(stmt)

        try:
            # Stage 1: applicants
            t0 = time.monotonic()
            result_1 = await conn.execute(_STAGE_1_APPLICANTS)
            stats["stage_1_applicants_duration_s"] = round(time.monotonic() - t0, 1)
            stats["stage_1_applicants_result"] = result_1
            logger.info(
                "junction_deriver_stage_1_ok",
                duration_s=stats["stage_1_applicants_duration_s"],
                result=result_1,
            )

            # Stage 2: patent_applicants
            t0 = time.monotonic()
            result_2 = await conn.execute(_STAGE_2_PATENT_APPLICANTS)
            stats["stage_2_patent_applicants_duration_s"] = round(
                time.monotonic() - t0, 1
            )
            stats["stage_2_patent_applicants_result"] = result_2
            logger.info(
                "junction_deriver_stage_2_ok",
                duration_s=stats["stage_2_patent_applicants_duration_s"],
                result=result_2,
            )

            # Stage 3: patent_cpc
            t0 = time.monotonic()
            result_3 = await conn.execute(_STAGE_3_PATENT_CPC)
            stats["stage_3_patent_cpc_duration_s"] = round(time.monotonic() - t0, 1)
            stats["stage_3_patent_cpc_result"] = result_3
            logger.info(
                "junction_deriver_stage_3_ok",
                duration_s=stats["stage_3_patent_cpc_duration_s"],
                result=result_3,
            )

            # Row counts (fuer Log + stats dict)
            row = await conn.fetchrow(
                "SELECT "
                "(SELECT COUNT(*) FROM patent_schema.applicants)         AS applicants, "
                "(SELECT COUNT(*) FROM patent_schema.patent_applicants)  AS patent_applicants, "
                "(SELECT COUNT(*) FROM patent_schema.patent_cpc)         AS patent_cpc"
            )
            stats["row_counts"] = dict(row) if row else {}

        finally:
            # Tuning zuruecksetzen — auch bei Fehler
            for stmt in _TUNING_OFF:
                try:
                    await conn.execute(stmt)
                except Exception as exc:
                    logger.warning(
                        "junction_deriver_reset_fehler", stmt=stmt, error=str(exc)
                    )

    stats["total_duration_s"] = round(time.monotonic() - t_total, 1)
    logger.info(
        "junction_deriver_abgeschlossen",
        total_duration_s=stats["total_duration_s"],
        row_counts=stats.get("row_counts"),
    )
    return stats
