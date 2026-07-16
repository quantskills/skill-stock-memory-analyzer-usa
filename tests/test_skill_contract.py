import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

    def test_refresh_precedes_local_login(self):
        self.assertIn("五个必需模块", self.skill)
        self.assertIn("industry_refresh.py validate", self.skill)
        self.assertIn("industry_refresh.py commit", self.skill)
        self.assertLess(self.skill.index("industry_refresh.py commit"), self.skill.index("scripts/run_with_prompt.ps1"))

    def test_explicit_cached_decision_is_required(self):
        self.assertIn("是否允许本次使用旧数据继续分析", self.skill)
        self.assertIn("authorize-current", self.skill)
        self.assertIn("用户未回复", self.skill)

    def test_regional_official_sources_are_named(self):
        for domain in ("nvidia.cn", "investor.nvidia.com", "micron.cn", "news.skhynix.com", "news.samsung.com", "investor.tsmc.com"):
            self.assertIn(domain, self.skill)

    def test_chat_never_requests_credentials(self):
        self.assertIn("不得要求用户在聊天中发送凭据", self.skill)
        self.assertNotIn("登录验证成功前不执行分析、不浏览网页补数", self.skill)


if __name__ == "__main__":
    unittest.main()
