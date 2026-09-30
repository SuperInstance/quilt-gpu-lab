# QO3 — early-forecast horizon: at which gen does the oracle first clear AUC 0.80?

## Pre-registration (written before firing; commit precedes run)

**Question.** QO1 pooled all gens and hit val AUC 0.951. Is crossing foreseeable EARLY (gen <= 3,
i.e. near-deterministic at birth per QG2 desert-at-birth) or does late-gen information matter
(per QG3 slow-climb)? Horizon = first gen g where a per-gen oracle (champion state at gen g only)
clears AUC 0.80 on stream-split val.

**Design (declared).**
- Data: fresh instrumented lane, identical physics/protocol to QO1 (shot arm, S=4096, W=6,
  15 children, 12 gens, bar 0.45, rng seed 1234 global fresh — same as QO1, so lane should
  reproduce QO1's crossing rate; trajectories deterministic given seed => lane == QO1 lane,
  declared intentionally so QO3 is directly comparable).
- Per-gen models: for each g in 0..12, train the same MLP (3x64 ReLU, BCE, Adam 1e-3, <=300 ep,
  early stop val AUC patience 30) on rows from THAT GEN ONLY; features identical to QO1
  (gen-scaled, len/W, train v, champ_v, gate hist/6). Split 80/20 by stream, same perm seed 99.
- Also fit the per-gen balance-only logistic baseline (cv at gen g) for reference.

**Frozen gates.**
- G1 (anchor): lane crossing rate inside QG2 CP95 [0.5670, 0.5974]; else STOP, book FAILED-DIVERGED.
- G2 (horizon, primary): first g with val AUC >= 0.80. Report g* and the full AUC trajectory.
  No pass/fail on g* itself — it IS the readout. Declare interpretation rule in advance:
  g* <= 3 => crossing visible at/near birth (feeds QO2 early routing); g* >= 8 => late-gen
  information dominates (slow-climb signature; oracle must run mid-flight); monotone-vs-jump
  shape is itself evidence (monotone climb = accumulating signal; jump at late g = path-dependent
  lottery component).
- G3 (noise floor): bootstrap the g* estimate — 200 resamples of val streams, report how stable
  the first-crossing gen is (IQR of g* across resamples). If g* unstable (IQR >= 3), book
  HORIZON-UNSTABLE rather than a point claim.

**Failure modes honored:** fail-loud; no re-rolls; if AUC never clears 0.80 by gen 12, book
HORIZON->NONE (itself informative: QO1's 0.951 needed pooled gens).

Artifacts: `experiments/qo3_horizon.py`, `results/qo3_horizon/{results.json,run.log}`.
Provenance: qcells lab canonical home = **SuperInstance/micrograd-quilt** (labs/qcells tree),
per MicroMoth-quilt PR #29 citation convention.
