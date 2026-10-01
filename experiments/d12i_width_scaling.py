#!/usr/bin/env python3
"""D12i — QUBITS (channel-width) scaling of correlation-key discovery.

D12h closed the (N, p_corr) surface with the rule "T >= 50 is universal for
exact partner discovery" at fixed QUBITS=4. This opens the width lane: does
that universal hold as the per-cell channel width W=QUBITS grows? Intuition:
more qubits = more independent correlation sub-channels, so the discovery
signal per timestep grows roughly linearly in W and T_floor should SHRINK
with W. Pre-registered: KEEP the width claim iff
  (a) T_floor(W) is non-increasing in W at every tested N and p_corr, and
  (b) at the hardest corner (N=64, p=0.3), W=16 reaches partner_id_acc >= 0.9
      at T=25 or below (i.e. width buys back at least one grid rung of T).
"""
from __future__ import annotations

import json
import random

SEED = 2718
W_VALUES = (2, 4, 8, 16)
N_VALUES = (8, 16, 32, 64)
P_VALUES = (0.3, 0.5, 0.7)
T_VALUES = (5, 10, 25, 50, 100, 200)
DRAWS = 3
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


def streams_for(rng, partner, n, p_corr, t_obs, w):
    streams = {c: [[] for _ in range(w)] for c in range(n)}
    for _ in range(t_obs):
        seen = set()
        for a in partner:
            if a in seen:
                continue
            seen.add(a)
            seen.add(partner[a])
            b = partner[a]
            for q in range(w):
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
    for q in range(len(streams[a])):
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


def run_cell(n, p, t, w, draw):
    rng = random.Random(SEED * 100000 + w * 10000 + n * 1000 + int(p * 100) * 10 + t * 2 + draw)
    partner = make_pairs(n, rng)
    streams = streams_for(rng, partner, n, p, t, w)
    disc = discover(streams, n)
    return sum(1 for c in range(n) if disc[c] == partner[c]) / n


def main():
    grid = []
    for w in W_VALUES:
        for n in N_VALUES:
            for p in P_VALUES:
                for t in T_VALUES:
                    accs = [run_cell(n, p, t, w, d) for d in range(DRAWS)]
                    grid.append({
                        "W": w, "N": n, "p_corr": p, "T": t,
                        "partner_id_acc": round(sum(accs) / len(accs), 4),
                        "chance": round(1 / (n - 1), 4),
                    })

    def floor(w, n, p):
        rows = sorted((r for r in grid if r["W"] == w and r["N"] == n and r["p_corr"] == p),
                      key=lambda r: r["T"])
        for r in rows:
            if r["partner_id_acc"] >= ACC_BAR:
                return r["T"]
        return None

    floors = {(w, n, p): floor(w, n, p)
              for w in W_VALUES for n in N_VALUES for p in P_VALUES}

    # (a) monotone non-increasing in W at fixed (N, p), ignoring None floors
    inversions = []
    for n in N_VALUES:
        for p in P_VALUES:
            seq = [floors[(w, n, p)] for w in W_VALUES]
            avail = [s for s in seq if s is not None]
            for i in range(1, len(seq)):
                if seq[i] is not None and seq[i - 1] is not None and seq[i] > seq[i - 1]:
                    inversions.append({"N": n, "p": p, "w_prev": W_VALUES[i - 1],
                                       "w": W_VALUES[i], "t_prev": seq[i - 1], "t": seq[i]})

    hard = [r for r in grid if r["W"] == 16 and r["N"] == 64 and r["p_corr"] == 0.3 and r["T"] == 25]
    hard_acc = hard[0]["partner_id_acc"] if hard else None

    result = {
        "experiment": "d12i_width_scaling",
        "seed": SEED, "draws": DRAWS,
        "pre_registered": {
            "a": "T_floor(W) non-increasing in W at fixed (N, p)",
            "b": "W=16, N=64, p=0.3 reaches acc>=0.9 at T<=25",
        },
        "floors": {f"W{w}_N{n}_p{p}": t for (w, n, p), t in sorted(floors.items())},
        "monotonicity_inversions": inversions,
        "hard_corner_acc_W16_N64_p03_T25": hard_acc,
        "grid": grid,
    }
    with open("results/d12i_width_scaling.json", "w") as f:
        json.dump(result, f, indent=2)

    keep = not inversions and hard_acc is not None and hard_acc >= ACC_BAR
    print("T_floors (W x N at p=0.3):")
    for w in W_VALUES:
        print(f"  W={w}: " + ", ".join(f"N{n}={floors[(w, n, 0.3)]}" for n in N_VALUES))
    print("inversions:", len(inversions))
    print("hard corner acc (W=16, N=64, p=0.3, T=25):", hard_acc)
    print("VERDICT:", "KEEP" if keep else "KILL")


if __name__ == "__main__":
    main()
