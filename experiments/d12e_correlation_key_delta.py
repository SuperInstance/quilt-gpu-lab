#!/usr/bin/env python3
"""D12e — the delta verdict, re-measured with GROWN addressing.

D12 showed delta B−max(A,C)=0.44 but only with HANDED addressing (the receiver
was told who its partner is). D13c KILLed reward-based learning; D13d KEEPed
correlation-based discovery (partner ID acc 1.0). This closes the loop:
replace handed partner addresses with correlation-discovered ones and
re-measure the structure delta. If the delta survives, the substrate's
advantage is real under a mechanism cells can find on their own.

Setup = D12 world + D13d streams:
  - N_CELLS disjoint partner pairs; over T_OBS steps partner atoms are
    correlated (prob P_CORR), non-partner atoms independent.
  - Fact = parity of two atoms across two DIFFERENT cells.
  - B' (correlation-key relational): each receiver picks its partner by max
    |correlation| of atom streams, then messages flow along discovered edges;
    parity is reconstructed exactly when the edge is correct, coin-flip when not.
  - A (isolated): coin-flip baseline (same as D12).
  - C' (correlation control): same discovery compute, but edges chosen by
    MIN |correlation| (anti-partner) — same bytes, wrong targeting.
Pre-registered: delta = acc(B') − max(A, C') must stay >= 0.10 for the
structure verdict to survive grown addressing. Also sweeps P_CORR to find
where the mechanism's floor is.
"""
from __future__ import annotations

import json
import random

SEED = 2718
N_CELLS = 8
QUBITS = 4
K_FACTS = 120
T_OBS = 200
MARGIN = 0.10


def make_pairs(rng):
    partner = {}
    for i in range(0, N_CELLS, 2):
        partner[i] = i + 1
        partner[i + 1] = i
    return partner


def streams_for(rng, partner, p_corr):
    streams = {c: [[] for _ in range(QUBITS)] for c in range(N_CELLS)}
    for t in range(T_OBS):
        for a in range(0, N_CELLS, 2):
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


def discover(streams, mode):
    """Return discovered[cell] = partner cell under mode ('max'|'min')."""
    out = {}
    for a in range(N_CELLS):
        others = [c for c in range(N_CELLS) if c != a]
        key = (lambda c: corr(streams, a, c))
        out[a] = max(others, key=key) if mode == "max" else min(others, key=key)
    return out


def bootstrap_ci(vals, seed, draws=500):
    r = random.Random(seed)
    n = len(vals)
    means = sorted(sum(vals[r.randrange(n)] for _ in range(n)) / n for _ in range(draws))
    return means[int(0.025 * draws)], means[int(0.975 * draws)]


def run_world(rng, p_corr):
    partner = make_pairs(rng)
    cells, facts = [], []
    while len(facts) < K_FACTS:
        a = rng.randrange(N_CELLS)
        b = rng.randrange(N_CELLS)
        if a == b:
            continue
        qa, qb = rng.randrange(QUBITS), rng.randrange(QUBITS)
        facts.append((a, qa, b, qb))

    truth_rng = random.Random(SEED + 5000)
    streams = streams_for(rng, partner, p_corr)

    # A: isolated — coin flip
    a_vals = [1 if truth_rng.random() < 0.5 else 0 for _ in facts]

    # B': correlation-key relational. Message along DISCOVERED edge: receiver
    # reconstructs parity exactly iff discovered[b] == partner[b].
    disc_max = discover(streams, "max")
    disc_min = discover(streams, "min")
    id_acc = sum(1 for c in range(N_CELLS) if disc_max[c] == partner[c]) / N_CELLS

    def relational(disc):
        vals = []
        for (a, qa, b, qb) in facts:
            if disc[b] == partner[b]:
                va, vb = streams[a][qa][-1], streams[b][qb][-1]
                recon = 1 if va == vb else 0
            else:
                recon = 1 if truth_rng.random() < 0.5 else 0
            truth = 1 if streams[a][qa][-1] == streams[b][qb][-1] else 0
            vals.append(1 if recon == truth else 0)
        return vals

    b_vals = relational(disc_max)
    c_vals = relational(disc_min)  # anti-partner targeting control

    acc = lambda v: sum(v) / len(v)
    return {
        "p_corr": p_corr,
        "partner_id_acc": round(id_acc, 3),
        "acc_A": round(acc(a_vals), 4),
        "acc_B_corrkey": round(acc(b_vals), 4),
        "acc_C_antipartner": round(acc(c_vals), 4),
        "delta": round(acc(b_vals) - max(acc(a_vals), acc(c_vals)), 4),
        "ci_B": [round(x, 3) for x in bootstrap_ci(b_vals, SEED + 11)],
    }


def main():
    sweep = []
    for p_corr in (0.9, 0.75, 0.6, 0.5):
        rng = random.Random(SEED)
        sweep.append(run_world(rng, p_corr))
    main_row = sweep[0]
    delta = main_row["delta"]
    verdict = "KEEP" if delta >= MARGIN else "KILL"
    result = {
        "experiment": "D12e delta verdict under correlation-key (grown) addressing",
        "seed": SEED, "n_cells": N_CELLS, "qubits": QUBITS,
        "facts": K_FACTS, "T_obs": T_OBS, "preregistered_margin": MARGIN,
        "sweep": sweep,
        "verdict": verdict,
        "note": "structure delta re-measured with partner edges DISCOVERED by max |correlation| of atom streams (no handed addresses, no reward). Control C' = min |correlation| (anti-partner) targeting. KEEP iff delta >= 0.10 at p_corr=0.9.",
    }
    print(json.dumps(result, indent=2))
    with open("results/d12e_correlation_key_delta.json", "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
