from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from .broker import broker_for_mode
from .engine import TradingEngine
from .models import TradingPlan
from .price_provider import CsvPriceProvider, ManualPriceProvider


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="User-defined buy/sell auto trading draft")
    parser.add_argument(
        "--config",
        default="config/trade_plan.example.json",
        help="Trading plan JSON path",
    )
    parser.add_argument(
        "--price-csv",
        help="Simulated quote CSV path. Without it, enter prices manually.",
    )
    parser.add_argument(
        "--order-log",
        default="logs/orders.csv",
        help="Dry-run order log path",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    plan = TradingPlan.from_json_file(Path(args.config))
    provider = (
        CsvPriceProvider(Path(args.price_csv))
        if args.price_csv
        else ManualPriceProvider()
    )
    broker = broker_for_mode(plan.mode, Path(args.order_log))
    engine = TradingEngine(plan=plan, price_provider=provider, broker=broker)
    engine.run_forever()


if __name__ == "__main__":
    main()
