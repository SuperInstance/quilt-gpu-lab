"""test_pidfire.py — pins for the PIDFIRE-1 ported semantics (frozen pre-reg
proposals/runs/PIDFIRE-1-servo-soc.md; mirrors upstream crate tests where noted)."""
import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "experiments"))
from pidfire_common import (  # noqa: E402
    TernaryPid, fit_powerlaw, ks_one_sample, ks_two_sample, ks_two_sample_gate,
    mle_tau, run_fixed, step_grid,
)


class TestPidPort(unittest.TestCase):
    def test_textbook_formula_parity(self):
        """Mirror of upstream test_discrete_pid_math_matches_textbook_formula:
        u[n] = Kp*e[n] + Ki*sum(e[0..=n]) + Kd*(e[n]-e[n-1]), alpha=1, no clamp."""
        pid = TernaryPid(2.0, 0.5, 1.0)
        pid.derivative_filter = 1.0
        pid.integral_limit = float("inf")
        sp = 10.0
        manual_integral = 0.0
        prev_error = 0.0
        initialized = False
        for m in (0.0, 3.0, 7.0, 9.0, 11.0):
            e = sp - m
            manual_integral += e
            d_term = (e - prev_error) if initialized else 0.0
            expected = 2.0 * e + 0.5 * manual_integral + 1.0 * d_term
            raw = pid.update_raw(sp, m)
            self.assertAlmostEqual(raw, expected, places=12)
            prev_error = e
            initialized = True

    def test_proportional_sign(self):
        pid = TernaryPid(1.0, 0.0, 0.0)
        self.assertEqual(pid.update(10.0, 5.0), 1)
        self.assertEqual(pid.update(5.0, 10.0), -1)

    def test_deadband_and_bleed(self):
        pid = TernaryPid(1.0, 0.0, 0.0)
        pid.deadband = 1.0
        self.assertEqual(pid.update(10.0, 9.5), 0)   # |e|=0.5 < 1
        pid.integral = 1.0
        self.assertEqual(pid.update(10.0, 9.5), 0)
        self.assertAlmostEqual(pid.integral, 0.95, places=12)  # x0.95 bleed
        self.assertEqual(pid.update(10.0, 8.0), 1)   # |e|=2 outside

    def test_deadband_does_not_break_derivative(self):
        """Upstream regression: deadband must keep prev_error consistent."""
        pid = TernaryPid(0.0, 0.0, 10.0)
        pid.deadband = 1.0
        self.assertEqual(pid.update(10.0, 10.0), 0)
        self.assertEqual(pid.update(10.0, 9.5), 0)
        self.assertEqual(pid.update(10.0, 5.0), 1)

    def test_anti_windup(self):
        pid = TernaryPid(0.0, 1.0, 0.0)
        pid.integral_limit = 10.0
        for _ in range(1000):
            pid.update(100.0, 0.0)
        self.assertLessEqual(pid.integral, 10.0)
        raw = pid.update_raw(100.0, 0.0)
        self.assertAlmostEqual(raw, 10.0, places=9)  # saturates at ki*Ilim

    def test_integral_memory_holds_output(self):
        pid = TernaryPid(0.0, 0.1, 0.0)
        for _ in range(10):
            pid.update(10.0, 9.0)  # e = +1
        self.assertGreater(pid.integral, 0.0)
        self.assertEqual(pid.update(10.0, 10.0), 1)  # memory holds after e -> 0


class TestCaPort(unittest.TestCase):
    def test_ignition_and_old_grid_spread(self):
        """3x3 all trees, ignite center, p=1: step1 -> only center burns (upstream
        test_step_ignition); step2 -> 4 neighbors burn, center empties (spread reads
        the OLD grid; burning lasts exactly one step)."""
        rng = np.random.default_rng(1)
        tree = np.ones((3, 3), dtype=bool)
        burn = np.zeros((3, 3), dtype=bool)
        shadow = np.zeros((3, 3), dtype=np.int32)
        tree, burn = step_grid(tree, burn, shadow, 1.0, 0.0, rng, ignite_idx=(1, 1))
        self.assertEqual(int(burn.sum()), 1)
        self.assertTrue(burn[1, 1])
        self.assertEqual(int(tree.sum()), 8)
        tree, burn = step_grid(tree, burn, shadow, 1.0, 0.0, rng)
        self.assertFalse(burn[1, 1])          # burned -> empty
        self.assertEqual(int(burn.sum()), 4)  # 4 von Neumann neighbors caught
        self.assertEqual(int(tree.sum()), 4)

    def test_growth_and_shadow_exclusion(self):
        rng = np.random.default_rng(2)
        tree = np.zeros((4, 4), dtype=bool)
        burn = np.zeros((4, 4), dtype=bool)
        shadow = np.zeros((4, 4), dtype=np.int32)
        shadow[0, 0] = 128
        tree, burn = step_grid(tree, burn, shadow, 0.5, 1.0, rng)
        self.assertFalse(tree[0, 0])          # shadow cell cannot grow
        self.assertTrue(tree[1, 1])           # q=1 -> all others grow
        self.assertEqual(int(tree.sum()), 15)

    def test_no_spread_p_zero(self):
        rng = np.random.default_rng(3)
        tree = np.array([[True, True, True]])
        burn = np.array([[False, True, False]])
        shadow = np.zeros((1, 3), dtype=np.int32)
        tree, burn = step_grid(tree, burn, shadow, 0.0, 0.0, rng)
        self.assertFalse(burn.any())          # burning -> empty, nothing catches
        self.assertEqual(int(tree.sum()), 3)

    def test_catch_probability_two_neighbors(self):
        """Per-tree catch w.p. 1-(1-p)^k (distribution-equal to sequential per-edge
        trials). Row [T,B,T,B,T]: center tree has k=2 burning neighbors."""
        rng = np.random.default_rng(4)
        n, hits_k2, hits_k1 = 4000, 0, 0
        for _ in range(n):
            tree = np.array([[True, True, True, True, True]])
            burn = np.array([[False, True, False, True, False]])
            shadow = np.zeros((1, 5), dtype=np.int32)
            _, burn2 = step_grid(tree, burn, shadow, 0.5, 0.0, rng)
            hits_k2 += int(burn2[0, 2])
            hits_k1 += int(burn2[0, 0]) + int(burn2[0, 4])
        self.assertAlmostEqual(hits_k2 / n, 0.75, delta=0.03)   # 1-(1-.5)^2
        self.assertAlmostEqual(hits_k1 / (2 * n), 0.5, delta=0.03)

    def test_run_fixed_smoke_and_determinism(self):
        a = run_fixed(1.0, 0.01, 7, 0.5, t_total=3000, t_transient=1000)
        b = run_fixed(1.0, 0.01, 7, 0.5, t_total=3000, t_transient=1000)
        self.assertEqual(a[0], b[0])          # deterministic per seed
        self.assertTrue(len(a[0]) >= 1)       # fires happened
        self.assertTrue(all(s >= 1 for s in a[0]))
        self.assertLessEqual(len(a[0]), 2000)  # cannot exceed measure window
        self.assertTrue(max(a[0]) >= 2)       # p=1 fires spread beyond the struck cell


class TestStats(unittest.TestCase):
    def test_mle_tau_recovers_synthetic(self):
        # Sample the finite-support discrete power law the pipeline assumes
        # (support [1, 16384] = grid area, weights k^-tau), tau_true = 1.2.
        rng = np.random.default_rng(5)
        support = np.arange(1, 16_385, dtype=np.float64)
        w = support ** (-1.2)
        p = w / w.sum()
        sizes = rng.choice(support.astype(int), size=50_000, p=p).tolist()
        tau_hat, s_min, d_ks, n_tail = fit_powerlaw(sizes)
        self.assertGreaterEqual(n_tail, 1000)
        # Bounded-support bias BOOKED: the CSM discrete MLE assumes support->inf;
        # truncation at S=16384 removes ln-tail mass (P(s>10^3)=0.25 at tau=1.2),
        # biasing tau_hat UP by ~+0.12 here. Same bias applies to reference and
        # eval arms alike -> cancels in the comparison gates (C3, reaches-SOC).
        self.assertLessEqual(abs(tau_hat - 1.2), 0.13)
        self.assertGreaterEqual(tau_hat, 1.2)  # bias direction pinned: upward
        # Amended cell-SOC self-KS bar is 0.10 (annotated pre-run); synthetic sample
        # at the biased MLE floors ~0.11, so the PIN uses 0.13 as the synthetic-side
        # sanity bound (the experiment's scan window selection differs on real data).
        self.assertLessEqual(d_ks, 0.13)

    def test_ks_two_sample_identical_is_zero(self):
        self.assertEqual(ks_two_sample([1, 2, 3, 4], [1, 2, 3, 4]), 0.0)

    def test_ks_one_sample_perfect_fit_small(self):
        # tau -> inf collapses support; use tau=2 over [1,3]: F = (1, 1.25/1.3611, 1)
        sizes = [1, 1, 2, 3, 3]
        d = ks_one_sample(sizes, 2.0, 1)
        self.assertGreater(d, 0.0)
        self.assertLess(d, 1.0)

    def test_gate_formula(self):
        g = ks_two_sample_gate(300, 300)
        expected = max(0.10, 1.358 * math.sqrt(600 / 90_000))
        self.assertAlmostEqual(g, expected, places=9)


if __name__ == "__main__":
    unittest.main()
