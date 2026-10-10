#!/usr/bin/env python3
"""D12ac - saturating k_eff(p) fit + per-p heldout re-certification.

D12ab measured k_eff(0.55)=1.2 directly, landing exactly ON the p=0.7
anchor (1.20) - the curve rises steeply over [0.3, 0.55] then flattens
toward 0.7. This run fits a saturating k_eff(p) = k0 + A*tanh((p-p0)/tau)
to the 4 DIRECT anchors (0.657@0.3, 0.896@0.4, ~1.2@0.55, 1.20@0.7), then
re-certifies the saved p=0.35 and p=0.45 harness floors (D12y/D12v) with
PER-P k from the fit - the interpolation D12v/D12y originally certified
(chord-based) is known to sit BELOW the true curve at 0.55.

Gates:
 G1: per-p-k coverage of the saved 0.35/0.45 floors within [0.5, 2.0].
 G2: saturating fit beats the linear (chord) fit on the 4 anchors (SSE),
     and both 0.35/0.45 surfaces get at least as good a max-|log ratio|
     as the chord k did.

Zero-GPU recomputation + MC model. Seed 2718. CPU-only.
"""
import json
import math
import os
import numpy as np

SEED = 2718
N_CELLS = 64
ALPHA = 1.92
THRESH = 0.5
MC = 20000
ANCHORS = [(0.3, 0.657), (0.4, 0.896), (0.55, 1.20), (0.7, 1.20)]

def model_floor(W, eps, p, k, T_GRID, rng):
    s = p * (1 - 2 * eps)
    sig_decay = s ** ALPHA if s > 0 else 0.0
    for T in T_GRID:
        sigma = k / math.sqrt(W * T)
        z = rng.standard_normal((MC, N_CELLS - 2))
        null_max = z.max(axis=1) * sigma
        partner = rng.standard_normal(MC) * sigma + sig_decay
        if np.mean(partner > null_max) >= THRESH:
            return T
    return None

def fit_saturating():
    """Grid-search k(p) = k0 + A*tanh((p-p0)/tau) with k0 pinned to anchor@0.3."""
    p0, k0 = ANCHORS[0]
    best = None
    for tau in np.linspace(0.05, 1.5, 60):
        for pmid in np.linspace(0.3, 0.8, 51):
            ts = np.tanh([(p - pmid) / tau for p, _ in ANCHORS])
            A = np.polyfit(ts, [k for _, k in ANCHORS], 1)[0]
            if A <= 0:
                continue
            resid = [k0 + A * math.tanh((p - pmid) / tau) - k for p, k in ANCHORS]
            sse = sum(r * r for r in resid)
            if best is None or sse < best[0]:
                best = (sse, A, pmid, tau)
    sse, A, pmid, tau = best
    return lambda p: k0 + A * math.tanh((p - pmid) / tau), dict(k0=k0, A=A, pmid=pmid, tau=tau, sse=sse)

def fit_linear():
    (x, y) = zip(*ANCHORS)
    c = np.polyfit(x, y, 1)
    sse = sum((np.polyval(c, xi) - yi) ** 2 for xi, yi in ANCHORS)
    return lambda p: float(np.polyval(c, p)), dict(sse=float(sse), slope=float(c[0]), intercept=float(c[1]))

def main():
    rng_master = np.random.default_rng(SEED)
    k_sat, fit_sat = fit_saturating()
    k_lin, fit_lin = fit_linear()
    print("saturating fit:", fit_sat)
    print("linear fit:", fit_lin)
    print("anchors pred sat:", {p: round(k_sat(p), 3) for p, _ in ANCHORS})
    print("anchors pred lin:", {p: round(k_lin(p), 3) for p, _ in ANCHORS})

    results = {"seed": SEED, "sat_fit": fit_sat, "lin_fit": fit_lin,
               "anchors": ANCHORS, "surfaces": []}

    # Load saved harness floors
    saved = {}
    for tag, f, p in [("0.35", "results/d12y_keff_p035.json", 0.35),
                      ("0.45", "results/d12v_keff_p045.json", 0.45)]:
        d = json.load(open(f))
        saved[tag] = (p, d["T_grid"], [(c["W"], c["eps"], c["harness_floor"]) for c in d["cells"]],
                      d["k_interp"])

    g1_pass = True
    g2 = True
    for tag, (p, T_GRID, floors, k_chord) in sorted(saved.items()):
        k_here = k_sat(p)
        k_chord_here = k_lin(p)
        print(f"\n=== p={p}: k_sat={k_here:.4f} (chord-certified k={k_chord:.4f}, "
              f"linear-4pt k={k_chord_here:.4f}) ===")
        surf = []
        for W, eps, hf in floors:
            rng = np.random.default_rng(rng_master.integers(1 << 62))
            mf = model_floor(W, eps, p, k_here, T_GRID, rng)
            ratio = (hf / mf) if (hf and mf) else None
            ok = ratio is not None and 0.5 <= ratio <= 2.0
            if not ok:
                g1_pass = False
            logr = math.log(ratio) if ratio else None
            surf.append({"W": W, "eps": eps, "harness_floor": hf,
                         "model_floor@k_sat": mf, "ratio": ratio,
                         "within_2x": ok, "log_ratio": logr})
            print(f" W={W} eps={eps}: harness={hf} model={mf} ratio={ratio} ok={ok}")
        # G2 component: max |log ratio| under k_sat vs the chord-k certification
        saved_ratios = []
        for c in json.load(open(dict(zip(['0.35', '0.45'], ['results/d12y_keff_p035.json',
                                                             'results/d12v_keff_p045.json']))[tag]))["cells"]:
            if c["ratio"] is not None:
                saved_ratios.append(abs(math.log(c["ratio"])))
        max_saved = max(saved_ratios)
        max_now = max(abs(s["log_ratio"]) for s in surf if s["log_ratio"] is not None)
        print(f" max|log ratio|: chord-k={max_saved:.3f} sat-k={max_now:.3f}")
        results["surfaces"].append({"p": p, "k_sat": k_here, "k_chord_saved": k_chord,
                                    "cells": surf, "max_abslog_chord": max_saved,
                                    "max_abslog_sat": max_now})
        if max_now > max_saved + 1e-9:
            g2 = False

    # G2 also requires saturating fit to beat linear on anchors
    g2 = g2 and (fit_sat["sse"] < fit_lin["sse"])
    print(f"\nfit SSE: sat={fit_sat['sse']:.5f} lin={fit_lin['sse']:.5f}")
    results["G1_perpk_coverage"] = g1_pass
    results["G2_sat_beats_lin_and_centres"] = g2
    os.makedirs("results", exist_ok=True)
    with open("results/d12ac_saturating_kfit_certify.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("G1 (per-p-k coverage [0.5,2]):", "PASS" if g1_pass else "FAIL")
    print("G2 (sat beats lin + centres 0.35/0.45):", "PASS" if g2 else "FAIL")

if __name__ == "__main__":
    main()
