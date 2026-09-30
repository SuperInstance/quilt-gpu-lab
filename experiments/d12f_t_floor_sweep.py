#!/usr/bin/env python3
"""D12f — the T-floor sweep: where is the correlation signal BORN?

D11b diagnosed that both don-validation routes failed at T=5 because
|corr| estimates from 5-atom streams are noise. D12e's floor test only went
down to p_corr=0.5 at fixed T=200. This closes the robustness caveat:
sweep T = 5/10/25/50/100/200 at the hardest coupling (p_corr=0.3) and find
the sample-size floor where pure correlation discovery first beats chance.

Metric: partner_id_acc over 8 cells (chance = 1/7 ≈ 0.143 for the argmax pick).
Pre-registered: KEEP the "discovery is born at T_floor" claim iff partner_id_acc
>= 0.9 at some T and the acc-vs-T curve is monotone-ish upward from T=5.
Also re-measure B' reconstruction acc and delta at each T (facts drawn from
last-step atom values, as in D12e).
"""
from __future__ import annotations

import json
import random

SEED = 2718
N_CELLS = 8
QUBITS = 4
K_FACTS = 120
MARGIN = 0.10
T_VALUES = (5, 10, 25, 50, 100, 200)
P_CORR = 0.3


def make_pairs(rng):
    partner = {}
    for i in range(0, N_CELLS, 2):
        partner[i] = i + 1
        partner[i + 1] = i
    return partner


def streams_for(rng, partner, p_corr, t_obs):
    streams = {c: [[] for _ in range(QUBITS)] for c in range(N_CELLS)}
    for t in range(t_obs):
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
    out = {}
    for a in range(N_CELLS):
        others = [c for c in range(N_CELLS) if c != a]
        key = lambda c: corr(streams, a, c)
        out[a] = max(others, key=key) if mode == "max" else min(others, key=key)
    return out


def bootstrap_ci(vals, seed, draws=500):
    r = random.Random(seed)
    n = len(vals)
    means = sorted(sum(vals[r.randrange(n)] for _ in range(n)) / n for _ in range(draws))
    return means[int(0.025 * draws)], means[int(0.975 * draws)]


def run_world(rng, t_obs):
    partner = make_pairs(rng)
    facts = []
    while len(facts) < K_FACTS:
        a = rng.randrange(N_CELLS)
        b = rng.randrange(N_CELLS)
        if a == b:
            continue
        qa, qb = rng.randrange(QUBITS), rng.randrange(QUBITS)
        facts.append((a, qa, b, qb))

    truth_rng = random.Random(SEED + 7000 + t_obs)
    streams = streams_for(rng, partner, P_CORR, t_obs)

    a_vals = [1 if truth_rng.random() < 0.5 else 0 for _ in facts]

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
    c_vals = relational(disc_min)

    acc = lambda v: sum(v) / len(v)
    return {
        "T": t_obs,
        "partner_id_acc": round(id_acc, 3),
        "acc_B_corrkey": round(acc(b_vals), 4),
        "ci_B": [round(x, 3) for x in bootstrap_ci(b_vals, SEED + 11 + t_obs)],
        "acc_C_antipartner": round(acc(c_vals), 4),
        "acc_A": round(acc(a_vals), 4),
        "delta": round(acc(b_vals) - max(acc(a_vals), acc(c_vals)), 4),
    }


def main():
    sweep = []
    for t in T_VALUES:
        rng = random.Random(SEED)
        sweep.append(run_world(rng, t))

    t_floor = None
    for row in sweep:
        if row["partner_id_acc"] >= 0.9:
            t_floor = row["T"]
            break
    verdict = "KEEP" if t_floor is not None else "KILL"
    result = {
        "experiment": "D12f T-floor sweep for pure correlation discovery",
        "seed": SEED, "n_cells": N_CELLS, "qubits": QUBITS, "facts": K_FACTS,
        "p_corr": P_CORR, "t_values": list(T_VALUES),
        "chance_partner_id": round(1 / (N_CELLS - 1), 3),
        "pre_registered": "KEEP iff partner_id_acc >= 0.9 at some T (T_floor); curve should rise from T=5",
        "sweep": sweep,
        "t_floor": t_floor,
        "verdict": verdict,
        "note": "Closes D11b/D12e caveat: at p_corr=0.3 (hardest coupling), finds the sample-size floor where correlation discovery first identifies partners. Directly tests whether the T=5 failure in D11b was a sample-size floor (predicted) vs a validation-mechanism failure.",
    }
    print(json.dumps(result, indent=2))
    with open("results/d12f_t_floor_sweep.json", "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
