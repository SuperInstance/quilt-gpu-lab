#!/usr/bin/env python3
"""D12ah (v2) — empirical-null discovery model vs the k_eff(p) dip.

Question (fresh lane, opened after D12ag closed the k_eff lane):
The calibrated order-statistics model needs a p-dependent variance dial k_eff(p)
(non-monotone: 0.657@0.3, 0.896@0.4, ~0.65@0.5, ~0.79@0.525, ~1.2@0.55, 1.20@0.7).
Is the dip an artifact of the ideal-Gaussian null in the model, or real in the
streams?

v2: uses the CERTIFIED D12u4 generator verbatim (copy-branch pairing, whole-cell
eps flips) and the D12u4 estimator verbatim (pooled flat centered cosine over
W*T, |corr|, argmax match). v1 had a home-grown generator + per-subchannel
estimator that under-coupled; discarded before trusting any numbers.

Model: NO Gaussian assumption, NO k. Monte-Carlo the actual estimator:
  - nulls: |corr| estimates of independent cell pairs (empirical null)
  - partner: |corr| estimate of true (p, eps) pairs
  - per-pair success: P(|x_partner| > max of 62 nulls) via empirical CDF,
    P_succ = mean_i F(|x_i|)^62
  - floor = smallest T with P_succ >= 0.9  (harness uses acc >= 0.9 over 32 pairs)
Gates:
  G1: empirical-model floors within [0.5, 2.0]x of harness floors at ALL 16
      (p, eps) cells with k=1 (covers the trough with no dial).
  G2: trough cells (p=0.525) specifically within [0.5, 2.0].
If G1 passes -> the k_eff(p) dip is a Gaussian-null artifact (KEEP empirical model).
If only the trough fails -> the dip is real in the streams (physical).
"""
import json, time
import numpy as np

SEED = 2718
rng = np.random.default_rng(SEED)
W = 8
N_NULLS = 62          # 64 cells, partner excluded
N_SAMPLES = 4000
EPS_LIST = [0.0, 0.05, 0.1, 0.2]

HARNESS = {   # W=8 floors from results: d12u2, d12u4, d12v, d12af
    0.3:   {0.0: 20, 0.05: 30, 0.1: 60, 0.2: 160},
    0.4:   {0.0: 15, 0.05: 20, 0.1: 30, 0.2: 120},
    0.45:  {0.0: 10, 0.05: 15, 0.1: 30, 0.2: 80},
    0.525: {0.0: 8,  0.05: 12, 0.1: 20, 0.2: 65},
}

def t_grid(p):
    if p == 0.525:
        return [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 65, 80, 100, 130, 160]
    return [4, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 65, 80, 100, 130, 160, 200, 260, 320]

def pair_streams(n, T, p, eps, partner):
    """D12u4 generator, reduced to one (top, bot) pair family, vectorized over n pairs."""
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
    """D12u4 estimator verbatim: pooled flat centered cosine."""
    f = x.reshape(len(x), -1).astype(np.float64)
    g = y.reshape(len(y), -1).astype(np.float64)
    f = f - f.mean(1, keepdims=True)
    g = g - g.mean(1, keepdims=True)
    nf = np.linalg.norm(f, axis=1); ng = np.linalg.norm(g, axis=1)
    nf[nf == 0] = 1; ng[ng == 0] = 1
    return np.abs(((f / nf[:, None]) * (g / ng[:, None])).sum(1))

def floor_for(p, eps):
    grid = t_grid(p)
    floor = None
    for T in grid:
        na, nb = pair_streams(N_SAMPLES, T, p, eps, partner=False)
        nulls = np.sort(corr_flat(na, nb))
        pa, pb = pair_streams(N_SAMPLES, T, p, eps, partner=True)
        px = corr_flat(pa, pb)
        Fx = np.searchsorted(nulls, px, side="right") / len(nulls)
        succ = np.mean(Fx ** N_NULLS)
        if succ >= 0.9 and floor is None:
            floor = T
    return floor

def main():
    t0 = time.time()
    # sanity: corr = p exactly (D12x standard)
    a, b = pair_streams(3000, 800, 0.525, 0.0, partner=True)
    fa = a.reshape(len(a), -1).astype(float); fb = b.reshape(len(b), -1).astype(float)
    c = (fa * fb).mean(1)
    print(f"sanity corr(p=0.525, T=800) = {c.mean():.4f} (expect 0.525)", flush=True)
    cells, g1, g2 = [], [], []
    for p in sorted(HARNESS):
        for eps in EPS_LIST:
            mf = floor_for(p, eps)
            hf = HARNESS[p][eps]
            ratio = (mf / hf) if (mf and hf) else None
            ok = ratio is not None and 0.5 <= ratio <= 2.0
            g1.append(ok)
            if p == 0.525:
                g2.append(ok)
            cells.append({"p": p, "eps": eps, "empirical_floor": mf,
                          "harness_floor": hf, "ratio": ratio, "covered_2x_k1": ok})
            print(f"p={p} eps={eps}: empirical={mf} harness={hf} ratio={ratio}", flush=True)
    res = {
        "seed": SEED, "W": W, "nulls": N_NULLS, "n_samples": N_SAMPLES,
        "model": "empirical-null MC of the D12u4 harness estimator, k=1, succ>=0.9",
        "cells": cells,
        "G1_all_covered_k1": all(g1), "G1_hits": sum(g1), "n_cells": len(g1),
        "G2_trough_covered_k1": all(g2), "G2_hits": sum(g2),
        "wall_s": round(time.time() - t0, 1),
        "verdict": ("KEEP_empirical_model_dip_is_gaussian_artifact" if all(g1)
                    else ("PARTIAL_dip_real_in_streams" if all(g2) else
                          "KILL_empirical_model_fails_including_trough")),
    }
    with open("results/d12ah_empirical_null_dip.json", "w") as f:
        json.dump(res, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != "cells"}, indent=2))

if __name__ == "__main__":
    main()
