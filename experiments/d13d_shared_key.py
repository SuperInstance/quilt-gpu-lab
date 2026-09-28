#!/usr/bin/env python3
"""D13d — shared-key discovery: correlation, not reward.

D13 (Hebbian), D13b (confidence-weighted), D13c (REINFORCE) all KILLed:
reward-based credit assignment cannot learn the relational partner in a sparse
setting. This tests the OTHER mechanism — "shared-key discovery" — that Casey
named: two cells that are truly related have ATOMS THAT ARE CORRELATED across
time, and a cell can detect its partner DIRECTLY by computing the correlation
of its atom stream against every other cell, with NO reward signal at all.

Setup: over T observation steps, each cell's atoms are re-sampled with noise.
A true partner pair's matching atoms are CORRELATED (equal with prob p>0.5, or
opposite); non-partner atoms are independent (coin-flip). A cell identifies
its partner as the cell whose atom stream has the highest |correlation| with
its own.

Pre-registered: correlation-based identification must find the true partner
with >= 0.9 accuracy — decisively beating all three RL variants (0.2-0.3
concentration, which is barely above chance 0.143). If correlation cracks it,
the finding is sharp: the relational primitive is CORRELATION DETECTION
(mutual information), not reward accumulation.
"""
from __future__ import annotations

import json
import random

SEED = 2718
N_CELLS = 8
QUBITS = 4
T_OBS = 200       # observation steps
P_CORR = 0.9      # true partner atoms agree with this probability
TARGET = 0.90


def main():
    rng = random.Random(SEED)

    # true partner pairs: DISJOINT pairs (0,1),(2,3),(4,5),(6,7). Each cell has
    # exactly ONE partner and appears in exactly ONE stream, so correlation is
    # not scrambled by double-appends.
    partner = {}
    cells_list = list(range(N_CELLS))
    for i in range(0, N_CELLS, 2):
        partner[i] = i + 1
        partner[i + 1] = i

    # stream of atom values per cell (qubit 0) over T observations
    streams = {c: [] for c in range(N_CELLS)}
    for t in range(T_OBS):
        # sample an independent base for each pair's "hidden" value
        for a in range(N_CELLS):
            b = partner[a]
            if a < b:
                base = 1 if rng.random() < 0.5 else -1
                # partner pair shares the base with prob P_CORR, else independent
                if rng.random() < P_CORR:
                    va = vb = base
                else:
                    va = 1 if rng.random() < 0.5 else -1
                    vb = 1 if rng.random() < 0.5 else -1
                streams[a].append(va)
                streams[b].append(vb)

    # each cell computes correlation (mean of product, i.e. agreement) with all
    def corr(a, b):
        n = min(len(streams[a]), len(streams[b]))
        if n == 0:
            return 0.0
        return abs(sum(streams[a][i] * streams[b][i] for i in range(n)) / n)

    correct = 0
    for a in range(N_CELLS):
        others = [c for c in range(N_CELLS) if c != a]
        best = max(others, key=lambda c: corr(a, c))
        correct += 1 if best == partner[a] else 0
    acc = correct / N_CELLS

    verdict = "KEEP" if acc >= TARGET else "KILL"
    result = {
        "experiment": "D13d shared-key discovery (correlation, not reward)",
        "seed": SEED, "cells": N_CELLS, "observations": T_OBS, "p_corr": P_CORR,
        "partner_identification_acc": round(acc, 3), "target": TARGET,
        "verdict": verdict,
        "note": "cells identify their partner by max |correlation| of atom streams, with NO reward signal. KEEP iff >=0.90, decisively beating the RL variants (0.2-0.3).",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
