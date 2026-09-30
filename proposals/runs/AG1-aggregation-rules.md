# AG1 — Aggregation-rule repair: consensus vs union vs track record (CPU)

**Status:** PRE-REGISTERED, frozen before fire. 2026-09-30, ~09:5x AKDT.
**Runners:** `experiments/ag1_aggregation_rules.py` · **Results:** `results/ag1_aggregation_rules/results.json`
**Source:** Syzygy d158 holarchy finding (forwarded by Casey 09:25): "consensus repairs substitution
errors, union repairs omission errors, and a member's track record — not momentary agreement —
picks the rule." This experiment converts that finding into a falsifiable test on OUR machinery
(kNN judgment fields over tictactoe, the H1/FD1 codebase). Operationalization differs from
Syzygy's (their events vs our 3-class outcome fields) — the CLAIM tested is the principle, not
their implementation.

## Construction

- Pool: 2500 labeled tictactoe boards (minimax solver, correct mover) → live 1500 (each member
  samples its own 1200 from the live pool — subsets differ, ~80% overlap) / calibration 300 /
  dev 200 / test 500 (disjoint). 7 members, each with its own 16-d random projection
  (member diversity via geometry + data). [AMENDED PRE-FIRE before any smoke: original single
  1200-corpus gave members identical data — diversity must come from subsets too.]
- Member answer: kNN k=9, inverse-distance vote over {−1,0,+1}; internal margin.
  Abstention: nearest-episode distance > per-member τ_abs (frozen = 85th pct of that member's
  calibration nearest-distances, post-defect).
- Defect injections (per member, per condition):
  - SUB: flip 15% of stored labels (confident wrong votes).
  - OM: delete 15% of stored episodes (abstentions rise naturally).
  - MIX: flip 8% + delete 8%.
  - CLEAN: none (track-record reference).
- Track record: member's calibration accuracy measured POST-defect (honest — the record
  includes its damage).
- Rules (final answer per test board):
  - R-consensus: majority vote among non-abstaining members (ties → 0).
  - R-union: majority among DECISIVE voters (member margin >= its calibration-median margin);
    if none decisive → 0. Quorum not required — "any signal counts."
  - R-track: vote weight = softmax(calib_acc / 0.05) over non-abstaining members.
- Selectors for G3 (pick between R-consensus and R-union on the MIXED stream):
  - SEL-momentary: per board — consensus vote-share >= τ_m → consensus else union; τ_m frozen
    on dev by grid {0.40,0.45,0.50,0.55,0.60} maximizing dev accuracy.
  - SEL-track: stream-level — pick whichever rule scored higher on the dev split scored by
    members' POST-defect track records; one choice for the whole stream.

## Frozen gates (decided before fire)

- **G1:** R-consensus > mean single-member accuracy on SUB-heavy — paired, >= 4/5 seeds.
- **G2:** R-union > R-consensus on OM-heavy — paired, >= 4/5 seeds.
- **G3:** SEL-track > SEL-momentary on MIXED — paired, >= 4/5 seeds.
- **KEEP** iff all three gates pass; otherwise report per-gate results honestly
  (PARTIAL-SUB / PARTIAL-OM / PARTIAL-SEL labels for whichever pass). No post-hoc threshold
  changes; dev-frozen quantities stay frozen.

## Seeds

8811–8815 (corpus draws, member projections, defect masks, board splits).

## Failure handling

Smoke first (2 seeds, 600-board pool). Fail loud; no provider calls; book whatever lands.
