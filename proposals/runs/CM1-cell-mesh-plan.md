# CM1 — Cell-mesh round 1: does judgment-gating beat ungated generation? (frozen pre-registration)

Date: 2026-09-29 14:0x AKDT. Pushed BEFORE the run (push-first doctrine).
Parent-authored; lanes rate-limited earlier. First round of Casey's
"dozens of rounds" cell-mesh directive (relational-cells: routings, filters,
projections between dedicated cells — IE3 settled: cells are DEDICATED).

## Cells (each dedicated — IE3 DILUTION_CONFIRMS lesson)

- GEN (generative): Ollama `qwen2.5:0.5b`, temperature 0, one job — draft a
  routing decision from a stimulus using the stated rule.
- JUDGE (judgment): TypeSafe Jev `jev-preview` via /v1/systemone — graded
  noul gates (verified format in docs/typesafe-judgment-cells.md).
- PROJECT (projection): Ollama `nomic-embed-text` — embeds stimulus, drafts,
  canonical answers; local geometry substrate (not gated on; books per round).

## Stimuli (deterministic set, ground truth by rule)

12 fleet-style stimulus strings. Ground-truth rule (deterministic, in the GEN
prompt AND the JUDGE state — identical text):
- domain = engine if any engine term (temp rising/falling, oil, fuel, rpm);
  else navigation if any motion term (blob moving, course drift, AIS contact);
  else deck.
- urgency = high if any hazard term (rising, falling, dropping, leak, fire)
  or two+ domains implicated; else mid if any motion term; else low.
Canonical answer format: `BOOK:<domain>:<urgency>`, domain in
{navigation, engine, deck}, urgency in {low, mid, high}.

## Arms

- A (ungated): GEN drafts once; first answer counts. 12 stimuli.
- B (gated relay): GEN draft -> JUDGE two noul gates ("domain correct per
  rule?", "urgency correct per rule?"), each graded 0..1. If min(gates) < 0.5:
  one retry with gate feedback appended; if still < 0.5: PINCH -> fallback =
  deterministic keyword router (same rule, implemented in harness).
  Per-stimulus path recorded: DRAFT_PASS / RETRY_PASS / PINCHED_FALLBACK.

## Frozen gate (exact bands, sealed before run)

diff = correct(B) − correct(A), n=12 each.
- diff ≥ +2 → GATING_WINS
- −1 ≤ diff ≤ +1 → TIE_NOISE
- diff ≤ −2 → GATING_HURTS
Books regardless: Jev usage tokens, Ollama eval counts, wall time, per-path
counts (where B's correctness came from), embedding geometry (nomic cosine
sims of drafts vs canonical).

## Fail-loud + determinism

- Ollama temp 0; Jev calls retried once on 429/5xx (2 s backoff), then fail
  loud (round INVALID_HARNESS).
- Any parse failure of a final answer = scored wrong (not dropped), recorded.
- Output: results/cm1/round_001_out.json (+ append to results/cm1/rounds.jsonl).
- Parent books the round to the i2i ledger AFTER the run (harness is pure).

## Why this round (insight bought)

The mesh's core bet is that CHEAP dedicated judgment cells make cheap
generative cells trustworthy (pincher doctrine). Round 1 buys the first
cell-level answer: does gating move accuracy at all, where does correctness
come from (gate-passed drafts vs pinched fallbacks), and what does it cost.
Later rounds vary: pinch threshold (0.3/0.5/0.7), jev-latest vs preview,
bigger GEN, stimulus families — every round booked -> Vectorize accumulates
the config-outcome geometry.
