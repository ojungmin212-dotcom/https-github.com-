from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import sleep

from .broker import BrokerClient
from .models import OrderRequest, Quote, Side, TradingPlan
from .price_provider import PriceProvider
from .safety import SafetyGuard, SafetyViolation


class PositionState(str, Enum):
    WAITING_TO_BUY = "WAITING_TO_BUY"
    HOLDING = "HOLDING"
    FINISHED = "FINISHED"


@dataclass
class EngineStatus:
    state: PositionState = PositionState.WAITING_TO_BUY
    buy_order_id: str | None = None
    sell_order_id: str | None = None


class TradingEngine:
    def __init__(
        self,
        plan: TradingPlan,
        price_provider: PriceProvider,
        broker: BrokerClient,
        safety_guard: SafetyGuard | None = None,
    ) -> None:
        plan.validate()
        self.plan = plan
        self.price_provider = price_provider
        self.broker = broker
        self.safety_guard = safety_guard or SafetyGuard.from_plan(plan)
        self.safety_guard.validate_plan(plan)
        self.status = EngineStatus()

    def evaluate_once(self) -> str:
        quote = self.price_provider.get_quote(self.plan.symbol)
        return self._evaluate_quote(quote)

    def run_forever(self, max_ticks: int | None = None) -> None:
        print("Auto monitor started. Press Ctrl+C to stop.")
        ticks = 0
        while self.status.state != PositionState.FINISHED:
            try:
                message = self.evaluate_once()
                print(message)
                ticks += 1
                if max_ticks is not None and ticks >= max_ticks:
                    print(f"Max ticks reached: {max_ticks}")
                    break
                sleep(self.plan.poll_seconds)
            except SafetyViolation as exc:
                print(f"Safety stop: {exc}")
                break
            except StopIteration as exc:
                print(str(exc))
                break

    def _evaluate_quote(self, quote: Quote) -> str:
        if self.status.state == PositionState.WAITING_TO_BUY:
            if quote.price <= self.plan.buy_price:
                result = self._place_order(
                    OrderRequest(
                        symbol=self.plan.symbol,
                        side=Side.BUY,
                        price=self.plan.buy_price,
                        quantity=self.plan.quantity,
                    )
                )
                self.status.buy_order_id = result.order_id
                self.status.state = PositionState.HOLDING
                return (
                    f"[BUY_TRIGGERED] quote {quote.price:,}, "
                    f"limit {self.plan.buy_price:,}, order_id {result.order_id}"
                )

            return (
                f"[WAIT_BUY] quote {quote.price:,}, "
                f"target {self.plan.buy_price:,}"
            )

        if self.status.state == PositionState.HOLDING:
            if quote.price >= self.plan.sell_price:
                result = self._place_order(
                    OrderRequest(
                        symbol=self.plan.symbol,
                        side=Side.SELL,
                        price=self.plan.sell_price,
                        quantity=self.plan.quantity,
                    )
                )
                self.status.sell_order_id = result.order_id
                self.status.state = PositionState.FINISHED
                return (
                    f"[SELL_TRIGGERED] quote {quote.price:,}, "
                    f"limit {self.plan.sell_price:,}, order_id {result.order_id}"
                )

            return (
                f"[WAIT_SELL] quote {quote.price:,}, "
                f"target {self.plan.sell_price:,}"
            )

        return "[FINISHED] buy and sell orders are complete."

    def _place_order(self, request: OrderRequest):
        self.safety_guard.validate_order(request)
        return self.broker.place_order(request)
