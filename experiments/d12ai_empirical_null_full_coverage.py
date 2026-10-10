#!/usr/bin/env python3
"""D12ai — empirical-null (k=1) model coverage over the cells D12ah didn't test.

D12ah established that the k_eff(p) dip is a Gaussian-null artifact at W=8 for
p in {0.3, 0.4, 0.45, 0.525}. Open lever (from the D12ah journal entry):
recompute the k=0.657-era predictions with the empirical-null model across the
remaining D12u-series surfaces to confirm k=1 covers everything the dial did.

Pure recomputation of coverage: harness floors are pulled from SAVED results
(d12ae, d12z, d12ag) — no new harness runs. Only the model side is MC.

Cells (W, p, eps) with harness floors from saved results:
  - p=0.5,  W=4/8   (d12ae_keff_p05_extended)
  - p=0.7,  W=4/8   (d12z_keff_p07_finegrid; W=4 eps=0.2 is 'never', skipped)
  - p=0.5/0.525, W=16 (d12ag_keff_w16_dip_robustness)

Model: D12ah verbatim — MC the CERTIFIED D12u4 generator + estimator
(copy-branch pairing, whole-cell eps flips, pooled flat centered cosine |corr|),
nulls = 62 independent-pair estimates, P_succ = mean F(|x|)^62,
floor = min T with P_succ >= 0.9. NO Gaussian, NO k dial (k=1).

Gates:
  G1: all covered floors within [0.5, 2.0]x of harness with k=1.
  G2: mean |log ratio| <= 0.35 (tighter than 2x — is k=1 CENTERED, unlike the
      k-dial era which needed per-p constants 0.657..1.2?).
"""
import json, time
import numpy as np

SEED = 2718
rng = np.random.default_rng(SEED)
N_NULLS = 62
N_SAMPLES = 4000

# (W, p) -> {eps: harness_floor or None}; eps=0.2 W=4 at p=0.7 is never<=50 -> excluded
CELLS = {
    (4, 0.5):  {0.0: 15, 0.05: 25, 0.1: 40, 0.2: 130},   # d12ae
    (8, 0.5):  {0.0: 8, 0.05: 12, 0.1: 20, 0.2: 65},     # d12ae
    (4, 0.7):  {0.0: 8, 0.05: 15, 0.1: 20},              # d12z
    (8, 0.7):  {0.0: 4, 0.05: 6, 0.1: 10, 0.2: 50},      # d12z
    (16, 0.5):  {0.0: 4, 0.05: 6, 0.1: 10, 0.2: 40},     # d12ag
    (16, 0.525): {0.0: 4, 0.05: 6, 0.1: 10, 0.2: 20},    # d12ag
}

def t_grid(W, p):
    # fine grids: floors here are tiny (4..130); resolve to ~15% rungs
    if W == 4:
        g = [4, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 65, 80, 100, 130, 160]
    elif W == 8:
        g = [2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 65, 80]
    else:
        g = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50]
    return [t for t in g if t >= (1 if p >= 0.5 else 4)]

def pair_streams(n, T, W, p, eps, partner):
    top = (rng.random((n, T, W)) < 0.5).astype(np.int8) * 2 - 1
    if partner:
        copy_mask = rng.random((n, T, W)) < p
        bot = (rng.random((n, T, W)) < 0.5).astype(np.int8) * 2 - 1
        bot[copy_mask] = top[copy_mask]
    else:
        bot = (rng.random((n, T, W)) < 0.5).astype(np.int8) * 2 - 1
    if eps > 0:
        ft = rng.random((n, T, W)) < eps
        fb = rng.random((n, T, W)) < eps
        top = np.where(ft, -top, top)
        bot = np.where(fb, -bot, bot)
    return top, bot

def corr_flat(x, y):
    f = x.reshape(len(x), -1).astype(np.float64)
    g = y.reshape(len(y), -1).astype(np.float64)
    f = f - f.mean(1, keepdims=True)
    g = g - g.mean(1, keepdims=True)
    nf = np.linalg.norm(f, axis=1); ng = np.linalg.norm(g, axis=1)
    nf[nf == 0] = 1; ng[ng == 0] = 1
    return np.abs(((f / nf[:, None]) * (g / ng[:, None])).sum(1))

def floor_for(W, p, eps):
    floor = None
    for T in t_grid(W, p):
        na, nb = pair_streams(N_SAMPLES, T, W, p, eps, partner=False)
        nulls = np.sort(corr_flat(na, nb))
        pa, pb = pair_streams(N_SAMPLES, T, W, p, eps, partner=True)
        px = corr_flat(pa, pb)
        Fx = np.searchsorted(nulls, px, side="right") / len(nulls)
        succ = np.mean(Fx ** N_NULLS)
        if succ >= 0.9 and floor is None:
            floor = T
    return floor

def main():
    t0 = time.time()
    cells, ratios = [], []
    for (W, p), epsmap in sorted(CELLS.items()):
        for eps in sorted(epsmap):
            hf = epsmap[eps]
            mf = floor_for(W, p, eps)
            ratio = (mf / hf) if (mf and hf) else None
            ok = ratio is not None and 0.5 <= ratio <= 2.0
            if ratio is not None:
                ratios.append(ratio)
            cells.append({"W": W, "p": p, "eps": eps, "empirical_floor": mf,
                          "harness_floor": hf, "ratio": ratio, "covered_2x_k1": ok})
            print(f"W={W} p={p} eps={eps}: empirical={mf} harness={hf} ratio={ratio}", flush=True)
    g1 = all(c["covered_2x_k1"] for c in cells)
    lr = np.abs(np.log(np.array(ratios)))
    g2 = bool(len(lr) and lr.mean() <= 0.35)
    res = {
        "seed": SEED, "n_samples": N_SAMPLES, "nulls": N_NULLS,
        "model": "empirical-null MC of D12u4 estimator, k=1, succ>=0.9 (D12ah verbatim)",
        "harness_sources": ["d12ae_keff_p05_extended", "d12z_keff_p07_finegrid",
                            "d12ag_keff_w16_dip_robustness"],
        "cells": cells,
        "G1_all_covered_k1": g1, "G2_mean_abslogratio_le_0.35": g2,
        "mean_abs_log_ratio": float(lr.mean()) if len(lr) else None,
        "ratios": ratios,
        "wall_s": round(time.time() - t0, 1),
        "verdict": ("KEEP_k1_empirical_null_covers_full_surface" if (g1 and g2)
                    else ("PARTIAL_k1_covers_but_off_center" if g1
                          else "KILL_k1_fails_somewhere")),
    }
    with open("results/d12ai_empirical_null_full_coverage.json", "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({k: res[k] for k in ("G1_all_covered_k1", "G2_mean_abslogratio_le_0.35",
                                          "mean_abs_log_ratio", "verdict", "wall_s")}, indent=2))

if __name__ == "__main__":
    main()
