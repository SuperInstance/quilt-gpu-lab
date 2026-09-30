# FD1 — Frontier Distillation (CPU)

**Status:** PRE-REGISTERED, frozen before fire. 2026-09-30, ~09:26 AKDT.
**Runners:** `experiments/fd1_frontier_distillation.py` · **Results:** `results/fd1_frontier_distillation/results.json`
**Lane:** wide-scope #1 — the "student never sees easy cases" claim, made falsifiable.

## Question

A tiny student trained ONLY on frontier episodes (the field's low-consensus boundary) — does
it (a) not lose accuracy vs a uniformly-trained student, and (b) when combined with the field
(field answers easy, student answers hard), BEAT the uniform student? Teacher = minimax
solver (free, perfect, no API).

## Construction

- Corpus: 3000 random reachable tictactoe positions (solver labels {+1,0,−1}); split
  2000 field / 1000 held-out eval.
- Field: 27-dim one-hot → fixed random projection (16-d); kNN k=9 inverse-distance vote;
  leave-one-out confidence margin for every field board.
- Frontier = bottom-⅓ by margin (~667 boards). Non-frontier = "easy".
- Students (size-matched across arms, identical hyperparameters): MLP 27→48→24→3, tanh,
  softmax CE, Adam lr 1e-2, 60 full-batch epochs — only the TRAINING SUBSET differs:
  - **uniform:** all 2000 field boards
  - **frontier:** frontier boards only (~667)
  - **hybrid (eval-time composition):** field answers easy eval boards, frontier-student
    answers hard eval boards (hardness = field margin on the eval board, thresholded at the
    field's own ⅓ quantile)
- Seeds 7721–7725 vary corpus draw, eval draw, student init.

## Frozen gates (decided before fire)

- **KEEP** iff on ≥ 4/5 seeds:
  (a) acc(frontier) ≥ acc(uniform) − 0.5pp  [no loss from ignoring easy cases]
  AND (b) acc(hybrid) ≥ acc(uniform) + 1.0pp  [concentrating capacity wins]
- **KILL** otherwise; partial (a only) → verdict **HALF** (recorded: frontier-training is
  safe but composition doesn't win).
- No architecture changes after fire; no extra epochs; thresholds frozen at the ⅓ quantile.

## Failure handling

Smoke first (2 seeds, 400/200 corpus). Fail loud. Book honestly whatever lands.
