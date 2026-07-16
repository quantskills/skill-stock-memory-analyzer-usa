import unittest

from tests.test_industry_refresh import valid_candidate
from utils.industry_refresh import apply_runtime_snapshot
from utils.memory_analyzer import analyze_hbm_gpu_demand


class MemoryRuntimeSnapshotTests(unittest.TestCase):
    def test_model_uses_runtime_revenue_units_and_gpu_capacities(self):
        industry_data = apply_runtime_snapshot({}, valid_candidate())
        result = analyze_hbm_gpu_demand(industry_data)
        quarter = result["demand_by_quarter"][0]
        self.assertEqual(quarter["compute_rev_100m_usd"], 604)
        self.assertAlmostEqual(quarter["avg_hbm_per_gpu_gb"], 232.1, places=1)
        self.assertAlmostEqual(result["supply_by_year"]["2025"], 652.5, places=1)


if __name__ == "__main__":
    unittest.main()
