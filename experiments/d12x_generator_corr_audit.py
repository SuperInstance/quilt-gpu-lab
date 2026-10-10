#!/usr/bin/env python3
"""D12x - generator corr audit.

Loose thread from D12u3: partner corr sanity-check measured 0.605 at p=0.7,
noticeably below the nominal p=0.7, while D12q measured corr = p exactly at
smaller draws. Question: does the measured partner |corr| of the stream
generator fall BELOW p (and where), or was D12u3's 0.605 a sampling artifact?

Harness (same generator family as D12u4): partner pairs (i, i+N_PAIRS) share
copy-prob p; atoms in {-1,+1}; eps=0 here (noise axis already characterized).
Estimator: centered cosine |corr| (the D13d-style estimator the floors use).

Measurements:
  1. corr_hat(p, T) for p in {0.3, 0.4, 0.45, 0.5, 0.7}, T in {25, 200, 800},
     W=8, many independent pair draws (2000 pairs per cell) -> mean, sd.
  2. Null-pair |corr| distribution at same configs -> mean/sd (bias check:
     centered cosine on finite +-1 streams should be slightly positive).
  3. Gate: at T=800 (200*W*T=12800 atoms) corr_hat(0.7) must lie within
     [0.66, 0.74] (3 sigma with sigma ~ 1/sqrt(800*8) = 0.0125).

Seed 2718, CPU-only, seconds.
"""
import json
import numpy as np

SEED = 2718
W = 8
P_LIST = [0.3, 0.4, 0.45, 0.5, 0.7]
T_LIST = [25, 200, 800]
N_PAIR_DRAWS = 2000  # independent partner pairs per config
N_NULL_PER_DRAW = 32  # null pairs sampled per draw for null stats

def draw_partner_corr(T, p, rng):
    a = (rng.random((T, W)) < 0.5).astype(np.int8) * 2 - 1
    b = (rng.random((T, W)) < 0.5).astype(np.int8) * 2 - 1
    cp = rng.random((T, W)) < p
    b[cp] = a[cp]
    fa = a.reshape(-1).astype(np.float64)
    fb = b.reshape(-1).astype(np.float64)
    fa -= fa.mean(); fb -= fb.mean()
    na = np.linalg.norm(fa); nb = np.linalg.norm(fb)
    if na == 0 or nb == 0:
        return 0.0
    return abs(float(fa @ fb / (na * nb)))

def draw_null_corr(T, rng):
    a = (rng.random((T, W)) < 0.5).astype(np.int8) * 2 - 1
    b = (rng.random((T, W)) < 0.5).astype(np.int8) * 2 - 1
    fa = a.reshape(-1).astype(np.float64); fb = b.reshape(-1).astype(np.float64)
    fa -= fa.mean(); fb -= fb.mean()
    na = np.linalg.norm(fa); nb = np.linalg.norm(fb)
    if na == 0 or nb == 0:
        return 0.0
    return abs(float(fa @ fb / (na * nb)))

def main():
    rng = np.random.default_rng(SEED)
    results = {"seed": SEED, "W": W, "n_pair_draws": N_PAIR_DRAWS, "cells": []}
    gate_pass = True
    for p in P_LIST:
        for T in T_LIST:
            cs = np.array([draw_partner_corr(T, p, rng) for _ in range(N_PAIR_DRAWS)])
            ns = np.array([draw_null_corr(T, rng) for _ in range(200)])
            cell = {"p": p, "T": T, "corr_mean": float(cs.mean()),
                    "corr_sd": float(cs.std()), "null_mean": float(ns.mean()),
                    "null_sd": float(ns.std())}
            results["cells"].append(cell)
            print(f"p={p} T={T}: corr_hat={cs.mean():.4f} (sd {cs.std():.4f}) "
                  f"null={ns.mean():.4f}  deficit={p - cs.mean():+.4f}")
            if p == 0.7 and T == 800:
                ok = bool(0.66 <= cs.mean() <= 0.74)
                gate_pass = gate_pass and ok
                results["gate_p07_T800"] = {"mean": float(cs.mean()),
                                            "window": [0.66, 0.74], "pass": ok}
    results["G1_pass"] = gate_pass
    import os
    os.makedirs("results", exist_ok=True)
    with open("results/d12x_generator_corr_audit.json", "w") as f:
        json.dump(results, f, indent=2)
    print("G1 (corr_hat(0.7, T=800) in [0.66, 0.74]):",
          "PASS" if gate_pass else "FAIL")

if __name__ == "__main__":
    main()
