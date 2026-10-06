#!/usr/bin/env python3
"""D12u4 - near-degenerate p heldout for the calibrated order-statistics model.

D12u3's p=0.7 heldout passed trivially (floors pinned at T-grid bottom).
This run tests p=0.4, where s_eff = p*(1-2eps) makes floors large and
resolvable - the regime that can genuinely pin k across p.

v2 BUGFIX: v1 paired b[i] with a[i] but matched cell i against cell i+N_PAIRS -
partner corr measured correctly (0.405) yet matching was structurally wrong
(acc 0.03 at T=800). Now pairs are (i, i+N_PAIRS) in the A-streams themselves;
match = argmax |corr| row i over all other cells.

Model: M1 order statistics, sigma = k/sqrt(W*T), k=0.657 UNCHANGED (D12u1),
alpha=1.92, threshold 0.5. Seed 2718. CPU-only.
"""
import json
import math
import os
import numpy as np

SEED = 2718
rng = np.random.default_rng(SEED)
N_CELLS = 64
N_PAIRS = 32
P = 0.4
W_LIST = [4, 8]
EPS_LIST = [0.0, 0.05, 0.1, 0.2]
T_GRID = [10, 15, 20, 30, 40, 60, 80, 120, 160, 240, 320, 480, 640, 800]
DRAWS = 5
K = 0.657
ALPHA = 1.92
THRESH = 0.5
MC = 4000

def gen_streams(T, W, p, eps, rng):
    """Partner pairs (i, i+N_PAIRS) share corr=p streams; atoms flipped w.p. eps."""
    a = (rng.random((N_CELLS, T, W)) < 0.5).astype(np.int8) * 2 - 1
    # second half: per atom, with prob p copy the first-half partner's atom
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

def model_floor(W, eps, k=K, alpha=ALPHA, thresh=THRESH, n_nulls=N_CELLS - 2):
    s = P * (1 - 2 * eps)
    sig_decay = s ** alpha if s > 0 else 0.0
    for T in T_GRID:
        sigma = k / math.sqrt(W * T)
        z = rng.standard_normal((MC, n_nulls))
        null_max = z.max(axis=1) * sigma
        partner = rng.standard_normal((MC,)) * sigma + sig_decay
        if np.mean(partner > null_max) >= thresh:
            return T
    return None

def main():
    global rng
    rng = np.random.default_rng(SEED)
    results = {"seed": SEED, "p": P, "N": N_CELLS, "k": K, "alpha": ALPHA,
               "draws": DRAWS, "T_grid": T_GRID, "cells": []}
    all_pass = True
    ratios = []
    for W in W_LIST:
        for eps in EPS_LIST:
            hf = None
            for T in T_GRID:
                acc = partner_id_acc(T, W, P, eps, rng)
                if acc >= 0.9:
                    hf = T
                    break
            mf = model_floor(W, eps)
            ratio = (hf / mf) if (hf and mf) else None
            if ratio is not None:
                ratios.append(ratio)
                if not (0.5 <= ratio <= 2.0):
                    all_pass = False
            results["cells"].append({"W": W, "eps": eps, "harness_floor": hf,
                                     "model_floor": mf, "ratio": ratio})
            print(f"W={W} eps={eps}: harness={hf} model={mf} ratio={ratio}")
    results["G1_pass"] = all_pass
    results["ratios"] = ratios
    os.makedirs("results", exist_ok=True)
    with open("results/d12u4_p04_heldout.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("G1 (all ratios within 2x, k unchanged):", "PASS" if all_pass else "FAIL")

if __name__ == "__main__":
    main()
