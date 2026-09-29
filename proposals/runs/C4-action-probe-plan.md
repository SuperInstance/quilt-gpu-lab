# C4 — Action-separability probe (frozen pre-registration)

Date: 2026-09-29 13:25 AKDT. Pushed BEFORE the run (push-often doctrine).
Model lane: parent-authored (lanes rate-limited; parent is the builder of record).

## Question

Do Cosmos3-Edge latents carry action identity BEYOND content? C3 answered the
easy half (synth/real separates at AUC 1.0 — near-tautological). C4 tests the
non-trivial half: is cross-video separation (av_0 vs av_1, two different action
ids) larger than within-video temporal drift?

## Sources & geometry

- The two snapshot action examples: `assets/example_action_id_av_0_input.mp4`,
  `av_1` (different action ids). Same snapshot as C2/C3 (sha256 recorded).
- 8 clips per video, even t0 grid (`real_t0s`), 16 frames, 256x256, fps=10,
  rawvideo rgb24 — identical geometry + pipeline to C3 (reuse `real_clip`).
- Extraction: the PROVEN skip-tower loader (NF4 LM, bf16 tower+projector,
  `llm_int8_skip_modules=["visual","projector","model.visual","model.projector"]`),
  fail-loud dtype receipt (bf16 AND Parameter), layer-B post-projector
  mean-pooled 2048-d (`emb_tokens_f16`).

## Sets (no RNG anywhere; deterministic t0 grid)

- S_cross: 16 clips, label = video (av_0=0, av_1=1).
- S_time: 16 clips, label = half (early 4 windows=0, late 4=1, pooled over both videos).

## Metric

LOOCV nearest-centroid AUC per set (leave-one-out, centroid from the other 15,
`auc_exact` rank AUC). n=16 → coarse granularity (1/64); acceptable for a probe;
recorded, not smoothed.

## Frozen gate (exact numbers)

diff = AUC(S_cross) − AUC(S_time)

- diff ≥ 0.10 → ACTION_SEPARABLE
- diff ≤ 0.00 → CONTENT_DOMINANT
- else → WEAK_UNRESOLVED

## Confound honesty (sealed before the run)

av_0 vs av_1 differ in action AND content. S_time controls temporal drift only.
A high diff is NECESSARY, not sufficient, for action identity in latents: it
shows cross-video structure exceeds within-video drift. Booked as such — no
stronger claim.

## Fail-loud + guards

- dtype receipt must be bf16/Parameter else INVALID_HARNESS.
- OOM auto-halve batch (4→2→1, fail loud at 1).
- VRAM guard preflight (free ≥1024 MiB, temp ≤80°C).
- All subprocess list-form. Output: results/c4_action_probe.json
  (aucs, per-clip held-out scores, verdict, versions, receipts).
