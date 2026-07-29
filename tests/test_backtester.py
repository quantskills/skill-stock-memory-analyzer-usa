import unittest

import pandas as pd

from utils.backtester import run_backtest


def _price_frame(start: str, periods: int) -> pd.DataFrame:
    index = pd.bdate_range(start, periods=periods)
    return pd.DataFrame(
        {
            "Open": range(100, 100 + periods),
            "High": range(101, 101 + periods),
            "Low": range(99, 99 + periods),
            "Close": range(100, 100 + periods),
            "Volume": [1000] * periods,
        },
        index=index,
    )


class BacktesterTests(unittest.TestCase):
    def test_skhy_backtest_reports_post_listing_history_shortage(self):
        result = run_backtest("SKHY", _price_frame("2026-07-10", 30), {}, {})

        self.assertFalse(result["available"])
        self.assertEqual(result["listing_date"], "2026-07-10")
        self.assertEqual(result["trading_days"], 30)
        self.assertIn("上市后历史不足", result["reason"])


if __name__ == "__main__":
    unittest.main()
