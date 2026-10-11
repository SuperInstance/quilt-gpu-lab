# THRESH-2 PRE-REG — Granularity-ladder census over censused knobs (2026-10-11)

Spawned by SCOUT-99 (rc-20260824-11 q33: armed eviction exposes 8/9 intermediate rungs;
"exposure, not ordering, is how an eviction preference becomes real") sharpening the
THRESH-1 lesson (knob-liveness is input-dependent; q32's trace-identical mid-rungs are
the fleet-side twin). Extends THRESH-1's 2-setting divergence probe to a LADDER.

## Question
For each knob THRESH-1 witnessed at its endpoints, how many DISTINCT trace rungs does
the full ladder expose? Grade each knob COARSE vs CONTINUOUS; a non-monotone ladder
(q34 hazard shape) is recorded as such, not scored dead.

## Knobs and pinned ladders (5 settings each, endpoints = THRESH-1 anchors)
1. determ1 eps: 1e-1, 1e-2, 1e-3, 1e-4, 1e-5 (arm B, pinned runner; unique per-setting
   tags thresh2_eps* — never touches booked artifacts, honoring the 7th RC-1
   in-place-write witness; payload = booked JSON minus wall_s, canonical digest).
2. eproc sigma: 0.0, 0.25, 0.5, 0.75, 1.0 (pinned 64-pt series from THRESH-1; digest of E).
3. degrade_gate tolerance: 0.0, 0.25, 0.5, 0.75, 1.0 (pinned sweep incl. the
   tolerance-witnessing small positive delta; digest of output file bytes).
4. verdict_gate minimum: 0.80, 0.85, 0.875, 0.90, 0.95 (pinned value 0.91, stat std 0.03
   n=32, completeness true; digest of verdict + full receipt).

## Grading (per knob, words frozen before fire)
- n_rungs = count of distinct payload digests across the 5 settings.
- CONTINUOUS: n_rungs == 5.
- LADDERED: 2 < n_rungs < 5 (mid-rungs partially collapse).
- COARSE: n_rungs == 2 (endpoints only, all mid-rungs collapse to one side — q32 shape).
- MONOLITHIC: n_rungs == 1 (entire ladder identical).
- Monotonicity: for knobs with ordinal output (verdict strings / E-path), record the
  rung sequence; a non-monotone sequence is booked as HAZARD-shape (q34), NOT dead.

## Gates
- G1 (runnability): all 4 knobs x 5 settings execute without error => 20 rows, 0 EXC.
- G2 (endpoint anchors): endpoints reproduce THRESH-1's booked behavior — determ1
  1e-2 != 1e-4; eproc 0.5 != 0.75; degrade 0.0 => REGIME-BRITTLE and 1.0 => GRACEFUL
  (byte-digests of the file vary); verdict_gate 0.80 => PASS, 0.95 => FAIL. Any anchor
  miss => gate FAIL, stop, amend THRESH-1 booking in place.
- G3 (vacuous => RED): any MONOLITHIC knob => RED (parameter decoration, q32 class).
  COARSE/LADDERED/CONTINUOUS are findings, not failures.
- G4 (determinism, SOFT where torch): in-process knobs (eproc, verdict_gate) re-run
  bit-identical; subprocess knobs (determ1 torch lane, degrade file bytes) verdict-level
  identical (known determ1 run-to-run digest nondeterminism, W5B2 precedent).

## Cost
CPU ~20m (dominated by 5 determ1 arm-B runs). Serial; GPU idle-or-light torch lane only.

## Honest-booking clause
Verdict from the committed tree only; fail-loud anchors; wrong guesses amended in place.
