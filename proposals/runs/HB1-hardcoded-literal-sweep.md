# HB-1 — Hardcoded-literal + degenerate-statistic sweep over booked verdicts

Spawned by SCOUT-26 (canons 59th wipe): holonomy-consensus published "VALIDATED" results whose
baselines were hardcoded literals (412.0) with a never-run benchmark suite. Our own scripts get
the same audit. 412.0-class in OUR committed scripts = fabricated receipt under our own seal.

## Scope
Committed (`git ls-files`) producing scripts in `tools/` and `experiments/` for the booked verdicts:
qcell_sim, qcell_oracle/QO1, QO3 horizon, QG2/QG3/QG6/QG7 lanes, DECIDE-1 family (decision_cell),
W5b/W5b2, eproc (QO6), D12i, F1, QC-JEV, QO10.

## Gates (pre-registered, in words)
- **G1 (hardcoded-literal)**: for each booked headline value (list below), `grep -F` the literal in
  the producing committed source. A hit **inside a gate THRESHOLD or chance-level constant** (e.g.
  0.5 AUC baseline, 0.25 random) is BENIGN. A hit as a **data value, expected output, or
  comparator-that-always-passes** is **RED** (fabricated-receipt class).
  Headline literals: `0.9510, 0.880, 0.8922, 0.5718, 0.5828, 0.4268, 0.078, 0.891, 0.755, 0.763,
  0.606, 412.0, 8.35, 13.83`.
- **G2 (degenerate-statistic)**: for every gate that contributes to a PASS/KEEP verdict, the gate
  statistic must be capable of FAILING (not saturated-by-construction, not tautological, not
  std==0-blind). Any verdict-PASSING gate whose statistic is constant or reads only its own input
  = **RED**.
- **G3 (never-run suite)**: any producing script with a test/verification entrypoint never invoked
  by a committed test, CI, or a booked repro run = YELLOW (tool-level; verdicts are covered by the
  mandatory (C) repro rule — SCOUT-26 found our defense held, so expect 0 RED here).

## Verdicts
- 0 RED => **CLEAN** (our RC-1/RC-1b/mandatory-repro defenses held, 2nd independent witness).
- Any RED => name the booking it fabricates, amend the booking in place, do not re-roll silently.

## Cost
CPU only, ~20m. No GPU. Fire: one throwaway sweep script under scratch/ (sweep itself is not a
pinned instrument; findings must be independently checkable by re-running the greps).
