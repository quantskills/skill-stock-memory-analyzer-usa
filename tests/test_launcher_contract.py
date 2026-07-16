import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class LauncherContractTests(unittest.TestCase):
    def test_windows_prechecks_industry_before_credentials(self):
        content = (ROOT / "scripts" / "run_with_prompt.ps1").read_text(encoding="utf-8")
        self.assertIn("IndustryRunManifest", content)
        self.assertIn("industry_refresh.py", content)
        self.assertLess(content.index("industry_refresh.py"), content.index('Read-Host "panda_data account"'))
        self.assertIn("--industry-run-manifest", content)

    def test_macos_prechecks_industry_before_credentials(self):
        content = (ROOT / "scripts" / "run_with_prompt.sh").read_text(encoding="utf-8")
        self.assertIn("--industry-run-manifest", content)
        self.assertIn("industry_refresh.py", content)
        self.assertLess(content.index("industry_refresh.py"), content.index("read -r -p 'panda_data account"))
        self.assertNotIn("PANDA_DATA_PASSWORD=\"$2\"", content)


if __name__ == "__main__":
    unittest.main()
