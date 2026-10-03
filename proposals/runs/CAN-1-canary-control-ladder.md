# CAN-1 — canary control ladder (crab-traps template), pre-registered 2026-10-03 ~12:2xZ

Spawned by SCOUT-30 (crab-traps 47b-self-test.mjs, mutation-verified by canons scout; 1 hex flip → EXIT=1).

## Goal
Upgrade tools/canary.py from a single negative control (cx→cxr alphabet pin) to a crab-traps-style
CONTROL LADDER: multiple negative controls + positive control, each proven to flip the verdict
fail-closed. Port the "self-test must not dirty the tree" property by running all controls IN-MEMORY
(no writes to any tracked path). RC-5's push-time --check layer is a separate item — do not duplicate.

## Controls (frozen before fire)
- POS (positive): canonical fixture + canonical pin → GREEN.
- T1 tamper-expectation: mutate the expected FLEET_CANARY integer by one hex digit → detector must
  report MISMATCH (RED).
- T2 wrong-pin-tip: write the byte canary as non-canonical 0x024A… (leading zero, L9(d) violation)
  → detector must flag non-canonical text (RED).
- T3 tamper-input-bytes: mutate the fixture string ("café Δ 日本語" → "cafe Δ 日本語", unaccented
  twin / byte swap) → computed digest must diverge from pin (RED).
- T4 tamper-canon-ops: rename one canon gate in the op list → alphabet canary mismatch (RED;
  subsumes the existing cx→cxr test, kept as explicit ladder rung).

## Gates (pre-registered)
- G1: ALL controls (T1-T4) RED, POS GREEN, asserted by a single `control_ladder()` function that
  returns a verdict dict; any control NOT red => ladder FAIL.
- G2: running the ladder leaves the working tree byte-identical (git status unchanged; in-memory only).
- G3: mutation sanity — flipping any one bit of the fixture inside the ladder test flips the rung RED
  (the ladder is itself verified, crab-traps doctrine).
- G4: full existing suite still green (28 tests + new ladder tests), CI green on push.

## Verdict rule
PASS only if G1-G4 all hold. Any gate fail => book FAIL honestly, no re-roll this slice.
Cost: CPU ~40m. Zero GPU.
