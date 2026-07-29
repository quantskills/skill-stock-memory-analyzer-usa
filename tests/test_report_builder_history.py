import unittest

import pandas as pd

from utils.indicators import calc_technicals
from utils.report_builder import (
    _assessment_footer,
    _backtest_unavailable_card,
    _fig_price_with_ma,
    _fig_rsi_macd,
    _history_boundary_card,
    _position_bar,
)
from utils.ticker_policy import build_history_context


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

    def test_short_skhy_history_hides_unready_technical_indicators(self):
        price_df = pd.DataFrame(
            {
                "Open": range(100, 113),
                "High": range(101, 114),
                "Low": range(99, 112),
                "Close": range(100, 113),
                "Volume": [1000] * 13,
            },
            index=pd.bdate_range("2026-07-10", periods=13),
        )
        technicals = calc_technicals(price_df)
        context = build_history_context("SKHY", price_df)

        price_html = _fig_price_with_ma(price_df, technicals, context)
        indicator_html = _fig_rsi_macd(price_df, technicals, context)

        self.assertNotIn('"name":"MA20"', price_html)
        self.assertNotIn('"name":"MA50"', price_html)
        self.assertNotIn('"name":"MA200"', price_html)
        self.assertIn(r"\u6682\u4e0d\u5c55\u793a", price_html)
        self.assertIn(r"\u6682\u4e0d\u5c55\u793a", indicator_html)

    def test_short_skhy_history_does_not_emit_short_term_direction(self):
        price_df = pd.DataFrame(
            {
                "Open": range(100, 113),
                "High": range(101, 114),
                "Low": range(99, 112),
                "Close": range(100, 113),
                "Volume": [1000] * 13,
            },
            index=pd.bdate_range("2026-07-10", periods=13),
        )
        context = build_history_context("SKHY", price_df)

        html = _assessment_footer(
            {}, {}, {}, calc_technicals(price_df), {}, {}, history_context=context
        )

        self.assertIn("短期 (1-5日): 暂不判断", html)
        self.assertIn("数据不足", html)


if __name__ == "__main__":
    unittest.main()
