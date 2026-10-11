# THRESH-1 — trace-divergence census over parameterized gates

Spawned by SCOUT-96 (rc-20260824-11 q32: "continuous" eviction-preference dial s∈[0,1]
whose intermediate rungs s=0.25–0.75 are TRACE-IDENTICAL to base — a multi-valued gate
parameter whose intermediate settings cannot change the verdict = vacuous-knob class,
TIE-1/PARAM-1 family fleet-side instance).

## Question
Does every parameterized instrument in our live stack have at least ONE adjacent
parameter-setting pair that produces a WITNESSABLE trace/output difference on a pinned
input? A knob with no witnessable effect anywhere in its tested range = RED (q32 shape:
the parameter is decoration, and any PASS it "tunes" is not robustness evidence).

## Knobs under census (pinned, adjacent pairs)
- K1 determ1 eps: experiments/determ1_lattice_snap.py arm B, eps 1e-2 vs 1e-4
  (known-divergent per DETERM-1 booking — positive control for the census method itself).
- K2 eproc sigma: tools/eproc.py witness() on a pinned deterministic series,
  sigma=0.5 vs sigma=0.75 → E path must differ.
- K3 degrade_gate tolerance: tools/degrade_gate.py on the docstring pinned sweep,
  tolerance=0.0 vs tolerance=1.0 → INVERTED vs GRACEFUL flip.
- K4 verdict_gate bounds: Gate("x", value=0.91, minimum=0.80) vs minimum=0.95
  → PASS vs FAIL flip.

## Gates (frozen BEFORE firing)
- G1: every knob executes at both settings on its pinned input; both runs complete
  with parseable receipts/outputs (a knob that cannot even run at two settings = RED).
- G2: for each knob, at least one tested adjacent pair produces a differing output
  digest / verdict / numeric trace (knob WITNESSED).
- G3: any knob failing G2 = RED (vacuous knob). Verdict RED if any RED; GREEN if all
  four witnessed.
- G4: census is deterministic — a second in-process re-run yields identical verdict
  and census JSON (modulo the run-index field).

## Hazard inheritance
EP-1b rule: --out refuses to overwrite an existing fired artifact (exit 3) unless
--force. Fired output immutable once committed.

## Cost
CPU only, ~15–20 min. No GPU. No network.
