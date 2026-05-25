from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
import csv
import uuid

from .models import OrderRequest, OrderResult, TradingMode


class BrokerClient(ABC):
    @abstractmethod
    def place_order(self, request: OrderRequest) -> OrderResult:
        """Send an order to a broker or a simulator."""


class DryRunBroker(BrokerClient):
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def place_order(self, request: OrderRequest) -> OrderResult:
        order_id = f"DRY-{uuid.uuid4().hex[:10].upper()}"
        row = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "order_id": order_id,
            "symbol": request.symbol,
            "side": request.side.value,
            "price": request.price,
            "quantity": request.quantity,
        }
        is_new = not self.log_path.exists()
        with self.log_path.open("a", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=list(row.keys()))
            if is_new:
                writer.writeheader()
            writer.writerow(row)

        return OrderResult(
            accepted=True,
            order_id=order_id,
            message="Dry-run order recorded. No real account order was sent.",
        )


class NamuQvBroker(BrokerClient):
    def place_order(self, request: OrderRequest) -> OrderResult:
        raise NotImplementedError(
            "Install the Namu QV Open API module and official order spec first."
        )


def broker_for_mode(mode: TradingMode, log_path: Path) -> BrokerClient:
    if mode == TradingMode.DRY_RUN:
        return DryRunBroker(log_path=log_path)
    return NamuQvBroker()
