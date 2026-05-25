from __future__ import annotations

from datetime import datetime, time
from pathlib import Path

from .models import OrderRequest, SafetyConfig, TradingPlan


class SafetyViolation(RuntimeError):
    pass


class SafetyGuard:
    def __init__(self, config: SafetyConfig) -> None:
        self.config = config

    @classmethod
    def from_plan(cls, plan: TradingPlan) -> "SafetyGuard":
        return cls(plan.safety)

    def validate_plan(self, plan: TradingPlan) -> None:
        self._validate_symbol(plan.symbol)
        if plan.quantity > self.config.max_quantity_per_order:
            raise SafetyViolation(
                f"quantity {plan.quantity} exceeds max_quantity_per_order "
                f"{self.config.max_quantity_per_order}."
            )
        largest_amount = max(plan.buy_price, plan.sell_price) * plan.quantity
        if largest_amount > self.config.max_order_amount:
            raise SafetyViolation(
                f"order amount {largest_amount} exceeds max_order_amount "
                f"{self.config.max_order_amount}."
            )

    def validate_order(self, request: OrderRequest, now: datetime | None = None) -> None:
        self._validate_stop_file()
        self._validate_market_hours(now or datetime.now())
        self._validate_symbol(request.symbol)
        if request.quantity > self.config.max_quantity_per_order:
            raise SafetyViolation(
                f"quantity {request.quantity} exceeds max_quantity_per_order "
                f"{self.config.max_quantity_per_order}."
            )
        if request.amount > self.config.max_order_amount:
            raise SafetyViolation(
                f"order amount {request.amount} exceeds max_order_amount "
                f"{self.config.max_order_amount}."
            )

    def _validate_symbol(self, symbol: str) -> None:
        if self.config.allowed_symbols and symbol not in self.config.allowed_symbols:
            raise SafetyViolation(f"symbol {symbol} is not in allowed_symbols.")

    def _validate_stop_file(self) -> None:
        if Path(self.config.stop_file).exists():
            raise SafetyViolation(
                f"emergency stop file exists: {self.config.stop_file}"
            )

    def _validate_market_hours(self, now: datetime) -> None:
        if not self.config.require_market_hours:
            return
        start = _parse_hhmm(self.config.market_start)
        end = _parse_hhmm(self.config.market_end)
        current = now.time().replace(second=0, microsecond=0)
        if not start <= current <= end:
            raise SafetyViolation(
                f"current time {current.strftime('%H:%M')} is outside market hours "
                f"{self.config.market_start}-{self.config.market_end}."
            )


def _parse_hhmm(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()
