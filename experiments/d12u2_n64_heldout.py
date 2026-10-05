#!/usr/bin/env python3
"""D12u2: out-of-sample validation of the calibrated order-statistics model at N=64.

D12u1 fitted ONE variance multiplier k=0.657 (sigma = k/sqrt(W*T)) on the
N=32, W in {4,8} harness surface and held out only W=16 (same N). This run
tests the model at a config family it has NEVER seen: N=64 cells (63 nulls,
vs 31 in every calibration/heldout point).

Falsifiable gate: the D12u1 model (k=0.657, alpha=1.92, threshold 0.5,
63 nulls) must predict the measured harness floors at N=64 within 2x on
every (W, eps) cell. If k must change by >2x at N=64, the calibration is
N-local and the model fails out-of-family.

Seed 2718. CPU-only, ~1-2 min. No GPU, guard untouched.
"""
import json, math, os
import numpy as np

SEED = 2718
rng = np.random.default_rng(SEED)

N = 64
P = 0.3
EPS_GRID = [0.0, 0.05, 0.1, 0.2]
W_GRID = [4, 8]
T_GRID = [10, 15, 20, 30, 40, 60, 80, 120, 160, 240, 320, 480, 640, 800]
DRAWS = 5
K_D12U1 = 0.657
ALPHA_CORR = 1.92

def partner_id_acc(w, t, eps):
    half = N // 2
    accs = []
    for d in range(DRAWS):
        a = rng.choice([-1, 1], size=(half, w, t))
        mask = rng.random((half, w, t)) < P
        b = np.where(mask, a, rng.choice([-1, 1], size=a.shape))
        flip = rng.random(a.shape) < eps
        a = np.where(flip, -a, a)
        flip2 = rng.random(b.shape) < eps
        b = np.where(flip2, -b, b)
        A = np.empty((half, 2, w, t)); A[:, 0] = a; A[:, 1] = b
        s = A.reshape(N, w, t).astype(np.float64)
        s = s - s.mean(axis=2, keepdims=True)
        sd = s.std(axis=2, keepdims=True)
        ok = sd > 1e-9
        sz = np.where(ok, s / np.where(ok, sd, 1), 0.0)
        flat = sz.transpose(0, 2, 1).reshape(N, -1)
        C = (flat @ flat.T) / flat.shape[1]
        np.fill_diagonal(C, -2)
        pred = C.argmax(axis=1)
        cells = [(2 * i, 2 * i + 1) for i in range(half)]
        correct = sum(1 for i, j in cells if pred[i] == j)
        accs.append(correct / half)
    return float(np.mean(accs))

def find_floor(w, eps):
    for t in T_GRID:
        if partner_id_acc(w, t, eps) >= 0.9:
            return t
    return None

def model_floor(w, eps, k=K_D12U1, n_mc=20000, threshold=0.5):
    s = P * (1 - 2 * eps)
    if s <= 0:
        return float("inf")
    mu = s ** ALPHA_CORR
    def disc_prob(t):
        sig = k / math.sqrt(w * t)
        nul = rng.normal(0, sig, size=(n_mc, N - 1)).max(axis=1)
        part = rng.normal(mu, sig, size=n_mc)
        return float((part > nul).mean())
    lo, hi = 1.0, 200000.0
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
    rows = []
    for w in W_GRID:
        for eps in EPS_GRID:
            tf = find_floor(w, eps)
            mp = model_floor(w, eps)
            ratio = (mp / tf) if tf else float("inf")
            rows.append({"w": w, "eps": eps, "harness_floor": tf,
                         "model_pred": round(mp, 1),
                         "ratio_model_over_harness": round(ratio, 2) if tf else None,
                         "covered_2x": bool(tf is not None and ratio <= 2.0)})
    cov = sum(r["covered_2x"] for r in rows)
    worst = max((r["ratio_model_over_harness"] or 0) for r in rows)
    out = {
        "seed": SEED, "N": N, "p": P, "draws": DRAWS, "t_grid": T_GRID,
        "k_d12u1": K_D12U1, "nulls": N - 1,
        "cells": rows,
        "gates": {"G1_all_covered_2x": bool(cov == len(rows)),
                  "worst_ratio": round(worst, 2)},
        "verdict": "KEEP_model_generalizes_to_N64" if cov == len(rows) else "KILL_N_local_calibration",
    }
    os.makedirs("results", exist_ok=True)
    with open("results/d12u2_n64_heldout.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
