#!/usr/bin/env python3
"""D13b — relational addressing with confidence-weighted reward.

D13 killed the naive binary-reward Hebbian rule (0.467, no convergence). The
booked hypothesis: the reward signal was too weak — "matched" vs "coin-flip"
is a 1.0 vs 0.5 difference, but the naive rule discarded the STRUCTURE that
distinguishes a correct partner from a lucky coin. This revision gives the
receiver a CONFIDENCE: when it holds the matching atom (true partner), its
reconstruction is certain (confidence 1.0); when it does not, its confidence
is a noisy 0.5. The reward is the confidence itself, not a binary match, so
true partners earn consistently higher reward and the edge should concentrate.

Pre-registered: after 30 epochs, reconstruction accuracy >= 0.80 AND edge
concentration on the true partner >= 0.5 (vs chance 1/(N-1) = 0.143).
"""
from __future__ import annotations

import json
import random

SEED = 2718
N_CELLS = 8
QUBITS = 4
K_FACTS = 60
EPOCHS = 30
TARGET_ACC = 0.80
TARGET_CONC = 0.50


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

    edge = [[1.0 / (N_CELLS - 1) for _ in range(N_CELLS)] for _ in range(N_CELLS)]
    for i in range(N_CELLS):
        edge[i][i] = 0.0

    acc_history = []
    for epoch in range(EPOCHS):
        correct = 0
        for (a, qa, b, qb) in facts:
            others = [r for r in range(N_CELLS) if r != a]
            probs = [edge[a][r] for r in others]
            r = rng.choices(others, weights=probs, k=1)[0] if sum(probs) > 0 else others[0]
            if r == b:
                # true partner: confident, correct reconstruction
                conf = 1.0
                recon = 1 if (cells[a][qa] == cells[b][qb]) else 0
            else:
                # wrong partner: a noisy guess, confidence ~0.5
                conf = 0.5
                recon = 1 if rng.random() < 0.5 else 0
            truth = 1 if (cells[a][qa] == cells[b][qb]) else 0
            # reward = confidence when right, -confidence when wrong (signed)
            reward = conf if (recon == truth) else -conf
            # confidence-weighted update: true partner gets +1.0 always,
            # wrong partners get +0.5 half the time, -0.5 half the time -> ~0
            for rr in others:
                edge[a][rr] *= 0.95
                if rr == r:
                    edge[a][rr] += 0.05 * reward
                edge[a][rr] = max(0.0, edge[a][rr])
            tot = sum(edge[a][rr] for rr in others) or 1.0
            for rr in others:
                edge[a][rr] /= tot
            correct += 1 if (recon == truth) else 0
        acc_history.append(round(correct / len(facts), 3))

    final = acc_history[-1]
    concentrated = 0
    for (a, qa, b, qb) in facts:
        others = [r for r in range(N_CELLS) if r != a]
        best = max(others, key=lambda r: edge[a][r])
        concentrated += 1 if best == b else 0
    conc = concentrated / len(facts)

    verdict = "KEEP" if (final >= TARGET_ACC and conc >= TARGET_CONC) else "KILL"
    result = {
        "experiment": "D13b relational addressing (confidence-weighted reward)",
        "seed": SEED, "epochs": EPOCHS, "cells": N_CELLS, "facts": K_FACTS,
        "final_acc": final, "target_acc": TARGET_ACC,
        "edge_concentration": round(conc, 3), "target_conc": TARGET_CONC,
        "acc_history": acc_history,
        "verdict": verdict,
        "note": "signed confidence reward (true partner +1.0 always, wrong ~0 net) should concentrate edges; KEEP iff acc>=0.8 AND concentration>=0.5.",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
