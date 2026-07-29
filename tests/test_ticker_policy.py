import unittest

import pandas as pd

from utils.ticker_policy import build_history_context, filter_price_history


class TickerPolicyTests(unittest.TestCase):
    def test_skhy_filters_all_rows_before_nasdaq_listing(self):
        rows = pd.DataFrame(
            {"Close": [100, 101, 102]},
            index=pd.to_datetime(["2026-07-09", "2026-07-10", "2026-07-13"]),
        )

        actual = filter_price_history("SKHY", rows)

        self.assertEqual(
            list(actual.index.strftime("%Y-%m-%d")),
            ["2026-07-10", "2026-07-13"],
        )

    def test_non_skhy_does_not_filter_existing_history(self):
        rows = pd.DataFrame(
            {"Close": [100]}, index=pd.to_datetime(["2020-01-02"])
        )

        actual = filter_price_history("MU", rows)

        self.assertEqual(len(actual), 1)

    def test_skhy_context_marks_52_week_data_unavailable_before_252_sessions(self):
        rows = pd.DataFrame(
            {"Close": range(20)},
            index=pd.bdate_range("2026-07-10", periods=20),
        )

        context = build_history_context("SKHY", rows)

        self.assertFalse(context["has_52_week_history"])
        self.assertEqual(context["listing_date"], "2026-07-10")
        self.assertIn(
            "上市后交易日不足", context["unavailable_reasons"]["52_week"]
        )


if __name__ == "__main__":
    unittest.main()
