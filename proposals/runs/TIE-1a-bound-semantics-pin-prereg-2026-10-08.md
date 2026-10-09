# TIE-1a PREREG — inclusive-bound / tie-semantics pin (spawned by TIE-1, SCOUT-79 selectlib class)

Date: 2026-10-08 22:4x AKDT. Spawned by TIE-1 G3 (both tolerance flips UNDETECTED by owning suites).
Slot: day-conductor (B), 2026-10-09 06:4xZ. Cost ~12 min CPU, 0 GPU.

## Frozen scope
Two instruments with UNPINNED boundary semantics (TIE-1 yellows):
1. `tools/verdict_gate.py` `Gate.passes` — currently: value==minimum PASSES (`<` is the fail
   condition), value==maximum PASSES (`>` is the fail condition). INCLUSIVE at both bounds.
2. `tools/degrade_gate.py` `run_gate` tolerance — currently: `delta > tolerance` flags;
   delta==tolerance is NOT flagged (permissive at tie, strict pass inside).

## Pre-registered decision (before firing)
PIN CURRENT SEMANTICS, do not change verdicts (no booked result sits on a boundary value — TIE-1
G3 found latent class only). Changing semantics now would be a retroactive verdict edit; pinning
documents and locks them instead.

## Gates
- G1: `Gate.passes` docstring states INCLUSIVE bounds explicitly (`value >= minimum`,
  `value <= maximum`); tie-case tests added to tests/test_verdict_gate.py: (value==minimum PASS,
  value==maximum PASS, value just-below-minimum FAIL, value just-above-maximum FAIL).
- G2: degrade_gate `run_gate` docstring states tie semantics explicitly ("delta == tolerance is
  NOT flagged"); tie-case tests added (a degrade_gate suite file if none exists, else a new
  tests/test_degrade_gate.py): delta==tolerance → not flagged; delta just-above → flagged;
  delta below → not flagged. Suite self-runs via unittest.main().
- G3: mutation-lite re-check (temp-copy flips, never working tree): `<`→`<=` in Gate.passes and
  `>`→`>=` in degrade_gate tolerance MUST NOW BE DETECTED by the owning suites (at least one
  failing test each). This is the TIE-1 red that must go green-then-red-proven.
- G4: zero verdict change — tests/test_verdict_gate.py existing 11 tests still pass unchanged;
  degrade_gate --selftest (if present) still passes; grep of committed call sites confirms no
  caller relied on exclusive-bound behavior.

## Honesty clause
If G3 mutation detection fails for an unforeseen reason, book RED with the failure mode named;
no re-roll within the slice.
