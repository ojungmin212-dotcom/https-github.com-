from __future__ import annotations

from datetime import datetime

from .broker import BrokerClient
from .models import OrderRequest, OrderResult, Quote
from .price_provider import PriceProvider
from .settings import NamuQvSettings


class NamuQvApiUnavailable(RuntimeError):
    pass


class NamuQvSession:
    def __init__(self, settings: NamuQvSettings) -> None:
        self.settings = settings

    def ensure_ready(self) -> None:
        missing = self.settings.missing_items()
        if missing:
            raise NamuQvApiUnavailable(
                "Namu QV settings are incomplete: " + ", ".join(missing)
            )
        raise NamuQvApiUnavailable(
            "Namu QV Open API binding is not implemented yet. "
            "Install the official module and confirm the function spec first."
        )


class NamuQvQuoteProvider(PriceProvider):
    def __init__(self, session: NamuQvSession) -> None:
        self.session = session

    def get_quote(self, symbol: str) -> Quote:
        self.session.ensure_ready()
        return Quote(symbol=symbol, price=0, received_at=datetime.now())


class NamuQvBroker(BrokerClient):
    def __init__(self, session: NamuQvSession) -> None:
        self.session = session

    def place_order(self, request: OrderRequest) -> OrderResult:
        self.session.ensure_ready()
        return OrderResult(
            accepted=False,
            order_id="",
            message="Namu QV order binding is not implemented yet.",
        )
