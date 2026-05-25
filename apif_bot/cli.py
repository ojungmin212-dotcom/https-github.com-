from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from .broker import broker_for_mode
from .engine import TradingEngine
from .models import TradingPlan
from .price_provider import CsvPriceProvider, ManualPriceProvider


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="사용자 지정가 기반 자동 매수/매도 초안")
    parser.add_argument(
        "--config",
        default="config/trade_plan.example.json",
        help="매매 설정 JSON 파일 경로",
    )
    parser.add_argument(
        "--price-csv",
        help="모의 현재가 CSV 경로. 없으면 실행 중 직접 현재가를 입력합니다.",
    )
    parser.add_argument(
        "--order-log",
        default="logs/orders.csv",
        help="모의 주문 기록 파일 경로",
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
