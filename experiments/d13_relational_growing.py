#!/usr/bin/env python3
"""D13 — relational intelligence GROWING: cells learn whom to message.

D12 proved the structural baseline: with PERFECT addressing, the relational
graph reconstructs cross-boundary facts at 1.0 (vs isolated 0.558, permuted
0.508). But that handed cells their partner's address. This is the real
falsification Casey named: does the graph LEARN the addressing?

Setup: same cross-boundary world (K facts, each = parity of two atoms in
DIFFERENT cells). But now a cell does NOT know its partner's address a priori.
It broadcasts its atoms, and each receiver can respond to SOME message it
received. The cell updates a message-to-receiver preference by a simple
Hebbian/reinforcement rule: when a receiver's response helps reconstruct a
fact (matches the local parity), the edge strengthens; otherwise it weakens.
Over epochs, edges should concentrate on the correct cross-cell partner.

Falsifiable claim (pre-registered): after T epochs, reconstruction accuracy
on cross-boundary facts must rise from the isolated baseline (~0.5) to >= 0.8
(within 0.2 of the perfect-addressing ceiling 1.0). If it stays near chance,
learned relational addressing does not work -> KILL.
"""
from __future__ import annotations

import json
import random

SEED = 2718
N_CELLS = 8
QUBITS = 4
K_FACTS = 60
EPOCHS = 30
TARGET = 0.80   # pre-registered: must reach >= 0.8 by the end


def main():
    rng = random.Random(SEED)
    cells = [[1 if rng.random() < 0.5 else -1 for _ in range(QUBITS)]
             for _ in range(N_CELLS)]
    facts = []
    while len(facts) < K_FACTS:
        a = rng.randrange(N_CELLS)
        b = rng.randrange(N_CELLS)
        if a == b:
            continue
        facts.append((a, rng.randrange(QUBITS), b, rng.randrange(QUBITS)))

    # Each cell maintains a preference vector over the OTHER cells (whom it
    # sends each atom to). Init uniform. Learn via reward.
    edge = [[1.0 / (N_CELLS - 1) for _ in range(N_CELLS)] for _ in range(N_CELLS)]
    for i in range(N_CELLS):
        edge[i][i] = 0.0

    acc_history = []
    for epoch in range(EPOCHS):
        correct = 0
        # sample the sender's atom, pick a receiver from the preference, and
        # the receiver reconstructs using ITS matching atom (if it has one)
        for (a, qa, b, qb) in facts:
            # sender a chooses a receiver r from its preference
            others = [r for r in range(N_CELLS) if r != a]
            probs = [edge[a][r] for r in others]
            s = sum(probs)
            r = rng.choices(others, weights=probs, k=1)[0] if s > 0 else others[0]
            # reconstruction: receiver r has atom qb? only the TRUE partner b
            # holds the matching atom. If r == b, reconstruction is exact.
            recon = (cells[a][qa] == cells[r][qb]) if (r == b) else (1 if rng.random() < 0.5 else 0)
            truth = 1 if (cells[a][qa] == cells[b][qb]) else 0
            reward = 1 if (recon == truth) else 0
            # Hebbian-ish: strengthen edge a->r on reward, weaken otherwise
            for rr in others:
                edge[a][rr] *= 0.98
                edge[a][rr] += (0.02 if rr == r else 0) * reward
            # normalize
            tot = sum(edge[a][rr] for rr in others) or 1.0
            for rr in others:
                edge[a][rr] /= tot
            correct += 1 if (recon == truth) else 0
        acc = correct / len(facts)
        acc_history.append(round(acc, 3))

    final = acc_history[-1]
    verdict = "KEEP" if final >= TARGET else "KILL"
    # check edges concentrated on the true partner b for each fact
    concentrated = 0
    for (a, qa, b, qb) in facts:
        others = [r for r in range(N_CELLS) if r != a]
        best = max(others, key=lambda r: edge[a][r])
        concentrated += 1 if best == b else 0
    conc_rate = concentrated / len(facts)

    result = {
        "experiment": "D13 relational intelligence growing (learned addressing)",
        "seed": SEED, "epochs": EPOCHS, "cells": N_CELLS, "facts": K_FACTS,
        "final_acc": final, "target": TARGET,
        "acc_history": acc_history,
        "edge_concentration_on_true_partner": round(conc_rate, 3),
        "verdict": verdict,
        "note": "cells learn whom to message via reward; KEEP iff reconstruction reaches 0.80 (within 0.2 of the perfect-addressing 1.0 ceiling).",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
