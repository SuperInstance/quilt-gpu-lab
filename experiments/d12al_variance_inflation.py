#!/usr/bin/env python3
"""D12al — variance-inflation model of the dependent-null floor blow-up (v2).

D12aj measured MC discovery floors under common-mode dependence rho:
  W=8,  eps=0, p=0.3: rho=0 -> 25, rho=0.2 -> 50 (2.00x), rho=0.4 -> 160 (6.40x)
  W=16, eps=0, p=0.3: rho=0 -> 12, rho=0.2 -> 25 (2.08x), rho=0.4 -> 80 (6.67x)
D12ak killed the mean-shift explanation. Candidate: common mode inflates the
NULL TAIL VARIANCE: nulls ~ N(0, (1+c*rho^2)/(WT)), partner unchanged
~ N(s^1.92, 1/(WT)). Since floors scale ~ sigma_eff^2, the model blow-up
ratio ~ (1 + c*rho^2) — test the rho^2 scaling of the tail inflation with
constant cancellation (v1 showed the absolute Gaussian baseline is ~3x off
the measured rho=0 floors, so absolute floors are not comparable; ratios are).

Gates (pre-registered):
  G1: with c fit to the rho=0.2 blow-up ratio, model ratio within [0.5,2]x of measured.
  G2: SAME c predicts the rho=0.4 blow-up ratio within [0.5,2]x (heldout, no refit).
  G3: ratio-based implied c(0.4)/c(0.2) in [3,5] (rho^2 scaling hypothesis = 4).

Model: MC bisection of the full order-statistics floor (20k samples,
P_succ >= 0.5) on a fine T grid; c fit by bisection on RATIOS so grid
quantization cancels. Seed 2718, CPU-only, seconds.
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
T_GRID = np.unique(np.round(np.logspace(math.log10(5), math.log10(4000), 80)).astype(int))


def floor_at(W, c):
    """Model floor (min T with P[partner>max nulls]>=0.5) for a given inflation c."""
    for T in T_GRID:
        sig = 1.0 / math.sqrt(W * T)
        sig_eff = math.sqrt(1.0 + c) * sig
        partner = rng.normal(SIG_DECAY, sig, NS)
        nulls = rng.normal(0.0, sig_eff, (NS, N_NULLS))
        if float(np.mean(partner > nulls.max(axis=1))) >= 0.5:
            return int(T)
    return None


def blowup(W, rho):
    """Model blow-up ratio floor(rho-inflated)/floor(rho=0), c = c_fit*rho^2."""
    return None


def main():
    out_rows = []
    results = {}
    for W in (8, 16):
        base = floor_at(W, 0.0)
        # fit c on rho=0.2 blow-up ratio (target 50/base vs measured 2.0-ish)
        target_02 = MEAS[(W, 0.2)] / MEAS[(W, 0.0)]
        lo, hi = 0.0, 1000.0
        for _ in range(25):
            mid = 0.5 * (lo + hi)
            r = (floor_at(W, mid * 0.04) or 10 ** 9) / base
            if r > target_02:
                hi = mid
            else:
                lo = mid
        c_fit = 0.5 * (lo + hi)
        # heldout: rho=0.4 with c*rho^2, no refit
        pred_04 = floor_at(W, c_fit * 0.16)
        meas_04 = MEAS[(W, 0.4)]
        # heldout compared RATIO-to-RATIO (model base vs measured base differ ~3x)
        ratio = ((pred_04 / base) / (meas_04 / MEAS[(W, 0.0)])) if pred_04 else None
        # diagnostic: implied c from the rho=0.4 blow-up directly
        target_04 = meas_04 / MEAS[(W, 0.0)]
        lo, hi = 0.0, 2000.0
        for _ in range(25):
            mid = 0.5 * (lo + hi)
            r = (floor_at(W, mid * 0.16) or 10 ** 9) / base
            if r > target_04:
                hi = mid
            else:
                lo = mid
        c_04 = 0.5 * (lo + hi)
        results[W] = {"base_floor": base, "c_fit_rho02": c_fit,
                      "pred_floor_rho04": pred_04, "meas_floor_rho04": meas_04,
                      "heldout_ratio": ratio, "c_implied_rho04": c_04,
                      "c_scaling_ratio": c_04 / c_fit if c_fit > 0 else None}
        print(f"W={W}: base={base} c_fit(rho=.2)={c_fit:.2f} "
              f"pred(rho=.4)={pred_04} meas={meas_04} ratio={ratio} "
              f"c_implied(.4)={c_04:.2f} c-scaling={results[W]['c_scaling_ratio']}")
        for rho in (0.0, 0.2, 0.4):
            out_rows.append({"W": W, "rho": rho,
                             "meas_floor": MEAS[(W, rho)],
                             "meas_blowup": MEAS[(W, rho)] / MEAS[(W, 0.0)]})

    g1 = True
    for W in (8, 16):
        pred_02 = floor_at(W, results[W]["c_fit_rho02"] * 0.04)
        # ratio-vs-ratio: model blow-up vs measured blow-up (baseline constants cancel)
        r = (pred_02 / results[W]["base_floor"]) / (MEAS[(W, 0.2)] / MEAS[(W, 0.0)])
        g1 &= r is not None and 0.5 <= r <= 2.0
        print(f"W={W} rho=0.2 model_blowup={pred_02 / results[W]['base_floor']:.2f} "
              f"meas_blowup={MEAS[(W, 0.2)] / MEAS[(W, 0.0)]:.2f} ratio={r:.2f}")
    g2 = all(r["heldout_ratio"] and 0.5 <= r["heldout_ratio"] <= 2.0
             for r in results.values())
    g3 = all(3.0 <= r["c_scaling_ratio"] <= 5.0 for r in results.values())
    verdict = "KEEP" if (g1 and g2 and g3) else "KILL"
    print(f"G1={g1} G2={g2} G3={g3} -> VERDICT {verdict}")

    out = {"name": "d12al_variance_inflation", "seed": 2718, "v": 2,
           "model": "nulls ~ N(0,(1+c*rho^2)/(WT)); partner ~ N(s^1.92,1/(WT)); "
                    "ratios vs own rho=0 baseline (constants cancel); P_succ>=0.5, 20k MC",
           "s_decay": SIG_DECAY, "results": results, "G1": bool(g1), "G2": bool(g2),
           "G3": bool(g3), "verdict": verdict, "measured_rows": out_rows}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "results", "d12al_variance_inflation.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(f"saved {os.path.abspath(path)}")


if __name__ == "__main__":
    main()
