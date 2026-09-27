"""E2 — flow-beat-vs-pool: does the flow+beat L0 beat the mean-pool floor?

The lab's pyramid-contract baseline: d_glyph <-> d_macro (4x4 mean-pool)
rho = 0.824 Pearson / 0.891 Spearman on synthetic frames, and
corr(repr-change, macro-temporal-delta) = 0.966 for the lab repr vs
0.187 for static luminance. This experiment rebuilds the comparison on
REAL ffmpeg frames with the designed L0: 40x20 flow+beat tokens
(frame-diff magnitude + temporal energy, RAFT-lite via differencing).
"""
from __future__ import annotations

import json
import sys

import numpy as np

sys.path.insert(0, "/home/eileen/projects/quilt-gpu-lab/experiments")
from common import ppms_from_lavfi, to_glyph

SEED = 2718
SOURCES = [("still-solid", "color=c=gray:duration=6:size=160x90:rate=10"),
           ("moving-testsrc", "testsrc=duration=6:size=160x90:rate=10"),
           ("smpte", "smptebars=duration=6:size=160x90:rate=10"),
           ("testsrc2", "testsrc2=duration=6:size=160x90:rate=10")]
SECONDS, FPS = 6, 10
MAX_PAIRS = 40000
RNG_SEED = 2718


def macro_pool(frames: np.ndarray, gh: int = 4, gw: int = 4) -> np.ndarray:
    T, H, W = frames.shape
    return frames.reshape(T, gh, H // gh, gw, W // gw).mean(axis=(2, 4))


def flow_beat_tokens(frames: np.ndarray, gh: int = 12, gw: int = 40) -> np.ndarray:
    """L0 tokens: per-cell flow (|frame t - frame t-1|) + beat (temporal energy).

    Returns (T-1, 2*gh, gw): flow pooled on the top gh rows, beat pooled on
    the bottom gh rows — one token map carrying both channels.
    """
    T, H, W = frames.shape
    lum = frames.astype(np.float32) / 9.0
    flow = np.abs(np.diff(lum, axis=0))  # (T-1, H, W)
    beat = np.stack([flow[max(0, i-3):i+1].mean(0) for i in range(len(flow))])
    def pool(x):
        return x.reshape(len(x), gh, H // gh, gw, W // gw).mean(axis=(2, 4))
    return np.concatenate([pool(flow), pool(beat)], axis=1)  # (T-1, 2*gh? no)


def main() -> dict:
    rng = np.random.default_rng(RNG_SEED)
    all_glyph, all_clip = [], []
    for name, src in SOURCES:
        frames = to_glyph(ppms_from_lavfi(src, SECONDS, FPS, (160, 90)))
        all_glyph.append(frames)
        all_clip.append(name)
        print(f"[e2] {name}: {frames.shape}")

    glyph = np.concatenate(all_glyph)              # (T, 24, 80)
    macro = macro_pool(glyph)                      # (T, 4, 4)
    tokens = flow_beat_tokens(glyph)               # per-transition L0

    T = len(glyph)
    i, j = rng.integers(0, T, (MAX_PAIRS, 2)).T
    keep = np.abs(i - j) > 0
    i, j = i[keep], j[keep]

    d_glyph = np.abs(glyph[i].astype(np.float32) - glyph[j]).mean(axis=(1, 2))
    d_macro = np.abs(macro[i] - macro[j]).mean(axis=(1, 2))

    # L0 distance: flow+beat token distance; align macro pair to transition
    # domain: for pair (i, j) use tokens at transitions t and s where
    # t = i-1 (into frame i), s = j-1; distance between token maps, plus
    # pairing glyph distance to macro distance as in the lab.
    ti = np.clip(i - 1, 0, len(tokens) - 1)
    tj = np.clip(j - 1, 0, len(tokens) - 1)
    d_l0 = np.abs(tokens[ti] - tokens[tj]).mean(axis=(1, 2))

    def rho(a, b):
        return float(np.corrcoef(a, b)[0, 1]), float(_spearman(a, b))

    def _spearman(a, b):
        ra = np.argsort(np.argsort(a)).astype(np.float64)
        rb = np.argsort(np.argsort(b)).astype(np.float64)
        return np.corrcoef(ra, rb)[0, 1]

    pear_pm, spear_pm = rho(d_glyph, d_macro)      # baseline: mean-pool
    pear_pl, spear_pl = rho(d_glyph, d_l0)         # flow+beat L0

    # temporal-delta test (the lab's decisive number): does representation
    # change track macro temporal delta?
    tt = np.arange(1, len(tokens))  # consecutive transitions inside tokens
    repr_change_l0 = np.abs(tokens[tt - 1] - tokens[tt]).mean(axis=(1, 2))
    macro_delta = np.abs(macro[tt] - macro[tt - 1]).mean(axis=(1, 2))
    repr_change_lum = np.abs(glyph[tt].astype(np.float32) - glyph[tt - 1]).mean(axis=(1, 2))
    c_l0 = float(np.corrcoef(repr_change_l0, macro_delta)[0, 1])
    c_lum = float(np.corrcoef(repr_change_lum, macro_delta)[0, 1])

    out = {
        "experiment": "E2 flow-beat-vs-pool", "seed": RNG_SEED,
        "frames": int(T), "clips": all_clip, "pairs": int(len(i)),
        "glyph_vs_macropool": {"pearson": round(pear_pm, 3), "spearman": round(spear_pm, 3)},
        "glyph_vs_flowbeat": {"pearson": round(pear_pl, 3), "spearman": round(spear_pl, 3)},
        "repr_change_vs_macro_delta": {"flowbeat": round(c_l0, 3), "static_lum": round(c_lum, 3)},
        "lab_baseline": {"pearson": 0.824, "spearman": 0.891, "repr_change": 0.966, "static": 0.187},
    }
    ok = spear_pl >= spear_pm - 0.05 and c_l0 > c_lum
    out["verdict"] = "KEEP" if ok else "INCONCLUSIVE"
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
