#!/usr/bin/env python3
"""D12p — fit the p-dependent constant C(p) in the discovery-floor law.

D12o validated the bound T_floor <= C/(W*s^1.92), s=(2p-1)(1-2eps), at
p=0.7 with C=600 fixed — coverage held but the bound was ~8x looser at
p=0.7 than at p=0.3 (mean measured/bound ratio 0.025 vs ~0.1-0.2). The
open question: is C effectively p-dependent, specifically C(p) ~
C0*(2p-1)^-beta? This run measures floors across a p grid (eps=0, W=8,
N=32), computes C_emp(p) = W*T_floor*s^1.92 at each p, and fits beta by
log-log regression. p=0.5 is excluded (degenerate, s=0).

Pre-registered gates:
  G1: fit quality — log-log R^2 >= 0.8 across the p grid.
  G2: held-out prediction — the fitted C(p) with beta from a 3-point
      fit on {p=0.3, 0.5-excluded... } — concretely: fit beta on
      p in {0.3, 0.4} only, then predict the floor at p=0.6 and 0.7;
      prediction must satisfy measured W*T_floor <= C_fit(p)/s^1.92
      (coverage 2/2) AND non-vacuous (ratio >= 0.02).
KEEP iff G1 and G2. Seed 2718. CPU-only, <2 min, 6GB/80C guard untouched.
"""
from __future__ import annotations

import json
import math
import random

SEED = 2718
W = 8
N = 32
EPS = 0.0
P_GRID = (0.3, 0.4, 0.6, 0.7)          # fit grid
P_HELDOUT = (0.6, 0.7)                 # predicted from a 2-point fit
P_FIT = (0.3, 0.4)
T_VALUES = (2, 5, 10, 15, 20, 25, 30, 40, 50, 70, 100, 150, 200, 300)
DRAWS = 3
ACC_BAR = 0.9
ALPHA = 1.92


def make_pairs(n, rng):
    perm = list(range(n))
    rng.shuffle(perm)
    partner = {}
    for i in range(0, n, 2):
        a, b = perm[i], perm[i + 1]
        partner[a] = b
        partner[b] = a
    return partner


def streams_for(rng, partner, n, p_corr, eps, t_obs, w):
    streams = {c: [[] for _ in range(w)] for c in range(n)}
    for _ in range(t_obs):
        seen = set()
        for a in partner:
            if a in seen:
                continue
            seen |= {a, partner[a]}
            b = partner[a]
            for q in range(w):
                base = 1 if rng.random() < 0.5 else -1
                if rng.random() < p_corr:
                    va = vb = base
                else:
                    va, vb = base, (1 if rng.random() < 0.5 else -1)
                if rng.random() < eps:
                    va = -va
                if rng.random() < eps:
                    vb = -vb
                streams[a][q].append(va)
                streams[b][q].append(vb)
    return streams


def signed_corr(streams, a, b):
    tot, n = 0.0, 0
    for sa, sb in zip(streams[a], streams[b]):
        n += len(sa)
        tot += sum(sa[i] * sb[i] for i in range(len(sa)))
    return tot / n if n else 0.0


def discover(streams, n):
    return {a: max((c for c in range(n) if c != a),
                   key=lambda c: abs(signed_corr(streams, a, c)))
            for a in range(n)}


def floor_at_p(p):
    accs = {}
    for t in T_VALUES:
        run = []
        for d in range(DRAWS):
            r = random.Random(SEED * 100000 + int(p * 1000) * 10 + t * 2 + d)
            partner = make_pairs(N, r)
            streams = streams_for(r, partner, N, p, EPS, t, W)
            found = discover(streams, N)
            run.append(sum(found[c] == partner[c] for c in partner) / N)
        accs[t] = sum(run) / len(run)
    for t in T_VALUES:
        if accs[t] >= ACC_BAR:
            return t, accs
    return None, accs


def fit_beta(points):
    # points: list of (p, C_emp); model log C = log C0 - beta*log(2p-1)
    xs = [math.log(abs(2 * p - 1)) for p, _ in points]
    ys = [math.log(c) for _, c in points]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx if sxx else 0.0
    intercept = my - slope * mx
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
    return math.exp(intercept), -slope, r2


def main():
    c_emp = {}
    floors = {}
    acc_grids = {}
    for p in P_GRID:
        fl, accs = floor_at_p(p)
        floors[p] = fl
        acc_grids[p] = accs
        if fl is not None:
            s = abs(2 * p - 1) * (1 - 2 * EPS)
            c_emp[p] = W * fl * s ** ALPHA

    c0, beta, r2 = fit_beta([(p, c_emp[p]) for p in P_FIT])
    g2_details = {}
    g2_ok = 0
    for p in P_HELDOUT:
        s = abs(2 * p - 1) * (1 - 2 * EPS)
        bound = c0 * abs(2 * p - 1) ** (-beta) / s ** ALPHA
        fl = floors[p]
        wt = W * fl if fl is not None else None
        ok = wt is not None and wt <= bound
        g2_ok += ok
        g2_details[p] = {"floor": fl, "wt": wt, "bound": round(bound, 1),
                         "ratio": round(wt / bound, 5) if wt else None, "ok": ok}
    g2 = g2_ok == len(P_HELDOUT) and all(
        (d["ratio"] or 0) >= 0.02 for d in g2_details.values())
    g1 = r2 >= 0.8

    verdict = "KEEP" if (g1 and g2) else "KILL"
    out = {
        "experiment": "d12p_cp_fit",
        "seed": SEED, "N": N, "W": W, "eps": EPS,
        "p_grid": P_GRID, "p_fit": P_FIT, "p_heldout": P_HELDOUT,
        "T_values": T_VALUES, "draws": DRAWS, "alpha_fixed": ALPHA,
        "T_floors": {str(p): floors[p] for p in P_GRID},
        "acc_grids": {str(p): {str(t): round(a, 4) for t, a in acc_grids[p].items()}
                      for p in P_GRID},
        "C_emp": {str(p): round(c, 1) for p, c in c_emp.items()},
        "fit_C0": round(c0, 1), "fit_beta": round(beta, 4), "fit_r2": round(r2, 4),
        "g1_r2_pass": g1, "g2_details": {str(k): v for k, v in g2_details.items()},
        "verdict": verdict,
    }
    with open("results/d12p_cp_fit.json", "w") as f:
        json.dump(out, f, indent=1)
    print("T_floors:", {p: floors[p] for p in P_GRID})
    print("C_emp:", {p: round(c_emp[p], 1) for p in c_emp})
    print(f"fit: C0={c0:.1f} beta={beta:.4f} r2={r2:.4f}")
    print("heldout:", g2_details)
    print("verdict:", verdict)


if __name__ == "__main__":
    main()
