from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
import csv

from .models import Quote


class PriceProvider(ABC):
    @abstractmethod
    def get_quote(self, symbol: str) -> Quote:
        """Return the latest price for a symbol."""


class ManualPriceProvider(PriceProvider):
    def get_quote(self, symbol: str) -> Quote:
        raw = input(f"{symbol} latest price: ").strip().replace(",", "")
        return Quote(symbol=symbol, price=int(raw), received_at=datetime.now())


class CsvPriceProvider(PriceProvider):
    def __init__(self, path: Path) -> None:
        self.rows = self._load_rows(path)
        self.index = 0

    def get_quote(self, symbol: str) -> Quote:
        if self.index >= len(self.rows):
            raise StopIteration("CSV 가격 데이터가 끝났습니다.")
        price = self.rows[self.index]
        self.index += 1
        return Quote(symbol=symbol, price=price, received_at=datetime.now())

    @staticmethod
    def _load_rows(path: Path) -> list[int]:
        with path.open("r", newline="", encoding="utf-8") as fp:
            reader = csv.DictReader(fp)
            if "price" not in reader.fieldnames:
                raise ValueError("CSV에는 price 컬럼이 필요합니다.")
            prices = [int(row["price"]) for row in reader]

        if not prices:
            raise ValueError("CSV 가격 데이터가 비어 있습니다.")
        return prices
