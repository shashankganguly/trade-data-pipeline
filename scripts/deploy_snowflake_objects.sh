#!/usr/bin/env bash

# Generate synthetic trade data and load it into Snowflake.
# This script assumes Python and the Snowflake loader script are available.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TRADE_GENERATOR="$ROOT_DIR/ingestion/trade_generator/generate_trades.py"
SNOWFLAKE_LOADER="$ROOT_DIR/ingestion/loader/stage_to_snowflake.py"

if ! command -v python >/dev/null 2>&1 && ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: Python is not installed or not on PATH." >&2
  exit 1
fi

PYTHON_COMMAND=python
if ! command -v python >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
  PYTHON_COMMAND=python3
fi

GENERATION_FILE="$ROOT_DIR/tmp_trades.csv"

if [[ $# -gt 0 ]]; then
  echo "Usage: $0"
  echo "This script generates a trade file and loads it into Snowflake using the hardcoded target file path." >&2
  exit 1
fi

if [[ ! -f "$TRADE_GENERATOR" ]]; then
  echo "ERROR: Trade generator script not found: $TRADE_GENERATOR" >&2
  exit 1
fi

if [[ ! -f "$SNOWFLAKE_LOADER" ]]; then
  echo "ERROR: Snowflake loader script not found: $SNOWFLAKE_LOADER" >&2
  exit 1
fi

# Generate sample trade data
echo "Generating trade data to $GENERATION_FILE..."
$PYTHON_COMMAND "$TRADE_GENERATOR" --count 100 --format csv --output "$GENERATION_FILE"

echo "Loading trade data into Snowflake..."
$PYTHON_COMMAND "$SNOWFLAKE_LOADER" \
  --file "$GENERATION_FILE" \
  --format csv \
  --table PUBLIC.raw_trades

echo "Deployment completed."
