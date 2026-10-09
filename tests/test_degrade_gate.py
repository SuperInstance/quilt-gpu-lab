import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from tools.degrade_gate import run_gate, RC_PASS, RC_FAIL


class TestDegradeGateTieSemantics(unittest.TestCase):
    """TIE-1a (2026-10-08): pin the tolerance tie case — delta == tolerance is NOT flagged."""

    def test_delta_tie_not_flagged__tie_1a(self):
        # benefit RISES by exactly tolerance at the step: permissive at tie, GRACEFUL
        pts = [{"param": 70, "benefit": 0.90}, {"param": 45, "benefit": 1.00}]
        rc, receipt = run_gate(pts, tolerance=0.10)
        self.assertEqual(rc, RC_PASS)
        self.assertEqual(receipt["reasons"], [])

    def test_delta_just_above_tolerance_flagged__tie_1a(self):
        pts = [{"param": 70, "benefit": 0.90}, {"param": 45, "benefit": 1.000001}]
        rc, receipt = run_gate(pts, tolerance=0.10)
        self.assertEqual(rc, RC_FAIL)
        self.assertTrue(any("INVERTED" in r for r in receipt["reasons"]))

    def test_delta_below_tolerance_not_flagged__tie_1a(self):
        pts = [{"param": 70, "benefit": 0.90}, {"param": 45, "benefit": 0.95}]
        rc, receipt = run_gate(pts, tolerance=0.10)
        self.assertEqual(rc, RC_PASS)

    def test_default_tolerance_zero_flags_any_rise(self):
        pts = [{"param": 70, "benefit": 0.50}, {"param": 45, "benefit": 0.6000001}]
        rc, receipt = run_gate(pts)
        self.assertEqual(rc, RC_FAIL)
        self.assertTrue(any("INVERTED" in r for r in receipt["reasons"]))


if __name__ == "__main__":
    unittest.main()
