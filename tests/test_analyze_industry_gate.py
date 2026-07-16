import sys
import unittest
from unittest.mock import patch

import analyze


class AnalyzeIndustryGateTests(unittest.TestCase):
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
