import unittest

from apif_bot.models import OrderRequest, Side
from apif_bot.order_preview import build_native_order_preview


class OrderPreviewTest(unittest.TestCase):
    def test_buy_uses_namu_buy_tr(self) -> None:
        preview = build_native_order_preview(
            OrderRequest(symbol="005930", side=Side.BUY, price=70000, quantity=2)
        )

        self.assertEqual(preview.tr_code, "c8102")
        self.assertEqual(preview.tr_name, "주식매수 주문")
        self.assertEqual(preview.order_type_code, "00")
        self.assertEqual(preview.amount, 140000)
        self.assertTrue(preview.live_order_blocked)

    def test_sell_uses_namu_sell_tr(self) -> None:
        preview = build_native_order_preview(
            OrderRequest(symbol="005930", side=Side.SELL, price=75000, quantity=1),
            market_code="KRX",
            account_index=2,
        )

        self.assertEqual(preview.tr_code, "c8101")
        self.assertEqual(preview.tr_name, "주식매도 주문")
        self.assertEqual(preview.market_code, "KRX")
        self.assertEqual(preview.account_index, 2)

    def test_rejects_non_stock_code(self) -> None:
        with self.assertRaises(ValueError):
            build_native_order_preview(
                OrderRequest(symbol="ABC", side=Side.BUY, price=70000, quantity=1)
            )

    def test_rejects_unknown_market(self) -> None:
        with self.assertRaises(ValueError):
            build_native_order_preview(
                OrderRequest(symbol="005930", side=Side.BUY, price=70000, quantity=1),
                market_code="BAD",
            )


if __name__ == "__main__":
    unittest.main()
