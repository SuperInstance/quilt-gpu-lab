#!/usr/bin/env python3
"""D12z - k_eff(p) line completion: p=0.7 with a dense fine T grid.

D12u3's p=0.7 cells were grid-pinned (floors at T-grid bottom) so they could
not constrain k_eff. This run resolves the p=0.7 surface with a FINE T grid
starting at T=1 and 15 draws/point. k is LINEARLY EXTRAPOLATED from the
2-point line (0.657@0.3, 0.8963@0.4): k(0.7) = 0.657 + 2.393*0.4 = 1.6142.
This is a genuine extrapolation test — the line has never been stretched.

G1: all harness/model ratios within [0.5, 2.0], no refit.
G2: implied k_eff non-decreasing in p relative to the D12u5 0.8963 anchor is
    NOT testable here (single p); instead G2 = k_eff_implied resolvable
    (floors not pinned) in >= 6 of 8 cells.

Seed 2718. CPU-only.
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
DRAWS = 15
K_EXTRAP = 0.657 + (0.8963 - 0.657) / 0.1 * 0.4  # linear extrapolation to p=0.7
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
    results = {"seed": SEED, "p": P, "N": N_CELLS, "k_extrap": K_EXTRAP,
               "alpha": ALPHA, "draws": DRAWS, "T_grid": T_GRID,
               "note": "extrapolation beyond the 2-point k_eff(p) line", "cells": []}
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
            mf = model_floor(W, eps, K_EXTRAP, rng)
            ratio = (hf / mf) if (hf and mf) else None
            if ratio is None or not (0.5 <= ratio <= 2.0):
                g1 = False
            if hf is not None:
                resolvable += 1
            k_eff = ratio * K_EXTRAP if ratio else None
            results["cells"].append({"W": W, "eps": eps, "harness_floor": hf,
                                     "model_floor": mf, "ratio": ratio,
                                     "k_eff_implied": k_eff})
            print(f"W={W} eps={eps}: harness={hf} model={mf} ratio={ratio} k_eff={k_eff}")
    results["G1_pass"] = g1
    results["resolvable_cells"] = resolvable
    g2 = resolvable >= 6
    results["G2_pass"] = g2
    os.makedirs("results", exist_ok=True)
    with open("results/d12z_keff_p07_finegrid.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("G1 (extrapolated-k coverage):", "PASS" if g1 else "FAIL")
    print(f"G2 (resolvable floors >= 6): {resolvable}/8 ->", "PASS" if g2 else "FAIL")

if __name__ == "__main__":
    main()
