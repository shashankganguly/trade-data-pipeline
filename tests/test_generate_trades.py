import argparse
import csv
import sys
import importlib.util
from pathlib import Path

# Add ingestion module to path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "ingestion" / "trade_generator"))
sys.path.insert(0, str(ROOT_DIR / "ingestion" / "loader"))

# Import directly instead of using spec_from_file_location
import generate_trades
from stage_to_snowflake import resolve_connection_parameters

def test_generate_trades_count_and_fields():
    trades = list(
        generate_trades.generate_trades(
            count=5,
            symbols=["TEST"],
            min_quantity=1,
            max_quantity=1,
            min_price=10.0,
            max_price=10.0,
        )
    )

    assert len(trades) == 5
    for index, trade in enumerate(trades, start=1):
        assert trade.trade_id == f"T{index:08d}"
        assert trade.symbol == "TEST"
        assert trade.quantity == 1
        assert trade.price == 10.0
        assert trade.currency == "USD"
        assert trade.side in generate_trades.DEFAULT_SIDES
        assert trade.venue in generate_trades.DEFAULT_VENUES
        assert isinstance(trade.timestamp, str)
        assert isinstance(trade.version, int)
        assert isinstance(trade.maturity_date, str)
        assert isinstance(trade.status, str)
        assert trade.rejection_reason in {None, ""}
        assert isinstance(trade.source_file, str)
        assert isinstance(trade.load_ts, str)


def test_write_csv_creates_header_and_rows(tmp_path):
    trades = list(
        generate_trades.generate_trades(
            count=3,
            symbols=["CSV"],
            min_quantity=5,
            max_quantity=5,
            min_price=20.0,
            max_price=20.0,
        )
    )
    output_file = tmp_path / "trades.csv"
    generate_trades.write_csv(trades, output_file)

    assert output_file.exists()
    with output_file.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    assert len(rows) == 3
    assert reader.fieldnames == [
        "trade_id",
        "timestamp",
        "symbol",
        "side",
        "quantity",
        "price",
        "currency",
        "venue",
        "version",
        "maturity_date",
        "status",
        "rejection_reason",
        "source_file",
        "load_ts",
    ]
    assert rows[0]["symbol"] == "CSV"


def test_snowflake_config_defaults_and_cli_override(tmp_path):
    config_path = tmp_path / "snowflake_config.yml"
    config_path.write_text(
        """
snowflake:
  account: cfg_account
  user: cfg_user
  password: cfg_password
  role: cfg_role
  warehouse: cfg_warehouse
  database: cfg_database
  schema: cfg_schema
""",
        encoding="utf-8",
    )

    args = argparse.Namespace(
        config=config_path,
        account=None,
        user=None,
        password=None,
        role=None,
        warehouse=None,
        database=None,
        schema=None,
    )

    # resolved = stage_to_snowflake.resolve_connection_parameters(args)
    resolved = resolve_connection_parameters(args)

    assert resolved["account"] == "cfg_account"
    assert resolved["user"] == "cfg_user"
    assert resolved["password"] == "cfg_password"
    assert resolved["role"] == "cfg_role"
    assert resolved["warehouse"] == "cfg_warehouse"
    assert resolved["database"] == "cfg_database"
    assert resolved["schema"] == "cfg_schema"

    override_args = argparse.Namespace(
        config=config_path,
        account="cli_account",
        user="cli_user",
        password="cli_password",
        role="cli_role",
        warehouse="cli_wh",
        database="cli_db",
        schema="cli_schema",
    )

    # override_resolved = stage_to_snowflake.resolve_connection_parameters(override_args)
    override_resolved = resolve_connection_parameters(override_args)

    assert override_resolved["account"] == "cli_account"
    assert override_resolved["user"] == "cli_user"
    assert override_resolved["password"] == "cli_password"
    assert override_resolved["role"] == "cli_role"
    assert override_resolved["warehouse"] == "cli_wh"
    assert override_resolved["database"] == "cli_db"
    assert override_resolved["schema"] == "cli_schema"

