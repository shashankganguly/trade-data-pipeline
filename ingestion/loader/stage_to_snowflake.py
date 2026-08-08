"""Stage local trade data to Snowflake using PUT and COPY INTO.

This script connects to Snowflake, uploads a local file into the table stage,
and loads it into the target table using COPY INTO.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import snowflake.connector
from snowflake.connector import SnowflakeConnection

try:
    import yaml
except ImportError:
    yaml = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload local trade data to Snowflake and load it into a table."
    )
    parser.add_argument(
        "--file",
        type=Path,
        required=True,
        help="Local path to the trade file to load.",
    )
    parser.add_argument(
        "--table",
        required=True,
        help="Target Snowflake table name in the form SCHEMA.TABLE or TABLE.",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="File format of the source trade file.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "config" / "snowflake_config.yml",
        help="Path to the Snowflake YAML config file.",
    )
    parser.add_argument(
        "--account",
        help="Snowflake account identifier.",
    )
    parser.add_argument(
        "--user",
        help="Snowflake user name.",
    )
    parser.add_argument(
        "--password",
        help="Snowflake password.",
    )
    parser.add_argument(
        "--role",
        help="Snowflake role.",
    )
    parser.add_argument(
        "--warehouse",
        help="Snowflake warehouse.",
    )
    parser.add_argument(
        "--database",
        help="Snowflake database.",
    )
    parser.add_argument(
        "--schema",
        help="Snowflake schema.",
    )
    parser.add_argument(
        "--on-error",
        default="abort_statement",
        choices=["continue", "skip_file", "skip_file_1", "abort_statement"],
        help="COPY INTO ON_ERROR action.",
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help="Purge staged files after successful COPY INTO.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def configure_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        format="%(levelname)s: %(message)s",
        level=level,
    )


def load_snowflake_config(config_path: Path) -> Dict[str, Any]:
    """Load the YAML Snowflake contract for connection defaults.

    The loader only reads the ``snowflake`` node from the config file. Explicit
    command-line arguments remain the highest priority input; environment
    variables are an intermediate fallback source.
    """
    if not config_path:
        return {}

    if not config_path.exists():
        logging.warning("Snowflake config file not found at %s; continuing with CLI/env defaults.", config_path)
        return {}

    if yaml is None:
        raise RuntimeError(
            "PyYAML is required to read the Snowflake config file. Install it with `pip install pyyaml`."
        )

    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    snowflake_config = payload.get("snowflake") or {}
    return snowflake_config if isinstance(snowflake_config, dict) else {}


def resolve_connection_parameters(args: argparse.Namespace) -> Dict[str, Optional[str]]:
    config_dict = load_snowflake_config(args.config)

    config_account = config_dict.get("account")
    config_user = config_dict.get("user")
    config_password = config_dict.get("password")
    config_role = config_dict.get("role")
    config_warehouse = config_dict.get("warehouse")
    config_database = config_dict.get("database")
    config_schema = config_dict.get("schema")

    connection_parameters: Dict[str, Optional[str]] = {
        "account": args.account or os.getenv("SNOWFLAKE_ACCOUNT") or config_account,
        "user": args.user or os.getenv("SNOWFLAKE_USER") or config_user,
        "password": args.password or os.getenv("SNOWFLAKE_PASSWORD") or config_password,
        "role": args.role or os.getenv("SNOWFLAKE_ROLE") or config_role,
        "warehouse": args.warehouse or os.getenv("SNOWFLAKE_WAREHOUSE") or config_warehouse,
        "database": args.database or os.getenv("SNOWFLAKE_DATABASE") or config_database,
        "schema": args.schema or os.getenv("SNOWFLAKE_SCHEMA") or config_schema,
    }

    return connection_parameters


def get_snowflake_connection(args: argparse.Namespace) -> SnowflakeConnection:
    connection_parameters = resolve_connection_parameters(args)
    missing = [key for key, value in connection_parameters.items() if key in ["account", "user", "password"] and not value]
    if missing:
        raise ValueError(
            "Missing required Snowflake connection parameters: " + ", ".join(missing)
        )
    return snowflake.connector.connect(**{k: v for k, v in connection_parameters.items() if v is not None})


def build_put_command(local_file: Path, table: str) -> str:
    stage_reference = f"@%{table}"
    local_uri = f"file://{local_file.resolve().as_posix()}"
    return f"PUT '{local_uri}' {stage_reference} AUTO_COMPRESS=FALSE OVERWRITE=TRUE"


def build_copy_command(table: str, staged_file_name: str, file_format: str, on_error: str, purge: bool) -> str:
    stage_reference = f"@%{table}/{staged_file_name}"
    format_clause = "TYPE=CSV FIELD_DELIMITER=',' SKIP_HEADER=1 FIELD_OPTIONALLY_ENCLOSED_BY='\"'" if file_format == "csv" else "TYPE=JSON"
    purge_clause = " PURGE=TRUE" if purge else ""
    return (
        f"COPY INTO {table} FROM {stage_reference} "
        f"FILE_FORMAT=({format_clause}) ON_ERROR={on_error.upper()}{purge_clause}"
    )


def execute_sql(connection: SnowflakeConnection, sql: str) -> list[dict]:
    logging.debug("Executing SQL: %s", sql)
    with connection.cursor() as cursor:
        cursor.execute(sql)
        try:
            return cursor.fetchall()
        except snowflake.connector.errors.ProgrammingError:
            return []


def main() -> None:
    args = parse_args()
    configure_logging(args.debug)

    if not args.file.exists():
        raise FileNotFoundError(f"Input file does not exist: {args.file}")

    logging.info("Connecting to Snowflake...")
    connection = get_snowflake_connection(args)

    try:
        put_sql = build_put_command(args.file, args.table)
        logging.info("Uploading file to table stage...")
        execute_sql(connection, put_sql)

        staged_file_name = args.file.name
        copy_sql = build_copy_command(
            table=args.table,
            staged_file_name=staged_file_name,
            file_format=args.format,
            on_error=args.on_error,
            purge=args.purge,
        )
        logging.info("Loading file into Snowflake table %s...", args.table)
        results = execute_sql(connection, copy_sql)

        logging.info("COPY INTO completed.")
        if results:
            logging.info("Rows processed: %s", results)
        else:
            logging.info("No query result metadata returned.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
