import json
import unittest
from pathlib import Path


class IndustryConfigTests(unittest.TestCase):
    def test_skhy_profile_capex_and_adr_peer_are_configured(self):
        config_path = Path(__file__).resolve().parents[1] / "config" / "industry_data.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertIn("SKHY", data["company_profiles"])
        self.assertIn("SKHY", data["capex_guidance"])
        dram_peers = data["memory_peers"]["dram_focused"]
        skhy_peer = next(peer for peer in dram_peers if peer["ticker"] == "SKHY")
        self.assertEqual(skhy_peer["underlying_ticker"], "000660.KS")
        self.assertEqual(skhy_peer["underlying_market"], "KRX")


if __name__ == "__main__":
    unittest.main()
