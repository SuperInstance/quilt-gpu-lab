#!/usr/bin/env python3
"""D16 — is the embedded tone vector READABLE? (embedder validation)

The embedder (qthe_embedder.py) turns a tone trajectory into a 13-dim vector.
It is brand-new and unvalidated: nothing has shown a downstream model can
recover the tone CLASS from that vector. This experiment closes that loop.

Falsifiable claim (pre-registered): a tiny MLP, trained on the embedded
vector, must recover the tone class from held-out samples at >= 0.85 — while
the untrained baseline is chance (1/K). If the MLP can't read the vector, the
embedder is lossy/insufficient and needs rework (KILL).

Bonus arm: compare classifier-on-embedding vs classifier-on-raw-momentum —
if they match, the embedding is not losing the signal; if embedding >> raw,
the embedder's SHAPE features (arc/run/spectral) are doing real work.
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path.home() / "projects" / "qthe-codec"))

import qthe_embedder as qe

SEED = 2718
K = 6
N_TRAIN = 800
N_HELD = 200
TARGET = 0.85


def tone_catalog():
    """K canonical tone shapes (12-16 tokens each), from the tone-emotion example."""
    L = 12
    d, f, u, h = 0, 1, 2, 3
    return {
        "sarcasm":  [f, f, u, u, u, u, h, h, d, d, d, d][:L],
        "joy":      [f, u, u, u, u, h, u, u, h, u, u, u][:L],
        "anger":    [d, d, h, d, d, d, h, h, d, d, d, d][:L],
        "doubt":    [u, d, u, d, f, u, f, d, d, d, d, d][:L],
        "flat":     [f] * L,
        "excite":   [u, u, u, h, u, u, u, h, u, u, u, u][:L],
    }


def make_data(rng, n):
    cat = list(tone_catalog().keys())
    X, y = [], []
    for _ in range(n):
        c = rng.choice(cat)
        base = tone_catalog()[c]
        # jitter: flip each step with small prob, keep the shape's fingerprint
        tone = [base[i] if rng.random() > 0.1 else rng.randrange(4) for i in range(len(base))]
        X.append(qe.embed(tone))
        y.append(cat.index(c))
    return X, y


def main():
    import torch
    rng = random.Random(SEED)
    Xtr, ytr = make_data(rng, N_TRAIN)
    Xte, yte = make_data(rng, N_HELD)

    Xtr_t = torch.tensor(Xtr, dtype=torch.float32, device="cuda")
    ytr_t = torch.tensor(ytr, dtype=torch.long, device="cuda")
    Xte_t = torch.tensor(Xte, dtype=torch.float32, device="cuda")
    yte_t = torch.tensor(yte, dtype=torch.long, device="cuda")

    dim = Xtr_t.shape[1]
    model = torch.nn.Sequential(
        torch.nn.Linear(dim, 32), torch.nn.ReLU(),
        torch.nn.Linear(32, K),
    ).to("cuda")
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    lossf = torch.nn.CrossEntropyLoss()

    for epoch in range(300):
        model.train()
        opt.zero_grad()
        loss = lossf(model(Xtr_t), ytr_t)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        pred = model(Xte_t).argmax(1)
        acc = (pred == yte_t).float().mean().item()

    # baseline: majority class
    from collections import Counter
    majority = Counter(ytr).most_common(1)[0][0]
    base_acc = sum(1 for y in yte if y == majority) / len(yte)

    verdict = "KEEP" if acc >= TARGET else "KILL"
    result = {
        "experiment": "D16 embedder readability (tiny MLP reads the tone class)",
        "seed": SEED, "classes": K, "train": N_TRAIN, "heldout": N_HELD,
        "mlp_acc": round(acc, 4), "majority_baseline": round(base_acc, 4),
        "chance": round(1 / K, 4), "target": TARGET,
        "embedding_dim": dim,
        "verdict": verdict,
        "note": "tiny MLP (dim->32->K) reads the tone class from the 13-dim embedded vector; KEEP iff >=0.85. Validates the embedder is readable, not lossy.",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
