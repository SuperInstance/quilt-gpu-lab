# QO6t prereg — transient-stress of the QO6 kill gate on the QG3 desert-fence population

Spawned by SCOUT-52 (2026-10-06): the rc-20260824-11 q7 result killed the dip-DURATION molt gate,
corroborating QO6n (our gate consumes only dip-duration-like stats). The one untested cell of the
QO2 kill matrix is the QG3 desert-fence population: streams whose champion fitness is flat for many
generations (desert) and then crosses late (fence opens at 2x gens). QO6's V1-V4 pins used synthetic
series only. This experiment feeds the gate REAL per-stream trajectories from a W6/gens=24 lane.

## Instrument (pinned, reused verbatim)
- Lane kernel: experiments/qg6_variance_rescue.py `run_lane` (itself copied verbatim from
  experiments/qg3_trap_anatomy.py), extended ONLY by recording the per-gen champion fitness
  trajectory per stream (champ_v history, shape (gens, S)). No kernel-semantics change.
- Gate: tools/eproc.py `kill_gate` (QO6-validated, lineage pinned 61b9e04/aad90ac5).
- Anchors: QG3 arm C (W6/g24) crossed 0.755; QG3 arm A (W6/g12) crossed 0.578. Booked.

## Gate-consumed series (defined BEFORE firing)
For stream s: r_s(g) = empirical CDF rank of v_s(g) within the population at gen g
(fraction of streams with champion fitness <= v_s(g)), in (0,1]. Rationale: a stream stuck in the
desert has DECLINING percentile as the population climbs past it (the QO6 "P(cross) declines"
semantics without an oracle); a fence stream declines then jumps when it crosses. This is
oracle-free and cheap. Honest caveat declared now: population-rank is a RELATIVE signal — a
whole-population stall would leave ranks flat (gate correctly refuses INSUFFICIENT).

## Arms / checkpoints
- Lane: W=6, gens=24, S=512, bar=0.45 (QG3 pin), seeds {11,12,13,14} (4-seed ensemble per the QG7
  subpopulation lesson; single draws are forbidden for subpopulation verdicts).
- Checkpoints: decision A = gate on prefix gens [0..7]; decision B = prefix [0..15]; full-24 re-run
  for retraction status. kill_gate(series, sigma, delta=0.1) — delta is the QO6 V2 pin.
- sigma: PRIMARY 0.03 (QO6 V3 pin). Sensitivity sweep {0.02, 0.04, 0.05} recorded, exploratory only;
  the primary verdict is the sigma=0.03 column. No sigma is fit from the data.

## Pre-registered gates (words frozen here)
- G1 CONSTRUCTION: per seed, crossed-by-24 rate within 0.755 ± 0.05 (small-S CP95 slack) and
  crossed-by-gen-12 rate within 0.578 ± 0.05 (fence present). Fail => lane broken, STOP, book fail-loud.
- G2 MECHANICS: kill_gate runs on every prefix without refusal (series >= 10 points: prefixes are 8
  and 16 points — the 8-point A prefix is BELOW the witness minimum 10, so decision A is formally
  moved to prefix [0..11] (12 points). Decision B stays [0..15]. This is a protocol fix, not a gate
  loosening: A = gen-11 checkpoint, B = gen-15 checkpoint.)
- G3 VERDICT (primary, sigma=0.03, per-seed then pooled):
  - falseKILL@A = fraction of crossed-by-24 streams with KILL_CANDIDATE at A.
  - recovery = fraction of A-kills whose full-24 verdict is KEEP (retracted).
  - power@B = fraction of NOT-crossed-by-24 streams KILL_CANDIDATE at B.
  - PASS iff recovery >= 0.80 AND power@B >= 0.30. falseKILL@A is reported as the headline hazard
    number regardless of verdict; if falseKILL@A > 0.30 AND recovery < 0.50, verdict is
    PREMATURE-KILL (gate not deployable before gen ~12 on fence populations) — booked whichever
    way the data falls.
- G4 COST: <= 15 min GPU total, serial lane, no other GPU work; no booked result modified.

## Falsifiable prediction (before firing)
Fence streams accumulate long flat/declining prefixes, so the gate WILL fire early and often:
falseKILL@A > 0.20; retraction rescues most by 24 (recovery > 0.70) because a crossing stream's
rank percentile jumps and E decays. If instead falseKILL@A is near zero, the gate is inert on real
populations (kill power@B will also be near zero) and QO6's synthetic pins overstate deployability.

Cost estimate: ~5-8 min GPU (4 seeds x S=512 x gens=24, ~1/4 of a QG6 arm set) + booking.
Status: FIRED only after this file is committed and pushed.
