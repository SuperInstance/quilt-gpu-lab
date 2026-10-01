# PX2 — patchwork-3x3: the gardener's first falsifiable wiring test

**Status: FROZEN 2026-09-30 16:1x AKDT, before any build. Commit-first.**
Parents: PX1 (ceiling ladder, commit 7973dbb), PX0 ideation round 1 (results/px0_ideation/round1.md).
Terrain donor: SuperInstance/pie-minimax @ main (read-only clone), 180,361 our-turn states,
FNV-1a-64 `0x75f652bc1d8464b8`.

## Objective

Test the patchwork-experts thesis on ground-truth-able terrain: can a GLM-5.3 gardener
wiring shallow cells beat the best shallow single model (d3 tree, 0.481) — **with receipts
that causally earn their moves**?

## Fixed eval

- PX1 seed-0 80/20 split. Test split: 36,073 states. Quick-eval subset: 200 frozen test
  states (gardener-in-the-loop only; never trained on).
- Metrics: top1-in-optimal + set-recall, always together. 3 eval seeds; std==0 →
  INCONCLUSIVE.

## Baselines (PX1, frozen)

linear 0.198 · d3 **0.481** · d4 0.602 · d6 **0.748** · deep 0.999.
The patchwork must beat **d6** to justify existing (cheap-baseline control).

## Cells (launch roster — train-split-only)

- depth-k trees (k ≤ 6), trained
- tev1:0.8b, qwen3.5:0.8b, qwen2.5:0.5b (ollama local)
- format gate (structural), pinch-to-known-answer, majority-vote combiner
- embeddinggemma-300m (DeepInfra) — NN-gate against train states

**Gardener:** GLM-5.3 subagent, ≤50 moves. Move = JSON receipt
`{move_type: wire|rearrange|create|retire, targets, rationale, predicted_effect_direction}`.

**Standing panel (Casey's 16:04 picks):**
- ByteDance/Seed-2.0-mini — candidate-cell referee (cheap semantic grade pre-wiring)
- NousResearch/Hermes-3-Llama-3.1-405B — adversarial receipt auditor (CoT vs move diffs)
- tencent/Hy3 — wildcard designer (off-canvas cell proposals per session)

## Pre-registered branches

| Result | Ruling |
|---|---|
| quick-eval ≥ 2× d3 (≥ 0.96) within 50 moves | **WIN**: gardener wiring ≈ recovers deep-tree ceiling from shallow cells. Then audit receipts: fraction of moves whose predicted_effect_direction matches measured direction must beat 0.5, else the gardener got lucky rather than understood. |
| 1.3–2× d3 | **PARTIAL**: catalog which cell types earned keep; analyze move types. |
| < 1.3× after 200 moves | **KILL**: gardener layer adds nothing over fitting the best single tree on ground-truth-able tasks. Thesis retreats to fuzzy/semantic terrain only. |

## Controls (one per ideation lane + house rules)

1. **H3 shadow randomizer:** 5% of gardener moves silently replaced by no-op. If
   accepted-vs-rejected receipt quality is indistinguishable, the gardener is post-hoc
   rationalizing → WIN/PARTIAL rulings voided; harness finding booked instead.
2. **Hermes drift control:** fixed 1k train states re-scored every 10 moves; cell output
   drift > ε must appear in receipts, else rot.
3. **Seed-mini sanity cell:** cataloged trivial cell (center-if-empty-else-block) verified
   against 5 known ground-truth positions before every wiring session; failure = harness
   broken, no numbers that day.
4. **Cheap-baseline control (doc rule 5):** final patchwork must beat a d6 tree fit on
   identical train states.
5. Provenance: device string per run; seeds recorded; no test leakage.

## Smoke gate (before gardener ever runs)

Cells alone, no gardener: majority-vote(d3,d4) + format gate must beat d3 alone on the
quick-eval. If plain composition can't beat d3, fix the harness before crediting any
gardener.
