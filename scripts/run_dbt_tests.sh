#!/usr/bin/env bash

# Run dbt models and tests for the Snowflake DBT project.
# This script assumes dbt is installed and the profile is configured.

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DBT_PROJECT_DIR="$ROOT_DIR/snowflake/dbt"
DBT_LOG_DIR="$ROOT_DIR/logs/dbt"
DBT_RUN_LOG="$DBT_LOG_DIR/dbt-run.log"
DBT_DEPS_LOG="$DBT_LOG_DIR/dbt-deps.log"
DBT_TEST_LOG="$DBT_LOG_DIR/dbt-test.log"

mkdir -p "$DBT_LOG_DIR"

log() {
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*" | tee -a "$DBT_RUN_LOG" >&2
}

run_dbt_step() {
  local label="$1"
  local logfile="$2"
  shift 2

  log "Starting $label..."

  if "$@" >"$logfile" 2>&1; then
    log "$label completed successfully."
    return 0
  fi

  local exit_code=$?
  log "ERROR: $label failed with exit code $exit_code."
  log "--- DBT diagnostic log: $logfile ---"
  cat "$logfile" >&2
  exit "$exit_code"
}

if ! command -v dbt >/dev/null 2>&1; then
  echo "ERROR: dbt is not installed or not on PATH." >&2
  exit 1
fi

cd "$DBT_PROJECT_DIR"

log "DBT project root: $DBT_PROJECT_DIR"

run_dbt_step "dbt deps" "$DBT_DEPS_LOG" dbt deps
run_dbt_step "dbt run" "$DBT_RUN_LOG" dbt run
run_dbt_step "dbt test" "$DBT_TEST_LOG" dbt test

log "DBT validation completed successfully."
exit 0
