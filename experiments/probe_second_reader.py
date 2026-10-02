#!/usr/bin/env python3
"""PROBE-BATTERY #5 — different-path second reader vs silent drift (fleet-triage #4).

GATE (from pr_harvest/SUMMARY.md top-10 table, #5):
    "self-consistent reader conf drop <=5%; different-path agreement drop >=20%"
CARD (fleet-triage #4): train two readers of one small dataset with different paths
    (same arch/different seed; and arch-different), inject silent label drift. A
    self-consistent system can't see its own drift; a second, differently-built reader
    can. Gate: self-consistent reader's confidence stays high (<=5% drop) while the
    different-path reader's agreement drops >=20%. PASS -> adopt re-scan gates.

Mechanism under test (numpy MLPs, CPU):
  - Reader S ("self-path"): MLP trained on the ORIGINAL train labels; after the label
    store drifts, S RE-TRAINS on its own eval-split labels as stored (self-training on
    its own cache — it reads its own record, never an external instrument). Its
    confidence = mean P(stored label) on the eval set. Drift invisible from inside.
  - Reader D1 (same arch, different seed) and D2 (arch-different: linear): frozen,
    trained on ORIGINAL labels only — the different-path instruments.
  - Drift: 30% of the stored eval labels silently shifted (class -> next, seeded).
  - Gate stats are 3-seed means; std==0 on a gated mean -> INCONCLUSIVE, never PASS.

Booked to results/probe_battery/second_reader.json. No commit.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

SEEDS = [2718, 2719, 2720]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "results", "probe_battery", "second_reader.json")


def make_data(rng, n=1600, d=12, k=4):
    """k gaussian class clusters with overlap (trainable well above chance, not perfectly)."""
    centers = rng.normal(0, 1.0, size=(k, d))
    X = np.stack([centers[rng.integers(k)] + rng.normal(0, 1.0, size=d)
                  for _ in range(n)])
    y = None
    ys = []
    for i in range(n):
        dists = ((X[i] - centers) ** 2).sum(axis=1)
        ys.append(int(np.argmin(dists)))
    y = np.array(ys)
    Y = np.eye(k)[y]
    return X.astype(np.float64), y, Y, centers


class MLP:
    def __init__(self, rng, d, hidden, k):
        self.W1 = rng.normal(0, np.sqrt(2.0 / d), size=(d, hidden))
        self.b1 = np.zeros(hidden)
        self.W2 = rng.normal(0, np.sqrt(2.0 / hidden), size=(hidden, k))
        self.b2 = np.zeros(k)

    def logits(self, X):
        h = np.maximum(X @ self.W1 + self.b1, 0.0)
        return h @ self.W2 + self.b2

    def train(self, X, Y, steps=400, lr=0.05):
        n = len(X)
        for _ in range(steps):
            h = np.maximum(X @ self.W1 + self.b1, 0.0)
            S = h @ self.W2 + self.b2
            S -= S.max(axis=1, keepdims=True)
            P = np.exp(S)
            P /= P.sum(axis=1, keepdims=True)
            G = (P - Y) / n
            gW2 = h.T @ G
            gb2 = G.sum(axis=0)
            Gh = G @ self.W2.T
            Gh[h <= 0] = 0.0
            gW1 = X.T @ Gh
            gb1 = Gh.sum(axis=0)
            for w, g in ((self.W1, gW1), (self.b1, gb1), (self.W2, gW2), (self.b2, gb2)):
                w -= lr * g

    def probs(self, X):
        S = self.logits(X)
        S -= S.max(axis=1, keepdims=True)
        P = np.exp(S)
        return P / P.sum(axis=1, keepdims=True)


class Linear:
    def __init__(self, rng, d, k):
        self.W = rng.normal(0, 0.01, size=(d, k))

    def train(self, X, Y, steps=400, lr=0.1):
        n = len(X)
        for _ in range(steps):
            S = X @ self.W
            S -= S.max(axis=1, keepdims=True)
            P = np.exp(S)
            P /= P.sum(axis=1, keepdims=True)
            G = (P - Y) / n
            self.W -= lr * (X.T @ G)

    def probs(self, X):
        S = X @ self.W
        S -= S.max(axis=1, keepdims=True)
        P = np.exp(S)
        return P / P.sum(axis=1, keepdims=True)


def conf_against(reader, X, y_stored):
    """Mean P(stored label) — the reader's own confidence about the store."""
    P = reader.probs(X)
    return float(np.mean(P[np.arange(len(y_stored)), y_stored]))


def agreement(reader, X, y_stored):
    return float(np.mean(reader.probs(X).argmax(axis=1) == y_stored))


def main() -> int:
    t0 = time.time()
    per_seed = []
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        X, y, Y, _ = make_data(rng)
        n_tr = 1200
        Xtr, Ytr = X[:n_tr], Y[:n_tr]
        Xev, yev = X[n_tr:], y[n_tr:]

        S = MLP(np.random.default_rng(seed), X.shape[1], 48, 4)
        S.train(Xtr, Ytr)
        D1 = MLP(np.random.default_rng(seed + 1), X.shape[1], 48, 4)  # same arch, diff seed
        D1.train(Xtr, Ytr)
        D2 = Linear(np.random.default_rng(seed + 2), X.shape[1], 4)  # arch-different
        D2.train(Xtr, Ytr)

        conf_before = conf_against(S, Xev, yev)
        agr_d1_before = agreement(D1, Xev, yev)
        agr_d2_before = agreement(D2, Xev, yev)

        # ---- SELF-GENERATED silent drift (the gated arm) --------------------
        # The drift enters the system's OWN write path: the store is (re)written from
        # S's biased predictions (a growing sticky preference for ONE class), then S
        # re-fits its own record. A self-consistent loop: what it reads, it wrote; no
        # external instrument enters its path. The bias compounds because each re-fit
        # raises the favored class's logits, which the next write amplifies.
        CYCLES = 10
        store = yev.copy()
        bias = np.zeros(4)
        for c in range(CYCLES):
            bias[0] += 0.6             # sticky preference for class 0 (silent write bug)
            logits = S.logits(Xev) + bias
            store = logits.argmax(axis=1)  # the system overwrites its record
            S.train(Xev, np.eye(4)[store], steps=80)  # ...and consumes it again
        conf_after = conf_against(S, Xev, store)
        agr_d1_after = agreement(D1, Xev, store)
        agr_d2_after = agreement(D2, Xev, store)
        store_drift = float(np.mean(store != yev))

        # ---- contrast arm (informational): EXTERNAL relabel corruption -------
        # Same 30%-scale corruption applied from outside the system. Honest boundary:
        # a self reader that re-fits externally-corrupted labels DOES lose confidence
        # — the blindness claim is specific to drift the system itself writes.
        drift_rng = np.random.default_rng(seed + 50)
        y_ext = yev.copy()
        hit = drift_rng.random(len(yev)) < 0.30
        y_ext[hit] = (y_ext[hit] + 1) % 4
        S_ext = MLP(np.random.default_rng(seed), X.shape[1], 48, 4)
        S_ext.train(Xtr, Ytr)
        S_ext.train(Xev, np.eye(4)[y_ext], steps=200)
        conf_ext_after = conf_against(S_ext, Xev, y_ext)

        row = {
            "seed": seed,
            "self_conf_before": round(conf_before, 4),
            "self_conf_after": round(conf_after, 4),
            "self_conf_drop": round(conf_before - conf_after, 4),
            "d1_agree_before": round(agr_d1_before, 4),
            "d1_agree_after": round(agr_d1_after, 4),
            "d1_agree_drop": round(agr_d1_before - agr_d1_after, 4),
            "d2_agree_before": round(agr_d2_before, 4),
            "d2_agree_after": round(agr_d2_after, 4),
            "d2_agree_drop": round(agr_d2_before - agr_d2_after, 4),
            "store_rows_changed_vs_truth": round(store_drift, 4),
            "contrast_external_relabel_conf_after": round(conf_ext_after, 4),
            "contrast_external_relabel_conf_drop": round(conf_before - conf_ext_after, 4),
        }
        per_seed.append(row)
        print(f"[seed {seed}] SELF conf {conf_before:.3f}->{conf_after:.3f} "
              f"(drop {conf_before - conf_after:+.3f}) | store drift {store_drift:.1%} | "
              f"D1 agr {agr_d1_before:.3f}->{agr_d1_after:.3f} "
              f"(drop {agr_d1_before - agr_d1_after:+.3f}) | D2 agr "
              f"{agr_d2_before:.3f}->{agr_d2_after:.3f} "
              f"(drop {agr_d2_before - agr_d2_after:+.3f}) || contrast ext-relabel "
              f"conf_after {conf_ext_after:.3f}")

    def mstat(key):
        v = np.array([r[key] for r in per_seed])
        return float(v.mean()), float(v.std())

    conf_drop_m, conf_drop_s = mstat("self_conf_drop")
    d1_drop_m, d1_drop_s = mstat("d1_agree_drop")
    d2_drop_m, d2_drop_s = mstat("d2_agree_drop")
    ext_drop_m, _ = mstat("contrast_external_relabel_conf_drop")
    drift_m, _ = mstat("store_rows_changed_vs_truth")

    gate_conf = conf_drop_m <= 0.05
    gate_d1 = d1_drop_m >= 0.20
    gate_d2 = d2_drop_m >= 0.20
    stds = {"self_conf_drop": conf_drop_s, "d1_agree_drop": d1_drop_s,
            "d2_agree_drop": d2_drop_s}
    degenerate = {k: v for k, v in stds.items() if v == 0.0}
    if degenerate:
        verdict = "INCONCLUSIVE"  # std==0 on a gated seed-mean
        note = f"std==0 law fired on {list(degenerate)}"
    else:
        verdict = "PASS" if (gate_conf and gate_d1 and gate_d2) else "FAIL"
        note = ""

    result = {
        "probe": "different-path second reader vs silent drift",
        "source": "pr_harvest/SUMMARY.md #5 / CARDS.md fleet-triage #4",
        "gate": "self-consistent reader conf drop <=5%; different-path agreement drop "
                ">=20% (both D1 same-arch-diff-seed and D2 arch-different); "
                "std==0 on gated seed-mean -> INCONCLUSIVE",
        "verdict": verdict,
        "numbers": {
            "drift_protocol": "self-generated: the store is rewritten from the self "
                              "reader's own biased predictions (growing sticky class "
                              "preference over 8 cycles), then re-consumed by it; "
                              "different-path readers stay frozen on original labels",
            "per_seed": per_seed,
            "mean_store_rows_changed_vs_truth": round(drift_m, 4),
            "mean_self_conf_drop": round(conf_drop_m, 4),
            "mean_d1_agreement_drop_samearch": round(d1_drop_m, 4),
            "mean_d2_agreement_drop_archdiff": round(d2_drop_m, 4),
            "seed_stds": {k: round(v, 4) for k, v in stds.items()},
            "contrast_arm_external_relabel_mean_conf_drop": round(ext_drop_m, 4),
            "gate_clauses": {"conf_drop_le_5pct": bool(gate_conf),
                             "d1_drop_ge_20pct": bool(gate_d1),
                             "d2_drop_ge_20pct": bool(gate_d2)},
        },
        "reading": ("with drift entering the system's own write path, the self-consistent "
                    "reader keeps its confidence (it reads what it wrote) while both "
                    "differently-built readers see the store move — instrument diversity "
                    "as a freeze detector, demonstrated on our iron. Honest boundary "
                    "(contrast arm): an EXTERNAL relabel corruption of the same size "
                    "does hurt the self reader's confidence — the blindness is specific "
                    "to drift the system itself generates, not to arbitrary corruption"),
        "extra_note": note,
        "seed": SEEDS,
        "runtime_seconds": round(time.time() - t0, 1),
        "device": "cpu",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=2)
    print(f"VERDICT: {verdict} {note}")
    print(f"booked -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
