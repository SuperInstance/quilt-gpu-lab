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

## E7 — vjepa2-in-cells — V-JEPA 2 ViT-L (Meta, downloaded) embeddings through the same cell contract; judged on separation, drift-gate, and surprise vs local heads
- ran: 2026-09-27 14:05
- verdict: ABORTED
- result: ```json
{
  "experiment": "E7",
  "guard": {
    "samples": 2,
    "min_free_vram_mib": 5920,
    "max_temp_c": 47,
    "breach": null,
    "timed_out": false
  },
  "verdict": "ABORTED",
  "reason": "exit 1",
  "stderr": "Traceback (most recent call last):\n  File \"<frozen runpy>\", line 198, in _run_module_as_main\n  File \"<frozen runpy>\", line 88, in _run_code\n  File \"/home/eileen/projects/quilt-gpu-lab/experiments/e7_vjepa2_in_cells.py\", line 107, in <module>\n    main()\n    ~~~~^^\n  File \"/home/eileen/projects/quilt-gpu-lab/experiments/e7_vjepa2_in_cells.py\", line 42, in main\n    processor = VJEPA2VideoProcessor.from_pretrained(MODEL_ID)\n                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/home/eileen/venvs/elephant-gpu/lib/python3.14/site-packages/transformers/utils/import_utils.py\", line 2388, in __getattribute__\n    requires_backends(cls, cls._backends)\n    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^\n  File \"/home/eileen/venvs/elephant-gpu/lib/python3.14/site-packages/transformers/utils/import_utils.py\", line 2374, in requires_backends\n    raise ImportError(\"\".join(failed))\nImportError: \nVJEPA2VideoProcessor requires the PIL library but it was not found in your environment. You can install it with pip:\n`pip install pillow`. Please note that you may need to restart your runtime after installation.\n\nVJEPA2VideoProcessor requires the Torchvision library but it was not found in your environment. Check out the instructions on the\ninstallation page: https://pytorch.org/get-started/locally/ and follow the ones that match your environment.\nPlease note that you may need to restart your runtime after installation.\n\n"
}
```

## E7 — vjepa2-in-cells (retry after pillow+torchvision install) — V-JEPA 2 ViT-L (Meta, downloaded) embeddings through the same cell contract; judged on separation, drift-gate, and surprise vs local heads — 2026-09-27 ABORTED
- ran: 2026-09-27 14:11
- verdict: KEEP
- result: ```json
{
  "experiment": "E7 vjepa2-in-cells",
  "device": "cuda",
  "seed": 2718,
  "model": "facebook/vjepa2-vitl-fpc16-256-ssv2",
  "rooms": [
    "still-solid",
    "moving-testsrc",
    "smpte",
    "moving-testsrc2"
  ],
  "cells": 24,
  "emb_dim": 1024,
  "still_vs_testsrc_cross_cos": 0.5442,
  "within_still": 1.0,
  "within_testsrc": 0.9898,
  "heldout_gap": 0.4456,
  "tex_vs_motion_axis_corr": 0.2799,
  "verdict": "KEEP",
  "guard_summary": {
    "samples": 3,
    "min_free_vram_mib": 5056,
    "max_temp_c": 59,
    "breach": null,
    "timed_out": false
  }
}
```

## D7 — quant-drift (portability probe)
- ran: 2026-09-27 15:02
- verdict: **KEEP**
- result: ```json
{
  "experiment": "D7 quant-drift",
  "device": "cuda",
  "seed": 2718,
  "model": "BAAI/bge-small-en-v1.5",
  "max_seq_length": 64,
  "probe": {
    "n_unique_sentences": 254,
    "n_cal_pairs": 60,
    "n_probe_pairs": 240,
    "balanced_labels": true
  },
  "calibration": {
    "threshold_tau": 0.7184,
    "fp16_mean_same_cos": 0.9226,
    "fp16_mean_diff_cos": 0.5142,
    "separation": 0.4084,
    "protocol": "tau from fp16 cal split only, frozen for all precisions"
  },
  "flip_ceiling": 0.05,
  "precisions": {
    "fp32": {
      "bits": 32,
      "mean_cos_drift": 1.0001354217529297,
      "min_cos_drift": 0.9995529651641846,
      "mean_pair_sim_absdelta": 0.00020337113528512418,
      "probe_flips": 0,
      "flip_rate": 0.0
    },
    "fp16": {
      "bits": 16,
      "mean_cos_drift": 1.0002720355987549,
      "min_cos_drift": 0.9991075992584229,
      "mean_pair_sim_absdelta": 0.0,
      "probe_flips": 0,
      "flip_rate": 0.0
    },
    "int8": {
      "bits": 8,
      "mean_cos_drift": 0.9998080730438232,
      "min_cos_drift": 0.9989901781082153,
      "mean_pair_sim_absdelta": 0.0024867805186659098,
      "probe_flips": 0,
      "flip_rate": 0.0
    },
    "nf4": {
      "bits": 4,
      "mean_cos_drift": 0.9840461015701294,
      "min_cos_drift": 0.9783671498298645,
      "mean_pair_sim_absdelta": 0.01710696332156658,
      "probe_flips": 0,
      "flip_rate": 0.0
    }
  },
  "smallest_viable_precision": "nf4",
  "verdict": "KEEP",
  "reason": "nf4 holds probe flip-rate 0.0000 < ceiling 0.05",
  "loads": {
    "fp32": {
      "seconds": 7.97,
      "dim": 384
    },
    "fp16": {
      "seconds": 6.92,
      "dim": 384
    },
    "int8": {
      "seconds": 6.26,
      "dim": 384
    },
    "nf4": {
      "seconds": 6.1,
      "dim": 384
    }
  },
  "versions": {
    "torch": "2.14.0+cu126",
    "transformers": "5.17.0",
    "sentence_transformers": "6.1.0",
    "bitsandbytes": "0.50.2"
  }
}
```
- drift/flip table (probe pairs=240, tau=0.7184, ceiling=0.05):

| precision | bits | mean cos drift vs fp16 | mean pair-sim abs-delta | probe flips | flip rate |
|---|---|---|---|---|---|
| fp32 | 32 | 1.0001 | 0.0002 | 0/240 | 0.0000 |
| fp16 | 16 | 1.0003 | 0.0000 | 0/240 | 0.0000 |
| int8 | 8 | 0.9998 | 0.0025 | 0/240 | 0.0000 |
| nf4 | 4 | 0.9840 | 0.0171 | 0/240 | 0.0000 |

- note: nf4 holds probe flip-rate 0.0000 < ceiling 0.05. fp32-vs-fp16 rows price the reference's own noise floor (no int8/NF4 treatment). E5 line closes into D7 (cross-link: GPU-DOCKET D7 'cross-link the closed E5 line').

## D2 — qthe ternary matmul kernel
- ran: 2026-09-27 15:09
- verdict: KEEP
- result: ```json
{
  "experiment": "D2 qthe ternary kernel",
  "parity": "PASS", "vs_node_ref": true, "vs_py_ref": true,
  "benchmark": [
    {"size": 1024, "fp16_ms": 0.0273, "ternary_ms": 0.015, "speedup": 1.824},
    {"size": 2048, "fp16_ms": 0.1109, "ternary_ms": 0.0311, "speedup": 3.567},
    {"size": 4096, "fp16_ms": 0.3743, "ternary_ms": 0.456, "speedup": 0.821}
  ],
  "prereg_margin": 1.10, "verdict": "KEEP"
}
```
- note: parity PASS (byte-exact vs qthe.mjs vectorPass AND vs a python integer reference — the mandatory Law-0 gate). ternary beats fp16 by 1.82x @1024 and 3.57x @2048 (past the 1.10 pre-registered margin), reversing to 0.82x @4096 where fp16 cuBLAS tensor cores dominate. This PRICES qthe SPEC Layer-2 claim C1: the "gain of function" is real in the small-to-mid regime, not at scale on this GPU.

## D3 — statevector ceiling (GPU executor for micromoth)
- ran: 2026-09-27 15:09
- verdict: KEEP
- result: ```json
{
  "experiment": "D3 statevector ceiling",
  "correctness_max_err": 5.96e-08, "correctness": "PASS",
  "ceiling": [
    {"n": 16, "gpu_ms": 3.99}, {"n": 18, "gpu_ms": 3.18}, {"n": 20, "gpu_ms": 9.95},
    {"n": 22, "gpu_ms": 51.72}, {"n": 24, "gpu_ms": 207.28}, {"n": 26, "gpu_ms": 817.25},
    {"n": 27, "gpu_ms": 25559.49}, {"n": 28, "error": "OOM"}
  ],
  "verdict": "KEEP"
}
```
- note: correctness PASS at 5.96e-08 vs micromoth's own simulator (battery of Bell/GHZ/Clifford up to n=12). GPU executor reaches n=27 complex64 (25.6s) before OOM at n=28; pure-Python micromoth chokes ~n=20. That's a ~7-qubit ceiling lift AND a reusable in-place GPU executor for the fleet's quantum-wow work. Booked bugs: LSB-first reshape order (my first two attempts used MSB-first — caught by the correctness gate), plus a latent RX sign error.

## D6 — fun scorer + seed bank (cargo-line-tycoon)
- ran: 2026-09-27 15:09
- verdict: KEEP
- result: ```json
{
  "experiment": "D6 fun scorer",
  "n_worlds": 3000, "seed": 2718,
  "model_B_params": 41473,
  "heldout_rho_B": 0.869, "heldout_rho_A": 0.781,
  "top_seed": 1421, "top25_mean_proxy": 1.298, "population_mean_proxy": 0.029,
  "verdict": "KEEP"
}
```
- note: real cargo-line-tycoon procgen (GameEngine constructor, 40-tick deterministic loop), no fallback. 6 features verified seed-variant (lcc_fraction, price_entropy, route_diversity, reachability, price_dispersion, activity); 3 excluded for zero seed-variance (booked honestly). Transparent weighted proxy. Tiny MLP (41k params) ranks held-out seeds at rho=0.869, past the 0.60 bar; top-25 seeds genuinely higher-proxy. Seed bank in results/d6_seed_bank.json. The shippable scorer is 41k params (binned 118-dim tensor beats raw distances — coarse generalizes better).

## D1 — look-again-scale (2026-09-27 15:07 AKDT)
- ran: by hand (single local pass; the full 2k-item × dozens-of-readers docket
  sweep intentionally NOT run — this is the scaled-down proof pass)
- verdict: **KEEP**
- result: ```json
{
  "experiment": "D1 look-again-scale (reach-bound fold sweep)",
  "device": "cuda",
  "seed": 2718,
  "n_items": 600,
  "n_semantic": 360,
  "n_counting": 240,
  "best_single_acc": 0.7178,
  "look_again_chord_acc": 0.8444,
  "chord_ci95": [0.8089, 0.8778],
  "single_ci95": [0.6733, 0.76],
  "ceiling_lift_look_again_vs_best_single": 0.1267,
  "ceiling_lift_symbolic_purchase": 0.1267,
  "ceiling_lift_correlated_dense_purchase": 0.0,
  "lift_ci95_k2": [0.0956, 0.16],
  "peak_vram_mib": 451.0,
  "runtime_s": 32.8,
  "verdict": "KEEP"
}
```

| configuration (chord = majority fold) | readers | eval acc | 95% CI | counting acc | semantic acc |
|---|---|---|---|---|---|
| best single (calib-selected) | bge-small | 0.718 | [0.673, 0.760] | 0.517 | 0.864 |
| dense chord, all 3 | bge+MiniLM+gte | 0.627 | [0.580, 0.671] | 0.479 | 0.733 |
| dense chord + symbolic | all 4 | 0.744 | [0.702, 0.784] | 0.767 | 0.733 |
| **Look-Again chord (calib-selected)** | **bge + symbolic** | **0.844** | **[0.809, 0.878]** | **0.821** | 0.864 |
| symbolic alone | counting-address | 0.618 | [0.578, 0.664] | 0.808 | 0.478 |

Reach-bound curve (calib-selected per k, marginal lift vs best prev):
k=1 0.718 → k=2 **+0.127** [0.096, 0.160] (bought symbolic) → k=3 −0.024 (bought
gte) → k=4 −0.076 (bought MiniLM). Only the independent-reach purchase lifts
the ceiling; correlated dense purchases are dead weight or worse.

- note: G21's effect holds and sharpens at scale. The counting-address
  purchase is worth +0.127 overall with fully non-overlapping CIs
  (counting subset: 0.517 → 0.821; semantic subset unchanged at 0.864 —
  symbolic abstains there, no harm). The surprise: the all-dense majority
  chord LOST to best-single (0.627 vs 0.718) — dense witnesses are
  correlated (pairwise agreement 0.66–0.82) and share a liberal bias, so
  40% of items split 2–1 and the weaker readers outvote the better one.
  The doctrine lands cleaner than G21 stated it: **ceiling-lift comes from
  independent REACH, not vote count.** Buying reach: +0.127. Buying
  correlated votes: −0.076 at k=4. Honest caveats booked: synthetic corpus
  (number-binding weakness is by construction, though the near-miss
  manifests are adversarial rather than trivial); chord selection done on
  the calibration split (150 items) so the eval claim is clean; symbolic
  reader's grammar covers 2 of 3 manifest formats — its 74% abstain rate is
  the honest reach limit, and it still carries the lift. Full curve +
  diagnostics: `results/d1_reach_bound_curve.json`. Code:
  `experiments/d1_look_again_scale.py` (D1_N/D1_BOOT env to scale it up).

## E8 — encoder-swap leaderboard (generated 2026-09-27)

| encoder | exp | separation gap (heldout) | drift gate | surprise | axis corr | verdict | date |
|---|---|---|---|---|---|---|---|
| our contrastive RoomEncoder (~150k, learned L0) | E1 | +1.2833 (margin delta trained-minus-untrained (heldout)) | not run | not taken | not taken | KEEP | 2026-09-27 |
| elephant vMF pipeline (hand-crafted dials) | E3 | +0.6640 (vmf d_mu (heldout fits)) | pass (stability 2/2 not-real, separation 2/2 real) | 217.4 | not taken | KEEP | 2026-09-27 |
| V-JEPA 2 ViT-L (frozen, video JEPA) | E7 | +0.4456 (cosine within-minus-cross (heldout)) | not run | not taken | 0.2799 | KEEP | 2026-09-27 |
| I-JEPA ViT-B (frozen, still-image JEPA) | E9 | pending (no non-aborted result in RESULTS.md yet) | | | | | |
- caveat: gaps are within-metric only (E1 margin on learned obs; E3 vMF d_mu on hand-crafted dials; E7/E9 cosine on frozen JEPA embeddings) — the board compares encoders against the SAME cell contract, not raw gap numbers across rows. Cross-encoder correlation (MODELS.md surprise protocol) needs persisted embeddings — future work.
- full machine-readable board: results/leaderboard.json

## E8 — encoder-swap leaderboard — aggregate E1/E3/E7 (+E9) readings into one table: separation gap, drift-gate, surprise dims per encoder. The scoreboard for the swap-and-hunt protocol.
- ran: 2026-09-27 15:21
- verdict: KEEP
- note: the runner first logged this INCONCLUSIVE due to a parser bug (rindex on nested indent=2 JSON); the board itself is correct and on disk at results/leaderboard.json. E1 margin +1.283 KEEP, E3 vMF d_mu 0.664 KEEP, E7 cosine gap 0.4456 KEEP, E9 pending. Gaps are within-metric only. Runner parser hardened (raw_decode scan-backward).
- result: ```json
{
  "experiment": "E8",
  "verdict": "KEEP",
  "stdout_tail": "\": \"2026-09-27\"\n    },\n    {\n      \"encoder\": \"elephant vMF pipeline (hand-crafted dials)\",\n      \"experiment\": \"E3\",\n      \"heldout_gap\": 0.664,\n      \"gap_metric\": \"vmf d_mu (heldout fits)\",\n      \"drift_gate\": \"pass (stability 2/2 not-real, separation 2/2 real)\",\n      \"surprise\": 217.4,\n      \"surprise_metric\": \"KL sym (heldout vMF fits)\",\n      \"axis_corr\": null,\n      \"axis_corr_metric\": \"not taken\",\n      \"verdict\": \"KEEP\",\n      \"date\": \"2026-09-27\"\n    },\n    {\n      \"encoder\": \"V-JEPA 2 ViT-L (frozen, video JEPA)\",\n      \"experiment\": \"E7\",\n      \"heldout_gap\": 0.4456,\n      \"gap_metric\": \"cosine within-minus-cross (heldout)\",\n      \"drift_gate\": \"not run\",\n      \"surprise\": null,\n      \"surprise_metric\": \"not taken\",\n      \"axis_corr\": 0.2799,\n      \"axis_corr_metric\": \"tex-vs-motion axis corr (smpte-still vs testsrc-testsrc2)\",\n      \"verdict\": \"KEEP\",\n      \"date\": \"2026-09-27\"\n    }\n  ],\n  \"pending\": [\n    {\n      \"encoder\": \"I-JEPA ViT-B (frozen, still-image JEPA)\",\n      \"experiment\": \"E9\",\n      \"status\": \"pending (no non-aborted result in RESULTS.md yet)\"\n    }\n  ],\n  \"aborted_latest_only\": [],\n  \"caveat\": \"gaps are within-metric only (E1 margin on learned obs; E3 vMF d_mu on hand-crafted dials; E7/E9 cosine on frozen JEPA embeddings) \\u2014 the board compares encoders against the SAME cell contract, not raw gap numbers across rows. Cross-encoder correlation (MODELS.md surprise protocol) needs persisted embeddings \\u2014 future work.\",\n  \"verdict\": \"KEEP\"\n}\n"
}
```
