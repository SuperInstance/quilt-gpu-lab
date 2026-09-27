"""E2b — flow-beat-revision: per-clip temporal correlation, within-texture pairs.

E2's cross-clip pairing conflated static-content distance (SMPTE vs gray
dominates pairwise d_glyph) with the temperature axis. The lab's actual
headline was repr-CHANGE vs macro-DELTA. This revision:

  1. per-clip: corr( L0 repr-change, macro temporal-delta ) within each
     clip alone — 4 clips, 4 independent numbers
  2. within-texture pairs: distance-structure correlation restricted to
     moving pairs (testsrc <-> testsrc2) where static content does not
     dominate

Pass: flow+beat per-clip correlations >= static-luminance correlations
in most clips, or within-texture rho meaningfully recovers toward the
lab's synthetic numbers.
"""
from __future__ import annotations

import json
import sys

import numpy as np

sys.path.insert(0, "/home/eileen/projects/quilt-gpu-lab/experiments")
from common import ppms_from_lavfi, to_glyph  # noqa: E402

SEED = 2718
SOURCES = [("still-solid", "color=c=gray:duration=6:size=160x90:rate=10"),
           ("moving-testsrc", "testsrc=duration=6:size=160x90:rate=10"),
           ("smpte", "smptebars=duration=6:size=160x90:rate=10"),
           ("moving-testsrc2", "testsrc2=duration=6:size=160x90:rate=10")]


def macro_pool(frames, gh=4, gw=4):
    T, H, W = frames.shape
    return frames.reshape(T, gh, H // gh, gw, W // gw).mean(axis=(2, 4))


def flow_beat_tokens(frames, gh=12, gw=40):
    T, H, W = frames.shape
    lum = frames.astype(np.float32) / 9.0
    flow = np.abs(np.diff(lum, axis=0))
    beat = np.stack([flow[max(0, i - 3):i + 1].mean(0) for i in range(len(flow))])
    def pool(x):
        return x.reshape(len(x), gh, H // gh, gw, W // gw).mean(axis=(2, 4))
    return np.concatenate([pool(flow), pool(beat)], axis=1)


def main() -> dict:
    per_clip = {}
    glyphs = {}
    for name, src in SOURCES:
        frames = to_glyph(ppms_from_lavfi(src, 6, 10, (160, 90)))
        glyphs[name] = frames
        macro = macro_pool(frames)
        tokens = flow_beat_tokens(frames)
        tt = np.arange(1, len(tokens))
        ch_l0 = np.abs(tokens[tt - 1] - tokens[tt]).mean(axis=(1, 2))
        ch_md = np.abs(macro[tt] - macro[tt - 1]).mean(axis=(1, 2))
        ch_lum = np.abs(frames[tt].astype(np.float32) - frames[tt - 1]).mean(axis=(1, 2))
        c_l0 = float(np.corrcoef(ch_l0, ch_md)[0, 1])
        c_lum = float(np.corrcoef(ch_lum, ch_md)[0, 1])
        per_clip[name] = {"flowbeat_vs_macro_delta": round(c_l0, 3),
                          "staticlum_vs_macro_delta": round(c_lum, 3)}
        print(f"[e2b] {name}: flowbeat {c_l0:.3f} vs static {c_lum:.3f}")

    # within-texture pair: testsrc <-> testsrc2 (both moving)
    rng = np.random.default_rng(SEED)
    A, B = glyphs["moving-testsrc"], glyphs["moving-testsrc2"]
    T = min(len(A), len(B))
    i = rng.integers(0, T, 20000)
    j = rng.integers(0, T, 20000)
    keep = np.abs(i - j) > 0
    i, j = i[keep], j[keep]
    d_glyph = np.abs(A[i].astype(np.float32) - B[j]).mean(axis=(1, 2))
    mA, mB = macro_pool(A), macro_pool(B)
    d_macro = np.abs(mA[i] - mB[j]).mean(axis=(1, 2))
    tA, tB = flow_beat_tokens(A), flow_beat_tokens(B)
    ti, tj = np.clip(i - 1, 0, len(tA) - 1), np.clip(j - 1, 0, len(tB) - 1)
    d_l0 = np.abs(tA[ti] - tB[tj]).mean(axis=(1, 2))
    def sp(a, b):
        ra = np.argsort(np.argsort(a)).astype(np.float64)
        rb = np.argsort(np.argsort(b)).astype(np.float64)
        return float(np.corrcoef(ra, rb)[0, 1])
    rho_macro, rho_l0 = sp(d_glyph, d_macro), sp(d_glyph, d_l0)

    wins = sum(1 for v in per_clip.values()
               if v["flowbeat_vs_macro_delta"] >= v["staticlum_vs_macro_delta"])
    verdict = "KEEP" if (wins >= 3 or rho_l0 > rho_macro) else "KILL"
    out = {
        "experiment": "E2b flow-beat-revision", "seed": SEED,
        "per_clip": per_clip, "flowbeat_wins": wins,
        "within_texture_testsrc_testsrc2": {
            "glyph_vs_macropool_spearman": round(rho_macro, 3),
            "glyph_vs_flowbeat_spearman": round(rho_l0, 3)},
        "verdict": verdict,
    }
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
