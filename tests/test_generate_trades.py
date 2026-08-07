import csv
import importlib.util
import json
import tempfile
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT_DIR / "ingestion" / "trade_generator" / "generate_trades.py"

spec = importlib.util.spec_from_file_location("generate_trades", MODULE_PATH)
generate_trades = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_trades)


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


def test_write_json_outputs_valid_json(tmp_path):
    trades = list(
        generate_trades.generate_trades(
            count=2,
            symbols=["JSON"],
            min_quantity=2,
            max_quantity=2,
            min_price=30.0,
            max_price=30.0,
        )
    )
    output_file = tmp_path / "trades.json"
    generate_trades.write_json(trades, output_file)

    assert output_file.exists()
    content = json.loads(output_file.read_text(encoding="utf-8"))
    assert isinstance(content, list)
    assert len(content) == 2
    assert content[0]["symbol"] == "JSON"
    assert content[0]["quantity"] == 2
    assert content[0]["price"] == 30.0
