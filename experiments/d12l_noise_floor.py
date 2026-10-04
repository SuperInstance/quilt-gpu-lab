#!/usr/bin/env python3
"""D12l — does channel noise move the W*T bandwidth-time floor?

D12i/D12j established: correlation-key partner discovery floors are governed by
the bandwidth-time product W*T (>= ~400 at p_corr=0.3, ~100-200 at p>=0.5).
Untested: what happens when the streams themselves are corrupted by symmetric
measurement noise (each atom flipped with prob eps independently AFTER the
correlation step). This is the realistic degraded-regime question that D11's
hard-noise corner (T=5, p=0.3) touched but never mapped.

Pre-registered gates:
  J1 (noise hurts): T_floor at eps>0 >= T_floor at eps=0 for W=4, N=16, p=0.3.
  J2 (product law survives): defining effective signal s = (2p-1)*(1-2eps),
    floors satisfy W*T_floor <= 600/s^2 (a bonus-consistent bound, not a fit).
Verdict KEEP iff J1 and J2 both hold; KILL otherwise. Chance acc = 1/(N-1).
"""
from __future__ import annotations

import json
import random

SEED = 2718
W_VALUES = (4, 8)
N = 16
P = 0.3
EPS_VALUES = (0.0, 0.05, 0.10, 0.20, 0.30)
T_VALUES = (10, 25, 50, 100, 200, 400)
DRAWS = 3
ACC_BAR = 0.9


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


def corr(streams, a, b):
    tot, n = 0.0, 0
    for sa, sb in zip(streams[a], streams[b]):
        n += len(sa)
        tot += sum(sa[i] * sb[i] for i in range(len(sa)))
    return abs(tot / n) if n else 0.0


def discover(streams, n):
    return {a: max((c for c in range(n) if c != a), key=lambda c: corr(streams, a, c))
            for a in range(n)}


def run_point(w, eps, t, draw):
    rng = random.Random(SEED * 100000 + w * 1000 + int(eps * 100) * 10 + t * 2 + draw)
    partner = make_pairs(N, rng)
    streams = streams_for(rng, partner, N, P, eps, t, w)
    found = discover(streams, N)
    return sum(found[c] == partner[c] for c in partner) / N


def main():
    grid = {}
    for w in W_VALUES:
        for eps in EPS_VALUES:
            for t in T_VALUES:
                accs = [run_point(w, eps, t, d) for d in range(DRAWS)]
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

    # J1: monotone non-decreasing floor in eps at W=4 and W=8
    j1 = []
    for w in W_VALUES:
        vals = [floors[f"W={w},eps={e}"] or 999 for e in EPS_VALUES]
        j1.append(all(vals[i + 1] >= vals[i] for i in range(len(vals) - 1)))

    # J2: W*T_floor <= 600/s^2 with s = (2p-1)(1-2eps)
    s = (2 * P - 1)
    j2 = []
    for w in W_VALUES:
        for e in EPS_VALUES:
            fl = floors[f"W={w},eps={e}"]
            if fl is None:
                j2.append(False)
                continue
            bound = 600 / (s * (1 - 2 * e)) ** 2
            j2.append(w * fl <= bound)

    verdict = "KEEP" if all(j1) and all(j2) else "KILL"
    out = {
        "experiment": "d12l_noise_floor",
        "seed": SEED, "N": N, "p_corr": P, "W": W_VALUES, "eps": EPS_VALUES,
        "T_values": T_VALUES, "draws": DRAWS, "acc_bar": ACC_BAR,
        "acc_grid": grid, "T_floors": floors,
        "J1_noise_monotone": j1, "J2_product_bound": j2, "verdict": verdict,
    }
    with open("results/d12l_noise_floor.json", "w") as f:
        json.dump(out, f, indent=1)
    print("T_floors:", floors)
    print("J1:", j1, "J2:", j2)
    print("verdict:", verdict)


if __name__ == "__main__":
    main()
