import sys
import unittest
from unittest.mock import patch

import pandas as pd

import analyze


class AnalyzeIndustryGateTests(unittest.TestCase):
    def test_prepare_price_history_discards_skhy_pre_listing_rows(self):
        prices = pd.DataFrame(
            {
                "Close": [100, 101, 102],
                "High": [100, 101, 102],
                "Low": [100, 101, 102],
                "Volume": [1, 1, 1],
            },
            index=pd.to_datetime(["2026-07-09", "2026-07-10", "2026-07-13"]),
        )

        filtered, history_context = analyze._prepare_price_history("SKHY", prices)

        self.assertEqual(
            list(filtered.index.strftime("%Y-%m-%d")),
            ["2026-07-10", "2026-07-13"],
        )
        self.assertEqual(history_context["listing_date"], "2026-07-10")

    def test_missing_manifest_blocks_before_preflight(self):
        with patch.object(sys, "argv", ["analyze.py", "--ticker", "MU"]), \
             patch.object(analyze, "run_preflight") as preflight:
            with self.assertRaises(SystemExit) as raised:
                analyze.main()
        self.assertEqual(raised.exception.code, 5)
        preflight.assert_not_called()

    def test_direct_analysis_without_context_blocks_before_login(self):
        with patch.object(analyze, "init_token", create=True) as init_token:
            with self.assertRaisesRegex(RuntimeError, "行业数据运行授权"):
                analyze.analyze_single("MU", "5y", username="user", password="secret")
        init_token.assert_not_called()


if __name__ == "__main__":
    unittest.main()
