from __future__ import annotations

from .broker import BrokerClient
from .bridge import JsonLineBridge
from .models import OrderRequest, OrderResult, Quote
from .price_provider import PriceProvider
from .settings import NamuQvSettings


class NamuQvApiUnavailable(RuntimeError):
    pass


class NamuQvSession:
    def __init__(self, settings: NamuQvSettings) -> None:
        self.settings = settings
        self.bridge = JsonLineBridge(settings.bridge_command)

    def ensure_ready(self, require_account: bool = False) -> None:
        missing = self.settings.missing_connection_items()
        if require_account:
            missing += self.settings.missing_account_items()
        if missing:
            raise NamuQvApiUnavailable(
                "Namu QV settings are incomplete: " + ", ".join(missing)
            )
        if not self.bridge.ping():
            raise NamuQvApiUnavailable("Namu QV bridge is not responding.")

    def get_quote(self, symbol: str) -> Quote:
        self.ensure_ready()
        return self.bridge.get_quote(symbol)

    def place_order(self, request: OrderRequest) -> OrderResult:
        self.ensure_ready(require_account=True)
        return self.bridge.place_order(request)


class NamuQvQuoteProvider(PriceProvider):
    def __init__(self, session: NamuQvSession) -> None:
        self.session = session

    def get_quote(self, symbol: str) -> Quote:
        return self.session.get_quote(symbol)


class NamuQvBroker(BrokerClient):
    def __init__(self, session: NamuQvSession) -> None:
        self.session = session

    def place_order(self, request: OrderRequest) -> OrderResult:
        return self.session.place_order(request)
