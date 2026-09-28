#!/usr/bin/env python3
"""D13c — relational addressing via REINFORCE with baseline.

D13 (naive Hebbian) and D13b (confidence-weighted) both KILL: the reward
signal exists but the credit-assignment rule can't climb it. This is the
textbook next rung: a policy-gradient update with a learned BASELINE. The
baseline subtracts the ~0.5 average reward that wrong partners earn by luck,
leaving only the true partner's consistent +1.0 advantage to accumulate.

Pre-registered: after 30 epochs, reconstruction accuracy >= 0.80 AND edge
concentration on the true partner >= 0.5 (chance 1/7 = 0.143).
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
LR = 0.5


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

    # logit policy per sender over receivers (REINFORCE)
    import math
    logit = [[0.0] * N_CELLS for _ in range(N_CELLS)]
    baseline = [0.5] * N_CELLS

    def softmax(logits, others):
        e = [math.exp(logits[r]) for r in others]
        s = sum(e)
        return [x / s for x in e]

    acc_history = []
    for epoch in range(EPOCHS):
        correct = 0
        for (a, qa, b, qb) in facts:
            others = [r for r in range(N_CELLS) if r != a]
            probs = softmax(logit[a], others)
            r = rng.choices(others, weights=probs, k=1)[0]
            truth = 1 if (cells[a][qa] == cells[b][qb]) else 0
            if r == b:
                recon = truth  # exact
            else:
                recon = 1 if rng.random() < 0.5 else 0
            reward = 1.0 if (recon == truth) else 0.0
            # REINFORCE: gradient of log-prob, scaled by (reward - baseline)
            for j, rr in enumerate(others):
                grad = (1.0 - probs[j]) if rr == r else (-probs[j])
                logit[a][rr] += LR * (reward - baseline[a]) * grad
            baseline[a] = 0.9 * baseline[a] + 0.1 * reward
            correct += 1 if (recon == truth) else 0
        acc_history.append(round(correct / len(facts), 3))

    final = acc_history[-1]
    concentrated = 0
    for (a, qa, b, qb) in facts:
        others = [r for r in range(N_CELLS) if r != a]
        best = max(others, key=lambda r: logit[a][r])
        concentrated += 1 if best == b else 0
    conc = concentrated / len(facts)

    verdict = "KEEP" if (final >= TARGET_ACC and conc >= TARGET_CONC) else "KILL"
    result = {
        "experiment": "D13c relational addressing (REINFORCE with baseline)",
        "seed": SEED, "epochs": EPOCHS, "cells": N_CELLS, "facts": K_FACTS,
        "final_acc": final, "target_acc": TARGET_ACC,
        "edge_concentration": round(conc, 3), "target_conc": TARGET_CONC,
        "acc_history": acc_history,
        "verdict": verdict,
        "note": "policy-gradient with learned baseline; KEEP iff acc>=0.8 AND concentration>=0.5.",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
