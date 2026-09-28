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

## D5 — probe foundry (proof batch)
- ran: 2026-09-27 15:29
- verdict: KEEP
- result: ```json
{
  "experiment": "D5 probe foundry (proof batch)",
  "seed": 2718, "n_generated": 240, "n_deduped": 215, "dedup_rate": 0.1042,
  "counts": {"canon": 107, "distortion": 108},
  "train": 149, "heldout": 66,
  "reproducibility_hash": "9817d604826801ddd7ff53b2c748d10e964b003b0d17832d0a91cf63cb82be7e",
  "verdict": "KEEP"
}
```
- note: seeded template grammar (no model, no API) proves the foundry plumbing: content-addressed (sha256), 10.4% dedup (periodic grammar collisions), hash-split 149 train / 66 held-out. Full-scale recipe (7B-4bit regeneration) in recipe.json; probes.jsonl + recipe.json on disk. Feeds D1 readers and D4 QLoRA.

## D10 — cudaclaw cell kernel (micromoth-quilt-cudaclaw step 1)
- ran: 2026-09-27 15:29
- verdict: KEEP
- result: ```json
{
  "experiment": "D10 cudaclaw cell kernel",
  "seed": 2718, "n_qubits": 6,
  "determinism": "PASS", "reconstruction": "PASS",
  "cell_A_message": 1, "cell_B_before": 0, "cell_B_after": 1,
  "two_cell_smoke": "PASS", "verdict": "KEEP"
}
```
- note: a quilt cell whose memory is an n-qubit statevector and whose edge is ternary-quantized (never raw amplitude). Determinism PASS (byte-identical state hash across two seeded runs); reconstruction PASS (ternary message = sign of dominant correlation); 2-cell relational smoke PASS (biased cell A emits +1, balanced cell B shifts 0->1 in the received direction). Booked bugs: X applied to an already-uniform qubit does nothing (bias qubit must be set definite before the H loop); a phase-only RZ message cannot move probabilities (must RX). This is D13's substrate in miniature.

## D4 — canon-lora (QLoRA local canon reader)
- ran: 2026-09-27 15:43
- verdict: INCONCLUSIVE (full-scale: tuned 1.0 vs base 0.8833, +0.1167 < +0.15 bar)
- result: ```json
{
  "experiment": "D4 canon-lora (QLoRA local canon reader)",
  "mode": "full + smoke", "seed": 2718, "model": "Qwen/Qwen2.5-0.5B-Instruct", "quant": "nf4-4bit",
  "base_acc": 0.75, "tuned_acc": 0.7,
  "margin": -0.05, "preregistered_margin": 0.15,
  "peak_vram_mib": 1024.2, "wall_seconds": 506.4,
  "verdict": "INCONCLUSIVE"
}
```
- note (FULL-SCALE, D4_FULL=1): Qwen2.5-1.5B-Instruct, 4-bit NF4 + LoRA r=16, 24 steps over D5 probes (98 train / 60 held-out), peak VRAM 2.05 GB, 20.4 min wall. tuned 1.0 vs base 0.8833 = +0.1167, UNDER the pre-registered +0.15 margin -> INCONCLUSIVE (positive but short; tuned hit 100% on 60 held-out probes — the local reader CAN learn the doctrinal read, the bar was just set conservatively). Adapter at results/d4_adapter_smoke/.
- note: SMOKE pass proves the pipeline — 4-bit NF4 load WORKED on Qwen2.5-0.5B (no fp16 fallback), 2 optimizer steps, base 0.750 vs tuned 0.700 (margin -0.05, INCONCLUSIVE by design — a 2-step run can't KEEP/KILL). Full-scale recipe in results/d4_eval.json: D4_FULL=1 -> Qwen2.5-1.5B-Instruct, 2 epochs over D5 probes (98 train / 60 held-out, sha256-parity split), ~4-4.5 GB peak, ~1h wall, KEEP iff tuned >= base + 0.15. Adapter (8.8M params, 34MB) at results/d4_adapter_smoke/.


## E9 — ijepa stills — I-JEPA ViT-B (facebookresearch/ijepa) on still frames through the same cell contract; does a still-image world model read rooms differently than video V-JEPA 2?
- ran: 2026-09-27 15:45
- verdict: ABORTED
- result: ```json
{
  "experiment": "E9",
  "facebook/ijepa_vitb": "load failed: OSError: facebook/ijepa_vitb is not a local folder and is not a valid model identifier listed on 'https://huggingface.co/models'\nIf this is a private repository, make sure to pass a token having permission to this repo either by logging in with `hf auth login` or by passing `token=<your",
  "guard_summary": {
    "samples": 243,
    "min_free_vram_mib": 4104,
    "max_temp_c": 61,
    "breach": null,
    "timed_out": false
  }
}
```

## D14 — qthe timbre channel proof (zero-bit-cost context-keyed embedding)
- ran: 2026-09-27 15:54
- verdict: KEEP
- result: ```json
{
  "experiment": "D14 qthe timbre channel proof",
  "seed": 2718, "n_turns": 2000, "n_contexts": 4, "n_momenta": 4, "chance": 0.25,
  "data_only_acc": 0.259, "naive_timbre_acc": 0.2645, "contextual_timbre_acc": 1.0,
  "I(M;T)_naive_bits": 0.0026, "I(M;T,context)_contextual_bits": 1.9995,
  "zero_bit_cost": "the byte is always 8 bits; the momentum signal rides in the 2 timbre bits at no extra bit-cost",
  "verdict": "KEEP"
}
```
- note: PROVES Casey's ah-ha — QTHE's 2 timbre bits (already paid for by the byte) carry a ternary momentum signal at ZERO additional bit-cost, and the channel is CONTEXT-KEYED: the 6-bit data plane reads ~chance (0.259), the 2-bit timbre ALONE reads ~chance (0.2645, I(M;T)=0.0026 bits ≈ 0), but timbre+context recovers the signal perfectly (1.0, 2.0 bits). A plaintext reader sees nothing; a timbre reader without the context key sees noise; only a contextual decoder recovers it. That is a2a vector-embedding riding in plaintext for free.
- booked encoding lessons (the two false starts ARE the finding): (1) a RANDOM permutation leaks through fixed points — a naive identity reader gets ~1 free hit per context (I(M;T) 0.3765); (2) a DERANGEMENT over-corrects — "t != m" becomes itself 1 bit of info (I(M;T) 0.95). Only a LATIN SQUARE (each row a bijection, each column covers all timbres) is information-clean: I(M;T)=0 exactly. The Latin-square construction IS the extractable tool Casey described — modular, 8-bit, and it composes with qthe's 64-slot wormhole + the 200-repo ternary wiki.

## E10 — invariance race (ternary gate vs stateless sign-trackers)
- ran: 2026-09-27 17:50
- verdict: KILL
- result: ```json
{
  "experiment": "E10 invariance race",
  "seed": 2718, "frames": 200, "dims": 256,
  "gate_acc": 0.6784, "persistence_acc": 0.9146, "deadreckon_acc": 0.9192,
  "gate_minus_persistence": -0.2362, "preregistered_margin": 0.05,
  "verdict": "KILL"
}
```
- note: the naive ternary coordinate-stepper (one clamped flip/frame over 256 cells) LOSES to a stateless persistence tracker (0.678 vs 0.915) and to dead-reckoning (0.919) on smooth-sinusoid next-sign prediction. This is the honest null the docket pre-registered — on a smooth signal, "predict the last sign" IS the lookup table that wins, and the gate does not beat it. It CONFIRMS the earlier adversary-lane prediction (NMEA/smooth-signal = mirage: a persistence tracker looks brilliant and is a lookup table). The "ternary = learning substrate" claim is NOT supported by this task. It survives only on a task where persistence structurally FAILS — e.g. a reach-bound task where the truth is in the correlation between two positions, not in "keep going the same way." That is the discriminating test to run next (E11 debounce-kill should isolate exactly that). Booked as KILL, not dressed up.


## E11 — debounce-kill (delay-2 discriminating test)
- ran: 2026-09-27 17:54
- verdict: KEEP
- result: ```json
{
  "experiment": "E11 debounce-kill (delay-2 discriminating test)",
  "seed": 2718, "frames": 300, "window": 8,
  "gate_acc": 0.9966, "persistence_acc": 0.0, "deadreckon_acc": 0.0,
  "gate_minus_persistence": 0.9966, "preregistered_margin": 0.30,
  "verdict": "KEEP"
}
```
- note: the DISCRIMINATING test E10 demanded. On a delay-2 signal (s[t]=s[t-2], alternating +1/-1) a stateless persistence tracker is structurally blind (0% — it predicts the last sign, which is always wrong on an alternating line), and dead-reckoning is also 0%. The ternary gate, holding an 8-tap memory window, finds the delay-2 tap and reaches 0.9966. So the gate is NOT a pure debounce circuit: it learns a temporal dependency no stateless sign-tracker can reach. Combined with E10 (KILL on smooth signals where persistence wins), the two poles bracket the truth: ternary adds nothing on smooth signals, but adds real structure-learning where the stateless tracker is blind. Honest caveat booked: this is a toy alternating line, not a realistic signal — the point is narrow (existence of a learnable dependency beyond persistence), not a claim of practical win.


## D12 — substrate falsification (relational graph vs isolated cells)
- ran: 2026-09-27 17:57
- verdict: KEEP
- result: ```json
{
  "experiment": "D12 substrate falsification (relational vs isolated)",
  "seed": 2718, "n_cells": 8, "qubits": 4, "facts": 120,
  "acc_isolated_A": 0.5583, "acc_relational_B": 1.0, "acc_traffic_permuted_C": 0.5083,
  "delta": 0.4417, "preregistered_margin": 0.10,
  "ci_A": [0.475, 0.642], "ci_B": [1.0, 1.0], "ci_C": [0.425, 0.6],
  "verdict": "KEEP"
}
```
- note: the design doc's crown jewel, at the reach-bound structural baseline. Cross-boundary facts (parity of two atoms in DIFFERENT cells) are structurally invisible to any isolated cell (A 0.558 ~ chance). The relational graph recovers them at 1.0 by message-passing (a cell receives its partner's atom value and reconstructs the parity). The traffic-permuted control C (SAME message volume, scrambled targeting) stays at 0.508 — proving the win is the RELATIONAL TARGETING, not the communication volume. delta 0.44 >> 0.10. Honest caveat: this is the structural baseline with noiseless messages and perfect addressing; the learning version (cells must LEARN whom to message) is D13. Booked bug en route: my first measurement conflated "fraction of facts with parity=1" (0.44) with reconstruction accuracy — the receiver reconstructs the parity CORRECTLY, so B=1.0, not 0.44.


## D13 — relational intelligence growing (learned addressing)
- ran: 2026-09-27 17:58
- verdict: KILL
- result: ```json
{
  "experiment": "D13 relational intelligence growing (learned addressing)",
  "seed": 2718, "epochs": 30, "cells": 8, "facts": 60,
  "final_acc": 0.467, "target": 0.80,
  "edge_concentration_on_true_partner": 0.233,
  "verdict": "KILL"
}
```
- note: the REAL falsification Casey named — cells must LEARN whom to message (D12 handed them the address). With a naive binary-reward Hebbian rule (reward 1.0 when reconstruction matches, 0.5-coin otherwise, 0.98-decay + 0.02-boost), the graph does NOT converge: final accuracy 0.467 (below the isolated baseline 0.558), edge concentration 0.233 vs chance 0.143. There IS a real but weak gradient (true partner rewards 1.0 always vs 0.5 for wrong), but the rule is too slow/weak to climb in 30 epochs over only 30 updates/edge. BOOKED HONESTLY: the structural result (D12, perfect addressing -> 1.0) stands; "relational intelligence GROWING" needs a stronger credit-assignment mechanism than naive Hebbian reward — that IS the finding. Next: policy-gradient-style edge learning, or a reward that uses reconstruction CONFIDENCE (not binary match) as the signal. D13 kills the naive version, not the program.


## D13b — relational addressing (confidence-weighted reward)
- ran: 2026-09-27 18:00
- verdict: KILL
- result: ```json
{
  "experiment": "D13b relational addressing (confidence-weighted reward)",
  "seed": 2718, "epochs": 30, "cells": 8, "facts": 60,
  "final_acc": 0.533, "target_acc": 0.80,
  "edge_concentration": 0.30, "target_conc": 0.50,
  "verdict": "KILL"
}
```
- note: the confidence-weighted (signed) reward is a STRONGER signal than D13's binary reward — edge concentration rose 0.233 -> 0.30 (chance 0.143) and mid-run accuracy peaked 0.717 — but it still does not converge within 30 epochs. The trail is now honest and sharp: D12 proves the STRUCTURAL reach-bound (perfect addressing -> 1.0), but LEARNING the addressing is a genuinely hard credit-assignment problem. Naive Hebbian (D13) and confidence-weighted (D13b) both fail; the next rung is a proper policy-gradient / REINFORCE-with-baseline, or a shared-key (two cells discover their correlation by noticing their atoms are anti-correlated, then message each other directly). "Relational intelligence GROWING" is real at the structure level and HARD at the learning level — that is the finding. Booked honestly, not dressed up.


## D13c — relational addressing (REINFORCE with baseline)
- ran: 2026-09-27 18:53
- verdict: KILL
- result: ```json
{
  "experiment": "D13c relational addressing (REINFORCE with baseline)",
  "seed": 2718, "epochs": 30, "cells": 8, "facts": 60,
  "final_acc": 0.65, "target_acc": 0.80,
  "edge_concentration": 0.217, "target_conc": 0.50,
  "verdict": "KILL"
}
```
- note: the third rung. Policy-gradient with learned baseline does NOT converge either (concentration 0.217, worse than D13b's 0.30; final acc 0.65). The arc is now COMPLETE and honest: D12 KEEP (structure reachable at 1.0 with perfect addressing), D13/D13b/D13c all KILL (learning the addressing does not yield to Hebbian, confidence-weighted, OR REINFORCE-with-baseline in this sparse setting — only ~32 reward updates per edge over 30 epochs, a 0.5 signal buried in coin-flip noise). The finding: the credit-assignment of RELATIONAL LEARNING is the open problem, and standard RL does not crack it here. Next rung is NOT another RL variant — it is the SHARED-KEY discovery (two cells detect their atoms are anti-correlated and identify each other directly, O(1) information instead of reward accumulation), which is a different MECHANISM, not a better reward.


## D13d — shared-key discovery (correlation, not reward)
- ran: 2026-09-27 18:55
- verdict: KEEP
- result: ```json
{
  "experiment": "D13d shared-key discovery (correlation, not reward)",
  "seed": 2718, "cells": 8, "observations": 200, "p_corr": 0.9,
  "partner_identification_acc": 1.0, "target": 0.90,
  "verdict": "KEEP"
}
```
- note: the payoff of the D13 arc. Three RL variants (Hebbian, confidence-weighted, REINFORCE-with-baseline) all KILLed on learning the relational partner (concentration 0.217-0.30, chance 0.143). This tests the OTHER mechanism Casey named — SHARED-KEY DISCOVERY — and it cracks it at 1.0: a cell finds its true partner by computing max |correlation| of atom streams over 200 observations, with NO reward signal. The finding is sharp and general: the relational primitive is CORRELATION DETECTION (mutual information), not reward accumulation. "Relational intelligence growing" = cells noticing their atoms are correlated, then messaging the correlated peer directly — O(1) information, not gradient descent over reward. This connects to elephant's vmf/correlation machinery: the room-sense is already correlation; the substrate's partner-discovery is the same primitive. Booked bug: first run used a cyclic pairing (each cell in two pairs -> scrambled streams, 0.375); fixed to disjoint pairs.


## E6 — harness self-test (guard breach paths, torn-queue, receipt integrity)
- ran: 2026-09-27 18:57
- verdict: KEEP
- result: ```json
{
  "experiment": "E6 harness self-test",
  "guard_low_vram_refuses": true, "guard_high_temp_refuses": true, "guard_healthy_accepts": true,
  "claim_skips_scriptless": true, "checkoff_exactly_one": true, "receipt_drift_detected": true,
  "verdict": "KEEP"
}
```
- note: the watchdog works — guard refuses low-VRAM (<1GB) and high-temp (>80C) preflights and accepts a healthy one; the runner skips scriptless items and checks off exactly one; the receipt manifest detects a tampered digest. The harness is not the weak point.


## E5 — quantization probe (CLOSED — subsumed by D7)
- ran: 2026-09-27 18:57
- verdict: CLOSED (subsumed)
- note: E5's "int8 vs fp16 embedding drift" question was fully answered by D7 (quant-drift probe): fp16->int8->NF4 drift and verdict-flip rate measured on a held-out probe set, NF4 held flip-rate 0.0. No redundant experiment run; cross-linked to D7 per the docket.


## D16 — embedder readability (tiny MLP reads the tone class)
- ran: 2026-09-27 19:00
- verdict: KEEP
- result: ```json
{
  "experiment": "D16 embedder readability (tiny MLP reads the tone class)",
  "seed": 2718, "classes": 6, "train": 800, "heldout": 200,
  "mlp_acc": 0.93, "majority_baseline": 0.20, "chance": 0.1667, "target": 0.85,
  "embedding_dim": 13,
  "verdict": "KEEP"
}
```
- note: validates the embedder (qthe_embedder.py) — a 13-dim tone vector IS readable by a tiny MLP (dim->32->K), recovering the tone class from held-out samples at 0.93 vs majority 0.20. So the embedder is not lossy: the tone shape (histogram/arc/run/spectral features) is a real, learnable representation. This is the first validation of the embedder stage, closing the loop that D14 opened (the primitive exists) -> compiler (verifiable) -> embedder (readable) -> transformer (condense/spatialize).


## D17 — compiler compression at scale
- ran: 2026-09-27 19:06
- verdict: KEEP
- result: ```json
{
  "experiment": "D17 compiler compression at scale",
  "seed": 2718,
  "crossover_chars": 200,
  "largest_ratio": 0.7893,
  "largest_momentum_compression": 0.0345,
  "largest_wire_compression": 0.72,
  "verdict": "KEEP"
}
```
- note: first pass KILLED — the compiler (RLE on the WIRE timbre) INFLATED the stream (ratio 1.73) because the Latin square scrambles the wire timbre into noise (that scrambling IS what hides the tone). The fix, and the FINDING: decode the momentum FIRST (using the data plane as context), then RLE the decoded momentum — which compresses to 0.034 (3.4%!), vs the wire's 0.72. With 6-bit data packed 4-per-3-bytes, the compiler now beats raw at 200 chars and reaches ratio 0.789 at 4000. This is a genuine, sharp result: the tone channel's INVISIBILITY (Latin-square scrambling) and its COMPRESSIBILITY are in tension on the wire — you cannot compress what you are hiding. A receiver with context can decode-and-compress; a context-free observer can neither read nor compress it. That is the whole game in one number.


## D15 — read-the-channel (VLM LoRA reads the tone channel) [SMOKE]
- ran: 2026-09-27 19:09
- verdict: INCONCLUSIVE (full-scale: tuned 0.3509 vs base 0.2658, +0.0851 — positive but under the 0.80/0.30 gate)
- result: ```json
{
  "experiment": "D15 read-the-channel (VLM LoRA reads the tone channel)",
  "mode": "smoke", "seed": 2718, "model": "Qwen2.5-0.5B-Instruct", "quant": "nf4-4bit",
  "train_pairs": 8, "heldout_pairs": 10, "steps": 2,
  "tuned_token_acc": 0.127, "base_token_acc": 0.00,
  "peak_vram_mib": 1390, "wall_s": 45,
  "verdict": "INCONCLUSIVE"
}
```
- note: the reading gate. A 2-step smoke proves the pipeline: the tuned model immediately learns the output FORMAT (loss 1.04->0.52, emits d/f/u/h codes) while base just echoes hex (0.00 wellformed). 0.127 token-acc on a 2-step run is pipeline proof, not the hypothesis test. 4-bit NF4 held, no fallback. FULL-SCALE RECIPE (D15_FULL=1): Qwen2.5-1.5B, 2 epochs over 400 train pairs, eval 60 held-out pairs; pre-registered gate: tuned >= 0.80 AND base <= 0.30 (chance 0.25). Since D14 proved I(M;T)=0 without context, >=0.80 can only be reached by actually reading timbre+context. ~1h on the 4050.


## E4b — next-room revision (60s clips, 236 cells, blocked split) [SMOKE]
- ran: 2026-09-27 19:11
- verdict: KILL (full-scale: heldout 0.821 vs markov-1 0.846)
- result: ```json
{
  "experiment": "E4b next-room revision",
  "mode": "smoke", "seed": 2718, "rooms": 2, "cells": 38, "epochs": 1,
  "model_train_acc": 0.923, "model_heldout_acc": 0.750,
  "constant_baseline": 0.250, "markov1_baseline": 0.750,
  "verdict": "INCONCLUSIVE"
}
```
- note: the E4 fix. The degenerate E4 baseline is DEAD: constant-predictor now 0.25 (chance, was 0.75 in E4's broken tail-split), markov-1 0.75 is the real bar. 60s clips -> 236 cells, interleaved walk (35 room transitions), blocked split by cell-block (all 4 rooms in heldout). Full data-path validation: constant 0.179, markov-1 0.846 — so the full-scale question is sharp: beat 0.846+0.05 by reading run-position from 8-cell context, not just current room. FULL-SCALE: E4B_FULL=1 -> rooms=4, 60s, 120 epochs, minutes on 4050. Determinism proven (byte-identical runs).



## D15 — read-the-channel [FULL-SCALE]
- ran: 2026-09-27 19:53
- verdict: INCONCLUSIVE (positive but under gate)
- result: ```json
{
  "experiment": "D15 read-the-channel (full-scale)",
  "tuned_token_acc": 0.3509, "base_token_acc": 0.2658,
  "tuned_minus_base": 0.0851, "gate_tuned": 0.80, "gate_base": 0.30,
  "verdict": "INCONCLUSIVE"
}
```
- note: the reading gate, honestly. Tuned beats base (+0.0851) — the LoRA is learning SOMETHING about the channel — but tuned 0.3509 is far from the 0.80 gate, and base 0.2658 is barely under its 0.30 ceiling (chance 0.25). Reading the timbre channel from bytes is HARD: the model climbs to 0.35 (well above chance, format learned) but can't reach the read-the-channel ceiling in 2 epochs on 1.5B. This is the honest first rung of Casey's VLM-LoRA vision: the channel is learnable-but-hard, and the gap (0.35 -> 0.80) is exactly where a bigger model / more epochs / better tokenization lives. Not a KILL — a direction with a measured distance.


## E4b — next-room revision [FULL-SCALE]
- ran: 2026-09-27 20:04
- verdict: KILL
- result: ```json
{
  "experiment": "E4b next-room-revision",
  "mode": "full", "seed": 2718, "params": 68164,
  "cells": 236, "room_transitions": 35, "train_windows": 189, "heldout_windows": 39,
  "train_acc": 0.963, "heldout_acc": 0.821,
  "constant_baseline": 0.179, "markov1_baseline": 0.846,
  "preregistered_margin": 0.05, "verdict": "KILL"
}
```
- note: the fixed dataset finally runs, and the honest null lands. The degenerate constant baseline is dead (0.179, was 0.75 in E4's broken tail-split). But markov-1 (0.846) is the real bar, and the 68k-param transformer — now with 236 cells, interleaved walk (35 transitions), blocked split (all 4 rooms in heldout) — reaches heldout 0.821, which is BELOW markov-1. Verdict KILL per pre-registration (heldout must exceed max(baseline)+0.05). Finding: next-room prediction from 8-cell glyph context does NOT beat a simple transition-count model at this scale. The JEV-temporal question closes as: the temporal signal in this glyph-cell encoding is already fully captured by markov-1; a learned model adds nothing at 68k params. (The E4b note's "SMOKE" text in the JSON note field is stale cosmetic text from the smoke template — the mode/verdict/cells are the real full-scale run.)

## D18 — correlation-discovery scaling (does D13d generalize?) [CPU]
- ran: 2026-09-27 20:23
- verdict: INCONCLUSIVE (correlation CONFIRMED, but the contrast half FALSIFIED)
- result: ```json
{
  "experiment": "D18 correlation-discovery scaling",
  "seed": 2718, "observations": 200, "reps": 5,
  "corr_matrix_acc": {
    "8":  {"0.9": 1.0, "0.75": 1.0, "0.6": 1.0, "0.55": 1.0},
    "32": {"0.9": 1.0, "0.75": 1.0, "0.6": 1.0, "0.55": 1.0},
    "100":{"0.9": 1.0, "0.75": 1.0, "0.6": 1.0, "0.55": 1.0},
    "300":{"0.9": 1.0, "0.75": 1.0, "0.6": 1.0, "0.55": 1.0}
  },
  "rl_reinforce_d13c": {"N=8": {"conc": 1.0, "chance": 0.143}, "N=32": {"conc": 1.0, "chance": 0.032}},
  "sanity_wrong_partner_conc": 0.0,
  "strict_joint_ok_N100_p060": true,
  "reinforce_collapses_N32": false,
  "verdict": "INCONCLUSIVE"
}
```
- note: TWO findings, one clean one painful. (1) Correlation-discovery is CONFIRMED and STRONGER than claimed — identification holds at 1.0 on the ENTIRE grid, every cell including the strict joint (N=100, p_corr=0.6) and the whole p_corr=0.55 row (the doc predicted crossing 0.5 near 0.55; the real floor sits far lower, ~0.25 by SNR math at T=200). (2) The contrast half FALSIFIED — re-running D13c REINFORCE on *disjoint consistent partners* (not the scattered per-fact partners of the original) reaches concentration 1.0 at N=8 AND N=32, NOT the claimed collapse below 0.3. The D13/D13b/D13c "reward is structurally poor" claim was CONFOUNDED: D13c's 0.217 was measured with one per-sender policy chasing ~7 conflicting targets (argmax structural ceiling ~1/7), while D13d's correlation read disjoint consistent pairs. On the SAME partner-consistent ground truth, REINFORCE learns the addressing at 1.0 even at N=32. Corrections: correlation scales (stronger than claimed); reward ALSO scales when the relational target is consistent. The primitive is NOT "correlation vs reward" — it is "consistent relational target," and correlation is the O(1) way to FIND that target. Negative control (reward wired to a shifted partner → conc 0.0) and verbatim D13c reproduction (0.217) confirm the harness is sound. Verdict INCONCLUSIVE per pre-registration because the contrast half of the claim failed, not because the signal was weak. RELATIONAL-CORRELATION-PRIMITIVE.md revised to correct the confound.

## D15b — read-the-channel v2 (few-shot + curriculum + 5 real epochs) [SMOKE]
- ran: 2026-09-27 20:09
- verdict: INCONCLUSIVE (smoke; full-scale recipe ready)
- result: ```json
{
  "experiment": "D15b read-the-channel v2",
  "mode": "smoke", "seed": 2718, "model": "Qwen2.5-0.5B-Instruct", "quant": "nf4-4bit",
  "peak_vram_mib": 1873.5, "wall_seconds": 100.4,
  "verdict": "INCONCLUSIVE"
}
```
- note: pipeline proven on GPU (4-bit NF4 held, no fallback). D15b attacks the 0.35->0.80 gap with 4 concrete changes: (1) 5 REAL curriculum epochs — fixes a step-math bug in D15 where steps=len*epochs//8 but the loop ate 4 examples/step, so "2 epochs" was ~1 effective pass; (2) few-shot worked examples (4 codec-asserted byte decodings) in the prompt, both arms; (3) curriculum short->long (12-char -> 24-char -> full, so the model learns the per-byte subroutine before long-output alignment); (4) bigger base chain Qwen2.5-3B 4-bit with VRAM-headroom fallback to 1.5B. Gate unchanged: tuned>=0.80 AND base<=0.30. FULL-SCALE: D15B_FULL=1, ~2.5-3.5h on the 4050.


## D1b — look-again sweep (bundled corpus, oracle/safe-fold/Look-Again) [SMOKE]
- ran: 2026-09-28 (dev-box smoke, no GPU/network in that box — this is the
  zero-setup portability proof, not the docket-scale decision)
- verdict: INCONCLUSIVE (smoke; full-scale ready via `D1B_FULL=1` on the RTX 4050)
- result: ```json
{
  "experiment": "D1b look-again sweep (bundled corpus, reach-bound scaling)",
  "mode": "smoke", "device": "cpu", "have_torch": false, "seed": 2718,
  "item_source": "bundle:d1_lookagain_items.jsonl (n=320)",
  "n_items": 320, "n_semantic": 160, "n_counting": 160, "n_eval": 240,
  "readers": {"dense_0": "bge-small-en-v1.5 (hash-fallback)",
              "dense_1": "all-MiniLM-L6-v2 (hash-fallback)",
              "dense_2": "gte-small (hash-fallback)",
              "symbolic": "counting-address (G21)"},
  "headline": {
    "best_single_acc": 0.45, "best_single_ci95": [0.3875, 0.5083],
    "oracle_dense_acc": 0.7083, "oracle_dense_plus_reach_acc": 0.9125,
    "safe_fold_dense_acc": 0.45, "safe_fold_dense_plus_reach_acc": 0.6292,
    "look_again_acc": 0.6292, "look_again_minus_best_single": 0.1792,
    "lift_ci95": [0.1375, 0.2292], "reach_ceiling_lift": 0.2042
  },
  "correlated_dense_purchase_oracle_lift": 0.1542,
  "bootstrap_draws": 500, "runtime_s": 0.1,
  "verdict": "INCONCLUSIVE"
}
```
- note: this is D1 (`experiments/d1_look_again_scale.py`, KEEP) repackaged as
  a zero-setup artifact — a COMMITTED 320-item bundle
  (`experiments/data/d1_lookagain_items.jsonl`, 50/50 semantic/counting,
  seed 2718, regenerate with `--regen-bundle`) plus an explicit
  best-single / oracle(dense) / oracle(dense+symbolic) / safe-fold-vote /
  Look-Again comparison (not just a chord sweep), and a scaling readout over
  #items and #dense-readers (`scaling_by_items`, `scaling_by_readers` in
  `results/d1_lookagain_scaling.json`). This run used the CPU/offline
  hashing-trick fallback (no torch, no network in the dev sandbox that
  wrote this line) — deliberately weak individual dense readers, which is
  WHY `best_single_acc` (0.45) reads below chance and `safe_fold_dense_acc`
  matches it exactly (3 noisy, correlated hash-projections voting together
  add nothing). The qualitative finding survives anyway, sharply: buying
  the independent-reach symbolic reader lifts the existential oracle
  ceiling +0.204 (0.708 -> 0.913, more than the +0.154 a second correlated
  dense reader buys), and Look-Again (best-single, overridden by the
  reach reader at its addresses) beats best-single by +0.179
  [0.138, 0.229] — CI excludes 0. Both scaling curves
  (`scaling_by_items` n=48..320, `scaling_by_readers` k=1..3) hold the same
  qualitative shape across sizes. **This is a pipeline/portability proof,
  not the docket decision** — the verdict is correctly downgraded to
  INCONCLUSIVE per the smoke convention (cf. D4, D15, D15b) because weak
  fallback embeddings aren't the real LLM-reader question. On the RTX 4050
  tonight, `D1B_FULL=1 python -m experiments.d1b_lookagain_sweep` downloads
  the real `bge-small-en-v1.5` / `all-MiniLM-L6-v2` / `gte-small` encoders
  (GPU-accelerated via sentence-transformers/torch, <2 GB VRAM per the
  docket envelope), generates 3000 items on the fly (same generator, seed
  2718), and can return **KEEP/KILL** for real: KEEP iff the accuracy-lift
  CI excludes 0 AND the reach-reader purchase raises the oracle ceiling
  over the dense pool alone. **Caveat on `runner.py`:** its queue-claim
  regex (`ITEM_RE`) only matches `E\d+` ids, so — like every other D-item
  in this ledger — D1b is NOT auto-claimed by the cron loop; run it
  directly with the command above (still wired into `runner.EXP_MOD["D1b"]`
  for `guard.py`-wrapped manual invocation via `runner.run("D1b")`).


## D15b — read-the-channel v2 (FULL-SCALE, D15B_FULL=1)
- ran: 2026-09-27 21:35
- verdict: KEEP
- result: ```json
{
  "experiment": "D15b read-the-channel v2",
  "mode": "full", "seed": 2718, "model": "Qwen2.5-3B-Instruct", "quant": "nf4-4bit",
  "peak_vram_mib": 4236.2, "wall_seconds": 5167.8,
  "tuned_token_acc": 0.9413, "base_token_acc": 0.0781, "margin_token_acc": 0.8632,
  "verdict": "KEEP"
}
```
- note: full-scale landed. Tuned adapter reads the tone channel at 0.9413 (gate >=0.8) vs base 0.0781 (gate <=0.3, chance 0.25) — margin 0.8632. Plaintext carries zero momentum bits (D14), so >=0.80 is only reachable by decoding timbre+context. The tone channel is a real, learnable, decodable side-channel.


## D19 — transitional-jepa (relational transition kernel)
- ran: 2026-09-27 21:37
- verdict: KEEP
- result: ```json
{
  "experiment": "D19 transitional-jepa (relational transition kernel)",
  "seed": 2718, "n_agents": 8, "field_dim": 32, "n_steps": 4000,
  "heldout_mse": {
    "markov1": 0.01786,
    "jepa_ternary": 0.01012,
    "oracle_continuous": 0.01098,
    "jepa_shuffled": 0.01801
  },
  "signal_gain": 0.00774,
  "ternarization_cost": -0.00085,
  "control_ok": true,
  "verdict": "KEEP"
}
```
- note: the relational transition kernel (tools/transition_kernel.py) — the "Transitional JEPA" primitive where ternary correlation is the perceptual feature predicting field-state transitions. TWO findings: (1) KEEP — ternary correlation of the acting edge carries real signal: 0.0101 vs markov1 0.0179 (+0.0077 gain), and the shuffled control collapses to 0.0180 (≈ markov1), so the win is the signal, not capacity. (2) BONUS — ternarization is FREE: the ternary model (0.0101) slightly BEATS the continuous-diff oracle (0.0110); the sign/deadband acts as a regularizer, not a cost. The 3-state codec generalizes at least as well as the continuous identity difference here.


## D20 — transitional-jepa ablation (nonlinear + identity)
- ran: 2026-09-27 21:41
- verdict: KEEP
- result: ```json
{
  "experiment": "D20 transitional-jepa ablation (nonlinear + identity)",
  "seed": 2718,
  "heldout_mse": {
    "linear_ternary": 0.01012,
    "nonlinear_quadratic": 0.01043,
    "identity_onehot": 0.01015,
    "oracle_continuous": 0.01098
  },
  "rel_gain_nonlinear": -0.0305,
  "rel_gain_identity": -0.0023,
  "verdict": "KEEP"
}
```
- note: the simple linear ternary kernel is SUFFICIENT. Nonlinear quadratic expansion is 3% WORSE (0.0104 vs 0.0101 — overfits; the generator is linear in field_before and corr is already {-1,0,+1}). Exact agent identity (one-hot pair) adds nothing (0.0101 vs 0.0101, -0.2% — sign-only ternary correlation already carries all the identity signal that matters). Together with D19's "ternarization is free", the picture sharpens: the 3-state codec's sign-only correlation is not a compromise — it is the RIGHT abstraction for relational transitions. Full nonlinearity and exact identity both buy zero predictive value here.


## D1b — look-again sweep (FULL-SCALE, D1B_FULL=1)
- ran: 2026-09-27 21:54
- verdict: KEEP
- result: ```json
{
  "experiment": "D1b look-again sweep (bundled corpus, reach-bound scaling)",
  "mode": "full", "device": "cuda", "seed": 2718,
  "n_items": 3000, "bootstrap_draws": 2000,
  "best_single_acc": 0.6884, "look_again_acc": 0.8569, "lift": 0.1684,
  "oracle_dense_plus_reach_acc": 0.9649, "reach_ceiling_lift": 0.1462,
  "peak_vram_mib": 471.9, "runtime_s": 38.5,
  "verdict": "KEEP"
}
```
- note: full-scale on the RTX 4050 with real dense encoders (bge-small-en-v1.5 / all-MiniLM-L6-v2 / gte-small, GPU-accelerated). Look-Again beats best-single 0.8569 vs 0.6884 (+0.1684, bootstrap CI excludes 0); buying the independent-reach reader raises the existential oracle ceiling to 0.9649 (+0.146 over the dense pool). Confirms D1's KEEP at scale: the reach reader's independent address-space buys more than a second correlated dense reader.


## E9 — ijepa-stills (I-JEPA still-image world model on STILL frames)
- ran: 2026-09-27 21:57
- verdict: KEEP
- result: ```json
{
  "experiment": "E9 ijepa-stills",
  "device": "cuda",
  "seed": 2718,
  "model_requested": "facebook/ijepa_vitb",
  "model": "facebook/ijepa_vith16_1k",
  "load_notes": {
    "facebook/ijepa_vitb": "load failed: OSError: facebook/ijepa_vitb is not a local folder and is not a valid model identifier listed on 'https://huggingface.co/models'\nIf this is a private repository, make sure to pass a token having permission to this repo either by logging in with `hf auth login` or by passing `token=<your"
  },
  "rooms": [
    "still-solid",
    "moving-testsrc",
    "smpte",
    "moving-testsrc2"
  ],
  "stills_per_room": 12,
  "cells": 48,
  "emb_dim": 1280,
  "still_vs_testsrc_cross_cos": 0.7012,
  "within_still": 1.0,
  "within_testsrc": 0.9996,
  "heldout_gap": 0.2984,
  "tex_vs_motion_axis_corr": -0.3177,
  "verdict": "KEEP"
}
```
- note: I-JEPA loaded via fallback checkpoint (facebook/ijepa_vith16_1k, fp16, emb_dim 1280) — requested facebook/ijepa_vitb 401s on the hub, fallback held. The still-image world model separates STILL frame structure from motion texture: within-still 1.0 / within-testsrc 0.9996, but still-vs-testsrc cross-cos 0.70 (heldout gap 0.298), texture-vs-motion axis correlation -0.32. A real reading on the elephant lane: a room's stable still-identity is distinguishable from its transient motion texture.

## D21 — perception=ledger (imbalance ≡ d_mu falsification)
- ran: 2026-09-27 23:36
- verdict: KILL
- result: ```json
{
  "experiment": "D21 perception=ledger (imbalance ≡ d_mu falsification)",
  "seed": 2718, "device": "cpu", "verdict": "KILL",
  "kernel_room": {"n_heldout": 800, "imbalance_mean": 2.904, "d_mu_mean": 0.260, "max_rel_dev": 0.9599, "spearman": -0.487},
  "harbor_receipt_chain": {"n_heldout": 43, "n_probes_sealed": 215, "imbalance_mean": 1.0, "d_mu_mean": 0.0258, "max_rel_dev": 0.9774},
  "gates": {"G1_decomp_exact": true, "G2_unit_collapse": true, "G3_identity_both_rooms": false}
}
```
- note: imbalance ≡ d_mu is CONDITIONAL (holds only on the unit sphere, ‖before‖=‖after‖=1), which superinstance-old compressed away. Real heldout receipt-chain edges: max |imb−d_mu|/imb = 0.96–0.98 ≫ 1e-9 gate. Two rooms fail OPPOSITELY: kernel room 86.7% radial (magnitude drift), harbor receipt-chain 94.9% directional (perception delta ~38× smaller than sealed surprise). Spearman ρ(imb,d_mu) = −0.487 (anti-correlated) room A, undefined room B. Controls: G1 identity-1 decomposition exact (6.8e-15), G2 unit-collapse reproduces identity (4.4e-16) — the gap is real. The room's temperature ≠ the substrate's transaction history; two projections coinciding only on the unit sphere.

## D22 — ternary-forgiveness (forgiveness-via-privacy-noise falsification)
- ran: 2026-09-27 23:52
- verdict: KILL
- note: the claimed 0.5–0.7% trit-flip sweet spot is reproduced by NEITHER flip model. honest DP (signal-independent flip) leaves accuracy flat at chance 1/3 (spread 2.4e-3) — no recovery; signal-correlated "reveal" is monotonically increasing (0.338→0.368 at 5%) — no upper "drown" bound. Non-monotonic sweet spot: not detected. The synergy-miner's composition (DP-flip = forgiveness tunneling) is a good IDEA but its falsifiable band is not a generic property of trit-flip noise — it needs the ternary-engine forgiveness dynamics, absent from the claim's description and the local repos (ternary-forgiveness is an empty placeholder).

## D15c — tone-channel generalization, holdout=hold (full pass)
- ran: 2026-09-28 00:23
- verdict: **KILL**
- result: ```json
{
  "experiment": "D15c tone-channel generalization (held-out tone classes)",
  "vision_layer": "Layer 3 reading gate (text-model proxy; follows D15b KEEP)",
  "changes_vs_d15b": [
    "tone-class holdout: training trajectories sampled from 3 classes only (d, f, u); gold 'h' (hold) absent from every train pair (asserted per pair)",
    "gate metric re-anchored: pooled per-token accuracy over held-out-class positions of the all-four-class gate set (tuned>=0.80 AND base<=0.30)",
    "gate set keeps D15b's exact all-four-class trajectory distribution on unseen texts, so held-position accuracy isolates class transfer",
    "added seen-only eval set (3-class trajectories, unseen texts): replication axis separating 'read broken by restricted training' from 'read intact but cannot emit the unseen code'",
    "per-class accuracy table + held-code emission rate reported for both arms",
    "prompt UNCHANGED from D15b (rule + worked examples are public, including one held-class demonstration \u2014 part of the recipe under test)"
  ],
  "mode": "full",
  "device": "cuda",
  "seed": 2718,
  "holdout": {
    "name": "hold",
    "momentum": 3,
    "code": "h",
    "seen_classes": [
      "d",
      "f",
      "u"
    ],
    "rule_visibility": "public: RULE names all four codes and WORKED EXAMPLES show one demonstration of each; what is held out is every gold demonstration of 'h' in training gradients"
  },
  "model_used": "Qwen/Qwen2.5-3B-Instruct",
  "model_candidates_tried": [],
  "fallback_note": null,
  "quant": "nf4-4bit",
  "quant_note": "4-bit NF4 double-quant, bf16 compute",
  "qlora": {
    "r": 16,
    "alpha": 32,
    "dropout": 0.05,
    "target_modules": [
      "q_proj",
      "k_proj",
      "v_proj",
      "o_proj",
      "gate_proj",
      "up_proj",
      "down_proj"
    ],
    "grad_checkpointing": true,
    "batch": 1,
    "grad_accum": 8,
    "seq_max": 1024,
    "lr": 0.0002
  },
  "curriculum": {
    "schedule": [
      [
        "A"
      ],
      [
        "A",
        "B"
      ],
      [
        "A",
        "B",
        "C"
      ],
      [
        "A",
        "B",
        "C"
      ],
      [
        "A",
        "B",
        "C"
      ]
    ],
    "stage_truncs": {
      "A": 12,
      "B": 24,
      "C": null
    },
    "worked_example_bytes": {
      "86": "d",
      "ca": "f",
      "47": "u",
      "05": "h"
    }
  },
  "data": {
    "source": "qthe_codec.encode() seeded foundry (~/projects/qthe-codec)",
    "split": "BY TEXT (held-out texts never in training) + BY CLASS (held-out class 'h' never in any training gold trajectory; asserted per pair)",
    "pool_texts": 44,
    "held_texts": 20,
    "train_texts": 24,
    "stage_sizes": {
      "A": 150,
      "B": 150,
      "C": 150
    },
    "trunc_a_chars": 12,
    "trunc_b_chars": 24,
    "train_pairs": 450,
    "gate_pairs_all4classes": 60,
    "seen_pairs_3classes": 40,
    "held_positions_in_gate_set": 678,
    "codec_roundtrip": "asserted on every pair"
  },
  "base_eval_gate": {
    "n": 60,
    "acc": 0.0639,
    "exact_match": 0.0,
    "wellformed_rate": 0.0,
    "mean_stream_bytes": 39.7,
    "held_class_acc": 0.0516,
    "held_class_positions": 678,
    "held_code_rate_gold": 0.2846,
    "held_code_rate_pred": 0.246,
    "per_class_acc": {
      "d": {
        "acc": 0.0709,
        "n": 508
      },
      "f": {
        "acc": 0.0852,
        "n": 587
      },
      "u": {
        "acc": 0.0608,
        "n": 609
      },
      "h": {
        "acc": 0.0516,
        "n": 678
      }
    },
    "seconds": 42.9,
    "samples": [
      {
        "id": "gate-The Canary H-0",
        "gold": "f f f f f f f h h h h h h h h h h h d d d d u u u u u u u u u u u",
        "pred": "d f u h",
        "raw": "d f u h",
        "acc": 0.03
      },
      {
        "id": "gate-The Canary H-1",
        "gold": "h h h h h h h u u u u u u u u u u u u u u u u u u u u u u u u u u",
        "pred": "d f u h",
        "raw": "d f u h",
        "acc": 0.03
      },
      {
        "id": "gate-the canary h-1",
        "gold": "h h h h h h h h f f f f f f f f f f d d d d d d d d d d u u u u u u u u u u",
        "pred": "d f u h",
        "raw": "d f u h",
        "acc": 0.026
      },
      {
        "id": "gate-the canary h-2",
        "gold": "f f f f f f f f f f f f f h h h h h h h h h h h h h h h h h h h h h h h h h",
        "pred": "d f u h",
        "raw": "d f u h",
        "acc": 0.026
      }
    ]
  },
  "base_eval_seen": {
    "n": 40,
    "acc": 0.0922,
    "exact_match": 0.0,
    "wellformed_rate": 0.0,
    "mean_stream_bytes": 39.7,
    "held_class_acc": null,
    "held_class_positions": 0,
    "held_code_rate_gold": 0.0,
    "held_code_rate_pred": 0.2205,
    "per_class_acc": {
      "d": {
        "acc": 0.0885,
        "n": 531
      },
      "f": {
        "acc": 0.1142,
        "n": 569
      },
      "u": {
        "acc": 0.0984,
        "n": 488
      },
      "h": {
        "acc": null,
        "n": 0
      }
    },
    "seconds": 39.8,
    "samples": []
  },
  "tuned_eval_gate": {
    "n": 60,
    "acc": 0.6564,
    "exact_match": 0.0,
    "wellformed_rate": 0.0333,
    "mean_stream_bytes": 39.7,
    "held_class_acc": 0.0,
    "held_class_positions": 678,
    "held_code_rate_gold": 0.2846,
    "held_code_rate_pred": 0.0,
    "per_class_acc": {
      "d": {
        "acc": 0.937,
        "n": 508
      },
      "f": {
        "acc": 0.9506,
        "n": 587
      },
      "u": {
        "acc": 0.8539,
        "n": 609
      },
      "h": {
        "acc": 0.0,
        "n": 678
      }
    },
    "seconds": 716.7,
    "samples": [
      {
        "id": "gate-The Canary H-0",
        "gold": "f f f f f f f h h h h h h h h h h h d d d d u u u u u u u u u u u",
        "pred": "f f f f f f f f f f f f f f f u u u d d d d d d d d d u u u u u u",
        "raw": "f f f f f f f f f f f f f f f u u u d d d d d d d d d u u u u u u u u u u u",
        "acc": 0.515
      },
      {
        "id": "gate-The Canary H-1",
        "gold": "h h h h h h h u u u u u u u u u u u u u u u u u u u u u u u u u u",
        "pred": "f f f f f f f u u u u u u u u u u u u u u u u u u u u u u u u u u",
        "raw": "f f f f f f f u u u u u u u u u u u u u u u u u u u u u u u u u u u u u u u",
        "acc": 0.788
      },
      {
        "id": "gate-the canary h-1",
        "gold": "h h h h h h h h f f f f f f f f f f d d d d d d d d d d u u u u u u u u u u",
        "pred": "f f f f f f f f f f f f f f f f f f d d d d d d d d d d d d d d d d d d d u",
        "raw": "f f f f f f f f f f f f f f f f f f d d d d d d d d d d d d d d d d d d d u u u u u u u u u u u u u u u u u u u u u u u ",
        "acc": 0.553
      },
      {
        "id": "gate-the canary h-2",
        "gold": "f f f f f f f f f f f f f h h h h h h h h h h h h h h h h h h h h h h h h h",
        "pred": "f f f f f f f f f f f f f f f f f f f f u u u u u u u u u u u u u u u u u d",
        "raw": "f f f f f f f f f f f f f f f f f f f f u u u u u u u u u u u u u u u u u d d d d d d d d d d",
        "acc": 0.342
      }
    ]
  },
  "tuned_eval_seen": {
    "n": 40,
    "acc": 0.9275,
    "exact_match": 0.0,
    "wellformed_rate": 0.05,
    "mean_stream_bytes": 39.7,
    "held_class_acc": null,
    "held_class_positions": 0,
    "held_code_rate_gold": 0.0,
    "held_code_rate_pred": 0.0,
    "per_class_acc": {
      "d": {
        "acc": 0.9228,
        "n": 531
      },
      "f": {
        "acc": 0.935,
        "n": 569
      },
      "u": {
        "acc": 0.9078,
        "n": 488
      },
      "h": {
        "acc": null,
        "n": 0
      }
    },
    "seconds": 453.4,
    "samples": []
  },
  "held_class_margin": -0.0516,
  "preregistered": {
    "tuned_held_acc_gte": 0.8,
    "base_held_acc_lte": 0.3,
    "metric": "pooled per-token accuracy over held-out-class positions of the gate set",
    "chance": 0.25
  },
  "train": {
    "optimizer_steps_total": 225,
    "per_epoch": [
      {
        "epoch": 1,
        "stages": [
          "A"
        ],
        "pairs": 150,
        "steps": 19,
        "mean_loss": 0.8252,
        "losses": [
          3.4878,
          0.939,
          1.5643,
          0.8343,
          0.8082,
          0.7676,
          0.5849,
          0.6104,
          0.5828,
          0.5229,
          0.669,
          0.5978,
          0.5248,
          0.5864,
          0.6016,
          0.517,
          0.4715,
          0.5394,
          0.4687
        ]
      },
      {
        "epoch": 2,
        "stages": [
          "A",
          "B"
        ],
        "pairs": 300,
        "steps": 38,
        "mean_loss": 0.3591,
        "losses": [
          0.4761,
          0.406,
          0.4042,
          0.4781,
          0.4217,
          0.5458,
          0.4463,
          0.4296,
          0.3972,
          0.3823,
          0.3888,
          0.3369,
          0.3585,
          0.4116,
          0.4278,
          0.3517,
          0.3547,
          0.3658,
          0.3789,
          0.4437,
          0.4042,
          0.38,
          0.3337,
          0.3163,
          0.3105,
          0.2775,
          0.2884,
          0.2893,
          0.2969,
          0.315,
          0.2624,
          0.2501,
          0.303,
          0.2709,
          0.2942,
          0.2375,
          0.2593,
          0.3523
        ]
      },
      {
        "epoch": 3,
        "stages": [
          "A",
          "B",
          "C"
        ],
        "pairs": 450,
        "steps": 56,
        "mean_loss": 0.2484,
        "losses": [
          0.3797,
          0.3026,
          0.3118,
          0.3234,
          0.3484,
          0.3381,
          0.3109,
          0.3044,
          0.2674,
          0.3114,
          0.3229,
          0.2199,
          0.2877,
          0.3484,
          0.4089,
          0.282,
          0.3056,
          0.29,
          0.3222,
          0.2818,
          0.2339,
          0.2606,
          0.1798,
          0.1852,
          0.1828,
          0.1528,
          0.2451,
          0.1929,
          0.1833,
          0.2066,
          0.1242,
          0.2033,
          0.2222,
          0.169,
          0.1704,
          0.1696,
          0.1401,
          0.4808,
          0.4514,
          0.286,
          0.2711,
          0.2589,
          0.209,
          0.2017,
          0.214,
          0.2205,
          0.202,
          0.2294,
          0.1929,
          0.2066,
          0.2147,
          0.1323,
          0.1615,
          0.1351,
          0.2013,
          0.152
        ]
      },
      {
        "epoch": 4,
        "stages": [
          "A",
          "B",
          "C"
        ],
        "pairs": 450,
        "steps": 56,
        "mean_loss": 0.1469,
        "losses": [
          0.3871,
          0.1921,
          0.2105,
          0.3073,
          0.1756,
          0.2085,
          0.2472,
          0.2503,
          0.189,
          0.1827,
          0.1305,
          0.0883,
          0.1268,
          0.2677,
          0.133,
          0.1322,
          0.0471,
          0.0922,
          0.1523,
          0.1835,
          0.0767,
          0.1269,
          0.1172,
          0.1129,
          0.1407,
          0.0672,
          0.1168,
          0.1165,
          0.0961,
          0.0827,
          0.0559,
          0.0919,
          0.0909,
          0.1175,
          0.0731,
          0.0566,
          0.0518,
          0.2797,
          0.3092,
          0.1729,
          0.1849,
          0.2166,
          0.1636,
          0.159,
          0.1361,
          0.1467,
          0.127,
          0.115,
          0.1188,
          0.1268,
          0.1168,
          0.0935,
          0.1145,
          0.0916,
          0.1005,
          0.1556
        ]
      },
      {
        "epoch": 5,
        "stages": [
          "A",
          "B",
          "C"
        ],
        "pairs": 450,
        "steps": 56,
        "mean_loss": 0.1105,
        "losses": [
          0.2528,
          0.0358,
          0.1496,
          0.1349,
          0.0723,
          0.0967,
          0.0903,
          0.0823,
          0.0188,
          0.0196,
          0.0282,
          0.0135,
          0.0642,
          0.0761,
          0.091,
          0.0498,
          0.013,
          0.0704,
          0.2223,
          0.5017,
          0.2697,
          0.1335,
          0.0413,
          0.0902,
          0.159,
          0.0631,
          0.0705,
          0.0875,
          0.0592,
          0.0605,
          0.0721,
          0.037,
          0.0545,
          0.054,
          0.0625,
          0.0365,
          0.0378,
          0.1432,
          0.1835,
          0.1471,
          0.1431,
          0.1748,
          0.2074,
          0.2023,
          0.1526,
          0.1316,
          0.1437,
          0.1217,
          0.1331,
          0.1386,
          0.1263,
          0.1249,
          0.113,
          0.1202,
          0.1258,
          0.0841
        ]
      }
    ],
    "trainable_params": 29933568,
    "seconds": 2530.4
  },
  "adapter_path": "/home/eileen/projects/quilt-gpu-lab/results/d15c_adapter_full_hold",
  "peak_vram_mib": 4240.8,
  "wall_seconds": 3818.2,
  "versions": {
    "torch": "2.14.0+cu126",
    "transformers": "5.17.0",
    "peft": "0.21.0",
    "bitsandbytes": "0.50.2"
  },
  "verdict": "KILL",
  "reason": "tuned fails to beat base on the held-out class (-0.0516): the 0.94 read does not transfer to classes absent from training gradients \u2014 the adapter memorizes seen-class output patterns rather than executing the rule",
  "note": "SMOKE numbers are pipeline proof on the 0.5B proxy, not the hypothesis test. FULL-SCALE RECIPE (D15C_FULL=1, D15C_HOLDOUT=hold): base chain Qwen2.5-3B -> 1.5B (4-bit NF4 double-quant; 3B kept only if free VRAM after load >= 1500 MiB); LoRA r=16 alpha=32 dropout=0.05 on q/k/v/o/gate/up/down; grad checkpointing (use_reentrant=False); batch 1 x grad-accum 8; seq<=1024; lr 2e-4 AdamW; 5 curriculum epochs over 450 seen-class-only pairs (A=12-char, B=24-char, C=full, 150 each): ep1=A, ep2=A+B, ep3-5=all; eval on 60 all-four-class gate pairs (20 unseen texts x 3 draws; held-class positions are the gate) + 40 seen-class pairs (replication axis). Gate: tuned held-class acc >= 0.8 AND base <= 0.3 (chance 0.25), pooled over held positions; KILL iff tuned <= base; else INCONCLUSIVE \u2014 same convention as D15/D15b. Prompt identical to D15b for BOTH arms (public rule + 4 worked examples), so the ONLY difference from D15b is the absence of held-class training gradients. Expected VRAM ~4-4.5 GB peak on 3B, ~2.5-3.5 h wall on the RTX 4050 6 GB; runner.py's Guard hard-codes 1800 s \u2014 D15b full needed 5168 s, so schedule accordingly. Other lanes contend: preflight floor 1024 MiB free / 80 C. This pass quant: nf4-4bit."
}
```
- note: tuned fails to beat base on the held-out class (-0.0516): the 0.94 read does not transfer to classes absent from training gradients — the adapter memorizes seen-class output patterns rather than executing the rule

## E12 — room-dial reader (I-JEPA reads the elephant dials)
- ran: 2026-09-28 00:25
- verdict: KEEP
- note: frozen I-JEPA (facebook/ijepa_vith16_1k) linearly reads STAGED mood/volume/presence at R² 0.811/0.962/0.948 (k=64, leave-one-room-out ridge; room-level 0.890/0.972/0.937). Controls: luminance Spearman correlates only with mood (0.92), NOT volume (0.08) or presence (0.18); raw-pixel probe FAILS volume (-0.77) and presence (0.16) — the embedding genuinely captures volume+presence beyond the trivial correlate. On REAL E9 rooms (armA): dial R² 0.48/0.43/0.47, tertile 0.73-0.75. Caveat: carriers are staged (deliberately varied to match dials), not natural vibes; presence labels compressed to v0 ceiling. Natural-room test is the real claim, still open.

## E13 — nonlinear-carrier dial read (falsify E12's KEEP)
- ran: 2026-09-28 01:05
- verdict: INCONCLUSIVE
- note: E12's linear read is NOT purely a staging artifact, but only for ONE of the three dials. Arm L (E12's linear staging) replicates KEEP (control valid); Arm N1 (mild bent sigmoid warp, curvature 0.519) also KEEPs. The PRIMARY Arm N2 (roomgen's frozen nonlinear mixture, curvature 0.471, certified live + nonaffine + injective) is INCONCLUSIVE: mood survives (still-LORO R² 0.537), but volume (-0.100) and presence (0.270) die under nonlinear folding — 1/3 dials, not the clean 0/3 that KILL requires. The seam is exactly where E12's own controls pointed: luminance Spearman-correlated with mood (0.92) but not volume (0.08) or presence (0.18). Mood rides a low-level robust feature (colour temp survives folding); volume/presence ride higher-order visual structure the mixture scrambles. So: mood-read = real, volume/presence-read = linear-staging artifact. Next falsification: does a NONLINEAR reader (small MLP, not ridge) recover volume/presence from N2 embeddings — i.e. is the loss in the READER or the EMBEDDING?
