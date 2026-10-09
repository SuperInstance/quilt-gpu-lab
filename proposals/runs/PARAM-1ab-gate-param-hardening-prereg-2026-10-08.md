# PARAM-1a/1b/eproc-delta — gate-parameter hardening (pre-registration)
Date: 2026-10-08 17:4x AKDT. Spawned by PARAM-1 (265ce29 GREEN, 2 latent yellows + 1 heuristic
divergence at 16:4x repro). CPU-only, no GPU lane. This is hardening of validation instruments —
no booked verdict is expected to change; any change to a booked verdict = RED and must be
amended in place, not silently.

## Scope (frozen)
1. **PARAM-1a — verdict_gate boundless-Gate vacuous-pass** (`tools/verdict_gate.py`):
   today a `Gate(name, value)` with BOTH bounds None evaluates() True and passes() True.
   Fix: in `finalize`, an evaluated gate with no bound is FAIL-closed — the whole finalize
   returns FAIL with reason `gate X: no bound (vacuous gate)`, placed AFTER the VOID/
   DEGENERATE/INCONCLUSIVE precedence checks (a boundless gate must not mask a VOID or a
   degenerate stat). Refuses at the pin level, not at the caller.
2. **PARAM-1b — determ1 eps unvalidated at argv** (`experiments/determ1_lattice_snap.py`):
   today `float(sys.argv[2])` accepts 0.0, negative, NaN, inf; snap(t/0.0) on arm B diverges
   silently. Fix: for arm B require `eps > 0 and math.isfinite(eps)` else raise ValueError
   (fail-loud, refuse-to-run). Arm A unchanged (eps ignored).
3. **eproc delta explicit bound** (`tools/eproc.py`): `delta` currently unvalidated (16:4x
   repro booked it UNVALIDATED-by-heuristic where the hand census said GREEN). Fix: in
   `witness` (and it flows to kill_gate via witness), require `0 < delta < 1 and
   math.isfinite(delta)` else raise ValueError. Default 0.05 unchanged; documented-overrule
   pin no longer needed because the instrument itself now carries the bound.

## Pre-registered gates (words, frozen before fire)
- G1: verdict_gate selftest extended: boundless evaluated gate => finalize verdict FAIL with
  the vacuous-gate reason; all existing selftest cases unchanged in verdict (precedence
  preserved: VOID still beats vacuous, DEGENERATE still beats vacuous).
- G2: determ1 arm B with eps=0 / -1 / NaN / inf each raise ValueError before any GPU work;
  arm B with eps=1e-2 still runs (or at minimum passes validation if the slice is too short
  to run the lane — validation-only is acceptable for THIS gate).
- G3: eproc witness with delta=0, delta=1, delta=-0.1, delta=NaN each raise ValueError;
  delta=0.05 default path unchanged (existing QO6s/KILL-gate semantics untouched).
- G4: no booked verdict's script changes behavior at its committed arguments (all committed
  calls pass validated params). Spot-check: grep committed finalize()/determ1/eproc call
  sites; if any committed booking called with a now-invalid argument => RED, amend booking.

## Cost
~20 min CPU. No GPU. Nothing else in scope; verdict_index / param_audit untouched except if
G4 finds a live RED.
