# C5 — paired-condition action probe (frozen)

**Status:** pre-registered, frozen before fire. Push-before-fire: this file must be committed+pushed before the farm fires `c5_paired_action.py`.
**Date:** 2026-09-30 22:2x AKDT. Lane: Casey "go" — feed the farm. Builds on C4 (identity LOOCV 1.000, temporal control strongly structured).

## Question

Does the Cosmos3-Edge embedding encode the ACTION/direction dimension — forward vs reversed playback — as a factor separable from identity? C4 showed the embedding carries rich identity + temporal structure; C5 crosses the two with a paired-condition design on the same sources.

## Design (deterministic, no rerolls)

- Sources: `example_action_id_av_0_input.mp4`, `example_action_id_av_1_input.mp4` (the c3 REAL_SOURCES).
- 4 frame-aligned windows per source (`frame_starts` + `pick_frames`, label "c5/av%d").
- 2 conditions per window: **forward** (c3 geometry verbatim) and **reversed** (same argv + `reverse` in the filter chain — same 16 frames, opposite order; 256×256×16f@10fps rgb24).
- 16 clips total. Identity balanced across conditions by construction (4 av0 + 4 av1 per condition).
- Model: skip-tower NF4 recipe, fail-loud visual bf16/Parameter receipt (c4's block, verbatim discipline). Embeddings checkpointed before scoring.

## Frozen hypotheses & bands

- **H1 (action in latent):** fwd-vs-rev LOOCV nearest-centroid AUC ≥ **0.75** → KEEP; ≤ 0.55 → CONTENT_ONLY (KILL); between → WEAK_UNRESOLVED.
- **H2 (beyond endpoints):** pixel-endpoint baseline = frame0+frame15 downsampled 16×16 gray, flattened, nearest-centroid LOOCV on the same 16 clips. KEEP iff emb AUC ≥ pixel AUC + **0.05**. (Endpoints carry direction info because reversal swaps their roles — a fair cheap-features control, not a strawman.)
- **H3 (identity anchor):** av0-vs-av1 AUC within fwd-only clips ≥ **0.90** → replicates C4's identity result under the C5 clip set; below → book honestly (clip-set sensitivity).
- **Harness control:** label-shuffle (seed 11) action AUC must land in **[0.35, 0.65]**, else verdict = HARNESS_INVALID and NO hypothesis verdicts are booked.
- Informational (not gated): identity AUC on rev clips; cross-condition identity (train fwd → test rev).

## Honest predictions (pre-data)

H1 KEEP ~0.85 (C4 says temporal structure is strong in this embedding). H2 genuinely uncertain — endpoints are weak for continuous motion direction, but av sources may have distinctive start/end states. H3 KEEP (C4 replicated twice already).

## Receipts

results/c5_paired_action.json (schema c5-paired-action/1): config, argv per clip, harness receipt, all AUCs + verdicts, peak VRAM, checkpoint path. Booked in RESULTS.md after the run, verdicts as they land.
