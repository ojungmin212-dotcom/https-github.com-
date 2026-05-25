from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import subprocess
from typing import Any

from .models import OrderRequest, OrderResult, Quote


class BridgeError(RuntimeError):
    pass


@dataclass(frozen=True)
class BridgeResponse:
    ok: bool
    data: dict[str, Any]


class JsonLineBridge:
    def __init__(self, command: str, timeout_seconds: float = 10.0) -> None:
        if not command.strip():
            raise BridgeError("APIF_NAMU_BRIDGE_COMMAND is empty.")
        self.command = command
        self.timeout_seconds = timeout_seconds

    def get_quote(self, symbol: str) -> Quote:
        response = self._request({"command": "quote", "symbol": symbol})
        price = int(response.data["price"])
        return Quote(symbol=symbol, price=price, received_at=datetime.now())

    def place_order(self, request: OrderRequest) -> OrderResult:
        response = self._request(
            {
                "command": "order",
                "symbol": request.symbol,
                "side": request.side.value,
                "price": request.price,
                "quantity": request.quantity,
            }
        )
        return OrderResult(
            accepted=bool(response.data.get("accepted", False)),
            order_id=str(response.data.get("order_id", "")),
            message=str(response.data.get("message", "")),
        )

    def ping(self) -> bool:
        try:
            response = self._request({"command": "ping"})
        except BridgeError:
            return False
        return response.ok

    def _request(self, payload: dict[str, Any]) -> BridgeResponse:
        if not self.command.strip():
            raise BridgeError("Bridge command is empty.")

        try:
            result = subprocess.run(
                self.command,
                input=json.dumps(payload) + "\n",
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
                shell=True,
            )
        except OSError as exc:
            raise BridgeError(f"Bridge command failed to start: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise BridgeError("Bridge command timed out.") from exc

        if result.returncode != 0:
            raise BridgeError(result.stderr.strip() or "Bridge command failed.")

        first_line = result.stdout.splitlines()[0] if result.stdout else ""
        if not first_line:
            raise BridgeError("Bridge returned no response.")

        try:
            decoded = json.loads(first_line)
        except json.JSONDecodeError as exc:
            raise BridgeError(f"Bridge returned invalid JSON: {first_line}") from exc

        if not isinstance(decoded, dict):
            raise BridgeError("Bridge response must be a JSON object.")
        if not decoded.get("ok", False):
            raise BridgeError(str(decoded.get("error", "Bridge returned an error.")))

        data = decoded.get("data", {})
        if not isinstance(data, dict):
            raise BridgeError("Bridge response data must be a JSON object.")
        return BridgeResponse(ok=True, data=data)
