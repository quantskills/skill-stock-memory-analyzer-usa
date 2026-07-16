import unittest

from tests.test_industry_refresh import valid_candidate
from utils.industry_refresh import build_industry_snapshot_html


class IndustrySnapshotReportTests(unittest.TestCase):
    def test_fresh_report_distinguishes_facts_and_estimates(self):
        html = build_industry_snapshot_html(valid_candidate(), "fresh")
        self.assertIn("本轮已核验", html)
        self.assertIn("事实", html)
        self.assertIn("模型估算", html)
        self.assertIn("verified_at", html)
        self.assertIn("模型假设", html)
        self.assertIn("https://docs.nvidia.com/", html)
        self.assertNotIn("9天前", html)

    def test_cached_report_has_prominent_warning(self):
        html = build_industry_snapshot_html(valid_candidate(), "cached-authorized")
        self.assertIn("本次使用上一份行业数据", html)
        self.assertIn("用户已明确授权", html)

    def test_source_text_is_escaped(self):
        candidate = valid_candidate()
        candidate["modules"]["gpu_specs"]["sources"][0]["title"] = "<script>alert(1)</script>"
        html = build_industry_snapshot_html(candidate, "fresh")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
