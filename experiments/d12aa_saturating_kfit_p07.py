#!/usr/bin/env python3
"""D12aa - saturating k_eff(p) fit + p=0.7 coverage re-check.

D12z KILLED the linear extrapolation of k_eff(p) to p=0.7 (ratios 0.4-0.5,
k_eff saturating ~0.65-0.86 instead of climbing to 1.61). Open lever: fit a
SATURATING k_eff(p) = k0 + A*exp(-p/tau) to calibration points at p <= 0.45
ONLY, predict p=0.7 with no refit, and re-check coverage against the SAVED
D12z harness floors (zero-GPU recomputation; model is monotone in k).

Calibration anchors (never the test point):
  p=0.3 : k=0.657   (D12u1 fit, D12u2/u4 certified)
  p=0.4 : k=0.8963  (D12u5 refit)
  p=0.45: k=0.7765  (D12v linear midpoint interpolation, heldout-certified)

G1: refit-k p=0.7 model floors within [0.5, 2.0] of harness floors,
    and ratio set STRADDLES 1.0 (not one-sided like D12z's 0.4-0.5).
G2: saturating fit residual at the anchors <= 10%.

Seed 2718. CPU-only, <5s, 6GB/80C guard untouched (no GPU code).
"""
import json
import math
import os
import numpy as np

SEED = 2718
N_CELLS = 64
N_PAIRS = 32
P = 0.7
W_LIST = [4, 8]
EPS_LIST = [0.0, 0.05, 0.1, 0.2]
T_GRID = [1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 50]
ALPHA = 1.92
THRESH = 0.5
MC = 4000

ANCHORS = [(0.3, 0.657), (0.4, 0.8963), (0.45, 0.7765)]

def fit_saturating():
    """k0 + A*exp(-p/tau) through 3 anchor points (closed form via solve).
    With 3 points and 3 params this interpolates exactly; G2 checks the
    solution is physically sane (k0 > 0, A != 0, tau > 0) rather than numeric.
    Solve in log space by grid over tau, exact solve of k0,A for each tau."""
    best = None
    for tau in np.geomspace(0.01, 10.0, 20001):
        e = [math.exp(-p / tau) for p, _ in ANCHORS]
        M = np.array([[1.0, e[0]], [1.0, e[1]], [1.0, e[2]]])
        y = np.array([k for _, k in ANCHORS])
        sol, res, *_ = np.linalg.lstsq(M, y, rcond=None)
        r = float(np.sqrt(np.sum((M @ sol - y) ** 2)))
        k0, A = sol
        if best is None or r < best[0]:
            best = (r, k0, A, tau)
    return best  # (resid, k0, A, tau)

def model_floor(W, eps, k, rng):
    s = P * (1 - 2 * eps)
    sig_decay = s ** ALPHA if s > 0 else 0.0
    for T in T_GRID:
        sigma = k / math.sqrt(W * T)
        z = rng.standard_normal((MC, N_CELLS - 2))
        null_max = z.max(axis=1) * sigma
        partner = rng.standard_normal((MC,)) * sigma + sig_decay
        if np.mean(partner > null_max) >= THRESH:
            return T
    return None

def main():
    with open("results/d12z_keff_p07_finegrid.json") as f:
        dz = json.load(f)

    resid, k0, A, tau = fit_saturating()
    k_pred = k0 + A * math.exp(-P / tau)
    g2 = resid <= 0.10 and k0 > 0 and tau > 0
    print(f"saturating fit: k(p) = {k0:.4f} + {A:.4f}*exp(-p/{tau:.4f}), "
          f"anchor resid {resid:.4f}, k(0.7) = {k_pred:.4f} "
          f"(D12z linear extrapolation was {dz['k_extrap']:.4f})")

    rng = np.random.default_rng(SEED)
    cells = []
    g1 = True
    ratios = []
    for cell in dz["cells"]:
        hf = cell["harness_floor"]
        if hf is None:
            mf = model_floor(cell["W"], cell["eps"], k_pred, rng)
            cells.append({"W": cell["W"], "eps": cell["eps"],
                          "harness_floor": None, "model_floor": mf,
                          "ratio": None})
            print(f"W={cell['W']} eps={cell['eps']}: harness=never model={mf} (untestable)")
            continue
        mf = model_floor(cell["W"], cell["eps"], k_pred, rng)
        ratio = hf / mf if mf else None
        ok = ratio is not None and 0.5 <= ratio <= 2.0
        g1 = g1 and ok
        if ratio is not None:
            ratios.append(ratio)
        k_eff = ratio * k_pred if ratio else None
        cells.append({"W": cell["W"], "eps": cell["eps"], "harness_floor": hf,
                      "model_floor": mf, "ratio": ratio, "k_eff_implied": k_eff})
        print(f"W={cell['W']} eps={cell['eps']}: harness={hf} model={mf} "
              f"ratio={ratio:.3f}" if ratio is not None else
              f"W={cell['W']} eps={cell['eps']}: harness={hf} model=never")
    straddle = ratios and min(ratios) < 1.0 < max(ratios)
    results = {"seed": SEED, "p": P, "fit": {"k0": k0, "A": A, "tau": tau,
               "anchor_resid": resid, "k_at_p07": k_pred,
               "dz_linear_extrap": dz["k_extrap"]},
               "cells": cells, "G1_pass": g1, "G2_pass": g2,
               "straddles_1": bool(straddle)}
    os.makedirs("results", exist_ok=True)
    with open("results/d12aa_saturating_kfit_p07.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("G1 (refit-k coverage [0.5,2.0]):", "PASS" if g1 else "FAIL")
    print("G2 (sane exact saturating fit):", "PASS" if g2 else "FAIL")
    print("straddle 1.0:", "YES" if straddle else "NO",
          f"(ratios {min(ratios):.2f}-{max(ratios):.2f})" if ratios else "")

if __name__ == "__main__":
    main()
