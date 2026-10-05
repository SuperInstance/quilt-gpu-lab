#!/usr/bin/env python3
"""D12u1: calibrate the order-statistics model's absolute constant.

D12u found the M1 model (partner ~ N(s^alpha, sigma), nulls ~ N(0, sigma),
alpha=1.92, sigma=1/sqrt(W*T)) reproduces alpha_disc ~ 4 but floors are ~400x
above the harness (model C ~ 500 vs harness C_hat ~ 1.4). Hypothesis: the
model's ideal-Gaussian null is too easy (real nulls from N-1 finite-T
correlations have fatter tails). Calibrate a single variance multiplier k:
    sigma = k / sqrt(W*T)
by fitting k on a subset of (W, eps) harness floors from D12t, then test
heldout coverage on the rest. Falsifiable: k must be ONE number that covers
all heldout floors within 1.5x. If k needs to vary per cell by >2x, the
fatter-tail hypothesis fails and the constant gap is structural.

Seed 2718. CPU-only, seconds. No GPU, guard untouched.
"""
import json
import math
import os
from scipy.stats import norm

SEED = 2718
import numpy as np
rng = np.random.default_rng(SEED)

ALPHA_CORR = 1.92
P = 0.3

# Harness floors from D12t (draws=10): W -> [eps=0, 0.05, 0.1, 0.2]
FLOORS = {
    4:  [40, 60, 120, 320],
    8:  [20, 30, 60, 160],
    16: [15, 15, 30, 80],
}
EPS = [0.0, 0.05, 0.1, 0.2]
N_CELLS = 32  # N=32 -> 31 nulls

def model_floor(W, eps, k, n_mc=20000, threshold=0.5):
    """T at which discovery prob reaches threshold, coarse log grid then refine."""
    s = P * (1 - 2 * eps)
    if s <= 0:
        return float("inf")
    sig_mu = s ** ALPHA_CORR
    # solve: P(partner_est > max of 31 nulls) = threshold
    # partner_est ~ N(mu, sig); null_max ~ Gumbel-ish; use MC over null max dist
    # analytically: need z such that 1 - Phi((z - mu)/sig) * F_nullmax(z) ... just MC:
    def disc_prob(T):
        sig = k / math.sqrt(W * T)
        nul = rng.normal(0, sig, size=(n_mc, N_CELLS - 1)).max(axis=1)
        part = rng.normal(sig_mu, sig, size=n_mc)
        return float((part > nul).mean())
    lo, hi = 1.0, 100000.0
    if disc_prob(hi) < threshold:
        return float("inf")
    if disc_prob(lo) >= threshold:
        return lo
    for _ in range(40):
        mid = math.sqrt(lo * hi)
        if disc_prob(mid) >= threshold:
            hi = mid
        else:
            lo = mid
    return hi

def main():
    cells = [(W, e) for W in FLOORS for e in EPS]
    # fit k on W in {4, 8}, hold out W=16
    fit_cells = [(W, e) for W in (4, 8) for e in EPS]
    hold_cells = [(16, e) for e in EPS]

    # coarse k grid, minimize max ratio model/harness on fit cells
    best_k, best_obj = None, float("inf")
    for k in np.geomspace(0.05, 50, 60):
        ratios = []
        for (W, e) in fit_cells:
            f = model_floor(W, e, k)
            if math.isinf(f):
                ratios.append(100.0)
                continue
            ratios.append(f / FLOORS[W][EPS.index(e)])
        obj = max(max(ratios), 1.0 / min(ratios))
        if obj < best_obj:
            best_obj, best_k = obj, k
    k = float(best_k)
    print(f"fitted k = {k:.3f} (fit-set max deviation {best_obj:.2f}x)")

    results = {"seed": SEED, "k_fitted": k, "fit_cells": {}, "holdout": {}}
    for (W, e) in fit_cells:
        f = model_floor(W, e, k)
        results["fit_cells"][f"W{W}_eps{e}"] = {"model": f, "harness": FLOORS[W][EPS.index(e)]}
        print(f"fit    W={W:2d} eps={e}: model={f:7.1f} harness={FLOORS[W][EPS.index(e)]}")
    cover = 0
    for (W, e) in hold_cells:
        f = model_floor(W, e, k)
        h = FLOORS[W][EPS.index(e)]
        r = f / h
        ok = 0.67 <= r <= 1.5
        cover += ok
        results["holdout"][f"W{W}_eps{e}"] = {"model": f, "harness": h, "ratio": r, "covered": ok}
        print(f"hold   W={W:2d} eps={e}: model={f:7.1f} harness={h} ratio={r:.2f} {'COVERED' if ok else 'MISS'}")

    g1 = cover == len(hold_cells)
    # G2: k must be a single scale — fit-set cells each within 2x of model
    fit_within2 = all(0.5 <= v["model"] / v["harness"] <= 2.0 for v in results["fit_cells"].values())
    results["g1_holdout_4of4"] = g1
    results["g2_fit_within_2x"] = fit_within2
    results["verdict"] = "KEEP" if (g1 and fit_within2) else "KILL"
    print(f"G1 holdout {cover}/4; G2 fit-within-2x: {fit_within2} -> verdict {results['verdict']}")
    os.makedirs("results", exist_ok=True)
    with open("results/d12u1_calibrated_null_variance.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
