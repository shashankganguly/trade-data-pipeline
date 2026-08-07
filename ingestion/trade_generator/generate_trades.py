"""Generate synthetic trade data for the ingestion pipeline.

This script produces a configurable number of simulated trade records and writes
CSV payloads for Snowflake ingestion.
"""

from __future__ import annotations

import argparse
import csv
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List


DEFAULT_SYMBOLS = ["AAPL", "MSFT", "GOOG", "AMZN", "TSLA", "NFLX"]
DEFAULT_VENUES = ["NYSE", "NASDAQ", "CBOE", "IEX"]
DEFAULT_CURRENCIES = ["USD"]
DEFAULT_SIDES = ["BUY", "SELL"]


@dataclass
class Trade:
    trade_id: str
    timestamp: str
    symbol: str
    side: str
    quantity: int
    price: float
    currency: str
    venue: str
    version: int
    maturity_date: str
    status: str
    rejection_reason: str | None
    source_file: str
    load_ts: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic trade data for testing and ingestion."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of trades to generate.",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=DEFAULT_SYMBOLS,
        help="List of trade symbols to sample from.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to output file. If omitted, data is written to stdout.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for repeatable output.",
    )
    parser.add_argument(
        "--min-quantity",
        type=int,
        default=1,
        help="Minimum trade quantity.",
    )
    parser.add_argument(
        "--max-quantity",
        type=int,
        default=1000,
        help="Maximum trade quantity.",
    )
    parser.add_argument(
        "--min-price",
        type=float,
        default=10.0,
        help="Minimum trade price.",
    )
    parser.add_argument(
        "--max-price",
        type=float,
        default=1000.0,
        help="Maximum trade price.",
    )
    return parser.parse_args()


def generate_trade_timestamp(index: int, start_time: datetime) -> str:
    timestamp = start_time + timedelta(seconds=index * random.randint(1, 5))
    return timestamp.isoformat(timespec="seconds")


def generate_trades(
    count: int,
    symbols: List[str],
    min_quantity: int,
    max_quantity: int,
    min_price: float,
    max_price: float,
) -> Iterable[Trade]:
    start_time = datetime.utcnow()
    for index in range(1, count + 1):
        symbol = random.choice(symbols)
        version = random.randint(1, 9)
        maturity_offset_days = random.randint(1, 365)
        maturity_date = (datetime.utcnow().date() + timedelta(days=maturity_offset_days)).isoformat()
        status = random.choice(["ACTIVE", "EXPIRED"])
        load_ts = (start_time + timedelta(seconds=index * random.randint(1, 5))).isoformat(timespec="seconds")
        trade = Trade(
            trade_id=f"T{index:08d}",
            timestamp=generate_trade_timestamp(index, start_time),
            symbol=symbol,
            side=random.choice(DEFAULT_SIDES),
            quantity=random.randint(min_quantity, max_quantity),
            price=round(random.uniform(min_price, max_price), 2),
            currency=random.choice(DEFAULT_CURRENCIES),
            venue=random.choice(DEFAULT_VENUES),
            version=version,
            maturity_date=maturity_date,
            status=status,
            rejection_reason=None,
            source_file="synthetic_trades.csv",
            load_ts=load_ts,
        )
        yield trade


def write_csv(trades: Iterable[Trade], output_file: Path) -> None:
    fieldnames = [
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
    with output_file.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for trade in trades:
            writer.writerow(asdict(trade))


def print_csv(trades: Iterable[Trade]) -> None:
    fieldnames = [
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
    writer = csv.DictWriter(
        f=__import__("sys").stdout,
        fieldnames=fieldnames,
    )
    writer.writeheader()
    for trade in trades:
        writer.writerow(asdict(trade))


def main() -> None:
    args = parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    if args.count < 1:
        raise ValueError("--count must be a positive integer.")
    if args.min_quantity < 1 or args.max_quantity < args.min_quantity:
        raise ValueError("Invalid quantity range.")
    if args.min_price <= 0 or args.max_price <= 0 or args.max_price < args.min_price:
        raise ValueError("Invalid price range.")

    trades = list(
        generate_trades(
            count=args.count,
            symbols=args.symbols,
            min_quantity=args.min_quantity,
            max_quantity=args.max_quantity,
            min_price=args.min_price,
            max_price=args.max_price,
        )
    )

    if args.output:
        write_csv(trades, args.output)
        print(f"Generated {len(trades)} trades and wrote to {args.output}")
    else:
        print_csv(trades)


if __name__ == "__main__":
    main()
