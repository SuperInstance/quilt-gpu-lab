# VNaN-1 — Fail-open red-team of our numeric/enum surfaces (spawned by SCOUT-89)

Spawned by SCOUT-89 (2026-10-09): canons f464caa — external mirrors of the fail-open
validator class (a2a-constraint-protocol accepts `confidence: NaN`; fleet-murmur-worker
tests transcribe the implementation). Our receipt_manifest already fails closed
(GOLDEN-PIN M1-M3). This exercise red-teams the *numeric/enum parsing* surfaces that
produce verdict inputs, where a NaN/string injection could silently flip a comparison.

## Scope (inventory, G1)

Fields consumed by:
1. `tools/verdict_gate.py` — `Gate.value/minimum/maximum`, `StatMeta.std/n/saturated`,
   `completeness`, `status_source` (inputs to `finalize`).
2. `tools/eproc.py` — `series` values, `sigma`, `delta`, `claim` (inputs to
   `witness`/`kill_gate`, plus `eprocess` directly).
3. `tools/prereg_seal.py` — env secret, CLI path args (enum: missing/empty secret).

Injections per numeric field: `float("nan")`, `float("inf")`, `"-inf"`, `"NaN"` (string),
`None`, `""` (empty string), and for enum fields: `""`, `"Own"` (case), `"own "` (space).

## Pre-registered gates

- **G1 (inventory)**: script emits a complete field:path table for the three surfaces
  above; every field enumerated receives at least one injection.
- **G2 (refuse-or-allowlist)**: every injection either REFUSES loudly (exception with
  a clear message, or a verdict lattice value in {VOID, DEGENERATE, INCONCLUSIVE, FAIL})
  OR the field is named in an explicit allowlist with rationale in the results table.
- **G3 (no silent-coerce)**: no injection yields a PASS / WITNESSED / SEALED-equivalent
  outcome that the honest input would not also yield; specifically `float("nan")` must
  never pass a bound comparison (NaN < x is False, NaN > x is False — the a2a lesson).
- **G4 (landing)**: any fix landed is committed with the script; manifest re-sealed;
  CI green post-push.

## Prediction (honest, pre-fired)

Suspected RED: `verdict_gate.Gate.passes()` — `value=nan` with bounds set evaluates
both comparisons False → `passes() == True`, i.e. NaN silently passes every bound.
Also `StatMeta.std = nan` escapes the `std == 0.0` degenerate check. Everything in
eproc looks fail-closed (isfinite on series, `0 < delta < 1`, `sigma > 0` — all three
comparisons are NaN-refusing). prereg_seal already refuses empty secret.

## Cost

One CPU lane, no GPU. ~20 min.
