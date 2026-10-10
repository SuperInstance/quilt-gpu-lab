#!/usr/bin/env python3
"""D12ae - p=0.5 dip resolution check (T grid extended to 200).

D12ad measured implied k_eff(0.5) = 0.60-0.74, far below the saturating-fit
prediction 1.116, but its T grid capped at 50 and the two (eps=0.2) cells
were unresolvable ('never<=50') for BOTH harness and model. Two readings:
(a) genuine dip / non-monotone k_eff(p), or (b) small-T grid quantization
biasing implied k down. This run extends the T grid to 200 to resolve the
eps=0.2 cells and re-test the dip with all 8 cells measurable.

G1: all 8 harness/model ratios within [0.5, 2.0] under sat-k (no refit).
G2: >= 6 of 8 implied k_eff resolvable and in [0.7, 1.6] (saturating band).

Seed 2718. CPU-only.
"""
import json
import math
import os
import numpy as np

SEED = 2718
N_CELLS = 64
N_PAIRS = 32
P = 0.5
W_LIST = [4, 8]
EPS_LIST = [0.0, 0.05, 0.1, 0.2]
T_GRID = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 65, 80, 100, 130, 160, 200]
DRAWS = 15
K_SAT = 0.657 + 0.598 * math.tanh((0.5 - 0.3) / 0.197)
ALPHA = 1.92
THRESH = 0.5
MC = 4000

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
    rng = np.random.default_rng(SEED)
    results = {"seed": SEED, "p": P, "N": N_CELLS, "k_sat": K_SAT,
               "alpha": ALPHA, "draws": DRAWS, "T_grid": T_GRID,
               "note": "p=0.5 dip resolution: T grid extended to 200",
               "cells": []}
    g1 = True
    resolvable = 0
    for W in W_LIST:
        for eps in EPS_LIST:
            hf = None
            for T in T_GRID:
                acc = partner_id_acc(T, W, P, eps, rng)
                if acc >= 0.9:
                    hf = T
                    break
            mf = model_floor(W, eps, K_SAT, rng)
            ratio = (hf / mf) if (hf and mf) else None
            if ratio is None or not (0.5 <= ratio <= 2.0):
                g1 = False
            k_eff = ratio * K_SAT if ratio else None
            if ratio is not None and 0.7 <= k_eff <= 1.6:
                resolvable += 1
            results["cells"].append({"W": W, "eps": eps, "harness_floor": hf,
                                     "model_floor_sat": mf, "ratio": ratio,
                                     "k_eff_implied": k_eff})
            print(f"W={W} eps={eps}: harness={hf} model_sat={mf} ratio={ratio} k_eff={k_eff}")
    results["G1_pass"] = g1
    results["G2_pass"] = resolvable >= 6
    results["resolvable_cells"] = resolvable
    os.makedirs("results", exist_ok=True)
    with open("results/d12ae_keff_p05_extended.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("k_sat(0.5)=%.4f" % K_SAT)
    print("G1 (sat-k coverage [0.5,2]):", "PASS" if g1 else "FAIL")
    print(f"G2 (k_eff in [0.7,1.6] in >=6/8): {resolvable}/8 ->", "PASS" if resolvable >= 6 else "FAIL")

if __name__ == "__main__":
    main()
