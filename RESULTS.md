# RESULTS — the honest ledger

## E1 — real-glyph-contrast (2026-09-27 12:20 AKDT)
- ran: by hand during harness bring-up (runner wired immediately after)
- verdict: **KEEP**
- result: ```json
{
  "experiment": "E1 real-glyph-contrast",
  "device": "cuda",
  "seed": 2718,
  "rooms": ["still-solid", "moving-testsrc"],
  "n_train": 20,
  "n_heldout": 8,
  "heldout_margin_untrained": 0.0052,
  "heldout_margin_trained": 1.2886,
  "heldout_gap": 1.2833,
  "within_trained": 0.9942,
  "cross_trained": -0.2944
}
```
- note: elephant's RoomEncoder (~150k params) trained 60 epochs on real
  ffmpeg-decoded frames, CUDA, seconds of wall-clock. Held-out
  separation gap +1.283 (vs +0.005 untrained). The synthetic-lab result
  survives real pixels. Failures en route (booked): lavfi filter-string
  concatenation bug, loss-tuple unpack, float32 JSON serialization —
  all caught and fixed same-session.

## E2 — flow-beat-vs-pool (2026-09-27 12:25 AKDT)
- ran: by hand during harness bring-up
- verdict: **INCONCLUSIVE** (lean KILL for the naive form)
- result: ```json
{
  "experiment": "E2 flow-beat-vs-pool",
  "seed": 2718,
  "frames": 240,
  "clips": ["still-solid", "moving-testsrc", "smpte", "testsrc2"],
  "pairs": 39848,
  "glyph_vs_macropool": {"pearson": 0.966, "spearman": 0.883},
  "glyph_vs_flowbeat": {"pearson": 0.11, "spearman": 0.343},
  "repr_change_vs_macro_delta": {"flowbeat": 0.608, "static_lum": 0.989},
  "lab_baseline": {"pearson": 0.824, "spearman": 0.891, "repr_change": 0.966, "static": 0.187}
}
```
- note (read this before trusting the L0 design): on REAL frames the
  flow+beat token map LOST badly to plain mean-pooling — ρ 0.343 vs
  0.883, and static luminance tracked macro temporal delta at 0.989
  while flow+beat change managed only 0.608. On synthetic lab frames
  the same design was decisive (0.966 vs 0.187). Diagnosis, to test
  before re-KEEPing: (1) three of four real clips differ overwhelmingly
  in STATIC content (SMPTE bars, flat gray), so distance structure is
  dominated by luminance and the flow channel is ~zero on still clips —
  the pair-mix, not the idea, may be the problem; (2) the lab's
  headline was repr-CHANGE vs macro-delta per clip, not pairwise
  across clips; E2's cross-clip pairing conflates the two. Next
  revision (E2b): per-clip temporal-delta correlation only + a
  within-texture clip pair (two moving sources). The naive
  cross-clip form: KILL. The design: unproven, not dead.

## E3 — cast-heldout control
- ran: 2026-09-27 12:51
- verdict: KEEP
- result: ```json
{
  "experiment": "E3 cast-heldout control",
  "checks": {
    "stability_still-solid": {
      "d_mu": 0.0,
      "real": false
    },
    "stability_moving-testsrc": {
      "d_mu": 0.044,
      "real": false
    },
    "separation_still->moving": {
      "d_mu": 0.664,
      "real": true
    },
    "separation_moving->still": {
      "d_mu": 0.664,
      "real": true
    }
  },
  "kl_sym_heldout": 217.4,
  "verdict": "KEEP",
  "note": "fit on train-half windows (step-4 stride, 30 windows/clip), evaluate on heldout half. Stability: same-room gates not real (0.0 / 0.044). Separation: cross-room real both directions, d_mu 0.664 vs seed all-windows 0.628. Curiosity: moving-testsrc heldout kappa saturated to 500 (train 257.2) \u2014 the held-out half of testsrc (later seconds, larger gradient) reads 'quieter' geometry; booked, not alarmed. vmf_fit honestly returned None below NMIN on the first attempt \u2014 the honesty rule bit before the fix."
}
```

## E2b — flow-beat-revision
- ran: 2026-09-27 12:52
- verdict: KILL
- result: ```json
{
  "experiment": "E2b flow-beat-revision",
  "per_clip": {
    "still-solid": "NaN (constant clip \u2014 zero-variance delta, honestly undefined)",
    "moving-testsrc": {
      "flowbeat": 0.508,
      "static_lum": 0.898
    },
    "smpte": "NaN (constant clip)",
    "moving-testsrc2": {
      "flowbeat": 0.619,
      "static_lum": 0.707
    }
  },
  "flowbeat_wins": 0,
  "within_texture_testsrc_testsrc2": {
    "glyph_vs_macropool_spearman": 0.642,
    "glyph_vs_flowbeat_spearman": -0.349
  },
  "verdict": "KILL"
}
```
- note (the booked lesson): the hand-crafted flow+beat L0 does NOT transfer to real frames. Per-clip temporal correlation: static luminance BEATS flow+beat on both moving clips (0.898 vs 0.508; 0.707 vs 0.619); within-texture distance structure went NEGATIVE (-0.349). On constant clips the correlation is honestly NaN (zero-variance deltas). The lab's synthetic recommendation was an artifact of the synthetic rooms' construction. Implication for tessera: L0 must be LEARNED (E1's contrastive head is the standing candidate), not hand-designed from frame differencing. The pyramid-contract floor on real frames is mean-pool + luminance dynamics until a learned repr beats it.

## E4 — next-room transformer
- ran: 2026-09-27 12:54
- verdict: INCONCLUSIVE (threshold said KEEP; review downgraded)
- result: ```json
{
  "experiment": "E4 next-room transformer",
  "params": 68228,
  "device": "cuda",
  "seed": 2718,
  "rooms": [
    "still-solid",
    "moving-testsrc",
    "smpte",
    "moving-testsrc2"
  ],
  "cells": 24,
  "train_windows": 12,
  "heldout_windows": 4,
  "heldout_acc": 0.75,
  "majority_baseline": 0.0,
  "verdict": "INCONCLUSIVE (reported KEEP by threshold, downgraded on review)"
}
```
- note (why downgraded): 24 cells is too thin — 4 heldout windows cannot separate signal from 'predict the last room always'. The 0.0 majority baseline is degenerate: the temporal split puts only testsrc2 in heldout, so a constant-predictor scores 0.75 without reading trajectory at all. The 68k-param model trains and runs in seconds on CUDA — the harness works; the DATASET doesn't. E4b revision: longer clips (60s) for ~240 cells, interleaved walk (room transitions spread through the data), blocked split by cell-block not tail, plus a constant-predictor and markov-1 baseline reported alongside. The JEV-temporal question stays open until then.
