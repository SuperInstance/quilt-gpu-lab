import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from tools.verdict_gate import Gate, StatMeta, finalize


class TestVerdictGate(unittest.TestCase):
    def test_pass_clean(self):
        v = finalize([Gate("auc", 0.91, minimum=0.80)],
                     {"auc": StatMeta(std=0.03, n=32)}, completeness=True,
                     status_source="own")
        self.assertEqual(v.verdict, "PASS")

    def test_fail_when_gate_missed(self):
        v = finalize([Gate("auc", 0.70, minimum=0.80)],
                     {"auc": StatMeta(std=0.03, n=32)}, completeness=True,
                     status_source="own")
        self.assertEqual(v.verdict, "FAIL")

    def test_zero_variance_never_passes__murmuration_law(self):
        # std==0 with a nominally passing value still cannot PASS (F1 G1 class)
        v = finalize([Gate("g1", 0.95, minimum=0.90)],
                     {"g1": StatMeta(std=0.0, n=100)}, completeness=True,
                     status_source="own")
        self.assertEqual(v.verdict, "DEGENERATE")

    def test_saturation_attestation_degenerate__w5a_class(self):
        v = finalize([Gate("det_err", 0.0, maximum=0.1)],
                     {"det_err": StatMeta(std=0.2, n=24, saturated=True)},
                     completeness=True, status_source="own")
        self.assertEqual(v.verdict, "DEGENERATE")

    def test_single_observation_degenerate(self):
        v = finalize([Gate("auc", 0.99, minimum=0.80)],
                     {"auc": StatMeta(std=None, n=1)}, completeness=True,
                     status_source="own")
        self.assertEqual(v.verdict, "DEGENERATE")

    def test_truncated_never_passes__trunc_b(self):
        # the 09:1x tmpfs/tail class: plausible numbers, incomplete output
        v = finalize([Gate("auc", 0.91, minimum=0.80)],
                     {"auc": StatMeta(std=0.03, n=32)}, completeness=False,
                     status_source="own")
        self.assertEqual(v.verdict, "INCONCLUSIVE")

    def test_missing_completeness_attestation_is_void(self):
        v = finalize([Gate("auc", 0.91, minimum=0.80)],
                     {"auc": StatMeta(std=0.03, n=32)}, completeness=None,
                     status_source="own")
        self.assertEqual(v.verdict, "VOID")

    def test_inherited_status_is_void__convergence_shape3(self):
        v = finalize([Gate("auc", 0.91, minimum=0.80)],
                     {"auc": StatMeta(std=0.03, n=32)}, completeness=True,
                     status_source="inherited")
        self.assertEqual(v.verdict, "VOID")

    def test_missing_gate_value_inconclusive(self):
        v = finalize([Gate("auc", None, minimum=0.80)],
                     {"auc": StatMeta(std=0.03, n=32)}, completeness=True,
                     status_source="own")
        self.assertEqual(v.verdict, "INCONCLUSIVE")

    def test_degenerate_outranks_truncation_void_ordering(self):
        # VOID (status source) outranks everything
        v = finalize([Gate("g", 1.0, minimum=0.0)],
                     {"g": StatMeta(std=0.0, n=10)}, completeness=False,
                     status_source="inherited")
        self.assertEqual(v.verdict, "VOID")

    def test_max_gates(self):
        v = finalize([Gate("fpr", 0.05, maximum=0.10)],
                     {"fpr": StatMeta(std=0.01, n=50)}, completeness=True,
                     status_source="own")
        self.assertEqual(v.verdict, "PASS")
        v2 = finalize([Gate("fpr", 0.80, maximum=0.10)],
                      {"fpr": StatMeta(std=0.01, n=50)}, completeness=True,
                      status_source="own")
        self.assertEqual(v2.verdict, "FAIL")


if __name__ == "__main__":
    unittest.main()

    def test_boundless_gate_vacuous_fails_closed__param_1a(self):
        # PARAM-1a: an evaluated gate with NO bound can never fail => finalize must FAIL.
        v = finalize([Gate("auc", 0.91)],
                     {"auc": StatMeta(std=0.03, n=32)}, completeness=True,
                     status_source="own")
        self.assertEqual(v.verdict, "FAIL")
        self.assertIn("vacuous", " ".join(v.reasons))

    def test_boundless_never_masks_void(self):
        # precedence: VOID still beats the vacuous-gate FAIL
        v = finalize([Gate("auc", 0.91)], {"auc": StatMeta(std=0.03, n=32)},
                     completeness=None, status_source="own")
        self.assertEqual(v.verdict, "VOID")

    def test_boundless_never_masks_degenerate(self):
        v = finalize([Gate("g1", 0.95)], {"g1": StatMeta(std=0.0, n=100)},
                     completeness=True, status_source="own")
        self.assertEqual(v.verdict, "DEGENERATE")
