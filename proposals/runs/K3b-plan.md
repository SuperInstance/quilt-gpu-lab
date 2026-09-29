# K3b — plan (worker contract, written before build)
*Pre-registered after K3's INVALID_HARNESS. Same frozen question as K3 — WHERE
does diff-target pay — with ONE repair: replicate the mix draw. Nothing else moves.*

## Why K3b exists (the K3 post-mortem, one cell)
K3 (proposals/runs/K3-plan.md, commits ab8ec08+d749565) ran all 20 cells; 18 beat
the persistence floor (2.879 on the fixed 50/50 mixed val). The r=0.25 seed-42
cell failed it for BOTH arms (state 3.111 / diff 3.079), while seed 1337 at the
same r passed comfortably (1.572 / 1.635). That is deterministic mix-DRAW
variance (the seeded coin chooses which training windows come from which domain),
not a domain effect — but K3's frozen gate says any arm failing persistence →
INVALID_HARNESS, and no post-hoc loosening is allowed. Verdict stood. K3b is the
pre-registered replication that makes the estimator able to decide.

## Design (frozen; deltas from K3 marked)
- Same two frozen caches, same fixed 50/50 val interleave, same TinyPredictor,
  same STEPS=1200/BATCH/LR/windowing, same ratios r ∈ {1.00, 0.75, 0.50, 0.25, 0.00}.
- **DELTA 1 — draws:** seeds (42, 1337, **7**) → 3 deterministic mix draws per
  cell (30 cells, ~8 min GPU). Seed 7 chosen now, before any run.
- **DELTA 2 — health gate:** persistence floor applies to the per-cell MEAN over
  the 3 draws (both arms, every r). Floor value itself unchanged: it is still the
  persistence MSE of the same fixed val set. Per-draw grid is recorded so draw
  variance stays visible; no draw is discarded.
- **DELTA 3 — rel_win(r):** mean over the 3 draws of (mse_state − mse_diff)/mse_state,
  per r. Primary metric only; readers stay skipped (K3's rationale unchanged).

## Gates (frozen; textually identical to K3 otherwise)
- **BOUNDARY_MAPPED:** mean rel_win(r) decreasing in r (Spearman < 0) AND spread ≥ 0.05;
  r* = interpolated zero-crossing, booked.
- **NO_BOUNDARY:** spread < 0.05 or non-monotone noise.
- **INVALID_HARNESS:** any per-cell mean arm MSE ≥ persistence, non-finite losses,
  cache load failure.
- K3's numbers are NOT pooled into K3b's verdict. K3b stands alone.
- No post-hoc loosening. Replication of an r* booking is K4's job.

## Honest scope note
K3's per-r rel_win (unbooked, informational) was non-monotone with the r=1.0 point
negative (−0.041) and r=0.0 positive (+0.039) — inverted vs the K1/K2 bookends
(diff won on pure-synth val in K1, lost on pure-lavfi val in K2). The mixed-val
testbed changed the question, not just the noise. If K3b books a boundary, its r*
is a property of THIS 50/50 testbed; per-domain val splits are K4, not K3b.
