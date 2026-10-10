#!/usr/bin/env python3
"""D12af - p=0.525 dip-width probe.

D12ae certified a k_eff dip at p=0.5 (implied k_eff = 0.65 +- 0.05, all 8
cells resolvable with T<=200), between the 0.657@0.3 and 0.896@0.4 anchors
and far below the ~1.2 plateau at p>=0.55. The dip is measured at exactly
one p-point. This run probes p=0.525 — the midpoint between the dip (0.5,
k~0.65) and the recovery (0.55, k~1.2) — to measure the dip's width.

G1 (dip confirmation): >= 6 of 8 cells yield implied k_eff < 0.90.
G2 (sat-band check): >= 6 of 8 implied k_eff in [1.0, 1.6] would instead
mean the dip has already closed at 0.525.

Seed 2718. CPU-only.
"""
import json
import math
import os
import numpy as np

SEED = 2718
N_CELLS = 64
N_PAIRS = 32
P = 0.525
W_LIST = [4, 8]
EPS_LIST = [0.0, 0.05, 0.1, 0.2]
T_GRID = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 65, 80, 100, 130, 160, 200]
DRAWS = 15
K_SAT = 0.657 + 0.598 * math.tanh((P - 0.3) / 0.197)
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
               "note": "p=0.525 dip-width probe (D12ae follow-up)",
               "cells": []}
    g1_hits = 0
    g2_hits = 0
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
            k_eff = ratio * K_SAT if ratio else None
            if k_eff is not None:
                if k_eff < 0.90:
                    g1_hits += 1
                if 1.0 <= k_eff <= 1.6:
                    g2_hits += 1
            results["cells"].append({"W": W, "eps": eps, "harness_floor": hf,
                                     "model_floor_sat": mf, "ratio": ratio,
                                     "k_eff_implied": k_eff})
            print(f"W={W} eps={eps}: harness={hf} model_sat={mf} ratio={ratio} k_eff={k_eff}")
    results["G1_dip_confirmed"] = g1_hits >= 6
    results["G1_hits"] = g1_hits
    results["G2_dip_closed"] = g2_hits >= 6
    results["G2_hits"] = g2_hits
    os.makedirs("results", exist_ok=True)
    with open("results/d12af_keff_p0525_probe.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("k_sat(0.525)=%.4f" % K_SAT)
    print(f"G1 dip confirmed (k_eff<0.90 in >=6/8): {g1_hits}/8 ->", "PASS" if g1_hits >= 6 else "FAIL")
    print(f"G2 dip already closed (k_eff in [1.0,1.6] in >=6/8): {g2_hits}/8 ->", "PASS" if g2_hits >= 6 else "FAIL")

if __name__ == "__main__":
    main()
