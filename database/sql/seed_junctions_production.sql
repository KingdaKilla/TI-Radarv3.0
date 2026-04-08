-- ============================================================================
-- seed_junctions_production.sql
--
-- Production-safe Variante von seed_junctions.sql: Leitet die Junction-
-- Tabellen (patent_schema.applicants, patent_applicants, patent_cpc) aus den
-- denormalisierten Feldern patents.applicant_names und patents.cpc_codes ab.
--
-- Unterschiede zu seed_junctions.sql (Mock-Version):
--
--   1. KEIN BEGIN/COMMIT-Wrapper. seed_junctions.sql hatte BEGIN..COMMIT mit
--      `REFRESH MATERIALIZED VIEW CONCURRENTLY` innerhalb — das verbietet
--      PostgreSQL explizit ("cannot run inside a transaction block"). Jeder
--      INSERT ist hier eine eigene implizite Transaktion (psql-autocommit).
--
--   2. Nur die drei Produktion-relevanten Patent-Stages (applicants,
--      patent_applicants, patent_cpc). Die Mock-spezifischen Stages fuer
--      CORDIS-unified_actors und research_schema.papers sind ausgeklammert.
--
--   3. Hardcoded-CPC-Description-Block weggelassen — cpc_descriptions ist
--      Production-seitig bereits mit echten Daten gefuellt.
--
--   4. Materialized-View-Refreshes sind in die separate Datei
--      refresh_cross_schema_mvs.sql ausgelagert und muessen NACH diesem
--      Skript ausgefuehrt werden.
--
--   5. Stage 1 (applicants) hat Skip-Logik: laeuft nur, wenn die Tabelle
--      noch unter 5 M Zeilen hat (Mock-Schwellwert). Bei einem Re-Run nach
--      bereits erfolgtem Stage 1 wird der teure DISTINCT-Scan uebersprungen.
--
--   6. Stage 2 (patent_applicants) und Stage 3 (patent_cpc) sind in DEKADEN
--      partitioniert (pre1980, 1980s, 1990s, 2000s, 2010s, 2020s). Ein
--      einzelner Lauf gegen die volle 156 M Patents Tabelle hatte bei Stage 2
--      nach 4+ Stunden noch keinen einzigen Commit produziert (riesiger
--      Sort+JOIN+Insert in einer Query). Per-Decade INSERTs reduzieren die
--      Sort-Groesse, erlauben Zwischen-Commits und sind resumable.
--
-- Design-Entscheidungen, die aus der Mock-Version uebernommen wurden:
--
--   a) Jaccard-Filter `array_length(cpc_codes, 1) >= 2` in Stage 3. Per
--      Schema-Kommentar ist das by design:
--      "Only patents with >= 2 distinct CPC codes are included
--       (Jaccard requires pairs)."
--
--   b) CPC-Regex '^[A-HY][0-9]{2}[A-Z]$' — strict 4-char subclass match,
--      konsistent mit dem Schema-Check-Constraint.
--
--   c) Alle INSERTs mit ON CONFLICT DO NOTHING — Skript ist idempotent und
--      kann gefahrlos re-run werden, falls es unterbrochen wurde.
--
-- Aufruf (manuell, einmalig nach einem Import):
--
--   docker cp database/sql/seed_junctions_production.sql \
--     ti-radar-db:/tmp/seed_junctions_production.sql
--   docker exec ti-radar-db psql -U tip_admin -d ti_radar \
--     -f /tmp/seed_junctions_production.sql
--
-- Anschliessend die Materialized Views refreshen:
--
--   docker cp database/sql/refresh_cross_schema_mvs.sql \
--     ti-radar-db:/tmp/refresh_cross_schema_mvs.sql
--   docker exec ti-radar-db psql -U tip_admin -d ti_radar \
--     -f /tmp/refresh_cross_schema_mvs.sql
--
-- ============================================================================

\echo ''
\echo '=== TI-Radar: Junction-Tabellen aus Patents ableiten (production) ==='
\echo ''
\timing on

-- Defense in depth: beim ersten Fehler abbrechen, nicht weiterlaufen.
-- Ohne das marschiert psql -f durch alle Stages, auch wenn die erste
-- Stage abbricht (z.B. wegen statement_timeout), und erzeugt irrefuehrende
-- "fertig"-Zeilen.
\set ON_ERROR_STOP on

-- ---------------------------------------------------------------------------
-- Temporaeres Performance-Tuning fuer den aktuellen psql-Session
-- ---------------------------------------------------------------------------
-- Diese Settings gelten NUR fuer diese Session und werden am Ende
-- zurueckgesetzt. Sie beschleunigen grosse Bulk-Inserts durch groessere
-- Sort-Buffers und asynchrones Commit.
--
-- statement_timeout = 0 deaktiviert das (production-seitige) 10-Minuten-
-- Query-Limit fuer diese Session. Auch mit per-Decade-Splits kann eine
-- einzelne Decade (besonders 2010s mit ~50 M Patents) das Default-Limit
-- ueberschreiten.

SET statement_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET lock_timeout = 0;
SET work_mem = '512MB';
SET maintenance_work_mem = '2GB';
SET synchronous_commit = OFF;
SET temp_buffers = '256MB';

-- Pre-Check: Zeigt die aktuellen Row-Counts an, damit der Benutzer
-- VOR dem Lauf sieht, ob die Tabellen leer sind oder teilweise befuellt.
\echo ''
\echo '--- Vorher (Row-Counts) ---'
SELECT 'patents' AS tabelle, COUNT(*) AS zeilen FROM patent_schema.patents
UNION ALL
SELECT 'applicants',                      COUNT(*) FROM patent_schema.applicants
UNION ALL
SELECT 'patent_applicants',               COUNT(*) FROM patent_schema.patent_applicants
UNION ALL
SELECT 'patent_cpc',                      COUNT(*) FROM patent_schema.patent_cpc;


-- ============================================================================
-- Stage 1/3: patent_schema.applicants
-- ----------------------------------------------------------------------------
-- Extrahiert eindeutige Anmeldernamen aus dem denormalisierten Feld
-- patents.applicant_names (Semikolon-separiert).
--
-- Skip-Logik: Wenn die Tabelle bereits >= 5 M Zeilen hat, wird Stage 1
-- uebersprungen (Re-Run-safe). Mock-Daten-Stand ist << 5 M.
-- ============================================================================

\echo ''
\echo '[1/3] applicants aus patents.applicant_names extrahieren...'

DO $$
DECLARE
    cnt BIGINT;
BEGIN
    SELECT COUNT(*) INTO cnt FROM patent_schema.applicants;
    IF cnt >= 5000000 THEN
        RAISE NOTICE '    Stage 1 SKIP: applicants hat bereits % Zeilen (>= 5 M)', cnt;
    ELSE
        RAISE NOTICE '    Stage 1 RUN: applicants hat % Zeilen (< 5 M)', cnt;

        INSERT INTO patent_schema.applicants (raw_name, normalized_name)
        SELECT DISTINCT
            trim(applicant_name)                                     AS raw_name,
            upper(regexp_replace(trim(applicant_name),
                  '\s+(GMBH|AG|SA|SAS|SRL|LTD|LLC|INC|CORP|BV|NV|SE|PLC|CO\.)\.?$',
                  '', 'i'))                                          AS normalized_name
        FROM patent_schema.patents p,
             LATERAL unnest(string_to_array(p.applicant_names, ';')) AS applicant_name
        WHERE p.applicant_names IS NOT NULL
          AND trim(applicant_name) <> ''
        ON CONFLICT (raw_name) DO NOTHING;

        RAISE NOTICE '    Stage 1 done';
    END IF;
END $$;

\echo '    -> applicants fertig.'


-- ============================================================================
-- Stage 2/3: patent_schema.patent_applicants (N:M Junction, per Dekade)
-- ----------------------------------------------------------------------------
-- Verknuepft jedes Patent mit seinen Anmeldern. Join ueber raw_name.
-- Per-Decade-Splits: pre1980, 1980s, 1990s, 2000s, 2010s, 2020s.
-- Jeder INSERT ist eine eigene implizite Transaktion (psql autocommit).
-- ============================================================================

\echo ''
\echo '[2/3] patent_applicants Junction befuellen (per Dekade)...'

\echo '    [2.1/6] pre1980...'
INSERT INTO patent_schema.patent_applicants (patent_id, patent_year, applicant_id)
SELECT DISTINCT sub.patent_id, sub.patent_year, a.id
FROM (
    SELECT p.id AS patent_id, p.publication_year AS patent_year, trim(applicant_name) AS raw_name
    FROM patent_schema.patents p,
         LATERAL unnest(string_to_array(p.applicant_names, ';')) AS applicant_name
    WHERE p.applicant_names IS NOT NULL
      AND p.publication_year IS NOT NULL
      AND p.publication_year < 1980
      AND trim(applicant_name) <> ''
) sub
JOIN patent_schema.applicants a ON a.raw_name = sub.raw_name
ON CONFLICT DO NOTHING;

\echo '    [2.2/6] 1980s...'
INSERT INTO patent_schema.patent_applicants (patent_id, patent_year, applicant_id)
SELECT DISTINCT sub.patent_id, sub.patent_year, a.id
FROM (
    SELECT p.id AS patent_id, p.publication_year AS patent_year, trim(applicant_name) AS raw_name
    FROM patent_schema.patents p,
         LATERAL unnest(string_to_array(p.applicant_names, ';')) AS applicant_name
    WHERE p.applicant_names IS NOT NULL
      AND p.publication_year BETWEEN 1980 AND 1989
      AND trim(applicant_name) <> ''
) sub
JOIN patent_schema.applicants a ON a.raw_name = sub.raw_name
ON CONFLICT DO NOTHING;

\echo '    [2.3/6] 1990s...'
INSERT INTO patent_schema.patent_applicants (patent_id, patent_year, applicant_id)
SELECT DISTINCT sub.patent_id, sub.patent_year, a.id
FROM (
    SELECT p.id AS patent_id, p.publication_year AS patent_year, trim(applicant_name) AS raw_name
    FROM patent_schema.patents p,
         LATERAL unnest(string_to_array(p.applicant_names, ';')) AS applicant_name
    WHERE p.applicant_names IS NOT NULL
      AND p.publication_year BETWEEN 1990 AND 1999
      AND trim(applicant_name) <> ''
) sub
JOIN patent_schema.applicants a ON a.raw_name = sub.raw_name
ON CONFLICT DO NOTHING;

\echo '    [2.4/6] 2000s...'
INSERT INTO patent_schema.patent_applicants (patent_id, patent_year, applicant_id)
SELECT DISTINCT sub.patent_id, sub.patent_year, a.id
FROM (
    SELECT p.id AS patent_id, p.publication_year AS patent_year, trim(applicant_name) AS raw_name
    FROM patent_schema.patents p,
         LATERAL unnest(string_to_array(p.applicant_names, ';')) AS applicant_name
    WHERE p.applicant_names IS NOT NULL
      AND p.publication_year BETWEEN 2000 AND 2009
      AND trim(applicant_name) <> ''
) sub
JOIN patent_schema.applicants a ON a.raw_name = sub.raw_name
ON CONFLICT DO NOTHING;

\echo '    [2.5/6] 2010s...'
INSERT INTO patent_schema.patent_applicants (patent_id, patent_year, applicant_id)
SELECT DISTINCT sub.patent_id, sub.patent_year, a.id
FROM (
    SELECT p.id AS patent_id, p.publication_year AS patent_year, trim(applicant_name) AS raw_name
    FROM patent_schema.patents p,
         LATERAL unnest(string_to_array(p.applicant_names, ';')) AS applicant_name
    WHERE p.applicant_names IS NOT NULL
      AND p.publication_year BETWEEN 2010 AND 2019
      AND trim(applicant_name) <> ''
) sub
JOIN patent_schema.applicants a ON a.raw_name = sub.raw_name
ON CONFLICT DO NOTHING;

\echo '    [2.6/6] 2020s+...'
INSERT INTO patent_schema.patent_applicants (patent_id, patent_year, applicant_id)
SELECT DISTINCT sub.patent_id, sub.patent_year, a.id
FROM (
    SELECT p.id AS patent_id, p.publication_year AS patent_year, trim(applicant_name) AS raw_name
    FROM patent_schema.patents p,
         LATERAL unnest(string_to_array(p.applicant_names, ';')) AS applicant_name
    WHERE p.applicant_names IS NOT NULL
      AND p.publication_year >= 2020
      AND trim(applicant_name) <> ''
) sub
JOIN patent_schema.applicants a ON a.raw_name = sub.raw_name
ON CONFLICT DO NOTHING;

\echo '    -> patent_applicants fertig.'


-- ============================================================================
-- Stage 3/3: patent_schema.patent_cpc (Jaccard Junction, per Dekade)
-- ----------------------------------------------------------------------------
-- Extrahiert CPC-Subklassen (4-stellig) aus patents.cpc_codes. By design:
-- nur Patents mit >= 2 CPC-Codes (UC5 Jaccard Co-Occurrence).
-- Per-Decade-Splits wie Stage 2.
-- ============================================================================

\echo ''
\echo '[3/3] patent_cpc Junction befuellen (>= 2 CPC, per Dekade)...'

\echo '    [3.1/6] pre1980...'
INSERT INTO patent_schema.patent_cpc (patent_id, cpc_code, pub_year)
SELECT DISTINCT p.id, substring(code, 1, 4), p.publication_year
FROM patent_schema.patents p,
     LATERAL unnest(p.cpc_codes) AS code
WHERE p.cpc_codes IS NOT NULL
  AND array_length(p.cpc_codes, 1) >= 2
  AND p.publication_year IS NOT NULL
  AND p.publication_year < 1980
  AND substring(code, 1, 4) ~ '^[A-HY][0-9]{2}[A-Z]$'
ON CONFLICT DO NOTHING;

\echo '    [3.2/6] 1980s...'
INSERT INTO patent_schema.patent_cpc (patent_id, cpc_code, pub_year)
SELECT DISTINCT p.id, substring(code, 1, 4), p.publication_year
FROM patent_schema.patents p,
     LATERAL unnest(p.cpc_codes) AS code
WHERE p.cpc_codes IS NOT NULL
  AND array_length(p.cpc_codes, 1) >= 2
  AND p.publication_year BETWEEN 1980 AND 1989
  AND substring(code, 1, 4) ~ '^[A-HY][0-9]{2}[A-Z]$'
ON CONFLICT DO NOTHING;

\echo '    [3.3/6] 1990s...'
INSERT INTO patent_schema.patent_cpc (patent_id, cpc_code, pub_year)
SELECT DISTINCT p.id, substring(code, 1, 4), p.publication_year
FROM patent_schema.patents p,
     LATERAL unnest(p.cpc_codes) AS code
WHERE p.cpc_codes IS NOT NULL
  AND array_length(p.cpc_codes, 1) >= 2
  AND p.publication_year BETWEEN 1990 AND 1999
  AND substring(code, 1, 4) ~ '^[A-HY][0-9]{2}[A-Z]$'
ON CONFLICT DO NOTHING;

\echo '    [3.4/6] 2000s...'
INSERT INTO patent_schema.patent_cpc (patent_id, cpc_code, pub_year)
SELECT DISTINCT p.id, substring(code, 1, 4), p.publication_year
FROM patent_schema.patents p,
     LATERAL unnest(p.cpc_codes) AS code
WHERE p.cpc_codes IS NOT NULL
  AND array_length(p.cpc_codes, 1) >= 2
  AND p.publication_year BETWEEN 2000 AND 2009
  AND substring(code, 1, 4) ~ '^[A-HY][0-9]{2}[A-Z]$'
ON CONFLICT DO NOTHING;

\echo '    [3.5/6] 2010s...'
INSERT INTO patent_schema.patent_cpc (patent_id, cpc_code, pub_year)
SELECT DISTINCT p.id, substring(code, 1, 4), p.publication_year
FROM patent_schema.patents p,
     LATERAL unnest(p.cpc_codes) AS code
WHERE p.cpc_codes IS NOT NULL
  AND array_length(p.cpc_codes, 1) >= 2
  AND p.publication_year BETWEEN 2010 AND 2019
  AND substring(code, 1, 4) ~ '^[A-HY][0-9]{2}[A-Z]$'
ON CONFLICT DO NOTHING;

\echo '    [3.6/6] 2020s+...'
INSERT INTO patent_schema.patent_cpc (patent_id, cpc_code, pub_year)
SELECT DISTINCT p.id, substring(code, 1, 4), p.publication_year
FROM patent_schema.patents p,
     LATERAL unnest(p.cpc_codes) AS code
WHERE p.cpc_codes IS NOT NULL
  AND array_length(p.cpc_codes, 1) >= 2
  AND p.publication_year >= 2020
  AND substring(code, 1, 4) ~ '^[A-HY][0-9]{2}[A-Z]$'
ON CONFLICT DO NOTHING;

\echo '    -> patent_cpc fertig.'


-- ============================================================================
-- Nachher: Row-Counts
-- ============================================================================

\echo ''
\echo '--- Nachher (Row-Counts) ---'
SELECT 'patents' AS tabelle, COUNT(*) AS zeilen FROM patent_schema.patents
UNION ALL
SELECT 'applicants',                      COUNT(*) FROM patent_schema.applicants
UNION ALL
SELECT 'patent_applicants',               COUNT(*) FROM patent_schema.patent_applicants
UNION ALL
SELECT 'patent_cpc',                      COUNT(*) FROM patent_schema.patent_cpc;


-- ---------------------------------------------------------------------------
-- Session-Settings zuruecksetzen
-- ---------------------------------------------------------------------------

RESET statement_timeout;
RESET idle_in_transaction_session_timeout;
RESET lock_timeout;
RESET work_mem;
RESET maintenance_work_mem;
RESET synchronous_commit;
RESET temp_buffers;


\echo ''
\echo '=== Junction-Ableitung abgeschlossen ==='
\echo ''
\echo 'NAECHSTER SCHRITT: Materialized Views refreshen'
\echo '  docker exec ti-radar-db psql -U tip_admin -d ti_radar -f /tmp/refresh_cross_schema_mvs.sql'
\echo ''
