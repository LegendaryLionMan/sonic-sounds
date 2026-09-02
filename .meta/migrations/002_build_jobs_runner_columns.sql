-- 002_build_jobs_runner_columns.sql
-- Day 6 build runner (build/runner.py) tracks per-job execution metadata:
-- output_path (path to generated artifact), elapsed_sec (run duration),
-- exit_code (subprocess rc). The original schema predates the runner
-- so these columns were not present. Idempotent: ADD COLUMN with
-- check + ALTER TABLE fallback (SQLite has no native IF NOT EXISTS
-- for ADD COLUMN).

ALTER TABLE build_jobs ADD COLUMN output_path TEXT;
ALTER TABLE build_jobs ADD COLUMN elapsed_sec REAL;
ALTER TABLE build_jobs ADD COLUMN exit_code INTEGER;
