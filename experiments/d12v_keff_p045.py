#!/usr/bin/env python3
"""D12v - k_eff(p) monotonicity probe at p=0.45.

D12u5 found the calibrated k=0.657 is conservative at p=0.4 (k_eff~0.90 fit)
but near-optimal at p=0.3 - from exactly TWO p-points. This run measures the
midpoint p=0.45 surface and tests whether a LINEARLY INTERPOLATED k
(k=0.7765) covers the harness floors within 2x.

G1: all 8 ratios (harness/model, k interpolated) within [0.5, 2.0].
G2: the k_eff implied per-cell (harness/model floor ratio * 0.7765, since
    floors scale linearly in k) is MONOTONE in eps - structural drift, not
    per-cell noise, is what D12u5 claimed.

Reuse of the d12u4 harness (pairing bugfix lineage). Seed 2718. CPU-only.
"""
import json
import math
import os
import numpy as np

SEED = 2718
N_CELLS = 64
N_PAIRS = 32
P = 0.45
W_LIST = [4, 8]
EPS_LIST = [0.0, 0.05, 0.1, 0.2]
T_GRID = [10, 15, 20, 30, 40, 60, 80, 120, 160, 240, 320, 480, 640, 800]
DRAWS = 5
K_INTERP = 0.657 + (0.8963 - 0.657) * ((0.45 - 0.3) / (0.4 - 0.3)) / 2  # 0.7765
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
    results = {"seed": SEED, "p": P, "N": N_CELLS, "k_interp": K_INTERP,
               "alpha": ALPHA, "draws": DRAWS, "T_grid": T_GRID, "cells": []}
    g1 = True
    for W in W_LIST:
        for eps in EPS_LIST:
            hf = None
            for T in T_GRID:
                acc = partner_id_acc(T, W, P, eps, rng)
                if acc >= 0.9:
                    hf = T
                    break
            mf = model_floor(W, eps, K_INTERP, rng)
            ratio = (hf / mf) if (hf and mf) else None
            if ratio is None or not (0.5 <= ratio <= 2.0):
                g1 = False
            k_eff = ratio * K_INTERP if ratio else None
            results["cells"].append({"W": W, "eps": eps, "harness_floor": hf,
                                     "model_floor": mf, "ratio": ratio,
                                     "k_eff_implied": k_eff})
            print(f"W={W} eps={eps}: harness={hf} model={mf} ratio={ratio} k_eff={k_eff}")
    results["G1_pass"] = g1
    # G2: per-W monotonicity of k_eff in eps
    g2 = True
    for W in W_LIST:
        keffs = [c["k_eff_implied"] for c in results["cells"]
                 if c["W"] == W and c["k_eff_implied"] is not None]
        inv = sum(1 for i in range(len(keffs) - 1) if keffs[i + 1] < keffs[i] - 1e-9)
        if inv > 0:
            g2 = False
        print(f"W={W} k_eff by eps: {keffs} inversions={inv}")
    results["G2_pass"] = g2
    os.makedirs("results", exist_ok=True)
    with open("results/d12v_keff_p045.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("G1 (interpolated-k coverage):", "PASS" if g1 else "FAIL")
    print("G2 (k_eff monotone in eps):", "PASS" if g2 else "FAIL")

if __name__ == "__main__":
    main()
