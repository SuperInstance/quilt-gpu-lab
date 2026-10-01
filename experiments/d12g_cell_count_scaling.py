#!/usr/bin/env python3
"""D12g — cell-count scaling: does the T=25 discovery floor move with N?

D12f found the correlation signal is born at T=25 for N=8 cells (chance 1/7).
This sweep varies N = 8/16/32/64 at the hardest coupling (p_corr=0.3) to test
whether partner_id_acc at fixed T degrades with N (more confusable candidates)
and whether the effective T_floor shifts upward. Chance = 1/(N-1).
Pre-registered: KEEP "floor is N-robust (T=25)" iff partner_id_acc >= 0.8 at
T=25 for every N; KILL the N-robustness if accuracy at T=25 drops below 0.8
for any N >= 16 (i.e., the D12f floor was an artifact of the small pool).
"""
from __future__ import annotations

import json
import random

SEED = 2718
QUBITS = 4
K_FACTS = 120
MARGIN = 0.10
T_VALUES = (25, 50, 100, 200)
N_VALUES = (8, 16, 32, 64)
P_CORR = 0.3
KEEP_BAR = 0.8


def make_pairs(rng, n):
    partner = {}
    for i in range(0, n, 2):
        partner[i] = i + 1
        partner[i + 1] = i
    return partner


def streams_for(rng, partner, p_corr, t_obs):
    n = len(partner)
    streams = {c: [[] for _ in range(QUBITS)] for c in range(n)}
    for t in range(t_obs):
        for a in range(0, n, 2):
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


def discover_max(streams, n):
    out = {}
    for a in range(n):
        others = [c for c in range(n) if c != a]
        out[a] = max(others, key=lambda c: corr(streams, a, c))
    return out


def run_world(rng, n, t_obs):
    partner = make_pairs(rng, n)
    streams = streams_for(rng, partner, P_CORR, t_obs)
    disc = discover_max(streams, n)
    id_acc = sum(1 for c in range(n) if disc[c] == partner[c]) / n
    return id_acc


def main():
    sweep = []
    for n in N_VALUES:
        for t in T_VALUES:
            # 5 pairing/stream draws to tame N=64 variance
            accs = []
            for d in range(5):
                rng = random.Random(SEED + 1000 * n + t + 97 * d)
                accs.append(run_world(rng, n, t))
            mean_acc = sum(accs) / len(accs)
            sweep.append({
                "n_cells": n,
                "T": t,
                "partner_id_acc_mean": round(mean_acc, 4),
                "draws": [round(a, 3) for a in accs],
                "chance": round(1 / (n - 1), 4),
            })

    t25 = {r["n_cells"]: r["partner_id_acc_mean"] for r in sweep if r["T"] == 25}
    robust = all(v >= KEEP_BAR for v in t25.values())
    verdict = "KEEP" if robust else "KILL"
    result = {
        "experiment": "D12g cell-count scaling of correlation discovery",
        "seed": SEED, "qubits": QUBITS, "p_corr": P_CORR, "t_values": list(T_VALUES),
        "n_values": list(N_VALUES), "draws_per_cell": 5,
        "pre_registered": f"KEEP floor-N-robust iff partner_id_acc >= {KEEP_BAR} at T=25 for ALL N",
        "sweep": sweep,
        "t25_by_n": t25,
        "verdict": verdict,
        "note": "Tests whether D12f's T=25 floor holds as the cell pool grows (more confusable candidates per argmax pick).",
    }
    print(json.dumps(result, indent=2))
    with open("results/d12g_cell_count_scaling.json", "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
