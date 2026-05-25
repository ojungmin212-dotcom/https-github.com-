from pathlib import Path
import sys
import unittest

from apif_bot.bridge import BridgeError, JsonLineBridge
from apif_bot.models import OrderRequest, Side


class BridgeTest(unittest.TestCase):
    def test_mock_bridge_returns_quote(self) -> None:
        bridge = JsonLineBridge(_mock_bridge_command())

        quote = bridge.get_quote("005930")

        self.assertEqual(quote.symbol, "005930")
        self.assertEqual(quote.price, 70000)

    def test_mock_bridge_accepts_order(self) -> None:
        bridge = JsonLineBridge(_mock_bridge_command())

        result = bridge.place_order(
            OrderRequest(symbol="005930", side=Side.BUY, price=70000, quantity=1)
        )

        self.assertTrue(result.accepted)
        self.assertTrue(result.order_id.startswith("MOCK-"))

    def test_empty_command_is_rejected(self) -> None:
        with self.assertRaises(BridgeError):
            JsonLineBridge("")


def _mock_bridge_command() -> str:
    mock_bridge_path = Path("apif_bot/mock_bridge.py").resolve()
    return f'"{sys.executable}" "{mock_bridge_path}"'


if __name__ == "__main__":
    unittest.main()
