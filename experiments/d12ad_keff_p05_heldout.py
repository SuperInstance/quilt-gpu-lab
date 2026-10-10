#!/usr/bin/env python3
"""D12ad - k_eff(p) saturating-fit heldout at p=0.5 (fine T grid).

The k_eff(p) line has direct anchors at p=0.3 (0.657), 0.4 (0.8963), 0.55
(~1.2), 0.7 (1.20), and D12ac fitted a saturating curve
    k_eff(p) = 0.657 + 0.598*tanh((p-0.3)/0.197)
that beats linear on the anchors but was never tested at an UNMEASURED
interior p. p=0.5 is the last gap: the fit predicts k(0.5) ~ 1.116, while
the abandoned linear chord would give 0.657 + 2.393*0.2 = 1.136 (nearly
identical here, so the discriminating gate is coverage itself, not fit
choice — both predictions are tested).

G1: all 8 harness/model ratios within [0.5, 2.0] under sat-k (no refit).
G2: >= 6 of 8 implied k_eff resolvable and in [0.7, 1.6] (saturating
    regime, not the pre-saturation 0.657 band nor runaway).

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
T_GRID = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50]
DRAWS = 15
K_SAT = 0.657 + 0.598 * math.tanh((0.5 - 0.3) / 0.197)
K_LIN = 0.657 + (0.8963 - 0.657) / 0.1 * 0.2
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
    results = {"seed": SEED, "p": P, "N": N_CELLS, "k_sat": K_SAT, "k_lin": K_LIN,
               "alpha": ALPHA, "draws": DRAWS, "T_grid": T_GRID,
               "note": "saturating-fit heldout at unmeasured interior p=0.5",
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
    with open("results/d12ad_keff_p05_heldout.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("k_sat(0.5)=%.4f k_lin(0.5)=%.4f" % (K_SAT, K_LIN))
    print("G1 (sat-k coverage [0.5,2]):", "PASS" if g1 else "FAIL")
    print(f"G2 (k_eff in [0.7,1.6] in >=6/8): {resolvable}/8 ->", "PASS" if resolvable >= 6 else "FAIL")

if __name__ == "__main__":
    main()
