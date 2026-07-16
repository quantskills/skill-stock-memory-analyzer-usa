import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tests.test_industry_refresh import NOW, valid_candidate
from utils.industry_refresh import (
    RunManifestError,
    authorize_current_snapshot,
    claim_run_manifest,
    precheck_run_manifest,
    promote_snapshot,
)


class IndustryGateTests(unittest.TestCase):
    def test_manifest_is_ticker_bound_and_single_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            promote_snapshot(valid_candidate(), runtime, ticker="MU", now=NOW)
            manifest_path = runtime / "industry_run.json"
            with self.assertRaisesRegex(RunManifestError, "ticker_mismatch"):
                precheck_run_manifest(manifest_path, "WDC", now=NOW)
            claimed = claim_run_manifest(manifest_path, "MU", now=NOW)
            self.assertEqual(claimed["mode"], "fresh")
            self.assertFalse(manifest_path.exists())
            with self.assertRaisesRegex(RunManifestError, "manifest_missing"):
                precheck_run_manifest(manifest_path, "MU", now=NOW)

    def test_expired_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            promote_snapshot(valid_candidate(), runtime, ticker="MU", now=NOW)
            path = runtime / "industry_run.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["expires_at"] = "2026-07-16T11:59:59+00:00"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(RunManifestError, "manifest_expired"):
                precheck_run_manifest(path, "MU", now=NOW)

    def test_cached_authorization_requires_valid_current_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            with self.assertRaisesRegex(RunManifestError, "snapshot_missing"):
                authorize_current_snapshot(runtime, "failed-refresh", "MU", ["gpu_specs"], now=NOW)

            promote_snapshot(valid_candidate(), runtime, ticker="MU", now=NOW)
            manifest = authorize_current_snapshot(runtime, "failed-refresh", "MU", ["gpu_specs"], now=NOW)
            self.assertEqual(manifest["mode"], "cached-authorized")
            self.assertEqual(manifest["failed_modules"], ["gpu_specs"])
            self.assertEqual(precheck_run_manifest(runtime / "industry_run.json", "MU", now=NOW)["mode"], "cached-authorized")


if __name__ == "__main__":
    unittest.main()
