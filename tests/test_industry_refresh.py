import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from utils.industry_refresh import (
    SnapshotValidationError,
    apply_runtime_snapshot,
    host_is_allowed,
    promote_snapshot,
    select_latest_sources,
    validate_snapshot,
)
from utils.data_updater import get_data_freshness


FIXTURE = Path(__file__).parent / "fixtures" / "industry_candidate_valid.json"
NOW = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)


def valid_candidate():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class SnapshotValidationTests(unittest.TestCase):
    def test_valid_candidate_passes(self):
        validated = validate_snapshot(valid_candidate(), now=NOW)
        self.assertEqual(set(validated["modules"]), {
            "gpu_specs", "nvda_compute_revenue", "gpu_shipments", "gpu_mix", "hbm_supply"
        })

    def test_domain_boundary_is_exact(self):
        self.assertTrue(host_is_allowed("docs.nvidia.com"))
        self.assertTrue(host_is_allowed("www.nvidia.cn"))
        self.assertFalse(host_is_allowed("nvidia.com.attacker.example"))
        self.assertFalse(host_is_allowed("evilnvidia.com"))

    def test_missing_module_is_rejected(self):
        candidate = valid_candidate()
        del candidate["modules"]["gpu_mix"]
        with self.assertRaisesRegex(SnapshotValidationError, "missing_modules"):
            validate_snapshot(candidate, now=NOW)

    def test_redirect_to_third_party_is_rejected(self):
        candidate = valid_candidate()
        candidate["modules"]["gpu_specs"]["sources"][0]["final_url"] = "https://example.com/copied"
        with self.assertRaisesRegex(SnapshotValidationError, "source_domain"):
            validate_snapshot(candidate, now=NOW)

    def test_estimate_contract_is_required(self):
        candidate = valid_candidate()
        del candidate["modules"]["gpu_shipments"]["limitations"]
        with self.assertRaisesRegex(SnapshotValidationError, "estimate_contract"):
            validate_snapshot(candidate, now=NOW)

    def test_mix_ratios_must_sum_to_one(self):
        candidate = valid_candidate()
        candidate["modules"]["gpu_mix"]["data"]["ratios"]["2026"]["B300"] = 0.2
        with self.assertRaisesRegex(SnapshotValidationError, "gpu_mix_ratio"):
            validate_snapshot(candidate, now=NOW)

    def test_source_must_be_retrieved_this_run(self):
        candidate = valid_candidate()
        candidate["modules"]["gpu_specs"]["sources"][0]["retrieved_this_run"] = False
        with self.assertRaisesRegex(SnapshotValidationError, "not_retrieved"):
            validate_snapshot(candidate, now=NOW)

    def test_unresolved_conflict_is_rejected(self):
        candidate = valid_candidate()
        candidate["modules"]["gpu_specs"]["conflicts"] = [{"status": "unresolved"}]
        with self.assertRaisesRegex(SnapshotValidationError, "source_conflict"):
            validate_snapshot(candidate, now=NOW)


class SnapshotStorageTests(unittest.TestCase):
    def test_invalid_candidate_does_not_replace_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            current = runtime / "industry_snapshot.json"
            current.write_text('{"sentinel": true}', encoding="utf-8")
            bad = valid_candidate()
            del bad["modules"]["hbm_supply"]
            with self.assertRaises(SnapshotValidationError):
                promote_snapshot(bad, runtime, ticker="MU", now=NOW)
            self.assertEqual(json.loads(current.read_text(encoding="utf-8")), {"sentinel": True})

    def test_valid_candidate_promotes_and_preserves_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            old = valid_candidate()
            old["refresh_id"] = "old"
            (runtime / "industry_snapshot.json").write_text(json.dumps(old), encoding="utf-8")
            promote_snapshot(valid_candidate(), runtime, ticker="MU", now=NOW)
            self.assertEqual(json.loads((runtime / "industry_snapshot.json").read_text(encoding="utf-8"))["refresh_id"], "20260716T180000Z")
            self.assertEqual(json.loads((runtime / "industry_snapshot.previous.json").read_text(encoding="utf-8"))["refresh_id"], "old")
            manifest = json.loads((runtime / "industry_run.json").read_text(encoding="utf-8"))
            self.assertEqual((manifest["ticker"], manifest["mode"]), ("MU", "fresh"))

    def test_source_selection_uses_as_of_not_response_order(self):
        sources = [
            {"as_of": "2025-Q4", "published_at": "2026-01-01", "source_type": "company_ir"},
            {"as_of": "2026-Q1", "published_at": "2026-05-01", "source_type": "regional_product_page"},
        ]
        self.assertEqual(select_latest_sources(sources)[0]["as_of"], "2026-Q1")

    def test_overlay_does_not_mutate_static_sections(self):
        base = {"dram_contract_price_qoq": {"2026-Q1": 1}, "gpu_hbm_specs": {"old": True}}
        result = apply_runtime_snapshot(base, valid_candidate())
        self.assertEqual(base["gpu_hbm_specs"], {"old": True})
        self.assertEqual(result["dram_contract_price_qoq"], base["dram_contract_price_qoq"])
        self.assertEqual(result["gpu_hbm_specs"]["generations"][1]["hbm_capacity_gb"], 180)
        self.assertIn("nvda_quarterly_revenue", result["gpu_hbm_specs"])
        self.assertEqual(result["gpu_hbm_specs"]["nvda_quarterly_revenue"]["2026-Q1"], 604)

    def test_shipment_formula_uses_consistent_units(self):
        formula = valid_candidate()["modules"]["gpu_shipments"]["formula"]
        self.assertEqual(
            formula,
            "shipments_k = compute_revenue_b_usd * 1000 / weighted_asp_k_usd",
        )

    def test_runtime_freshness_uses_module_verification(self):
        freshness = get_data_freshness(snapshot=valid_candidate(), run_mode="fresh", now=NOW)
        self.assertEqual(freshness["gpu_specs"]["status"], "fresh")
        self.assertEqual(freshness["gpu_specs"]["age_days"], 0)
        self.assertEqual(
            get_data_freshness(snapshot=valid_candidate(), run_mode="cached-authorized", now=NOW)["gpu_specs"]["status"],
            "cached-authorized",
        )


if __name__ == "__main__":
    unittest.main()
