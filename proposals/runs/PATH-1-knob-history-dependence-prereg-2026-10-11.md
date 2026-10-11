# PATH-1 — knob history-dependence census (prereg, frozen before fire)

Spawned by SCOUT-101 (rc q34 PATH-DEPENDENT law): closed-loop s-dial FAIL — same rung via
ramp ≠ same rung held fixed. THRESH-1/THRESH-2 ladder grades are certified single-step-from-pin
only. PATH-1 tests whether our booked grades survive a two-arm schedule comparison.

## Question
Does the payload at a pinned endpoint setting depend on the schedule that reached it
(history-dependence), or only on the setting itself (stateless)?

## Knobs (endpoint settings pinned)
- determ1 eps, endpoint 1e-3 (subprocess; SOFT torch class — verdict/digest-level comparison, wall_s excluded)
- eproc sigma, endpoint 0.5 (in-process; pinned THRESH-2 series)
- degrade_gate tolerance, endpoint 0.5 (subprocess, fresh per call — invocation-order arm only; declared scope caveat)
- verdict_gate minimum, endpoint 0.875 (in-process)

## Arms
- RAMP: walk the full THRESH-2 5-rung ladder in order, capture endpoint payload at the final rung.
- DIRECT: run only the endpoint setting.
Each arm executes inside ONE fresh interpreter (driver mode) so in-process module state sees the
full schedule; the parent compares endpoint payload digests across arms.

## Gates (frozen)
- G1: all 8 arm-runs complete (4 knobs × 2 arms), each arm emits a parseable endpoint digest.
- G2: THRESH-2 anchor — grades at ladder endpoints reproduce the booked classes
  (determ1 CONTINUOUS-digests-present, eproc CONTINUOUS + sigma0 refusal, degrade COARSE
  REGIME-BRITTLE→GRACEFUL, verdict COARSE PASS→FAIL); cite fd25a5c.
- G3: any endpoint digest mismatch across arms ⇒ PATH-DEPENDENT for that knob ⇒ annotate
  affected receipts (THRESH-2 grades for that knob are schedule-conditional).
- G4: all endpoint digests identical across arms ⇒ PATH-INDEPENDENT ⇒ booked CONTINUOUS grades
  upgraded toward unconditional (annotation only; verdict language changes booked here).

## Honest caveats (pre-declared)
- determ1: run-to-run nondeterminism (SOFT class, W5B2/THRESH-1 precedent) can mimic path
  dependence; a mismatch is graded PATH-DEPENDENT-SOFT unless it reproduces in a DIRECT-vs-DIRECT
  control (which it must pass for any RED to stand).
- degrade_gate: subprocess-per-call means arm order is parent-level only; a GREEN is
  invocation-order statelessness, not deep statelessness.
- determ1 lattice_snap writes tagged scratch artifacts — unique tags per arm; no booked-artifact
  contact. Census output to --out only (refuse-overwrite, exit 3, RC-1 rule).

CPU only, deterministic except determ1 SOFT lane. Never echoes secrets. Fail-loud on missing gates.

## AMENDMENT 1 (PATH-1b steerability result, 2026-10-11 — post-verdict annotation per PATH-1b G4)

PATH-1b (prereg PATH-1b-steerability-prereg-2026-10-11.md, fired from 1bbe6f2, receipt
results/path1b/census.json digest c9d39ea16f05bf4b) measured fine-target steerability at
ladder+midpoint resolution: **eproc sigma STEERABLE** (3 distinct digests at 0.5/0.55/0.75) —
the CONTINUOUS upgrade granted by this census's G4 STANDS for eproc. **degrade_gate tolerance
and verdict_gate minimum: FIXED-POINT-AT-FINE rows** (all three fine targets byte-identical) —
per PATH-1b G4 these carry a steerability caveat: within a grade band the payload is
target-indistinguishable; any downstream claim requiring FINE-grained discrimination from these
two gates is unsupported by booked evidence. Interpretation note (honest, not gate-changing):
both knobs are quantized/COARSE per THRESH-2 (verdict PASS→FAIL at 0.95; degrade RB→GRACEFUL),
so the identical fine region is consistent with payload quantization; the q36-shaped
target-insensitivity caveat is attached to the receipts either way.
