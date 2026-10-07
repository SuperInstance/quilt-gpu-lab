# MUA-1 — Match-presence assertions on VX-1 taint queries (pre-register)

Spawned: SCOUT-61 slice, day-conductor (B) slot, 2026-10-07 ~09:2x AKDT.
Source: canons 3a7498a mutant-applied assertion lesson — a grep-based census GREEN with
ZERO matches is indistinguishable from clean; every probe must assert it MATCHED
(nonzero evidence of exposure) before a pass/RED is recorded. No-match = INDETERMINATE.

## Failure class in our instrument
tools/verdict_index.py G3 negative control (`taint_query(idx, NEG) == []`) and every
G2 expected-hit set share one silent assumption: that the matcher is alive. A corrupted
haystack join, a case-folding regression, or an empty index would make G2/G3 report
PASS-shaped output (empty or trivial sets) without probing anything.

## Upgrade (frozen)
1. **Positive evidence**: every G2 round-trip assertion additionally records the
   per-booking match COUNT for its probe term; count==0 on any expected hit => FAIL
   (probe pattern did not match where the verdict demands exposure).
2. **Matcher-alive canary (G3b)**: inject NEG into a copy of one booking's
   verdict_reads; the matcher MUST return that booking on the injected copy. A negative
   control on the live index is only meaningful if the same probe fires positive on a
   seeded copy (mutant-applied assertion — apply the mutation, watch it detected).
3. **INDETERMINATE rule**: any query whose total matched-evidence count across the
   index is 0 cannot distinguish "clean" from "unprobed"; CLI arm reports INDETERMINATE
   instead of a bare empty set for such queries (negative control on live index still
   passes because G3b proves the machinery).

## Gates
- G1: existing G1-G4 selftest verdicts unchanged (9 bookings, statuses, tamper arm).
- G2: all 9 round-trip term->set results IDENTICAL to booked VX-1 sets, each now
  carrying per-booking match counts >= 1.
- G3: negative control still empty on live index; NEW G3b seeded-copy canary returns
  the seeded booking; tamper arms unchanged.
- G4: still CPU-only < 5 s; no GPU (lane contended by inbox-015 student-v2 anyway).
- RED-first: harness must demonstrably FAIL under the old matcher semantics before
  the new gates go green (probe: empty-index copy should now FAIL, not pass).

## Claim under test
The VX-1 taint instrument cannot silently pass on a dead matcher. PASS => match-presence
class closed for this lineage; noted for FW-1-successor census rows. FAIL => book honestly.
