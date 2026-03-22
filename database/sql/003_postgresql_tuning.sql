-- ============================================================================
-- 003_postgresql_tuning.sql
-- PostgreSQL 17 runtime configuration for TI Platform
-- ============================================================================
-- Apply these settings in postgresql.conf or via ALTER SYSTEM.
-- Tuned for: 8 GB container RAM, SSD storage, 154M+ row patent dataset.
-- ============================================================================

-- Memory
-- shared_buffers: 25% of container RAM.
ALTER SYSTEM SET shared_buffers = '2GB';

-- effective_cache_size: 75% of container RAM.
ALTER SYSTEM SET effective_cache_size = '6GB';

-- work_mem: Per-sort/hash operation. Conservative for concurrent queries.
ALTER SYSTEM SET work_mem = '64MB';

-- maintenance_work_mem: For CREATE INDEX, VACUUM, REFRESH MATERIALIZED VIEW.
ALTER SYSTEM SET maintenance_work_mem = '512MB';

-- WAL
-- wal_buffers: Scales with shared_buffers.
ALTER SYSTEM SET wal_buffers = '64MB';

-- checkpoint_completion_target: Spread checkpoint I/O over longer window.
ALTER SYSTEM SET checkpoint_completion_target = 0.9;

-- max_wal_size: Allow larger WAL before checkpoint (reduces I/O during imports).
ALTER SYSTEM SET max_wal_size = '4GB';

-- Planner
-- random_page_cost: SSD-appropriate (default 4.0 is for spinning disks).
ALTER SYSTEM SET random_page_cost = 1.1;

-- effective_io_concurrency: SSD can handle parallel I/O.
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Parallelism (PostgreSQL 17)
ALTER SYSTEM SET max_parallel_workers_per_gather = 2;
ALTER SYSTEM SET max_parallel_workers = 4;
ALTER SYSTEM SET max_parallel_maintenance_workers = 2;
ALTER SYSTEM SET parallel_tuple_cost = 0.001;
ALTER SYSTEM SET parallel_setup_cost = 100;

-- Enable partition pruning at plan and execution time
ALTER SYSTEM SET enable_partition_pruning = on;

-- JIT compilation: beneficial for complex aggregation queries on large tables
ALTER SYSTEM SET jit = on;
ALTER SYSTEM SET jit_above_cost = 100000;

-- Statement timeout: prevent runaway queries (10 minutes for MV refresh)
ALTER SYSTEM SET statement_timeout = '600s';

-- Full-text search: default text search configuration
ALTER SYSTEM SET default_text_search_config = 'pg_catalog.english';

-- Autovacuum tuning for large tables
-- More aggressive on the 100M+ row tables to prevent bloat
ALTER SYSTEM SET autovacuum_vacuum_scale_factor = 0.01;    -- vacuum at 1% dead rows (default 20%)
ALTER SYSTEM SET autovacuum_analyze_scale_factor = 0.005;  -- analyze at 0.5% changed rows
ALTER SYSTEM SET autovacuum_vacuum_cost_delay = '2ms';     -- less throttling on SSD

-- Reload to apply
-- SELECT pg_reload_conf();
