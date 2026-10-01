# PX6 — signature-router: can the board predict the routing surface?

FROZEN 2026-09-30 ~17:45 AKDT, before any scoring run. Commit-first.

## Question

PX5 measured the VALUE of perfect routing (any-cell ceiling 0.8698 vs composition 0.7437 on the
36,073-state test split; headroom H = 0.1261) and showed the signature carries 0.5955 bits about
composition success. It did NOT measure whether the routing signal is predictable FROM THE BOARD —
the MI asymmetry does not guarantee board→signature is learnable. PX6 tests that link directly.

## Method

- PX2 registry, depths (1,2,3,4,5,6) + pinch; PX1 seed-0 split; routers see the SAME 9-float
  representation — nothing more.
- Router target (train split, deterministic priority stated here): pinch if pinch correct,
  else lowest-index correct tree; states where NO cell is correct are excluded from training.
- Arm (a) PRIMARY: DecisionTreeClassifier(max_depth=6, min_samples_leaf=5, random_state=0) on
  best-cell-index; routed top1 = predicted cell's correctness on the test state.
- Arm (b) SECONDARY: confidence-gated — predict_proba max < 0.5 → fall back to the exact
  MajorityVote composition. Threshold frozen here; no tuning.
- Baselines: composition 0.7437; any-cell ceiling 0.8698.

## Branches (test-split routed top1, arm a)

- WIN: ≥ 0.807 (claims ≥ 50% of headroom)
- PARTIAL: ≥ 0.759 (claims ≥ 12.5% of headroom)
- KILL: < 0.759 — routing signal not board-predictable; the +12.6pts stays measured-but-unclaimable.

## Fixed secondary outputs

- Per-class routed vs composition (does routing help BLOCK specifically?).
- Router prediction distribution; degeneracy flag if one cell >95% of predictions.
- Reflex-coverage probe: pinch fired-rate within train all-correct states (how much of the
  reflex-compile partition the existing reflex already owns) — feeds the superinstance-api
  compile-back lane.
- Honesty: KILL is a real outcome. No threshold tuning, no arm selection after seeing numbers;
  both arms reported.
