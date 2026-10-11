# CONST-1 — winning-arm-constant census (pre-registered 2026-10-10 ~18:5x AKDT)

Spawned by SCOUT-95 (canons 55a2afb: CRDT_Research 98.4% "improvement" subtracted from a class
constant; neural-plato exit-1-when-green polarity). Question: does any of OUR A-vs-B booked
verdicts rest on a metric that the producer emits as a constant (zero variance across runs),
i.e. an "improvement" computed against a class the producer can only ever emit one value of?

## Targets (frozen before firing)
1. **QG6 k-arms** — results/qg6_variance_rescue/results.json (arms k=1/2/3, metric `crossed`),
   producer experiments/qg6_variance_rescue.py. Verdict claim: k=3 significantly BELOW k=1
   (variance harmful), k=2 indistinguishable.
2. **DETERM-1 A/B** — results/determ1_lattice_snap/A-*.json vs B-*.json (metrics rate12/rate24/
   auc_fresh/`crossed_gen_sha` distinctness), producer experiments/determ1_lattice_snap.py.
   Verdict claim: snap arms distinct ⇒ draw-path mechanism (RED on lattice-snap determinism).
3. **DECIDE-1b vs DECIDE-1c** — results/decide1/decide1b_results.json vs decide1c_results.json
   (argmax_acc, pred_is_argmin_balance), producers experiments/decide1b.py (+1c lane).
   Verdict claim: IDENTICAL accuracy across instructions (instruction-blind). Identity is the
   claim — a constant here is the FINDING, not a defect (pre-classified; census must verify the
   constant is data-derived, not hardcoded).
4. **IONQ-2 rung-2 battery** — experiments/ionq2_rung2_battery.py (stdout-only; exact-equality
   gates vs literal theory values). Verdict claim: computed == pinned theory constant. Constant
   want-values are the CLAIM; census verifies the `got` side is computed from statevector, and
   gates are equality (not improvement vs a produced class).

## Gates (frozen words)
- **G1 (load)**: all cited result files present and tracked at the firing commit; producers
  importable/greppable.
- **G2 (variance table)**: per-metric cross-run variance computed for every numeric metric in
  targets 1-3; zero-variance metrics flagged. For target 4: gate polarity census (equality vs
  improvement-vs-produced-class).
- **G3 (classification)**: a flagged constant is RED iff (a) the metric decides the verdict
  direction, AND (b) the booking claims an A-vs-B difference, AND (c) grep of the producing
  script shows no data-derived write site for the metric (hardcoded/derived-from-constant).
  Identity-claim bookings with verified data-derived constants = GREEN-with-note.
- **G4 (verdict)**: CONST-1 overall GREEN iff zero RED. Any RED names the threatened booking
  and the book is amended in place per protocol (never silently).

Honest limits: grep-based producer-liveness is a heuristic (note for FW-1-successor); target 4
has no artifact JSON (stdout-only booking — accepted at its own booking, noted).
