from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from apif_bot.broker import DryRunBroker
from apif_bot.engine import PositionState, TradingEngine
from apif_bot.models import SafetyConfig, TradingPlan
from apif_bot.price_provider import CsvPriceProvider
from apif_bot.safety import SafetyViolation


class TradingEngineTest(unittest.TestCase):
    def test_buy_then_sell_from_csv_prices(self) -> None:
        with TemporaryDirectory() as temp_dir:
            plan = TradingPlan(
                symbol="005930",
                name="Samsung Electronics",
                buy_price=70000,
                stop_loss_price=68000,
                sell_price=75000,
                quantity=1,
            )
            provider = CsvPriceProvider(Path("tests/sample_prices.csv"))
            broker = DryRunBroker(Path(temp_dir) / "orders.csv")
            engine = TradingEngine(plan, provider, broker)

            messages = [engine.evaluate_once() for _ in range(5)]

            self.assertIn("[BUY_TRIGGERED]", messages[2])
            self.assertIn("[SELL_TRIGGERED]", messages[4])
            self.assertEqual(engine.status.state, PositionState.FINISHED)

    def test_stop_loss_sells_after_buy_when_price_falls(self) -> None:
        with TemporaryDirectory() as temp_dir:
            prices = Path(temp_dir) / "prices.csv"
            prices.write_text("price\n70000\n67000\n", encoding="utf-8")
            plan = TradingPlan(
                symbol="005930",
                name="Samsung Electronics",
                buy_price=70000,
                stop_loss_price=68000,
                sell_price=75000,
                quantity=1,
            )
            provider = CsvPriceProvider(prices)
            broker = DryRunBroker(Path(temp_dir) / "orders.csv")
            engine = TradingEngine(plan, provider, broker)

            buy_message = engine.evaluate_once()
            stop_message = engine.evaluate_once()

            self.assertIn("[BUY_TRIGGERED]", buy_message)
            self.assertIn("[STOP_LOSS_TRIGGERED]", stop_message)
            self.assertEqual(engine.status.state, PositionState.FINISHED)

    def test_rejects_stop_loss_above_buy_price(self) -> None:
        plan = TradingPlan(
            symbol="005930",
            name="Samsung Electronics",
            buy_price=70000,
            stop_loss_price=71000,
            sell_price=75000,
            quantity=1,
        )

        with self.assertRaises(ValueError):
            plan.validate()

    def test_rejects_symbol_outside_allow_list(self) -> None:
        plan = TradingPlan(
            symbol="000660",
            name="SK hynix",
            buy_price=100000,
            sell_price=110000,
            quantity=1,
            safety=SafetyConfig(allowed_symbols=("005930",)),
        )
        provider = CsvPriceProvider(Path("tests/sample_prices.csv"))
        broker = DryRunBroker(Path("logs/test_orders.csv"))

        with self.assertRaises(SafetyViolation):
            TradingEngine(plan, provider, broker)

    def test_emergency_stop_file_blocks_order(self) -> None:
        with TemporaryDirectory() as temp_dir:
            stop_file = Path(temp_dir) / "STOP_TRADING"
            stop_file.write_text("stop", encoding="utf-8")
            plan = TradingPlan(
                symbol="005930",
                name="Samsung Electronics",
                buy_price=70000,
                sell_price=75000,
                quantity=1,
                safety=SafetyConfig(stop_file=str(stop_file)),
            )
            provider = CsvPriceProvider(Path("tests/sample_prices.csv"))
            broker = DryRunBroker(Path(temp_dir) / "orders.csv")
            engine = TradingEngine(plan, provider, broker)

            engine.evaluate_once()
            engine.evaluate_once()
            with self.assertRaises(SafetyViolation):
                engine.evaluate_once()


if __name__ == "__main__":
    unittest.main()
