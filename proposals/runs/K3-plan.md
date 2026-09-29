# K3 — plan (worker contract, written before build)
*Pre-registered after K2's KILL. The question changed: not "does diff-target win"
(K1: yes-synth / K2: no-lavfi) but WHERE it wins. The boundary, not the average.*

## Question
Map rel_win(r) — the diff-vs-state relative reconstruction win — as a function of
r = fraction of smooth-synthetic motion in the training mix (vs content-rich lavfi).
Find r* = the crossover where diff-target stops paying.

## Design
- **No new encoding:** merge the two existing frozen caches (cache.pt = synth,
  cache_lavfi.pt = lavfi; both V-JEPA 2 fp16, 1024-d, 96 train/32 val each).
- **Ratios:** r ∈ {1.00, 0.75, 0.50, 0.25, 0.00} — train-set mix only; val is
  ALWAYS the 50/50 mixed val (both domains judged together — the map must hold
  on the same testbed across r; changing val per-r would confound).
- **Arms:** {state, diff} × {seed 42, seed 1337} × r — same TinyPredictor,
  steps, LR, windowing as K1/K2 (identical harness; the ONLY knob is the mix).
- **Primary metric:** rel_win(r) = mean over seeds of (mse_state − mse_diff)/mse_state.
- **Readers:** SKIPPED in K3 by pre-registration — the mixed label space makes
  reader scores ambiguous across subpopulations; K1 (ridge-visible) and K2
  (ceiling 1.0) already characterize the readers. Primary metric only.

## Gates (frozen)
- **BOUNDARY_MAPPED:** rel_win(r) decreases with r (Spearman(r, rel_win) < 0)
  AND total spread ≥ 0.05. r* = the interpolated zero-crossing, booked.
- **NO_BOUNDARY:** spread < 0.05 or non-monotone noise — the K1/K2 contrast
  was seed-level, not domain-level; the keel latent rung demotes to noise.
- **INVALID_HARNESS:** any arm fails persistence on the mixed val, non-finite
  losses, cache load failure.
- No post-hoc loosening. Replication of the exact r* number is K4's job, not
  tonight's.

## Receipts
- training/keel_k1/results/k3_results.json (full grid) + RESULTS.md block.
- Budget ≤45 min. Fire under chip_route tensor + .gpu.lock + verified-fire chain.
