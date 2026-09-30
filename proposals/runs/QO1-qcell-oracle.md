# QO1 — qcell-oracle: first trained fleet component on the qcell substrate

## Pre-registration (written before firing; commit precedes run)

**Question.** Can a tiny MLP predict, from a stream's champion state, whether that stream will
eventually cross the bar (exact/shot balance >= 0.45) by gen 12 — i.e. is crossing foreseeable
from observable champion state, or does it arrive by lottery?

**Design (declared).**
- Data: fresh GPU lane run, shot arm, S=4096 streams, W=6, 15 children, 12 gens, bar 0.45,
  same calibrated physics as QG2 (`tools/qcell_sim.py` conventions, pi-units, balance=min).
  S=4096 (not 8192) to stay inside the night timebox; a different S changes the mutation-rng
  consumption pattern so trajectories differ from the QG2 run (declared, not hidden).
- Instrumented lane: at each gen g (after selection), record champion state per stream:
  `{gen, champion_len, train_balance v, verified champ_v, gate_histogram[49] (champion gates incl PAD)}`.
- Label: stream's final `crossed` (champ_v >= 0.45 at gen 12).
- Model: MLP 3 hidden layers x 64, ReLU, BCE, Adam 1e-3, <= 300 epochs, early stop on val AUC.
  float32 on the 4050. Split: 80/20 **by stream** (all gens of a stream stay on one side —
  leakage guard).
- Frozen gates:
  - G1 (anchor): lane-level sanity — crossing rate must land within the QG2 CP95
    (0.5670–0.5974); if not, the instrumented lane diverged -> STOP, diagnose, no re-roll.
  - G2 (skill): oracle val AUC >= 0.70 AND beat a balance-only logistic baseline by >= 0.05 AUC.
  - G3 (calibration): mean |pred - outcome| (Brier) reported; no pass/fail, first census.
  - G4 (feature census): permutation importance ranking (balance, len, gen, hist) reported.
- Failure modes honored: fail-loud (exceptions abort, no blanket try/except); if G1 fails the
  run is booked as FAILED-DIVERGED with the diff, not silently re-seeded.

**Artifacts (planned).** `experiments/oracle1.py`, `results/qo1_oracle/` (states parquet/json,
metrics json), `tools/qcell_oracle.pt` + `tools/README.md` update. Commit+push before firing
(this file); book in RESULTS.md after landing.

## PROVENANCE CITATION AMENDMENT (2026-09-30 02:2x, docs-only — per MicroMoth-quilt PR #29)
Training data derives from QG2's reimplementation of the qcells lab loop; canonical home of the
lab is **SuperInstance/micrograd-quilt** (labs/qcells tree). Local paths are quoted history.
No data or gates changed.
