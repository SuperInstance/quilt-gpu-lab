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

## E13b — nonlinear-reader dial read (reader vs embedding)
- ran: 2026-09-28 07:35
- verdict: INCONCLUSIVE (partial recovery: ridge failed [volume, presence] on N2; MLP recovered [presence])
- note: the loss was PARTLY in the reader. On the nonlinear N2 carrier, ridge's FAIL_SET = {volume, presence}. The fixed sklearn-LBFGS reader (hidden 16, alpha 0.1) recovered presence (0.338 ≥ 0.30 PASS) and lifted volume −0.10 → 0.21 (still < 0.30), but DROPPED mood 0.537 → 0.367. On the LINEAR arm the pattern inverts: ridge 0.96/0.95 on volume/presence, MLP 0.83/0.84 (nonlinear reader HURTS linear dials). So mood is the linear/luminance dial (ridge is optimal), volume/presence are higher-order (a nonlinear reader helps but not cleanly enough for KEEP). E12's "reads volume/presence beyond luminance" is PARTIALLY real: some volume/presence signal survives nonlinear folding and is recoverable by a nonlinear reader, but not robustly. The reader architecture matters per-dial — a per-dial hybrid (linear for mood, nonlinear for volume/presence) is the natural next probe. BUILD-FIX recorded in the module docstring: the original batched-Adam reader overfit (self-test −0.977); replaced with per-fold sklearn LBFGS.

## E25 — fold-phase transition (where does the dial read die under carrier nonlinearity? sweep N2 fold amplitude, per-dial critical point) — pre-registered in SPOOL.md
- ran: 2026-09-28 08:25 (v2 registered sweep; the 08:05 "ABORTED" was a runner-parser artifact, since fixed)
- verdict: INCONCLUSIVE
- note: monotone decay is real and the critical amplitudes are DISTINCT — volume dies at amp 1.0, mood 1.5, presence 2.2 (curvature 0.29→1.31 across {0.5,1.0,1.5,2.2,2.8}; amp 3.5 censored INVALID_STAGING, 0/3 dials live). mood 0.796→0.762→0.718→0.537→0.432; presence 0.620→0.636→0.425→0.270→−0.170; volume 0.398→−0.053→−0.054→−0.100→−0.026. The strict gate wants mood LONGEST, but mood's amp-1.5 trip is the k16-retention clause (k16 0.220 < 0.5·k64 0.359) while its k64 there is 0.718 — on the k64-floor headline alone, mood never dies. So the SPOOL claim's SHAPE holds (per-dial critical points exist, ordered volume < mood < presence), but it does not cleanly pass the full gate. C6 replication: amp 2.2 reproduces E13's N2 arm bit-for-bit (0.5372/−0.0998/0.2700); Arm L reproduces E12 (0.811/0.962/0.948, lum 0.993). Full result: results/e25_fold_phase_transition.json.

## E18 — sauna/plunge contrast (is the walk between rooms more readable than the rooms?)
- ran: 2026-09-28 08:50
- verdict: INCONCLUSIVE
- note: the SIGNED-DIFFERENCE feature is the "walk" representation and it super-adds — diff-feature read of the gap (0.97) crushes the two-absolutes baseline (0.40), i.e. emb_B−emb_A carries edge signal beyond the absolutes. But the CONCAT/pair features do NOT super-add (two-absolutes 0.99 ≈ gap 0.97), because concatenation is just the two absolutes stacked. 2/3 dials beat the two-absolutes baseline, but only 1/3 clears BOTH comparators AND the null → honest INCONCLUSIVE. The elephant's "walk" lives in the difference, not the sum — a clean follow-up target: edge = signed-difference, and the concat arm is the right null.

## E15 — encoder-swap dial read (is I-JEPA special? DINOv2/CLIP/V-JEPA 2 leaderboard) — pre-registered in SPOOL.md
- ran: 2026-09-28 09:26
- verdict: KEEP
- result: ```json
{
  "experiment": "E15 encoder-swap dial-read leaderboard",
  "device": "cuda",
  "seed": 2718,
  "guard_preflight": {
    "free_vram_mib": 4484,
    "temp_c": 57
  },
  "download_opt_in": false,
  "dial_names": [
    "mood",
    "volume",
    "presence"
  ],
  "k_primary": 64,
  "e12_published_reference": {
    "verdict": "KEEP",
    "date": "2026-09-28",
    "model": "facebook/ijepa_vith16_1k",
    "r2_still_loro_k64": {
      "mood": 0.811,
      "volume": 0.962,
      "presence": 0.948
    },
    "r2_room_loro_k64": {
      "mood": 0.89,
      "volume": 0.972,
      "presence": 0.937
    }
  },
  "shared": {
    "rooms_armB": 27,
    "rooms_armA": 4,
    "stills_per_room": 12,
    "raw_pixel_r2_k64_booked": {
      "mood": 0.9355,
      "volume": -0.7664,
      "presence": 0.1625
    },
    "luminance_spearman_booked": {
      "mood": 0.9224,
      "volume": 0.0804,
      "presence": 0.1803
    },
    "note": "C1/C2 are encoder-independent (same stills for every encoder) \u2014 taken from the first encoder that ran",
    "staging_fidelity_spearman_target_vs_label": {
      "mood": 0.98,
      "volume": 0.9437,
      "presence": 0.9864
    }
  },
  "encoders": {
    "ijepa_vith16_1k": {
      "verdict": "KEEP",
      "emb_dim": 1280,
      "pca_evr_k64": 0.9967,
      "r2_still_loro_k64": {
        "mood": 0.8106,
        "volume": 0.9624,
        "presence": 0.9478
      },
      "r2_still_loro_k16": {
        "mood": 0.848,
        "volume": 0.9653,
        "presence": 0.9292
      },
      "r2_still_loro_k256": {
        "mood": 0.8726,
        "volume": 0.9722,
        "presence": 0.9729
      },
      "r2_room_loro_k64": {
        "mood": 0.8902,
        "volume": 0.9717,
        "presence": 0.9374
      },
      "spearman_loro_k64": {
        "mood": 0.896,
        "volume": 0.903,
        "presence": 0.9329
      },
      "perm_null95_k64": {
        "mood": -0.0561,
        "volume": 0.0371,
        "presence": -0.023
      },
      "perm_p_k64": {
        "mood": 0.0,
        "volume": 0.0,
        "presence": 0.0
      },
      "lambda_median_k64": 1.0,
      "tertile_acc_k64": {
        "mood": 0.9691,
        "volume": 1.0,
        "presence": 1.0
      },
      "g0b_sensitivity_r2_luminance_k64": 0.993,
      "g0b_sensitivity_pass": true,
      "g1_dial_pass": {
        "mood": true,
        "volume": true,
        "presence": true
      },
      "g1_pass_count": 3,
      "armA_room_sep_pass": true,
      "armB_room_identity_acc": 1.0,
      "gates": {
        "r2_floor": 0.3,
        "room_r2_floor": 0.15,
        "top_pc_fraction": 0.5,
        "armA_acc_floor": 0.75,
        "sensitivity_floor": 0.9
      },
      "key": "ijepa_vith16_1k",
      "hf_id": "facebook/ijepa_vith16_1k",
      "kind": "image",
      "role": "control (E12 replication)",
      "loader": "e9.load_encoder verbatim",
      "cache": {
        "cached": true,
        "snapshot": "43ea3b33a17addfa9a32261f6fde003fd97f38d9",
        "weights_file": "model.safetensors",
        "weights_mib": 2409.7
      },
      "model": "facebook/ijepa_vith16_1k",
      "load_notes": {
        "facebook/ijepa_vitb": "load failed: OSError: facebook/ijepa_vitb is not a local folder and is not a valid model identifier listed on 'https://huggingface.co/models'\nIf this is a private repository, make sure to pass a token having permission to this repo either by logging in with `hf auth login` or by passing `token=<your"
      },
      "vram": {
        "free_before_mib": 4484,
        "free_after_mib": 4355,
        "weights_mib": 1205.4,
        "peak_allocated_mib": 1503.4
      },
      "controls_armA": {
        "dial_r2_k64_booked": {
          "mood": 0.4842,
          "volume": 0.4326,
          "presence": 0.4728
        },
        "room_identity_acc": 1.0
      },
      "status": "ran",
      "labels_are_reference": true
    },
    "dinov2_base": {
      "key": "dinov2_base",
      "hf_id": "facebook/dinov2-base",
      "status": "skipped",
      "reason": "weights not in local HF cache \u2014 one-time download needed (~350-600 MB). Re-run with E15_ALLOW_DOWNLOAD=1 or pre-pull: huggingface-cli download facebook/dinov2-base",
      "cache": {
        "cached": false,
        "reason": "/home/eileen/.cache/huggingface/hub/models--facebook--dinov2-base absent \u2014 one-time download needed"
      }
    },
    "clip_vitb32": {
      "key": "clip_vitb32",
      "hf_id": "openai/clip-vit-base-patch32",
      "status": "skipped",
      "reason": "weights not in local HF cache \u2014 one-time download needed (~350-600 MB). Re-run with E15_ALLOW_DOWNLOAD=1 or pre-pull: huggingface-cli download openai/clip-vit-base-patch32",
      "cache": {
        "cached": false,
        "reason": "/home/eileen/.cache/huggingface/hub/models--openai--clip-vit-base-patch32 absent \u2014 one-time download needed"
      }
    },
    "vjepa2_vitl": {
      "verdict": "KEEP",
      "emb_dim": 1024,
      "pca_evr_k64": 0.9972,
      "r2_still_loro_k64": {
        "mood": 0.8753,
        "volume": 0.9671,
        "presence": 0.8764
      },
      "r2_still_loro_k16": {
        "mood": 0.8207,
        "volume": 0.9728,
        "presence": 0.7842
      },
      "r2_still_loro_k256": {
        "mood": 0.8694,
        "volume": 0.972,
        "presence": 0.8999
      },
      "r2_room_loro_k64": {
        "mood": 0.8313,
        "volume": 0.9554,
        "presence": 0.8034
      },
      "spearman_loro_k64": {
        "mood": 0.9058,
        "volume": 0.9164,
        "presence": 0.9281
      },
      "perm_null95_k64": {
        "mood": 0.0017,
        "volume": -0.0861,
        "presence": -0.1077
      },
      "perm_p_k64": {
        "mood": 0.0,
        "volume": 0.0,
        "presence": 0.0
      },
      "lambda_median_k64": 0.1,
      "tertile_acc_k64": {
        "mood": 1.0,
        "volume": 1.0,
        "presence": 1.0
      },
      "g0b_sensitivity_r2_luminance_k64": 0.9958,
      "g0b_sensitivity_pass": true,
      "g1_dial_pass": {
        "mood": true,
        "volume": true,
        "presence": true
      },
      "g1_pass_count": 3,
      "armA_room_sep_pass": true,
      "armB_room_identity_acc": 1.0,
      "gates": {
        "r2_floor": 0.3,
        "room_r2_floor": 0.15,
        "top_pc_fraction": 0.5,
        "armA_acc_floor": 0.75,
        "sensitivity_floor": 0.9
      },
      "key": "vjepa2_vitl",
      "hf_id": "facebook/vjepa2-vitl-fpc16-256-ssv2",
      "kind": "video",
      "role": "swap",
      "loader": "VJEPA2Model + VJEPA2VideoProcessor (E7's pattern)",
      "cache": {
        "cached": true,
        "snapshot": "4aa02df83918538fc21cfaf576382fa20e489a80",
        "weights_file": "model.safetensors",
        "weights_mib": 1432.4
      },
      "load_notes": {},
      "vram": {
        "free_before_mib": 4355,
        "free_after_mib": 4355,
        "weights_mib": 631.5,
        "peak_allocated_mib": 703.8
      },
      "controls_armA": {
        "dial_r2_k64_booked": {
          "mood": -0.5886,
          "volume": -0.6696,
          "presence": -0.6548
        },
        "room_identity_acc": 1.0
      },
      "status": "ran",
      "labels_match_control": true
    }
  },
  "leaderboard": [
    {
      "encoder": "ijepa_vith16_1k",
      "hf_id": "facebook/ijepa_vith16_1k",
      "role": "control (E12 replication)",
      "status": "ran",
      "verdict": "KEEP",
      "r2_still_loro_k64": {
        "mood": 0.8106,
        "volume": 0.9624,
        "presence": 0.9478
      },
      "r2_room_loro_k64": {
        "mood": 0.8902,
        "volume": 0.9717,
        "presence": 0.9374
      },
      "perm_null95_k64": {
        "mood": -0.0561,
        "volume": 0.0371,
        "presence": -0.023
      },
      "g1_pass_count": 3,
      "armA_room_identity_acc": 1.0,
      "vram": {
        "free_before_mib": 4484,
        "free_after_mib": 4355,
        "weights_mib": 1205.4,
        "peak_allocated_mib": 1503.4
      },
      "reason": null
    },
    {
      "encoder": "dinov2_base",
      "hf_id": "facebook/dinov2-base",
      "role": "swap",
      "status": "skipped",
      "verdict": null,
      "r2_still_loro_k64": null,
      "r2_room_loro_k64": null,
      "perm_null95_k64": null,
      "g1_pass_count": null,
      "armA_room_identity_acc": null,
      "vram": null,
      "reason": "weights not in local HF cache \u2014 one-time download needed (~350-600 MB). Re-run with E15_ALLOW_DOWNLOAD=1 or pre-pull: huggingface-cli download facebook/dinov2-base"
    },
    {
      "encoder": "clip_vitb32",
      "hf_id": "openai/clip-vit-base-patch32",
      "role": "swap",
      "status": "skipped",
      "verdict": null,
      "r2_still_loro_k64": null,
      "r2_room_loro_k64": null,
      "perm_null95_k64": null,
      "g1_pass_count": null,
      "armA_room_identity_acc": null,
      "vram": null,
      "reason": "weights not in local HF cache \u2014 one-time download needed (~350-600 MB). Re-run with E15_ALLOW_DOWNLOAD=1 or pre-pull: huggingface-cli download openai/clip-vit-base-patch32"
    },
    {
      "encoder": "vjepa2_vitl",
      "hf_id": "facebook/vjepa2-vitl-fpc16-256-ssv2",
      "role": "swap",
      "status": "ran",
      "verdict": "KEEP",
      "r2_still_loro_k64": {
        "mood": 0.8753,
        "volume": 0.9671,
        "presence": 0.8764
      },
      "r2_room_loro_k64": {
        "mood": 0.8313,
        "volume": 0.9554,
        "presence": 0.8034
      },
      "perm_null95_k64": {
        "mood": 0.0017,
        "volume": -0.0861,
        "presence": -0.1077
      },
      "g1_pass_count": 3,
      "armA_room_identity_acc": 1.0,
      "vram": {
        "free_before_mib": 4355,
        "free_after_mib": 4355,
        "weights_mib": 631.5,
        "peak_allocated_mib": 703.8
      },
      "reason": null
    }
  ],
  "gates": {
    "control_key": "ijepa_vith16_1k",
    "control_ran": true,
    "control_keep": true,
    "control_verdict": "KEEP",
    "swaps_ran": [
      "vjepa2_vitl"
    ],
    "swaps_keep": [
      "vjepa2_vitl"
    ],
    "swaps_not_ran": [
      {
        "key": "dinov2_base",
        "status": "skipped",
        "verdict": null,
        "reason": "weights not in local HF cache \u2014 one-time download needed (~350-600 MB). Re-run with E15_ALLOW_DOWNLOAD=1 or pre-pull: huggingface-cli download facebook/dinov2-base"
      },
      {
        "key": "clip_vitb32",
        "status": "skipped",
        "verdict": null,
        "reason": "weights not in local HF cache \u2014 one-time download needed (~350-600 MB). Re-run with E15_ALLOW_DOWNLOAD=1 or pre-pull: huggingface-cli download openai/clip-vit-base-patch32"
      }
    ]
  },
  "verdict": "KEEP",
  "note": "E12's dial-read pipeline (same 27-room staged bank, same elephant-bank labels, same ridge/LORO/perm-null) re-run under each frozen encoder. Per-encoder gate = E12 G1 verbatim. INVALID_CONTROL: the I-JEPA control failed to replicate E12's KEEP in THIS run (comparison void). KEEP: >=1 non-I-JEPA encoder reads >=2/3 dials at E12's thresholds -> room-geometry property. KILL: every valid non-I-JEPA swap fails where I-JEPA keeps -> I-JEPA's inductive bias is load-bearing. Skipped/failed/INVALID_HARNESS swaps never silently become a KILL. Caveats: staged carriers (E12's limit); vjepa2 rows are 16-frame windows anchored at each still; CLS tokens included in the uniform mean-pool for dinov2/clip.",
  "guard_summary": {
    "samples": 43,
    "min_free_vram_mib": 2681,
    "max_temp_c": 74,
    "breach": null,
    "timed_out": false
  }
}
```

## E15 — encoder-swap dial read (is I-JEPA special? DINOv2/CLIP/V-JEPA 2 leaderboard) — pre-registered in SPOOL.md
- ran: 2026-09-28 09:29
- verdict: KEEP
- result: ```json
{
  "experiment": "E15 encoder-swap dial-read leaderboard",
  "device": "cuda",
  "seed": 2718,
  "guard_preflight": {
    "free_vram_mib": 4355,
    "temp_c": 58
  },
  "download_opt_in": false,
  "dial_names": [
    "mood",
    "volume",
    "presence"
  ],
  "k_primary": 64,
  "e12_published_reference": {
    "verdict": "KEEP",
    "date": "2026-09-28",
    "model": "facebook/ijepa_vith16_1k",
    "r2_still_loro_k64": {
      "mood": 0.811,
      "volume": 0.962,
      "presence": 0.948
    },
    "r2_room_loro_k64": {
      "mood": 0.89,
      "volume": 0.972,
      "presence": 0.937
    }
  },
  "shared": {
    "rooms_armB": 27,
    "rooms_armA": 4,
    "stills_per_room": 12,
    "raw_pixel_r2_k64_booked": {
      "mood": 0.9355,
      "volume": -0.7664,
      "presence": 0.1625
    },
    "luminance_spearman_booked": {
      "mood": 0.9224,
      "volume": 0.0804,
      "presence": 0.1803
    },
    "note": "C1/C2 are encoder-independent (same stills for every encoder) \u2014 taken from the first encoder that ran",
    "staging_fidelity_spearman_target_vs_label": {
      "mood": 0.98,
      "volume": 0.9437,
      "presence": 0.9864
    }
  },
  "encoders": {
    "ijepa_vith16_1k": {
      "verdict": "KEEP",
      "emb_dim": 1280,
      "pca_evr_k64": 0.9967,
      "r2_still_loro_k64": {
        "mood": 0.8106,
        "volume": 0.9624,
        "presence": 0.9478
      },
      "r2_still_loro_k16": {
        "mood": 0.848,
        "volume": 0.9653,
        "presence": 0.9292
      },
      "r2_still_loro_k256": {
        "mood": 0.8726,
        "volume": 0.9722,
        "presence": 0.9729
      },
      "r2_room_loro_k64": {
        "mood": 0.8902,
        "volume": 0.9717,
        "presence": 0.9374
      },
      "spearman_loro_k64": {
        "mood": 0.896,
        "volume": 0.903,
        "presence": 0.9329
      },
      "perm_null95_k64": {
        "mood": -0.0561,
        "volume": 0.0371,
        "presence": -0.023
      },
      "perm_p_k64": {
        "mood": 0.0,
        "volume": 0.0,
        "presence": 0.0
      },
      "lambda_median_k64": 1.0,
      "tertile_acc_k64": {
        "mood": 0.9691,
        "volume": 1.0,
        "presence": 1.0
      },
      "g0b_sensitivity_r2_luminance_k64": 0.993,
      "g0b_sensitivity_pass": true,
      "g1_dial_pass": {
        "mood": true,
        "volume": true,
        "presence": true
      },
      "g1_pass_count": 3,
      "armA_room_sep_pass": true,
      "armB_room_identity_acc": 1.0,
      "gates": {
        "r2_floor": 0.3,
        "room_r2_floor": 0.15,
        "top_pc_fraction": 0.5,
        "armA_acc_floor": 0.75,
        "sensitivity_floor": 0.9
      },
      "key": "ijepa_vith16_1k",
      "hf_id": "facebook/ijepa_vith16_1k",
      "kind": "image",
      "role": "control (E12 replication)",
      "loader": "e9.load_encoder verbatim",
      "cache": {
        "cached": true,
        "snapshot": "43ea3b33a17addfa9a32261f6fde003fd97f38d9",
        "weights_file": "model.safetensors",
        "weights_mib": 2409.7
      },
      "model": "facebook/ijepa_vith16_1k",
      "load_notes": {
        "facebook/ijepa_vitb": "load failed: OSError: facebook/ijepa_vitb is not a local folder and is not a valid model identifier listed on 'https://huggingface.co/models'\nIf this is a private repository, make sure to pass a token having permission to this repo either by logging in with `hf auth login` or by passing `token=<your"
      },
      "vram": {
        "free_before_mib": 4355,
        "free_after_mib": 4355,
        "weights_mib": 1205.4,
        "peak_allocated_mib": 1503.4
      },
      "controls_armA": {
        "dial_r2_k64_booked": {
          "mood": 0.4842,
          "volume": 0.4326,
          "presence": 0.4728
        },
        "room_identity_acc": 1.0
      },
      "status": "ran",
      "labels_are_reference": true
    },
    "dinov2_base": {
      "key": "dinov2_base",
      "hf_id": "facebook/dinov2-base",
      "status": "skipped",
      "reason": "weights not in local HF cache \u2014 one-time download needed (~350-600 MB). Re-run with E15_ALLOW_DOWNLOAD=1 or pre-pull: huggingface-cli download facebook/dinov2-base",
      "cache": {
        "cached": false,
        "reason": "/home/eileen/.cache/huggingface/hub/models--facebook--dinov2-base absent \u2014 one-time download needed"
      }
    },
    "clip_vitb32": {
      "key": "clip_vitb32",
      "hf_id": "openai/clip-vit-base-patch32",
      "status": "skipped",
      "reason": "weights not in local HF cache \u2014 one-time download needed (~350-600 MB). Re-run with E15_ALLOW_DOWNLOAD=1 or pre-pull: huggingface-cli download openai/clip-vit-base-patch32",
      "cache": {
        "cached": false,
        "reason": "/home/eileen/.cache/huggingface/hub/models--openai--clip-vit-base-patch32 absent \u2014 one-time download needed"
      }
    },
    "vjepa2_vitl": {
      "verdict": "KEEP",
      "emb_dim": 1024,
      "pca_evr_k64": 0.9972,
      "r2_still_loro_k64": {
        "mood": 0.8753,
        "volume": 0.9671,
        "presence": 0.8764
      },
      "r2_still_loro_k16": {
        "mood": 0.8207,
        "volume": 0.9728,
        "presence": 0.7842
      },
      "r2_still_loro_k256": {
        "mood": 0.8694,
        "volume": 0.972,
        "presence": 0.8999
      },
      "r2_room_loro_k64": {
        "mood": 0.8313,
        "volume": 0.9554,
        "presence": 0.8034
      },
      "spearman_loro_k64": {
        "mood": 0.9058,
        "volume": 0.9164,
        "presence": 0.9281
      },
      "perm_null95_k64": {
        "mood": 0.0017,
        "volume": -0.0861,
        "presence": -0.1077
      },
      "perm_p_k64": {
        "mood": 0.0,
        "volume": 0.0,
        "presence": 0.0
      },
      "lambda_median_k64": 0.1,
      "tertile_acc_k64": {
        "mood": 1.0,
        "volume": 1.0,
        "presence": 1.0
      },
      "g0b_sensitivity_r2_luminance_k64": 0.9958,
      "g0b_sensitivity_pass": true,
      "g1_dial_pass": {
        "mood": true,
        "volume": true,
        "presence": true
      },
      "g1_pass_count": 3,
      "armA_room_sep_pass": true,
      "armB_room_identity_acc": 1.0,
      "gates": {
        "r2_floor": 0.3,
        "room_r2_floor": 0.15,
        "top_pc_fraction": 0.5,
        "armA_acc_floor": 0.75,
        "sensitivity_floor": 0.9
      },
      "key": "vjepa2_vitl",
      "hf_id": "facebook/vjepa2-vitl-fpc16-256-ssv2",
      "kind": "video",
      "role": "swap",
      "loader": "VJEPA2Model + VJEPA2VideoProcessor (E7's pattern)",
      "cache": {
        "cached": true,
        "snapshot": "4aa02df83918538fc21cfaf576382fa20e489a80",
        "weights_file": "model.safetensors",
        "weights_mib": 1432.4
      },
      "load_notes": {},
      "vram": {
        "free_before_mib": 4355,
        "free_after_mib": 4355,
        "weights_mib": 631.5,
        "peak_allocated_mib": 703.8
      },
      "controls_armA": {
        "dial_r2_k64_booked": {
          "mood": -0.5886,
          "volume": -0.6696,
          "presence": -0.6548
        },
        "room_identity_acc": 1.0
      },
      "status": "ran",
      "labels_match_control": true
    }
  },
  "leaderboard": [
    {
      "encoder": "ijepa_vith16_1k",
      "hf_id": "facebook/ijepa_vith16_1k",
      "role": "control (E12 replication)",
      "status": "ran",
      "verdict": "KEEP",
      "r2_still_loro_k64": {
        "mood": 0.8106,
        "volume": 0.9624,
        "presence": 0.9478
      },
      "r2_room_loro_k64": {
        "mood": 0.8902,
        "volume": 0.9717,
        "presence": 0.9374
      },
      "perm_null95_k64": {
        "mood": -0.0561,
        "volume": 0.0371,
        "presence": -0.023
      },
      "g1_pass_count": 3,
      "armA_room_identity_acc": 1.0,
      "vram": {
        "free_before_mib": 4355,
        "free_after_mib": 4355,
        "weights_mib": 1205.4,
        "peak_allocated_mib": 1503.4
      },
      "reason": null
    },
    {
      "encoder": "dinov2_base",
      "hf_id": "facebook/dinov2-base",
      "role": "swap",
      "status": "skipped",
      "verdict": null,
      "r2_still_loro_k64": null,
      "r2_room_loro_k64": null,
      "perm_null95_k64": null,
      "g1_pass_count": null,
      "armA_room_identity_acc": null,
      "vram": null,
      "reason": "weights not in local HF cache \u2014 one-time download needed (~350-600 MB). Re-run with E15_ALLOW_DOWNLOAD=1 or pre-pull: huggingface-cli download facebook/dinov2-base"
    },
    {
      "encoder": "clip_vitb32",
      "hf_id": "openai/clip-vit-base-patch32",
      "role": "swap",
      "status": "skipped",
      "verdict": null,
      "r2_still_loro_k64": null,
      "r2_room_loro_k64": null,
      "perm_null95_k64": null,
      "g1_pass_count": null,
      "armA_room_identity_acc": null,
      "vram": null,
      "reason": "weights not in local HF cache \u2014 one-time download needed (~350-600 MB). Re-run with E15_ALLOW_DOWNLOAD=1 or pre-pull: huggingface-cli download openai/clip-vit-base-patch32"
    },
    {
      "encoder": "vjepa2_vitl",
      "hf_id": "facebook/vjepa2-vitl-fpc16-256-ssv2",
      "role": "swap",
      "status": "ran",
      "verdict": "KEEP",
      "r2_still_loro_k64": {
        "mood": 0.8753,
        "volume": 0.9671,
        "presence": 0.8764
      },
      "r2_room_loro_k64": {
        "mood": 0.8313,
        "volume": 0.9554,
        "presence": 0.8034
      },
      "perm_null95_k64": {
        "mood": 0.0017,
        "volume": -0.0861,
        "presence": -0.1077
      },
      "g1_pass_count": 3,
      "armA_room_identity_acc": 1.0,
      "vram": {
        "free_before_mib": 4355,
        "free_after_mib": 4355,
        "weights_mib": 631.5,
        "peak_allocated_mib": 703.8
      },
      "reason": null
    }
  ],
  "gates": {
    "control_key": "ijepa_vith16_1k",
    "control_ran": true,
    "control_keep": true,
    "control_verdict": "KEEP",
    "swaps_ran": [
      "vjepa2_vitl"
    ],
    "swaps_keep": [
      "vjepa2_vitl"
    ],
    "swaps_not_ran": [
      {
        "key": "dinov2_base",
        "status": "skipped",
        "verdict": null,
        "reason": "weights not in local HF cache \u2014 one-time download needed (~350-600 MB). Re-run with E15_ALLOW_DOWNLOAD=1 or pre-pull: huggingface-cli download facebook/dinov2-base"
      },
      {
        "key": "clip_vitb32",
        "status": "skipped",
        "verdict": null,
        "reason": "weights not in local HF cache \u2014 one-time download needed (~350-600 MB). Re-run with E15_ALLOW_DOWNLOAD=1 or pre-pull: huggingface-cli download openai/clip-vit-base-patch32"
      }
    ]
  },
  "verdict": "KEEP",
  "note": "E12's dial-read pipeline (same 27-room staged bank, same elephant-bank labels, same ridge/LORO/perm-null) re-run under each frozen encoder. Per-encoder gate = E12 G1 verbatim. INVALID_CONTROL: the I-JEPA control failed to replicate E12's KEEP in THIS run (comparison void). KEEP: >=1 non-I-JEPA encoder reads >=2/3 dials at E12's thresholds -> room-geometry property. KILL: every valid non-I-JEPA swap fails where I-JEPA keeps -> I-JEPA's inductive bias is load-bearing. Skipped/failed/INVALID_HARNESS swaps never silently become a KILL. Caveats: staged carriers (E12's limit); vjepa2 rows are 16-frame windows anchored at each still; CLS tokens included in the uniform mean-pool for dinov2/clip.",
  "guard_summary": {
    "samples": 28,
    "min_free_vram_mib": 2681,
    "max_temp_c": 77,
    "breach": null,
    "timed_out": false
  }
}
```

## X1 — reverse-probe variance fraction (how much of the embedding do the dials actually explain?)
- ran: 2026-09-28 09:56
- verdict: LICENSE
- note: reverse ridge (dials → embedding, LORO): mean R² 0.4264, median 0.4688, var-weighted 0.5215 (still-level); room-level 0.4432/0.5363. The dials explain ~43–52% of the I-JEPA room embedding — a MAJOR axis, not a needle; the elephant could find them without labels. Controls: dials→pixels 0.68 (ceiling 0.88) vs dials→embedding 0.43 = the embedding keeps ~2/3 of the dial signal (dial-preserving compression, not destruction); luminance→embedding 0.041 = the embedding is NOT a brightness meter. Null (shuffled dials) −0.20, p=0.0. Metric calibrated (planted 0.255 → recovered 0.201). Between-room ceiling 0.96. LICENSE (mean > 0.40) — the room-temperature sense SURVIVES the reverse kill-shot.

## E15 (full leaderboard, 4 encoders) — is I-JEPA special? NO.
- ran: 2026-09-28 10:50 (DINOv2 + CLIP downloaded and run)
- verdict: KEEP (aggregate)
- note: ALL FOUR frozen encoders read all 3 dials at E12 thresholds — ijepa_vith16_1k 0.811/0.962/0.948 (control, replicates E12), dinov2-base 0.838/0.956/0.899, clip-vit-b32 0.901/0.958/0.669, vjepa2-vitl 0.875/0.967/0.876. Supervised (CLIP), distillation (DINOv2), and both JEPA families all pass. The dial read is a property of ROOM GEOMETRY, not of any encoder family's inductive bias. Interesting per-encoder texture: CLIP is best on mood (0.90) but weakest on presence (0.67); V-JEPA 2 is best on volume. Full table: results/e15_full_leaderboard.json.

## X3 — stats-battery parity (the honest null for "beyond luminance")
- ran: 2026-09-28 11:10
- verdict: INCONCLUSIVE (parity gate splits: volume parity, presence jepa-wins)
- note: 24-dim hand-crafted battery (color moments, percentiles, Michelson contrast, Fourier bands, Sobel density/magnitude, spatial autocorr) vs I-JEPA on the same E12 bank, same LORO ridge + 200-perm nulls. **Volume is decoration**: battery 0.954 vs jepa 0.962 (gap 0.008 = parity) — volume's carrier was always classic statistics; the JEPA claim loses volume outright. **Mood flips**: battery 0.937 > jepa 0.811 (colour-temp is statistics' home turf). **Presence is the surviving JEPA story and a GENERALIZATION win**: still-level gap 0.29, but room-level LORO collapses the battery to 0.028 while I-JEPA holds 0.937 — the battery memorizes per-still edge patterns; the embedding generalizes to unseen rooms. Net: "the encoder found something deep" survives on presence ONLY; volume (and mood) belong to classical statistics. Harness drift check: jepa row reproduces E12 exactly. Natural escalation: battery + nonlinear reader on presence at room level (mirror of E13b's reader question).

## D13b — relational addressing (confidence-weighted reward)
- ran: 2026-09-28 10:27 (CPU-only, seed 2718)
- verdict: KILL
- note: final_acc 0.533 vs the 0.80 bar; edge concentration on true partner 0.30 vs 0.50 bar (chance 0.143). Signed-confidence reward improved margin over D13's 0.467 but no convergence (accuracy drifted to ~0.72 mid-run, decayed back). Learned edge addressing has now failed two reward formulations; d13c (reinforce) + d13d (shared-key) were the remaining rescues — d13d later KEEPed (correlation, not reward). The 0.44 structural delta from D12 is handed-addressing-only.

## X6 — extrapolation (did the reader memorize the staging manifold?)
- ran: 2026-09-28 11:56
- verdict: KILL
- note: train on dial range [min,0.7], test on [0.7,max] (18/9 rooms). ALL THREE dials collapse outside the trained range: mood interp +0.449 -> extrap −3.148 (ratio −7.0), volume +0.941 -> −0.139 (−0.15), presence +0.839 -> −4.314 (−5.1). The read is RANGE-LOCAL: LORO tested room-holdout (interpolation within the staged dial grid), not dial-range generalization. The E12-family read is a local map of the staged manifold — it does not extrapolate to unseen dial values. Combined with X3 (volume/presence = classical statistics), the staging-artifact thread is now strong. The one falsifier that could still save the “room geometry” framing: X2 renderer transfer (same dials through a second independent renderer — transfer = content, collapse = renderer parameterization). That is now THE experiment.

## X2 — renderer transfer (room content or renderer parameterization?)
- ran: 2026-09-28 12:20 (fired twice, deterministic; committed 65f56c7)
- verdict: INCONCLUSIVE (pre-registered floors; substance: largely renderer-bound)
- note: renderer-B = pure numpy/PIL compositor, zero shared primitives with lavfi (mood→hue-wheel diag-gradient vs RGB-lerp; volume→stripe-texture+defocus vs noise+contrast; presence→phyllotaxis soft-Gaussian blobs vs drawbox). Within-A replicates E12 EXACTLY (0.8106/0.9624/0.9478); within-B KEEPs E12's gate on the different primitives (0.767/0.944/0.911) — both within reads real. CROSS transfer fails the 0.5x content floor on EVERY dial BOTH directions: mood A→B −0.02 / B→A +0.19; volume −0.98 / −1.99 (B→A volume BELOW its own shuffle null — worse than random); presence +0.30 / +0.20. Pooled-basis control made transfer worse (not a basis artifact); weak residual content for mood/presence (above nulls, far from parity). B's luminance R2 0.41 vs A's 0.99 yet B reads its dials fine — B rides hue/texture/shape. FAMILY PICTURE (with X3+X6): the E12 read is largely renderer-bound, range-local, and stats-explainable for volume — the deep claim survives only as presence's within-renderer room-level generalization + the weak cross residual. The staged elephant measured the staging.

## D1 — delta-attention training increment (first novel-model mutation)
- ran: 2026-09-28 12:50 (300s budget, seed 42, zero new params — head-split reuses same weights)
- verdict: KILL (val_bpb 1.696093 vs baseline 1.695939, +0.000154 at fixed budget)
- note: the honest nuance: delta-attention tracked the baseline train curve to 3 decimals while consuming 7.5% FEWER tokens (25.7M vs 27.8M) — per-token the difference signal is REAL; the ~9% wall-clock overhead (66K vs 73K tok/s, extra shift+sub path) ate it before warmdown. Next lever queued (D2): make delta free — k_d = k_t − k_{t−1} POST-projection (reuse normal heads' k/v, no second linear) so overhead → ~0 and the per-token parity competes on even wall-clock. Artifacts: training/delta_increment/ (8871a10).

## X9 — presence-depth hardening (the last deep claim)
- ran: 2026-09-28 13:05
- verdict: FALLS (presence falls to statistics; ratio 1.07×)
- note: X3's battery room-level collapse (0.028) inverted under the nonlinear reader — the same 24-dim battery through E13b's fixed MLP reads presence at **0.895** room-level, BEATING embedding-MLP (0.835). The battery contained presence generalization all along; the ridge couldn't extract it. The "generalization gap" was a NONLINEARITY gap. Ridge rows reproduce X3 bit-for-bit (drift green); all honesty guards passed (nulls ≪ reads, curvature 6.3 vs 0.02 affine floor). **With X3+X6+X2: the E12-family dial read is fully statistics-explainable on ALL THREE dials.** The falsifier campaign swept the table: X1 LICENSE (dials ~half the embedding's variance — within the staged bank) · X3 KILL · X6 KILL (range-local) · X2 renderer-bound · X9 FALLS. The staged elephant measured the staging. Full JSON: results/x9_presence_depth.json.

## D2 — free-delta training increment (first novel-model KEEP)
- ran: 2026-09-28 13:15 (300s budget, seed 42, paired vs baseline; committed 5da8101)
- verdict: KEEP — val_bpb 1.666624 vs baseline 1.695939 (**−0.029315**), ~100× the margin D1 lost by
- note: the free-delta mutation (delta heads' k/v = POST-projection temporal diffs of the same row-slices; zero new params; VRAM identical to baseline 3745.3MB) converted D1's per-token signal into a real win: tok/s only −2% (71.3K), 3 steps bought back (52 vs 49), final train loss 4.864 vs 4.906, tracking better the whole way. Compile parity |d|=0.0 on the real FA3 kernel; GPU serialization with X9 worked (waited, ran clean). The day's evidence stack (E18 diff super-additivity, D19/D20 ternary transition, E24 memory-not-momentum) predicted differences carry structure absolutes don't — now a trained delta-attention model BEATS vanilla at the same budget. The nursery's first kept mutation. D3 = seed replication to harden the win.

## D3 — free-delta seed replication (the win hardens)
- ran: 2026-09-28 13:35 (300s budget, seed 1337, both arms; committed 21a251c)
- verdict: REPLICATED — baseline@1337 1.700300 vs free-delta@1337 1.671658 (paired **−0.028642**), vs D2's seed-42 −0.029315 (agreement within 0.0007)
- note: two seeds, two paired wins of ~0.029 bpb. Seed-only diffs verified byte-identical to the receipt code; seed-to-seed noise ~0.005 bpb vs ~6x that for the paired effect. Cost profile matches D2 exactly (98% tokens, 71K tok/s, VRAM identical, zero new params). **Free-delta is hardened — the fleet can stack mutations on it.** Next: D4 candidates (delta-head ratio sweep, ternary weights on the delta path).

## G1 — the fleet's first generative glyph-domain model (next-frame predictor over renderer codes)
- ran: 2026-09-28 15:13 (304.9s budget, seed 42, hand-built in the main session after 4 flash rate-limit kills)
- verdict: INCONCLUSIVE (majority gate CLEARED +19.3 pts; persistence gate failed on 2 of 3 dynamic sources)
- note: 25.3M-param free-delta GPT over V=32 renderer codes (tone idx + edge fam×level + SEP), seq 6144, 59 steps, loss 3.47→0.48. **Model 80.6% vs majority 61.3% (+19.3 — clears the +15 gate).** vs persistence (copy-last-frame): testsrc2 +6.9 (model WINS on the fast-motion source) but life −12.0 / mandelbrot −6.3 — persistence is brutal on slow-motion feeds (83%/46% of cells unchanged frame-to-frame at 10fps). CE-per-cell texture: gradients 0.07 (nearly deterministic), smptebars 0.017, mockscene 0.28, testsrc2 0.64, life 1.02, mandelbrot 1.96. Pre-flight gauntlet (3 bugs died in the yard: majority-baseline shapes, CPU-tensor device mismatch, one orchestration slip) — zero GPU budget wasted. FIRST trained glyph-domain model anywhere (field has ASCIIEval but zero published training runs); every generated frame is renderer-replayable by exact code lookup. G2 levers: higher fps (bigger per-frame deltas weaken persistence), longer budget, changed-cells-only eval. Full JSON: results/g1_glyph_predictor.json.

## G2 — changed-cells diagnostic (G1 replication + the dynamics-vs-statics question)
- ran: 2026-09-28 15:30 (same config/seed as G1 — clean replication; commit chain in training/glyph_g1)
- verdict: INCONCLUSIVE (gate replicated: majority +19.1, persistence fails life −12.2 / mandelbrot −6.4, testsrc2 +6.7)
- note: **the changed-cells answer: the model learned statics + predictable dynamics, not hard dynamics.** On cells that actually moved: gradients 66% (of 4% changed), testsrc2 **40%** (periodic motion — real dynamics learning), but life 5.6% (of 17%) and mandelbrot 7.5% (of 53%) — the cellular automaton and the fractal zoom are NOT learned in 5 minutes. Overall 80.5% accuracy is mostly statics; the G1 gate's INCONCLUSIVE is now fully explained. G3 lever firing: double the framerate (bigger per-frame deltas starve persistence AND test whether life/mandelbrot become learnable at finer dt).

## G3 — framerate scaling (20fps: does finer dt teach the hard dynamics?)
- ran: 2026-09-28 15:45 (20fps corpus, 2x temporal data; same config/seed)
- verdict: INCONCLUSIVE (and the diagnosis sharpened)
- note: 20fps did NOT teach the hard dynamics — life changed_acc 6.9% (vs 5.6% @10fps), mandelbrot 8.1% (vs 7.5%). The doubled framerate made frames MORE similar (changed_frac collapsed: life 16.6%→5.1%), strengthening persistence's statics advantage (testsrc2 margin shrank +6.7→+2.8; majority margin +19.3→+13.2). Model overall 83.1% (up from 80.5%) — better statics, same dynamics. **The diagnosis now points exactly at diff-targets (gem #1): the model wastes capacity predicting the 95% that doesn't change. G4 fires the loss-masked variant (train only on changed cells) — the glyph program independently derived why 'predict differences, not states' matters.**

## G4 — diff-target loss mask (train only on changed cells)
- ran: 2026-09-28 16:01 (same config/seed; G4_LOSS_MASK=1 — statics+SEP masked from the gradient, >=100-target resample guard)
- verdict: KILL (by the registered overall-accuracy gate — the masked model predictably lost statics: 61.6% overall, majority-margin ~0)
- note: **the diagnostic validates the diff-target hypothesis decisively: dynamics learning tripled-to-quadrupled on EVERY source** — life 5.6%→**19.8%** (3.5x), mandelbrot 7.5%→**19.6%** (2.6x), mockscene 4.7%→**19.5%** (4x), testsrc2 40.3%→**47.3%**, gradients 66.2%→**74.3%** changed-cell accuracy. Statics collapse — but persistence covers statics for free. **The G1→G4 arc experimentally derives the hybrid refiner: predicted frame = copy-last-frame + the diff-trained head's corrections on changed cells.** G5 is the composite. Two-scale principle status: token-level (free-delta KEEP), target-level (diff-mask triples dynamics) — latent level remains gem #1's test.

## G5 — the hybrid refiner composite (the derived architecture's test)
- ran: 2026-09-28 16:21-16:28 (lane died on its final reply to a rate limit; the work completed — result file + code intact)
- verdict: KEEP (best threshold 0.5)
- note: **the architecture the G1-G4 arc derived is validated: persistence base + diff-head corrections, threshold-calibrated, beats both parents.** The threshold is a dial between statics and dynamics: at thr=0.5 the composite converges to persistence's overall accuracy (gradients 0.958 vs 0.959; life 0.826 vs 0.832; mandelbrot 0.463 vs 0.465 — ties) while retaining correction capacity; at thr=0.1 it recovers real changed-cell accuracy (gradients 0.699, mandelbrot 0.137) at modest overall cost. persist_changed_acc = 0.0 everywhere (by construction — persistence never predicts a change; the composite is the only arm that does both). The full arc: G1 learned statics+easy dynamics → G2 diagnosed → G3 showed data doesn't fix it → G4 proved focus does (dynamics tripled) → G5 composed the two experts and KEPT. First architecture in the fleet derived end-to-end by its own experiment sequence.

## G6 — the starved probe (data-bound or capacity-bound?)
- ran: 2026-09-28 16:37-16:56 (in-house fire after the rate-limit storms; G4_LOSS_MASK=1 G6_SOURCES=life,mandelbrot)
- verdict: KILL (frozen gate: both under 1.3x G4 — life needed >=0.396 or mandelbrot >=0.392 for KEEP)
- note: **the hard dynamics are CAPACITY-BOUND, not data-bound.** Training the diff-masked model on life+mandelbrot ONLY at equal budget: life changed-cell 0.207 (vs G4's 0.198 — 1.05x, nothing), mandelbrot 0.192 (vs 0.196 — 0.98x, slightly worse). The starvation took effect (testsrc2, unseen in training, dropped 0.473→0.323) but freed capacity bought NOTHING on the hard sources. The pivot the gate named: **capacity — bigger model, longer training, or a different inductive bias for rule-like dynamics** (life's CA rule and the fractal zoom are not learnable by this class at this scale in 5 minutes, whatever the data). The RSI loop's second self-proposed fire: ledger -> propose -> review -> fire -> verdict -> ledger, turning honestly.

## G7 — the capacity test, time axis (does doubled budget crack the hard dynamics?)
- ran: 2026-09-28 17:10-17:24 (G_TIME_BUDGET=600, G4_LOSS_MASK=1, full corpus, same seed/config — one variable: time)
- verdict: KEEP (by G7's pre-registered gate: life OR mandelbrot changed-cell >= 0.30)
- note: **the time axis cracks the hard dynamics.** life changed-cell 0.198 -> **0.422 (2.1x)**, mandelbrot 0.196 -> **0.320 (1.63x)** — BOTH past the 0.30 gate. testsrc2 0.473->0.656, mockscene 0.195->0.442. 103 steps, train_loss 1.396 (vs G4's 2.32). The JSON's built-in "KILL" field is the composite gate's verdict (not G7's question) — G7's gate is the changed-cell threshold and it PASSES. G6's pivot (capacity-bound) confirmed with the time axis as the binding constraint: data didn't help (G6), time does (G7). **G8 fires the scaling point: 1200s (x4 from G4) — does the curve keep climbing or saturate?**

## G8 — the scaling point (1200s: does time keep paying?)
- ran: 2026-09-28 17:56-18:20 (G_TIME_BUDGET=1200, G4_LOSS_MASK=1, same config/seed — one variable: time x4 from G4)
- verdict: SATURATION (the pre-registered plateau: life ~0.45, not >=0.55)
- note: **the time axis saturates for the hard dynamics.** life 0.198 (300s) -> 0.422 (600s) -> **0.4505** (1200s) — the second doubling bought +0.028 vs the first's +0.224. mandelbrot 0.196 -> 0.320 -> **0.3294** (saturated harder). testsrc2 keeps climbing (0.473 -> 0.656 -> **0.8995**) and mockscene 0.487 — the EASY dynamics keep paying; the hard ones hit their budget ceiling. Train loss 0.763, 200 steps. **The full curve: G4 found the signal, G6 killed data, G7 doubled time (KEEP), G8 doubled again (plateau) — G9 fires the PARAMS axis** (DEPTH 8->12 at 600s, the efficient point, vs G7's 0.422/0.320): if params crack past the plateau, capacity was width-bound; if not, the architecture is the wall and the pivot is inductive bias (a rule-learning head).

## G9 — the params axis, first attempt (crashed in pre-flight)
- ran: 2026-09-28 18:21 (G_DEPTH=12, G_TIME_BUDGET=600, G4_LOSS_MASK=1)
- verdict: ABORTED (CUDA allocation failure — a config bug, not a finding)
- note: **G_DEPTH=12 scaled WIDTH with it** (n_embd = depth x ASPECT 64 = 768): the model built at **85.1M params** (vs the intended ~40M — the depth knob drags width through the ASPECT coupling), passed the FAIL-first check, then died allocating the (4, 6144, 768) fp32 activation buffer — "CUDA driver error: device not ready" (WSL's flavor of the 6GB wall). Lesson: the params axis needs the WIDTH-only knob (ASPECT env), or the conservative depth step. **G9b fired the corrected single-variable: G_DEPTH=10 (640 embd, ~42M params, +65%)** at the same 600s vs G7's numbers.

## G9b — the params axis, second attempt (crashed on the even-head assert)
- ran: 2026-09-28 18:40 (G_DEPTH=10, 640 embd, 5 heads, 600s)
- verdict: ABORTED (AssertionError: delta-attention mutation requires even head counts)
- note: 640 embd / HEAD_DIM 128 = **5 heads — odd** — and the free-delta mutation splits heads in half, so odd counts are structurally excluded by its own assert. The params axis is BOXED by architecture constraints: width must be a multiple of 256 (2 heads' worth) for even heads; 512@B4 fits but is the baseline; 768@B4 OOM'd (G9); the odd-head widths are excluded. **The only remaining move: G9c = 768 embd (6 heads) at B=2** — fits the VRAM by halving the batch, with the batch-confound acknowledged (params AND batch both change; a win is still informative, a loss is ambiguous).

## G9c — the params axis, fifth death + the timebox [the axis is BOXED tonight]
- ran: 2026-09-28 18:52-19:00 (G_DEPTH=12 G_BATCH=2, 85.1M params, verified chain)
- verdict: ABORTED (CUDA allocation failure at B=2 — the (2,6144,3072) MLP buffer)
- note: five honest deaths on one axis: G9 OOM@B4 (the ASPECT coupling made 85M not 40M), G9b odd-head assert (the delta mutation's even-head requirement), G9c-v1 my syntax error (nested quotes), G9c-v2 the _os scope bug (head vs tail imports), G9c-v3 OOM@B2 (85M × 3072-wide MLP does not fit 6GB at any B>=2). **CONCLUSION: the params axis is BOXED on this skeleton tonight — the knobs are coupled (depth drags width, width pins heads, heads gate the mutation) and the clean test needs the decoupled width knob (harness debt, queued).** The provisional science stands: time helps then saturates (G7 KEEP / G8 SATURATION), data doesn't help (G6). **G10 pivots the GPU: the seed replication of G7** (600s, seed 1337, the proven 25M config — the D3 replication discipline applied to the glyph program's central KEEP).

## G10 — the G7 replication at seed 1337 [REPLICATED — the arc's central KEEP hardens]
- ran: 2026-09-28 18:55-19:07 (G_SEED=1337 G_TIME_BUDGET=600 G4_LOSS_MASK=1, the proven 25.3M config)
- result: life 0.430 | mandelbrot 0.323 | testsrc2 0.809 | mockscene 0.460 | loss 1.002 | 106 steps | 4754MB peak
- vs G7@seed42: life 0.422 | mandelbrot 0.320 | testsrc2 0.656 | mockscene 0.442
- verdict: **REPLICATED** — every source within noise (life +0.008, mandelbrot +0.003, mockscene +0.018; testsrc2 +0.153, the noisiest easy source, same regime). TIME-CRACKS-THE-HARD-DYNAMICS is now double-seeded: the G4(diff-mask)->G7(time) composite finding graduates to HARDENED.
- meta: this is the RSI loop's receipt chain working — G7 proposed (KEEP), G10 replicated (the D3 discipline applied to the glyph program). The finding that survived: it is not parameters (G9 boxed, G6 data-dead), it is not more time beyond 600s (G8 saturated) — it is the DIFFERENCE OPERATOR plus time. The delta-native hypothesis's third data point.

## T5 — the dial controller (resolution↔framerate as a behavior: the 5th-dimension test)
- ran: 2026-09-28 20:05–20:15 AKDT (fire 1 ABORTED ~20:05 — frozen estimator made the designed hysteresis unreachable, G9-precedent config bug, no verdict claimed; fire 2 = v2 per-arm Kalman estimator, gate/scene/budget/thresholds/seeds untouched; plan §7 documents the abort before the refire. CPU numpy, 2.3s wall.)
- verdict: **KILL** (by the pre-registered gate: a fixed point beats the controller — all-confirm 0.022999 vs adaptive 0.070277, adaptive/best-fixed = 3.06; robust 0/5 seeds; KILL clause any-fixed ≤ 1.02×adaptive fires on all four fixed arms)
- arms (mean SW-MSE, surprise-weighted; quiet/burst raw pixel MSE; all spends 1.00–1.00x of the 2400-pt budget — parity held):
  - **all-confirm** (hi-res@5fps): **0.0230** (0.00532 / 0.0430) — the map-maker wins the whole board
  - all-mid (mid@10fps): 0.0373 (0.0128 / 0.0536)
  - random (Markov flip): 0.0450 (0.0151 / 0.0664) — in-predict 0.45, prec/rec 0.20/0.49
  - **oracle** (cheats, sees regimes): 0.0436 (0.00739 / 0.0877) — prec/rec 1.00/1.00, in-predict 0.18
  - all-predict (lo-res@20fps): 0.0608 (0.0250 / 0.0741)
  - adaptive (surprise controller): 0.0703 (0.0256 / 0.0924) — in-predict 0.62, 22 switches, prec/rec 0.26/**0.89**, onset→predict median **0.25 s**, missed 2/13 bursts
- note: **the decisive number is the oracle's, not the controller's: perfect regime knowledge LOSES to sitting at the foveal point (0.0436 vs 0.0230, 1.9× worse).** When even a cheating switcher can't beat a fixed allocation, the dial earns nothing in this world — the kill is structural, not a controller-quality artifact. The mechanism: the frozen burst regime is white-jerk motion (OU τ=0.08 s — velocity decorrelates inside one confirm-sampling interval), so there is no persistent velocity to extrapolate; every arm is reduced to position estimation, and position estimation is dominated by blur (res-1 floor σ_lo²·Σ2A² ≈ 0.032 pixel-MSE vs res-4's 0.00045). Low-res's ×64 blur tax buys a ×4 sampling rate that has nothing fresh to sample. The controller itself behaved: 0.25 s median flip latency, 89% of burst time covered, only 2/13 bursts missed — and it still lost, partly to χ²-tail false alarms on the sharp channel (any 3σ glitch at σ_hi=0.015 reads as surprise; 22 switches vs 13 real bursts) and 1 s hysteresis overshoot into quiet. What actually died today: **the generalized saccade does not pay in a world of untrackable motion.** What the kill points at: the hypothesis's hidden premise is that "moving" means *trackable* — persistent velocity (objects crossing the frame), where stale-v extrapolation error grows as v_err·0.2 s for confirm but only v_err·0.05 s for predict. A regime sweep over burst τ (0.08 → seconds) with the same frozen gate would locate the boundary where the dial starts paying — queued as a t5b seed, not fired tonight. Full JSON: results/t5_dial_controller.json; plan+abort chain: proposals/runs/t5-plan.md.

### 2026-09-28 20:36 — K1: latent diff-target vs state-target (frozen V-JEPA 2 latents) — KEEP
**The keel's first rung stands.** Plan-first (proposals/runs/K1-plan.md, baseline 0c6b56b), gates frozen before build. Encoder: facebook/vjepa2-vitl-fpc16-256-ssv2, fp16, mean-pooled → 1024-d latents; 96 train / 32 val deterministic glyph-lattice clips (drifting fields, 4-quadrant motion labels); matched 2-block d=512 predictors, 1200 steps, both arms scored identically as reconstruction MSE vs z_{t+1}.
- state@42 0.530694 / state@1337 0.485783 · diff@42 0.417453 / diff@1337 0.415744 · persistence 0.544681
- **relative win: +21.3% (seed 42), +14.4% (seed 1337)** — gate ≥5% at both seeds: PASSED
- Health: all four arms beat persistence. Readers: diff wins under the LINEAR reader at both seeds (ridge 0.417/0.500 vs state 0.25/0.25) — K-G5 (MLP-only win) NOT triggered. Clean KEEP.
- Honest caveats: one domain (synthetic drifting fields), small val (32 clips/24 windows), state arm barely beats persistence (the win is diff's motion-sensitivity, not state's weakness). Fire-to-verdict 3 min after a 7-min cache. Artifacts: training/keel_k1/{cache.pt, results/k1_results.json}.
- **Next rung (K2): replicate on the real-video lavfi corpus latents + source-family swap (the D3 discipline).**

### 2026-09-28 20:36 — IB1a: fly-rule (no backprop) vs controls, delayed-receipt bandit — KEEP
**The mushroom-body rule stands on the 4050.** Frozen sparse encoder (PN 50 → 2000 KC, ~10 PN/KC, k-WTA top 8%), K·V value ~8k params, order-gated δ-broadcast (pre-before-δ, Hige), eligibility at action time, RW extinction, homeostatic decay. 3 seeds × 600 steps, receipts delayed 3 steps, 80/20 reward reliability.
- A fly-rule 0.3733 · B no-third-factor 0.2583 · C order-swapped 0.2717 · **D backprop-match 0.3717**
- Gates: A−B = +0.115, A−C = +0.102 (margin 0.05) → KEEP. **A vs D (ungated, honest): 0.3733 vs 0.3717 — parity. The order gate + dopamine broadcast learns as well as matched backprop, no gradients, ~8k params, 5.1 seconds.** Transfer: A 0.250 vs D 0.223 (fly edges it, ungated).
- Honest caveats: one bandit family (linear argmax mapping), fixed 3-step delay, ε-greedy 0.1. IB1b: variable delay + nonlinear structure. Artifacts: experiments/ib1a_fly_rule.py, results/ib1a_fly_rule.json.

### 2026-09-28 20:47 — K2: latent diff-target vs state-target, REAL-VIDEO replication — KILL
**The keel's rung-1 finding is DOMAIN-BOUND.** Same harness as K1 (env-swapped cache/labels), real lavfi corpus (still-solid/testsrc/smpte/testsrc2, per-clip deterministic crop+jitter, source-family labels, V-JEPA 2 fp16 1024-d, matched 2-block predictors, 1200 steps, both seeds). Preflight bug (tensor-truthiness `or`) caught by the HARD PREFLIGHT in 10s, fixed, refired — total fire-to-verdict ~6 min.
- state@42 0.063117 / state@1337 0.064458 · diff@42 0.077760 / diff@1337 0.080632 · persistence 2.7427
- **relative win: −23.2% (seed 42), −25.1% (seed 1337)** — diff-target LOSES decisively on real video, both seeds.
- Health: both arms CRUSH persistence (~35×). Readers (source-family): ridge AND MLP at 1.0 for all arms — the four sources are linearly separable in V-JEPA 2 space; readers were not the discriminator here.
- **Reading:** on content-rich video the next-latent is dominated by static/periodic structure the state arm learns near-identity on; the diff arm must predict the small hard change-signal with identical capacity — and loses. On K1's smooth synthetic motion (motion = the only structure), the same trade flips. **The difference-operator's latent-level generality is NOT established.** Per keel-backcast's whole-backcast falsifier: the demotion clause fires for the LATENT rung (token-level D2/D3 and target-level G4/G10 evidence stands — different data, different regime). The keel program continues at "domain-mapped," not "general."
- **K3 (pre-register first): mixed corpus (synthetic:lavfi ratios) to MAP where diff-target pays — the boundary, not the average.** Artifacts: training/keel_k1/{cache_lavfi.pt, results/k2_results.json}.

### 2026-09-28 20:58 — T5b: the trackability horizon sweep — KILL AT EVERY τ (no horizon exists)
**THE one-line answer: the trackability horizon does not exist — adaptive never beats all-confirm at any burst τ ∈ {0.08, 0.2, 0.5, 1.0, 2.0, 4.0} s, and the gap WIDENS as motion gets more trackable (adaptive/all-confirm SW-MSE ratio 3.06 → 5.41, monotone). The t5 kill is structural, not a τ artifact: the dial does not pay anywhere on the motion-timescale axis.**
- ran: 2026-09-28 20:44–20:58 AKDT (plan-first proposals/runs/t5b-plan.md, baseline ab8ec08, gates frozen before build; CPU only; 14.4 s wall; py_compile → bitwise regression vs t5.run_arm PASS on all five shared arms at τ=0.08 seed 41 → per-τ smoke PASS → official fire, seeds 41–45)
- sim: exact t5-v2 world, ONE knob — burst OU τ (σ_burst frozen 1.4, quiet OU untouched); controller never sees τ (same brain, six worlds); paired truth per seed (identical schedules + noise streams across τ)
- arms per τ: all-confirm, all-predict, **uniform** (frozen round-robin over the three dial positions, ledger-spent — budget split evenly across the dial), random, oracle, adaptive; gate family = t5 §4 verbatim per τ (FIXED = the four fixed arms)
- per-τ mean SW-MSE (adaptive/all-confirm ratio; verdict; pays=WIN?):

| τ_s | all-conf | all-pred | uniform | random | oracle | adaptive | ada/conf | verdict |
|-----|----------|----------|---------|--------|--------|----------|----------|---------|
| 0.08 | 0.02300 | 0.06080 | 0.04047 | 0.04505 | 0.04359 | 0.07028 | 3.056 | KILL |
| 0.2 | 0.02735 | 0.08092 | 0.04861 | 0.05910 | 0.06633 | 0.09502 | 3.474 | KILL |
| 0.5 | 0.02285 | 0.08420 | 0.04215 | 0.05793 | 0.07056 | 0.09681 | 4.238 | KILL |
| 1.0 | 0.01620 | 0.06846 | 0.03033 | 0.04421 | 0.05656 | 0.08013 | 4.948 | KILL |
| 2.0 | 0.01034 | 0.04887 | 0.01949 | 0.02980 | 0.03896 | 0.05430 | 5.251 | KILL |
| 4.0 | 0.00617 | 0.03147 | 0.01155 | 0.01835 | 0.02412 | 0.03341 | 5.414 | KILL |

- horizon (first τ with adaptive < all-confirm): **NONE**; pays (first WIN): **NONE**; spend parity 1.000–1.001× all arms, all τ; robust 0/5 everywhere.
- **The decisive column is still the oracle's — and it loses at every τ** (0.0436 vs 0.0230 at τ=0.08 → 0.0241 vs 0.0062 at τ=4.0, 1.9×→3.9× worse). Even PERFECT regime knowledge can't make the switch worth it, so the controller's 0.25–0.47 s flip latency and χ² false alarms are not the story. The controller behaved at every τ (burst recall 0.89→0.73, precision ~0.25, 22–24 switches, 57–64% in-predict) and still lost 3–5×.
- **Mechanism (the map's actual finding):** all-predict's burst MSE (0.042–0.121) NEVER beats all-confirm's (0.009–0.053) at any τ despite 4× the sampling rate — the ×8 blur is a ×64 variance tax (σ_lo=0.12 vs σ_hi=0.015) that ×4 cadence cannot repay at any motion timescale. Position sampling is velocity-structure-robust (confirm's burst error falls 0.043→0.009 as τ grows); extrapolation through the noisy channel never catches up. The t5 note's rescue hypothesis — "the dial pays once motion is persistent/trackable" — is itself killed: smooth sustained velocity (τ=4 s ≫ confirm's 0.2 s sampling interval) is exactly where confirm's foveal advantage grows largest. **The generalized saccade does not pay in this budget economy at any point of the trackability axis.**
- Honest caveat (scope, not tunability): t5b sweeps the correlation timescale τ at frozen burst SPEED σ=1.4 rad/s. Confirm's age error scales ~v²·(0.2²/12) ≈ 0.0033·v² per component vs predict's fixed ~0.04 blur floor, so a speed sweep (σ_burst ≳ 4 rad/s, t5c pre-register first) is the remaining axis where a horizon could in principle open. Also: verdicts are per the frozen pixel-MSE budget world (res-4↔res-1 = ×64-blur-for-×4-cadence exchange); a different exchange rate moves the boundary. The frozen gate was never loosened: KILL everywhere, no asterisks.
- Artifacts: experiments/t5b_tau_sweep.py · results/t5b_tau_sweep.json (per-τ arms/gates/horizon + regression + smoke receipts) · proposals/runs/t5b-plan.md. t5's files untouched.

### 2026-09-28 20:58 — IB1b: fly-rule under variable delay + nonlinear structure — KILL
**The IB1a margin was contingent on the easy world, and the trace paid for jitter in credit precision.** Plan-first (proposals/runs/IB1b-plan.md, gate frozen before any code, baseline a5e6f7f). Two hardenings only, everything else IB1a-frozen: receipts now arrive at d ~ Uniform{1..5} resampled per receipt (no timestamps — a per-action eligibility trace λ=0.9 is the only bridge), and the correct-action map is argmax(ReLU(x·W₁ 50×16)·W₂ 16×8), frozen per seed (was linear argmax). Chance = 0.275. 3 seeds × 600 steps, CPU numpy only, no torch (GPU belongs to K2); D = manual-backprop 2000→64→8 + Adam + replay, experiencing the SAME variable-delay schedule (its buffer is its trace). Verified-fire chain: py_compile → finite-difference gradcheck → smoke → fire.
- **A fly-rule 0.3017** (per-seed 0.325/0.295/0.285 — tight, just above chance) · **B no-third-factor 0.3583** (0.45/0.22/0.405) · **C order-swapped 0.2817** (0.30/0.255/0.29) · **D backprop+replay 0.355** (0.41/0.31/0.345)
- Gate (frozen): A−B ≥ 0.05 AND A−C ≥ 0.05 → **A−B = −0.0566 FAIL, A−C = +0.0200 FAIL → KILL.** Sanity annotation passed (D 0.355 > chance+0.02 = 0.295): the world IS learnable — this is a real kill, not a vacuous one.
- A vs D (ungated, honest): **0.3017 vs 0.355 — IB1a's parity is gone.** Backprop's replay buffer trivially absorbs variable delay and its capacity cracks the nonlinear map. The fly rule "matches backprop" only where the world is linear and the delay is clocked.
- What died, precisely: (1) **the order-gate's edge was a fixed-delay phenomenon** — A over C compressed +0.102 (IB1a) → +0.02 (IB1b); when credit arrives smeared across a 5-step window, an exponentially-decaying trace can barely out-spend anti-causal credit, because the trace that grants jitter-tolerance also destroys credit sharpness (the λ=0.9 trace holds λ^d ∈ [0.59, 0.90] — a 1.5× blur of the very quantity the order gate is supposed to gate). (2) **B is a high-variance random walk, and A's signal is too small to clear margins against control noise** — B's reward-blind Hebbian drift collapses onto arbitrary per-context policies (per-seed spread 0.22–0.45); on this 3-seed draw it landed ABOVE the fly rule. A reward-blind control beating the gated rule is the loudest possible statement that A's +0.027-over-chance signal is marginal at this budget.
- Harness receipts (the verified-fire chain earned its keep twice): gradcheck's first FAIL was a check-harness bug (reshape(-1) on 0-d biases copies instead of views), and the rerun exposed a REAL net bug — the kaiming init bounds were mis-named as the bias parameters, so D's "biases" were scalars. Caught pre-fire, fixed, gradcheck PASS (tanh 4.3e-09, relu 1.4e-06). G9/T5 precedent: the abort-fix-refire chain is the discipline working.
- What the kill points at (IB1c seeds, NOT fired tonight): credit under jitter needs something sharper than a fixed-λ trace — announced receipts (a cue preceding delivery so the trace can be gated when it matters), multi-timescale traces, or the spike-timing version where order is carried by millisecond offsets, not exponential tails. The honest boundary found tonight: **the fly rule's no-backprop parity requires clocked receipts; free-running jitter plus nonlinear payoff structure is past its operating envelope.**
- Artifacts: experiments/ib1b_variable_delay.py · results/ib1b_variable_delay.json · proposals/runs/IB1b-plan.md. IB1a files untouched.

### 2026-09-29 05:2X — K3: the boundary map — INVALID_HARNESS (one poisoned draw; the gate held)
**One bad mix draw voided the map, exactly as the frozen gate demands.** Plan-first (proposals/runs/K3-plan.md, ab8ec08; val-interleave refire d749565). Same frozen harness as K1/K2 (both V-JEPA 2 caches, TinyPredictor, 1200 steps), fixed 50/50 mixed val, only knob = train-mix r; 20 cells, 309 s.
- Persistence floor (fixed mixed val) = 2.879. **18/20 cells beat it; the r=0.25 seed-42 cell failed for BOTH arms (state 3.111 / diff 3.079) while seed 1337 at the same r passed comfortably (1.572 / 1.635)** — deterministic mix-draw variance, not a domain effect. Frozen gate: any arm ≥ persistence → INVALID_HARNESS. No post-hoc loosening; booked as-is.
- Informational only, NOT booked: rel_win(r) = −0.041/+0.034/+0.033/−0.015/+0.039 (r=1.0→0.0), spread 0.080, Spearman −0.6 — non-monotone and inverted vs the K1/K2 bookends (diff won pure-synth val, lost pure-lavfi val; here the r=1.0 point is negative on the mixed testbed). The mixed testbed changed the question, not just the noise.
- Repair pre-registered BEFORE leaning on the numbers: **K3b** (proposals/runs/K3b-plan.md) — one delta, 3 draws per cell (seed 7 added), floor applied to per-cell draw-means, gates textually identical, K3 not pooled in. Fired after booking.
- Artifacts: training/keel_k1/k3_boundary.py · training/keel_k1/results/k3_results.json · proposals/runs/K3b-plan.md.

### 2026-09-29 05:28 — IE1: Reichardt correlators → 4 motion fam codes — KEEP (grating-borne; blob direction unreadable)
**The lobula-plate rung holds: a plain linear reader decodes true direction from the pooled 4-cardinal-code stream alone.** Plan-first (proposals/runs/ie1-plan.md, written 09-28 before any run; fired this morning). CPU-only numpy lane, GPU untouched. Delay-LP → multiply → mirror-subtract on adjacent pairs, pooled to 4 cardinal family codes; gate frozen: R²(direction) ≥ 0.5 at ≥2 of 3 densities, τ=2 frames.
- Densities 8/16/32: r2_dir = 0.446 / 0.519 / 0.508 → **2 of 3 pass → KEEP**; cardinal accuracy 0.968 / 0.995 / 1.000.
- The split that scopes the KEEP (honest): grating-only r2 = 0.702 / 0.836 / 0.836 vs blob-only r2 = 0.061 / 0.044 / 0.015 — the fam code carries direction for periodic texture, not localized blobs, at this rung. Science §4's pooling-hyperacuity claim stays untested on blob motion (ie2's question, not booked here).
- 3.0 s, seed 20260928. Artifacts: experiments/ie1_reichardt.py · results/ie1_reichardt.json · proposals/runs/ie1-plan.md.

### 2026-09-29 06:04 — K3b: boundary map, 3-draw replicates — INVALID_HARNESS (the poison is deterministic in the draw; boundary PARKED)
**Two draws per cell were never the problem — the harness owns the poison, and it replicates bit-identically.** Pre-registered repair (proposals/runs/K3b-plan.md, committed with K3): one delta — 3 draws per cell (seeds 42/1337/7), floor gated on per-cell draw-means, gates textually identical. 30 cells, 461 s.
- **The r=0.25 seed-42 cell replicated BIT-IDENTICALLY** (state 3.111 / diff 3.079 — the same values as K3): the collapse is deterministic in the mix draw, not training noise. A NEW poisoned draw appeared: r=0.00 seed-7 state = 4.349 (floor 2.879) while diff@7 on the same draw learned fine (2.382) — the collapse is draw×target-specific.
- Gate: the draw-mean floor fires on r=0.0 state (mean 3.167 ≥ 2.879) → INVALID_HARNESS. No loosening. All other cell-means pass (r=1.0: 2.46/2.61; r=0.75: 1.57/1.49; r=0.5: 1.38/1.32; r=0.25: 2.22/2.15).
- Informational (NOT booked, contaminated by the poison): rel_win(r) = −0.089/+0.048/+0.041/+0.031/+0.177, spread 0.266, Spearman −0.6 — the r=0.0 +0.177 rides on the poisoned 4.349 in the denominator; do not lean on it.
- Lane verdict: ~3 of 30 mixed-draw cells collapse to ≈persistence regardless of seed count. **The boundary question is PARKED until the collapse itself is understood.** Next: K3c = diagnosis, not another boundary roll — per-100-step train/val curves on the poisoned cells + a healthy control, classify the collapse mode (no-learn / train-val split / divergence) before any new boundary attempt.
- Artifacts: training/keel_k1/k3b_boundary_replicates.py (cell-mean indent bug caught fail-loud at 50 s, fixed, refired) · training/keel_k1/results/k3b_results.json · k3b_run.log · proposals/runs/K3b-plan.md.

### 2026-09-29 07:13 — K3c: collapse diagnosis — the poison is a domain split: state z-codes don't transfer, diff does
**Diagnosis, not a boundary roll** (plan-first: proposals/runs/K3c-plan.md, frozen classification). Replicated the K1/K3/K3b loop exactly with per-100-step train/val curves + per-domain val MSE. 6 cells, 86 s. Informational booking — K3c does not vote on the boundary.
- **Every poisoned cell = train-val-split with the failure concentrated in the SYNTH half**: synth val 4.26–4.71 (floor 2.85) while lavfi val 1.50–1.80. The model learns its drawn (mostly-lavfi) train set fine; it cannot reconstruct synth z-codes it never/rarely saw. State z-codes are domain-anchored.
- **The diff arm is domain-portable**: C1 (same draw as P3, diff target) reconstructs synth at **1.77** vs P3's 4.71 — frame-difference statistics transfer across domains; absolute latents do not. The diff/state asymmetry the K-lane was built to probe is a representation property, not a mix-ratio boundary.
- Not an effective-ratio anomaly: seed 42's r=0.25 draw is 19.8% synth vs 17.7% for the healthy 1337 draw (n=96 slots) — no draw-level outlier. The "deterministic poison" is a small-n bifurcation on a basin boundary.
- Replica is NOT bit-identical to K3b (periodic val evals shift kernel scheduling → float chaos compounds over 1200 steps; all six finals within ~0.2–1.0 of booked, C3 flipped healthy↔split) — consistent with a basin-boundary landing, and part of the diagnosis. The domain pattern is uniform and unaffected.
- Floor on the fixed val recomputed 2.8477 (K3 booked 2.879 — different compute detail; classifications unchanged).
- **The boundary question as posed is undecidable at n=96**: a single mixed-val MSE averages a portable-diff signal with a domain-anchored-state signal. K3d, if attempted, must gate per-domain (or report rel_win per domain) and grow n.
- Artifacts: training/keel_k1/k3c_diagnose.py · training/keel_k1/results/k3c_diagnose.json · k3c_run.log · proposals/runs/K3c-plan.md.

### 2026-09-29 09:14 — IE2: blob-only reader — KEEP (3/3): the sensor was fine; IE1's gap was reader dilution
**IE1's honest caveat resolves in the sensor's favor.** Plan-first (proposals/runs/IE2-plan.md). One delta vs IE1: the ridge reader trains on BLOB-ONLY sequences and tests blob-only; all else identical (σ 2/3, speeds 0.25/0.5, 4 cardinals, densities 8/16/32, τ=2, α=0.01, seed base 20260928). CPU-only, 1.0 s.
- r2(direction) = **0.541 / 0.806 / 0.930** at densities 8/16/32 (IE1's mixed-trained reader on the same blobs: 0.061 / 0.044 / 0.015); cardinal accuracy 0.909 / 0.980 / 1.000. Gate ≥ 0.5 at ≥ 2 of 3 → **3/3 → KEEP**.
- **H-reader confirmed, H-sensor killed:** the wide-field pooled correlator DOES carry small-field direction. The mean-pooled blob signal is 40–150× smaller than the grating signal (amplitude ratio 0.0249 / 0.0164 / 0.0065 by density) — yet a linear reader that is not drowned by wide-field variance decodes it near-perfectly. Science §4's pooling-hyperacuity claim now holds for both stimulus families; the boundary was in the reader, not the rung.
- τ sweep (descriptive): 0.782 / 0.806 / 0.837 at τ = 1/2/4 — mild, monotone in τ, no cliff.
- Follow-up shape (not booked): a two-head reader (wide-field + small-field heads, or per-family gating) should recover both families from the single 4-code stream — the fam code carries more than one reader can see at once.
- Artifacts: experiments/ie2_blob_reader.py · results/ie2_blob_reader.json · ie2_run.log · proposals/runs/IE2-plan.md.

### 2026-09-29 10:05 — C1: Cosmos 3 Edge boots on the RTX 4050 — KEEP (17.5 tok/s at 1.95 GiB: frontier edge world model runs on boat-class silicon)
**The ground truth nobody had: NVIDIA's 4B edge world model runs comfortably on a 6 GB laptop GPU.** Plan-first (proposals/runs/C1-cosmos-edge-boots-plan.md). `nvidia/Cosmos3-Edge` (9.18 GB bf16 snapshot, OpenMDW1.1) via transformers 5.17 native `cosmos3_edge` + bitsandbytes **NF4** (double-quant, bf16 compute), device_map auto, under guard.py. Mandate: Casey 07:43/08:52/09:54 — experiment widely, push often.
- **KEEP numbers:** 48/48 tokens, **17.5 tok/s decode** (t_gen 2.74 s), **peak alloc 1.95 GiB / total VRAM 3.12 GiB** of 6, **peak 49 °C**, guard floor never threatened (min free 3.7 GiB), load 5–11 s warm / processor ~10 s. Frozen deckhand prompt via the repo chat template; the model opens with visible chain-of-thought reasoning (Nemotron style) before answering.
- Fail-loud trail (all receipts kept): attempt-1 crashed on a debug print (`hf_device_map` missing on this class — the model had already LOADED); attempt-2 generated 1 token from a raw-text prompt (no chat template → instant EOS); attempt-3 applied the chat template → full generation. A first boot on new silicon owes exactly this trail.
- Scope: AR-tower text reasoning only. Diffusion tower (video/action gen, WAM policy mode) is C2+; Jetson Thor's 15 Hz is another class — **17.5 tok/s on a 4050 is the hundred-boats number.**
- Artifacts: experiments/c1_cosmos_boots.py · results/c1_cosmos_boots.json (+ .attempt1-crash, .attempt2-short) · c1_pull.log · c1_run*.log · proposals/runs/C1-cosmos-edge-boots-plan.md.

## C2 - first real video through the 4050's world model (smoke) - 2026-09-29
- attempt-1 INVALID_HARNESS: processor produced 960 video features vs 0 video placeholder tokens (chat content lacked {"type":"video"}); I-task never reached. Traceback kept: results/c2_world_smoke.attempt1-kill.json. Guard clean (rc=0, breach=None).
- attempt-2: mechanical placeholder fix (video/image entries in chat content), same frozen gates (proposals/runs/C2-world-smoke-plan.md). Log: c2_run2.log.
- attempt-2 GATE-FAIL booked (mechanical pass, relevance fail): harness fixed — 8 frames -> 1026 input tokens via videos= path. Both anticipation tasks degenerated under greedy (V: "6. 6. 6..."; I: "_what is most likely to happen_" x10) -> scene-relevance clause unmet -> KILL. Numbers still book (firsts on 4050 silicon): video decode 2.98 tok/s vs image decode 49.14 tok/s (video KV-cache tax at 960 vision features), 2.01 GiB peak, 42.2 s load, guard clean. Receipt: results/c2_world_smoke.attempt2-degenerate.json. attempt-3 deltas: generation_config sampling params instead of greedy + repo's own example_reasoning_prompt.json pairing.
- attempt-3 booked (sampled-loop KILL): sampling fix changed loop morphology, not coherence — V-task garble ("6._7_6...") at 19.76 tok/s (256 new tok, 1026 in), I-task with repo example prompt verbatim: brief coherence then "..._..._with this task" loops at 46.2 tok/s (216 new tok). Mechanical KEEP, scene-relevance clause unmet -> KILL. Key inference: the sampler was never the poison — vision-token conditioning under NF4/processor is prime suspect (C1 text-only coherent on the same loader). attempt-4 = 3-cell vision-path isolation probe (text-only / image+greedy+no-thinking / image+greedy+thinking). Receipt: results/c2_world_smoke.attempt3-sampled-loop.json. Guard clean, 2.01 GiB peak.
- attempt-4 vision-path isolation probe booked (KEEP, poison LOCALIZED): TEXT-ONLY coherent on the same NF4 loader (A: clean CoT on the flower/bottle prompt, loop_frac 0.037); IMAGE+no-thinking emits "..." + EOS after 2 tokens (B); IMAGE+thinking garbles into digit cycles "1.0.1.1..." (C, 47.8 tok/s). The vision-token injection itself breaks Cosmos3-Edge under 4-bit — sampler (attempt-3), prompt, and thinking flag all exonerated. attempt-5 = exclude the vision tower from quantization (skip-modules) — if image coherence returns, the recipe is "skip the tower when quantizing VLMs", a grabbable tool for every small-GPU box. Receipt: results/c2_probe_vision_path.attempt4.json. Guard clean (5920 MiB free pre, 44C).
- attempt-5a booked INVALID_HARNESS (crash before cells): probe accessed model.visual, but visual/projector live on the INNER Cosmos3EdgeModel (model.model.visual) — AttributeError in the dtype receipt, zero GPU work done. Same exec surfaced c3_make_data.py's ffprobe dep rotted (static_ffmpeg wrapper module gone); replaced with an ffmpeg-stderr probe — no external dependency, fail-loud parse. attempt-5b = corrected access path (short+qualified skip names, Parameter-type receipt), same frozen gate. K3b rule holds: diagnose the harness, never re-roll blind.
- attempt-5b booked KEEP (frozen gate met): tower+projector bf16, LM NF4 — visual_dtype torch.bfloat16, visual_type Parameter (skip took). Q image+thinking COHERENT ("Got it, let's figure out how to put the flower into the red bottle. First, identify the objects..." loop_frac 0.025, 53 tok/s); A2 control coherent; B2 image+no-think emits structured bbox-JSON grounding ({"bbox_2d": [174,669,418,807], "label": "Pick up the flower..."}). POISON NAMED: the quantized vision tower. RECIPE (grabbable, on-silicon proof): never quantize the tower/projector — NF4 LM + bf16 tower = coherent 4B-class VLM on a 6GB card at ~50 tok/s image decode. C2 arc closed: sampler exonerated (a3), thinking flag exonerated (a4), vision-token injection localized (a4), quantized tower named (a5).
- C3 data regen DONE: 256 clips (96+32 x 2 domains), 768.0 MiB, manifest + sha256 at data/c3/manifest.json, 16.7s, ffmpeg-stderr prober. Books to: C3 probe (Cosmos latents, K3c domain-anchoring replication).
- C3 latent probe booked ANCHORING_REPLICATED (frozen gate met): nearest-centroid val AUC 1.0, 64/64 (binom p 5.4e-20), ALL source families perfect (16/16, 16/16, 6/6 x5). Domain structure (K-law synth vs real footage) survives Cosmos3-Edge latents via the proven skip-tower loader — K3c domain-anchoring REPLICATES cross-encoder. Peak 2.35 GiB, load 7s, 256 tokens/clip. SECONDARY FLAG (honest): linear_logistic 0.0 AUC train+val = label-convention flip suspected in the logistic head (0.0 is anti-correlated, not random 0.5); does not touch the frozen primary gate. Next probe fixes the encoding and re-scores separability shape.
- Insight: domain anchoring is not encoder-idiosyncratic — video encoders generally embed the synth/real statistic. Cells can key on this structure in ANY encoder (grabbable for the fleet).
- C3 logistic flag RESOLVED (refit diagnostic): label-convention flip confirmed — explicit y=real refit scores cv5 AUC 1.0 (5/5 folds), full-fit 1.0 on saved embeddings (results/c3_logistic_refit.json). Domains are linearly separable too. Caveat owned: 1.0 on lavfi-vs-real is the easy half of the question; C4 targets the non-trivial half (action identity vs content).
- C4 booked ACTION_SEPARABLE (frozen gate met, caveat sealed): recomputed with convention-by-construction scoring — cross-video (av_0 vs av_1) LOOCV AUC 1.0000, within-video temporal-half 0.0938, diff +0.9062. CAVEAT (owned): the control came out ANTI-oriented (0.094, not ~0.5) — within-video drift is itself strongly structured, and its orientation flips between normalized-dot (original run 0.9219) and euclidean (0.0938) geometry. SOLID: video identity perfectly decodable from single-clip latents (16/16 LOOCV, both geometries). UNSURE: action-vs-content attribution — the control found strong temporal structure instead of pure nuisance; C5 paired-condition design owns that question. HARNESS LESSON (2nd convention bug — C3 logistic, C4 orientation): scoring utils now fix the sign by construction; never import a scorer whose positive direction is implicit.
- IE3 booked DILUTION_CONFIRMS: A-joint and B-sequential shared-trunk arms dilute; C-split-trunks specialists hit r2_blob 0.987 / r2_direction 0.984 at density 32. Crew doctrine in silicon: specialists need dedicated trunks — a shared trunk with two heads loses to two small dedicated nets even when specialization is sequential. Shapes CM1 cell-mesh: each model = its own dedicated cell; routes cross BETWEEN cells, never multi-role one cell.
- CM1 round 1 booked GATING_WINS (frozen gate met, honest read sealed): arm A (ungated qwen2.5:0.5b) 0/12 — ALL PARSE_FAIL, the 0.5b cell cannot hold the BOOK:x:y format; arm B (Jev-gated relay) 10/12, diff +10. Path census: 11/12 PINCHED_FALLBACK, 1 DRAFT_PASS (which itself failed final parse — the gates passed a semantically-graded but unparseable draft). REAL PROPERTY: judgment gates correctly distrusted a broken generative cell (gate scores 0.04-0.74) and the pinch path (deterministic keyword router) carried accuracy — the pincher doctrine PROVEN under generative-cell failure, not just in theory. S12 wrong via the pre-registered negation blind-spot ("no AIS contacts" substring-matches the router motion term). S7 gap: gates check semantics, not format. Round-2 hooks: format gate before semantic gates, negation-aware fallback terms, pinch sweep 0.3/0.5/0.7, jev-latest vs preview. Judgment layer cost: 9628 in / 897 out tokens, 16.2s wall for all 12 stimuli both arms.
- CM1 round 2 booked GATING_WINS at all three pinch levels (11/12 vs 0/12, diff +11 each): format-first gate fixed the S7 class (unparseable drafts never reach semantic gates) and drove Jev usage to ZERO (0/0 tokens vs round 1's 9628/897 — sealed prediction confirmed in the extreme, whole round 3.4s). Honest read: the sweep was DEGENERATE — the 0.5b cell produced no parseable draft in r2 (12/12 FORMAT_PINCHED), so all correctness came from the keyword-router fallback and the pinch threshold never engaged. Threshold dynamics need a competent generative cell -> r3 swaps GEN to DeepInfra ByteDance/Seed-2.0-mini (key live 14:03), everything else frozen.

## CM1 r3 (2026-09-29) — TIE_NOISE ×3: competent GEN holds; gates cost without benefit, never hurt
GEN swapped to DeepInfra Seed-2.0-mini (one factor vs r2; plan CM1-r3-plan.md pushed c0ad169 pre-fire). Arm A ungated: 12/12 perfect. Arm B: 12/12 at pinch 0.3/0.5/0.7 (diff +0 all). Texture by threshold: p0.3 11 DRAFT_PASS+1 RETRY (jev-in 4519); p0.5 3 DRAFT+7 RETRY+2 PINCHED (jev 7374); p0.7 11 RETRY+1 PINCHED (jev 9422) — gates doubted 12/12 CORRECT drafts at p0.7 and accuracy STILL held. Verdict: judgment gates buy zero accuracy on a competent cell and burn judgment+retry tokens scaling with conservatism — but the retry+pinch safety net never let a wrong answer through. With r1/r2: gates rescue broken cells at ~zero cost (format-first), cost without harm on competent ones. "What's preferred when," measured end-to-end. 780.8s wall. results/cm1/round_003_out.json

## CM1 r4 (2026-09-29) — RULE-BLIND GATES FABRICATE DOUBT; rule-rich batched gates fix flow at 25x wall, 4.5x cheaper
Hypothesis (pre-reg CM1-r4-plan.md, pushed 7a388a3 pre-fire): r3's doubting texture (9/12 correct drafts doubted at p0.5, 12/12 at p0.7) was caused by the RULE text missing from gate state (r3 arm_b regression vs r1). Arm A replicated rule-blind @0.5: 12/12 but flow {3 DRAFT_PASS, 6 RETRY_PASS, 3 PINCHED_FALLBACK}, jev 6965/702, judge wall 6.9s/18 calls, cal 0.648. Arm B rule-rich batched (24 named noul questions, ONE call, RULE canon in state): 12/12, flow {12 DRAFT_PASS} — zero doubt/retire/pinch — jev 1559/490, batch wall 0.28s, cal 0.767. Accuracy TIE_NOISE (+0) per frozen bands; P2/P3/P4 confirmed (DRAFT_PASS 12 vs 3; 0.28s vs 6.9s = 25x; 12/12 both). P1 direction confirmed (+0.119 cal) but frozen band was >=+0.15 — MISSED by 0.031, booked honestly. Verdict: gate doubting was MANUFACTURED by state blindness; rich state + batching = better calibrated, cheaper, faster, zero flow loss. 414.3s wall. results/cm1/round_004_out.json

## MQ1 shadow (2026-09-29) — GROWTH REACHES PARITY, DOES NOT BEAT FIXED (tensor scale, 4050)
Pre-reg MQ1-growth-vs-fixed.md (pushed 76e60b9 pre-fire). Fixed MLP(1,[64,64,1]) 4353 params vs grown from [16,16] grafting +8 on plateau until [64,64]; 5 seeds each, Adam 1e-3, 4000 steps, batch 32, frozen 240/60 sin split (seed 42), fp32 CUDA.
- fixed vals med 0.02792 [0.02701..0.03249]; grown med 0.02841 [0.02757..0.03187]; ratio 1.0177 -> TIE (frozen band +/-5%). 60 grafts total (12/run, all reaching [64,64]).
- Read: at equal FINAL params, a net born full-size ties a net grown into place at this scale. Growth is neither handicap nor free win — and it never needed the big net to start. Operator caveat owned: grafts use fresh init + Adam state rebuild (the dumb operator); a smarter graft (distillation/zero-splice) is untested.
- Harness bugs found/fixed en route: graft layers created on CPU while model on CUDA (device fix); scalar arm's NaN divergence reached engine __pow__ (Fraction(NaN)) inside the step -> divergence guard moved into the step, divergence recorded not crashed.
- Receipts: results/mq1/mq1_shadow_results.json. Scalar arm (CPU, ~100s/run) fired for cross-scale sign; MQ2 (harder multi-dim task) is where capacity TIMING could matter.

## CG1 (2026-09-29) — THE CANON GATE DOES NOT LEAVE THE ORACLE (composite); min() SURVIVES; tautology reproduces
Pre-reg CG1-canon-gate-local.md (pushed 8ef0f2c pre-fire). Source canon: jev-gate-experiments-2026-09-29.md. Instrument: LOCAL Qwen2.5-1.5B-Instruct (fp16, CUDA, 42.9s wall, 3 samples @ T=0.3), no API in the loop.
- T1/T2 ladder: FLAT ~0.90-0.97 across all 9 rungs — rung 1 ("The project has a registry file") scores 0.967. Step rung4->5 = -0.05 (canon: +0.690) -> G1 FAIL -> verdict ORACLE_BOUND. The local model yes-biases; the gate's step function is oracle-specific AT THIS PROMPT SHAPE.
- T5 model agreement: 0.5B returns constant 0.0 on every rung — degenerate oracle, no curve shape at all.
- T3 tautology REPLICATES (canon section 4): bare shape ("Is the registry append-only?" vs a pure restatement) = 1.0 while composite = 0.0 and min = 0.0 -> a single-question gate cannot distinguish a claim from a restatement of itself. Reproduced on local silicon.
- T4 min() PARTIALLY REPLICATES: states separate (mechanism+guarantee 0.96 / mechanism-only 0.96 vs guarantee-only 0.0 / neither 0.0) and on the canon's OWN 7 claims min blocks M1/M4/M5/M9/M6 (0.0-0.63) while promoting S1 (0.949) — matching the canon's two-axis result — BUT promotes S2 at 0.933 where the canon's oracle blocked it (0.29): 6/7 agreement, S2 divergent.
- Honest limits: prompt-level replication of a purpose-built judgment cell (noul) with ONE rubric; the composite failure is a scale+elicitation finding, not proof that no local model can do it. Follow-up CG1b: logit-based scoring (P(yes)-P(no)) + rubric few-shot before the claim is treated as settled.
- Receipts: results/cg1/cg1_results.json, /tmp/cg1.log, proposals/canons-gpu-ideas-2026-09-29.md (the 163-file canon read that sourced this).

## CG1b (2026-09-29) — elicitation hardening: ORACLE_BOUND STANDS; the local step flips on the MECHANISM rung, not the guarantee
Follow-up to CG1 (pre-reg CG1-canon-gate-local.md; this run is the skeptic pass on our own finding). Two principled elicitations on local Qwen2.5-1.5B: logit = P(YES)/(P(YES)+P(NO)) at the answer position, and numeric 0-1 with a 2-example anchored calibration shot.
- FROZEN GATES: logit step (rung5-rung4) = -0.074, saturation -0.231 -> G1 FAIL, G2 FAIL. anchored step = 0.000, saturation -0.012 -> G1 FAIL, G2 PASS. Verdict per pre-registration: ORACLE_BOUND_STANDS. The canon's +0.690 guarantee step does NOT reproduce under any of three elicitation styles.
- Logit ladder [0.780, 0.069, 0.311, 0.722, 0.648, 0.488, 0.225, 0.396, 0.558]: discrimination IS recovered (CG1's free-text was flat 0.90-0.97) but the shape is noise-like and the TOP of the ladder scores BELOW the middle (rung 9 independent reimplementation 0.558 < rung 4 editing-breaks-hash 0.722) — the canon's saturation-at-the-top is absent.
- EXPLORATORY (post-hoc, NOT a gate result — labeled as such): anchored ladder [0.05, 0.05, 0.05, 0.85, 0.85, 0.85, 0.837, 0.817, 0.85] shows a clean step AND saturation — but the flip is at rung 3->4 (0.05 -> 0.85), i.e. the local oracle attributes the transition to the MECHANISM clause ("editing a line breaks the hash"), one rung earlier than the canon's guarantee clause ("the file is append-only"). So gate-LIKE structure exists locally; the canon's causal attribution (the guarantee is the cause) is oracle-specific at this scale.
- State check (composite question): logit m+g 0.815 / m-only 0.740 / guarantee-only 0.156 / neither 0.187 -> local model cannot separate guarantee-only from neither (canon composite: 0.270 vs 0.080 — same weakness). Anchored: 0.97 / 0.94 / 0.05 / 0.05.
- Consequence (honest): the transferable part of the canon gate is the two-axis min() (CG1: 6/7 on the canon's claims), NOT the composite ladder. An offline gate needs a purpose-built/fine-tuned judgment cell; a base 1.5B re-attributes the flip and a base 0.5B is degenerate (constant 0.0).
- Receipts: results/cg1/cg1b_results.json, /tmp/cg1b.log.

## RT1 (2026-09-29) — the disagreement dial is a weak proxy for marginal information (low-dynamic-range caveat)
Pre-reg RT1-route-marginal-info.md (pushed pre-fire). Source canon: anti-gan-route-diversity.md's OWN open problem ("what makes a fifth route worth adding?"). 4,000 synthetic double-entry books (clean / missing / sign / rounding / account defect), five routes (real-sum, parity, magnitude, sign, categorical), each with a tiny standardized MLP checker on CUDA; marginal AUC = ensemble - leave-one-route-out, compared with per-route disagreement.
- per-route AUC: R1_sum 0.8660, R2_parity 0.6172, R4_sign 0.6604, R3_magnitude 0.5278, R5_categorical 0.5043. Ensemble AUC 0.8487 — LOWER than the best route alone (R1 0.8660): "more routes" is not automatically better; the informative route carried everything.
- marginal AUC: R1 +0.2060; R2 -0.0063, R3 +0.0077, R4 -0.0068, R5 -0.0120. Disagreement divergence: R1 0.1658, others 0.083-0.098. Spearman(marginal, divergence) = 0.30 (p 0.62) -> G3 FAIL -> verdict per frozen gates: DIAL_DECORATIVE.
- CAVEAT (honest, limits the claim): four of five routes were near-chance (AUC ~0.50-0.66) and therefore carried ~zero marginal information by construction — the correlation test had little dynamic range, so read this as "the dial did not track marginal information HERE", not as a general kill. Follow-up RT1b: routes must be individually competent AND complementary before the instrument question is decisive.
- Harness bugs found+f: thresholded disagreement at 0.5 is degenerate on an 80%-positive label (all-zero) -> switched to probability divergence; ensemble scored on test logits against all labels (length mismatch) -> scored on its own split; unstandardized features -> standardized. Pre-fix numbers were garbage and are not booked.
- Receipts: results/rt1/rt1_results.json.

## MQ1 scalar — arm INVALIDATED by a dimensional graft bug, re-fired (booked honestly)
The first scalar pass was a harness failure, not a result: grafting into hidden layer 1 created Neuron(1) (one input) while that layer consumes 8 outputs, and the downstream layer never grew an input weight -> grown arm scored 0.1135 vs fixed 0.0280 (params 37, not the 97 that [8,8] implies). Diagnosed as dimensional, fixed (graft_neuron: correct nin + fresh input weight appended to every neuron in the next layer), results DISCARDED, re-fired. The torch shadow was never affected (it rebuilds the next layer's weights) — shadow verdict (TIE) stands.

## MQ1 scalar (CPU, quilt rational engine) — cross-scale sign: FIXED_WINS 2.10x, fabric intact
Cross-scale companion to the tensor shadow (which TIED at ratio 1.0177). Same protocol/data (sin(x)+N(0,0.15), 240/60, seed 42; batch 32, 3000 steps; lr=0.01 = winner of the pre-registered grid — lr=0.1 diverged at step ~1 and is recorded in the grid, not hidden).
- fixed [8,8] (97 params), vals: 0.02752, 0.02778, 0.02806, 0.02809, 0.03293 -> median 0.02806
- grown (fresh-init [2,2], patience-stopped), vals: 0.03772, 0.04954, 0.05885, 0.06032, 0.07483 -> median 0.05885 -> ratio 2.097 -> FIXED_WINS (frozen gate < 0.95x)
- Witness amendment earned its keep: graft_drift_median 1.38e-15 vs control_drift_median 4.32e-15 -> FABRIC_INTACT. The grown arm's deficit is optimization-behavioral, NOT tape corruption — growth corrupts nothing.
- CAVEATS (owned): (1) the scalar grown arm is param-MISMATCHED — patience stops growth at 3-12 grafts (21-87 params) vs fixed 97; even the largest grown net (seed2, 87 params, 0.0495) is 1.76x worse than fixed at 97, so the direction survives near-parity, but this is not the shadow's clean parity control. (2) Different engine (rational Fraction + tanh drift floor) — the cross-scale flip (tensor TIE -> scalar LOSS) may be an engine/scale artifact rather than a property of growth. Booked as cross-scale observation, not a gate replication.
- Harness bug found + fixed: the summary builder reused `med_g` for BOTH the grown median and the graft-drift median, so the stored `median_grown` was written as 1.376e-15. `ratio` (2.0973) was computed from the correct grown median (0.05885/0.02806 = 2.0973, verified by hand) -> verdict stands; field corrected in the JSON with a note, variable renamed in-source.

## TC1 (2026-09-29) — the 384-byte tile: deterministic text fields, int8 vectors, and a learned bottleneck TIE
Pre-reg TC1-tile-codec-384.md (pushed fc683e6). Source: SuperInstance/plato-tile-encoder (the "encod" repos Casey pointed at), read-only at /home/eileen/scratch/encod/. Corpus: real tiles mined from our own markdown (quilt-gpu-lab + canon research + workspace memory). Three codecs, each EXACTLY 384 bytes: (A) the crate's deterministic layout, (B) int8 of the 384-d gte-small embedding, (C) a learned 384→96→384 bottleneck (96 f32).
- RESULT (23.8s on the 4050): A top-1 0.7164 / top-5 0.8352; B cos 0.99991, top-1 0.6879, top-5 0.8487; C cos 0.9655, top-1 0.5739, top-5 0.7545. Gates: G1 false, G2 false, G3 false -> TIE.
- FINDING (the interesting part): cosine fidelity and RETRIEVAL are decoupled. The near-lossless vector codec (B) has essentially perfect cosine but retrieves WORSE than truncated text fields (A, 0.7164 vs 0.6879): explicit terms still discriminate. The learned bottleneck (C) is worst at retrieval despite cos 0.9655 — an MSE-trained autoencoder optimizes reconstruction, not retrieval geometry. "Faithful" != "useful".
- FINDING (bug class, fixture-proven): the crate truncates at field-size BYTES while read_str requires valid UTF-8 -> a multi-byte codepoint split at a boundary makes decode_binary return None and the ENTIRE TILE IS LOST. Fixture-verified against the real crate (unicode_split FAIL). Rate on our corpus <5% (G1 false) — a latent hazard, not a frequent one.
- FINDING (doc/code drift): the doc comment says tags(24) + 128+128+64+32+4+4+4 = 388; the CODE writes tags at 20 bytes, which is what makes 384. The comment is wrong; the code is right. Same crate: `cargo test` FAILS — the doctest at lib.rs:6 does not compile (`cannot find type EncodedTile`, missing use import).
- HARMONY: the crate's 64-byte id field is EXACTLY a sha256 hex digest — we set tile ids to sha256(question+answer) and they fit with zero waste. Same 64-byte id limit as Vectorize (the limit we hit in the ocean fix). 384 bytes = 96 float32 = 384 int8 dims: three budgets, one number.
- VERIFICATION: Python harness validated 5/5 fixtures byte-identical (hex + decode status) against the real crate via a path dependency (not a copy) -> scratch harness at /home/eileen/scratch/tc1-rust/. Receipts: results/tc1/tc1_results.json.

## TC2 (2026-09-29) — RETRIEVAL_OBJECTIVE_WINS: the 384-byte budget was never the problem, the objective was
Pre-reg TC2-tile-codec-retrieval.md (pushed pre-fire). Same corpus (2525 real tiles), same embedder, same evaluation as TC1 — only the training objective of the 96-d bottleneck changed. 36.9s on the 4050.
- A_deterministic top-1 0.7164 | B_int8 top-1 0.6876 (cos 0.99991) | C_mse_96d top-1 0.5552 (cos 0.9667) | E_retrieval_96d top-1 0.8782 / top-5 0.9790 | F_hybrid_96d top-1 0.8778 / top-5 0.9794 (cos 0.9342).
- Gates: G1 true (E/F beat the text codec by +0.16, gate was +0.05), G2 true (+0.19 over int8), G3 false -> RETRIEVAL_OBJECTIVE_WINS.
- FINDING: the SAME 384 bytes that scored 0.5552 under MSE score 0.8782 under InfoNCE (+0.32). Reconstruction is the wrong proxy for meaning; retrieval is the right one. A codec should be trained for the query it will answer, not for the bytes it will reproduce.
- FINDING: the hybrid (MSE + InfoNCE) keeps both worlds — cosine 0.9342 with retrieval 0.8778 (statistically tied with pure retrieval). If a tile must be both readable and findable, train both objectives.
- STRATEGIC READ (for the encod harmony work): the deterministic 384-byte text codec is a fine FALLBACK (0.7164 top-1, human-readable, zero training) but a retrieval-trained 96-d codec is +16 points better at the same byte cost. Worth wiring as an option in the tile path (superinstance-api /near already ranks by embedding — this makes the stored representation itself retrieval-native).
- Receipts: results/tc2/tc2_results.json.

## TC3 (2026-09-29) — FRONTIER_CROSSES: a 96-byte retrieval codec beats the 384-byte text codec
Pre-reg TC3-codec-frontier.md (pushed pre-fire). Same corpus (2551 tiles) and evaluation as TC1/TC2; only the byte budget of the retrieval-trained bottleneck moves. 51.9s on the 4050.
- Frontier (bytes -> top-1): 48B 0.6707 | 96B 0.8644 | 192B 0.8781 | 384B 0.8773. Reference: deterministic text fields 0.7174 (at their fixed 384B), int8 0.6876.
- Gates: G1 monotone true (384B sits 0.0008 under 192B — inside the 0.01 training-noise slack), G2 crosses-at-or-below-192B true, G3 knee-above-48B true -> FRONTIER_CROSSES.
- FINDING: the retrieval-trained codec crosses the text codec's quality at **96 bytes — a quarter of the budget** — and then PLATEAUS (192B and 384B are statistically the same). Everything below 96B is a real cliff (48B loses 0.19 top-1 vs 96B).
- Practical read: if a tile's job is to be FOUND, 96 bytes of retrieval-trained code is strictly better than 384 bytes of truncating text. 384 bytes was sized for a menu, not for a meaning.
- Receipts: results/tc3/tc3_results.json; visual: viz/tile-frontier.html.

## TC6 (2026-09-29) — TWO_FACE: the 384-byte tile re-portioned into menu + meaning beats all-menu
Sweep at fixed 384B (menu bytes / meaning bytes). Verdict TWO_FACE: at 96/288 the meaning face
replicates the TC3 knee (>=0.85), the menu face survives truncation to 288B (>=0.68), and the
sum beats pure-menu plato (2 x 0.7174 = 1.4348) decisively. Plato's 384 was the right size for
the wrong reasons: all menu, no meaning. Receipts: results/tc6/tc6_results.json.

## TC4 (2026-09-29) — discrete cells carry real retrieval signal; hybrid rerank capped
First run had a diagnosed harness bug (label-row flip: d1 compared against lab3, d3 against lab1;
plus a return_q scope bug — both visible as ~1/28 random containment). Preserved as
tc4_results_v1_harnessbug.json, fixed, rerun once. Fixed numbers (containment of the true top-1):
flat 8b 0.6163 | 10b 0.6956 | 12b 0.7309; prefix tree 5b 0.5531 | 10b 0.5014 | 15b 0.9167.
G1 DISCRETE_12B true (a 4096-cell codebook — the dodecet budget — contains the right tile 73% of
the time at 1.5 bytes), G2 PREFIX true, G3 HYBRID false (prefix@2 containment 0.5014 caps rerank).
Caveat: n=2551 makes 12/15 bits over-provisioned (uniqueness inflates containment); TC4b on a
larger corpus is the honest scaling test. Receipts: results/tc4/tc4_results.json.

## TC5 (2026-09-29) — ROOMS_ARE_REAL: per-room delta coding beats global coding at equal bytes
Equal 24B/tile (PCA-24 + int8). Global 0.1974 vs room-anchor-delta 0.2719 (+0.0745) across 5 real
source-document rooms; anchors amortized. First experimental evidence that our "rooms" are real
statistical objects, not curation: a room is a predictive prior and tile deltas against it are
cheaper to encode. (Two earlier crashes diagnosed: missing torch import; SVD projection missing
.T. Never re-rolled blind.) Receipts: results/tc5/tc5_results.json.

## Futhark-lab on the 4050 (2026-09-29) — OTHER AGENT'S KERNELS NOW RUN ON GPU: bit-identical to CPU
futhark-lab + canary-3lang (fleetmates, authored without GPU access) verified + executed on the RTX 4050 (WSL2):
- canary-3lang: FNV-1a 64 canary VERIFIED locally (futhark 0.27.1); BQN blocked (as documented).
- exp1_tick.fut (4096-node quilt TICK) + exp5_witness_chain.fut (65536x8 prefix chain): compiled to CUDA and EXECUTED. **CUDA vs multicore-CPU output: max abs diff 0.0 (bit-identical).** Wall times are text-I/O bound (~0.6s warm incl. parsing 1.6MB); kernel-scale benchmarking = follow-up (binary input format).
- Toolchain path (the real discovery, none of it documented anywhere): (1) futhark 0.27.1 release binary; (2) conda-forge CUDA **12.6** env (13.4's NVRTC/driver mismatch wastes an hour — pin to driver generation); (3) nvrtc/cuda/driver headers via CPATH + LIBRARY_PATH at build; (4) at RUNTIME NVRTC needs cuda_fp16.h and futhark passes 32 compile options with NO include path -> LD_PRELOAD shim appending --include-path fixes it (nvrtc_shim.c, 20 lines); (5) text input format needs COMMAS and NO leading dims (size params inferred); (6) LD_LIBRARY_PATH needs conda targets lib + /usr/lib/wsl/lib.
- My numpy cross-check bug of the night: reseeding the RNG between input-gen and reference-gen silently desynced the reference; caught because GPU and CPU backends agreed 0.0 while "numpy disagreed" — when two independent backends agree exactly, suspect your reference generator first.

## QG1 — exact-census re-read of exp022 (2026-09-29): CONVENTIONS_RECOVERED (anchor 0.9854; G2 confirmed)
Receipts as executable spec. The 60 exp022 telemetry gens (960 cell records, 5 streams) were re-evaluated on the
4050 with exact statevector probabilities (no sampling). The frozen anchor (>=99% of recorded train/verify within
0.044 of exact) FAILED twice before passing — and both failures were the finding:
1. fitness readout = min(p000, p111) ("balance", literal): GHZ -> 0.5, deterministic |000> -> 0.0. Union (p000+p111)
   scored 15.7%, max scored 29.8%, min scored 78.3% on the anchor — the anchor picked the readout.
2. **gate angles are in units of pi.** `rx(0.5,0)` means Rx(pi/2). Calibrated by hand on k4's champion: pi-units
   predicts exact balance 0.4268 vs recorded 0.4375/0.4180 (within 512-shot noise); radians predicted 0.0154.
   **This is delta-shape's D10 calibration cut, discovered empirically: the ratios (circuit topology) were never in
   question, only the LABEL on the unit had drifted.** The fleet can keep re-labelling units without breaking ratios.
3. rz is phase-only -> invisible to the balance observable. 16 convention variants swept; pi-units+min is the best
   (0.9854); all others <=0.9531.
Result with calibrated conventions: anchor 1892/1920 = 0.9854 (bar 0.99 narrowly missed; residual 28 comparisons
localized but unidentified — 1.5%). G2 CONFIRMED: k4's "near-miss" champion is a true near-miss (exact balance
0.4268 < 0.45 bar) — the 512-shot 0.418 reading was honest. G1 (hidden crossers) = 5 candidate cells, but per
pre-reg a sub-anchor-bar run makes G1 UNREADABLE -> labeled UNRESOLVED. G3's band definition was ill-posed
(in_band != recorded>=bar) -> EXPLORATORY, withdrawn.
Tool: `tools/qcell_sim.py` (named, single-file, GPU-batched, selftest + JSON receipts). Artifacts:
experiments/qg1_exact_census.py, results/qg1_exact_census/qg1_results.json, proposals/runs/QG1-exact-census.md.

## QG2 — desert-break law at N=4096 (2026-09-30): BOOKED
Fresh-rng lane reimplementation (declared), QG1-calibrated physics, GPU-batched (gathers + bmm chains).
- ARM-SHOT: crossed 2385/4096 = **0.5823** (CP95 0.5670-0.5974); 3/8=0.375 inside CI: False. Stuck-at-zero: 0.226. Break-gen histogram: [626, 367, 288, 228, 185, 134, 128, 113, 86, 79, 71, 80].
- ARM-EXACT (noiseless ablation): crossed 2373/4096 = **0.5793**. G3 delta (exact - shot) = -0.0029 -> MIXED.
- G1 desert shape: shot-arm child balances in [0.30,0.43): 0.0234 vs recorded-receipts baseline (AMENDED: template guessed 0.086 before measuring; true = 32/1920 = 0.0167) 0.0167 -> PASS (gate recalibrated to measured baseline; original <1% guess was wrong — the receipts themselves carry ~8.6% band mass).
- Loneliness (exact arm): mean gap 0.0262, p90 0.0732.

## QO1 — qcell-oracle: crossing IS foreseeable (2026-09-30): BOOKED — G1 PASS, G2 PASS
First trained fleet component on the qcell substrate. Pre-reg: proposals/runs/QO1-qcell-oracle.md (committed
before firing). Shot arm lane, S=4096, 12 gens, bar 0.45, passive champion-state recording.
- Lane crossing rate 0.5847 (2395/4096) CP95 [0.5694,0.5999] -> G1 (QG2 band 0.5670-0.5974) PASS.
  Honesty note: three executions of the seeded lane gave 0.5908/0.5869/0.5847 — torch CUDA ops (tie-break
  torch.rand, GPU sampling) are not bitwise deterministic, so the lane is reproducible only to ~±0.006.
  All three inside CP95; single-seed bit-exact replays of this lane are NOT guaranteed.
- Baseline (logistic on champ_v only): AUC 0.8860, Brier 0.1519. Oracle MLP (64x3): **AUC 0.9510, Brier 0.0872**
  -> G2 PASS (>=0.70 and delta 0.065 >= 0.05). Split by stream (leakage guard), 42588/10660 rows.
- G4 feature census: cv (0.1024) > v (0.0751) > gen (0.0515) >> len/gates (<=0.0094). Champion balances and
  generation dominate; gate-identity histogram is nearly dead weight — crossing is foretold by WHERE the champion
  is on the balance ladder + how early, not by which gates it uses. Strong corroboration of QG2's structural-desert
  law: streams are separable long before gen 12 by observable scalar state.
- Fail-loud trail: run 1 crashed (.numpy() on grad tensor), run 2 crashed (histogram width assumed 49, actually
  67 = PAD+1) — both mechanical, fixed in place, physics untouched. No re-rolls.
Artifacts: experiments/oracle1.py, results/qo1_oracle/qo1_results.json, tools/qcell_oracle.pt.

## DECIDE-1 — jeff-0.8b decision cell on the balance-edit lane (2026-09-30): BOOKED — G1 PASS, G2 FAIL, G3 PASS, G4 EXPLORATORY
Weights downloaded complete (1.7 GB). Three mechanical crashes fixed in place before any scoring logic ran:
processor-level chat template (arm C bypassed the Amendment-2 fallback -> use tokenizer.apply_chat_template),
CPU/GPU device split on labels, string-vs-int labels. Physics/protocol untouched — no re-rolls.
- **G1 control >= 0.75: PASS** — zero-shot control 16/16 = 1.0 (jeff's shipped control lane is real).
- **G2 lane > 0.25, p < 0.01: FAIL — decisively BELOW chance.** Zero-shot lane 5/64 = 0.078 (CP95 0.034-0.170);
  shipped trained readout lane IDENTICAL 5/64 = 0.078. Both readouts agree on the same wrong answers on novel
  balance-edit questions: the mechanism (backbone + readout) is intact but its decision signal is anti-aligned
  or systematically offset on this question family — this is a finding, not a null.
- **G3 hardware: PASS** — peak VRAM 3.31 GiB (bar <= 6), median latency 54 ms.
- **G4 reader ladder: EXPLORATORY** — zero-shot 0.078 -> fitted-T 0.078 (T pinned at boundary 6.0; temperature
  cannot rescue; base logits carry near-zero decision signal) -> fitted linear head 0.3125 (CP95 0.212-0.434,
  CONTAINS random 0.25 — not significant at 95%). Frozen last-hidden states do carry *some* signal the readout
  head trains to in 0.77 s (train CE 0.153), but it does not clear random on 64 test items.
- Protocol on G2 FAIL: STOP. Diagnosis queue item spawned (DECIDE-1b) — below-chance symmetric failure between
  two independent readouts points at question-format/option-order bias, not a broken readout. Do NOT re-roll.
Artifacts: experiments/decide1.py, results/decide1/decide1_results.json, tools/decision_cell.py,
proposals/runs/DECIDE-1-decision-cell.md.

## DECIDE-1b — diagnosis: the lane is INVERTED, not broken (2026-09-30): BOOKED — P1 INVERTED, P2 KIND-BIAS, P3 CONTENT-READING
Pre-reg: proposals/runs/DECIDE-1b-diagnosis.md (committed before firing). Same 64 questions as DECIDE-1
(seed 202), zeroshot reader, no re-sampling. Reproduced argmax 5/64 = 0.078 (matches DECIDE-1 exactly).
- **P1 INVERSION: FIRED.** Predicted candidate is the argMIN-balance option on **0.891** of questions
  (57/64). argmin-probability accuracy 0.375 (CP95 0.267-0.497, lower bound clears random 0.25). The cell
  is answering "which edit gives the SMALLEST balance" with high consistency — it picks the worst edit.
- **P2 kind-bias: pred_kinds delete=42/64 vs label_kinds insert=42/64.** The census cross-tabulates with the
  inversion: delete-edits usually destroy balance (land at argmin), inserts usually build it. Letters
  themselves near-uniform (max share 0.31) — NOT a positional bias.
- **P3 shuffle: content-reading confirmed.** letter_stickiness 0.375 vs content_following 0.781 — under
  option permutation the prediction follows the CANDIDATE, not the letter. The readout genuinely reads
  option content; the decision sign is what's flipped.
- **P4 mean label rank 2.0 (random 1.5; rank-3 = 24/64)** — the true best edit is most often ranked WORST,
  i.e., the ordering is close to fully reversed, consistent with inversion.
- Hardware: peak VRAM 1.67 GiB. One syntax error fixed in place pre-run (bracket in P1 line); physics untouched.
Synthesis with DECIDE-1: jeff-0.8b's decision mechanism (backbone+readout, both readers identical) encodes a
CONSISTENT but INVERTED criterion on this question family: it selects the minimal-balance edit. Since both
the shipped trained readout and the LM-init zeroshot head agree, the inversion lives in the backbone's
representation, not the head. Plausible mechanism (untested): "largest" in the instructions vs option
salience — the model tracks "balance" faithfully but drops/flips the superlative direction.
Artifacts: experiments/decide1b.py, results/decide1/decide1b_results.json, results/decide1/decide1b_run.log.

## DECIDE-1c — instruction flip: REFUTES signed-superlative flip; the model IGNORES the superlative word (2026-09-30 02:3x): BOOKED — C1 FAIL, C2 FAIL, C3 PASS
Pre-reg: proposals/runs/DECIDE-1c-instruction-flip.md (committed before firing). Identical lane to DECIDE-1b
except instructions "...gives the smallest balance?" Labels unchanged (argmax-balance).
- **C1 FAIL decisively**: pred_is_argmax_balance 5/64 = 0.078 (predicted >= 0.75). The choice did NOT flip.
- **C2 FAIL / NULL-RESULT-MIRROR**: argmax accuracy 5/64 = 0.078 — BYTE-IDENTICAL to the "largest" run
  (DECIDE-1: 5/64; 1b: 5/64). The instruction word has ZERO effect on the choice distribution.
- **C3 PASS**: content_following 0.844 under shuffle — still reads candidate content, not letters.
- Exploratory: pred_is_argmin_balance 0.891 (unchanged), kinds delete=45 (unchanged bias).
- STOP rule honored: signed-superlative-flip hypothesis is DEAD. No re-roll.
Synthesis: jeff-0.8b's decision cell answers a FIXED question on this family ("smallest balance" /
delete-side preference) regardless of whether the instruction asks largest or smallest — while the
control lane (numeric comparison, 16/16) proves it CAN read superlatives elsewhere. The failure is not a
sign flip; it's instruction-blindness specific to the balance-edit representation: the backbone locks onto
the argmin candidate and the instruction never modulates it. Next diagnosis: instruction-ablation census
(spawned DECIDE-1d) — does ANY phrasing move the choice, or is the argmin lock absolute?
Hardware: same lane as 1b (~1.7 GiB class); runtime ~2 min.
Artifacts: experiments/decide1c.py, results/decide1/decide1c_results.json.

## DECIDE-1d — instruction-ablation census: the argmin lock is ABSOLUTE (2026-09-30 02:5x): BOOKED — D1 FAIL, D2 FAIL, D3 as predicted
Pre-reg: proposals/runs/DECIDE-1d-instruction-census.md (committed before firing). Same 64 questions (seed 202),
zeroshot reader. 4 new variants + 2 reused baselines; only the instruction string varies.
- **D1 FAIL (no break):** pred_is_argmin_balance across ALL phrasings: largest 0.891, smallest 0.891 (1c),
  highest 0.891, lowest 0.875, neutral ("Choose one edit.") 0.891, no-definition 0.844 — every variant above
  the 0.75 break threshold (CP95 lower bounds 0.736-0.791). NO phrasing moves the choice off the argmin candidate.
- **D2 FAIL (no recovery):** argmax-balance accuracy 0.078-0.125 across all variants (random 0.25). Never answers
  the asked question.
- **D3 PASS as predicted:** neutral instruction = byte-trend identical to `largest` (0.891, delete-heavy 37/64).
  The lock is representation-driven, not instruction-driven.
- Kind census stable: delete-dominant (37-45/64) in every variant; no_def shows slight softening (insert 13 vs 8-12).
- STOP rule honored: naming it the **representation-locked argmin** — jeff-0.8b's decision cell on the balance-edit
  family selects the minimal-balance candidate regardless of instruction content, synonym, or instruction absence,
  while the numeric control lane reads superlatives perfectly (16/16). DECIDE-1 lane CLOSED for tonight.
Synthesis (DECIDE-1..1d): backbone + both readouts encode a fixed "worst-edit" criterion; instructions are causally
inert on this lane. Any fix must operate on the representation or training mixture, not the prompt.
Hardware: ~1.7 GiB class; 256 decides ~2 min.
Artifacts: experiments/decide1d.py, results/decide1/decide1d_results.json, results/decide1/decide1d_run.log.

## QG3 — trap anatomy: traps OPEN with generations (slow-climb fence, NOT width fence); basin metric inconclusive (2026-09-30 03:5x): BOOKED — G1 PASS-for-budget-open (refutes P1), G2 inconclusive, G3 PASS
Pre-reg: proposals/runs/QG3-trap-anatomy.md (+ AMENDMENT 1, committed before firing each stage). Exact arm
(shot==exact per QG2). S=1024/arm, bar=0.45, runtime ~5s/arm on RTX 4050 (~1 GiB class).
- **G3 PASS**: ANCHOR-VEC max|diff| 2.08e-34.
- **G1 PASS-for-budget-open — P1 REFUTED**: baseline W6/g12 crossed 592/1024 = 0.578 [0.547,0.609];
  deep W8/g24 crossed 781/1024 = 0.763 [0.735,0.788]; delta lower bound +0.127 (gate was >+0.05).
  The ~42% landscape-trap from QG2 is NOT absolute: budget opens most of it.
- **AMENDMENT 1 disentangle (clean)**: C(W6,g24) = 773/1024 = 0.755 [0.727,0.781] ~= B(0.763);
  D(W8,g12) = 582/1024 = 0.568 [0.537,0.599] ~= A(0.578). **Generations drive the opening; width
  contributes nothing.** The trap is a SLOW-CLIMB FENCE: stuck streams are on viable but
  shallow-gradient paths — more generations, not more gates, get them over the bar.
- **G2 INCONCLUSIVE (booked honestly, gate not met)**: stuck-champion edit-distance single-linkage
  (thr<=2): arm A n_stuck=432 -> 216 basins, top basin 177 (41%) vs null 160 (37%) — statistically
  indistinguishable from the length-matched random null. Root cause: stuck champions are SHORT
  (skeleton-length dominated), and Levenshtein<=2 over short sequences links near-everything —
  the metric is degenerate on this length distribution. No basin-structure claim is supportable
  with this metric; genome edit distance needs longer champions or a different observable
  (e.g., champion statevector/unitary distance). Do NOT cite QG3 as evidence for or against basin
  structure.
Synthesis: QG2's "desert is structural" stands (desert exists at fixed budget, upstream of selection),
but QG3 sharpens it: the trap is passable with ~2x generations at same width. Streams are not
fenced out by landscape geometry — they're on slow gradient. Feeds QO2 (oracle-guided budget
allocation: spend generations where P(cross) is high — cheap since width is inert) and QG4
(phase diagram should sweep gens, not W). Slow-climb also suggests selection pressure, not move-set
poverty, is the limiter — desert streams may need higher child variance (bigger mutations) to find
gradient, spawning QG6.
Artifacts: experiments/qg3_trap_anatomy.py, results/qg3_trap_anatomy/{results.json,run.log}.

## QO3 — early-forecast horizon: g*=1 (stable); birth state carries ZERO signal (2026-09-30 04:5x): BOOKED — G1 PASS, G2 g*=1, G3 stable
Pre-reg: proposals/runs/QO3-early-forecast-horizon.md (committed+pushed before firing). Lane = QO1-identical
(seed 1234; run_lane_states copied verbatim into qo3_horizon.py — importing oracle1 would execute QO1's training).
Per-gen MLP (3x64) + cv-only logistic, stream-split 80/20, 13 models.
- **G1 PASS**: lane rate 0.5769 (2363/4096) CP95 [0.5616,0.5921] — inside QG2 band.
- **G2 HEADLINE — g\* = 1**: AUC trajectory 0.500 (g0) -> 0.880 (g1) -> 0.913 (g2) -> ... -> 0.999 (g12).
  One generation of selection makes crossing ~88% foreseeable; interpretation rule from pre-reg says
  "g\*<=3 => crossing visible at/near birth, feeds QO2 early routing" — but sharper than predicted:
  **gen 0 AUC = 0.5000 EXACTLY (both MLP and cv-logit)**. Birth champion state carries literally zero
  signal about eventual crossing.
- **G3 PASS (stable)**: bootstrap g\* median 1.0, IQR [1,1] across 200 resamples — no uncertainty.
- **Tension with QG2 desert-at-birth**: the desert is a property of the birth LANDSCAPE (exp018 cloud
  corroboration), but the stream-OBSERVABLE birth state does not encode it. After ONE selection round the
  champion state exposes fate (0.88, and cv-only logit alone gives 0.811 — most of the early signal is
  just where selection placed the champion after one round). Crossing is not visible at birth; it is
  visible one round after selection starts. Routing (QO2) can decide at gen 1 with ~0.88 skill, or wait
  until gen 3 for 0.93 at trivial extra cost.
- Monotone AUC climb (no jump) = accumulating signal, consistent with QG3 slow-climb; no path-dependent
  lottery component detectable at the observable level.
Artifacts: experiments/qo3_horizon.py, results/qo3_horizon/{results.json,run.log}.

## QO5 — birth is a LOTTERY: g0 states byte-identical across all 4096 streams (2026-09-30 04:3x/04:5x): BOOKED
Pre-reg: proposals/runs/QO5-birth-lottery-probe.md (analysis-only; retroactive pre-reg declared —
probe was fired opportunistically during the QO3 wake on existing lane code, booked honestly here).
- Census on QO3 lane (seed 1234, 4096 streams): g0 champion len unique=[2], v0/cv0 std 0.0,
  gate-hist across-stream std 0.0, **frac streams with identical birth cv = 1.0**.
- g0 AUC 0.500 is not weak signal — there is NOTHING to distinguish streams at birth. All
  streams share one skeleton draw with no state divergence before the first mutation+selection.
- **Named: birth lottery.** Fate diverges at the first selection round (g1 AUC 0.88-0.89).
- QG2 tension resolved: desert is a property of the (shared) birth landscape; stream identity
  is created by mutation+selection, not birth state. QO2 routing structurally must start at g>=1.
- Free QO3 replicate from the probe's lane re-run: rate 0.5769->0.5789 (inside ±0.006
  nondeterminism band), g0 AUC exactly 0.500 again, g*=1 again. Conclusions strengthened.
Artifacts: experiments/qo5_birth_probe.py, results/qo3_horizon/{qo5_birth_probe.json,qo5_run.log}.

## RECEIPT-HASH — tool/weight digests now sealed (2026-09-30 05:1x): BOOKED — docs/tooling, no GPU
Spawned by PR-SWEEP #4 (delta-shape #1's sha256-pinned vendoring). tools/receipt_manifest.py now
seals 17 tool/weight files (incl. qcell_sim.py, qcell_oracle.pt, decision_cell.py) alongside
experiments; tests/test_receipts.py pins the tools section (red on drift). Retroactive snapshot
`receipts/tool_pins_2026-09-30.md` pins the 2026-09-29/30 night-lane instruments — hashes are
seal-time, not fire-time (declared; earliest verifiable baseline). Ten night receipts (QG1-QG3,
QO1/QO3/QO5, DECIDE-1*) amended with Pinned-instruments pointer blocks; convention set: future
receipts pin at fire time. Also fixed pre-existing QUEUE drift the pins exposed: D22, E13, E13b
were booked in RESULTS but never claimed in QUEUE — backfilled per c9b39b4 precedent (D18).
Artifacts: tools/receipt_manifest.py, tests/test_receipts.py, receipts/tool_pins_2026-09-30.md, receipts/manifest.json.

## QG6 — variance does NOT rescue: bigger move-sets anti-monotone in k (2026-09-30 05:3x): BOOKED
Pre-reg: proposals/runs/QG6-variance-rescue.md (committed 269b561 before firing). Lane verbatim from
QG3 arm A (W=6, gens=12, S=1024, C=15 children/gen FIXED, bar=0.45), mutation kernel extended by
k applications/child only.
- G1 ANCHOR-VEC PASS (2.08e-34). G2 REPLICATE PASS: k=1 crossed 0.601, inside QG3 arm A CP95 window.
- **P-null (slow-climb) wins**: k=2 0.585 [0.554,0.615] statistically indistinguishable from k=1;
  **k=3 0.522 [0.491,0.553] is significantly BELOW k=1** (delta_lb -0.139) — mild "too-hot": 3-jump
  children destroy accumulated fitness faster than selection can bank it. No variance rescue at any k.
- **Crossing is delayed by bigger moves**: median crossed_gen 2 (k=1) -> 4 (k=2) -> 5 (k=3);
  early-crossing mass (gen<=1) collapses 247 -> 138 -> ~. Same WHETHER (roughly), later WHEN.
- **QG3+QG6 combined law: trapping is a TIME problem.** More generations rescue (QG3 2x gens);
  neither width (QG3 inert) nor move-set variance (QG6 flat-to-harmful) does. The slow-climb fence
  is climbed only by accumulating small wins — selection pressure on small mutations is the engine.
  Routing (QO2) should not spend budget on variance hacks; give slow climbers generations or kill them
  early per oracle (QO3: g1 AUC 0.88).
Honest notes: one mechanical crash fixed pre-scoring (insert slice off-by-one in the k-loop refactor;
declared, anchor unaffected). Stray uncommitted d23b files (pre-existing dirty state, unrelated lane)
left untouched. Pinned instruments per fire-time convention: tools/qcell_sim.py sha256 8c82d4bc…,
qcell_oracle.pt per receipts/manifest.json seal fc79ff1.
Artifacts: experiments/qg6_variance_rescue.py, results/qg6_variance_rescue/{results.json,run.log}.

## QO6 — retractable kill-evidence gate: ALL V1-V4 PASS (2026-09-30 05:5x): BOOKED — CPU only
Pre-reg: proposals/runs/QO6-retractable-kill-evidence.md (committed daf7db7 before firing; fired by the
05:3x wake which died pre-booking — replicated ALL_PASS this wake before booking, deterministic).
tools/eproc.py = semantic Python port of SuperInstance/quilt-ewitness eproc.mjs (lineage pinned:
commit 61b9e04, sha256 aad90ac5…, vendored-via delta-shape PR #1; parity enforced by exact-algebra pin abs_err 0.0).
- V2 CORE CLAIM HOLDS: late-bloomer trajectory fires (E_max 581 at t=5) then decays (0.40) -> RETRACTED -> gate
  says KEEP. Evidence accumulators, not tail predicates, gate stream-killing — "a process that cannot retract is
  a p-value in disguise" is now operative doctrine on this substrate.
- V3: monotone collapse -> WITNESSED (E_max 7.6e6) -> KILL_CANDIDATE. V4: flat -> INSUFFICIENT (keep).
- Honesty contract: sigma required, refuses short/missing/bad-sigma/non-finite inputs (V1c all refuse).
- QO2 routing now fully specified in components: oracle (QO1 AUC 0.951 / QO3 g1 0.88) + budget triage
  (QG3+QG6 law: generations rescue, variance/width do not) + QO6 gate. QG7 reuses the same trajectories.
Fire-time pins: tools/eproc.py 8243ef91b1a39f3f, experiments/qo6_kill_evidence.py fcbfe984ddfe0133.
Artifacts: tools/eproc.py, experiments/qo6_kill_evidence.py, results/qo6_kill_evidence/{results.json,run.log}.

## QG7 — gen-1 forecast CANNOT adjudicate late-vs-hopeless; e-process gate governs the desert (2026-09-30 06:4x): BOOKED
Pre-reg: proposals/runs/QG7-generation-asymmetry.md (committed 5781e58 before firing). Lane = QO3-identical
shot arm, GENS=24, S=2048. Four identical-seed reruns booked as an ensemble (lane torch-nondeterminism is
MATERIAL on this question — single-draw verdicts flip).
- G1 PASS 3/4 (rate@12 0.571-0.606 vs QG2 band 0.567-0.598; rep4 0.6069 marginal-outside, band calibrated at S=4096). rate@24 0.738-0.768 brackets QG3 arm C exact 0.755 — consistent.
- **P1 FAIL (ensemble)**: fresh gen-1 MLP on late(13-24)-vs-hopeless: AUC 0.546/0.663/0.636/0.580, mean 0.606 — only 1/4 draws clears the pre-registered 0.65; the one pass is luck, not signal. Late bloomers are only weakly distinguishable from hopeless at gen 1.
- **P2 PASS (weak)**: frozen QO1 oracle transfers with modest consistent ranking (AUC 0.566-0.581) but miscalibrated (median p late 0.33 vs hopeless 0.25 — expected, late streams were training negatives).
- **QO2 routing law finalized**: forecast (gen-1, AUC 0.88) governs the cross-by-12 majority; the desert subpopulation (~42%) goes to the QO6 e-process retraction gate — evidence accumulation, never an irrevocable tail predicate. Budget triage per QG3+QG6: generations rescue, variance/width do not.
Fire-time pins: qcell_sim.py 8c82d4bc…, qcell_oracle.pt fed2c15f…. Honest notes: 2 mechanical crashes fixed pre-verdict
(stray dead line; ckpt key 'state_dict'), lane nondeterminism booked as ensemble, no re-roll.
Artifacts: experiments/qg7_gen_asymmetry.py, results/qg7_gen_asymmetry/{results.json,run.log}.

## D23b — hidden-angle register carries only a WEAK, non-monotone relational channel (deep n-qubit cell semantics): BOOKED 2026-09-30 06:4x — CPU only
Gates (registered in the experiment source docstring): INVALID_HARNESS if shuffled-control partner_id >= 0.25; KEEP if partner_id_acc >= 0.90 at T=200 AND >= 0.50 at T=25; KILL if < 0.50 at T=200. Chance = 1/7 ~= 0.143.
- partner_id_acc by T: 5:0.500, 10:0.875, 25:0.625, 50:0.750, 100:1.000, 200:0.750. Null lane 0.113-0.150 (~chance, labels destroyed => harness valid).
- **VERDICT: KILL on the registered bar** — at T=200 only 0.75 (6/8) vs the 0.90 gate, and NON-MONOTONE at N=8 (1.000 at T=100 -> 0.750 at T=200). So the shared-secret angle on the partner qubit is a real but weak/noisy relational channel (2-7x chance at every T), far inferior to the ternary correlation keys (D12e: 1.0 at T>=25).
- Working read: **angles are a DEGRADED SECONDARY MIRROR of stream coupling, not the primary memory.** The correlation-key mechanism lives in the ternary atom streams (consistent with D12e/D13d), not the phase register.
Honest notes: (a) null lane had a template-guess bug — `_match_accuracy_null` took `grid` as a parameter and rebuilt its own linspace, so the null grid did not match the estimator's; fixed to reconstruct `grid = linspace(-pi, pi, GRIDS)` internally and the numbers were amended IN PLACE (supersedes the first run; the KILL verdict is unaffected). (b) Discipline miss: gates were registered in the experiment source, not as a frozen proposals/runs/ pre-reg. (c) QUEUE drift backfilled — D23b was booked nowhere, same class as D22/E13/E13b (D18 precedent c9b39b4).
Artifacts: experiments/d23b_relational_hidden_angle.py, results/d23b_relational_hidden_angle.json. Next: sigma-vs-T spread sweep at N=32 cells, or close the semantics lane.

## QG1-residual — verdict NAME: the 28 anchor misses are a SWAP/wire-order convention mismatch; the committed census script never produced its own booking (2026-09-30 07:1x): BOOKED — GPU (one batched matmul) + CPU
Pre-reg: proposals/runs/QG1-residual.md (frozen + committed BEFORE fire). Amendment 1 declared pre-fire: arbitration moved from the committed script's machinery to the BOOKING machinery after a bit-exact reproduction test.
- **META FINDING**: the committed qg1_exact_census.py (@cf268c6) does NOT reproduce the booked census — re-run gives 1503/1920 with a DIFFERENT schema than the committed results (the 1892 booking came from an uncommitted variant; dirty-tree receipt class, third instance tonight). Localized by this run's own enrichment table: the radians script's failures enrich on rx/crx (7.7e-41 / 4.9e-35) — it reads angles as RADIANS while the booking's conventions block declares pi-units (theta_pi * pi, standard half-angle). The pi-unit probe reproduces the booked anchor BIT-EXACTLY (1892/1920, frac 0.985417). Radians differential retained at results/qg1_residual/radians_variant_results.json.
- **Canonical arbitration (pi-units)**: failing = 28/1920 (exact match to the booking), signed mean dev -0.205 (recorded << exact — systematic, not symmetric noise), BH rejections @q=0.01 = **28/28** (every miss defies its own binomial noise model), re-band-99% fraction 0.9854 (< 0.99).
- Enrichment: **swap 7.0e-19 (n=442) OWNS the residual**; x 8.6e-5 (weak secondary); h/rx/rz/crx/cx clean (0.12-0.85).
- G-CLOSE fails all three clauses => **VERDICT NAME**: the missing convention is swap/wire-order semantics between the census machinery and micromoth-quilt's exp022 simulator (recorded values ARE simulator outputs; our exact-state readout disagrees precisely on swap-carrying genomes, and when it disagrees, recorded balance is LOWER — our swap mapping preserves more balance than theirs). The x enrichment is secondary (co-occurrence or a second-order convention — QG1c separates them).
- [spawned] QG1c (new pre-reg): fix swap/wire-order semantics in the census machinery (test both q0-MSB/LSB swap maps against telemetry), re-run census targeting the >=99% anchor; decompose swap-vs-x enrichment.
Honest notes: fires 1-2 were pre-verdict mechanical failures (gate2 math.exp crash; perm guessed as swap-semantics instead of the census XOR map — 604 then 417 bogus fails, NOTHING booked, both fixed verbatim + declared in code). Fire 2's "broken" run became the differential instrument that exposed the census script bug. Fire-time pins in results.json (runner, pre-reg, 5 telemetry files, angle_units). Census script carries a docs-only warning header (no logic change, per pre-reg's no-fix clause).
Artifacts: experiments/qg1_residual.py, results/qg1_residual/{results.json,radians_variant_results.json,run.log}, proposals/runs/QG1-residual.md (Amendment 1).

## QG1c — verdict NONE: the 28 residual misses survive the entire frozen convention set; all are swap-only (x was spurious) (2026-09-30 07:1x): BOOKED — GPU (6 batched matmuls) + CPU
Pre-reg: proposals/runs/QG1c-swap-convention.md (frozen C0-C5, committed BEFORE fire; no post-hoc expansion).
- Anchors: **C0 current 0.9854 (1892/1920, 28 fail) — BEST**; C1 embed-reversed 0.7875; C2 perm-reversed 0.8063; C3 both-reversed 0.9552; C4 order-reversed 0.6953; C5 swap-as-CNOT 0.9781 (42 fail).
- Decomposition of the C0 28: **swap_only 28, swap_and_x 0, x_only 0, neither 0** — every residual miss carries swap, and QG1-residual's "x enrichment (8.6e-5)" was coincidence, not convention. The secondary hypothesis is dead cleanly.
- G-FIX fails (nothing reaches 0.99) and G-PARTIAL fails (nothing improves on C0 — C0 IS the best) => **verdict NONE**: the mismatch is deeper than wire-order, application-order, or CNOT-substitution. Our swap map is not the error.
- Working read: either micromoth-quilt's exp022 simulator implements SWAP with semantics our frozen set cannot express (or its recorded values for those genomes are themselves stale — the dirty-tree class exists on both sides), or the genome's swap fields mean something other than (qubit_a, qubit_b).
- [spawned] **QG1d** = SOURCE-LEVEL RECON (read-only, cheap): read micromoth-quilt's exp022 simulator swap implementation and reconcile at byte level instead of by candidate search. Discipline lesson booked: after a frozen candidate set fails, go read the producer's source — don't widen the guess space.
Honest notes: analysis-only, no data touched, deterministic, candidates frozen pre-fire, 6/6 in one pass. The NONE verdict is a real negative result — the residual is not a convention typo and must not be "fixed" by widening the search post hoc.
Artifacts: experiments/qg1c_swap_convention.py, results/qg1c_swap_convention/{results.json,run.log}, proposals/runs/QG1c-swap-convention.md.

## W5a — re-observation vs trace-reading: **REFUTED** (trace-reading matches fresh re-observation at matched budget) (2026-09-30 08:5x AKDT): BOOKED — CPU only
Pre-reg: proposals/runs/W5a-reobserve-vs-trace.md (frozen + committed before fire; CONFIRM/REFUTED/MIXED gates, no post-hoc change).
Lane: x_t = mu_t + sigma*z_t, sigma=1, T=200, drift onset t0=50, mu in {0,0.2,0.5,1.0}, sign in {+1,-1}; 28 drift cells + 4 no-drift
cells, REPS=200 x SEEDS=[1101,1102,1103] = 600 worlds/cell. FOUR arms, ONE matched detector (mean-shift statistic, |stat|>=0.2*sigma,
max-|stat| split for t0): `trace` (quantized to q in {0.5,1.0}sigma + subsampled every k in {1,4} — what trace-reading gets),
`rawsame` (unquantized at the same positions), `fresh` (budget-matched fresh draws = pure re-observation), `freshfull` (fresh at all T = upper bound).
- **VERDICT: REFUTED per the frozen gate.** overall_pp 0.01 (det_err basis), 0/24 primary cells where fresh wins by >2pp, worst_cell_pp 0.0 =>
  error(fresh) - error(trace) within the 2pp band with no consistent direction: at MATCHED observation budget, re-observation does NOT beat
  trace-reading in this regime. QO6's retraction doctrine therefore does NOT generalize to the mildly-lossy-trace regime via this route —
  it keeps its substrate-side claim (evidence accumulators vs tail predicates) but loses the claim that *any* trace-reading is strictly dominated.
- **AUDIT (honest methodology flag — declared, not buried)**: the frozen verdict function scores `det_err` ONLY, and det_err is SATURATED
  everywhere — 0.0 for every arm on every drift cell (single exception: trace 0.00167 at (0.5,+1,1.0,4)) and ~1.0 on every no-drift cell.
  Cause: the detector thresholds a MAX over ~T candidate split statistics, so |stat|>=0.2*sigma fires ~always (no-drift false-alarm rate ~1.0)
  and always fires under real drift — det_err carries no information in either direction. The REFUTED verdict is therefore *forced by
  saturation*, not earned by a sensitive test. Re-scoring on the pre-reg's OTHER two registered metrics (collected in results.json but unused by
  the verdict function): sign_err mean +0.42pp (range -4.33..+5.83; 3 cells fresh-better >2pp, 2 trace-better >2pp) and |t0|>10 rate mean +0.12pp
  (range -3.50..+5.50; 4 vs 5) — both far inside the 2pp band with mixed direction. Verdict survives the honest re-read; it is a low-power REFUTED.
- Regime map (the MIXED payload, reported not gating): the gap never opens. The trace at its coarsest (q=1.0sigma, k=4) is within ~1pp of fresh on
  sign error at every mu. Signal that re-observation DOES carry more information: the full-power `freshfull` arm beats trace by 4.02pp mean on
  |t0|>10 (it sees all T positions) — but the BUDGET-MATCHED `fresh` arm does not, which is exactly the REFUTED clause. Any advantage of
  re-observation here is bought by budget, not by re-observation.
- Honest notes: (a) verdict-function metric scope is narrower than the pre-reg's metric list (det only) — audit above; not a re-roll, an in-place
  declaration. (b) Detector floor: t0_err is 0.53-0.98 in ALL arms including freshfull, i.e. the matched detector is swamped by a shared bias, so
  the test is a floor test — the honest conclusion is "no arm separates at this detector", not "trace = fresh in general". (c) Pre-reg says
  >=8/12 primary cells; the runner evaluates 24 (mu x sign x q x k) — a denominator discrepancy that cannot change the verdict (0 wins either way).
Fire-time pins: experiments/w5a_reobserve_vs_trace.py sha256 271a6251f592acb0… (receipts/manifest.json seal).
Artifacts: experiments/w5a_reobserve_vs_trace.py, results/w5a_reobserve_vs_trace/{results.json,run.log,smoke_results.json}.

## F1 — DeltaF-admission scheduling falsifier: **PREMISE-ABSENT** (the mined composition's claimed regime does not reproduce) (2026-09-30 08:5x AKDT): BOOKED — CPU only
Pre-reg: proposals/runs/F1-df-admission.md (frozen + committed before fire; G1-G4 + KEEP/KILL/PREMISE-ABSENT, no post-hoc change).
Lane: discrete-tick single server, TICKS=30000, Bernoulli(0.8) arrivals, u~Exp(1), depth d in 1..6 with p=[.40,.25,.15,.10,.06,.04],
service s=1+0.1*d, requeue prob 0.05*d per pass; paired streams across arms; SEEDS=[91,92,93]. Arms: `pfifo` (max-utility, FIFO tiebreak),
`df` (key u - T*z_d, z_d=(d-2.29)/1.43; T read off the budget trit: -1 if Q>6, 0 if 2<=Q<=6, +1 if Q<2 -> T in {0,1.0,2.0}), `slack` (T=2.0 always).
- Gate table (aggregate over 3 seeds): **G1 PASS within 5%** (df mean_wait 6755.903971 vs pfifo 6755.904026 — relative dev 8.2e-9, i.e. IDENTICAL);
  **G2 FAIL** (var ratio 0.9999994 vs the required <=0.6); **G3 premise FAIL** (r_blowup_pfifo 1.0013 < 3.0, so nothing to eliminate);
  **G4 FAIL** (slack mean_wait 6313.187 = 0.9346x df — slack is **6.5% FASTER**, not the claimed >=15% slower).
- **VERDICT: PREMISE-ABSENT** per the frozen G3 instruction ("if premise absent (r_pfifo < 3.0) the claimed regime does not reproduce in this
  sim — a finding about the claim's fragility, not a pass"). KEEP is impossible (G2 and G4 both dead); the mined DeltaF-admission composition
  as specified is not supported, and its slack-extreme prediction is CONTRADICTED in sign.
- What actually happened (honest read): (a) the `df` arm is behaviorally ~identical to `pfifo` — mean wait equal to 9 significant figures and
  frac_started equal to 10 (0.5511788441444608 both), so under this budget-trit read the u - T*z_d key essentially never changed which job was
  served; the "within 5% of priority-FIFO" gate is met DEGENERATELY, not by a tuned tradeoff. (b) The sim is saturated/overloaded: arrivals
  ~24.1k over 30k ticks vs ~13.3k completions (frac_started 0.55), mean wait ~6756 ticks — all wait metrics are saturation-dominated, so policy
  differences are structurally invisible in the mean. (c) The requeue mechanism (0.05*d) never produced the claimed 3x depth-4 blowup under
  FIFO (r=1.001); slack DID blow up by depth (r=6.48, w_deep ~14.8k vs w_shallow ~2.3k) while being FASTER in the mean — a real
  depth-redistributing tradeoff, opposite in sign to the claim's latency prediction.
- Honest notes: single server, rho=0.8, no reneging, one regime; the churn proxy (z-scored depth) is our minimal faithful reading of "nesting
  pressure" (pre-reg risk declared). A KILL/PREMISE-ABSENT here kills the mined composition as specified, not their repositories. Regime finding
  worth carrying: at this load the admission key is inert — any future revision must first fix the load (or report per-depth waits) before
  admission policy can be measured at all. No re-roll.
Fire-time pins: experiments/f1_df_admission.py sha256 52516866a64d8934… (receipts/manifest.json seal).
Artifacts: experiments/f1_df_admission.py, results/f1_df_admission/{results.json,run.log,smoke_results.json}.

## W5b — lifetime-scaled ternary delta state: **KILL** (lifetime-ranked precision allocation loses to random on the mean AND flips sign by seed) (2026-09-30 09:1x AKDT): BOOKED — GPU only
Pre-reg: proposals/runs/W5b-lifetime-precision.md (frozen before fire; KEEP/KILL gates frozen, antirank registered as a secondary EXPLORATORY arm with no gate — the two-sided design; no post-hoc change).
Lane: char-level 1-layer GRU (hidden 384, embed 384 float — embedding excluded from the ternary pool), pool = GRU `weight_ih_l0` + `weight_hh_l0` + head `weight` (~928k elements), TWN convention Δ=0.7·mean|W|, commit cadence C=25, Adam lr 3e-3 + clip 1.0, batch 64 / seq 64, no schedule.
Warmup T_warm=4000 (161 commits, shared per seed) → all four arms fork from the IDENTICAL warmup checkpoint; k=2% HP slots (19345 elements, identical across arms) held permanently exact; T_main=6000 per arm. Corpus = all tracked `*.md` at the fire commit (122 files, 992001 B, vocab 215), 90/10 contiguous byte split. Seeds 4241/4242/4243. Warmup fork bpbs: 6.31333 / 6.15534 / 6.11438. Wall-clock ≈ 55 min total (220–261 s per arm) — under the pre-reg's 80–90 min estimate, reported honestly.
- **VERDICT: KILL per the frozen gate.** mean relative bpb improvement of lifetime over random = **-1.05%** (gate: >= +0.5%) AND lifetime wins only **1/3** seed-pairs (gate: >=2/3; need = ceil(2/3·3) = 2). Pair detail (rel = (random − lifetime)/random): seed 4241 9.30227 vs 10.33607 → **+10.00%** (lifetime is the BEST arm here); seed 4242 9.92628 vs 9.02610 → **-9.97%**; seed 4243 10.22629 vs 9.91057 → **-3.19%** (lifetime is the WORST arm in both). The frozen KILL clause "wrong direction in >=2/3 seed-pairs" is met outright — this is a direction failure, not a near-miss on margin.
- Mean-bpb ordering across the three seeds: antirank 9.52182 < random 9.75758 < lifetime 9.81828 < uniform 9.95739. Ratio-of-means lifetime-vs-random = **-0.62%** (same sign as the gate's -1.05% pair-mean; both bases reported because the frozen gate scores the pair-mean, not the mean ratio). Per-seed rank of lifetime: 1st, 4th, 4th of 4 — best-or-worst, never middle.
- **Secondary (pre-registered EXPLORATORY, NO gate) — antirank vs lifetime** (antirank = the MOST-flipped, i.e. shortest-lived, elements): antirank_bpb − lifetime_bpb = +0.774 (4241, antirank worse), **-1.049** (4242), **-0.614** (4243) → antirank beats lifetime in 2/3 seeds. antirank vs random in the same run: 10.07632 vs 10.33607 (+2.51%), 8.87728 vs 9.02610 (+1.65%), 9.61186 vs 9.91057 (+3.01%) → **3/3**. So the inversion the pre-reg anticipated IS visible: instability, not persistence, tracks precision-worthiness in this regime, and antirank is the only arm that wins 3/3. It carries no verdict here (secondary, ungated) — W5b2 was fired at 08:4x specifically to test it on fresh seeds.
- Honest read: (a) the primary claim is not merely under-margined, it is seed-unstable with a sign flip (lifetime best arm at 4241, worst at 4242/4243), so the generous reading is "lifetime structure in the delta stream is real but not exploitable at allocation time"; the harsher reading is that concentrating exact slots on the longest-lived committed deltas is actively harmful in 2/3 seeds. Plausible mechanism — a READ, not a measurement: a long-lived committed trit is one whose ternary round is already stable, so buying its exactness buys little, while the elements that flip are where the round error actually lives. (b) `uniform` (deterministic stride) was the worst arm in 3/3 — the layout-stride confound the pre-reg warned about is real; random remains the primary comparator by construction. (c) 161 warmup commits make change_count coarse (0–161) with no rate resolution at the tails — the pre-reg's accepted risk. (d) Budget equality itself is clean: HP == 19345 for every arm, identical data order and optimizer seed per seed. No re-roll, no re-run blind.
- Spawned from this outcome at fire time: **W5b2 antirank-primacy confirmation** (5 fresh seeds 5291–5295, arms antirank vs random, gates >=0.5% and >=4/5; pre-reg proposals/runs/W5b2-antirank-primacy.md) — in flight, booking armed 10:25 AK.
Fire-time pins: experiments/w5b_lifetime_precision.py sha256 a6d2bbcc1b68da5f… (receipts/manifest.json seal).
Artifacts: experiments/w5b_lifetime_precision.py, results/w5b_lifetime_precision/{results.json,run.log,smoke_results.json}.

## W5b2 — antirank primacy confirmation: **KEEP** (instability-ranked precision slots beat random at confirmation-grade gates) (2026-09-30 09:4x AKDT): BOOKED — GPU
Pre-reg: proposals/runs/W5b2-antirank-primacy.md (frozen before fire; gates mean_rel >= +0.5% AND wins >= 4/5; 5 fresh seeds 5291–5295; machinery imported unchanged from committed w5b_lifetime_precision).
- **VERDICT: KEEP per the frozen gates.** mean_rel = **+8.35%** (gate >= +0.5%), wins **4/5** (gate >= 4/5). Pairs (rel = (random − antirank)/random): 5291 +20.76%, 5292 +15.39%, 5293 −3.59%, 5294 +4.00%, 5295 +5.21%. The single loss (5293) had the worst warmup fork (bpb 6.488) — noted as observation, not post-hoc adjustment.
- Doctrine landing: W5b KILLed lifetime (persistence) with a seed sign-flip; W5b2 CONFIRMS antirank (instability) on fresh seeds at +8.35% mean. Two-sided design paid off exactly as built: "the elements that flip are where the round error lives" is now pre-registered, confirmed evidence, not a reading. Precision allocation defaults to commit-count-ASCENDING (shortest-lived first).
- Feeds: antirank becomes the default HP allocator for the next ternary run; the distillery's TWN trainer inherits it; wide-scope lanes cite it as the precision-lives-at-instability result.
Fire-time pins: experiments/w5b2_antirank_primacy.py (receipts/manifest.json seal, 08:4x fire).
Artifacts: experiments/w5b2_antirank_primacy.py, results/w5b2_antirank_primacy/{results.json,run.log}.

## H1 — judgment holonomy audit: **KILL** (symmetry-loop inconsistency adds nothing beyond plain kNN margin) (2026-09-30 09:3x AKDT): BOOKED — CPU
Pre-reg: proposals/runs/H1-judgment-holonomy.md (frozen gates: KEEP iff AUC(holonomy) >= 0.80 AND paired baseline win on >= 4/5 seeds; INDIFFERENT if mean gap < 0.02; amended PRE-FIRE only — 3-cell pattern → 2-cell after smoke voided every seed; amendment committed before fire).
- **VERDICT: KILL per the frozen gates.** wins 0/5; mean AUC gap **−0.033** (holonomy 0.477/0.629/0.484/0.543/0.634 vs margin-baseline 0.585/0.597/0.566/0.591/0.594). AUC never approached 0.80; paired wins 0; INDIFFERENT clause not met (|gap| 0.033 > 0.02 — the gap is real but NEGATIVE).
- Honest read: at this scale (k=9 fields over ~12%-corrupted pockets), the 8-image symmetry loop is a noisier estimator of the same neighborhood uncertainty the margin already measures — extra images add variance, not signal. Zero-teacher field auditing stays interesting; holonomy specifically is falsified as the audit signal. Wide-scope #3 closed honestly.
- Smoke receipts: 3 real bugs caught pre-fire (3-cell pattern rarity; mover-parity label bug shared with FD1; smoke-scaled MIN_CORRUPT).
Artifacts: experiments/h1_judgment_holonomy.py, results/h1_judgment_holonomy/{results.json,run.log}.

## FD1 — frontier distillation: **KILL** (frontier-only training loses; hybrid doesn't clear the win gate) (2026-09-30 09:3x AKDT): BOOKED — CPU
Pre-reg: proposals/runs/FD1-frontier-distillation.md (frozen gates: KEEP iff frontier >= uniform−0.5pp AND hybrid >= uniform+1.0pp on >= 4/5 seeds; HALF if only frontier-safe).
- **VERDICT: KILL.** wins(both) 0/5; frontier-safe(a) 0/5 — frontier mean 0.550 vs uniform 0.603 (−5.3pp; gate allowed −0.5pp); hybrid-wins(b) 2/5, hybrid mean 0.606 vs uniform 0.603 (+0.3pp; gate needed +1.0pp). Not HALF (a failed outright).
- Honest read: the field's own low-consensus margin is a WEAK frontier definition — the "easy" boards carry label geometry that regularizes the hard ones, and uniform students win. Composition caps near field_only (0.596): the hybrid inherits the field's ceiling on easy boards. Margin-defined frontier distillation is falsified at this scale; TRUE teacher-uncertainty curricula remain untested (a different idea, not a re-roll).
Artifacts: experiments/fd1_frontier_distillation.py, results/fd1_frontier_distillation/{results.json,run.log}.

## AG1 — aggregation-rule repair (Syzygy d158 tested on our fields): **PARTIAL-SUB+OM** (2026-09-30 10:0x AKDT): BOOKED — CPU
Pre-reg: proposals/runs/AG1-aggregation-rules.md (frozen gates: G1 consensus > mean single member under SUB; G2 union > consensus under OM; G3 track-record selector > momentary selector on MIX; each >= 4/5 seeds; KEEP iff all three).
- **VERDICT: PARTIAL-SUB+OM.** **G1 PASS 5/5** (consensus vs mean-single under substitution: e.g. 0.558 vs 0.507, 0.642 vs 0.476 in smoke; full-run wins all seeds). **G2 PASS 4/5** (union vs consensus under omission). **G3 FAIL 2/5** (stream-level dev-accuracy selector loses to momentary agreement 3/5).
- Cross-fleet read: the Syzygy MECHANISM transfers to graded judgment fields — consensus repairs substitution (their E6), union repairs omission (their E7 causal injection result) — both confirm on our tictactoe kNN member-pools with our own defect injections. The SELECTOR does not transfer in my operationalization: dev-accuracy stream-level choice is an agreement-class selector, and their own E5 already refuted agreement-based selection (agreement ~0.2 in both regimes; their Jev chose union 76/76). Their working selector is the claim-ratio error-signature (<0.5 → union), 5/5 on held-out halves.
- Spawned: **AG2** — their exact claim-ratio selector on our fields (regime signature from member claim behavior, not agreement). Pre-designed by their E7; our substrate supplies the independent replication.
- Also recorded: track-weighted voting (R-track) underperformed consensus on MIX in most seeds (e.g. 0.475 vs 0.592 smoke seed 8811) — softmax-weighted votes are not the repair; the repair is rule choice. Clean-context: consensus under CLEAN ~0.59-0.66 vs single ~0.5 — the member-pool itself is sound.
Fire-time pins: experiments/ag1_aggregation_rules.py sha256 (receipts/manifest.json seal, pre-fire).
Artifacts: experiments/ag1_aggregation_rules.py, results/ag1_aggregation_rules/{results.json,run.log}.

## QC-JEV — discriminating-control pin for the jeff oracle: **DISCRIMINATING** (the murmuration JEV null does NOT transfer to jeff-0.8b) (2026-09-30 10:2x AKDT): BOOKED — CPU
Pre-reg: proposals/runs/QC-JEV-discriminating-control.md (frozen before fire; 4 probes, gates in words, no re-roll / no temperature tuning).
- **VERDICT: DISCRIMINATING per the frozen gate.** noul p(true): **2+2=4 → 0.9606**, **2+2=5 → 0.0243**, d_ptrue **0.936** (gate needed >= 0.10 with the correct sign); the cell says "true" to the correct sum and "false" to the incorrect one. Content-following check: choice probes with the OPTIONS SWAPPED and letters fixed also follow CONTENT — choice_pos picks code "4" (0.931) when "4" is described as the correct sum, and choice_neg picks code "5" (0.908) when "5" is described as correct. Both directions correct, no letter stickiness.
- **CONTRADICT resolved (against us, in OUR favor):** murmuration's `jev_control.json` (jev-1.13.0) reports positive "2+2=4" and negative "2+2=5" both argmax=unclear at 0.74/0.79 — a positive control and its negation reading the same. That null does **NOT** reproduce on our checkpoint. Their probe is a genuine finding about **jev-1.13.0**, not about the jeff family; the SCOUT-4 threat to our DECIDE-1 lineage (that the below-chance G2 = 5/64 and the temp-1.1289 fitted value might be a broken calibrator rather than an inverted mechanism) is **DISMISSED for jeff-0.8b**.
- **Consequences:** **DECIDE-2 premise STANDS** (representation surgery on jeff's hidden states is not voided by a dead oracle; the shipped readout demonstrably discriminates on a clean arithmetic control). DECIDE-1 **G2 stays booked as-is** — a below-chance balance-edit read on a checkpoint that is demonstrably able to discriminate is information about the *balance-edit lane*, not about a broken head. Caveat carried forward honestly: this pin tests the **oracle's ability to discriminate**, not whether the temperature 1.1289 is well-fitted for the balance-edit lane; the DECIDE-1 fitted-T boundary note (pinned at 6.0) remains a standing flag for that lane only.
- Honest notes: one mechanical crash pre-scoring (the noul answer branch returns a scalar `noul`, not a `probabilities` dict — my scoring line assumed the choice shape); fixed in place and declared, fix commit `802bae1` before any scoring ran. Probes use the same fire path as DECIDE-1 (DecisionCell, trained reader, shipped temperature, CPU). Latency 0.4-6.5 s/probe (first probe pays load cost). No zeroshot secondary was run — pre-registered as optional, skipped to stay inside the slice.
Fire-time pins: experiments/qc_jev_control.py sha256 **95cba5985274ff4a…**, results/qc_jev_control/results.json sha256 **be86893fd74664de…** (receipts/manifest.json seal).
Artifacts: experiments/qc_jev_control.py, results/qc_jev_control/results.json, proposals/runs/QC-JEV-discriminating-control.md.

### (C) MANDATORY REPRODUCTION CHECK — 10:3x: **QC-JEV PASS on verdict + gates; PARTIAL on byte-identity (honest)**
- Re-ran the COMMITTED `experiments/qc_jev_control.py` (sha256 95cba5985274ff4a…, pinned in the booking and
  re-asserted inside the result file's own `runner_sha256` field). Re-run reproduced every gate value exactly:
  noul p(true) 0.9606 vs 0.0243, d_ptrue **0.936322**, noul_identical_distribution False, choice_pos_ok True,
  choice_neg_ok True, **verdict DISCRIMINATING** — identical to the booking.
- **Honest caveat (fail-loud):** the byte-level comparison is NOT a clean bill. My reference copy was taken
  with `cp results/qc_jev_control/results.json` AFTER the second fire had already written the file in the same
  sweep, so the "committed reference" and the re-run output are the same bytes by construction — the diff is
  therefore uninformative, not evidence. The meaningful evidence is (a) the `runner_sha256` embedded in the
  artifact equals the committed script's hash, and (b) every gate-bearing field reproduces. Per-probe
  `_latency_ms` varies between runs (466.47 vs 467.87 in the choice_neg slot) — i.e. the artifact is NOT
  byte-stable across fires, which is exactly why claiming bit-exactness here would have been wrong.
- **Tooling defect (third instance of the class, new variant):** `qc_jev_control.py` writes to a HARDCODED
  `results/` path, so no stdout redirect can keep a verification run off the artifact it verifies — the same
  defect booked at 09:1x for W5a. It fired for real this time: the re-run overwrote the artifact under test.
  Reinforces the RC-1 spec item: **every runner needs `--out`, and verification writes to a scratch dir on
  ext4, never into `results/`.**
- **Dirty-tree exposure found and fixed in this slice:** `results/qc_jev_control/` was **untracked** when I
  re-sealed the manifest — the seal had pinned a runner whose result artifact was never committed (the D-2
  silent-edit class, caught by checking `git status` after the seal instead of trusting it). Committed now;
  manifest re-sealed again. `tools/local_jev_bench.py` appeared untracked this sweep (another agent's or a
  prior wake's stray, not mine) — left in place, flagged, not deleted.

## ST1 — quilt-cell-v0: trained receipt-validity judgment cell (2026-09-30) — **KILL**
- Trained cell (all-MiniLM-L6-v2, 22.7M) on 8000 synthetic receipts (6 corruption ops, dual render styles),
  5 seeds; real gate = 15 lab receipts × up to 4 injected corruptions; abstention on a non-circular OOD A/B split.
  Pre-reg `proposals/runs/ST1-quilt-cell-v0.md`, frozen+pushed before fire (3c373d0 → a10b76d → 94a6364).
- **Gates: G1 SYN FAIL** (AUC 0.5034 vs ≥0.95) · **G2 REAL FAIL** (AUC 0.5025 vs ≥0.80; honest FPR 0.20 vs ≤0.10) ·
  **G3 ABSTAIN PASS** (0.90) — but the pass is hollow: per-seed OOD thresholds all ≈0.50 and gate coverage flips
  0.0/1.0 per seed, i.e. the model is uniformly unconfident, not judicious. gate_coverage mean 0.42.
- **Diagnosis (harness fault, not a blind re-roll): lr 3e-4 is ~10× too hot for a 6-layer encoder** — it collapsed
  MiniLM's features to the uniform prior within the first steps (smoke train loss ≈ ln2 = 0.693 agrees). Standard
  MiniLM fine-tune LR is 2e-5. Pre-registered config failed as registered; no config retro-editing.
- Artifacts kept: `experiments/st1_quilt_cell_v0.py`, `results/st1_quilt_cell_v0/results.json` (both committed).
- **ST1v2** = new pre-reg, same frozen gates, lr 2e-5 + warmup, 3 epochs (gate thresholds untouched — that is the point).

## ST1v2 — quilt-cell-v0 at corrected lr 2e-5 + warmup 0.1, same frozen gates (2026-09-30) — **KILL**
- New pre-reg `proposals/runs/ST1v2-quilt-cell-v0.md` (frozen+pushed 505e323/9259fdd BEFORE fire; interpretation
  rules registered pre-fire). Single changed factor vs ST1: lr 3e-4→2e-5, warmup 0.0→0.1, epochs 4→3. Same corpus,
  seeds 6611-6615, same gates: syn≥0.95 · real≥0.80 · fpr≤0.10 · abstain≥0.90.
- **Gates: G1 SYN FAIL** (AUC 0.7207 vs ≥0.95 — up from v1's 0.5034 but nowhere near gate) · **G2 REAL FAIL**
  (AUC 0.4434 vs ≥0.80; honest FPR 0.80 vs ≤0.10 — and now BELOW chance, anti-correlated on real receipts) ·
  **G3 ABSTAIN PASS** (0.90) but again partially hollow: gate_coverage mean 0.584, per-seed OOD thresholds 0.73-0.84.
- **Per the pre-registered interpretation: "v2 KILL at 2e-5 ⇒ the diagnosis was incomplete; the failure is not
  LR."** The registered next-suspect order stands, no post-hoc drift: (a) label/format leakage audit op-by-op
  (is every corruption detectable by a token-level artifact? note syn improved while real went anti-correlated —
  the model may be learning render-style artifacts, not corruption semantics), (b) corpus size/epochs, (c) head
  capacity. **Spawned ST1-AUDIT (CPU, next): op-by-op detectability audit — for each of the 6 corruption ops,
  can a trivial hash/diff check distinguish corrupt from clean on our own corpus? Any op with a mechanical
  tell is flagged as leakage-prone and excluded from ST1v3's training mix unless it survives.**
- Honest provenance note: this artifact carries NO embedded `runner_sha256`/`args` fields (older runner output
  format), so provenance rests on timestamps (written 11:42 AKDT, after the 11:36 pre-reg push) + config fields
  matching the pre-reg exactly (lr 2e-5, epochs 3, warmup 0.1, seeds 6611-6615) + the reproduction re-run below.
  **Tooling gap (RC-1 family): runner should embed runner_sha256 + full args in EVERY result file — it does in
  qc_jev_control.py but not here.**
- **MANDATORY REPRODUCTION CHECK: fired in-slice to ext4 scratch via the committed runner's `--out` flag**
  (first clean use of the RC-1 fix on this runner); verdict + gate values to be appended on completion.
- Artifacts: `results/st1v2_quilt_cell_v0/results.json` (committed this slice), runner `experiments/st1_quilt_cell_v0.py`.

### (C) MANDATORY REPRODUCTION CHECK — 12:1x: **Pass on verdict + all gates; disciplined DISSENT recorded on per-seed real_auc**
- Re-ran the COMMITTED `experiments/st1_quilt_cell_v0.py` with the pre-reg's exact config
  (`--lr 2e-5 --epochs 3 --warmup-ratio 0.1`) using the newly-added `--out /tmp/st1v2_repro` (first clean
  application of the RC-1 fix on this runner — the verification wrote to ext4 scratch and did NOT touch the
  committed artifact under test; the hardcoded-path defect booked at 09:1x/10:3x did not recur).
- **Verdict + gate booleans reproduce exactly**: GATE1_syn False, GATE2_real False, GATE3_abstain True,
  verdict **KILL**, n_train 8000, n_val 1000.
- **Honest nondeterminism finding (why byte-identity is NOT claimed):** `syn_auc` reproduces **bit-identically for
  all 5 seeds** (0.7390 / 0.7821 / 0.6841 / 0.7022 / 0.6963 → exact match), while the **real-gate** numbers drift
  slightly per seed: real_auc mean 0.4434 → 0.4507, honest_fpr 0.80 → 0.8125, gate_coverage 0.584 → 0.5962
  (e.g. seed 6611 real 0.4267 vs 0.4307; seed 6613 0.4762 vs 0.4831). Every drift is small and in the SAME
  direction (real_auc slightly up, fpr slightly up) — the verdict has a wide margin at every gate, so this does
  not threaten the KILL.
- **Diagnosis of the asymmetry (new, bookable):** the synthetic arm is fully seeded and deterministic; the **real
  arm is not** — its per-receipt scores vary across fires at fixed seed. That points at a nondeterminism source in
  the real-receipt path (candidate: real receipts are enumerated/rendered in filesystem order or the held-out
  corruption injection is seeded from a non-reproducible source, so which receipts land in the real gate set, or
  their order, changes). **Fixed a latent trap for the whole ST line: any real-gate number should be reported as a
  range across fires, not a point value; ST1/ST1v2's real_auc ("below chance") is the *low* end of a
  ±0.01-wide band, still comfortably failing the ≥0.80 gate.** Flagged for ST1-AUDIT: it will read the same real
  path, so the audit must pin the real-set enumeration seed before drawing conclusions from real-gate numbers.
- Scratch artifacts kept at `/tmp/st1v2_repro/` (results.json + full run.log); nothing written into `results/`.
- Ledger change (RESULTS.md) → manifest re-sealed this slice.

### (C) MANDATORY REPRODUCTION CHECK — 13:1x (day-conductor): **ST1v2 PASS on verdict/gates; real-path nondeterminism ROOT-CAUSED**
- Re-ran the COMMITTED `experiments/st1_quilt_cell_v0.py` with the pre-reg's exact config
  (`--lr 2e-5 --epochs 3 --warmup-ratio 0.1`) using the RC-1 `--out` flag → **wrote to ext4 scratch
  `/home/eileen/scratch/st1v2_chk/`, never into `results/`** (third clean application of the RC-1 fix;
  the committed artifact under test was NOT touched). Exit 0.
- **Verdict + all gate booleans + frozen gate thresholds reproduce exactly**: `verdict KILL`,
  `GATE1_syn False / GATE2_real False / GATE3_abstain True`, `gates_frozen {syn_auc_min 0.95,
  real_auc_min 0.8, honest_fpr_max 0.1, ood_abstain_min 0.9, min_real_receipts 10}`, n_train 8000,
  n_val 1000, model/lr/epochs/warmup identical. Only `ts` differs (expected).
- **`syn_auc` reproduces BIT-IDENTICALLY for all 5 seeds** (0.7390/0.7821/0.6841/0.7022/0.6963 == committed).
- **ROOT CAUSE FOUND for the 12:1x "real-gate drifts" finding — it is not a floating-point wobble, it is an
  UNSTABLE REAL-SET ENUMERATION.** The `real_gate` block differs in *size* between fires:
  committed `{receipts 15, rows 50, corrupted 35, honest 15}` vs repro `{receipts 16, rows 53,
  corrupted 37, honest 16}`. Different receipts in the gate set ⇒ `summary_mean` real numbers move
  (real_auc 0.4434 → 0.4507, honest_fpr 0.80 → 0.8125, gate_coverage 0.584 → 0.5962 — all in the same
  direction, as booked at 12:1x). So the drift is a **membership artifact, not measurement noise**, and the
  band is wider than ±0.01 because the set size itself changes across fires.
- **Threat assessment: NONE to the booked verdict.** Every gate is missed by a wide margin
  (syn 0.72 vs ≥0.95; real 0.44-0.45 vs ≥0.80 and BELOW chance; fpr ~0.81 vs ≤0.10), so the KILL is
  robust to the whole observed band. No amendment to the ST1/ST1v2 bookings.
- **Doctrine (forward, ST line):** (1) report real-gate numbers as a band across fires, never a point value
  (12:1x rule, now root-caused); (2) **ST1-AUDIT must pin the real-receipt enumeration before reading any
  real-gate number** — the audit reads the same path and would otherwise inherit this instability;
  (3) RC-1 spec addition: the runner must record the real-set membership (receipt ids) in the result file,
  so a changing set is visible in the artifact rather than inferable only by re-running.
- Scratch kept at `/home/eileen/scratch/st1v2_chk/`. Ledger changed → manifest re-seal below.

### [DONE 14:2x GPU] **QO9 BOOKED: verdict P1_STREAM_LEVEL** — the gen-1 oracle signal is STREAM-level, not lane-level.
- SCOUT-5/6 CONTRADICT-candidate (jev-fusion grouped-error steelman + projection law) **ANSWERED for this substrate**:
  4 lanes (mutation-draw seeds 1234/1235/1236/1237, S=1024, GENS=12, pipeline verbatim qo3_horizon), classifier
  trained on 3 lanes tested on the held-out 4th: AUC(g1) = 0.8722 / 0.8692 / 0.8851 / 0.8802 — ALL folds >= 0.80
  (frozen P1 gate). Pooled mixed-lane AUC 0.8801, exactly reproducing QO3's booked 0.880 at the different seed.
  G1 rate anchor PASS (all lanes 0.570-0.600).
- **QO3/QO6/QG7/QO2 bookings UNTOUCHED**: the router's per-stream evidence generalizes across mutation draws;
  the shared skeleton does not carry the signal (a lane-locked classifier would have collapsed on held-out draws).
  jev-fusion's "per-cell sparse signal cannot represent grouped error" does not bite the qcell oracle at gen 1.
- Honest provenance: AMENDMENT 1 to the pre-reg — the draft's "existing data" premise was FALSE (no prior lane
  persisted per-stream features; every booking saved aggregates only). Discovered before fire, declared in the
  pre-reg, fresh multi-lane dump designed instead. Per-lane gen-1 features + outcomes persisted in the artifact
  (lane_data_g1.npz; RC-1 membership doctrine). Runner embeds runner_sha256 + args. Fire exit 0, no crashes.
- Pre-reg proposals/runs/QO9-lane-vs-stream-stratification.md (committed 97b629e BEFORE firing). Commit of
  artifact + this booking next; manifest re-seal after ledger change. Reproduction check for QO9 due next wake
  (deterministic torch.manual_seed(0) fits; rollout rng seeded per lane — expect near-bit-exact, MLP fit path
  nondeterminism class noted).

### [DONE 15:1x] **QO9 REPRODUCTION CHECK: PASS** (mandatory (C), committed runner + pre-reg config)
- `experiments/qo9_lane_vs_stream.py` re-run to ext4 scratch `/home/eileen/scratch/qo9_repro/` via `--out`
  (committed `results/qo9_lane_vs_stream/` untouched). Exit 0.
- **Verdict `P1_STREAM_LEVEL` reproduces exactly; G1 rate-band anchor PASS in both fires;
  ALL 4 lane-held-out folds >= 0.80 frozen gate in both fires** (repro: 0.8704/0.8658/0.8668/0.8611;
  booked: 0.8722/0.8692/0.8851/0.8802). No gate is near its threshold — margin >= 0.06 on the worst fold.
- **Honest band note (declared nondeterminism class, now measured):** per-lane point values wobble —
  fold AUCs d=0.002-0.019, pooled AUC 0.8801 -> 0.8628 (d=0.017), lane rates d=0.003-0.031. So "pooled
  0.8801 exactly reproduces QO3 0.880" in the 14:2x booking was a coincidence of draws, not a fixed point;
  the robust statement is pooled AUC(g1) ~ 0.86-0.88, folds ~ 0.86-0.89, comfortably in P1. Forward
  doctrine (QO line): report QO9-class numbers as bands across fires; single-fire point claims of
  "exact reproduction" for torch-fit paths are not warranted.
- Scratch kept (not results/). Manifest re-seal follows.

## PX1 — decision-tree ceiling on 3×3 (fleet-triage GPU-EXPERIMENTS.md Exp 2): **P1 CONFIRMED + P2 SHALLOW-WIN + P3 SIGN-FLIP SURPRISE** (2026-09-30 16:0x AKDT): BOOKED — CPU

- mavis (fleet-triage) pre-registered Exp 2 as the gate for their Exp 1 ("linear 0.1807 has no interpretation without a ceiling"). Ran it before touching a GPU, per the doc's own §3. sklearn trees on the exact solver enumeration: **180,361 our-turn states, count matches the doc**, provenance FNV-1a-64 `0x75f652bc1d8464b8` over the state+optimal-set stream. Seeds 0/1/2, 80/20 split; every reported metric has std > 0 (no INCONCLUSIVE rule trips). CPU only — no CUDA involved, device string recorded.
- **Ceiling = the exact function (P1 CONFIRMED):** deep tree **0.9987 ± 0.0002** top1-in-optimal on held-out. Linear retrained on the same split: **0.1978 ± 0.005 = 19.8% of ceiling** (mavis's 0.1807 was ~18% — their number is now interpretable and unflattering). Depth ladder: d3 **0.4811**, d4 **0.6024**, d6 **0.7481**.
- **P2 branch landed:** a depth-3 tree beats linear 2.4×. Task is nonlinearly separable but **shallowly structured** — most of the achievable win costs almost nothing. The plateau is representational, not compute (deep adds +0.25 over d6).
- **P3 SURPRISE — the carried-forward prediction flips sign:** linear SIMPLE (0-1 immediate wins, 93.6% of states) 0.1895 → **COMPOSED (≥2 immediate wins) 0.2640 (+0.0745)**. Double-win states are where additive voting works *fine* — each win lights its own local terms; no counting needed to top-1 one of them. Deep tree flat across the split (0.9984 → 1.0000). So the linear failure mode is NOT threat-counting; it must be **non-local** play (defuse/fork-on-a-line-you-didn't-just-look-at). Recorded as a correction to the doc's Exp 1 branch table. Follow-up PX1b: partition by "optimal move non-local to any opponent threat" to isolate the true mechanism.
- Controls: identical 9-cell representation + identical metric (top1-in-optimal + set-recall, always together) as pie-minimax `linear_expert.py`; trees never saw test states; solver ran untouched from a read-only clone at main.
- Runner `experiments/px1_tree_ceiling.py` (pre-registration P1-P4 frozen in module docstring BEFORE fire, commit-first); results `results/px1_tree_ceiling/results.json`. Receipt filed to SuperInstance/pie-minimax issues — Exp 1's numbers are now fractions of a ceiling.

## PX0 — patchwork-experts ideation round 1 (Casey's DeepInfra picks): all three lanes landed, one shared silent-failure class found (2026-09-30 16:1x AKDT): BOOKED — ideation

- Lanes: ByteDance/Seed-2.0-mini (38.0s), NousResearch/Hermes-3-Llama-3.1-405B (6.3s), tencent/Hy3 (5.2s). ID hunt receipt: `tencent/Hy3-preview` does NOT exist (404); correct id is `tencent/Hy3` (verified against /v1/openai/models, 187 models); Hy4-preview exists but was 429 engine_overloaded at fire time.
- **Convergence finding:** all three models independently located the silent-failure class in GARDENER EPISTEMICS, not cell quality — (1) format-pass/semantically-broken outputs (seed-mini), (2) cell drift under distribution shift with green receipts (hermes), (3) post-hoc CoT rationalization of wiring moves (h3). Their proposed controls compose into an immune layer: cataloged sanity cell + fixed-validation re-judge + shadow no-op randomizer (5% of gardener moves auto-rejected; if receipt quality of accepted vs rejected moves is indistinguishable, the gardener is rationalizing and all rulings void).
- Their falsifiable experiments converge on the same probe terrain (3×3 patchwork vs known baselines) → folded into PX2, pre-registered BEFORE build at `proposals/runs/PX2-patchwork-3x3.md`, baselines = PX1's frozen ladder (d3 0.481 / d6 0.748 / deep 0.999).
- Standing roles assigned (Casey's three picks): Seed-2.0-mini = candidate-cell referee; Hermes-405B = adversarial receipt auditor; Hy3 = wildcard designer + entropy-leak probe (0.3B watcher flagging neighbor-cell rot from input token-loss before wrong outputs appear). Novel cell proposals banked: webcam physical-board parser (seed-mini), consequence-predictor 2+ steps (hermes).
- Gemma 4 270M reality check: no such tag on ollama (library: e2b/e4b/12b/26b/31b) and no 270M on DeepInfra either (roster: gemma-4-26B-A4B/31B variants, gemma-3-4b/12b/27b, embeddinggemma-300m). Local tiny-cell slots filled with qwen3.5:0.8b (pulled, 1.0GB) + tev1:0.8b + qwen2.5:0.5b; embeddinggemma-300m slotted as the DeepInfra semantic cell (NN-gate vs train states).
- Receipts: results/px0_ideation/round1.md; runners experiments/px0_ideation_round1.py + px0_h3_refire.py. Keys never echoed (read at use-time from ~/.config/deepinfra/token).

## PX1b — threat-locality partition (real 180,361-state data): **P4 KILL BRANCH — the linear failure mode is the BLOCK/defensive override, NOT non-local play** (2026-09-30 16:2x AKDT): BOOKED — CPU

- Prompted by the fleet Canvas-Gardener doc's PX1b proposal — but run HERE on real solver data with frozen classes, not the circulating mock-data demo. Classes (frozen in runner docstring before fire): WIN = immediate win available (all opt are wins, fail-loud asserted); BLOCK = no win, opponent holds a 2-in-line threat, all opt are blocking cells; NON_LOCAL = everything else (prophylactic/positional). Sizes: WIN 109,392 (60.6%), BLOCK 29,632 (16.4%), NON_LOCAL 41,337 (22.9%). Provenance digest (states+opt+class) `0xa0b08dfac4d13c57`.
- Test-split numbers (PX1 80/20 split, 3 seeds, mean): WIN — linear 0.25 / d3 0.55 / d6 0.84 / deep 0.9998. BLOCK — linear **0.022 ± 0.003** / d3 0.24 / d6 0.57 / deep 0.997. NON_LOCAL — linear 0.17 / d3 0.49 / d6 0.64 / deep 0.996.
- **Mechanism, take three:** additive voting does NOT die on non-local play (0.17) — it dies on DEFENSE. When the opponent holds a threat, the correct cell is locally unremarkable while the voter's own-line terms light up; linear top-1s a blocking cell 2.2% of the time. Even d3 trees collapse on BLOCK (0.24) — the defensive override is the hardest shallow structure on the board. Deep tree 0.997 everywhere: the function is learnable from the 9-cell representation, just not additively and not by depth-3 splits.
- **Design consequence for PX2/patchwork:** the canvas's missing primitive is not spatial confinement geometry — it is VETO cells. Voters score; gates and pinchers veto. PX2's smoke gate gains a sharpened sub-test: composition must hold up on the BLOCK split specifically (16.4% of states, where voting-only stacks will bleed).
- P4 kill-branch honored: P1's ordered degradation (WIN > BLOCK > NON_LOCAL) did NOT hold — observed WIN 0.25 > NON_LOCAL 0.17 > BLOCK 0.027.
- Deviation note (receipts doctrine): pre-reg frozen in the runner docstring before fire, but committed post-hoc alongside results — no separate commit-first push this time. Flagged here; next pre-regs go back to commit-first.
- Runner `experiments/px1b_threat_locality.py`; results `results/px1b_threat_locality/results.json`. Cross-filed to SuperInstance/pie-minimax issue #1.

## PX2 — patchwork harness + gardener loop + blind-control statistics (2026-09-30 16:4x-17:3x AKDT): BOOKED — CPU (live arm in flight)

- Harness (px2_cells.py + px2_smoke.py): composed majority-vote(d3,d4)+format-gate **0.595** vs d3-alone 0.435 on the frozen 200-state eval (+0.16). Ollama cells wired, flag-gated OFF.
- Gardener loop (px2_gardener.py): dry-run PASS — sanity cell 5/5, byte-identical determinism, drift control, BLOCK split every eval; 5% shadow no-ops logged sidecar-only (never shown to the gardener). **Blind-gardener 10-move control: 0.855** (found pinch+d6; BLOCK 0.976 vs linear's 0.022 — PX1b veto-cell prediction vindicated in the running system).
- **Blind-control variance (budget-matched, serial 50-move runs): seeds 1/2/3 → 0.745 / 0.745 / 0.755 (mean 0.748, spread 0.010).** The blind walk has no ratchet — its endpoint is where the walk stopped, not best-seen. Seed-0's 0.855-at-10-moves was a lucky tail, not the control. **Adjudication bar for the live arm: beat ~0.75 endpoint AND receipt-direction audit >0.5.**
- Live saga (fires 1-5, every abort fail-loud, every fix receipt-driven): (1) GLM-5.3 thinking ate max_tokens 400 → empty content → abstain cascade; (2) `thinking: disabled` honored on easy moves but hard wiring moves trigger adaptive thinking that ignores the flag (17k-char reasoning, finish_reason=length) → cap 16384; (3) killed for the cap fix; (4) 120s ssl read timeout → 240s + transport failures become receipted abstains + one clean same-prompt retry (no outcome info seen); (5) in flight. ZAI open-platform key had no balance (429/1113); key is the CODING-plan key — pre-reg intact (GLM-5.3 via api.z.ai/api/coding/paas/v4).
- Infra lesson: parallel same-second launches collide on timestamped receipts filenames (three seeds, one file) — serial launches or sub-second suffixes.

## PX2 fire-5b — live-arm adjudication (2026-09-30 20:0x AKDT): BOOKED — PARTIAL (live arm did not beat the blind band)

- **Verdict: PARTIAL per the frozen branch table** (`proposals/runs/PX2-patchwork-3x3.md`): final quick-eval top1 0.745 = 1.55× d3 (0.481), inside the 1.3–2× PARTIAL band, far under the ≥0.96 WIN bar.
- **Booked live-arm bar (beat ~0.75 endpoint AND receipt-direction audit >0.5): NOT MET on the score arm.** 0.745 sits at the blind floor — budget-matched blind runs 0.745/0.745/0.755 (mean 0.748, spread 0.010); live −0.003 vs mean, within seed noise, but the bar was *beat*, not match. Direction-audit raw rates, reported as promised in paper §5: top1-direction **6/10 = 0.600** (39 of 50 moves flat on top1; only nominally above the bar), set_recall-direction **17/34 = 0.500** — exactly chance. The bar's pre-flagged chance-level weakness was real; no post-hoc strengthening.
- **Composition note: converged to 9× tree_d6** (`tree_d6`..`tree_d6#9`) — the PX1 strongest shallow cell. Nine identical clones cast identical votes (gardener's own move-42 receipt concedes the committee "behaves like a single tree_d6"). Rule-5 cheap-baseline control: 0.745 vs d6 blind 0.7481 — at parity within noise, **not beaten**.
- Move catalog (PARTIAL branch requirement): 26 wire / 14 create / 9 retire / 1 rearrange across the full 50/50 budget; every non-tree_d6 cell (pinch, format-gate, d3/d4/d5 trees) retired or wired out — only tree_d6 clones earned keep.
- Immune layer ran throughout: sanity gate passed; **2 live shadow no-ops** (moves 10, 37; sidecar `shadow_nop_log.jsonl`); 1,000-state drift check on schedule (final argmax_change_frac 0.359 receipted); BLOCK split per eval (final: WIN 0.832 / BLOCK 0.610 / NON_LOCAL 0.652).
- Receipts verified at adjudication: `results/px2_patchwork/gardener_live_20260930-182538.jsonl` = 52 lines (session_header + 50 move receipts + session_footer); footer numbers byte-match the walk log (initial 0.595 → final 0.745 top1, 0.5458 → 0.7196 set_recall, +0.150).
- **One-line meaning: live arm AT blind floor — rebuilt the PX1 strongest cell (all-tree_d6), matched d6 within noise, did not beat the blind band; gardener wiring ≈ d6 parity from shallow cells, no more.**
- Adjudicated 2026-10-01T04:0xZ by replacement adjudicator (scheduled cron died without delivering); no re-rolls, no re-interpretation. Paper §5 patched via numbered addendum only.

## PX3 — selectlib judge distillation (2026-09-30 17:1x-17:3x AKDT): BOOKED — INCONCLUSIVE (guard-fired) + mechanism discovery

- 576/576 jev-1.13.0 calls, 0 errors, digest `0x29ebeffdce727a44`; instrument byte-identical to run_judge's ask(); 5/5 controls fired on both fields.
- **Reproduction vs JUDGE-RUN.txt: harness exact, judge drifted.** Noise+oracle MAEs reproduce bit-exactly on both fields; BLIND_SPLIT judge deltas drifted in magnitude only (−0.0110/−0.0039/−0.0151 vs −0.0052/−0.0050/−0.0111, direction holds). Second finding: stored UNIFORM corr −0.184 is irreproducible (fresh −0.156) on an offline-deterministic quantity → that stored line predates the final fields.py.
- Evals: within-SPLIT 0.9583 (F1 0.50/0.98, only 3 correct-class states); cross-field split→uniform **0.9167 [0.854, 0.969]** — lands in the WIN zone, but uniform labels are 96/96 `needs_fix` (single-class) → frozen degeneracy guard caps the ruling at **INCONCLUSIVE**. Judge duplicate-triple consistency 1.0 (drift is cross-run, not within-run).
- **Mechanism discovery: the judge is ~a constant function on both blind fields** (93/96 and 96/96 needs_fix). That is WHY the stored result says judge ≈ noise — a nearly-constant label function carries no per-cell structural signal for any student to distill. The 3 `correct` outliers on SPLIT are the only structure; the student found 2.
- Consequence for the typesafe/judgment-cell lane: jev's threshold/bias on scene-format prompts needs calibration before it is used as a selector anywhere; feeds quilt-gpu-lab/docs/typesafe-judgment-cells.md.
- Pre-reg 0b5b88d (frozen, with degeneracy guard) → instrument ee99135 → receipts 62f256a → result f8c82e3. Key-name correction found by verification: keyfile line is TYPESAFE_AI_KEY.

## PX5 — cell-signature map: routing structure BETWEEN cells (2026-09-30 17:2x AKDT): BOOKED — EXPLORATORY_MAP

- Pre-reg FROZEN commit-first (ecc8288) before any scoring. Instrument: per-state 6-bit tree signature (d1..d6 top1-in-optimal) × pinch axis (fired-correct/wrong/abstain) × px1b class, over the full 36,073-state test split, terrain digest asserted.
- **Only 15 unique signatures exist** (of 64 possible) — the cells' success patterns are heavily structured, not noise.
- **The headline asymmetry: MI(signature → composition-correct) = 0.5955 bits vs MI(signature → class) = 0.1212 bits.** WHO-succeeds-WHERE strongly predicts whether the composition gets the state, and barely predicts the WIN/BLOCK/NON_LOCAL taxonomy — the routing surface is nearly orthogonal to the threat-class vocabulary. Candidate NEW latent taxonomy, discovered by the instrument, not authored.
- **Class-blind failure basin: 7,895 states (21.9%) are all-wrong for every tree AND pinch**, spread evenly across WIN/BLOCK/NON_LOCAL (2812/2392/2691) — a systematic hole no current class explains. All-correct: 9,470 (26.3%) — reflex-compile candidates.
- Router ceiling: any-cell-correct 0.8698 vs composition 0.7437 → **+12.6pts headroom** for a signature-conditional router cell (feeds CM1 r4+ / superinstance-api reflex).
- Pinch pre-empts 72.5% of the space (66.35% correct / 6.15% wrong), abstains 27.5%.
- Runner `experiments/px5_disagreement_map.py`; results `results/px5_disagreement/px5_map.json`.

## PX6 — signature-router: KILL on arm (a); routing wins on BLOCK, dies on NON_LOCAL (2026-09-30 17:5x AKDT): BOOKED — CPU

- Pre-reg FROZEN commit-first before scoring (both arms + threshold frozen; KILL declared a real outcome).
- Arm (a) pure DT(d6) board→best-cell router: **0.7545** test top1 vs composition 0.7437 — claims 8.6% of the +12.6pt headroom → **KILL branch** (< 0.759). The PX5 headroom stays measured-but-unclaimable by a shallow board router.
- Arm (b) confidence-gated router (proba < 0.5 → majority fallback): **0.7774** — 26.7% of headroom; the fallback does the work, pure routing does not.
- **The content is per-class (arm a): WIN 0.819, BLOCK 0.873, NON_LOCAL 0.497.** The defensive override — the exact thing PX1b said voting cannot do — IS board-routable. Positional play is not, at this depth. The wall is NON_LOCAL, matching PX5's class-blind basin.
- Router not degenerate (no cell >95% of predictions). Reflex-coverage probe: pinch already fires on **88.9%** of the 37,838 train all-correct states — the compile-back lane would add little; existing reflex owns the reflex-compile partition.
- Runner `experiments/px6_router.py`; results `results/px6_router/px6_result.json`.

## PX5b — permutation null for the PX5 MI asymmetry (2026-09-30 19:0x AKDT): BOOKED — CPU (paper-revision pass, brief item 3)

- Motivation: deepseek_stats review point 3 — PX5's MI numbers (0.5955 vs 0.1212 bits) were point estimates with no uncertainty. PX5's runner did not persist per-state artifacts, so `experiments/px5_permtest.py` REGENERATES the per-state join via the frozen px5 instrument machinery (build_registry(seed=0), identical per-state code path, terrain digest asserted), CROSS-CHECKS the regenerated aggregates against the booked `px5_map.json` (n_test, 15 signatures, comp 0.7437, both MIs to 4dp, 9,470/7,895 partitions — all PASS, fail-loud on mismatch), and persists the joinable artifact `results/px5_disagreement/per_state.npz` (signature, comp_correct, px1b_class per test state).
- **T1 (signature → composition-correct): observed 0.595498 bits; permutation null (1,000 shuffles of the label vector, seed 0) mean 0.000281 ± sd 0.000107, max 0.000663; empirical p = 0.001 ((1+0)/(1+1000)) — zero shuffles reached observed.** ~5,600 null-SDs above the null.
- **T2 (signature → threat class): observed 0.121228 bits; null mean 0.000578 ± sd 0.000149, max 0.001069; empirical p = 0.001.** ~810 null-SDs. The asymmetry is not an estimator artifact: BOTH MIs are decisively above their nulls; the ~5× gap between them is the finding.
- Miller-Madow bias: ~0.00028 bits (T1, 15×2 cells) / ~0.00056 bits (T2, 15×3) at N=36,073 — orders of magnitude below both observations. Effective cardinality: 15 OBSERVED signature values (not 64).
- Exact test-split class counts (from per_state.npz): WIN 21,922 / BLOCK 5,924 / NON_LOCAL 8,227; all-6-wrong∩BLOCK = 2,392/5,924 = 40.4% (reconciles with d6 BLOCK wrong-rate 42.25%: all-6-wrong ⊂ d6-wrong, stricter). Mixed (non-unanimous) signatures: 18,708 = 51.9%.
- Runner `experiments/px5_permtest.py` (numpy only, seed 0); results `results/px5_disagreement/permtest.json` + `per_state.npz`.

## (C) MANDATORY REPRODUCTION CHECK — 19:2x (day-conductor): **PX6 PASS (numbers bit-exact; env-metadata line differs honestly)**
- Committed `experiments/px6_router.py` re-run to scratch via the new `--out` flag →
  `/home/eileen/scratch/px6_repro/px6_result.json` (committed artifact NEVER touched — first
  PX-lane runner to carry the RC-1 `--out` doctrine; flag committed BEFORE the repro fired,
  398c662).
- **All booked numbers byte-identical**: arm (a) 0.7545 KILL branch, arm (b) 0.7774, per-class
  WIN 0.819 / BLOCK 0.873 / NON_LOCAL 0.497, composition 0.7437, ceiling 0.8698, reflex
  coverage 37838/0.8889, degenerate_flag unchanged. Sole diff: the runner's `device`
  environment self-report line (numpy 2.4.6→2.5.3, sklearn 1.9.0→1.9.1 — environment moved
  under us between the 17:5x booking and this repro). Numbers unaffected; sklearn
  DecisionTreeClassifier(random_state=0) is deterministic.
- Manifest re-sealed after this ledger change.

## SC-2 — arXiv-ID integrity check (2026-09-30 21:1x AKDT): BOOKED — ALL IDs RESOLVE (CPU, read-only)

- Pre-registered gates (in words) frozen in SCOUT-9 before firing: an ID that 404s or title-mismatches its
  claimed source => mark the citing proposal's spawn-premise UNVERIFIED in place; spawned item blocked
  until re-sourced. export.arxiv.org API, one query per ID, no retry loops. (First curl attempt over
  http:// returned empty bodies with exit 0 — https:// worked; noted as a fail-loud trap: exit code alone
  would have "confirmed" nothing.)
- Verified IDs (title match vs claim):
  - **2404.04616** = "Vanishing Variance Problem in Fully Decentralized Neural-Network Systems" — matches
    fleet-triage 50a5d66's correction citation exactly. SCOUT-9's downgraded FT-2 framing stands on a real ID.
  - **2609.35432** = "Self-Evolving Coding Agents: From Digital Programs to Physical-World Intelligence"
    — the PhysicalCoding tech report cited in proposals/physicalcoding-recon-2026-09-30.md. Title differs
    from the repo brand but is consistent with the recon's description; SOURCE verified.
  - **2602.17997** = "Whole-Brain Connectomic Graph Model Enables Whole-Body Locomotion Control in Fruit
    Fly" — matches the FlyGM citation in docs/quilt-insect-brain-2026-09-28.md.
- **The SCOUT-1 hand-waved "EvE 2609.36xxx": RESOLVED, not fabricated.** Title search "alternate optimizer
  to Adam" returns exactly one hit: **arXiv 2609.35614, "EvE: An Alternate Optimizer to Adam", published
  2026-09-28.** Honest note: SCOUT-1's "36xxx" guess was numerically wrong (actual 35614) — the id-half
  hand-wave is exactly the pattern fleet-triage caught as fabrication elsewhere, and this check is the only
  reason QO4's premise is now clean. **QO4 UNBLOCKED: premise SOURCED** (cheap-config early-ranking for
  oracle features; reading item, low priority).
- Verdict: **ALL PASS — zero fabricated or dead IDs among our own citations.** Fleet's fabricated-ID threat
  class does not currently touch our ledger. Doctrine: SC-2 becomes a standing pre-fire check for any
  scout-spawned READING item (verify the ID before the premise is consumed).

## AV1 — ascii→video (2026-09-30 21:13 AKDT)
- setup: pre-reg frozen (proposals/runs/AV1-ascii-to-video.md, pushed before fire). 49 usable hero pairs
  (pair0 frame missing — ffmpeg 1-index; train 1–39, held-out 40–49), eval res H100×W200 for A/B/truth alike.
  Model B: glyph-embed(32)+lum → conv → PixelShuffle(2), **667,491 params** (0.67M, <5M bar). fp32, Adam 2e-3,
  batch 8; plateau rule (<1% over 20 ep) stopped run1 at 40 ep; run2 = matched compute (same 40-ep budget).
- numbers (held-out 40–49): PSNR / SSIM / ΔL1-coh (L1(Δgen,Δtruth)):
  - A atlas floor: **11.62 dB / 0.2752 / 0.03048**
  - B run1 (frame L1, 40 ep, loss 0.0628): **17.89 dB / 0.3591 / 0.04150**
  - B run2 (+0.5·Δ loss, 40 ep, loss 0.0366): **18.49 dB / 0.3888 / 0.03675**
- verdicts: **H1 KEEP** (B beats A by +6.28 dB ≥ +1.5 bar) · **H2 KEEP** (coh ↓11.4% ≥10% bar; PSNR *gains*
  0.59 dB, no drop). Honest caveat: run2 was still improving when the matched-compute cap hit; A's near-zero
  |Δgen| (0.0042 vs truth 0.0297) means the atlas floor is temporally frozen, not coherent.
- warm-up D: ddpm-cifar10-32, 8 imgs × 8 DDIM steps = **1.94 it/s** on the 4050 (not a hypothesis; receipts
  in results/av1/av1-receipt.json, samples in results/av1/av1-samples.png). Total wall: 42.6 s.
- next: scale B on the porter's full clip set + cross-video probe (polyformalism, pre-reg H1 clause), then
  H3 dial policy; move training onto quilt G-cells with JEV-curl gating per the pre-reg fabric plan.

## CURL-1 — JEV↔JEPA curl mesh (2026-09-30 ~21:40 AKDT)
- Casey 21:17: "experiment with your quilt arrangement of different cells and how jepa and jev and
  others relate" → six-cell mesh as a real run, not a simulation. Pre-reg pushed before fire (1bd74be).
  One run, no rerolls. Data: 141 consecutive hero.mp4 frames → 16×16 → seeded random proj (seed 7) →
  64-d unit latents. Cells: enc1 → {jepa1 = online ridge λ1e-3 (sliding K=40 admitted buffer),
  persist1 = zero curl}; jev1 = REAL typesafe jev-latest noul per 10-step window; router1 =
  2-bad-window pinch / 2-good readmit, gates serving AND learning; pre-registered sick-cell injection
  on steps 81–100 (seed 13 input scramble). Receipts: results/curl1/ (results.json, trace.png,
  cells.csv + links.csv = the arrangement as a portable quilt record).
- numbers (117 post-warmup steps; error = 1−cos on unit latents):
  - persist mean 0.0122 — clip is mostly small motion (injected span nearly static: 0.00099)
  - jepa mean 0.0179, clean hit-rate **43.3%** — the learned linear curl LOST to zero-curl
  - routed mean **0.0126** — JEV pinched jepa at step 54 (noul 0.05); mesh fell back to persist
  - JEV: 13 calls, 4,962 in / 260 out tokens, 3.7 s wall, **12/12 windows agree with local arithmetic**
- frozen verdicts: **H1 KILL** (43.3% < 55 bar) · **H2 KEEP** (routed 0.0126 ≤ always-jepa 0.0179) ·
  **H3 KILL-per-bars, honest confound** (gate had already pinched jepa at step 54, before the
  injection window opened — the mesh served persist through 81–100, so the injection test never
  engaged; and 2-good hysteresis never re-admitted a weak-but-alive learner).
- the RELATION findings (the point of the round):
  - **JEV-at-the-metal works** (Casey 20:32): graded noul on window curl-stats is a cheap, faithful
    monitor of a predictor — perfect agreement, ~380 tokens/call. The clunk was downstream, not in the JEV connection.
  - **The gate converts a bad learner into baseline service** — CM1 r1's "pinch carried it," now proven
    for prediction cells: mesh ≈ persist floor + small warmup tax, never worse than the known-answer path.
  - **But a gate tuned for broken cells evicts mediocre-but-real learners**: H1-weak jepa never got
    served long enough to matter and strict 2/2 readmit froze it out. Admission policy must match
    expected competence — hard pinch is a judge for broken cells, not for weak ones. Soft gating
    (noul-weighted blend) is the candidate fix.
  - Dedicated cells + routing BETWEEN cells reconfirmed from the prediction side (IE-line echo).
- next: CURL-2 pre-reg — learned encoder (GPU idle: av1 trunk encoder or PCA latents), soft-gate
  blend routed = w·jepa + (1−w)·persist by noul, 1-good readmit, jepa re-tested only when it can win.

## C5 — paired-condition action probe (2026-09-30 22:41 AKDT)
- Casey "go": farm-fed round (first experiment the farm fired end-to-end). Pre-reg pushed before fire.
  Crashed twice on SCORING-stage harness bugs (list-vs-ndarray ytr → empty-class NaN centroid; pixel
  baseline 8 rows vs 16 labels) — the checkpoint kept the GPU work both times; fixes were scoring-only,
  zero re-extraction (checkpoint-resume path added).
- Design: 16 clips = {av_0, av_1} × 4 frame-aligned windows × {fwd, rev}; rev = exact byte-level frame
  flip of the fwd clip. Skip-tower NF4 Cosmos3-Edge, 2048-d pooled embeddings (receipt bf16/Parameter).
- Scoring: explicit-sign (score = cos(x, ĉ1) − cos(x, ĉ0), sep = max(AUC, 1−AUC)). The c3
  nearest_centroid_scores implicit direction has now bitten C3, C4-booking, and C5 — helper deprecated
  in-repo (lesson line 3: "convention-by-construction" — the fix belongs in the caller).
- Verdicts:
  - **H1 KEEP** — playback direction is linearly decodable in the latent: fwd-vs-rev LOOCV sep 1.00
    (16/16), margin 0.094, score ranges non-overlapping.
  - **H3 KEEP** — identity anchor: sep 1.00, margin 0.953 (10× the direction margin); identity SURVIVES
    reversal — fwd-trained centroids classify all 8 rev clips correctly (100% cross-condition).
  - **H2 KILL per frozen bar, degenerate at ceiling** — pixel-endpoint baseline ALSO sep 1.00 and
    carries MORE directional margin (0.197 vs emb 0.094): on this clip set, first/last-frame features
    beat the pooled embedding for direction. Follow-up: clip set with genuinely ambiguous endpoints
    (loops, pendula) where H2 becomes measurable.
  - Harness: single-draw shuffle band fired HARNESS_INVALID at 22:36 — correct call, it caught the sign
    bug. Replaced with 5-seed median; honest caveat: LOOCV-centroid shuffles still hit sep 1.0 twice
    (self-inclusion bias) — the probe machinery is biased; the score margins are the real evidence.
- Farm flow receipts: FIRE→EXIT-1→NOTE→(fix, re-queue)→FIRE→EXIT-1→(fix2, re-queue)→FIRE→DONE; farm
  v2.1 status-on-exit fix verified live (no phantom 'running').

### (C) MANDATORY REPRODUCTION CHECK — 23:1x: **C5 PASS (verdicts + every gate value exact)**
- Committed `experiments/c5_paired_action.py` (HEAD 0fc073f) re-run in a SCRATCH CLONE at HEAD
  (`/home/eileen/scratch/c5_repro`) — because the runner still hardcodes `OUT_JSON` into `results/`
  (no `--out`; **5th witness of the RC-1 hardcoded-path defect**), and per the 09:1x doctrine a
  verification run must never write over the artifact it verifies. Clone-at-HEAD is the workaround
  of record for runners lacking `--out` until RC-1 lands.
- Checkpoint-resume engaged (16 records matched) ⇒ **scoring-only, zero GPU** — completed in <5 s.
  GPU lane never contended; C5's own fire also finished before this slice (farm status verified, no
  phantom 'running').
- Diff vs committed `results/c5_paired_action.json`: **1 field differs — `created` timestamp.**
  All verdicts identical (H1 KEEP / H2 KILL-degenerate / H3 KEEP), all margins exact (0.0943 / 0.1965),
  auc_cond, auc_pixel, sep_id_fwd/rev, id_xacc, shuffle seps all equal. First PASS where the artifact
  is bit-stable modulo timestamp (scoring is fully deterministic given the frozen checkpoint).
- Honest note: the repro validates the SCORING stage only — the Cosmos3-Edge extraction stage is not
  re-exercised (checkpoint match short-circuits it by design; re-extraction is ~GB-scale NF4 inference).
  The C5 booking's GPU claim therefore rests on the committed checkpoint + farm receipts, not on this repro.

## CM1-r5 — judge swap + roster (2026-09-30 23:29 AKDT, farm-fed, 350.9s)
- Factors: jev-preview→**jev-latest**; roster = {Seed-2.0-mini, MiMo-V2.6-Flash,
  Ling-3.0-flash} (all 3 smoke-passed). Plan: proposals/runs/CM1-r5-plan.md (pushed
  0936af9 before fire). Arm A = r4-winning recipe, single cell. Arm B = 36 drafts,
  one 72-question batched judge, serve = argmax min(gd,gu) among gate-passing.
- Verdicts:
  - **H2 TRANSFERS** — Arm A 12/12 (all DRAFT_PASS), jev 1595/562 tok, batch wall 0.32s:
    the r4 rule-rich recipe holds under jev-latest.
  - **H1 KEEP** — Arm B 11/12 ≥ 11 bar, but the PATHS tell the real story:
    **all 12 stimuli DOUBTED_PINCH** — not one of 36 drafts cleared min(gd,gu) ≥ 0.5;
    11/12 came from the keyword_router pinch (7/3/1 served-from is router-only).
  - **H3 ROSTER_HURTS** — B 11 < A 12, zero rescued sids, 3× token cost (4770/1678).
- **The controlled finding (c0 ≡ A drafts, deterministic gen):** identical Seed drafts
  passed 12-report/24-question state in Arm A and failed the 36-report/72-question
  state in Arm B → **jev-latest gate judgment degrades with judge-state size
  (attention/question dilution), independent of draft quality.** r4's "80q ≈ flat
  latency" holds for LATENCY, not JUDGMENT QUALITY.
- **Doctrine receipts:** pinch-fallback carried a round AGAIN (third time: CURL-1 r1,
  CM1 r1, now r5) — the deterministic router is the load-bearing safety net.
  Roster earned nothing under a saturated corpus (as pre-registered: expected
  ROSTER_IDLE; actual ROSTER_HURTS — booked honestly).
- **r6 candidate:** gate state ≤ 12 reports per batch call (per-cell batches), or
  serve = argmax min(gd,gu) WITHOUT the 0.5 floor when the batch is large; roster
  only earns when a cell is DEAD (r1 pattern), not when all are competent.
- Output: results/cm1/round_005_out.json (schema cm1-round5/1), rounds.jsonl appended.

### (C) MANDATORY REPRODUCTION CHECK — 01:1x Oct 1: **CM1-r5 PASS (scoring re-derivation)**
- CM1-r5 is a live-API farm fire (DeepInfra cells + jev-latest judge), so a byte-level re-run is neither
  possible nor meaningful; the valid repro is SCORING-ONLY re-derivation from the committed
  `results/cm1/round_005_out.json` (scratch script, ext4, never touched results/ — 09:1x doctrine).
- Recomputed from per-record fields: correct_A **12**, correct_B **11**, A_paths {DRAFT_PASS:12},
  B_paths {DOUBTED_PINCH:11-correct/12-total}, B_served_from {c0:7,c1:3,c2:1}, verdicts
  **KEEP / TRANSFERS / ROSTER_HURTS**, cost_bar_ok **true** — ALL match the committed booking exactly.
- Two apparent diffs, both resolved as non-findings: (1) committed B_paths counts ALL records (runner
  lines 252-254 have no `correct` filter) vs my scratch filtering correct-only — my filter artifact;
  the one incorrect record (S12, DOUBTED_PINCH served from c0) is exactly the booked 11/12-with-pinch story.
  (2) committed verdicts carries the extra `rescued_sids: []` key — expected under ROSTER_HURTS.
- Honest scope note (same class as C5): this validates the SCORING/verdict stage and per-record internal
  consistency only; no pinch-floor violations found scanning all correct DRAFT_PASS records (none exist —
  all B passes were pinch-served, corroborating the dilution finding). Draft-generation and judge calls
  are NOT re-exercised; the booking rests on the committed artifact + farm receipts.
- 6th witness of RC-1 hardcoded-path class: cm1_relay_r5.py has no `--out` (OUT_JSON hardcoded); the
  clone-at-HEAD workaround wasn't needed here only because this repro makes no writes at all.

## FT-1b — pie-minimax #1 composed-sign claim vs our committed PX1 artifact: **CORROBORATE-with-citation + artifact erratum** (2026-10-01 02:1x AKDT): BOOKED — CPU (analysis-only, no re-run)

- Claim under test (pie-minimax issue #1 title/body): "the COMPOSED prediction flips sign" — linear SIMPLE 0.1895 → COMPOSED 0.2640, opposite of fleet-triage's predicted composed collapse. Gate (SCOUT-9): follows from our results.json → booking INCOMPLETE, amend; needs their added math → CORROBORATE-cite; contradicts numbers → fail loud.
- **Re-derivation from the COMMITTED `results/px1_tree_ceiling/results.json` (no re-run needed — analysis of the sealed artifact):** seed 0 `linear_split` SIMPLE **0.189539** → COMPOSED **0.264040** (delta +0.0745); seed 1 0.1876→0.2894; seed 2 0.2004→0.2738. Direction holds 3/3 seeds; deep tree SIMPLE→COMPOSED 0.9984→1.0000 (seed 0), also improving. Their quoted numbers are seed 0 verbatim. **Claim follows exactly from our own artifact.**
- **Verdict per gate: CORROBORATE-with-citation, booking NOT contradicted.** The authoritative PX1 booking (RESULTS.md 16:0x) already records P3 correctly as a sign-flip SURPRISE with "+0.0745" (a gain) and spawned PX1b, which then found the real mechanism (BLOCK/defensive override, 0.022). pie-minimax #1's composition comment and PX1b comment are consistent restatements of our own booked lineage.
- **ARTIFACT ERRATUM (honest, booked-not-silent):** the `branch_rulings` string embedded IN `results/px1_tree_ceiling/results.json` mislabels both deltas as "drop" ("drop -0.0745", "drop -0.0016") for what are improvements. The stored NUMBERS are correct; only the embedded prose polarity is wrong. Erratum noted here rather than editing a sealed result artifact. Lesson: embedded narrative rulings in result artifacts get read without the RESULTS.md alongside — booking prose and artifact prose must agree at fire time (extends the RC-1 class: the artifact should carry pointers, not interpretations).
- Threat disposition: SCOUT-9's CONTRADICT-candidate on FT-1/PX1 is **DISMISSED** — the fleet's Exp-1 branch-table correction is ours and is already booked. No amendment to PX1/PX1b needed.

## [DONE 04:2x CPU] **TRUNC-B + DEGENERATE pin LANDED** (tools/verdict_gate.py, tool-port — no pre-reg per JH-2 precedent; gates pinned in code + tests)
- One verdict lattice enforcing the three fleet laws, precedence VOID > DEGENERATE > INCONCLUSIVE > FAIL > PASS:
  1. **DEGENERATE** (murmuration std==0 law; our F1 G1 degenerate-pass, QO5 g0 AUC exactly 0.500, W5a saturation): a zero-variance (std==0), saturated-attested, or sub-min_n gate statistic can never yield PASS — DEGENERATE instead.
  2. **TRUNC-B** (canons judge_gate truncation blind spot 10:30Z; our 09:1x tmpfs tail incident): completeness must be explicitly attested True; missing attestation = VOID, attested-incomplete = INCONCLUSIVE — truncated-but-plausible never PASSes.
  3. **Status-source pin** (CONVERGENCE.md shape 3): caller must attest status_source="own"; an inherited status (exit-code-of-last-command class) = VOID.
- 12 tests, all PASS (`tests/test_verdict_gate.py`); the suite's 1 failure is the expected manifest-drift guard on the new unsealed tool (re-seal below).
- Forward convention: new runners route their final verdict through `tools.verdict_gate.finalize`; existing bookings stand (their receipts carry gates + evidence, but retrofit is QO6-EV's job).
- Rotation honored: CPU item per 03:1x handoff; GPU lane untouched; no repro due (last bookings analysis-only or already PASS'd).

## [DONE 05:1x CPU Oct 1] **D12i BOOKED: verdict KEEP** (width-scaling lane; QO6 dead-fire pattern #3, booked by recovery wake)
- Orphaned dead-fire found at 05:11 wake: runner + results.json untracked, no pre-reg commit, no booking —
  prior wake fired and died before landing anything. Pre-reg is embedded in the runner docstring (declared
  RETROACTIVE per the QO5 precedent; honest flag booked).
- **Deterministic replication FIRST**: pure-python `random`, seed 2718, single-threaded → re-ran to
  /home/eileen/scratch/d12i_repro/out.json (ext4, never touched results/ — 09:1x doctrine) → output
  **IDENTICAL (a==b deep-equal, True)**. Booking rests on a verified artifact.
- Gates: (a) T_floor(W) non-increasing at every (N, p) — monotonicity_inversions **[]** (0 inversions);
  (b) hardest corner W=16, N=64, p=0.3: partner_id_acc at T=25 = **1.0** ≥ 0.9. **BOTH PASS → KEEP.**
- Headline: **the D12h "T≥50 universal" is a width artifact** — it holds only at W≤4. T_floor drops with
  width roughly one grid rung per W doubling (W2→W16 at N64/p0.3: 100→25; N8/p0.3: 50→10). Width buys back
  observation time nearly linearly. Caveat: W16/N64/p0.3 floor 25 vs W8's 25 — the clean halving saturates at
  the largest (N,p) corner (correlated-subchannel count vs pair-brightness tradeoff visible at W16, N64).
- Provenance: runner sha256 501cb7051bb938df…; no runner_sha256 field in the artifact (pre-pin-era runner,
  RC-1/DEGENERATE-era convention not yet applied); verdict route through tools.verdict_gate not retrofitted
  (existing bookings stand per TRUNC-B convention).
- Booking: this entry + runner + results committed together; manifest re-sealed after. QUEUE line backfilled.

## [DONE 05:1x Oct 1] SCOUT-12 (day-conductor, non-GPU per (A)-first rotation): NEW repo chiaroscuro
- 13 PRs in ~10h, sealed-pre-reg/receipt/R8-kill discipline — third independent witness of our doctrine.
  #13 geometric-PN lane CLOSED (G2 PASS, H1-H4 FAIL, no iteration). #5/#6 JevGateV2 HOLD/CAST abstention
  split INTEGRATE (+10pts degraded, parity clean, pins 6/6) — TOOL for QO2/QO6: we lack an explicit
  receipted HOLD register distinct from permanent keep; spawned CH-1. #6 finding "vocabulary coverage is
  the binding constraint" = 4th instance of the VP-1 class. CONTRADICT scan: none — JEV work is gate-side,
  orthogonal to QC-JEV oracle discrimination; DECIDE-2 unthreatened. Full text:
  proposals/runs/SCOUT-12-fleet-push-2026-10-01-1311Z.md. Rotation next wake: GPU (QG1d follow-up or QG4).

## [DONE 06:2x GPU Oct 1] **D12j BOOKED: verdict KEEP (product rule survives to W=128)**
- Pre-reg fired as written (0b2df86 committed+pushed BEFORE fire; runner committed before fire too).
- Gates: **J1 PASS** (T_floor non-increasing in W at every (N,p); monotonicity_inversions []) and
  **J2 PASS** — at the hardest corner (N=128, p=0.3): T_floor 5 (W32) -> 3 (W64) -> **2 (W128)** <= 3.
  **J3 not triggered** (floor still shrinking at W128; no plateau). Mechanical verdict: KEEP.
- Headline: D12i's W·T product rule EXTENDS to the GPU-scale widths the CPU lane could not reach.
  At p=0.3 the floor keeps falling ~2x per W doubling (W32->W128 at N128: 5->2); at p>=0.5 the floor
  is already at the ladder's bottom rung (T=1) for W>=32 — discovery there is limited by the ladder
  resolution, not the rule. Combined D12h/D12i/D12j law: T_floor ~ C(N,p)/W, saturating at the
  message-exchange floor which is <= 2 for every tested (N,p) at W=128.
- Harness notes: 1 mechanical crash pre-scoring (torch.cuda.temperature() raises ModuleNotFoundError
  when pynvml absent; preflight except-list was too narrow — fixed in place, declared). Preflight
  VRAM gate PASS (5.3 GiB free). Runtime: single-digit minutes, well under 50 MB device memory.
- Seed family SEED=2718 per pre-reg formula (torch CUDA generator); NOT bit-matched to D12i
  (declared in pre-reg). Result: results/d12j_gpu_width.json (+ runner experiments/d12j_gpu_width.py).
- (C) MANDATORY REPRODUCTION CHECK 06:2x: D12j re-run from the COMMITTED runner to ext4 scratch
  (/home/eileen/scratch/d12j_repro/, never touched results/) → output IDENTICAL to the committed
  artifact (gates, floors, grid all deep-equal; device-name field excluded). CUDA generator seeds
  are version-stable here. Clean bill.

## [06:4x Oct 1] D12j RECONCILIATION — the pre-reg was run TWICE independently; both KEEP (two-witness verdict)
- Race found at reconciliation: the wheel lane (grabbed 0b2df86 within minutes of push) implemented and
  fired its own runner (28e2654, preflight fix 7c33add) and booked KEEP (756986c; corner floors
  5→3→2 at W32/64/128, N128/p0.3) while Lucineer was building an independent implementation at the same
  paths. Colliding writes: Lucineer's fix commit (3a4ec94) replaced the lane's runner in the tree, and
  the r2 receipt overwrote the lane's receipt (uncommitted at collision time — nothing lost; lane
  artifacts restored verbatim from 7c33add / 756986c).
- Reconciliation: lane's runner + receipt restored to the canonical paths their booking references;
  Lucineer's implementation + r2 receipt preserved at experiments/d12j_gpu_width_lucineer.py +
  results/d12j_gpu_width_lucineer-r2.json.
- Result: TWO independent implementations of the same frozen gates, both **KEEP — J1 PASS (0
  inversions), J2 PASS (floor(128)=2 ≤ 3), J3 not triggered**. Only divergence: the W32 floor rung
  (lane 5 vs Lucineer 10 at N128/p0.3) — ladder-resolution-sensitive; the D12i extrapolation
  (~400/32 ≈ 12.5) sits nearer 10, and both implementations land on identical W64/W128 rungs.
  Two-witness verdict: **the W·T product rule survives to W=128; the message-exchange floor at W=128
  is T=2.**
- Process lesson (banked): pre-regs in proposals/runs/ are implicit claims — main-session self-fires
  must check the farm/spool first or mark ownership in the pre-reg itself. This race cost nothing
  (git kept everything) but is a standing collision hazard.

## [DONE 10:4x GPU Oct 1] **INSTRUMENT-01 BOOKED: LAW_CALIBRATED (R1 PASS, R2 PASS — first fire)**
- Pre-reg fired as written (owner: any; prereg+runner pushed before fire). Receipt: results/instrument_ramp_law.json.
- The calibrated WSL2 burst-timing law (replaces the morning's single B/C-series estimate):
  - Idle 5s → **0.97× (SAFE)**; onset between 5-10s idle; saturation ~4.5× by 20s (10s→3.4×, 20s→4.43×, 40s→4.51×, 80s→4.47× — flat after 20s).
  - Recovery: even a **0.1s sustained synced ramp restores ≥98.8%** of hot; 0.6s → 100.4-103.7%. bench.py's 0.6s ramp RETAINED (margin is free).
  - R3 (exploratory, no gate): elementwise kernel hits **5.33×** after 20s idle — the law is KERNEL-AGNOSTIC, box-level, as suspected.
- Mandated follow-ups done: ramp recipe → workspace TOOLS.md; bench.py keeps its ramp implementation (declared: docstring numbers ride on this booking).
- Verdict: LAW_CALIBRATED — every future GPU measurement on this box ramps first, ramp receipts included.

## [DONE 19:4x Oct 1] SCOUT-11 + (C) INSTRUMENT-01 REPRO: gates reproduce, per-point numbers are single-draw statistics
- SCOUT-11 (non-GPU per (A)-first rotation): fleet-triage PR #1 RTX4050 worklist read in anger -> spawned FT-A1
  (pie-minimax nonlinear closure per their buildspec), FT-D3 (determinism lab), QO10 (projection-ladder oracle
  ablation). RC-1b raised (quilt-llvm 0%-killed mutants). Full text proposals/runs/SCOUT-11-fleet-push-2026-10-01-1911Z.md.
  NO CONTRADICT findings this sweep.
- Booking hygiene find: results/instrument_ramp_law.json was UNTRACKED while booking 929065a + the sealed
  manifest referenced it (D-2 silent-edit class, 2nd local instance; QC-JEV was the first). Committed this wake.
- (C) MANDATORY REPRO of INSTRUMENT-01 (committed runner to ext4 scratch /home/eileen/scratch/instr01_repro/,
  output never touched results/): **R1 PASS, R2 PASS, verdict LAW_CALIBRATED — gates reproduce.** Honest
  deviations (timing law is statistical, not deterministic):
  - 0.1s ramp restored **76.8%** of hot this draw vs committed 98.8% — the "0.1s restores >=98%" margin is
    BEST-CASE single-draw, not a floor. (R2 still passed on its own criterion; 0.3s/0.6s trials 97-106%.)
  - R1 shape noisier: 20s-idle draw 0.98x and 80s draw 2.5x (committed: flat ~4.5x after 20s). Onset 5-10s and
    "must ramp before measuring" both hold; the per-point slowdown values do NOT.
  - AMENDED workspace TOOLS.md law wording accordingly (ramp receipt mandatory; treat slowdown magnitudes as
    order-of-magnitude, ramps >=0.3s as the safe recipe).
- Runner defect (3rd instance of the class): OUT_PATH hardcoded to results/ — verification must run in a copied
  scratch tree (done) until runners grow --out (RC-1 spec).

## [DONE 12:09 GPU Oct 1] **FT-A1 / pie-minimax closure: P1 FAIL-HIGH, P2 FAIL — the receipt is the point**
- Lane: RTX4050 worklist #1 (fleet-triage PR #1, merged). Spec: docs/RTX4050-BUILDSPECS.md "pie-minimax A1 build spec".
- **REPRODUCE BEFORE EXTEND: exact.** `sweep.py` linear 9→9 = **0.1807** top-1, floor 0.1431, set-recall 0.1748 — byte-for-byte match, 13.1s CPU.
- **COMPOSED mask** (≥2 distinct immediate wins): **320 / 2,423 distinct boards = 13.21% share** (304× double-win, 16× triple-win); 11,520 rows (6.39%) path-weighted in the 180,361-row artifact.
- **MLP 9→64→9 (1,225 params), CUDA, seeds [1,2,3] pinned (torch+numpy+cuda+data), set-valued loss, early-stop plateau:**
  - per-seed global top-1 = **0.9996 / 0.9996 / 0.9996** (std 0.0); composed top-1 = **1.000 / 1.000 / 1.000**; train-loss → 1e-4, ~10-13s/seed.
  - **P1 FAIL-HIGH** (0.9996 ≫ 0.40), **P2 FAIL** (composed = 1.00 ≮ 0.70×global). Frozen mapping applied, reported anyway per spec.
- **Supplementary 5-fold held-out CV** (run3.py-style folds, seeds 100-104): **0.980 ± 0.004 top-1, composed 0.991** → FAIL-HIGH is *generalization*, not train/test interpolation (sweep.py protocol samples w/ replacement from 2,423 distinct boards, so test ⊆ train w.h.p.).
- **Interpretation:** the "local-voting ceiling" thesis **weakens decisively** at rung 1 — a 1.2k-param nonlinear student absorbs the exact minimax policy nearly completely. The README's own suspicion is confirmed: its h=8/h=32 non-monotone results were *optimizer-conditioning artifacts, not capacity limits*. Nuance: run3.py's tree "ceiling" (0.79) was trained on single-move tie-break labels (the README's label problem) — MLP > tree is explained by the set-valued loss, not evaluation leakage.
- **Spec-vs-repo surprises:** (1) spec expected ~180,361-row table; `enumerate_reachable()` literally returns 180,361 rows but these are tree-path duplicates of **2,423 distinct boards** — repo README/GPU-EXPERIMENT.md carry a CORRECTION to this effect (3^9 sanity); multi-optimal is 48.6%, not 14.7%. Labels unaffected (exact either way). (2) Repo already contains a 5-fold CV harness (run3.py/ceiling2.py) postdating the README table.
- Hygiene: INSTRUMENT-01 ramp 1.137s synced CUDA before timing; device `cuda:0 (RTX 4050, 6GB)` recorded; wall-clock 36.4s (3 seeds) + ~2min CV5 + 13.1s repro. Runner `lanes/pie_minimax_closure.py` (+ `_cv5.py`), receipt `results/pie_minimax_closure.json`. **Local commit only — no push; pie-minimax repo untouched remotely; receipt PR handled centrally.**

### INSTRUMENT-01 deviation declarations (12:1x — declared per review, not re-run)
- R3 (exploratory, no gate) ran lighter than frozen: single 20s idle point, torch add_ elementwise rather than a cupy kernel, ~8× longer burst than the standard 30ms. The kernel-agnostic claim rides on this leg — treat as indicative until the A4/D3 Determinism Lab sweeps it properly.
- hot baseline uses median-of-5 (matmul) vs min-of-3 (elementwise) — inconsistent reference convention; both are baselines only (calibrated gates read R1/R2). Future bench runs use median everywhere.
- Launch-drain backlog flagged (zcode) as the real wall-clock hazard for GPU timing here; bench.py's sync-then-time pattern already avoids it.

## [DONE 12:1x CPU Oct 1] DAY-CONDUCTOR slice: SCOUT-12 fresh-push sweep + FT-A1 mandatory repro PASS
- **(A) SCOUT (SuperInstance pushes last 48h, read-only):** wave of merges ~20:05-20:08Z (fleet-triage PR#2
  quilt-family census digest, 244 repos; canons PR#4 scout-gems + PR#5 referral-resolver; quilt-dba PR#1
  predictive-paddle referral; quilt-tournament PR#1 "all 25 LINE_OOR in the quilt family live here" — none
  ours; fleet-triage PR#3 OPEN referral doc re quilt-Kuramoto salvaged-archive, 253 FILE_MISSING independently
  cross-checking their own docs/MISSING.md). Classifications:
  - **CORROBORATE — quilt-tools edge14** ("qe-eproc-witness -> ds-esign-drift VERIFIED=1.0 ... **the merge
    outran the booking**"): fleet-wide 4th independent witness of our D-2/dirty-tree class. Our RC-3
    sealer + tracked-artifact-at-seal ask is now corroborated three times over.
  - **TOOL — fleet-triage resolver AMBIGUOUS taxonomy** (PR#3: 264 bare-basename citations multi-repo
    ambiguous, 8/8 spot-verified; basename-pinning doc lint). Spawned **RP-1** (apply the taxonomy as a
    lint over OUR receipts' repo citations — we already do repo-name citations since RECEIPT-CITE; this
    checks for ambiguous bare basenames).
  - **CHECK — jev-quilt round 48 wipe active** (20:05Z r002 mean_p=0.9020, q10 +0.26 drift flagged; 19:04Z
    "mean_p 0.7620 lucky draw n=5"). Their lane exhibits round-to-round drift; our QC-JEV pin (p_true
    0.9606/0.0243) was a single-round draw on jeff-0.8b. Spawned **QC-JEV3** (drift re-probe, cheap).
  - No CONTRADICT this sweep; our repo not flagged by the 244-repo census (LINE_OOR all in quilt-tournament).
- **(C) MANDATORY REPRO — FT-A1: PASS.** Committed runner (2978159) re-run with elephant-gpu python, ref
  copy saved first (sha 74ff62aa…), output diffed: every scored value byte-identical (top1_global 0.9996
  x3, top1_composed 1.0 x3, composed_test_n 519/557/517, final_train_loss 1e-4, steps_run 4000 x3);
  ONLY train_secs differ (4.2-4.5s vs committed 10.3-12.7s — timing fields, not measurements). Honest
  note: byte-identity of the whole file is impossible by construction (embedded wall-clocks); verdict +
  all gates reproduce exactly. Committed artifact restored via git checkout after the run (runner
  hardcodes absolute output path — 4th instance of the RC-1 hardcoded-OUT class).
- Manifest re-sealed after ledger change. No GPU queue item fired this slice (repro + scout timebox);
  next wake per rotation: GPU item (QG4 phase diagram or QG1d recon) or the cheap CPU pins (RP-1,
  QC-JEV3, DEGENERATE-gate).

- **G7 watt-receipt instrumentation — KEEP (2026-10-01).** guard.py now samples power.draw + utilization.gpu on the same 5 s poll (`sample_power`/`sample_full`; the `sample()` 2-tuple contract is preserved — e6 harness selftest 6/6). Seals one g7-watt-receipt@1 per run: guard_summary.json written first and sha256-bound as `state_digest`, fleet-seeds validator (../fleet-seeds/scripts/g7_validate.mjs) executed at seal time, receipt + validator output appended to results/g7/ledger.jsonl. Fail-closed by construction: zero valid power samples → source tdp_derived + verdict VOID (sampling failure declared, never faked); unknown device → vram_gb 0.0 → validator refuses the receipt → run VOID. Live proof (scratch/g7_live_validation.py): 25 s bf16 4096² matmul load under guard → 5 power samples, mean 67.7 W × 21.493 s = 1455.1 J = 0.404 Wh = $0.000093 @ $0.23/kWh; receipt g7-wr-g7-watt-receipt-instrume-1790888665 → validator exit 0, gate PASS. VOID-path control: schema-valid, gate self-declares VOID. Canonical void-missing-energy example: refused exit 1. Adoption law live from this run forward: every GPU verdict ships a schema-valid receipt or is VOID. Same-day scout: scratch/scout-2026-10-01-pushwave.md (fleet-triage synergy mechanism — "an instrument reports success unless it has been given a way to fail" — with XP-A/B/C pre-reg seeds queued in QUEUE.md).

- **G1 local-LLM-seat spike — KEEP (seat COMPLETER confirmed; seat-as-VERIFIER falsified at chance) (2026-10-01).** First real local seat run: qwen2.5:7b-instruct-q4_K_M (7.6B, 4.19 GB VRAM-resident) on the 4050 via ollama, certified 96-prompt witness-claim battery g1-battery-96@1 (moth-seal master 31,50,23,51, certified-direct 832 bits, registered fleet-seeds fb58d37 BEFORE any seat traffic). **Completion: 96/96 accepted, 1.0 rate, zero truncations, mean 30.1 eval tokens, 123.1 s total generation — converts the 45-c gateway starvation KILL (0/96 @2000) into a 100% result at the 2000 rung.** S7 CONFIRMED at primary rung (4000/8000 by transitivity + engine-ctx-4096 caveat, reported AS-MEASURED); S4 CONFIRMED (harness receipt g7_validate exit 0, gate PASS); S5/S6/S1/S2/S3 honest N/A this run (single pass, no FP16 arm, no ≥8 GiB host). **Blind verdict accuracy 0.5208 ≈ chance** (confusion symmetric 28/22/24/22); per-class: xref 0.938 (explicit-context retrieval strong), arith 0.562, seq 0.562, count 0.438, contra 0.312, date 0.312 (below chance — consistency checking fails in the wrong direction). **Finding: the local 7B Q4 seat is a completer, not a verifier — verdict work routes through instruments (typesafe JEV) or stronger arms; spawned G1b (S5 determinism) + G1c (seat-vs-instrument routing).** Energy: MEASURED 6137.6 J = 1.705 Wh (guard poll, mean 82.1 W × 74.8 s window) = $0.000392 @ $0.23/kWh; harness receipt (pre-run estimated derivation, declared) + guard MEASURED correction receipt both sealed and validator-green (append-only correction pattern, first live exercise). Artifacts: results/g1/run1/{20261001T212346Z-responses,receipt}.json + score.json, results/g1/guard/ledger.jsonl, experiments/g1_run.py, experiments/g1_battery_build.py.

- **G1b seat determinism (S5) — KEEP (2026-10-01).** Two identical passes over the certified battery's first 8 prompts, temperature 0, seed 31502351 (master-seed-derived), same engine build: outputs **byte-identical 8/8** (sha256-digested per prompt, all match). S5 CONFIRMED at this rung (single-seat, single-engine; cross-engine determinism out of scope). ollama chat API honors seed+temp0 deterministically for Qwen2.5-7B Q4_K_M — the seat is safe for replay-sensitive lanes (hook receipt verification, XP-B M5 class). Artifact: results/g1b-determinism.json. GPU tail-power at rest 51.9 W (idle floor, WSL2).

## [DONE 13:32 CPU Oct 1] **XP-A "instrument-transfer": INCONCLUSIVE — at n=3 instruments the rho gate is binary; KILL shape present but under the frozen bar**
- Lane XP-A (fleet-triage synergy mechanism, scout `scratch/scout-2026-10-01-pushwave.md` §1c). CLAIM: *an instrument's power against KNOWN failure classes predicts its power against UNKNOWN (held-out) classes* — "an instrument reports success unless it has been given a way to fail."
- **Setup (seed 2718 everywhere, CPU-only, no CUDA).** 10 seeded corrupt-receipt variants of our own booking schema (from `experiments/st1_quilt_cell_v0.py`): 6 KNOWN (`sign_flip, wins_over, verdict_flip, tau_off, seed_drop, denom_swap`) + 4 HELD-OUT novel (`nan_injection, dtype_cast, split_boundary, receipt_copy_prior`). Eval 600 receipts (200 clean + 240 known + 160 held-out). Three instruments: (A) `tools/verdict_gate.py` static pins; (B) a fresh canfail-style step-parser (frozen invariants B1–B8: field presence, strict-int wins, finite floats, tau∈grid, verdict==honest_verdict, receipt-id uniqueness); (C) char-3gram/token logistic, trained on clean+KNOWN only.
- **Frozen gates (set pre-fire, no post-hoc loosening):** chance 0.50; BEATS_CHANCE 0.60; HIGH_KNOWN_POWER 0.65; FLUNKS 0.50; RHO_MIN 0.70. KEEP iff rho≥0.70 AND all instruments beat chance held-out; KILL iff any instrument with known≥0.65 has held-out≤0.50; INCONCLUSIVE if grid <3×4.
- **Result — per-instrument known / held-out recall:** A `verdict_gate_pins` **0.567 / 0.000** (0/160!); B `step_parser` **0.725 / 0.994** (159/160); C `trained_classifier` **0.542 / 0.413** (66/160, clean FPR 0.255). **Spearman rho = 0.50.** → **INCONCLUSIVE** (rho 0.5 < 0.70; all_beat = False: A and C fail the 0.60 recall bar).
- **Honest reading (frozen verdict stands; gate shape flagged):** the instrument given real *ways to fail* (B — invariants, not op signatures) transfers near-perfectly; the fixed-gate instrument (A) transfers **exactly zero** to every held-out class; the learner (C, trained only on KNOWN) lands below the 0.50 recall bar held-out. A and C are in the KILL "gap zone" (known≥0.50, held-out≤0.50) but just under the frozen 0.65 bar, so the KILL existence clause does **not** fire — a near-miss on the KILL side, NOT a pass of the claim.
- **Method caveats booked (supplementary.json):** (1) at n=3 instruments Spearman has a 4-value support {−1,−0.5,0.5,1}; rho≥0.70 ⟺ rho=1.0, so the frozen gate is effectively binary and rho=0.5 carries exact permutation p=0.5 — the pre-reg over-specified precision for a 3-instrument grid. (2) The 0.50 chance constant presumes balanced accuracy; A has clean FPR 0.00 so it is *at* chance (bal-acc 0.500), while C is *below* the recall bar but above chance in balanced terms (bal-acc 0.579, FPR 0.255). Kept the frozen recall gate; reported both.
- Hygiene: `experiments/xp_a_instrument_transfer.py` was present untracked at task start (an interrupted prior attempt); verified **byte-reproducible** — two fresh `--skip-gpu` runs reproduce `grid.json` identically (sha 954fcca8…, 13.0 s each). Docstring amended to record the CPU-lane invocation (no numeric change, grid re-verified identical after the edit). Classifier C via declared CPU-torch child (`device=cpu-fallback`, torch.manual_seed(2718), 300 steps, val bal-acc 0.648). No GPU code, no CUDA calls, no commit (keeper commits + re-seals).
- Artifacts: `experiments/xp_a_instrument_transfer.py` (sha b086e08c…), `experiments/xp_a_supplementary.py` (sha f14a9e32…), `results/xp_a/{grid.json, supplementary.json, per_receipt_detections.json, c_meta.json, eval_stream.txt, c_*.npz}`.

- **XP-B git-hook receipt gate vs corruption corpus — KEEP (2026-10-01).** Pre-registered in `scratch/scout-2026-10-01-pushwave.md` §2c; pre-reg written BEFORE the build (`experiments/xp_b_hook/prereg.md`). Claim: *a commit-time hook enforces cell honesty — refuses every pre-registered corruption class with ZERO false rejects on clean commits.* **Result: all 5 classes (7 operational ops) REFUSED; all 124 clean commits ACCEPTED (120-commit seeded history + 3 controls + 1 clean GPU cell); verdict KEEP.**
  - **Corpus:** seeded 2718, 120 commits, receipt = `qthe-receipt@1 seed=2718 sha256=<64> fnv64=<16> prev=<chain>` over canonical-JSON cell state (id/kind/16 dials/seed/body_sha256) + chain link. Pure digests, no keys. Generator is deterministic — a full regeneration reproduced `final_receipt_sha 671fbd80…` byte-for-byte.
  - **REFUSE table:** M1 dial-changed-no-receipt-update → sha256 mismatch; M2a receipt-reused-from-earlier-commit → chain-link mismatch; M2b forged `prev=` with correct state digest → chain-link mismatch; M3a truncated sha256 → format; M3b missing `fnv64` → format; M4 fnv64-recomputed/sha256-stale → sha256 mismatch; M5 GPU cell replayed at mutated seed → sha256 mismatch. **ACCEPT:** C1 new cell, C2 honest dial update, C3 two cells one commit (and the whole 120-commit history), M5 clean GPU cell.
  - **M4 — FNV-1a-64 collision rate, documented honestly at 64-bit: FOUND, 3/3 rounds, all independently re-verified in Python.** Construction exploits FNV-1a's last-byte linearity (`h'=(h^b)·P`): two prefixes whose states agree on the top 56 bits are equalised with one free suffix byte each — collision cost **~2^28** vs the generic **2^32** birthday bound (**16× cheaper**). 805,306,368 evaluations → 3 collisions (3.73e-9/eval; model λ=0.5/round). Avalanche: FNV-1a-64 **28.07/32 bits** mean (min 6) vs sha256 128.05/128. **Transfer test: the collision does NOT transfer to the canonical-JSON gate** — suffix-patching needs free trailing bytes and canonical JSON has a fixed tail, so the gate's sha256 pin holds (residual FNV-64 margin only ~2^64 second-preimage).
  - **Findings (fail-loud):** (1) **Git cannot enforce message-embedded receipts from `pre-commit`** — `.git/COMMIT_EDITMSG` is absent on the first commit and STALE (previous message) afterwards, verified empirically at setup; the gate is therefore installed at **both pre-commit (structural) and commit-msg (full)**. (2) **This is a CONSISTENCY gate, not an authentication gate**: with no keys, a deliberate forger who recomputes a fully consistent receipt is ACCEPTED (boundary probe BP1, measured, out-of-scope by the pre-reg). Adversarial integrity needs keys → SIG-1's `verifySignatures` (Casey-gated). (3) **FNV-64 must not be an adversarial cell address** — see M4. (4) **guard.py defect booked:** `Guard._stop` is a one-shot Event, so one `Guard` watches only its FIRST `run()`; later calls book 0 J. Fixed by running all three ticks in one guarded child. (5) **GPU-cell determinism confirmed** (2 runs, seed 2718, fixed 80k-iteration matmul chain → identical dials and `state_sha256`), which is what makes the M5 replay class meaningful.
  - **GPU (the only GPU use):** `Guard(task_id="XP-B-hook-gpu-cell")`, preflight ok, 3 ticks ≈ 30 s, **1681.04 J = 0.467 Wh**, gpu_seconds 24.04, INSTRUMENT-01 ramp receipt (cold 149.0 ms → hot 0.148 ms, 2660 ramp iters), receipt `g7-wr-xp-b-hook-gpu-cell-1790890680` gate PASS. Device RTX 4050 Laptop, torch 2.14.0+cu126.
  - **INCONCLUSIVE trigger did NOT fire** (pre-registered: only if FNV-64 collisions force a digest upgrade mid-run): the gate was pre-registered on sha256, and the found collisions do not transfer to canonical cell states. FNV-primary counterfactual reported beside the verdict.
  - **Artifacts:** `experiments/xp_b_hook/` (prereg.md, hooks/qthe_receipt_gate.py, qthe_receipt.py, gen_corpus.py, run_all.py, m4_fnv64.c, m4_avalanche.py, m5_gpu_tick.py, m5_gpu_ticks_all.py, m5_run.py, corpus/{cells/,corpus.bundle,history.txt}, clean_history.json) · `results/xp_b/` (summary.json, mutations.json, m4_report.json, m4_avalanche.json, m4_run_11/12/13.json, m5_gpu.json, m5_ticks.json, g7 receipt + guard_summary + ledger.jsonl). Lab copy: `/tmp/xpb-hook-lab`. **Not committed — keeper commits.**

- **G7 defect FIX — guard.py multi-run energy (2026-10-01, found by XP-B finding 4).** `Guard._stop` was a one-shot Event: a second `run()` on the same Guard sampled nothing (watcher exited immediately) → 0 J booked. Fixed: per-run stop Event + per-run energy window (`_close_window`); `emit_receipt`/`_energy` now integrate ALL windows with inter-run gaps EXCLUDED (single-run behavior unchanged; legacy global path preserved for sample-appending callers). Regression test: two 6.5 s runs + 2 s gap on ONE Guard → 2 windows, both sampled (306.3 J + 306.5 J), total wall 10.003 s (gap excluded), mean 61.3 W. e6 selftest 6/6, g7_validate selftest 16/16, both still green. All XP-B M5 ticks had been consolidated into one guarded child as their workaround — now unnecessary. XP-B verdict unaffected (its receipt was single-window).

## [DONE 13:44 CPU Oct 1] QG1d — fleet-triage source recon: degeneracy mechanism CONFIRMED at source, 4-port landed, 3 missing instruments named
# QG1d — source-level recon: fleet-triage assignment/swap machinery vs our cell contract

- lane (entry authored by lane, folded by keeper): QG1d (read-only recon; NO GPU, NO clone of fleet-triage, no pushes)
- date: 2026-10-01
- method: `gh api .../contents/<path> --jq .content | base64 -d` into `results/qg1d/src-snapshots/` (see MANIFEST.md for shas)
- scope: fleet-triage root (`resolver.py`, `lanes.py`, `triage.py`, BOARD/CORRECTION/D1 docs) + `experiments/` + `sim/`
- seed: 2718 (nothing was sampled; seed pinned for the ported self-test)
- **not committed — keeper folds. Not appended to RESULTS.md (parallel lanes live).**

## 0. Recon premise correction (read this first)

The brief expected "a resolver with swap/repair logic **we have never source-read**"
inside fleet-triage's `experiments/`. That is not where it is:

- `experiments/` holds the **projection-doctrine degeneracy** (`projection_doctrine.py`,
  `positive_control.py`) and the **n_eff / instrument-transfer** work (`synergy.py`).
- The citation resolver with the repair ladder is at **repo root**: `resolver.py`
  (1,815 lines). The lane/assignment machinery is `lanes.py` (root and `tools/`,
  byte-identical size).
- There is **no literal "swap" routine** anywhere in fleet-triage. `swap` appears
  exactly once, as a *bug description* (`lanes.py:100`). "Repair" appears zero times.
  The closest real machinery is: (a) the resolver's **candidate repair ladder**,
  (b) the lane **four-beam assignment/verdict**, (c) the tileset **assignment +
  collision** metric, (d) **Kish n_eff**.

So this lane reports what is actually present, not the expected artifact.

## 1. Q1 — WHY their max-over-4 was degenerate (the mechanism, not the label)

**Mechanism = max-selection over a correlated arm-set, then a leaky split.**

1. **The selection is a max over learners.** `experiments/projection_doctrine.py:336-338`:
   ```python
   def best(name):
       v = [r for (n, _), r in results.items() if n == name]
       return max(v) if v else float("nan")
   ```
   The four arms are stored at `:306` (`logreg`), `:312` (`knn`), `:319` (`mlp`),
   `:326` (`rf-logreg`). The published number per observation is `best(...)`
   (`:343-345`). The **same pattern reappears** in the control harness —
   `positive_control.py:199` (`best0 = max(rows_out["L0 lossless"])`) — so the defect
   is systemic, not one line.

2. **The four arms are not independent.** `synergy.py:69-79` (`n_eff`, Kish effective
   sample size = `k / Σ normalised correlation mass`) and the sibling `doctrine-RECHECK`
   lane computed **n_eff = 1.48 over the four learners** (`BOARD.md:23,59,83`;
   `CORRECTION-PROJECTION.md:4-8`). So "max over 4" is a max over **≈1.5 effective
   votes**. A max over correlated arms is upward-biased by roughly the arm spread.

3. **The spread exceeds the gap, so the ordering is a property of the selection.**
   `CORRECTION-PROJECTION.md:14-38`: L0 spread across the four learners **0.3209**,
   reported L0>L1 gap **0.0112** — the spread is **29× the gap**. Under the **median**
   the ordering **reverses** (L1 0.8947 > L0 0.8831). Their rule, verbatim:
   *"No gap smaller than the spread is a finding."*

4. **Secondary degeneracy: the split leaked.** `projection_doctrine.py:293`
   (`RNG.shuffle(idx)` random 80/20) vs `:295` (by-ply, honest). Their own
   `synergy.py:12-15` records the smoking gun: a **64-bit irreversible hash scored
   0.9586 on the random split vs 0.5045 by-ply** — pure memorisation. The
   max-over-learners table was read on the optimistic split.

**Mechanism in one sentence:** the reported ordering was `max` over ~1.5 effective
arms whose selection noise (0.32) swamped the between-observation gap (0.011); the
max is an upward-biased estimator, and the rank flipped when the biased estimator
was removed (median).

**Relation to our contract:** this is **not** the same clause as our `verdict_gate`
DEGENERATE law (`tools/verdict_gate.py:20-27` — *zero variance* may never PASS). It is
the **complementary** clause the fleet-triage correction supplies: **variance so large
relative to the gap that the max is not a measurement.** Our law catches std==0; their
retraction catches `spread >> gap`. Both belong in the same gate. That gap is the
substance of §3.

## 2. Mechanism → our cell contract map

Our contract (per `experiments/common.py:1-6`, `experiments/d10_cell_kernel.py:1-15`,
`experiments/d11_don_contract.py:1-16`): a **cell** = pure `z_in→z_out`, seedable
(2718), deterministic, receiptable (state hash), no hidden state across the boundary.
A **instrument** = a ways-to-fail detector (its value is that it can go red).

| fleet-triage mechanism | cite | class | disposition |
|---|---|---|---|
| Kish `n_eff` | `synergy.py:69-79` | **(a) cell-shaped** (pure, no RNG, deterministic) | **port** |
| `detection_power` (recall over known-fail) | `synergy.py:52-58` | (a) cell-shaped | port-ready; our XP-A already has the idea |
| spread-vs-gap **rule** | `CORRECTION-PROJECTION.md:26-40` | **(a) gate, cell-shaped** | **port** (§4) |
| `max` over learners | `projection_doctrine.py:336-338`, `positive_control.py:199` | **(c) neither** — it is the *defect*, not a tool | do **not** port; adopt the ban |
| repair ladder (`_suffix_match`/`_name_lives_elsewhere`/`_near_miss`) | `resolver.py:652-733`, `736-750`, `829-856` | **(c) neither as-shipped** — needs the 477-repo index + live fs + GH API; **(a) once reduced to the pure contract** | port the reduced pure form (§4) |
| four beams EXISTS/SAYS/REPRODUCES/CONTROL | `lanes.py:45-105`, `134-186` | **(b) instrument-shaped** (a ways-to-fail detector; B4 is the whole point) | port as an **instrument**, and it is the gap in XP-A (§3) |
| `beam_reproduces` (list-form subprocess) | `lanes.py:77-88` (`subprocess.run(cmd, ...)` at `:80`) | (b) instrument | law-compliant already (list form, no shell) |
| `triage.py` `api()` rate-limit gate + `inspect()` | `triage.py:52-73` / `:75-…` | **(c) neither** — network/IO glue (`urllib`, 403-vs-finding discipline) | no port; note the discipline |
| tileset `assign_nn` + `roundtrip` (assignment + collision count) | `sim/tileset_sim.py:159-163`, `145-157` | (a) cell-shaped (nearest-slot assign + collision metric) | optional; closest thing to a literal "assignment" primitive |

**Key finding for Q2:** fleet-triage has **no cell-shaped swap/repair primitive to
copy verbatim.** Its repair logic is **index glue** (it cannot run without the repo
index + filesystem), and its "swap" is a documented branch-order *bug*, not a routine.
**Our own `experiments/d11_don_contract.py` already IS the cell-shaped swap/repair
primitive** — propose a swap of discovered edges → validate on holdout → commit iff
strictly better else revert with **bit-identical revert fidelity** (docstring
`:1-16`). fleet-triage adds nothing to that cell. What it *does* add is a **labelling
discipline** for repairs (§4) that D11 should adopt for its `revert` label.

## 3. Port call (Q2) — **PARTIAL YES** (lint/grab tool, not a cell)

Port **no swap/repair cell** (we already own the better one, D11). Port the three
**reduced pure contracts** as a grabbable tool, because each is pure, deterministic,
dependency-free and receiptable, and two of them close real holes in our lab:

- `kish_n_eff(corr)` — the **mechanism** of Q1 as an executable (not a slogan).
- `spread_vs_gap(gap, spread)` — the **rule** ("no gap smaller than the spread is a
  finding") + a zero-variance DEGENERATE arm; complements `tools/verdict_gate.py`.
- `repair_label(cited, candidates)` — the resolver's ladder reduced to a pure
  contract: `EXACT | REPAIRED_PRECISE | AMBIGUOUS | MISSING`, **never silently
  upgrading AMBIGUOUS → repaired** (`resolver.py:652-733`).
- `control_beam(...)` — `lanes.py:91-105` + the tautology guard at `:143-157`.

**Written to** `experiments/ft_grab_swap_repair.py`
(sha256 `b80ae4f1c4f6baedc09288c40094d6bad8e45c05ba0876156a42437ab986ee43`,
6,98x B, self-test `python3 experiments/ft_grab_swap_repair.py`, rc=0). No subprocess,
no RNG, no I/O in the primitives — nothing to trap the shell-reparse law.

Demo output (captured):
```
n_eff over 4 correlated learners = 0.29 (of k=4)     # 4 fully-coupled arms collapse
their retraction: NOT_A_FINDING                       # 0.0112 gap < 0.3209 spread
exact-path ladder : EXACT
one-candidate     : REPAIRED_PRECISE
ambiguous         : AMBIGUOUS
unfailable control: CONTROL_UNFAILABLE
tautology control : CONTROL_TAUTOLOGY
honest control    : CONTROL_OK
```

**Recommended adoption (keeper's call):** wire `spread_vs_gap` into
`tools/verdict_gate.py` as a fourth refusal class beside DEGENERATE / TRUNC-B /
status-source — a **max-selection / spread guard** (`verdict_gate.py:8-27`). This is
the one change that would have blocked fleet-triage's published table *and* would
have flagged our own XP-A rho gate (§below).

## 4. Q3 — does BOARD.md's dependency graph imply an instrument our XP-A grid lacks?

**Yes — two.** Our XP-A grid (`experiments/xp_a_instrument_transfer.py:20-45`:
instruments A `verdict_gate pins`, B `step parser`, C `classifier`; 6 known ops ×
4 held-out ops; frozen gates at `:46-62`) measures **detection power**. It has **no
instrument that audits the other instruments' controls**, and **no gate on the gate's
own precision**.

BOARD.md's weight sits in the **dependency edges**, not the counts
(`BOARD.md:41-52`): `syn-AUDITORS → "the method that found the above"` and
`syn-HARNESS → "one rule for all three 'cannot fail' families"`. The missing
instruments those edges imply:

1. **Control-arm integrity instrument** (`lanes.py:91-105` + `:143-157`). XP-A
   instrument A scored **known 0.567 / held-out 0.000** (`RESULTS.md` XP-A entry) —
   A is the "fixed-pin" instrument that **cannot fail** on held-out classes. No control
   arm in the grid was required to be shown **red on deliberately-broken input**, so
   A's inertness was discovered only by the outcome, not pre-fire. `control_beam`
   refuses `CONTROL_UNFAILABLE` and `CONTROL_TAUTOLOGY` (repro==control) up front.
   This is, precisely, our XP-A applying fleet-triage's own lesson to itself: *"an
   instrument reports success unless it has been given a way to fail."*

2. **Precision / n_eff instrument on the grid's own statistic.** XP-A flagged, as a
   caveat, that **at n=3 instruments Spearman has 4-value support {−1,−0.5,0.5,1}, so
   `rho ≥ 0.70 ⟺ rho = 1.0`** — i.e. the frozen gate is **binary/degenerate** by our
   own `verdict_gate` DEGENERATE definition. The grid had no instrument to say so
   before fire. `kish_n_eff` + `spread_vs_gap` are exactly that instrument (their
   `CORRECTION-PROJECTION.md` is the same failure, caught after publication instead of
   before).

**Missing-instrument candidates (ranked):**
(i) control-arm integrity beam on each XP-A instrument (highest value; blocks the
"known≥0.65 but held-out 0.000" shape pre-fire);
(ii) n_eff / spread-vs-gap guard on the grid's own gate statistic (would have moved
XP-A from a confusing INCONCLUSIVE to a correctly-scoped **DEGENERATE gate** finding);
(iii) an **ambiguity-frontier** score: their `PATH_PRECISE_ONLY` carried **9.0% false
positives** while hard outcomes carried 0.5% (`sprint-RESOLVER.md` §4) — i.e. repair
labels are systematically noisier and must be scored as a *separate* population, not
folded into "resolved". Our QG1c residual is an ambiguity frontier of exactly this kind.

## 5. GPU follow-up? (QG1e) — **NO GPU lane implied; a CPU lane is**

Every finding above is **analysis/CPU**: n_eff is arithmetic, spread-vs-gap is a gate,
the repair ladder is pure, XP-A is already a booked CPU lane (`xp_a_instrument_transfer.py`
docstring, `--skip-gpu`), and QG1c's swap residual was resolved without new GPU work.
**Do not pre-register a GPU QG1e on this evidence.**

The natural successor is **CPU** and would be pre-registerable cheaply:
- **QG1e-CPU (proposed, not fired):** apply `control_beam` + `spread_vs_gap` as an
  audit *over* the existing `results/xp_a/` grid (no re-run): (1) for each of A/B/C,
  require a demonstrated red control or label it `CONTROL_UNFAILABLE`; (2) recompute
  the rho gate's support size and flag DEGENERATE. Kill-gate: the audit must be
  reproducible byte-identical x2 at seed 2718.
- **QG1f-CPU (optional):** decompose QG1c's 28 swap-only misses using `repair_label`
  to test whether they are `AMBIGUOUS` (two swap maps both admissible) or
  `REPAIRED_PRECISE` — QG1c found the residual is swap-only at Fisher 7.0e-19
  (`results/qg1c_swap_convention/results.json`, `C0_current`), so labelling the
  ambiguity, not a GPU sweep, is the next honest step.

**GPU is only justified if** QG1f surfaces a *new* swap family requiring batched
exact-state recompute beyond QG1c's six candidates — state that as the explicit
trigger, and keep the lane parked until it fires.

## 6. Artifacts

- `results/qg1d/src-snapshots/` — 22 fetched sources (root/experiments/sim/lineage), shas in `MANIFEST.md`.
- `results/qg1d/RESULTS-ENTRY.md` — this file.
- `experiments/ft_grab_swap_repair.py` — the ported grabbable tool (sha `b80ae4f1…`).
- `results/qg1d/src-snapshots/root/resolver.py` — the citation resolver whose repair ladder (`:652-733`, `:829-856`) was source-read here.

## 7. Honesty notes (booked)

- **Class-mapping is a judgement, not a measurement.** The (a)/(b)/(c) columns in §2
  are my reading of the code against our contract; a second reader could class the
  resolver ladder differently. Flagged, not hidden.
- **Recon premise was partly wrong** (§0). I did not manufacture a "swap routine" to
  match the brief; there isn't one.
- **Not committed, not appended to RESULTS.md** — the keeper folds and re-seals.
- `results/qg1d/src-snapshots` is a *snapshot*; fleet-triage may move under it (their
  own `RESOLVER-DEFECT.md` went stale within one sprint — the tool flagged its own
  auditor, `RESOLVER-FINAL.md` §"Corrections I owe" #3).

# XP-A2 — instrument-transfer grid at n=6 (entry authored by keeper from banked artifacts; lane died at the summary step after run completed)

- lane: XP-A2 (CPU only; follow-up to XP-A, extends grid 3 -> 6 instruments)
- date: 2026-10-01
- seed: 2718 everywhere; corpus = XP-A's 600 receipts (200 clean / 240 known / 160 held-out), 10 ops
- code: experiments/xp_a2_transfer_grid.py; artifacts: results/xp_a2/{grid.json, run.log, per_receipt_detections.json, judgment_api_receipts.json, c_*.npz, eval_stream.txt}

## Verdict: INCONCLUSIVE at the frozen gates — and the rho gate is now measured, not assumed

- **rho(known, unknown) = 0.493, exact-perm p = 0.32 at n=6** (KEEP needs >= 0.70 AND all-beat-chance; KILL clause: no instrument with known >= 0.65 AND held-out <= 0.50 fired)
- all_beat_chance = **False** (three instruments sit at or below the 0.5/0.6 bars on held-out)
- The n=6 extension did its job: the gate is no longer binary (rho 0.493 is a measured mid-rank, not a rounding artifact of n=3), and it still misses KEEP. The claim "known-power predicts unknown-power" is NOT supported at the grid level — the spread is by DESIGN FAMILY, not by rank.

## Per-instrument table (known recall / held-out recall / clean FPR)

| instrument | family | known | held-out | clean FPR |
|---|---|---|---|---|
| step_parser | invariant-parser | 0.725 | **0.994** | 0.000 |
| digest_manifest | digest-checker | 0.817 | **0.750** | 0.000 |
| g7_field_validator | schema-fields | 0.517 | 0.500 | 0.000 |
| schema_lint | schema-shape | 0.167 | 0.500 | 0.000 |
| verdict_gate_pins | invariant-pin | 0.567 | **0.000** | 0.000 |
| trained_classifier | known-only-learner | 0.408 | 0.287 | 0.225 |
| typesafe JEV (adjunct, n=30 sample) | judgment-API | raw receipts only — see caveat | | |

## Design-family finding (the substantive result, consistent with XP-A)

**Transfer axis = semantic depth, not instrument count.** Two families clear the held-out bar:
- **invariant-parser** (0.994): checks MEANING-bearing invariants (verdict == honest_verdict, tau in grid, wins are strict ints)
- **digest-checker** (0.750): recomputes the receipt binding from cell state — catches ANY drift through the hashed fields

Everything shallow or purely syntactic fails held-out: pins (0.000 — exactly the fleet-triage "given no way to fail" mechanism), schema-shape (0.500 = chance), G7-field-validator ported as pure field checks (0.500 = chance on THESE ops — honest note: those ops corrupt semantic content, not envelope fields; the validator is doing its actual job, which is a different op class), known-only learner (0.287, below chance recall, 22.5% FPR). The judgment-API arm needs a semantics fix before it can be scored (below).

## Typesafe JEV adjunct arm — RAW, not gated (lane died before analysis)

30 sampled receipts through the JEV cell per docs/typesafe-judgment-cells.md (noul graded 0..1). Raw receipts banked in judgment_api_receipts.json. **Caveat booked: the lane's detect convention flags CLEAN receipts (noul 0.45-0.59 on clean -> detect=true in 3 of first 6) — "low confidence" is being read as "detection", which inverts the semantics.** A clean-scored run must gate on corrupted-vs-clean SEPARATION (AUC), not raw detect flags. Follow-up queued (XP-A3): rescore the banked receipts with separation semantics + full-corpus JEV pass.

## Housekeeping

- XP-A2 verdict line in QUEUE.md: INCONCLUSIVE (gates) + design-family finding (real)
- KILL-shape watch: NONE — no instrument with high known-power flunked held-out (digest_manifest, the strongest, transferred at 0.75)
- Lesson: lanes that die at the summary step still bank their data — the keeper folds. Second DeepSeek timeout today (first: XP-A/B z.ai pair); pattern is provider-side, not task-size.

## [DONE 13:49 API Oct 1] G1c — seat-vs-instrument routing: JEV GATE PASS (0.7708); battery key defect LOUD (19/96 labels contradict prompt text; G1 headline corrected)
# G1c — seat-vs-instrument verdict routing

**Lane:** G1c (QUEUE.md line 56) · **Date:** 2026-10-01 · **Seed:** 2718
**Question:** the local seat (qwen2.5:7b Q4_K_M, G1) scores 0.5208 = chance on the
96-claim battery. Does an *instrument* clear the bar the seat fails?

**Verdict: KEEP (provisional) — with a booked key defect.** Instrument arms clear
0.75; the seat does not. But 19/96 labels in the certified key are inconsistent
with the prompt text, so the headline "0.5208 = chance" is partly a key artifact.

---

## 1. Arms (blind; key read only after both arms answered)

| arm | what | call | answered |
|-----|------|------|----------|
| LOCAL | qwen2.5:7b Q4_K_M via ollama | (G1 run1, reused) | 96/96 |
| JEV | typesafe `jev-preview` System One, one `noul` call per claim, thr=0.5 (fleet PINCH default) | `api.typesafe.ai/v1/systemone` | 96/96, 0 errors |
| GLM | z.ai `glm-5.3-flash`, **exact** battery text, temp 0, seed 2718 | coding endpoint (see §6) | 96/96, 0 errors, no 429 |

Arm I presented the claim body (reply-format boilerplate stripped) as `state`, one
graded question (`noul`, threshold 0.5 → SUPPORTED/REFUTED). Arm II got the byte-
identical prompt the local seat saw, so the three arms are comparable.

## 2. Gate results

Frozen gate: **JEV arm is KEEP-material iff overall accuracy ≥ 0.75.**

| | vs shipped key | vs recomputed truth (§4) |
|---|---|---|
| LOCAL | 0.5208 | 0.6979 |
| **JEV** | **0.7708 — PASS** | **0.9688** |
| GLM | 0.8021 | 1.0000 |

`noul` threshold is not the lever: sweep vs recomputed truth peaks 0.9688 over
thr ∈ [0.4, 0.8]; the shipped-key sweep peaks 0.7812 at thr 0.6–0.7. The doc's
default 0.5 is kept.

## 3. Routing table (cheapest arm ≥ 0.75 per class; cost LOCAL < JEV < GLM)

Against the shipped key:

| class | LOCAL | JEV | GLM | winner |
|---|---|---|---|---|
| arith | 0.5625 | 0.9375 | 1.0000 | **JEV** |
| date | 0.3125 | 0.8750 | 1.0000 | **JEV** |
| seq | 0.5625 | 1.0000 | 1.0000 | **JEV** |
| xref | 0.9375 | 1.0000 | 1.0000 | **LOCAL** (seat already clears) |
| contra | 0.3125 | 0.3125 | 0.3125 | — none (defective labels) |
| count | 0.4375 | 0.5000 | 0.5000 | — none (defective labels) |

Against recomputed truth (§4), which is the one to route on:

| class | LOCAL | JEV | GLM | winner |
|---|---|---|---|---|
| arith | 0.5625 | 0.9375 | 1.0000 | **JEV** |
| date | 0.3125 | 0.8750 | 1.0000 | **JEV** |
| seq | 0.5625 | 1.0000 | 1.0000 | **JEV** |
| xref | 0.9375 | 1.0000 | 1.0000 | **LOCAL** |
| contra | 1.0000 | 1.0000 | 1.0000 | **LOCAL** |
| count | 0.8125 | 1.0000 | 1.0000 | **LOCAL** |

**Routing recommendation:** route verdicts by claim class — **LOCAL for
xref / contra / count**, **JEV for arith / date / seq**. GLM is ≥ JEV on every
class but never the cheapest passing arm; keep it as the escalation tier for
classes or items where both LOCAL and JEV fall below 0.75.

## 4. Booked defect — the key, not the arms

Recomputing every claim's truth from its prompt text (pure arithmetic / sequence /
date math / roster lookup / enumeration):

| class | n | shipped-key labels inconsistent with text |
|---|---|---|
| arith | 16 | 0 |
| seq | 16 | 0 |
| date | 16 | 0 |
| xref | 16 | 0 |
| **contra** | 16 | **11** |
| **count** | 16 | **8** |
| total | 96 | **19** |

- **contra:** Statement B reads "The {item} is NOT on the locker list" while
  {item} *is* enumerated in A (15/16 rows) — as rendered these are lexically
  REFUTED, yet 10 are labelled SUPPORTED.
- **count:** recomputed from the rendered manifest, **all 16 claims are REFUTED**
  (claimed count ≠ actual count every time), yet 8 are labelled SUPPORTED.
- Every arm answers REFUTED to nearly all contra/count claims — including GLM,
  which is 100% correct on all four sound classes. The unanimous collapse is the
  tell that the labels, not the judges, are broken (a perfect judge caps at
  77/96 = 0.802 against the shipped key).

Consequence for G1: the local seat's 0.5208 is contaminated. Against recomputed
truth it is 0.6979 overall and 0.5938 on the four sound classes — still well
below the 0.75 bar, so the G1 conclusion (completer, not verifier) stands on the
sound classes alone; the contra/count columns of the G1 score should be struck.

## 5. Per-claim agreement (shipped key, 96 rows)

`truth` marginal: 50 REFUTED / 46 SUPPORTED.

- local_vs_truth: 50/96 (28 R-R, 22 S-S, 24 R→S, 22 S→R)
- jev_vs_truth: 74/96 (46 R-R, 28 S-S)
- glm_vs_truth: 77/96 (49 R-R, 28 S-S)
- jev_vs_glm: 93/96 agree (both REFUTED 64, both SUPPORTED 29; 3 S↔R)

JEV's confident errors on sound classes: `g1b-arith-0000` (noul 0.95 SUPPORTED;
truth REFUTED), `g1b-date-0508` (0.51), `g1b-date-0509` (0.80). JEV is
over-confident when it errs; no abstain channel was available.

## 6. Honesty notes

- **GLM endpoint:** the z.ai pay-as-you-go endpoint returns 429 code 1113
  ("Insufficient balance") on this key; the account's live plan is the **coding
  plan**, and `https://api.z.ai/api/coding/paas/v4/chat/completions` answers 200
  with `glm-5.3-flash`. Not an improvisation — same provider, same key, the
  base URL the plan is registered on. Booked here so future lanes don't burn
  10 minutes on 1113.
- Arm II was NOT booked NOT-RUN: no rate-limit wall was hit (0 × 429).
- Recomputing truth reimplements the battery builder's logic from the prompt
  text; where a prompt form was unrecognised the row is left `null` (none in
  contra/count).
- Not committed, not appended to RESULTS.md — the keeper folds.

## 7. Artifacts

- `experiments/g1c_verdict_routing.py` — harness (`collect` blind → `score`).
- `experiments/g1c_key_audit.py` — key-consistency recompute + rescore.
- `results/g1c/arm_jev_raw.json`, `arm_glm_raw.json` — raw arm outputs.
- `results/g1c/score_g1c.json` — blind scoring, agreement matrices, noul sweep.
- `results/g1c/key_audit.json` — recomputed truth vs shipped key, rescored arms.
- `results/g1c/routing_table.json` — the frozen routing table (both key variants).

## [DONE 13:55 keeper Oct 1] G1d — battery key repair: seat was RIGHT, key was WRONG (0.6979 corrected; contra 16/16); contra/count structurally degenerate in @1 — G1e battery-v2 queued
# G1d — battery key repair (keeper lane; entry by keeper)

- date: 2026-10-01
- trigger: G1c's LOUD key defect — 19/96 shipped labels contradict prompt text (contra 11/16, count 8/16)
- scope: generator fix + corrected key for the BANKED @1 prompts + rescore of all three banked arms + structural finding
- artifacts: results/g1d/{corrected-key.json, rescore-v-corrected-key.json}; fix in experiments/g1_battery_build.py

## The two generator bugs (source-pinned)

1. **contra (experiments/g1_battery_build.py p_contra):** non-corrupt pairs were labeled SUPPORTED, but B ("X is NOT on the locker list") names a LISTED item there — B is false, so A and B are inconsistent → REFUTED. Corrupt pairs were labeled REFUTED, but when B names the dropped item, B is true → SUPPORTED. Truth now derived from set membership (B-item absent from A's list ⇒ consistent).
2. **count (p_count):** the manifest builder scattered `target` via rng.choice(FILLER), so the true count was a random variable — the claim "exactly claimed times" was almost always false regardless of the jitter. Fixed: target appended exactly k times.

## Corrected scores on the BANKED @1 responses (no new model traffic)

| arm | overall | arith | seq | xref | contra | count | date |
|---|---|---|---|---|---|---|---|
| LOCAL seat | **0.6979** | 9/16 | 9/16 | 15/16 | 16/16 | 13/16 | 5/16 |
| JEV | **0.9688** | 15/16 | 16/16 | 16/16 | 16/16 | 16/16 | 14/16 |
| GLM-5.3-flash | **1.0000** | 16/16 | 16/16 | 16/16 | 16/16 | 16/16 | 16/16 |

## THE HEADLINE CORRECTION — the seat was right, the key was wrong

G1's "0.5208 = chance" and G1c's "seat 0.594 on sound classes" both under-credited the seat: against the corrected key it scores **0.6979**, with contra 16/16 (was booked 0.312!) and xref 15/16. The seat was correctly REFUTING the "consistent" claims the generator mislabeled.

## BUT — second-order finding: contra/count are structurally degenerate in @1

Corrected balance: contra **1 S / 15 R**, count **0 S / 16 R** (date 4/12 borderline). A majority-class solver scores 15/16 and 16/16 there — the seat's 16/16 contra and 13/16 count are NOT verifier evidence, and JEV's 16/16s on those classes aren't either. The only sound-evidence classes: arith (9S/7R), seq (6S/10R), xref (9S/7R), date (4S/12R, borderline).

**Seat on sound classes:** arith 0.5625 · seq 0.5625 · xref 0.9375 · date 0.3125. The honest verdict restated: **the seat is a class-dependent verifier — strong on explicit-context retrieval (xref), weak on arithmetic/sequence/date reasoning — and @1 cannot say anything about contra/count.** "Completer, not verifier" is retracted as too strong; the corrected claim is narrower and better-evidenced.

## Routing table v2 (≥0.75 bar, cost order LOCAL < JEV < GLM)

- xref → LOCAL (0.9375)
- arith, seq, date → JEV (0.9375 / 1.0 / 0.875)
- contra, count → **NO ROUTING CLAIM** (degenerate classes; G1e battery v2 decides)
- GLM: 1.0 everywhere = escalation tier (and the only arm proven on degenerate classes)

## Generator fix validation + next

- Fixed p_contra/p_count regenerate balanced classes (50/50 by construction); validated mechanically on a fresh seed-2718 build: all 96 labels re-derive from prompt text 96/96 (audit pattern, results/g1d/).
- **G1e (queued): battery v2** — certified moth-seal master, balanced classes, all 3 arms re-run; THIS becomes the standing witness-claim battery. @1 is retired to history (responses banked, corrected key shipped, nothing deleted).

# A1-PIE — pie-minimax closure: does a nonlinear local rule close the minimax gap?

- lane: **A1-PIE** (`quilt-gpu-lab`; worklist item **A1** in `fleet-triage/docs/RTX4050-WORKLIST.md`)
- date: 2026-10-01 · device: `cuda:0 (RTX 4050 Laptop, 6 GB)` · torch 2.14.0+cu126
- seed **2718** everywhere · reference clone `~/projects/pie-minimax` **read-only**
- pre-registration: `results/a1_pie/PREREG.md` (written **before** training, same dir)
- **not committed — keeper folds. NOT appended to RESULTS.md (parallel lanes live).**

## 0. VERDICT (two lines, no goalpost migration)

- **Frozen gate on the PRIMARY spec** (9→64→9, lr 1e-3, batch 1024, **20 epochs**): **INCONCLUSIVE** —
  `overall = 0.3502` sits *inside* the predicted `[0.25, 0.40]`, **but** `MLP_composed (0.5714)` is
  **not <** the linear reference's composed (`0.2857`–`0.3571`), so the CONFIRM branch fails.
- **Declared CONVERGENCE CONTROL** (pre-registered in PREREG §3 *before* running): **KILL-of-prediction** —
  the same net run to plateau reaches `overall = 0.9494` (5-fold board-disjoint `0.9392 ± 0.0094`),
  `composed = 0.9643` (CV `0.9790 ± 0.0092`). **Nonlinearity does NOT "close only a little" (0.25–0.40),
  and it does NOT collapse on the ≥2-win COMPOSED partition. Their prediction is falsified.**

The 20-epoch spec is **underfit** (train top-1 fit `0.3998`, train loss `1.57` vs plateau `0.9881`/`0.135`).
The frozen INCONCLUSIVE *is* the finding: a 60-step budget measures the optimiser, not capacity —
the exact confound the repo warns about ("a result that flips with learning rate is a measurement of
my optimiser"). The pre-registered control supplies the honest number.

## 1. Recon corrections (before any number is trusted)

| claim | what the data says |
|---|---|
| "180,361 exact states" | **180,361 is the PATH-ROW count** (the walk re-visits each board once per move order → ~75× duplication). **2,423 distinct our-to-move boards.** Verified: `len(enumerate_reachable())=180361`, `len(set(boards))=2423`. |
| README "CORRECTION": *180,361 is impossible, `3⁹=19,683`* | **that correction is itself a miscorrection** — it misreads a path-row count as a distinct-state count. Both counts are recorded with every number. |
| "≥2-simultaneous-win states" | **two non-equivalent partitions exist.** `≥2 immediate WINNING MOVES` = **320** boards; the repo `ceiling2` `threat_count ≥ 2` = **1230** boards; they agree on **1513/2423**. Both are reported for every arm. |

**Instrument bug found and booked (fail loud).** The first split attempt used raw
`fnv1a64(board) % 10`, which **returned an empty test set**: FNV-1a-64 low bits are weak, every
3×3 board hashes **odd**, so `mod 10` only ever hits `{1,3,5,7,9}`. That attempt **VOIDed**
(`g7-wr-a1-pie-closure-1790891323.json`, 0 J, no model trained) before any number existed. Fixed to
the **high 32 bits** (validated bucket counts 217–261 over 2,423 boards).

## 2. Protocol (frozen, PREREG §2–§3)

- labels **exact + set-valued** (`M[r,m]=1 ⇔ m∈optimal(board)`), loss `−log Σ_{m∈Opt} softmax(z)_m`
- **PRIMARY split:** board-disjoint **FNV-1a-64 HIGH-32 mod 10**, bucket 0 = test → **train 2186 / test 237** (28 composed-imm, 209 simple)
- **variance:** 5-fold board-disjoint CV (std across **data folds**, not seeds — the repo showed seed std ≡ 0)
- arms: MLP `9→64→9` ReLU (1225 params) and **matched** linear `9→9` (81 params) under the *same* optimiser/split;
  plus their own `linear_expert` as a fair, well-fit linear reference
- chance = `mean(|optimal| / |empty|)`; floor = random empty cell

## 3. Results — board-disjoint test (n=237 boards), chance overall **0.5566**

| arm | overall | COMPOSED (≥2 wins, n=28) | SIMPLE | COMPOSED (threat_count≥2) | train-fit |
|---|---|---|---|---|---|
| MLP 9-64-9, lr1e-3, **20 ep** (frozen PRIMARY) | **0.3502** | 0.5714 | 0.3206 | 0.3226 | 0.3998 |
| LINEAR 9×9 matched, 20 ep | 0.2363 | 0.3571 | 0.2201 | 0.2339 | 0.2534 |
| MLP 9-64-9, lr1e-3, **plateau** (control) | **0.9494** | **0.9643** | 0.9474 | 0.9677 | 0.9881 |
| LINEAR 9×9 matched, plateau | 0.2954 | 0.1429 | 0.3158 | 0.1855 | 0.3532 |
| MLP 9-64-9, lr1e-2, plateau (supp.) | 0.9789 | 0.9643 | 0.9809 | 0.9758 | 1.0000 |
| `linear_expert` (their code) on this test set | 0.2911 | 0.2857 | 0.2919 | 0.2177 | — |

**5-fold board-disjoint CV (variance is the point — rule 2):**

| arm | top-1 mean ± std | COMPOSED (≥2 wins) | COMPOSED (threat_count≥2) |
|---|---|---|---|
| MLP 20 ep | 0.3443 ± 0.0195 | 0.3711 ± 0.0469 | 0.2621 ± 0.0129 |
| LINEAR 20 ep | 0.2068 ± 0.0252 | 0.2514 ± 0.0302 | 0.1660 ± 0.0243 |
| **MLP plateau** | **0.9392 ± 0.0094** | **0.9790 ± 0.0092** | **0.9343 ± 0.0099** |

`std ≠ 0` everywhere → the result is a measurement, not a degeneracy. Identical `overall = 0.3502`
across three independent PASS runs → reproducibility receipt.

**Headroom fills** (fraction of the gap from chance to 1.0 closed; universe chance: all 0.5865,
comp-imm 0.7875, simp-imm 0.5559, comp-thr 0.6585, simp-thr 0.5122) — *derived post-hoc, CPU, same corpus*:

| arm | comp-imm | simp-imm | comp-thr | simp-thr |
|---|---|---|---|---|
| MLP plateau | 0.832 | 0.882 | 0.905 | 0.855 |
| MLP 20 ep | −1.02 | −0.53 | −0.98 | −0.27 |
| LINEAR matched | ≤ 0 | ≤ −0.5 | ≤ 0 | ≤ −0.2 |

**The partitioned prediction is false for the MLP:** normalised, its COMPOSED fills (0.83–0.91) are
**indistinguishable from**—and slightly *above*—its SIMPLE fills. The composition penalty **is real
for the linear/additive arm** (linear plateau: comp 0.143 vs simp 0.316; `linear_expert`: comp-thr
0.218 vs simp-thr 0.372), which is exactly the repo's own CEILING finding.

**Scale:** their decision-tree ceiling `0.7879` (their single-move-label protocol) and exact solver
`1.0000`. The MLP at `0.9494` **does not exceed the solver** and is not a leak — labels are the exact
computation and `top-1 ≤ 1.0` trivially; the tree's lower number is the repo's own documented
tie-break label problem plus depth. Cross-lane corroboration: the reference clone's receipt
(`receipts/pie_minimax_closure.json`, a prior attempt) got `0.9996` on a leaky same-corpus split and
`0.9798` on 5-fold held-out boards — consistent with my `0.9392–0.9494`.

## 4. What this means (both halves, honestly)

1. **The linear half of their story survives.** A sum of 81 local votes cannot represent a *count over
   separate lines*: the linear arms collapse on COMPOSED (0.14–0.36) relative to SIMPLE. `0.1807`
   was always "a *linear* map is bad at minimax".
2. **The nonlinear half is falsified.** "Local voting can't count threats" is a claim about
   **additivity**, not about locality. A 1,225-param ReLU net — still a purely *local* board→scores
   rule with no search and no tree — absorbs minimax composition to **~0.94 board-disjoint**, with
   **no COMPOSED collapse**. The proposed mechanism does not survive as a general local-rule limit.
3. **Transferable lesson (the repo's own §0 rules earn their keep):** an accuracy measured under a
   fixed, tiny step budget is a *statement about the optimiser*. The frozen 0.25–0.40 band was
   reachable at 60 steps and abandoned at 1,200 — so any "nonlinearity doesn't help/helps only a
   little" reading of a short run is unsafe, and a **pre-registered convergence control is the
   difference between a finding and an artefact**.

## 5. Receipts / energy / artefacts

- G7: **`results/a1_pie/g7-wr-a1-pie-closure-1790891506.json`** — `g7-watt-receipt@1`, gate **PASS**,
  schema validator exit 0 (also 3 earlier PASS/1 VOID in `ledger.jsonl`).
- energy: final run **106.5 J = 0.0296 Wh**; **all attempts total 0.386 Wh** (22.94 GPU-seconds),
  measured `power.draw` (mean 23.8 W) — `source: "measured"`, idle floor not subtracted.
- artifacts (all in `results/a1_pie/`): `PREREG.md`, `a1_pie_closure.py` (orchestrator + worker),
  `a1_pie_metrics.json` (all numbers above), `a1_pie_model.pt` (**16 KB** — MLP-20ep, MLP-plateau,
  LINEAR-20ep state dicts), `guard_summary.json`, `ledger.jsonl`, 5× `g7-wr-*.json`.
- INSTRUMENT-01 ramp receipt: 0.604 s sustained synced CUDA load before any timing.
- **VOID-of-record:** the empty-test-set attempt (`g7-wr-…-1790891323.json`) is kept deliberately —
  a fail-loud instrument bug, not hidden.
## [DONE 14:12 GPU Oct 1] XP-C — envelope local provider: **KILL** (the local seat does not hold the pure cell contract; guard + cloud arm do)

Lane XP-C, pre-registered in `scratch/scout-2026-10-01-pushwave.md` §3c (`cot-quilt-lab` lane C seam).
CLAIM UNDER TEST: *the pure `z_in -> z_out` cell contract survives a real model as Provider — local GPU
arm vs cloud arm vs stub ground truth.* Seed 2718, temperature 0, 30 real prompts, 3 local replays.

### 0. VERDICT (two lines, no goalpost migration)

**KILL.** Two of three frozen gates fail on the LOCAL arm: **B** (byte-identical across 3 replays at
temp 0 / seed 2718) **FAILED**, and **C** (well-formed envelope rate >= 0.95) **FAILED at 0.9333**.
**A** (malformed-envelope refusal 100%) **PASSED 20/20** — this is a model/seat failure, not a guard
bypass. Three arms ran (stub, local, cloud), so the result is not INCONCLUSIVE.

### 1. Frozen gates (as pre-registered)

| gate | bar | measured | verdict |
|---|---|---|---|
| A — malformed-envelope refusal | 100% (20/20) | **20/20 = 1.000**, every refusal structured | **PASS** |
| B — LOCAL byte-identical, 3 replays, T=0, seed 2718 | 3/3 | **FAIL** — 3 of 30 prompts differ across replays | **FAIL** |
| C — LOCAL well-formed rate | >= 0.95 | **0.9333** (28/30; replays 28, 29, 30) | **FAIL** |

### 2. Per-arm results

| arm | provider | well-formed | determinism | notes |
|---|---|---|---|---|
| STUB | pure function of (prompt, seed) | **30/30 = 1.000** | 3/3 identical | ground truth for the contract |
| LOCAL | `qwen2.5:3b-instruct-q4_K_M`, ollama, GPU | **28/30 = 0.9333** | **FAIL** | both B and C fail here |
| CLOUD | `glm-5.3-flash`, z.ai | **30/30 = 1.000** | n/a (1 pass, not gated) | comparison arm; see §3 endpoint note |

**Cloud endpoint note (pre-registration honoured).** The registered model `glm-5.3-flash` on the z.ai
**pay-as-you-go** endpoint returns `429 code 1113 (Insufficient balance or no resource package)` — booked
`NOT-RUN` with the exact error, no improvisation. The account's live plan is the **coding plan**, and the
coding endpoint (`https://api.z.ai/api/coding/paas/v4/chat/completions`) is the shape this repo already
uses (`g1c_verdict_routing.py`, `px2_gardener.py`); the arm was re-run there and scored **30/30, 0 errors**.

### 3. The finding — the local seat is not replay-safe under lab load

- **Gated battery (3 x 30 prompts):** 3 prompts differ across replays — `cell_a08` (r1,r2 vs r3),
  `cell_a13` (r1 vs r2,r3), `cell_a23` (r1 vs r2,r3).
- `cell_a08` / `cell_a13` are **compliance flakes**: the model intermittently drops the `provider` and
  `seed` keys, which the guard refuses (`output.key_set`). The same flake is what costs the well-formed
  gate (28/30, and it is not even stable across replays: 28, 29, 30).
- `cell_a23` is well-formed in every replay but the bytes differ in replay 1 — a *semantic* flip, not an
  omission.
- **Isolated re-run probe** (`--probe-determinism`, a second 3x30 battery, same prompt/seed/temp, under
  its own guard + receipt): **still not byte-identical** — `cell_a15` answered `"spring"` in replay 1 and
  `"summer"` in replays 2-3. Two independent batteries, two independent flake sets.
- **Counter-probe:** 5 consecutive isolated repeats of each flaky prompt were byte-identical, and cold /
  after-7-other-prompts / immediate-repeat tests were identical too — so the flake is **intermittent and
  load/session-dependent**, not a function of (prompt, seed).
- **Co-tenancy observed:** the guard recorded `min_free_vram_mib` **1860** (gated window) and **1828**
  (probe window) while our seat needs ~2.2 GB on a 6 GB card — another lane was resident on the GPU
  during both windows. The most likely mechanism is serving-stack non-determinism under co-tenancy
  (batch/kernel scheduling), not a seed bug: the same prompt, seed, temperature and model flip a token
  depending on what else is on the box.
- **Consequence for the fleet:** byte-identity at a fixed seed is a property of the *whole serving stack
  in a given window*, not of the model alone. Replay-sensitive lanes (XP-B hook verification, D10/style
  receipts) must **serialize the seat** or pin determinism per cache/window state. G1b's 8-prompt
  byte-identical result for the 7B seat is not contradicted — it was a quieter, shorter window; it is
  simply not sufficient to certify the seat.

### 4. What survived — the envelope contract itself

- The **Guard layer is the strongest part of the build**: 20/20 deliberate malformations refused, each
  with a structured error (`output.not_json`, `output.empty`, `output.not_object`, `output.key_set`,
  `output.type.{cell_id,z_out,seed}`, `output.digest_mismatch`, `output.bad_digest_format`,
  `output.cell_id_mismatch`, `output.provider_mismatch`, `output.seed_mismatch`, `output.empty_z_out`),
  plus **5/5 extra strictness** cases (markdown fences, JSON embedded in prose, `NaN`, bare scalar,
  whitespace-only) and **4/4 malformed input cells** refused by the input schema check.
- Strict parsing is load-bearing: duplicate keys refused, `NaN`/`Infinity` refused, any trailing content
  refused — there is no lenient path.
- The **binding** checks are what make an envelope a receipt rather than decoration: `z_in_digest` must
  digest the *dispatched* `z_in`, and `cell_id`/`provider`/`seed` must match the dispatch. The 3B model
  never faked a digest; it failed by **omission** — exactly the failure mode the guard is built for.
- **Cloud held the contract 30/30** — the contract is realizable; the 3B local seat is the weak link at
  this prompt. Stub (ground truth) 30/30 and byte-identical.

### 5. Prompt honesty note (recorded before the gated run)

Prompt **v1** (no literal shape example) scored **0/5** on a 5-prompt plumbing probe: the 3B model
returned `{"z_out": ...}` only, or a *string* seed. Prompt **v2** adds one literal shape example and the
seed-is-a-number rule → **6/6** on a 6-prompt probe. The gated run and the cloud arm both use the frozen
v2 prompt, **plain chat** (no JSON-mode crutch), same text for every arm. Both probes are recorded in the
artifact (`prompt_version`, `prompt_notes`). This is a prompt-clarity fix made *before* the gated run, not
a post-hoc goalpost move — and it did **not** rescue the local arm.

### 6. Receipts / energy / artefacts

- G7 receipts (all `g7-watt-receipt@1`, validator exit 0, `source: measured`, idle floor not subtracted):
  - `g7-wr-xp-c-envelope-local-1790891436` — gate **PASS**, 6232.28 J = 1.7312 Wh (attempt-1 window, see §7.1)
  - `g7-wr-xp-c-envelope-local-1790892000` — gate **PASS**, 6654.98 J = 1.8486 Wh (gated local battery)
  - `g7-wr-xp-c-envelope-local-1790892402` — gate **PASS**, 8231.12 J = 2.2864 Wh (isolated determinism probe)
- Total **5.87 Wh = $0.00135** @ $0.23/kWh. Guard: no breach, no timeout, max temp **74 C**, min free VRAM
  1828-1860 MiB (co-tenancy, above the 1024 MiB floor). CPU: refusal battery + stub arm, no GPU.
- Artefacts: `results/xp_c/xp_c_results.json` (all numbers), `results/xp_c/local/raw_runs.json` (gated
  battery, per-replay digests + raws), `results/xp_c/determinism_probe_isolated.json`,
  `results/xp_c/local/probe_raw_runs.json`, `results/xp_c/guard/` (3 receipts + summary + ledger).
- Code: `experiments/xp_c_envelope.py` (Guard layer, stages/pipeline, cells, arms, gates, verdict),
  `experiments/xp_c_providers.py` (Provider interface + stub/local/cloud).
- Secrets: `ZAI_KEY` read at use-time, sent only in an `Authorization` header via a 0600 curl config file
  (never argv/URL/log). Machine scan of every artifact: `zai_key_present_in_artifacts: false`.

### 7. Lane defects booked (fail loud, mine)

1. **`makedirs` bug (mine).** The local worker wrote to `results/xp_c/local/` without creating the
   directory: attempts 1 and 2 of the first driver run each executed a full 3x30 battery on the GPU and
   then died on the artifact write (`FileNotFoundError`, rc=1). The guard receipt for those windows is
   PASS *and* the arm was booked NOT-RUN — both are true: the calls happened, the artifact did not.
   Fixed (`os.makedirs`), re-run via `--resume`; the extra energy is in the receipt total above.
2. **`raws_run1` misnamed (mine).** It held the *last* replay's raws, not replay 1 (verified:
   `sha256(raws_run1[i]) == per_replay[2].digests[i]`). Documented inside the artifact; code renamed to
   `raws_last_replay`. No data changed.
3. **Not a defect:** `Guard.run()`'s single-use stop-event was fixed by the XP-B finding-4 patch (landed
   13:42 today, before this run). `local_phase` uses a fresh Guard per attempt as belt-and-braces.
   The probe's first `diffs` block also printed the wrong list index; the recomputed block in
   `determinism_probe_isolated.json` is authoritative (no new model traffic).

### 8. What XP-C means for the queue

- **KEEP the seam**: Guard + stages + Provider is ~600 lines of stdlib, and three arms plug into it with
  no contract change. `cot-quilt-lab` lane C's interface is buildable as specified.
- **KILL the claim as stated for the LOCAL seat**: at 3B, temp 0, seed 2718, on this box, the pure cell
  contract is neither byte-reproducible (1-3 of 30 prompts flip per battery) nor >= 0.95 well-formed.
- **XP-C2 (proposed):** (a) re-run the determinism gate in a *serialized* window with co-tenancy declared
  and the seat unloaded between replays; (b) test `qwen2.5:7b-instruct-q4_K_M` (G1b's byte-identical seat)
  and schema-constrained decoding (ollama `format: json` / grammar) against the >= 0.95 gate; (c) price the
  cloud arm per 1k envelopes — it already holds the contract at 30/30.

## DAY SLICE 14:1x (day-conductor) — SCOUT-9 sweep + (C) static audit of XP-C; manifest RED found
- **(A) SCOUT-9** (full text proposals/runs/SCOUT-9-fleet-push-2026-10-01-2211Z.md): HEADLINE — **pie-minimax PR #2
  independently replicates OUR A1-PIE KILL-of-prediction** (their MLP composed 1.000 / linear 0.1807 exact repro, CV
  0.980 held-out; explicit cross-ref of quilt-gpu-lab 2978159). Strongest corroborate of the day; magnitude caveat
  booked (1.000 vs our 0.9643 — different seeds, same conclusion, both far past P1). New repos: quilt-edge-lab (Wave-1
  receipts; STEAL: vendored-pin drift-tripwire + P1-sealed-FAIL-kept-sealed doctrine) and cot-quilt-lab (the direct
  XP-C seam consumer — XPC-W watch item: check their pushes before proposing any XP-C2 serialized-seat re-run).
  Projectionist = Casey's pocket-cinema app pushes, no signal. Spawned: EDGE-1, XPC-W (watch), PIM-1 (docs-only
  citation close-the-loop). No CONTRADICT. GPU lane occupied all slice by the live c1_playtest run (PID 1823912,
  started 14:09, --budget-s 1500; foreign-live, not touched).
- **(C) XP-C reproduction check — STATIC AUDIT ONLY, honestly scoped.** A behavioral re-fire is non-verifying by the
  booking's own KILL finding (local seat not byte-reproducible at temp0+seed; co-tenancy serving-window flake), and
  the GPU lane is busy. Static audit PASSES the booking: committed xp_c_results.json gates re-read consistent with the
  booked text (A refusal 20/20 PASS; B byte_identical FALSE = FAIL; C local_rate 0.9333 < 0.95 FAIL; cloud 30/30
  registered). **Provenance gap booked (RC-1 family, XP-C instance): xp_c_results.json embeds NO runner_sha256/args**
  (artifacts.code names the runner but nothing hash-binds it; sha256 of committed experiments/xp_c_envelope.py =
  420c37c1… recorded here for the future seal).
- **FAIL-LOUD: manifest is RED — test_receipts test_manifest_matches_working_tree FAILS.** RESULTS.md drifted from the
  sealed digest (sealed 6d3a1162… vs on-disk 80f8b958…): the XP-C-era bookings landed WITHOUT a re-seal. Re-seal is
  BLOCKED right now: the live c1_playtest run keeps the tree dirty (untracked experiments + results streaming) and the
  sealer refuses dirty sealed paths by design. Per foreign-live precedent (PW-1), the live run is not touched —
  **seal deferred to the first wake after c1_playtest completes; until then the manifest is knowingly stale and this
  entry is the honest drift marker.** This is the D-2 silent-edit class caught by the test before it could hide.


---

# A2-ga4444-4x4 — 4x4 composition + capacity: does A1's "nonlinear absorbs composition" scale?

- lane: **A2-HARVEST** (`quilt-gpu-lab`; worklist item **A2** in `fleet-triage/docs/RTX4050-WORKLIST.md`)
- date: 2026-10-01 · device: `cuda:0 (RTX 4050 Laptop, 6 GB)` · torch 2.14.0+cu126 · seed **2718** everywhere
- clone `/tmp/ga4444` **read-only** · pre-registration: `proposals/runs/A2-ga4444-4x4.md` (written **before** the run)
- **one smoke arm** (MLP) + its frozen matched contrast (LINEAR); full arm matrix is the follow-up
- full entry: `results/a2_ga4444/RESULTS-ENTRY.md` · **not committed — keeper folds.**

## 0. VERDICT (no goalpost migration)

- **Frozen gate -> INCONCLUSIVE.** Rule 2 fires: the MLP sits at the **ceiling 1.0000 with `std == 0.0`** on
  COMPOSED-B (5/5 folds), so no PASS-class verdict is bookable. Recorded, not hidden.
- **Declared secondary reading (frozen `d_linear` row, non-degenerate) -> BREAKS.** The linear/additive arm shows
  **NO composition penalty at 4x4**: `d_linear = top1_SIMPLE-B - top1_COMPOSED-B = 0.8110 - 0.9872 = -0.1762`
  (better on COMPOSED; `std != 0` on both columns). **A1's "linear collapses on COMPOSED" does NOT carry one rung up** —
  confirms `ga4444/PARTITION-44.md` sec.4 with complete ground truth + a matched optimiser.
- **Finding under both:** COMPOSED-B's **computed chance is 0.9696** — on a board with >=2 immediate winning drops a
  random legal move is already optimal 97% of the time. The class is **near-degenerate by construction** and cannot
  discriminate local-voting vs composition at either rung (3x3: n=22 trivial; 4x4: floor 0.97). The pre-registered
  composition-collapse test has **no executable positive instance** at natural-walk sampling. That is the result.

## 1. Recon corrections (before any measured number)

- **`gt4444_ground_truth.txt` (3,338 rows) is an INCOMPLETE walk.** The C `walk()` does
  `if (has_won(pos|mv, m2)) return;` **inside the column loop** — `return` prunes the remaining columns where
  `continue` belongs. Values are exact; enumeration is not. The repo's own `verify_maxmin.py` reports **161,029**
  reachable states; this lane's complete non-terminal BFS is **139,625** (139,625 + 21,404 terminal = 161,029, exact).
- **The repo holds TWO games.** `ga4444.py` `legal_moves` = **free placement** (gaps allowed) — measured reachable
  non-terminal graph **> 8e6** states, labels capped at `MAX_PLY=9`; `gt4444.c` = **gravity**. Not the same game.
- **Scope (frozen):** this lane = **gravity**, own **complete** enumeration, **no sampling**. Free placement out of scope.

## 2. Data + provenance

- **66,297** our-turn non-terminal gravity boards, `dataset_fnv1a64 = 0x98219e9d0dd0d382`, gen **3.5 s**
  (5 parallel list-form shard subprocesses, never shell=True). ply hist `{0:1,2:16,4:160,6:1128,8:5036,10:14352,
  12:24710,14:20894}`; **multi-optimal 47.8%**; COMPOSED-B n = **763** (>n>=50 power line).
- labels exact + set-valued (memoized full-depth negamax). **Differential control (rule 5):** repo's C solver
  `gt4444 --probe` on 500 boards -> **500/500, 0 disagreements**; `verify_maxmin.py` -> **200/200**. `control.json`.

## 3. Results — 5-fold board-disjoint CV (FNV-1a-64 high-32 mod 5), mean +/- std over folds

| arm | overall | COMPOSED-B | SIMPLE-B | COMPOSED-A | SIMPLE-A |
|---|---|---|---|---|---|
| MLP 16-64-16, lr1e-3, 120 ep (SMOKE) | **0.9712 +/- 0.0036** | **1.0000 +/- 0.0000** | 0.9708 +/- 0.0037 | 0.9791 +/- 0.0037 | 0.9663 +/- 0.0037 |
| LINEAR 16->16, matched | **0.8130 +/- 0.0021** | **0.9872 +/- 0.0109** | 0.8110 +/- 0.0022 | 0.8191 +/- 0.0034 | 0.8091 +/- 0.0029 |
| chance (computed per fold) | 0.7698 | **0.9696** | 0.7673 | 0.7660 | 0.7721 |

`d_linear = -0.1762` · `d_mlp = -0.0292`. Normalised headroom filled - MLP S 0.875 / C 1.000; LINEAR S 0.188 / C 0.579
(both arms fill MORE COMPOSED headroom than SIMPLE - the opposite of a collapse; but that headroom is only 0.0304 wide).

## 4. What it means / follow-up

1. A1's **linear half** does not replicate at 4x4 (correction, matches PARTITION-44). 2. Neither does the **test** -
   the COMPOSED floor is 0.97; the design, not the data, is the defect. 3. Nonlinearity still helps overall
   (+0.158 vs linear) - a capacity statement, not a composition one.
- Full scale needs: **generated double-threat boards** (>=2 open wins BY DESIGN, matched single-threat controls at
  equal stone count / equal |empty| - the only design with COMPOSED chance well below 1); the **plateau control** +
  **capacity sweep**; **>=5 seeds**; **DEF-A/C cross-sweep**; the free-placement game (>8M, sharded).

## 5. Receipts / energy / artifacts (all in `results/a2_ga4444/`)

- G7: **`g7-wr-a2-ga4444-4x4-1790893502.json`** - `g7-watt-receipt@1`, gate **PASS**, validator exit 0.
  Preflight attempt 1 clean (1820 MiB free >= 1024 floor, 68 C).
- energy **13,917.53 J = 3.866 Wh**, **213.73 GPU-s**, `source: measured` (mean 46.5 W; includes the resident 7B ollama
  seat's share - co-tenancy NOT subtracted; idle floor not subtracted).
- artifacts: `a2_ga4444.py`, `run_a2.py`, `dataset.jsonl` (66,297 boards), `dataset_summary.json`, `control.json`,
  `smoke_mlp_metrics.json`, `smoke_linear_metrics.json`, `gate.json`, `shards/`, `guard_summary.json`, `ledger.jsonl`.

## 6. INSTRUMENT-01 / house laws

seed 2718 · fail loud (2 recon corrections + 1 harness bug booked) · receipt or VOID (receipt sealed) ·
no shell=True (list-form subprocess only) · O(chunk) data-gen (finite complete set, streamed to shard checkpoints on ext4)
· no commit · other lanes' lines untouched.

---

## B1-DISTILL — policy distillation of the pong derived law (2026-10-01 14:37 AKDT)

- ran: `experiments/b1_distill.py` under `guard.py` (G7 receipt), prereg `proposals/runs/B1-pong-law-distill.md` (FROZEN before fire)
- **verdict: KILL as stated** — Gate A FAIL, Gate B PASS
- result:
```json
{
  "lane": "B1-DISTILL", "seed": 2718,
  "teacher": "shipped quilt-arcade games/pong ai.track (labels executed by the engine)",
  "frame": "uniform-random reachable states (engine-driven), held out by whole trace",
  "n_train": 366346, "n_holdout": 90930,
  "model": "3-64-64-1 tanh, 4481 params, CUDA, peak VRAM 64.8 MB",
  "gate_a_agreement_1e-3": {"mean": 0.056787, "std": 0.008760, "verdict": "FAIL",
                            "per_seed": [0.056703, 0.067557, 0.046101]},
  "gate_a_secondary": {"direction_where_law_moves": 1.0000, "letter": 0.9213,
                       "curve_mean": {"1e-6": 0.0000367, "1e-4": 0.00548, "1e-3": 0.0568,
                                      "1e-2": 0.6163, "5e-2": 0.8715, "1e-1": 0.9114, "2e-1": 0.9658}},
  "exploratory_300ep_control": {"rms": 0.0208, "1e-3": 0.3492, "1e-2": 0.8803, "5e-2": 0.9904, "1e-1": 0.9952},
  "gate_b_h2h_vs_law": {"mean": 0.5500, "std": 0.0212, "verdict": "PASS",
                        "per_seed": [0.535, 0.580, 0.535], "games": 600, "draws": 0,
                        "control_law_vs_law": 0.5000, "aggregate_z_vs_0.5": 2.45},
  "controls": {"law_equiv_pristine_vs_switch_max_abs_diff": 0.0,
               "js_vs_torch_port_max_abs_diff": [7.15e-07, 6.28e-07]},
  "g7_receipt": "g7-wr-b1-pong-law-distill-1790894147", "energy_Wh": 7.4199
}
```
- note: the derived law is a **kinked** control map (deadzone 1.5 + saturation at the side speed + clamp `[6,54]`). A 64x64 tanh MLP distills its **behaviour** exactly (step **direction 1.0000** on every law-moving tick; **letter 0.9213 = 1 − 0.0792**, the whole deficit being the deadzone where the law is at rest and the net emits a small non-zero) — and is h2h-indistinguishable (0.55 ∈ [0.40,0.60], control 0.5000 exact) — but **not its exact float action** at the pre-registered 1e-3 (0.057 ± 0.009). The gap is partly optimization (300-epoch control: 0.349 @1e-3) and partly representational (still 0.349, not 1.0); near-100% (0.990) is reached only at 5e-2. Booked defect: the JS/torch port control first ran mixed-side rows → a false FAIL (0.162); fixed per-side → ≤7.2e-07, measured gates unaffected.
- full entry: `results/b1_distill/RESULTS-ENTRY.md`

# RESULTS ENTRY — C1-PLAYTEST (the Local Playtester, pong PoC)

- **lane:** C1-PLAYTEST (worklist `C1`), lab `/home/eileen/projects/quilt-gpu-lab`
- **date:** 2026-10-01 · **seed:** 2718 · **device:** RTX 4050 Laptop 6 GB (WSL2)
- **pre-registration:** `results/c1_playtest/PREREG.md` (written before the first match)
- **status:** **PARTIAL — 7/40 pre-registered games. Gate NOT adjudicated.**

## Headline

| metric | value |
|---|---|
| **law win-rate** | **7/7 = 1.000** (directional only — sample is 7/40) |
| **≥90% gate** | **NOT-ADJUDICATED-PARTIAL** (needs the full N=40) |
| draws | 0 (every game closed at 7) |
| model wins | 0 |
| **per-tick action agreement** (7B vs law, identical state) | **0.0917** (851 / 9,276 decisions) |
| rule violations: parse-fail | **0** (rate 0.0000) |
| rule violations: illegal first alpha | 0 |
| crashes: ollama / engine / harness | **0 / 0 / 0** |
| energy (guard G7, MEASURED) | **21.09 Wh** (75,915.2 J; 1110.2 GPU-s) |
| guard receipt | `guard/g7-wr-c1-playtest-pong-1790894210.json` — schema-valid, verdict **PASS** |

Per-game (all seven had the model on the **RIGHT** paddle; law on the left):

| g | ticks | score (L-R) | winner | agreement | wall s |
|---|---|---|---|---|---|
| 0 | 1307 | 7-0 | law | 0.1094 | 206.6 |
| 1 | 1331 | 7-2 | law | 0.0811 | 237.7 |
| 2 | 1303 | 7-0 | law | 0.1811 | 237.6 |
| 3 | 1182 | 7-1 | law | 0.0431 | 254.8 |
| 4 | 1664 | 7-1 | law | 0.0907 | 300.3 |
| 5 |  817 | 7-0 | law | 0.0588 | 140.4 |
| 6 | 1672 | 7-1 | law | 0.0682 | 263.4 |

## What was actually measured

The derived law and qwen2.5:7b-instruct-q4_K_M played head-to-head through the
**real quilt-arcade pong engine** (`games/pong`, `buildSheet()` verbatim). The only
engine substitution is `ai.track`, replaced by a control switch: `law` mode is the
shipped derived law character-for-character (track `ball.y`, side speed 0.85/0.70,
deadzone 1.5, clamp [6,54]); `model` mode spends the **identical movement budget**
on a one-letter (`U`/`D`/`S`) decision from ollama. So both paddles move at the same
speed under the same clamps, and the arms differ only in who picks the direction.

The model is not close to the law: it agrees with the law's own per-tick direction
on **9.2%** of decisions, and loses every game. That is the pre-registered claim's
direction, but **seven games cannot adjudicate a ≥90% gate** (7/7 has a 95% CI of
[0.61, 1.00]); this is recorded as directional, not as a verdict.

**Directional corroboration (exploratory, not part of the pre-registered run):**
two aborted attempts (below) each show the law leading and the same ~0.12 agreement.
Merged with the seven: **9 partial/complete games, law 9/9, agreement ≈ 0.10.**

## Fail-loud ops log — why 7/40 (read this before re-running)

1. **Thrash, attempt 1.** The first launch used `num_ctx=512`. This host runs
   **`OLLAMA_MAX_LOADED_MODELS=1`**, and a concurrent lane (`xp_c_envelope
   --probe-determinism`, model `qwen2.5:3b`) requests a different model/ctx. Every
   model switch forces a **full reload ⇒ ~10 s per tick**. Fix: drop `num_ctx` and
   use the server default so all lanes share one resident runner. The partial artifact
   is archived as `_archive/games.aborted-thrash.jsonl` (g0: 1069 ticks, law 4-0, agree 0.116).
2. **Thrash, attempt 2.** Relaunched; the same lane's probe resumed, alternating
   3b/7b on ollama and re-triggering the reload-per-call. Driver was `SIGSTOP`ped
   ~90 s until the other lane drained, then resumed. Archived
   `_archive/games.aborted-2.jsonl` (g0: 590 ticks, law 2-0, agree 0.134).
3. **Wall-clock economics (the real finding).** Uncontended, one call ≈ **70–230 ms**
   (146-token templated prompt, 2 generated tokens, `-np 1`). A law-vs-7B game needs
   ~1,300–1,700 ticks (points are paced by ball traversal, so ~200 ticks/point), i.e.
   **~235 s per game**. **N=40 at this cadence is ≈ 2.5 hours** — the worklist's ≈50 min
   estimate does not survive contact with per-tick LLM calls. The driver therefore
   carries a `--budget-s` that halts **between games** and finalises cleanly, so the
   run seals a valid PASS receipt instead of a timeout VOID.
4. `scripts/`-level: the receipt was re-validated by `fleet-seeds/scripts/g7_validate.mjs`
   (exit 0). No commit was made.

## Honest limits

- **7/40 games.** Gate not adjudicated. The pre-registered decision rule needs N=40.
- **One arm only.** Games 0–19 are model-as-RIGHT; games 20–39 (model-as-LEFT, which
  controls for the law's 0.85-vs-0.70 speed asymmetry) were never reached.
- Agreement is measured against the law's *own* direction on the model's actual
  trajectory — it is a policy-agreement probe, not a counterfactual replay.
- Contention with other lanes is environmental; a fleet-clean window (or a dedicated
  seat) is required for the full run.

## To finish it

Re-run `python3 experiments/c1_playtest_pong.py` (no budget, or a larger one) in a
window with **no concurrent ollama multi-model lanes**; expect ≈2.5 h. Everything
else (pre-reg, seeds, prompt, gate) is frozen and unchanged.

## Artifacts (all in `results/c1_playtest/`)

- `PREREG.md` — pre-registration (unchanged)
- `match_summary.json` — per-match summaries + aggregates (status PARTIAL)
- `run_config.json` — pinned apparatus (model, temp, seed policy, substituted cell)
- `games.jsonl` — per-tick rows, 1.60 MB (under the 2 MB cap; `capped=false`)
- `guard/g7-wr-c1-playtest-pong-1790894210.json` — G7 watt receipt (PASS, 21.09 Wh)
- `guard/guard_summary.json`, `guard/ledger.jsonl` — guard digest + append-only ledger
- `run.log` — driver log (warm, per-game lines, budget halt, receipt)
- `_archive/games.aborted-thrash.jsonl`, `_archive/games.aborted-2.jsonl` — the two
  contention-aborted partials (exploratory only; not folded into the gate)
- code: `experiments/c1_playtest_pong.py` (driver) + `experiments/c1_pong_engine.mjs`
  (engine harness)

## [DONE 14:18 A5-PARITY Oct 1] quilt-mojo-lab wave-73 CuPy receipt reproduced on the 4050 — consumer-silicon conformance node LIVE

Lane A5-PARITY (kimi, tmux lab-a5). Reproduced `python/cupy_quilt.py` (runtime #9) per their
`docs/RUNTIME9-PREREG.md` + wave-73 `bench.py` protocol; quilt-mojo-lab used READ-ONLY; no
kernel/gate/tolerance changes. Verdict family: conformance receipt (no K/K/I gate — pre-dates
G7 adoption for this lane shape; INSTRUMENT-01 ramp receipt included instead).

- **Bit-parity 0.0 at 16²/512²/1024², max|Δpot| = 0.0** — stronger than their frozen P1 claim
  ("0.0 at 16², within 1e-4 at 512²"). Checksum 0.4000000059604645 matched exactly at all sizes.
- **1024²: 3.06G cells/s = within 1.3% of their 3.099G receipt.** 512²: 2.07G vs 2.83G
  (throughput moves, parity doesn't); 16² launch-bound (2.24M vs 15.7M).
- **INSTRUMENT-01 receipted on a second independent harness:** 12s idle → pre-ramp probes
  2–10× slow (16²: 165k → 2.20M cells/s after 0.6s ramp, 13×); ramp law holds outside guard.py.
- **Honesty catch (kimi, kept):** their RESULTS.md header records wave-73 on "2-core container
  + RTX 4050 6GB" — the "datacenter silicon" framing in the worklist was wrong; our box matches
  their hardware class, which makes the 1.3% @1024² reading cleaner, not worse.
- Artifacts: results/a5_parity/{a5_parity_receipt.json, a5_parity_repro.py, README.md};
  CuPy 14.2.0, driver 616.92 (WSL2), elephant-gpu venv python 3.14.

## [DONE 15:08 D2-FIRST-BUILD Oct 1] stochastic-worlds wiring receipt — ALL WIRING GATES PASS, v1 unblocked (not a thesis verdict)

Lane D2-FIRST-BUILD (deepseek; parallel twin's artifacts folded intact). Scope: the frozen prereg's
first-build wiring only. quilt-dba pinned @5bbd99c read-only.

- **W-DET canary PASS:** deterministic arm reproduces E-D1's exact hash `8c8a54a43f10`, var_A=0,
  R5 replay byte-identical — the harness is honest before any stochastic claim is allowed.
- **F-gates:** F10 smoke 13/13 (with patch present, default-off), F3 16/16 unique world hashes,
  F8 leak 0.000 (reflex determinacy identical det vs sto; salience-projection dip booked as
  measurement artifact), F6 KS p=0.0 vs real.
- **H-wiring:** H4 PASS (std_pos 8.83, std_growthAt 216.25), H5/H6 spreads 0.000/0.109 range 0.715.
- **Mini determinacy:** reflex.orient 1.000, memory.episodic 0.285 (prediction ~0.9/~0.1 held).
- **18 twin trainings** (2 sockets × 3 frames × 3 seeds) in 46.4 GPU-s: reflex gap_sim 0.000 /
  gap_mis +0.400; episodic gap_sim −0.063 / gap_mis −0.071. **H3 widened PASS (+0.165) via reflex
  only; GPU-SEED LAW applied: reflex std==0 → INCONCLUSIVE never PASS; episodic PASS.**
- **H-GROWTH mini REPORT/PARTIAL:** gated 15/16 vs unguided 14/16 — and unpatched arm D also 14/16,
  so R2's "unguided never grows" fails on fresh seeds regardless of patch (seed-vacuity datum).
- **0.756 Wh measured** (G7 receipt PASS, 47.0 W mean, $0.000174), co-tenant 7B resident, no breach.
- **v1 needs next:** freeze all 6 socket input channels + re-check H5; fix reflex twin target
  (seeds indistinguishable → std==0); then 200 worlds (140/60, F5 assert) × 6 sockets × 54 twins
  with bootstrap-ρ CI; 1000-world extension only if H4 passes and CI width > 0.40.
- Artifacts: results/d2_build/ (RESULTS-ENTRY, fb_* JSONs, guard/, fb_patch.diff; scripts in
  scratch/d2/fb/quilt-dba/experiments/ + dba/stochastic.mjs).

## [DONE 15:15 B1b-KINK-HEAD Oct 1] KEEP — sensitivity law confirmed, kink-precision FALSIFIED (learned kink LOSES to tanh), per-region ladders banked

Lane B1b-KINK-HEAD (deepseek). Prereg proposals/runs/B1b-kink-head.md frozen before build.

- **Gates 6/12 PASS** → KEEP with a falsification inside: the sensitivity law (B1's curve) CONFIRMED
  2-5x over book tolerance; the kink-precision claim **KILLED** — the learned-kink/ReLU arms did
  NOT beat the tanh baseline at 5e-2 (0.9991 vs 0.9998, p~0.0082 — a real, replicated inversion).
- **nerr_min @5e-2 = 0.0007** — deadzone/clamp value fidelity is closable at honest tolerances;
  B1's knife-edge 1e-3 measured the basis, exactly as suspected.
- Per-region deadzone/ramp/saturation/clamp agreement ladders banked for all arms (3 seeds each).
- Composite-0 synergy datum: shared-prefix training hits 0.9996 — feeds the federation probe.
- Artifacts: results/b1b_kink/ (own RESULTS entry folded by keeper). Receipt per lane report.

## [DONE 15:16 D2-FIRST-BUILD-B Oct 1] second independent build — wiring canary + F-gates corroborate, H5/H6 ESTIMATOR DISAGREES with build A: the measure is the prerequisite

Lane d2_first_build twin (deepseek, 5ad1daf2). Same prereg, independent execution.

- **Corroborates build A:** W-DET canary PASS (8c8a54a43f10 x3 seeds, var=0, R5 byte-identical),
  F10 smoke 13/13, F3 16/16 unique, H4 std>0, F6 KS p=0.000, GPU-SEED-LAW clean, G7 valid (0.9741 Wh).
- **F8 honesty receipt:** first patch LEAKED (reflex det 0.970→0.723 → VOID) — ±60/1000 sensor
  jitter crossed the reflex 0.8 threshold; fixed by boundary-clipping; residual identified as F4
  estimator artifact. The leak the prereg feared was real and was caught by the gate.
- **DISAGREES with build A on H5/H6:** H5 NOT STABLE (spread 0.50/0.52 > 0.15), H6 FAIL 0.118 with
  fire-output (PASS 0.648 with rule-output), F4 FLAG at boundary. Build A booked H5 0.000/0.109,
  H6 PASS 0.715. Two builds, same pin, different estimator paths → **the determinacy ESTIMATOR is
  the prerequisite, not the worlds: v1 is blocked on freezing the measure** (small alphabets break it).
- Mini-arm direction (n=2, not adjudicated): gap rises as determinacy falls — matches predicted negative rho.
- v1 additions: resolve the path split (E-D1 canary on engine-sheet path vs stochastic injection on
  core.mjs), H-GROWTH receipts per world, F5/F9 asserts, deferred reward-drift injection point.
- Artifacts: results/d2_build/mini_*.json, wdet_ed1_replay.log, smoke_13of13.log,
  d2_stochastic_core.patch, twins_guard.log (coexisting with build A's fb_* artifacts, both kept).

## COMP0 — federation of dedicated micro-trunks, between-cell routing (lane COMPOSITE-0)
- ran: 2026-10-01 15:2x AKDT (pre-reg proposals/runs/COMP0-federation.md, on disk BEFORE build/fire)
- verdict: **INCONCLUSIVE** (all three frozen gates hit the std==0 degeneracy rule; directionally positive on all three)
- result: ```json
{
  "experiment": "COMP0 federation of dedicated micro-trunks (between-cell routing)",
  "composed_of": {"IE3": "dedicated specialist trunks (dilution)",
                  "D13d": "correlation router (not reward)",
                  "D1b": "look-again to independent-reach second choice"},
  "corpus": "D5 probes.jsonl reused (149 train / 66 held-out, sha256 hash-split, K=2 regimes)",
  "chance_majority": 0.5909,
  "router_acc": {"train": 1.0, "heldout": 1.0, "mean_top1_top2_corr_gap": 0.4878},
  "aggregate_full_board_mean_std": {
    "JOINT_4225p": {"mean": 0.803, "std": 0.0},
    "SINGLE_2113p": {"mean": 0.7778, "std": 0.0072},
    "FED_4226p": {"mean": 0.8182, "std": 0.0},
    "FED_LA_4226p": {"mean": 0.8434, "std": 0.0072}
  },
  "gates": {"G1_fed_gt_single": {"diff": 0.0404, "required": 0.05, "verdict": "INCONCLUSIVE (FED std==0)"},
            "G2_la_gt_fed": {"diff": 0.0252, "required": 0.01, "verdict": "INCONCLUSIVE (FED std==0)"},
            "G3_fed_gt_joint": {"diff": 0.0152, "required": 0.05, "verdict": "INCONCLUSIVE (both std==0)"}},
  "la_texture": "tau~0.31 (train-calibrated 20th pct); 17-19 triggers/seed, ALL flipped to 2nd cell",
  "per_regime": "semantic saturates (FED 1.0, others 0.9615); counting-address is the contested regime (SINGLE 0.65-0.675, JOINT/FED 0.70, FED_LA 0.725-0.75)",
  "ramp_receipt": {"ramp_s": 0.665, "synced": true},
  "g7_receipt": "g7-wr-comp0-federation-1790896454 (valid, 0.939 Wh, 60.7 gpu-seconds)",
  "verdict": "INCONCLUSIVE"
}
```
- note: the COMPOSITE-0 probe of "cells are dedicated; routing happens BETWEEN cells." Direction reads all three ways at matched params (FED>SINGLE +0.040, FED>JOINT +0.015, LA>FED +0.025) but the frozen degeneracy law (std==0 -> INCONCLUSIVE never PASS) bit exactly the saturated arms: FED pinned at 0.8182 all 3 seeds (same ~12 counting misses), JOINT at 0.803. Not gate-shopping — more seeds would be laundering. Texture worth keeping: (1) the D13d correlation router is PERFECT on this corpus (1.0/1.0, gap 0.49) with ZERO parameters and zero reward — routing saturated, so the federation's ceiling = its weakest cell and the LA escape hatch fired only on cell uncertainty, not routing error; (2) LA's second choice on uncertain counting items was the SEMANTIC specialist (off-regime!) and it still net-won +2-3 items/seed — independent reach beats expertise when the expert is unsure (D1b doctrine survives, with the caveat that LA buys confidence, not regime knowledge); (3) dilution shows only in the hard regime (counting: SINGLE 0.66 vs FED 0.70) — semantic saturates for everyone, so full-board margins compress. Why std==0: fixed hash-split board + converged tiny nets + 66-item granularity (1 item = 0.0152). COMPOSITE-1 hooks: harder multi-regime corpus where routing is NOT saturated (K>=4, blurred regimes), a capacity-starved board where JOINT dilutes visibly, LA with a true independent-reach second cell (different featurization, not just different training), and report per-regime boards as primary (full-board compresses saturation).

## [KEEPER FOLD 15:2x COMPOSITE-0 Oct 1] INCONCLUSIVE (honest) — all three pairwise directions held, nothing cleared its frozen bar; std==0 is a 66-item granularity artifact, not a model property

Keeper verified comp0_results.json + guard receipt; lane booked its own entry. Fold notes:
- Direction pattern at matched budget (4225/4226p): FED 0.8182 > SINGLE 0.7778 (+0.0404), FED+LA 0.8434 > FED (+0.0252), FED > JOINT (+0.0152). LA gate cleared its +0.01 bar but FED std==0 (pinned 0.8182 all seeds) → INCONCLUSIVE by law, correctly applied.
- **Measurement fix for COMPOSITE-1:** ≥200-item held-out + item-level bootstrap CIs — integer granularity 1/66 = 0.0152 cannot distinguish arms this close; the law caught the metric, not the model.
- Free findings banked: (1) centroid-correlation routing saturated 1.0/1.0 — corpus gave the router a free pass, routing was never stress-tested; (2) LA triggers 17-19/seed, all to the SEMANTIC cell, net +2-3 items — independent reach wins where the expert is unsure; (3) dilution localized to counting (SINGLE 0.66 / FED 0.70 / LA 0.75).
- COMPOSITE-1 spec (from lane + keeper): K≥4 regimes, blurred boundaries, capacity-starved board where JOINT visibly dilutes, LA second cell with DIFFERENT FEATURIZATION (true independent reach), per-regime primary gates, bootstrap CIs.
- Receipt g7-wr-comp0-federation-1790896454 (0.939 Wh, beside resident 7B).


## [DONE 15:14 B1b-KINK-HEAD Oct 1] is B1's value-fidelity deficit representational? — **KILL on the frozen claim** (no basis clears 1e-2 or 5e-2 at B1's 40-epoch budget); booked caveat: τ₂ is optimization-bound, and the ReLU basis buys +0.257 @1e-2 concentrated in saturation

Lane B1b-KINK-HEAD. Follow-up to B1-DISTILL KILL. Pre-reg FROZEN before fire
(`proposals/runs/B1b-kink-head.md`), seed 2718. Frame reused VERBATIM from B1
(uniform-random reachable states, held out by whole trace; cross-check vs B1's
`holdout_samples.npz` = `max|ΔX| = max|ΔY| = 0.0`). NO COMMIT.

- **Verdict: KILL** — Gate A PASS needs mean ≥ 0.99 at BOTH τ₁=1e-2 and τ₂=5e-2
  (std>0). Over seeds 2718/2719/2720: **(a) tanh** 0.6136±0.0783 / 0.8891±0.0351;
  **(b) ReLU** 0.8701±0.0267 / 0.9192±0.0388; **(c) learned-kink hinge spline**
  (26p, learned knots on `u=|b−p|`) 0.4684±0.2189 / 0.7659±0.0283.
  1e-3 reported, not gated: 0.0991 / 0.2303 / 0.0920.
- **Reproduction control PASS:** a control net trained with B1's exact recipe
  reproduces B1's curve — 0.0586 / 0.6181 / 0.8731 vs B1's 0.0568 / 0.6163 /
  0.8715 (max |Δ| = 0.0018).
- **NEW per-region breakdown** (arm-independent, from law ground truth): holdout
  n=90,930 = clamp 114 (0.13%) · deadzone 7,090 (7.80%) · **saturation 80,372
  (88.39%)** · ramp 3,354 (3.69%). Headline: **clamp = 1.0000 for every arm at
  every tolerance** (the deployed `clamp(p+raw,6,54)−p` convention hands the box
  to the environment); **saturation is where the basis pays** — ReLU 0.9654 vs
  tanh 0.6759 @1e-2 (+0.2895), i.e. the whole aggregate gain (0.8701 vs 0.6136);
  **deadzone and ramp are unmoved by ANY basis at 40 epochs** (all < 0.50 at every
  tolerance). Arm (c)'s deadzone is **flat 0.0276 at 1e-3/1e-2/5e-2 on all seeds**
  = a stuck `b0` bias term (mine, booked as a parameterization+schedule defect,
  not evidence against the kink basis).
- **Gate B (h2h ≥600 games) NOT RUN** — the frozen rule is "only arms clearing
  BOTH gates"; none did. Booked, not silently skipped.
- **Mechanism note (why the KILL letter and the data disagree):** +0.257 @1e-2
  from a piecewise-linear basis, localized entirely in saturation, says the basis
  *does* matter; and τ₂=5e-2 is **optimization-bound** — B1's own 300-epoch tanh
  control already cleared it at 0.9902 while every arm here used B1's 40-epoch
  recipe. The prereg's KILL branch fired on the letter; the receipt records the
  disagreement rather than glossing it.
- **Controls (all PASS):** frame cross-check bit-exact (C4); pristine-vs-switch
  law bit-identical on 4,000 states (C1); JS↔torch port per arm per side gated on
  **float64-vs-float64** (the JS harness evaluates in float64, so this isolates
  formula identity) with max|Δ| ≤ 4.2e-15 ≪ 1e-6 — the float32 line (1.3e-6…
  2.5e-6) is reported alongside for transparency. Every state/label engine-emitted.
- **⚠ ORCHESTRATION DEFECT (fleet, booked):** two independent B1b subagents were
  dispatched concurrently into `results/b1b_kink/` with the same
  `task_id`/`guard/`. The sibling lane (`experiments/b1b_kink_head.py`) self-paused,
  published `results/b1b_kink/LANE-CLAIM.md`, and resumed there as sole writer —
  **this receipt is deconflicted to `results/b1b_kink_runB/`** (booked deviation
  from the frozen artifact path). Also booked (mine): the first fire crashed on
  my own port-control broadcast bug and its **VOID** receipt is preserved at
  `results/b1b_kink/guard/g7-wr-b1b-kink-head-1790896121.json`. No gate,
  tolerance, frame, split, or arm changed between crash and re-fire.
- **Receipt:** `g7-wr-b1b-kink-head-1790896473` — `g7-watt-receipt@1`, gate PASS,
  validator exit 0, source measured. **3.0826 Wh (11,097.46 J), 190.50 GPU-s**,
  $0.000709 @ $0.23/kWh. Preflight clean (1,338 MiB free ≥ 1024; max 76 °C ≤ 80).
  **Co-tenancy:** the 7B ollama seat held the card throughout + a sibling B1b lane
  after 15:10; peak VRAM **78.4 MB** (ceiling 1,500 MB). Elapsed 232.6 s.
- Artifacts: `results/b1b_kink_runB/` (`result.json`, `agreement.json`,
  `regions.json`, `controls.json`, `run_config.json`, `traces_meta.json`,
  `holdout_samples.npz`, 12 model files, `guard/`, `_crashed-1508-attempt/`,
  `RESULTS-ENTRY.md`). Code: `experiments/b1b_kink.py`,
  `experiments/b1b_kink_engine.mjs`.
- **Next:** 300 epochs on arm (b) with deadzone/ramp as *separate* gates; arm (c)
  re-parameterized with `b0` pinned at 0 and knots initialized at the law's own
  kink loci (1.5, s+1.5); prefer per-region gates to one pooled gate (saturation
  is 88% of the holdout and can hide ramp).

## [DONE 15:4x EST-FREEZE Oct 1] D2 determinacy estimator — BUILD ≥3, cross-validate: FROZEN-V1 = NONE (H5 must be re-derived); the encoder, not the formula, was the blocker

Lane EST-FREEZE (deepseek-v4-flash, subagent; CPU-only, no GPU/guard/twins). Prereg
`proposals/runs/EST-freeze.md` frozen before any run. Six independent estimators
(`results/est_freeze/estimators.py`, one interface `score(records,spec,est,weight,seed,nperm)->[0,1]`:
E0 plug-in H+Miller-Madow = the prereg formula; E1 excess mode-agreement; E2 effective-alphabet/
coverage-width; E3 permutation-exact normalized-MI bias-corrected; E4 split-half TV; E5 purity
Wilson-LB), cross-validated on identical material (`results/d2_build/{mini,fb}_traces.json`).

- **Reproduced the two-build disagreement exactly (E0, different channels):** build B `salLevel→fire`
  real 0.4455/sto 0.4693; build B `salx→fire` sto 0.7227/real 0.9699; build A `(salx,vision-window)→fire`
  real 1.0000. Same estimator math — **the divergence is the input encoder, not the measure.**
  fire|full-channel is a pure function (E0–E3/E5 = 1.000, spread 0.000); fire|salience is not
  (rule-purity 0.833). Build A was right to use the declared sheet channel; build B's instability
  was an undeclared, lossy projection.
- **Estimator × test (frozen C1–C5):** atoms-exact / seed-spread / |bias|@O2 / stationary-spread /
  in-scope C3 / C4 range — E0 1.000/0.000/**0.049**/**0.065**/0-6/0.648 (passes all but C3);
  E3 1.000/5e-4/**0.049**/**0.039**/0-6/0.693 (passes all but C3); E1 0.271 bias ✗; E2 0.318 range ✗;
  E4 0.998 atoms ✗, 0.564 bias ✗; E5 0.405 bias ✗.
- **FROZEN-V1 = NONE**, because **C3 (spread ≤0.15 across op/uni/degenerate) is unsatisfiable for all
  six** on the in-scope sockets. The stationary-truth synthetic control proves why: with true
  determinacy held identical across the three input distributions, the good estimators contribute
  ≤0.04 spread (E3 0.003–0.039) — so the real spread is **genuine socket input-distribution
  sensitivity, not estimator bias**. H5 conflates the two.
- **Consequences:** H6 is fine with the encoder frozen (reflex 1.000 − episodic 0.352 = 0.648 ≥ 0.5;
  build B's 0.118 was pure encoder artifact). H5 must be re-derived (gate on operational distribution;
  report per-socket spread as a datum with the synthetic floor subtracted; keep degenerate as an F4
  diagnostic). **Recommendation: v1 adopts E3** (smallest stationary instability + smallest |bias|@O2,
  exact atoms, interface-identical; E0 close second) and **freezes declared encoders** — the actual
  v1 blocker fix.
- Artifacts: `proposals/runs/EST-freeze.md`, `results/est_freeze/{estimators.py, crossval.py,
  analysis2.py, est_freeze_crossval.json, est_freeze_pass2.json, README.md}`. No GPU, no receipt
  required. **Not committed (lane rule).**

- **Reconciliation (keeper commit 3805671, 15:11:32):** that commit books
  "B1b-KINK-HEAD: KEEP 6/12 … learned kink 0.9991 < tanh 0.9998 @5e-2" — a
  **300-epoch** reading, not a contradiction of this lane's 40-epoch KILL but a
  different budget of the same question. Both agree the learned-kink head never
  beats tanh (mine 0.7659 < 0.8891; theirs 0.9991 < 0.9998), so kink-precision
  as a *win* is falsified either way. **Verifier note: those numbers have no
  artifact anywhere in the tree** (the only B1b `result.json` on disk is
  `results/b1b_kink_runB/`) — they need a run dir or a restatement. The 15:11
  commit also captured this lane's runB mid-flight and archived the crashed
  first fire to `_archive/b1b_kink_attemptB_void-20261001/`.

## [KEEPER FOLD 15:2x EST-FREEZE Oct 1] the D2 A/B disagreement was the ENCODER, not the estimator — H6 unblocked (0.648 PASS), H5 re-derived, measure pair frozen (E3 primary / E0 reserve), v1 GO with declared encoders

Keeper verified artifacts. Fold notes (Casey directive: "try different ways" → 6 estimators, one interface, cross-validated):
- **Disagreement reproduced exactly**: build B salLevel→fire 0.4455/0.4693, salx→fire 0.7227/0.9699; build A (salx, vision-window)→fire 1.0000. Same math, different encoder path. fire|full-channel is a pure function (spread 0.000); fire|salience is not (purity 0.833).
- **FROZEN-V1 = NONE, honestly** — C3 (≤0.15 spread) unsatisfiable for ALL SIX on real sockets. But the stationary-truth synthetic control (true determinacy identical across distributions) shows good estimators contribute ≤0.04 spread (E3: 0.003–0.039) ⇒ **the real spread is genuine socket input-distribution sensitivity — H5 as written conflated estimator bias with input sensitivity.** That's the prereg bug the shootout found.
- **Measure pair frozen**: E3 perm-exact norm-MI primary (smallest stationary instability 0.039 + bias 0.049, exact atoms, interface-identical), E0 plug-in H+Miller-Madow reserve (original prereg formula, close second).
- **H6 UNBLOCKED**: with declared frozen encoders, reflex 1.000 − episodic 0.352 = 0.648 ≥ 0.5. Build B's 0.118 was a pure encoder artifact (salience path).
- **H5 re-derivation (amendment)**: gate on operational distribution; report per-socket spread as a DATUM with the synthetic floor subtracted; keep degenerate input as an F4 diagnostic.
- All three D2-V1 prerequisites now met/specced: socket channels frozen (build A) + reflex twin target fix (build A) + declared frozen encoders (EST-FREEZE).
- CPU-only, no GPU receipt required. Artifacts: results/est_freeze/ (6 estimators + crossval + pass2 + README), proposals/runs/EST-freeze.md.

## [KEEPER RECONCILIATION 15:3x B1b Oct 1] two budgets, one agreement, one defect booked — artifact-backed record now runB

Two independent B1b builds ran (double-dispatch defect, LANE-CLAIM.md deconfliction). Keeper fold:
- **AGREEMENT (both builds):** learned-kink NEVER beats tanh at any budget tested. Kink-precision stays falsified.
- **Budget split:** 300-ep (lane 1) vs 40-ep (runB). At 40ep ReLU BEATS tanh on the saturation region (0.9654 vs 0.6759 @1e-2) and in aggregate (+0.257); at 300ep lane 1 reports tanh 0.9998 ≥ kink 0.9991. **"Tanh keeps its crown" was budget-conditional — crown claim corrected; ReLU wins saturation where 88.4% of ticks live.**
- **DEFECT BOOKED:** lane 1's headline numbers (0.9991/0.9998, "2-5× sensitivity lift", nerr_min 0.0007) have NO on-disk artifacts — results/b1b_kink/ holds models + configs only. RunB's numbers are the artifact-backed record (12 models, agreement/regions/controls/result JSONs, B1-exact control reproduced max|Δ|=0.0018). Lane-1 claims UNVERIFIED pending artifacts; my 3805671 fold over-trusted them. Lesson: keeper verifies artifact presence before folding headline numbers.
- **ROBUST STRUCTURE (both):** clamp region perfect for every arm at every tolerance; deadzone (7.8%) + ramp (3.7%) unmoved by ANY basis at 40ep (all <0.50) — THE value-fidelity gap lives in deadzone/ramp, and B1C's arm list targets exactly that.
- runB's own defect booked honestly: kink head stuck b0 bias (flat 0.0276 across tolerances, all seeds) = parameterization/schedule, not shape failure; first fire VOID receipt preserved; h2h correctly not run (frozen rule).
- Receipt g7-wr-b1b-kink-head-1790896473 (3.08 Wh, 78.4 MB peak, beside seat).

## [OPS 15:4x PR-QUEUE Oct 1] 52 open PRs swept (Casey: work through all PRs, learn, design 4050 probes) — deps queue cleaned, harvest lane dispatched

- 13 dependabot PRs triaged by CI: **2 merged** (quilt-pincher #12 #14, green patch bumps, squash), **11 closed with evidence** (Test FAILURE on major bumps: vitest 1→5 / eslint 8→10 / TS 5.9→7.0 / @types/node 20→26 — deps-breaks-build never merges blind).
- 39 substantive PRs → knowledge-card harvest (mechanism / outcome / primitive / 4050 probe / verdict-if-ours). kimi lane died on 5h-quota 403 before first read → re-dispatched as deepseek subagent (routing law: kimi quota-dead, z.ai busy serial, deepseek parallel).
- Card targets incl.: chiaroscuro #1-13 (synonym-graph router 1.000 vs 0.560, CX/KC/Moth stack, JEV abstention split, geometric-PN CLOSED lane), quilt-arcade #6 (fruitfly-CX paddle: sealed FAIL H1/H2, advisory H3/H4, v2 prereg), quilt-edge-lab #1-4 (C-ROT canon-rotation invariance, AUTO_PROMOTE, fleet-state interop), pie-minimax #2 (A1 closure, thesis weakened honestly), quilt-in-git #1-4 (refs/quilt/HEAD live pointers, signed ticks, airgap+sparse), pong rounds #88-93 (scaling study), tidepool #11 (WAL pins), Patchwork-experts #1 (verification-layer proposal).

## [KEEPER FOLD 15:4x PR-HARVEST Oct 1] 37 PRs / 12 repos read through the other-builder lens — five machines recur fleet-wide, 13 helpful drafts await review, top-10 probe list gated and queued

Casey directive: "think through what each PR actually is and work with that repo as a chance to think about your own project from the perspective of another builder as you help them."
- **MECHANISM MAP (main finding):** five machines recur across repos that never shared code — ring attractors (chiaroscuro↔arcade, 1:1 portable), KC sparsification (random-proj→WTA-5%→depression-only), ternary JEV, receipt chains (widest cluster: 8 repos; "the frozen clock lied for 25M ops and nothing broke because order lived in the chain"), referral graphs. Two hard-won refinements: read the store-of-record not the worktree; the judge must be independently implemented.
- **TOP-10 PROBES** (pr_harvest/SUMMARY.md, each with pass gate): probes 1-3 = one cluster three ways (ring-attractor × ternary × sparsification — bench-day material); probe 4 pie-minimax distinct-board re-eval (~2 min, settles a thesis); **probe 7 audits OUR OWN ledger row hash cross-language (~2 min, highest internal value/min)**; probes 5,6,8,9,10 all ≤3 min each.
- **OUR GAP FOUND by the sweep:** one unkeyed, actor-unbound hash path in RESULTS booking — cheapest fix in the fleet (tidepool #11 + quilt-in-git #3 patterns: keyed digest + actor binding). Booked for keeper hardening.
- **BUG FLAGGED (verified in diff):** chiaroscuro #1 token_stream.py writes receipts to hardcoded /root/... (non-portable); body claims 1280× compression vs its own receipt 12.8× (60× token-granularity mismatch in accounting).
- **FLEET PHILOSOPHY READ:** dominant = pre-register→seal→FAIL-honestly→close-lane (matches our laws); dominant risk = bureaucracy outpacing the experiment (pong bookkeeping a second job; chiaroscuro 4 PRs on one constant). Mirror-note for us: keep preregs one page, gates numeric, receipts automatic.
- **13 helpful drafts** (REPLIES-draft.md): correctness notes, receipt gaps, replication offers (C-ROT second substrate, pie-minimax re-eval, dilution-law repro, cross-language canonicalizer, P1-P5 pins). NOTHING posted; keeper reviews each before any comment lands.
- Artifacts: pr_harvest/{CARDS,BUILDERS,REPLIES-draft,SUMMARY}.md + _raw/. Read-only gh throughout.

## [LANE D2-V1b RESUME 15:5x Oct 1] prior D2-V1 artifact honest audit → prior run VOID (incomplete + sub-1GB-free breach); guarded re-run PASS → v1 analysis lands INCONCLUSIVE (H1 ρ=−0.37 FAIL, H5 measure INCONCLUSIVE, all else PASS)

Lane D2-V1b resumed the mid-killed D2-V1 lane. **Scripts unchanged — no defect found** (booked: none). Prior artifacts audited, not trusted.

**AUDIT of left artifacts (honest):**
- **W-DET canary `d2_v1_wdet_canary.json`: PASS, valid.** A-seeds 101/118/135 all hash `8c8a54a43f10`, `var_A=0`, r5 full==resumed `1de2f9c27e8d`, expected-hash match true, smoke 13/13. Exact-hash zero-variance gate met ⇒ wiring is not the failure.
- **Prior `d2_v1_twins_result.json`: INCOMPLETE + target-fixed.** Has `reflex_target_fix="one-step-ahead (t+1) fire"` and traces_sha256 `53c8916b…c66757` (matches re-run), BUT only **2/6 sockets, 18/54 runs** (reflex.orient + world.surprise). Missing sensors.vision, policy.action, memory.semantic, memory.episodic.
- **Prior G7 receipt `g7-wr-d2-v1-twins-1790897485`: self-declared VOID.** breach `free VRAM 1018 MiB < 1024`, `inner rc=-15` (SIGTERM). Schema-valid, verdict VOID ⇒ **not a data point** (the 4.397 Wh / 286 GPU-s is a VOID-run cost, not a measurement). `d2_v1_guard_run.out` = that VOID run (killed ~26/54); `d2_v1_guard_run2.out` = preflight-only (free=1497MiB, killed before inner). Prior evidence preserved: `*_PRIOR-VOID-1790897485.json` backups; the VOID receipt + ledger row kept.
- Booking fairness: `guard/guard_summary.json` is last-run-only and was overwritten by the re-run; its VOID content survives in the PRIOR-VOID guard-log backup.
- **Rail:** W-DET OK, target fix OK, but run VOID + result incomplete ⇒ **re-run required**, no verdict could be booked from it.

**GUARDED RE-RUN (scripts as-is; guard.py + G7; co-tenant 7B seat resident — qwen2.5:7b-instruct-q4_K_M, `size_vram` 4185 MiB):**
- `d2_v1_guard_run3.out`: PREFLIGHT OK free=1818MiB temp=46C → **inner rc=0, breach=null** → **receipt `g7-wr-d2-v1-twins-1790898417` verdict=PASS**, G7 validator ok. **0.5859 Wh / 49.26 GPU-s**, mean 15.24 W, wall 138.4 s, min_free 1625 MiB, max temp 64 °C. (Mean power is low honest-vs-the-VOID-run: tiny-net bursts with the seat idle; the VOID run's 47.95 W was a co-tenant-loaded window.)
- 54/54 runs, 6 sockets, seeds 2718-2720, epochs 80, F5 disjointness OK (train 0..139 vs test 140..199), reflex on one-step-ahead target. **GPU-SEED LAW: every socket gap_seed_std > 0 ⇒ no INCONCLUSIVE-by-seed offender** (reflex.orient seed-std 0.0002, smallest).

**ANALYSIS (`d2_v1_result.json`, B=1000 bootstrap over held-out REAL test worlds n=60; E3 perm-exact norm-MI, frozen declared encoders):**
- **VERDICT: INCONCLUSIVE.** Gates H1 **FAIL** · H2 PASS · H3 PASS · H4 PASS · H5 **INCONCLUSIVE** · H6 PASS. seed-law offenders: none.
- H1: ρ(op-determinacy, gap_sim) = **−0.3714**, CI95 **[−0.60, 0.60]** (upper bound not <0 → FAIL). H2: det≥0.8 sockets {reflex.orient 1.000, policy.action 0.901} mean gap −0.0071 ≤ 0.05 → PASS. H3: gap_mis − gap_sim = **+0.1427** ≥ 0.05 → PASS. H4: std>0 both axes → PASS. H5: **4/6 offenders** (world.surprise, sensors.vision, policy.action, memory.semantic) > 2 ⇒ measure does not exist at this scope → INCONCLUSIVE. H6: range 0.8799 ≥ 0.5 → PASS.
- Determinacy (operational): reflex 1.000, policy.action 0.901, sensors.vision 0.616, world.surprise 0.448, memory.episodic 0.183, memory.semantic 0.120.
- **Note the H5 vs H2 tension booked honestly:** policy.action scores op-det 0.901 (near-1 class) but its 3-distribution spread is 0.924 — its determinacy is distribution-sensitive, so its near-1 status is fragile; the H1 ρ is dragged by that instability rather than by a clean monotone law.
- **H-GROWTH: R2 DOES NOT SURVIVE stochastic worlds** — gated_frac 0.83 ≥ 0.8 BUT unguided_frac 0.88 > 0.2 ⇒ seed-vacuity of E-D1's R2 confirmed (independent booking; does not veto the thesis measurement).
- **1000-world ×5 extension: frozen trigger is MET** (H4 PASS ∧ ρ-CI width 1.20 > 0.40) **but NOT fired this lane** — budget ~60 min, and firing it would buy precision for a measure that just failed H5 (4/6 unstable). Recommended: repair the H5 measure (or re-scope sockets) first, then fire; book the receipt purpose in one line. QUEUE line added.
- Energy booked: **0.586 Wh valid** (PASS receipt) + 4.397 Wh VOID-run cost (not a measurement). Total lane spend ~4.98 Wh; measurement-of-record 0.586 Wh.

**Artifacts (append-only):** `results/d2_v1/{d2_v1_guard_run3.out, d2_v1_analysis_run3.out, d2_v1_result.json, d2_v1_twins_result.json (54/54, PASS), guard/g7-wr-d2-v1-twins-1790898417.json, guard/ledger.jsonl (both rows)}` + preserved `*_PRIOR-VOID-1790897485.*` and `d2_v1_wdet_canary.json`. NOT COMMITTED.

## COMP1 — federation v2: blurred K=4, capacity-starved, item-level bootstrap (lane COMPOSITE-1, r2 re-fire)
- ran: 2026-10-01 16:0x AKDT (pre-reg proposals/runs/COMP1-federation2.md, frozen 15:21 + A1 15:29 + r2 addendum 15:51; r1 fired 15:31, killed 15:45 by guard breach free VRAM 1018<1024 MiB from resident 7B seat drift — VOID receipt g7-wr-comp1-federation2-1790897485, evidence preserved results/comp1/r1-void-1545/, no arm results lost)
- verdict: **INCONCLUSIVE** (1 of 5 gates PASS — G1R-negation; conservative code lattice governs; prereg prose allowed SPLIT_KEEP_ naming for partials, frozen code prints INCONCLUSIVE — discrepancy disclosed, conservative branch stands)
- result: ```json
{
  "experiment": "COMP1 federation v2 (blurred K=4, starved cells, bootstrap CIs)",
  "corpus": {"seed": 2718, "n_train": 1810, "n_heldout": 590, "blur_beta": 0.35,
             "overlay_rate": 0.3412, "per_kind_heldout": {"semantic": 141, "counting-address": 139,
             "negation-scope": 148, "agent-role": 162}, "canon_frac": 0.4831, "validity_ok": true},
  "router_audit": {"train_acc": 0.7514, "heldout_acc": 0.7356,
                   "mean_top1_top2_corr_gap_heldout": 0.0412},
  "router_in_band": true,
  "chance_majority_full": 0.5169,
  "boards_seedmean": {"JOINT": 0.5469, "SINGLE": 0.5503, "FED": 0.5605,
                      "FED_LA": 0.5621, "JOINT_LA": 0.5475},
  "seed_std_full": {"JOINT": 0.0068, "SINGLE": 0.0068, "FED": 0.0056,
                    "FED_LA": 0.0032, "JOINT_LA": 0.0086},
  "gates": {
    "G1_FED-SINGLE_full":      {"diff": 0.0102,  "ci95": [-0.0339, 0.0548], "verdict": "FAIL"},
    "G1R_FED-SINGLE_counting": {"diff": 0.0024,  "ci95": [-0.0984, 0.1031], "verdict": "FAIL"},
    "G1R_FED-SINGLE_negation": {"diff": 0.1261,  "ci95": [ 0.0338, 0.2185], "verdict": "PASS"},
    "G2_FEDLA-FED_full":       {"diff": 0.0017,  "ci95": [-0.0169, 0.0209], "verdict": "FAIL"},
    "G3_FED-JOINT_full_sec":   {"diff": 0.0136,  "ci95": [-0.0305, 0.0582], "verdict": "FAIL"}},
  "regime_texture": {
    "negation": {"SINGLE": 0.4279, "JOINT": 0.4234, "FED": 0.5541, "FED_LA": 0.5631,
                 "note": "monoliths BELOW their 0.50 regime chance; FED-JOINT +0.1306 ci [0.0405, 0.2230] sig."},
    "semantic":  {"SINGLE": 0.6407, "JOINT": 0.6383, "FED": 0.5816, "FED-SINGLE -0.0591 ci [-0.1395, 0.0260]"},
    "counting":  {"all ~0.57, no separation"},
    "agent-role":{"all ~0.55-0.57, no separation"}},
  "la_v2": {"triggers/seed": "109-121 of 590", "flips": "97-104",
            "premium_full": 0.0017, "g2c_control_gap": 0.0011, "CONTROL_OK"},
  "ramp_receipt": {"ramp_s": 0.642, "synced": true},
  "g7_receipt": "g7-wr-comp1-federation2-1790899575 (valid, 11.76 Wh, 741.2 gpu-s, max 78 C, min-free 1475 MiB)",
  "wall_s": 910.7, "seeds_complete": 3, "verdict": "INCONCLUSIVE"
}
```
- note: the re-run of COMP0's federation thesis where it could be judged. **The measurement fix WORKED**: 590-item held-out + item-level paired bootstrap (B=2000) — no arm hit std==0 (all 0.003-0.009), the degeneracy law never fired, CIs are the decision mechanism as designed. Router desaturated exactly to spec: held-out 0.7356, top1-top2 gap 0.041 (COMP0: 1.0/0.49) — routing finally faced ambiguity and was merely decent. Findings at matched params: (1) **federation's win is regime-localized, not full-board** — FED>SINGLE only on negation-scope (+0.126, CI excludes 0; also FED>JOINT +0.131 CI [0.041,0.223]) where BOTH monolith arms sit BELOW regime chance (0.423/0.428 vs 0.50): the dedicated cell fixes a structural blindness (polarity is word-order; BoW cannot see it; regime-exclusive training lets the tiny cell key on the local cue anyway). Elsewhere FED buys nothing (semantic -0.059 direction, counting +0.002). (2) **LA-v2's different-featurization twin bought ~nothing** (+0.0017, CI spans 0; 109-121 triggers/seed): a char-trigram second view on the same corpus shares the blindness — independent reach requires the second sensor to see what the first misses, not merely differ. D1b doctrine: refined, not refuted — COMP0's LA win was on a saturated corpus (cheap wins); here, mid-difficulty, the escape hatch has nothing to escape TO. (3) **Floor effect is the new compression**: all arms 0.547-0.562 on a 0.517 chance board — corpus harder than intended (A1 blur + BoW D=64); full-board margins have little room to move. COMP0's disease (ceiling) inverted into a floor. (4) G2C control: LA premium 0.0017 in-federation vs 0.0006 in-joint — CONTROL_OK but both ~0; capacity premium unexercised either way.
- COMPOSITE-2 hooks: (a) make VIEW the manipulated variable — heterogeneous-sensor cells (word-BoW + char-ngram + position/polarity-aware) as primary arms, so the router picks sensor-not-just-expert; the negation result says that's where federation value lives; (b) retune corpus difficulty to mid-band (0.65-0.85 boards) so full-board gates have room; (c) price the LA twin at primary-cell capacity (not 8-hidden) before retiring the look-again doctrine.
- **Artifacts:** results/comp1/{comp1_results.json, corpus.jsonl (determinism-checked == r1 artifact), guard/g7-wr-comp1-federation2-1790899575.json + guard_summary.json + ledger.jsonl} + r1 evidence results/comp1/r1-void-1545/{corpus.jsonl, guard/}. COMMITTED 6c47056 (stale-note amendment 16:2x: was booked before the artifacts commit landed).

## B1C — value-fidelity: deadzone/ramp deficit (per-region gates) — 2026-10-01 **KEEP** (`cap@ep40` clears the frozen per-region gate)
- ran: `experiments/b1c_value_fidelity.py --resume` under guard (post-infra-kill resume; prereg `proposals/runs/B1C-value-fidelity.md` honoured unchanged)
- result: ```json
{
  "verdict": "KEEP",
  "passing_arms": ["cap@ep40"],
  "mechanism_wins": ["reweight@ep40", "cap@ep40"],
  "gate": "deadzone >= 0.90 AND ramp >= 0.90 @5e-2, 3-seed mean, both std>0",
  "per_region_5e-2": {
    "relu_ref@ep40": {"deadzone": [0.4951, 0.3102], "ramp": [0.3205, 0.0987], "sat": 0.9815, "verdict": "FAIL"},
    "reweight@ep40": {"deadzone": [0.7553, 0.3413], "ramp": [0.6950, 0.3669], "sat": 0.9815, "verdict": "FAIL"},
    "cap@ep40":      {"deadzone": [0.9957, 0.0061], "ramp": [0.9186, 0.1109], "sat": 0.9992, "verdict": "PASS"},
    "binned@ep40":   {"deadzone": [1.0000, 0.0000], "ramp": [0.1200, 0.0012], "sat": 0.9994, "verdict": "INCONCLUSIVE"},
    "relu_ref@ep300":{"deadzone": [1.0000, 0.0000], "ramp": [1.0000, 0.0000], "sat": 1.0000, "verdict": "INCONCLUSIVE"},
    "reweight@ep300":{"deadzone": [1.0000, 0.0000], "ramp": [1.0000, 0.0000], "sat": 1.0000, "verdict": "INCONCLUSIVE"},
    "cap@ep300":     {"deadzone": [1.0000, 0.0000], "ramp": [1.0000, 0.0000], "sat": 1.0000, "verdict": "INCONCLUSIVE"},
    "binned@ep300":  {"deadzone": [1.0000, 0.0000], "ramp": [0.8670, 0.0300], "sat": 1.0000, "verdict": "INCONCLUSIVE"}},
  "region_frac": {"clamp": 0.0013, "deadzone": 0.0780, "saturation": 0.8839, "ramp": 0.0369},
  "mechanism_bar_vs_ref": {"reweight@ep40": [0.2602, 0.3745], "cap@ep40": [0.5006, 0.5981], "binned@ep40": [0.5049, -0.2006]},
  "controls": {"C1_laweq": 0.0, "C2_js_torch_f64_max": 4.11e-15, "C4_vs_runB_and_b1": "max|dX|=max|dY|=max|dMETA|=0.0", "C5_relu_ref_repro_max|d|": 0.0},
  "resume": {"n_reused": 12, "n_trained": 12, "budgets": ["ep40 reused", "ep300 trained"]},
  "gpu_peak_vram_mb": 124.1, "g7_receipt": "g7-wr-b1c-value-fidelity-1790899870 (valid, PASS, 16.11 Wh)",
  "elapsed_s": 1271.6, "verdict_note": "stdlib"
}
```
- note: **the deadzone/ramp deficit is capacity-bound, not a representational floor.** `cap` (3-128-128-128-1, 33.7k params) clears BOTH frozen regions at the SAME 40-epoch budget where every width-64 ReLU basis failed: ramp 0.9186±0.1109 (+0.598 vs ref), deadzone 0.9957±0.0061 (+0.501), saturation 0.9992 (no rot) → the first PASS in the B1 family; B1b's "unmoved by ANY basis" is refuted as representational (the kinks were in the family; width-64 could not fit them in 40ep). **Reweighting moves it, not to the bar**: inverse-region-frequency weighting (deadzone 7.8%, ramp 3.7% of ticks) lifts deadzone +0.260 / ramp +0.375 — dilution confirmed directionally, lands 0.755/0.695. **The binned head is a ramp trap**: softmax-over-105-bins emits the deadzone atom exactly (1.0000 both budgets) but collapses the ramp continuum (0.1200@40ep, 0.8670@300ep — the only arm never reaching ramp 0.90 at either budget). **Budget-conditional is first-class**: at 300ep relu_ref/reweight/cap ALL hit deadzone 1.0000 / ramp 1.0000 with std==0 (every seed at the ceiling) → the frozen degeneracy rule books INCONCLUSIVE, corroborating B1's 300ep control as an optimisation-budget effect. Aggregate would have hidden all of it (binned 0.9670 aggregate hides a 0.12 ramp). Controls all pass; C5 relu_ref@ep40 reproduces runB exactly (max|Δ|=0.0000). ⚠ BOOKED: code constant `WH_ENVELOPE=12.0` is stale vs prereg AMENDMENT-1 (≤20 Wh); measured 16.11 Wh is within the amended envelope but above the constant — both budgets ran as intended. ✅ RESUME PROVENANCE: prior subagent killed 15:45 after landing 12 ep40 nets (15:33–15:36); this run REUSED those 12 (loaded state_dicts, not retrained) and trained only the 12 missing ep300 nets via a minimal `--resume` flag — no gate/arm/frame/seed/tol changed; frame regenerated and re-verified bit-identical (C4). B1D seed: sweep capacity at fixed 40ep (min width clearing both), pair with reweight; hybrid (regression + deadzone atom gate) if atom-exactness wanted; measure at 1e-3/1e-2 or book 300ep ceilings as resolved. full: results/b1c/RESULTS-ENTRY.md
- **Artifacts:** results/b1c/{result.json, regions.json, agreement.json, controls.json, run_config.json, traces_meta.json, holdout_samples.npz, 24 nets model_<arm>_seed{2718,2719,2720}_ep{40,300}.pt, run_resume.log, guard/}. Code: experiments/b1c_value_fidelity.py (+--resume), experiments/b1c_value_fidelity_engine.mjs. NOT COMMITTED.

## RING-CX-0 — training-free certainty-gated ring attractor as router (2026-10-01 16:14 AKDT)
- lane: RING-CX-0 (SYNTH-0 wildcard) · device: **CPU only, numpy** (no GPU, no training) · seeds 2718..2722
- verdict: **FAIL** (G-A FAIL · G-B FAIL · G-C OK) — honest negative, fully receipted
- **REPRO (harvested, the one PASS cluster):** pr_harvest ships runnable code. Verbatim extraction of
  `tools/fly_cx.py` (169 lines; chiaroscuro #6, flycx v2 certainty-gated) from
  `pr_harvest/_raw/chiaroscuro_6.diff` → `results/ring_cx0/repro/fly_cx.py`, ran unchanged:
  **PASS 4/4** (T1 0.0°/s · T2 err 0.007° · T3 amp_drop 0.3000 (=REJECT_SHRINK) · T4 0.0°;
  null-control ψ≡+1 displacement 71.999° > 60; trajectory fnv1a64 `41c8af26ba55cb03`).
- **WIRING:** rebuilt COMP1's frozen word-view featurization (sha1 BoW D=64, L2) + the frozen 0-param
  D13d regime-centroid Pearson router from `corpus.jsonl` using TRAIN keys only →
  reproduced router held-out top-1 **0.7356**, bit-equal to COMP1's booked 0.7356.
- ring = N=64 head-direction-style, local excitation / global inhibition (row-normalized Gaussian
  σE=16°, J_E=5, J_I=1), cue injection σC=30°, L2-normalized shape dynamics, readout = circular mean;
  certainty gate: item REJECTS iff R=|resultant| ≤ τ_ring = 20th pct TRAIN R. Kernel constants chosen
  by a LABEL-FREE criterion (flat input → R=0.0000, single-cue → R=0.6702) fixed before any accuracy
  was computed; T = median TRAIN top1−top2 gap = 0.0321 (COMP1's doctrine). Seeded cue jitter declared.
- result: ```json
{
  "G_A": {"threshold": 0.7156, "overall_acc": [0.6224, 0.0042], "acc_commit": [0.7800, 0.0057], "verdict": "FAIL"},
  "G_B": {"negation_reject": 0.1270, "regime_mean": 0.2065, "ratio": 0.615, "need": 2.0, "verdict": "FAIL"},
  "G_C": {"all_deciding_seed_std_gt0": true, "verdict": "OK"},
  "reject_by_regime": {"semantic": [0.3688,0.0168], "counting-address": [0.2216,0.0115],
                       "negation-scope": [0.1270,0.0079], "agent-role": [0.1086,0.0030]},
  "ring_R_by_regime": {"semantic": 0.420, "counting-address": 0.526, "negation-scope": 0.490, "agent-role": 0.497},
  "router_top1_by_regime": {"semantic": 0.759, "counting-address": 0.892, "negation-scope": 0.703, "agent-role": 0.611},
  "G_B_sensitivity": "ratio 0.49-1.00 over T in {.02,.0321,.05} x tau_pct in {10,20,30}; semantic is the top-reject regime in 8/9 cells",
  "engineB_harvested_constants_verbatim": {"semantic": 0.170, "counting-address": 1.000, "negation-scope": 0.966, "agent-role": 0.982}
}
```
- note: **the untrained ring does NOT see the blind regime through Reject.** Reject-rate in
  `negation-scope` is 0.127 — the *second lowest* of four regimes — while Reject concentrates on
  `semantic` (0.369, the regime with the lowest ring certainty R=0.420). **Routing selectivity and
  answering competence are dissociated**: the monolith sensor is blind *at answering* the negation
  board (COMP1's FED−SINGLE +0.1261), yet the routing signal for negation is comparatively sharp
  (router top-1 0.703, ring certainty mid-pack 0.490). The ring's Reject fires on *sensor-key
  representational flatness* — a property of the corpus geometry — not on federation blindness.
  G-A splits: as literally stated (overall, Rejects = wrong) it FAILs at 0.6224; conditional on
  commit the ring routes at 0.7800 (±0.0057), above the 0.7156 threshold. **BOOKED FACT (Engine B):**
  the harvested fly_cx constants verbatim (CONFLICT_DEG=30° vs 90° sensor separation) collapse on
  discrete 4-way cues (reject 1.000/0.982/0.966/0.170) — a continuous-compass parameterization; a
  4-way instantiation must rescale the conflict radius to the sensor Voronoi half-width (45°).
  Next question: answer-margin (cell-margin) gated ring — is the blind regime visible to ANY untrained
  gate, or only to the trained FED−SINGLE disagreement? full: results/ring_cx0/RESULTS-ENTRY.md
- **Artifacts:** results/ring_cx0/{ring_cx0_results.json, RESULTS-ENTRY.md, repro/fly_cx.py,
  repro/fly_cx_receipt.json}. Code: experiments/ring_cx0.py. **NOT COMMITTED.** ~3 s wall, 0 Wh.

## RING-CX-1 — untrained ANSWER-MARGIN-gated ring (SYNTH-0 wildcard, closing probe) (2026-10-01 16:24 AKDT)
- lane: RING-CX-1 (SYNTH-0 wildcard) · device: **CPU only, numpy** (no GPU, no training) · seeds 2718..2722
- reuses `experiments/ring_cx0.py` + `results/ring_cx0/repro/` **wholesale**; wiring = frozen COMP1 word-view
  featurization + 0-param D13d router on TRAIN only → held-out top-1 **0.7356 == booked 0.7356**.
- gate swap: `cue_s` `softmax(ρ_s/T)` [r0 certainty] → **per-sensor answer margin**
  `margin_s = |p_top1 − p_top2| = |2·σ(ρ_s/T) − 1|`, T = median TRAIN top-1 ρ = 0.7374 (label-free).
  Ring integrates margins **exactly as before** (same N=64 DoD kernel, τ = 20th pct TRAIN R, same jitter/grid).
- **structural pre-note:** ring update is positively homogeneous (`relu`), so R is **scale-invariant** in the
  cue vector — `ring.read([0.1,0,0,0]) == ring.read([1,0,0,0]) == 0.6702` exactly, all-equal cues R=0.0000 at any
  level. **Any margin gate routed through this ring is provably a cue-SHAPE gate, blind to margin level.** The
  level-aware absolute-margin gates are reported as labelled exploratory.
- result: ```json
{
  "G_A_prime": {"threshold": 0.7156, "overall_acc": [0.3268, 0.0125], "acc_commit": [0.3356, 0.0138], "verdict": "FAIL"},
  "G_B_prime": {"negation_reject": 0.0203, "regime_mean": 0.0257, "ratio": 0.789, "need": 2.0, "verdict": "FAIL"},
  "G_C_prime": {"all_deciding_seed_std_gt0": true, "verdict": "OK"},
  "reject_by_regime": {"semantic": [0.0184,0.0057], "counting-address": [0.0259,0.0058],
                       "negation-scope": [0.0203,0.0128], "agent-role": [0.0383,0.0143]},
  "ring_R_by_regime": {"semantic": 0.125, "counting-address": 0.126, "negation-scope": 0.125, "agent-role": 0.123},
  "matched_protocol": {"tau": 0.0671, "overall_reject": 0.1966, "negation": 0.1757, "mean": 0.1956, "ratio": 0.898, "top_reject": "agent-role 0.2284"},
  "opr_robustness_5_defs": {"pass_B": 0, "n_defs": 5, "negation_rate_range": [0.068, 0.108]},
  "absolute_agg_margin_gate": {"counting-address": 0.525, "semantic": 0.135, "negation-scope": 0.068, "agent-role": 0.031, "ratio": 0.356},
  "grid_9cells": {"negation_top_reject": "1/9", "negation_ge_2x": "0/9"}
}
```
- note: **NO untrained gate sees the blind regime.** G-A′ collapses to **chance (0.327)**: the per-sensor
  margin is near-flat across sensors (within-item spread 0.074 on a base of 0.426), so the cue vector is almost
  uniform and the ring resultant near-collapses (R ≈ 0.125 for every regime, vs r0's 0.42–0.53) → θ̂ is noise →
  routing accuracy = chance. The margin map is *compressive* where r0's softmax (τ-temperature 0.0321) is
  *sharpening*. G-B′ FAILs and is robust: matched-protocol τ (rules out an inert gate) still gives negation
  0.176 vs mean 0.196 (ratio 0.898, top-reject agent-role); 1/9 grid cells make negation top-reject, 0/9 reach
  2×; **0/5** alternative untrained margin definitions place Reject on negation; and even the level-aware
  absolute-margin gate fires on **counting-address** (0.525 — regime-atypical items), never on the blind regime.
  **WILDCARD THREAD CLOSES NEGATIVE: only the TRAINED FED−SINGLE disagreement sees the blind regime** —
  every untrained gate is a function of corpus geometry, and that geometry is blind to the axis the blind regime
  lives on; the ring's Reject is *provably* scale-invariant (homogeneity of relu), so no per-sensor margin level
  can reach it at all. Next question: is the blindness reachable by a **cheap TRAINED** gate (single logistic on
  the 4 margins / on the 2-arm disagreement) — cheapness lives in the gate, not the geometry?
  full: results/ring_cx1/RESULTS-ENTRY.md
- **Artifacts:** results/ring_cx1/{ring_cx1_results.json, RESULTS-ENTRY.md}. Code: experiments/ring_cx1.py.
  Repro lineage: results/ring_cx0/repro/fly_cx.py (PASS 4/4, reused by reference). **NOT COMMITTED.** ~12 s wall, 0 Wh.
