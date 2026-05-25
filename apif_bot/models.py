from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
import json


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradingMode(str, Enum):
    DRY_RUN = "DRY_RUN"
    LIVE = "LIVE"


@dataclass(frozen=True)
class SafetyConfig:
    allowed_symbols: tuple[str, ...] = ()
    max_order_amount: int = 1_000_000
    max_quantity_per_order: int = 10
    require_market_hours: bool = False
    market_start: str = "09:00"
    market_end: str = "15:20"
    stop_file: str = "STOP_TRADING"

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SafetyConfig":
        if not data:
            return cls()
        return cls(
            allowed_symbols=tuple(str(symbol) for symbol in data.get("allowed_symbols", ())),
            max_order_amount=int(data.get("max_order_amount", 1_000_000)),
            max_quantity_per_order=int(data.get("max_quantity_per_order", 10)),
            require_market_hours=bool(data.get("require_market_hours", False)),
            market_start=str(data.get("market_start", "09:00")),
            market_end=str(data.get("market_end", "15:20")),
            stop_file=str(data.get("stop_file", "STOP_TRADING")),
        )


@dataclass(frozen=True)
class TradingPlan:
    symbol: str
    name: str
    buy_price: int
    sell_price: int
    quantity: int
    mode: TradingMode = TradingMode.DRY_RUN
    poll_seconds: float = 3.0
    safety: SafetyConfig = field(default_factory=SafetyConfig)

    def validate(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required.")
        if self.buy_price <= 0:
            raise ValueError("buy_price must be greater than 0.")
        if self.sell_price <= 0:
            raise ValueError("sell_price must be greater than 0.")
        if self.sell_price <= self.buy_price:
            raise ValueError("sell_price must be greater than buy_price.")
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than 0.")
        if self.poll_seconds < 1:
            raise ValueError("poll_seconds must be at least 1.")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TradingPlan":
        plan = cls(
            symbol=str(data["symbol"]),
            name=str(data.get("name", "")),
            buy_price=int(data["buy_price"]),
            sell_price=int(data["sell_price"]),
            quantity=int(data["quantity"]),
            mode=TradingMode(data.get("mode", TradingMode.DRY_RUN.value)),
            poll_seconds=float(data.get("poll_seconds", 3.0)),
            safety=SafetyConfig.from_dict(data.get("safety")),
        )
        plan.validate()
        return plan

    @classmethod
    def from_json_file(cls, path: Path) -> "TradingPlan":
        with path.open("r", encoding="utf-8") as fp:
            return cls.from_dict(json.load(fp))


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: int
    received_at: datetime


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: Side
    price: int
    quantity: int

    @property
    def amount(self) -> int:
        return self.price * self.quantity


@dataclass(frozen=True)
class OrderResult:
    accepted: bool
    order_id: str
    message: str
