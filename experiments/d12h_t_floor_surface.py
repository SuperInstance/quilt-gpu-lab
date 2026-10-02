#!/usr/bin/env python3
"""D12h — fit the T_floor(N, p_corr) surface for correlation-key discovery.

D12f found the discovery floor at T=25 for N=8, p_corr=0.3. D12g found the
floor shifts up with N (roughly T_floor ~ N at p=0.3, 3 points, not a fit).
This closes the scaling lane: grid over N x p_corr x T with multiple pairing
draws per cell, estimate T_floor(N, p) = smallest T with partner_id_acc >= 0.9,
and check whether a simple law (T_floor ~ N / f(p)) describes the surface.

Pre-registered: KEEP the "T_floor is governed by signal-vs-confusable-candidates"
claim iff (a) T_floor decreases monotonically-ish in p_corr at fixed N, and
(b) a log-linear fit of log T_floor vs log N at p=0.3 has slope in [0.7, 1.3].
"""
from __future__ import annotations

import json
import random

SEED = 2718
QUBITS = 4
N_VALUES = (8, 16, 32, 64)
P_VALUES = (0.3, 0.5, 0.7)
T_VALUES = (5, 10, 25, 50, 100, 200)
DRAWS = 3          # independent pairing draws per (N, p, T)
ACC_BAR = 0.9


def make_pairs(n, rng):
    partner = {}
    perm = list(range(n))
    rng.shuffle(perm)
    for i in range(0, n, 2):
        a, b = perm[i], perm[i + 1]
        partner[a] = b
        partner[b] = a
    return partner


def streams_for(rng, partner, n, p_corr, t_obs):
    streams = {c: [[] for _ in range(QUBITS)] for c in range(n)}
    for _ in range(t_obs):
        seen = set()
        for a in partner:
            if a in seen:
                continue
            seen.add(a)
            seen.add(partner[a])
            b = partner[a]
            for q in range(QUBITS):
                if rng.random() < p_corr:
                    base = 1 if rng.random() < 0.5 else -1
                    streams[a][q].append(base)
                    streams[b][q].append(base)
                else:
                    streams[a][q].append(1 if rng.random() < 0.5 else -1)
                    streams[b][q].append(1 if rng.random() < 0.5 else -1)
    return streams


def corr(streams, a, b):
    tot, n = 0.0, 0
    for q in range(QUBITS):
        sa, sb = streams[a][q], streams[b][q]
        n += len(sa)
        tot += sum(sa[i] * sb[i] for i in range(len(sa)))
    return abs(tot / n) if n else 0.0


def discover(streams, n):
    out = {}
    for a in range(n):
        others = [c for c in range(n) if c != a]
        out[a] = max(others, key=lambda c: corr(streams, a, c))
    return out


def run_cell(n, p, t, draw):
    rng = random.Random(SEED * 100000 + n * 1000 + int(p * 100) * 10 + t * 2 + draw)
    partner = make_pairs(n, rng)
    streams = streams_for(rng, partner, n, p, t)
    disc = discover(streams, n)
    return sum(1 for c in range(n) if disc[c] == partner[c]) / n


def main():
    grid = []
    for n in N_VALUES:
        for p in P_VALUES:
            for t in T_VALUES:
                accs = [run_cell(n, p, t, d) for d in range(DRAWS)]
                grid.append({
                    "N": n, "p_corr": p, "T": t,
                    "partner_id_acc": round(sum(accs) / len(accs), 4),
                    "chance": round(1 / (n - 1), 4),
                    "accs": [round(a, 3) for a in accs],
                })

    # T_floor per (N, p): smallest T whose mean acc >= 0.9
    floors = {}
    for row in grid:
        key = (row["N"], row["p_corr"])
        if row["partner_id_acc"] >= ACC_BAR and key not in floors:
            floors[key] = row["T"]

    # (a) monotone-ish decrease in p at fixed N (allow one inversion)
    mono = {}
    for n in N_VALUES:
        vals = [floors.get((n, p), 999) for p in P_VALUES]
        inversions = sum(1 for i in range(len(vals) - 1) if vals[i + 1] > vals[i])
        mono[n] = {"floors_by_p": dict(zip(map(str, P_VALUES), vals)),
                   "p_inversions": inversions}

    # (b) log-log fit of T_floor vs N at p=0.3
    import math
    pts = [(n, floors[(n, 0.3)]) for n in N_VALUES if (n, 0.3) in floors]
    slope = None
    if len(pts) >= 2:
        xs = [math.log(n) for n, _ in pts]
        ys = [math.log(t) for _, t in pts]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / \
                sum((x - mx) ** 2 for x in xs)

    cond_a = all(m["p_inversions"] <= 1 for m in mono.values())
    cond_b = slope is not None and 0.7 <= slope <= 1.3
    verdict = "KEEP" if (cond_a and cond_b) else "KILL"

    result = {
        "experiment": "D12h T_floor(N, p_corr) surface fit",
        "seed": SEED, "qubits": QUBITS, "draws_per_cell": DRAWS,
        "acc_bar": ACC_BAR,
        "grid": grid,
        "t_floors": {f"N={n},p={p}": t for (n, p), t in sorted(floors.items())},
        "monotonicity_in_p": mono,
        "loglog_slope_Tfloor_vs_N_at_p0.3": None if slope is None else round(slope, 3),
        "cond_a_p_monotone": cond_a,
        "cond_b_slope_in_[0.7,1.3]": cond_b,
        "verdict": verdict,
    }
    with open("results/d12h_t_floor_surface.json", "w") as f:
        json.dump(result, f, indent=2)

    print("T_floors:", result["t_floors"])
    print("monotonicity:", {n: m["floors_by_p"] for n, m in mono.items()})
    print("loglog slope at p=0.3:", result["loglog_slope_Tfloor_vs_N_at_p0.3"])
    print("verdict:", verdict)


if __name__ == "__main__":
    main()
