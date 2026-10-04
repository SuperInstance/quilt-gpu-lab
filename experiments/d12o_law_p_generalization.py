#!/usr/bin/env python3
"""D12o — p-generalization of the calibrated noise law.

D12n validated T_floor = C/(W * ((2p-1)(1-2eps))^1.92) with C=600,
alpha=1.92 — but ONLY at p=0.3. The p-dependence (the (2p-1) factor in s)
has never been tested out-of-sample. NOTE: p=0.5 is the degenerate point
(2p-1 = 0, partner streams uncorrelated by construction, s=0) — the first
draft of this script crashed with ZeroDivisionError exactly there, which is
the model correctly saying discovery is impossible at chance coupling. The
real untested coupling is p=0.7. This run asks the falsifiable question:
does the SAME constant C=600 and alpha=1.92 predict T_floors at p=0.7?

Pre-registered gates (no refitting):
  G1: measured floors satisfy W*T_floor <= 600 / s^1.92 with
      s = (2*0.7-1)*(1-2eps) = 0.4*(1-2eps), coverage >= 0.8 of cells
      with floors.
  G2: floors monotone non-increasing in W at fixed eps (0 inversions).
  G1b: the law is not vacuously loose — mean ratio of measured W*T_floor
      to the bound must be >= 0.02 (calibration-era in-sample ratios were
      ~0.1-0.2; if the p-factor is wrong in the loose direction the ratio
      collapses toward 0).
KEEP iff G1 and G2 and G1b. Seed 2718. CPU-only, ~1min, 6GB/80C guard untouched.
"""
from __future__ import annotations

import json
import random

SEED = 2718
W_VALUES = (4, 8, 16)
N = 32
P = 0.7
EPS_VALUES = (0.0, 0.05, 0.10, 0.20)
T_VALUES = (10, 25, 50, 100, 200, 400, 800)
DRAWS = 3
ACC_BAR = 0.9
ALPHA = 1.92
C_CONST = 600.0


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


def main():
    grid = {}
    for w in W_VALUES:
        for eps in EPS_VALUES:
            for t in T_VALUES:
                accs = []
                for d in range(DRAWS):
                    r = random.Random(SEED * 100000 + w * 1000 + int(eps * 100) * 10 + t * 2 + d)
                    partner = make_pairs(N, r)
                    streams = streams_for(r, partner, N, P, eps, t, w)
                    found = discover(streams, N)
                    accs.append(sum(found[c] == partner[c] for c in partner) / N)
                grid[f"{w}|{eps}|{t}"] = sum(accs) / len(accs)

    floors = {}
    for w in W_VALUES:
        for eps in EPS_VALUES:
            floor = None
            for t in T_VALUES:
                if grid[f"{w}|{eps}|{t}"] >= ACC_BAR:
                    floor = t
                    break
            floors[f"W={w},eps={eps}"] = floor

    # G1: bound coverage with the SAME C=600, alpha=1.92, now s = (2p-1)(1-2eps)
    s_base = (2 * P - 1)
    covered = cells_with_floor = 0
    g1_details = {}
    for w in W_VALUES:
        for e in EPS_VALUES:
            fl = floors[f"W={w},eps={e}"]
            if fl is None:
                continue
            cells_with_floor += 1
            bound = C_CONST / abs(s_base * (1 - 2 * e)) ** ALPHA
            ok = w * fl <= bound
            covered += ok
            g1_details[f"W={w},eps={e}"] = {"floor": fl, "wt": w * fl,
                                            "bound": round(bound, 1), "ok": ok}
    g1 = cells_with_floor > 0 and covered / cells_with_floor >= 0.8

    # G1b: non-vacuous looseness — mean measured/bound ratio must not collapse
    ratios = [g1_details[k]["wt"] / g1_details[k]["bound"] for k in g1_details]
    mean_ratio = sum(ratios) / len(ratios) if ratios else 0.0
    g1b = mean_ratio >= 0.02

    # G2: floors monotone non-increasing in W at fixed eps (None = infinity)
    inversions = 0
    for e in EPS_VALUES:
        vals = [floors[f"W={w},eps={e}"] for w in W_VALUES]
        vals = [10**9 if v is None else v for v in vals]
        inversions += sum(1 for i in range(len(vals) - 1) if vals[i] < vals[i + 1])
    g2 = inversions == 0

    verdict = "KEEP" if (g1 and g2 and g1b) else "KILL"
    out = {
        "experiment": "d12o_law_p_generalization",
        "seed": SEED, "N": N, "p_corr": P, "W": W_VALUES,
        "eps": EPS_VALUES, "T_values": T_VALUES, "draws": DRAWS,
        "acc_bar": ACC_BAR, "alpha_fixed": ALPHA, "C_constant": C_CONST,
        "acc_grid": grid,
        "T_floors": floors, "g1_details": g1_details,
        "g1_bound_coverage": covered / max(cells_with_floor, 1),
        "g1b_mean_ratio": round(mean_ratio, 5),
        "g2_w_inversions": inversions,
        "verdict": verdict,
    }
    with open("results/d12o_law_p_generalization.json", "w") as f:
        json.dump(out, f, indent=1)
    print("T_floors:", floors)
    print("G1 coverage (C=600, alpha=1.92, p=0.7 N=32/W=4-16):",
          covered, "/", cells_with_floor)
    print("G1b mean measured/bound ratio:", round(mean_ratio, 5))
    print("G2 inversions:", inversions)
    print("verdict:", verdict)


if __name__ == "__main__":
    main()
