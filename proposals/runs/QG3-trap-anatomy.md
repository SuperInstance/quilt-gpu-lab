# QG3 — Landscape-trap anatomy: budget sensitivity + champion-basin clustering (pre-registered)

Date: 2026-09-30 03:5x (night conductor, GPU slice; rotation honored — last slice SCOUT #1 non-GPU)
Status: PRE-REGISTERED before firing. Commit+push precedes the run.

## Question
QG2 established ~42% of streams are landscape-trapped (structural desert, exact==shot). WHY?
Two sub-questions, one lane instrumented:
1. **Budget**: do traps open with budget? Compare crossing fraction at baseline (W=6, gens=12)
   vs deeper budget (W=8, gens=24). If trapped-at-W6 streams mostly cross at W8/g24, traps are
   budget-artifacts; if they stay stuck, the landscape itself fences them.
2. **Basin structure**: do stuck champions cluster? Edit-distance clustering of final champion
   genomes of stuck streams. Few large basins => the desert has structure (routable-around,
   feeds QO2 oracle-guided resampling); diffuse => stuck streams are individually lost.

## Design (single lane, both arms, exact arm only — shot==exact per QG2, cheaper)
- Same mutation/skeleton machinery as `experiments/qg2_scale_lane.py` (W now a parameter).
- Arm A (baseline): W=6, gens=12, S=1024, bar=0.45, arm="exact".
- Arm B (deep): W=8, gens=24, S=1024, same bar, same skeleton [[h,0],[cx,0,1]].
- Fresh global mutation rng (seed 1234 machinery as QG2) — declared: each arm gets its own
  default_rng(seed = 1234 for A, 4321 for B) so arms are not the same mutation stream.
- Record per stream: crossed, crossed_gen, final_v, final champion gate-id sequence (trimmed to len).
- Basins: Levenshtein distance over gate-id sequences of STUCK champions (final_v < 0.45 at arm end).
  Clustering = greedy single-linkage at threshold d<=2 (declared a priori: a 6-gate genome within
  edit distance 2 of another is the same basin). Report: n_stuck, n_basins, top-basin share,
  largest-basin mean intra-distance, plus null reference: same statistic on 1024 uniformly random
  genomes of matched length distribution (diffuseness baseline).

## Gates
- **G1 (budget gate)**: crossed_frac(B) − crossed_frac(A) with exact binomial CIs (n=1024 each).
  PASS-for-budget-open if Δ lower bound > +0.05. If CIs overlap heavily => traps are NOT budget-
  artifacts (stronger structural claim).
- **G2 (basin gate)**: stuck-champion top-basin share vs null top-basin share (matched-N null).
  Structure declared if top-basin share > 3× null and n_basins < n_stuck/4.
- **G3 (anchor)**: ANCHOR-VEC max|diff| < 1e-9 vs qcell_sim.evaluate, else abort.

## Predictions (registered before firing)
- P1: Δ crossed_frac < +0.05 — traps do NOT open with budget (structural fence, consistent with
  QG2 desert-at-birth + exp018 desert-extends-to-cloud).
- P2: stuck champions concentrate into few basins (top basin ≥ 10% of stuck, n_basins << n_stuck).

## Bookkeeping
- Fail-loud: any crash => book the crash honestly, no silent fixes mid-run except mechanical
  (device/shape) errors, which get amended in place with a note.
- Artifacts: experiments/qg3_trap_anatomy.py, results/qg3_trap_anatomy/{results.json, run.log}.
- STOP: one shot, no re-roll; negative results booked as-is.

## AMENDMENT 1 (2026-09-30 03:5x, BEFORE firing disentangle arms)
Initial arms A/B changed W and gens together (confound). Run is 5s/arm — add arms C (W=6,
gens=24, seed=2468) and D (W=8, gens=12, seed=1357), S=1024, same gates. Question: is the
budget-open effect driven by generations (C≈B) or width (D≈B)? Prediction: generations drive
it (C≈B, D≈A) — the trap is a slow-climb fence, not a width fence.
