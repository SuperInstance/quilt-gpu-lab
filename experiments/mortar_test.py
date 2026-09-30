#!/usr/bin/env python3
"""MORTAR TEST — do tone trajectories self-attribute by shape alone?
Frozen per proposals/runs/MORTAR-2026-09-29.md. CPU-only, deterministic (seed 20260929).
Premise under test (INTERLEAVED): four stories' tone shapes, mixed on one tape with no
speaker tags, attributable by trajectory-shape features alone.
GATES (frozen): LOOCV acc >= 0.90 -> MORTAR_REAL | <= 0.35 -> PROJECTION | else WEAK_UNRESOLVED
VALIDITY CONTROL: time-shuffled-segment features must score <= 0.35, else INVALID_HARNESS.
"""
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
OUT = os.path.join(LAB, "results", "mortar_test.json")
SEED = 20260929
T = 40          # steps per utterance trajectory
N_PER = 16      # utterances per story (64 segments on the tape)
SIGMA = 0.05    # observation noise
rng = np.random.default_rng(SEED)

def log(m): print("[mortar %s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)

def shape_beckon(t):      # climb, climb, hold taut at the crest
    x = np.clip(t / 0.55, 0, 1) ** 0.8
    return 0.15 + 0.6 * x

def shape_farewell(t):    # falls level early, one clean drop near the end
    x = np.where(t < 0.78, 0.55 - 0.08 * t, 0.55 - 0.08 * 0.78 - 1.9 * (t - 0.78))
    return np.clip(x, 0.02, 1.0)

def shape_hostage(t):     # spikes and locks flat
    spike = 0.85 * np.exp(-((t - 0.10) / 0.05) ** 2)
    return np.clip(0.20 + spike, 0, 1)

def shape_refrain(t):     # climbs past its ceiling then folds over
    rise = 0.15 + 0.95 * np.clip(t / 0.45, 0, 1) ** 0.7
    fold = np.where(t > 0.45, 1.10 - 1.6 * (t - 0.45), rise)
    return np.clip(fold, 0.02, 1.10)

SHAPES = {"beckon": shape_beckon, "farewell": shape_farewell,
          "hostage": shape_hostage, "refrain": shape_refrain}
STORIES = list(SHAPES)

def gen_trajectory(story, k):
    """One utterance: canonical shape + per-utterance bounded jitter + noise."""
    t = np.linspace(0, 1, T)
    base = SHAPES[story](t)
    amp = 1.0 + 0.12 * np.sin(k * 2.399 + STORIES.index(story))   # bounded jitter, deterministic
    shift = 0.05 * np.cos(k * 1.7 + STORIES.index(story) * 2.0)
    return np.clip(base * amp + shift + rng.normal(0, SIGMA, T), 0.0, 1.2)

def features(traj):
    """Shape features only — no amplitude identity, no absolute level normalization leak."""
    z = (traj - traj.mean()) / (traj.std() + 1e-9)   # level/scale-free: the LEAN, not the level
    q = np.array_split(z, 4)
    slopes = [float(s.mean()) for s in q]
    peak = float(np.argmax(traj)) / T
    post_peak = float(np.mean(np.diff(z[int(np.argmax(traj)):]))) if peak < 0.95 else 0.0
    drops = float(np.sum(np.abs(np.diff(z)) > 1.5))
    ar1 = float(np.corrcoef(z[:-1], z[1:])[0, 1])
    plateau = float(np.max([len(r) for r in [np.flatnonzero(np.abs(np.diff(z[int(T*0.5):]))) < 0.2] if len(r) else [0]])) / T
    return slopes + [peak, post_peak, drops, ar1, plateau]

def loocv_centroid(X, y):
    correct = 0
    for i in range(len(y)):
        keep = [j for j in range(len(y)) if j != i]
        cents = {}
        for c in sorted(set(y)):
            m = [j for j in keep if y[j] == c]
            cents[c] = np.mean([X[j] for j in m], axis=0)
        d = {c: float(np.linalg.norm(X[i] - v)) for c, v in cents.items()}
        pred = min(d, key=d.get)
        correct += int(pred == y[i])
    return correct / len(y)

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    segs, labels = [], []
    for s in STORIES:
        for k in range(N_PER):
            segs.append(gen_trajectory(s, k)); labels.append(s)
    X = np.array([features(t) for t in segs]); y = np.array(labels)
    tape = rng.permutation(len(y))                      # mix onto one tape (no seam markers)
    X, y = X[tape], y[tape]
    acc = loocv_centroid(X, y)
    # validity control: destroy shape, keep marginals
    Xc = np.array([features(rng.permutation(t)) for t in segs])[tape]
    acc_ctrl = loocv_centroid(Xc, y)
    verdict = ("INVALID_HARNESS" if acc_ctrl > 0.35 else
               "MORTAR_REAL" if acc >= 0.90 else
               "PROJECTION" if acc <= 0.35 else "WEAK_UNRESOLVED")
    out = {"verdict": verdict, "loocv_acc": round(acc, 4), "chance": 0.25,
           "control_acc": round(acc_ctrl, 4), "control_gate": 0.35,
           "n_segments": len(y), "n_stories": len(STORIES), "T": T, "seed": SEED,
           "features": "level-free shape features (quartile slopes, peak pos, post-peak, drops, ar1, plateau)"}
    json.dump(out, open(OUT, "w"), indent=1)
    log("acc=%.4f control=%.4f -> %s" % (acc, acc_ctrl, verdict))

if __name__ == "__main__":
    main()
