#!/usr/bin/env python3
"""D12am — constant-c invariance test of the rho^2 variance-inflation law.

D12al (KILL per frozen gates, booked) showed G3's [3,5] band was mis-specified:
in the implemented parametrization inflation = 1 + c*rho^2, constant c predicts
implied-c ratio ~1.0; ratio ~4 corresponds to a rho^4 alternative. D12al's data
support one rho-independent c ~ 26-35 (implied-c ratios 1.19/1.37).

This run is pre-registered in proposals/runs/D12am-constant-c-prereg-2026-10-10.md
(frozen before firing). Denser T grid (160 pts vs 80). Gates:
  G1 fit sanity: model rho=0.2 blow-up / measured in [0.8, 1.25] both W.
  G2 heldout: rho=0.4 blow-up with SAME c / measured in [0.67, 1.5] both W.
  G3 constant-c invariance: implied c(0.4)/c_fit(0.2) in [0.67, 1.5] both W.
  G4 cross-W universality: c_implied(W=8)/c_implied(W=16) in [0.5, 2.0].
Verdict KEEP iff all PASS. Seed 2718, CPU-only. Ratios only (absolute model
floors are known ~3x off measured).
"""
import json
import math
import os
import numpy as np

rng = np.random.default_rng(2718)
NS = 20000
N_NULLS = 62

MEAS = {(8, 0.0): 25, (8, 0.2): 50, (8, 0.4): 160,
        (16, 0.0): 12, (16, 0.2): 25, (16, 0.4): 80}
P, EPS = 0.3, 0.0
SIG_DECAY = (P * (1 - 2 * EPS)) ** 1.92
T_GRID = np.unique(np.round(np.logspace(math.log10(5), math.log10(4000), 160)).astype(int))


def floor_at(W, c):
    """Model floor (min T with P[partner>max nulls]>=0.5) for inflation 1+c."""
    for T in T_GRID:
        sig = 1.0 / math.sqrt(W * T)
        partner = rng.normal(SIG_DECAY, sig, NS)
        nulls = rng.normal(0.0, math.sqrt(1.0 + c) * sig, (NS, N_NULLS))
        if float(np.mean(partner > nulls.max(axis=1))) >= 0.5:
            return int(T)
    return None


def fit_c(W, rho, base, hi0=2000.0, steps=25):
    """Bisect c so model blow-up matches measured blow-up at this rho."""
    target = MEAS[(W, rho)] / MEAS[(W, 0.0)]
    lo, hi = 0.0, hi0
    for _ in range(steps):
        mid = 0.5 * (lo + hi)
        f = floor_at(W, mid * rho * rho) or 10 ** 9
        if f / base > target:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def main():
    results = {}
    for W in (8, 16):
        base = floor_at(W, 0.0)
        c_fit = fit_c(W, 0.2, base)
        pred_04 = floor_at(W, c_fit * 0.16)
        c_impl = fit_c(W, 0.4, base)
        blowup_02 = pred_02 = None  # G1 re-eval below keeps call order fixed
        pred_02 = floor_at(W, c_fit * 0.04)
        results[W] = {
            "base_floor": base,
            "c_fit_rho02": c_fit,
            "pred_floor_rho02": pred_02,
            "pred_floor_rho04": pred_04,
            "meas_floor_rho04": MEAS[(W, 0.4)],
            "g1_ratio": (pred_02 / base) / (MEAS[(W, 0.2)] / MEAS[(W, 0.0)]),
            "g2_ratio": (pred_04 / base) / (MEAS[(W, 0.4)] / MEAS[(W, 0.0)]),
            "g3_ratio": c_impl / c_fit,
            "c_implied_rho04": c_impl,
        }
        r = results[W]
        print(f"W={W}: base={base} c_fit={c_fit:.2f} pred02={pred_02} "
              f"pred04={pred_04} c_impl={c_impl:.2f} "
              f"G1={r['g1_ratio']:.3f} G2={r['g2_ratio']:.3f} G3={r['g3_ratio']:.3f}")

    g1 = all(0.8 <= results[W]["g1_ratio"] <= 1.25 for W in results)
    g2 = all(0.67 <= results[W]["g2_ratio"] <= 1.5 for W in results)
    g3 = all(0.67 <= results[W]["g3_ratio"] <= 1.5 for W in results)
    g4 = 0.5 <= results[8]["c_implied_rho04"] / results[16]["c_implied_rho04"] <= 2.0
    verdict = "KEEP" if (g1 and g2 and g3 and g4) else "KILL"
    print(f"G1={g1} G2={g2} G3={g3} G4={g4} -> VERDICT {verdict}")

    out = {
        "name": "d12am_constant_c",
        "seed": 2718,
        "prereg": "proposals/runs/D12am-constant-c-prereg-2026-10-10.md",
        "model": "nulls ~ N(0,(1+c*rho^2)/(WT)); partner ~ N(s^1.92,1/(WT)); "
                 "ratios vs own rho=0 baseline; P_succ>=0.5, 20k MC, 160-pt T grid",
        "s_decay": SIG_DECAY,
        "gates": {"G1_fit_sanity": [0.8, 1.25], "G2_heldout": [0.67, 1.5],
                  "G3_constant_c": [0.67, 1.5], "G4_cross_W": [0.5, 2.0]},
        "results": results,
        "G1": bool(g1), "G2": bool(g2), "G3": bool(g3), "G4": bool(g4),
        "verdict": verdict,
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "results", "d12am_constant_c.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(f"saved {os.path.abspath(path)}")


if __name__ == "__main__":
    main()
