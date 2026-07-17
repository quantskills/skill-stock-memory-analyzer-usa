import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")

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

    def test_readme_explains_evaluation_model(self):
        required_sections = (
            "## 核心评估逻辑",
            "### 第一层：存储周期评分",
            "### 第二层：最终研究信号",
            "## 评估方面",
            "## Skill 特色",
        )
        for section in required_sections:
            self.assertIn(section, self.readme)

        for formula_term in (
            "0.10 × 短期技术",
            "0.25 × 存储周期",
            "0.12 × 分析师",
            "财务质量修正",
            "clamp(S, 10, 95)",
        ):
            self.assertIn(formula_term, self.readme)

        self.assertIn("不是买卖建议、目标价、上涨概率或收益承诺", self.readme)
        self.assertIn("相关性诊断", self.readme)


if __name__ == "__main__":
    unittest.main()
