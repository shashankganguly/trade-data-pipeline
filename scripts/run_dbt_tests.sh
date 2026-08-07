#!/usr/bin/env bash

# Run dbt models and tests for the Snowflake DBT project.
# This script assumes dbt is installed and the profile is configured.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DBT_PROJECT_DIR="$ROOT_DIR/snowflake/dbt"

if ! command -v dbt >/dev/null 2>&1; then
  echo "ERROR: dbt is not installed or not on PATH." >&2
  exit 1
fi

cd "$DBT_PROJECT_DIR"

echo "Running dbt deps..."
dbt deps

echo "Running dbt run..."
dbt run

echo "Running dbt test..."
dbt test

echo "DBT validation completed successfully."
