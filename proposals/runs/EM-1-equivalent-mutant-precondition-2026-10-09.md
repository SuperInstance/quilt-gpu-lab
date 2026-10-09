# EM-1 — Equivalent-Mutant Precondition (docs-only, 2026-10-09 ~07:1x AKDT / 15:1x UTC)

Spawned by SCOUT-85; cites SuperInstance/constraint-theory-py method correction in canons
b87ae87 (13:19Z): 4 of their mutations stayed 167/167-green and ALL were equivalent mutants
(self-correcting 3x3) — an "undetected mutant" row filed without a behavior check is a false
blind-spot accusation against the code, not a finding against the gate.

## Amendment (adopts the precondition)

**Rule added to FW-1-successor spec:** a mutation-row may only be filed as a blind spot AFTER
demonstrating the mutant changes measured behavior — an output diff, or a harness counter /
test verdict that flips on the mutant. Green-under-mutation alone is NOT evidence; the mutant
may be behaviorally equivalent (canons b87ae87 class).

## TIE-1 / PARAM-1a receipt audit against the precondition

- TIE-1's 2 UNDETECTED yellows (39-row census) were closed by TIE-1a pins; both TIE-1a flips
  re-verified behavior-checked BY CONSTRUCTION (not assumed): each flip is caught by the
  pinned tie-case tests, every one of which asserts a concrete gate output
  (tests/test_verdict_gate.py:103-121 — tie-at-min PASSES / tie-at-max PASSES /
  just-below-min FAILS / just-above-max FAILS; tests/test_degrade_gate.py:11-29 —
  delta==tol NOT flagged / just-above-tol flagged / below-tol NOT flagged / default-zero flags
  any rise). A behavior-changing mutant necessarily flips at least one of these assertions;
  mutation_lite rc=1 on both flips is therefore a behavior-diff witness, not a bare green-count.
- PARAM-1a's 3 boundless fail-closed tests (test_verdict_gate.py:83-97) likewise assert
  concrete verdicts (vacuous-gate FAILS; VOID/DEGENERATE precedence unmaksed) — any
  mutation row citing them carries a behavior-diff automatically.
- Caveat recorded: the FW-1-successor "appended-after-guard" row (TIE-1a mechanical finding)
  predates this rule — it was a *collection* finding (tests never ran), not a
  green-under-mutation claim, so it does not need retroactive behavior-diff evidence; noted
  so future readers do not demand one.

## Gates (from SCOUT-85 spawn)

- G1: amended receipts (this note + RESULTS.md FW-1-successor row) contain ZERO mutation-rows
  lacking a behavior-diff — verified above; TIE-1's two original yellows are annotated as
  closed-with-behavior-diff, and no other mutation-rows exist in receipts/RESULTS (census:
  only TIE-1/TIE-1a/PARAM-1a/GATE-MARGIN-adjacent mentions carry flips, all pinned by
  assertion-bearing tests). PASS.
- G2: TIE-1a's 22/22 census verdict stands unchanged (docs-only slice; no tool/test bytes
  touched). PASS.

No GPU fired (CPU docs slot per rotation). No booked result threatened.
