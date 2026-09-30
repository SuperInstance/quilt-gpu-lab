#!/usr/bin/env python3
"""MORTAR-2 — DECOMPOSITION: how much of a tone trajectory's identity is ORDER vs AMPLITUDE?
Successor to mortar_test.py (which returned INVALID_HARNESS: order-shuffle null scored 0.469 > 0.35,
because amplitude/step statistics alone separate the shapes). This run isolates the two carriers.
Frozen per proposals/runs/MORTAR-2-2026-09-29.md. CPU, deterministic seed 20260929.
GATES (frozen):
  HARNESS: label-shuffle null on ALL features <= 0.35  (else INVALID_HARNESS)
  ORDER_CARRIES_LEANING: order-only acc >= 0.90 AND order-shuffle null on order-only features <= 0.35
  MARGINAL_DOMINANT: order-only acc < 0.90 while marginal-only acc >= 0.90
  WEAK: neither
"""
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
OUT = os.path.join(LAB, "results", "mortar2_decompose.json")
SEED = 20260929
T, N_PER, SIGMA = 40, 16, 0.05
rng = np.random.default_rng(SEED)

def log(m): print("[mortar2 %s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)

def shape_beckon(t):
    return 0.15 + 0.6 * np.clip(t / 0.55, 0, 1) ** 0.8
def shape_farewell(t):
    x = np.where(t < 0.78, 0.55 - 0.08 * t, 0.55 - 0.08 * 0.78 - 1.9 * (t - 0.78))
    return np.clip(x, 0.02, 1.0)
def shape_hostage(t):
    return np.clip(0.20 + 0.85 * np.exp(-((t - 0.10) / 0.05) ** 2), 0, 1)
def shape_refrain(t):
    rise = 0.15 + 0.95 * np.clip(t / 0.45, 0, 1) ** 0.7
    return np.clip(np.where(t > 0.45, 1.10 - 1.6 * (t - 0.45), rise), 0.02, 1.10)

SHAPES = {"beckon": shape_beckon, "farewell": shape_farewell,
          "hostage": shape_hostage, "refrain": shape_refrain}
STORIES = list(SHAPES)

def gen(story, k):
    t = np.linspace(0, 1, T)
    base = SHAPES[story](t)
    amp = 1.0 + 0.12 * np.sin(k * 2.399 + STORIES.index(story))
    shift = 0.05 * np.cos(k * 1.7 + STORIES.index(story) * 2.0)
    return np.clip(base * amp + shift + rng.normal(0, SIGMA, T), 0.0, 1.2)

def order_features(traj):
    """Temporal-order carriers ONLY: shape of the curve, level/scale free."""
    z = (traj - traj.mean()) / (traj.std() + 1e-9)
    q = np.array_split(z, 4)
    slopes = [float(s.mean()) for s in q]
    peak = float(np.argmax(traj)) / T
    post = float(np.mean(np.diff(z[int(np.argmax(traj)):]))) if peak < 0.95 else 0.0
    ar1 = float(np.corrcoef(z[:-1], z[1:])[0, 1])
    return slopes + [peak, post, ar1]

def amplitude_features(traj):
    """Distribution carriers ONLY: order-free statistics."""
    d = np.diff(traj)
    return [float(traj.std()), float(traj.min()), float(traj.max()),
            float(np.mean(np.abs(d))), float(np.max(np.abs(d))),
            float(np.sum(np.abs(d) > 0.5)), float(np.median(np.abs(d)))]

def loocv_centroid(X, y):
    ok = 0
    for i in range(len(y)):
        keep = [j for j in range(len(y)) if j != i]
        cents = {}
        for c in sorted(set(y)):
            m = [j for j in keep if y[j] == c]
            cents[c] = np.mean([X[j] for j in m], axis=0)
        d = {c: float(np.linalg.norm(X[i] - v)) for c, v in cents.items()}
        ok += int(min(d, key=d.get) == y[i])
    return ok / len(y)

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    segs, labs = [], []
    for s in STORIES:
        for k in range(N_PER):
            segs.append(gen(s, k)); labs.append(s)
    y = np.array(labs)
    tape = rng.permutation(len(y)); y = y[tape]; segs = [segs[i] for i in tape]

    Xo = np.array([order_features(t) for t in segs])
    Xa = np.array([amplitude_features(t) for t in segs])
    Xall = np.hstack([Xo, Xa])

    acc_all = loocv_centroid(Xall, y)
    acc_ord = loocv_centroid(Xo, y)
    acc_amp = loocv_centroid(Xa, y)

    # null 1: order-shuffle (destroys order, keeps marginals) -> on order features
    null_ord = loocv_centroid(np.array([order_features(rng.permutation(t)) for t in segs]), y)
    # null 2: label-shuffle (harness validity) -> on all features
    y_perm = rng.permutation(y)
    null_lab = loocv_centroid(Xall, y_perm)

    if null_lab > 0.35:
        verdict = "INVALID_HARNESS"
    elif acc_ord >= 0.90 and null_ord <= 0.35:
        verdict = "ORDER_CARRIES_LEANING"
    elif acc_ord < 0.90 and acc_amp >= 0.90:
        verdict = "MARGINAL_DOMINANT"
    else:
        verdict = "WEAK_UNRESOLVED"

    out = {"verdict": verdict, "acc_all": round(acc_all, 4), "acc_order_only": round(acc_ord, 4),
           "acc_amplitude_only": round(acc_amp, 4), "null_order_shuffle": round(null_ord, 4),
           "null_label_shuffle": round(null_lab, 4), "chance": 0.25,
           "gates": {"harness_null_max": 0.35, "order_acc_min": 0.90, "order_null_max": 0.35},
           "n_segments": len(y), "seed": SEED,
           "note": "mortar-1 returned INVALID_HARNESS (order-shuffle null 0.469) → this run decomposes order vs amplitude carriers."}
    json.dump(out, open(OUT, "w"), indent=1)
    log("all=%.4f order=%.4f ampl=%.4f | nulls: order-shuf=%.4f label-shuf=%.4f -> %s"
        % (acc_all, acc_ord, acc_amp, null_ord, null_lab, verdict))

if __name__ == "__main__":
    main()
