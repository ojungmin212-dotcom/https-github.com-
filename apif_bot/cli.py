from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from .broker import broker_for_mode
from .engine import TradingEngine
from .models import TradingPlan
from .namu_qv import NamuQvQuoteProvider, NamuQvSession
from .price_provider import CsvPriceProvider, ManualPriceProvider
from .settings import NamuQvSettings, load_dotenv_file


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
        "--quote-source",
        choices=("manual", "csv", "namu"),
        default=None,
        help="Quote source. Defaults to csv when --price-csv is set, otherwise manual.",
    )
    parser.add_argument(
        "--order-log",
        default="logs/orders.csv",
        help="Dry-run order log path",
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        help="Stop after this many quote checks. Useful for testing.",
    )
    return parser


def main() -> None:
    load_dotenv_file()
    args = build_parser().parse_args()
    plan = TradingPlan.from_json_file(Path(args.config))
    quote_source = args.quote_source or ("csv" if args.price_csv else "manual")
    provider = _build_price_provider(quote_source, args.price_csv)
    broker = broker_for_mode(plan.mode, Path(args.order_log))
    engine = TradingEngine(plan=plan, price_provider=provider, broker=broker)
    engine.run_forever(max_ticks=args.max_ticks)


def _build_price_provider(quote_source: str, price_csv: str | None):
    if quote_source == "csv":
        if not price_csv:
            raise ValueError("--price-csv is required when --quote-source csv is used.")
        return CsvPriceProvider(Path(price_csv))
    if quote_source == "namu":
        return NamuQvQuoteProvider(NamuQvSession(NamuQvSettings.from_env()))
    return ManualPriceProvider()


if __name__ == "__main__":
    main()
