# CM1-r6 — judge-state chunking A/B/C: is r5's size degradation causal, and does chunking fix it?

Pre-registered 2026-10-01 ~05:55 AKDT, BEFORE fire. Frozen gates, mechanical
verdict mapping, booked either way (results/cm1/round_006_out.json).

## The constraint being tested

r5's controlled finding: identical Seed drafts cleared the gates in the
12-report judge state (arm A) but failed in the 36-report state (arm B) —
jev-latest's gate judgment degrades with judge-state size. r6 turns that
observation into a causal + engineering question:

1. Is state SIZE the mechanism (vs composition/nondeterminism)?
2. Does chunking a 36-draft workload into 12-draft judge calls restore
   12-report judgment quality?

## Design — three arms on IDENTICAL draft objects

Drafts: **reuse r5's stored drafts** from results/cm1/round_005_out.json
(arm-B 36 drafts = 3 cells × 12 stimuli for arms A'/C; arm-A 12 Seed drafts
for arm D). Fail-loud if absent → regenerate per the r5 recipe (Seed-2.0-mini,
temp 0, format retry) and book which path was taken.

- **Arm A' (monolithic replication):** all 36 arm-B drafts in ONE judge call,
  r5 arm-B recipe verbatim (batched rule-rich gate questions @0.5, jev-latest).
  Double duty: re-measures r5 arm B on the same draft objects → free
  jev-latest session-determinism check.
- **Arm C (chunked):** the SAME 36 drafts split into 3 × 12-draft chunks,
  stimulus-major (each chunk keeps whole stimuli, mixed cell composition —
  every draft intact in exactly one chunk), identical per-draft questions.
- **Arm D (reference):** the 12 arm-A drafts in one 12-draft judge call
  (r5 arm-A replica).

No GEN calls needed if drafts are reused — pure judgment A/B. GEN smoke of
cells only if regeneration was required.

## Frozen gates (mechanical)

- **H1 CHUNK_RESTORES:** pass_rate(C) − pass_rate(A') ≥ +0.20 on the
  identical 36 drafts, AND pass_rate(C) ≥ pass_rate(D) − 0.10.
- **H2 JUDGE_NONDETERMINISTIC:** pass_rate(A') differs from r5's stored
  arm-B gate outcomes on the same drafts by ≥ 0.20 absolute → jev-latest
  judgment is session-nondeterministic; book this FIRST (it changes fleet
  gate doctrine more than chunking does).
- **H3 CHUNK_NEUTRAL:** |pass_rate(C) − pass_rate(A')| < 0.05 → size is not
  the mechanism; suspects ranked: state encoding, question-key collision at
  scale, per-call attention budget.
- **H4 REPLICATE_FAIL:** pass_rate(D) < pass_rate(A') → r5's ordering
  reversed; re-book r5's finding as unstable.

Priority when multiple fire: H2 > H4 > H1 > H3.

## Cost gate (frozen)

Chunked arm's total wall ≤ 1.5× monolithic wall (3 calls vs 1; state tokens
partition, not duplicate). Cost ledger per arm (questions, wall, tokens if
exposed).

## Harness

Fail-loud receipts; verdict booked even on partial failure (arm that errored
= EXCLUDED, noted in receipt). Output round_006_out.json + rounds.jsonl
append, same schema as r5. No pinch in this round — this measures the GATES
only; serving quality is out of scope (r5 already booked pinch as the
load-bearing fallback).
