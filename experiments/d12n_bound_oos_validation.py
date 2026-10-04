#!/usr/bin/env python3
"""D12n — out-of-sample validation of the calibrated s^-alpha noise bound.

D12m found alpha_emp = 1.92 (naive 1/s^2 exponent confirmed) and that the
refit bound W*T <= C/s^alpha with C=600 covers 9/10 cells in-sample
(N=16, W in {4,8}) — but noted the constant was a calibration miss, not
a law miss, and tested nothing out-of-sample. This run asks the falsifiable
question: does the D12m-calibrated bound PREDICT floors at a config it never
saw — N=32 and W=16 — without refitting the constant?

Pre-registered gates (fitted constants from D12m, alpha fixed at 1.92):
  G1: at each (W in {4,8,16}, eps in {0,0.05,0.1,0.2}), the measured T_floor
      satisfies W*T_floor <= C/s^alpha with C = 600 (the original constant,
      NOT refit) — pass if coverage >= 0.8 of cells with a floor.
  G2: floors are monotone non-increasing in W at fixed eps (width buys back
      noise generalizes to W=16).
KEEP iff G1 and G2. Seed 2718. CPU-only, ~5s, no GPU — 6GB/80C guard untouched.
"""
from __future__ import annotations

import json
import random

SEED = 2718
W_VALUES = (4, 8, 16)
N = 32
P = 0.3
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

    # G1: bound coverage with the ORIGINAL constant C=600, alpha=1.92
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

    # G2: floors monotone non-increasing in W at fixed eps (None = infinity)
    inversions = 0
    for e in EPS_VALUES:
        vals = [floors[f"W={w},eps={e}"] for w in W_VALUES]
        vals = [10**9 if v is None else v for v in vals]
        inversions += sum(1 for i in range(len(vals) - 1) if vals[i] < vals[i + 1])
    g2 = inversions == 0

    verdict = "KEEP" if (g1 and g2) else "KILL"
    out = {
        "experiment": "d12n_bound_oos_validation",
        "seed": SEED, "N": N, "p_corr": P, "W": W_VALUES,
        "eps": EPS_VALUES, "T_values": T_VALUES, "draws": DRAWS,
        "acc_bar": ACC_BAR, "alpha_fixed": ALPHA, "C_constant": C_CONST,
        "T_floors": floors, "g1_details": g1_details,
        "g1_bound_coverage": covered / max(cells_with_floor, 1),
        "g2_w_inversions": inversions,
        "verdict": verdict,
    }
    with open("results/d12n_bound_oos_validation.json", "w") as f:
        json.dump(out, f, indent=1)
    print("T_floors:", floors)
    print("G1 coverage (C=600, alpha=1.92, N=32/W=4-16):",
          covered, "/", cells_with_floor)
    print("G2 inversions:", inversions)
    print("verdict:", verdict)


if __name__ == "__main__":
    main()
