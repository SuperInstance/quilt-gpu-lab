#!/usr/bin/env python3
"""D12ag - is the mid-coupling k_eff dip W-dependent?

The k_eff(p) trough (0.65@0.5, 0.79@0.525 vs anchors 0.657@0.3, 0.896@0.4,
~1.2@0.55/0.7) was measured only at W in {4,8}. D12af also saw within-p
eps-drift in implied k emerge in this band. Question: does the dip survive
at W=16, or is it a narrow-width artifact (null-confusability at small W*T
could differ structurally in the mid-coupling regime)?

Configs: p in {0.5, 0.525}, W=16, eps in {0, 0.05, 0.1, 0.2}, N=64,
fine T grid 1..200, 15 draws/point, sat-k model prediction for comparison.
Reference: implied k_eff ~ 0.65 (p=0.5) / ~0.79-0.93 (p=0.525) at W=4/8
would mean the dip is width-robust; ~1.1-1.2 would mean it is not.

Seed 2718. CPU-only.
"""
import json
import math
import os
import numpy as np

SEED = 2718
N_CELLS = 64
N_PAIRS = 32
P_LIST = [0.5, 0.525]
W = 16
EPS_LIST = [0.0, 0.05, 0.1, 0.2]
T_GRID = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 65, 80, 100, 130, 160, 200]
DRAWS = 15
ALPHA = 1.92
THRESH = 0.5
MC = 4000

def k_sat(p):
    return 0.657 + 0.598 * math.tanh((p - 0.3) / 0.197)

def gen_streams(T, W, p, eps, rng):
    a = (rng.random((N_CELLS, T, W)) < 0.5).astype(np.int8) * 2 - 1
    copy_mask = rng.random((N_PAIRS, T, W)) < p
    bot = (rng.random((N_PAIRS, T, W)) < 0.5).astype(np.int8) * 2 - 1
    top = a[:N_PAIRS]
    bot[copy_mask] = top[copy_mask]
    a[N_PAIRS:] = bot
    if eps > 0:
        flip = rng.random((N_CELLS, T, W)) < eps
        a[flip] *= -1
    return a

def partner_id_acc(T, W, p, eps, rng):
    ok = 0
    for _ in range(DRAWS):
        a = gen_streams(T, W, p, eps, rng)
        f = a.reshape(N_CELLS, -1).astype(np.float64)
        f = f - f.mean(1, keepdims=True)
        n = np.linalg.norm(f, axis=1)
        n[n == 0] = 1
        C = (f / n[:, None]) @ (f / n[:, None]).T
        np.fill_diagonal(C, 0.0)
        match = np.argmax(np.abs(C), axis=1)
        ok += int(np.sum(match[:N_PAIRS] == np.arange(N_PAIRS) + N_PAIRS))
    return ok / (DRAWS * N_PAIRS)

def model_floor(T_grid, W, eps, p, k, rng):
    s = p * (1 - 2 * eps)
    sig_decay = s ** ALPHA if s > 0 else 0.0
    for T in T_grid:
        sigma = k / math.sqrt(W * T)
        z = rng.standard_normal((MC, N_CELLS - 2))
        null_max = z.max(axis=1) * sigma
        partner = rng.standard_normal((MC,)) * sigma + sig_decay
        if np.mean(partner > null_max) >= THRESH:
            return T
    return None

def main():
    rng = np.random.default_rng(SEED)
    results = {"seed": SEED, "W": W, "N": N_CELLS, "alpha": ALPHA,
               "draws": DRAWS, "T_grid": T_GRID,
               "note": "W=16 dip robustness probe at p in {0.5, 0.525}",
               "cells": []}
    for p in P_LIST:
        ks = k_sat(p)
        for eps in EPS_LIST:
            hf = None
            for T in T_GRID:
                acc = partner_id_acc(T, W, p, eps, rng)
                if acc >= 0.9:
                    hf = T
                    break
            mf = model_floor(T_GRID, W, eps, p, ks, rng)
            ratio = (hf / mf) if (hf and mf) else None
            k_eff = ratio * ks if ratio else None
            results["cells"].append({"p": p, "W": W, "eps": eps,
                                     "harness_floor": hf, "model_floor_sat": mf,
                                     "ratio": ratio, "k_eff_implied": k_eff,
                                     "k_sat": ks})
            print(f"p={p} W={W} eps={eps}: harness={hf} model_sat={mf} "
                  f"ratio={ratio} k_eff={k_eff} k_sat={ks:.4f}")
    # Gate: dip robust if >=6 of 8 cells land in the dip band k_eff < 1.0
    hits = sum(1 for c in results["cells"]
               if c["k_eff_implied"] is not None and c["k_eff_implied"] < 1.0)
    results["G1_dip_robust_at_W16"] = hits >= 6
    results["G1_hits"] = hits
    os.makedirs("results", exist_ok=True)
    with open("results/d12ag_keff_w16_dip_robustness.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"G1 dip robust at W=16 (k_eff<1.0 in >=6/8): {hits}/8 ->",
          "PASS" if hits >= 6 else "FAIL")

if __name__ == "__main__":
    main()
