# QO6 — Retractable kill-evidence for QO2 routing (e-process gate)

Pre-registered 2026-09-30 05:3x AKDT, night conductor. Spawned by PR-SWEEP #4 (delta-shape PR #1
retraction doctrine: "a process that cannot retract is a p-value in disguise").

## Problem
QO2 routing (oracle-guided stream killing) must NOT kill streams on irrevocable tail predicates.
A fixed-threshold kill on oracle P(cross) < c is exactly such a predicate: one bad generation
kills a stream that might bloom late (QG3: traps open with generations; QG6: crossing time varies).

## Design
Port SuperInstance/quilt-ewitness `eproc.mjs` to Python verbatim (same mixture LR e-process,
same MU_GRID, same Ville bound, same honesty contract: sigma REQUIRED, pre-registered).
Vendored lineage pin (from delta-shape PR #1 src/esign.mjs):
- repo SuperInstance/quilt-ewitness, commit 61b9e0403f2254691570cdf877bbbf81624df1f1
- sha256 aad90ac5aedb4d8e19b189808b47b22fc7258044af2c25c8f7fc90efec19e63a

Kill-evidence gate (the QO2 consumer): for each stream, feed the oracle P(cross) per-gen
trajectory to `witness(series, {claim:"DECREASES", sigma, delta})`.
- verdict WITNESSED and not retracted => evidence the stream is diverging; kill candidate.
- verdict fired then retracted (E decayed below bar) => late evidence arrived; DO NOT kill.
- NOT_WITNESSED => insufficient evidence either way; keep.

## Claims to test (validation, CPU only, deterministic seeded series)
- V1 PORT-PARITY: Python port reproduces eproc.mjs semantics — deterministic reference series,
  hand-computed single-increment LR checks (exact algebra, tolerance 1e-12), and behavioral
  pins: strong downward drift (mean -2, jitter ±2, sigma 1.5) => WITNESSED early;
  flat noise (uniform {-4..4}, sigma 2.6) => NOT_WITNESSED; short series (<10) => refuses.
- V2 RETRACTION: synthetic late-bloomer trajectory — P(cross) slides down then jumps at t=8
  (QG3-style late opening). e-process fires (E >= 1/delta) then decays below bar => verdict
  retracted => kill-gate says KEEP. This is the core QO6 claim: the gate retracts.
- V3 HOPELESS-KILL: monotonically collapsing P(cross) trajectory => WITNESSED, no retraction,
  kill-gate says KILL_CANDIDATE.
- V4 sigma honesty: omitted / non-positive sigma => raises (no silent defaults).

Success = all four. Any failure is booked loudly, not patched silently.

## Non-goals this slice
No live QO2 integration, no GPU. Feeds QO2 (routing fully specified = oracle + budget triage +
this gate) and QG7 (gen-24 asymmetry test uses the same trajectories).

## RESULTS (booked 2026-09-30 05:5x AKDT, night conductor — fired by prior wake 05:3x, unbooked at its death; replicated ALL_PASS this wake)
- V1a PORT-PARITY PASS: single-increment LR exact-algebra match, abs_err 0.0 (vs 1e-12 tol).
- V1b PINS PASS: strong downward drift -> WITNESSED at t=7, no retraction; flat noise -> NOT_WITNESSED (E_max 3.61).
- V1c REFUSALS PASS: short series (<10), missing sigma, sigma<=0, non-finite -> all refuse (no silent defaults).
- V2 RETRACTION PASS (core claim): late-bloomer P(cross) trajectory fires at t=5 (E_max 581) then decays (E_final 0.40) -> verdict RETRACTED -> gate says KEEP. The gate retracts.
- V3 HOPELESS-KILL PASS: monotone collapse -> WITNESSED t=4, E_max 7.6e6, no retraction -> KILL_CANDIDATE.
- V4 PASS: flat -> INSUFFICIENT (keep, no evidence either way).
- Replicate this wake (deterministic CPU): ALL_PASS identical.

Pinned instruments (fire-time convention): tools/eproc.py sha256 8243ef91b1a39f3f, experiments/qo6_kill_evidence.py sha256 fcbfe984ddfe0133, qcell_sim.py untouched (not used; CPU-only slice).

Conclusion: QO2 routing = oracle (QO1/QO3) + budget triage (QG3/QG6: give generations, not variance) + THIS gate. QG7 consumes the same per-gen P(cross) trajectories.
