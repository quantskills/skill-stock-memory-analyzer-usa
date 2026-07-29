import unittest

from utils.report_builder import (
    _backtest_unavailable_card,
    _history_boundary_card,
    _position_bar,
)


class ReportHistoryTests(unittest.TestCase):
    def setUp(self):
        self.history_context = {
            "listing_date": "2026-07-10",
            "trading_days": 20,
            "has_52_week_history": False,
            "unavailable_reasons": {"52_week": "上市后交易日不足 252 个"},
        }

    def test_history_card_explains_skhy_listing_boundary(self):
        html = _history_boundary_card("SKHY", self.history_context)

        self.assertIn("SKHY 自 2026-07-10 在 Nasdaq 上市", html)
        self.assertIn("20", html)

    def test_position_bar_uses_unavailable_message_without_52_week_history(self):
        html = _position_bar({"currentPrice": 100}, self.history_context)

        self.assertIn("上市后交易日不足 252 个", html)
        self.assertNotIn("52周低", html)

    def test_backtest_card_preserves_unavailable_reason(self):
        html = _backtest_unavailable_card(
            {"available": False, "reason": "SKHY 上市后历史不足，暂不提供历史回测"}
        )

        self.assertIn("暂不提供历史回测", html)


if __name__ == "__main__":
    unittest.main()
