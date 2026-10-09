# TIE-1 — Tie/No-op Gate Census (pre-registered 2026-10-09 03:4x UTC)

Spawned by SCOUT-79 (canons 8fef113): selectlib fails its own anti-vacuous doctrine
because **a comparison whose tie/no-op case resolves to pass** (`mae() > 1e-6` never
calls the clean arm; `X <= Y + 1e-12` passes at tie). PARAM-1a fail-closed boundless
gates but did NOT pin boundary/tie semantics. This census names the class in our tree.

## Target set (frozen before firing)
1. `tools/verdict_gate.py` `Gate.passes()` — `value < minimum` / `value > maximum`
   (tie at value==minimum is PASS-side by reading; PARAM-1 booked it but did not pin).
2. `experiments/determ1_lattice_snap.py` arm-B eps validation (PARAM-1b).
3. `tools/eproc.py` delta/sigma bounds (PARAM-1 booked strict-side — expected GREEN).
4. `tools/degrade_gate.py` `run_gate` tolerance compare (`s["delta"] > tolerance`).
5. `tools/exit_gate_witness.py` parameter comparisons.

## Frozen gates (words, pre-registered)
- **G1 CENSUS**: AST-walk every target's gate-decision comparisons; classify each
  tie/absent-input case as PASS-side (permissive) or FAIL-side (strict). Output table.
- **G2 PROBE**: for every PASS-side flag, construct an explicit tie input and record
  the module's ACTUAL behavior (empirical, not AST-reading alone).
- **G3 MUTATION-LITE**: for every confirmed PASS-side tie, flip the permissive side
  in a TEMP copy (never the working tree), run the owning committed test/selftest;
  detection = suite fails. No distinguishing test => YELLOW "unpinned boundary
  semantics", naming the owning booked verdict(s).
- **G4 COST**: <= 20 min CPU, 0 GPU, one tool (`tools/tie_census.py`) with selftest;
  no booked verdict is edited by the census itself.

## Pre-registered predictions (honest, before fire)
- verdict_gate minimum/maximum: YELLOW (tie passes; no tie-case test likely exists).
- degrade_gate tolerance: YELLOW (delta==tolerance not counted inverted → permissive).
- eproc delta: GREEN on strict-side refusal, MAYBE YELLOW on mutation detection
  (refusal tests pinned in PARAM-1a may not distinguish `<=` vs `<`).
- exit_gate_witness / determ1 eps: expected GREEN (refusals are `in`-set membership,
  not float compares).

RED (live corruption) only if a flagged tie is load-bearing for a booked verdict's
outcome AND the owning suite cannot detect the flip. YELLOW = latent, hardening item
(TIE-1a candidates), no booked verdict is voided by census alone.
