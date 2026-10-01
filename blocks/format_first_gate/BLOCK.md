# format_first_gate

## WHAT IT DOES

A judge-answer gating layer: one batched call asks a frozen list of named
questions about a state, and this block decides — strictly, before trusting any
content — whether the judge's answer batch may be used, and on what terms.

Ported from the CM1 relay rounds (experiments/cm1_relay_r4.py, cm1_relay_r5.py)
and the batched judge wrapper (tools/typesafe_batch.py). The r4 lesson it
encodes: **rule-blind gates fabricate doubt**. When the RULE text was missing
from gate state, a competent judge doubted 9/12 correct drafts and the flow
degraded to {3 DRAFT_PASS, 6 RETRY_PASS, 3 PINCHED_FALLBACK} at 6.9s judge wall
over 18 calls; the rule-rich ONE-CALL batched gate (24 named questions, canon in
state) went {12 DRAFT_PASS} in 0.28s with 4.5x fewer judge input tokens and
higher calibration — same 12/12 accuracy. r5 then proved the recipe transfers
across a judge swap, and that judge-STATE size (not draft quality) degrades
judgment when batches over-dilute.

Five behaviors, all first-class:

1. **FORMAT-FIRST** — the batch is parsed strictly before any trust: every
   named question present exactly once, each value coercible to its declared
   type (noul/bool/int/float/str), no extras, no prose tolerance. A response
   that is not strict JSON with exactly the asked keys is a format failure,
   full stop — content is never half-trusted.
2. **RETRY-ONCE** — a format failure (or transport error) triggers exactly one
   structured re-ask, pinched to the complaint (the re-ask carries a
   `FORMAT_COMPLAINT`/`TRANSPORT_COMPLAINT` naming what was wrong). Never an
   infinite loop: at most 2 judge calls per `run`.
3. **PINCH-TO-FALLBACK** — persistent format failure falls back to a
   deterministic local fallback answer per unanswered question, and the pinch
   is booked honestly in the receipt: per-question flow `PINCHED_FALLBACK`,
   `pinched: true`, plus the carried error string. Not a silent degradation.
4. **Flow-state receipt** — per-question flow ∈ {DRAFT_PASS, RETRY_PASS,
   PINCHED_FALLBACK} + aggregate counts + judge_calls + retries + wall_s +
   token counts when the judge reports usage + error.
5. **Fail loud** — judge transport failure after retry-once (even with a
   fallback configured — a dead transport is not a format problem), or
   unparseable-after-retry with no fallback configured, raises `GateError`
   carrying the partial receipt. Never a silent pass.

Also ports the calibration scorer used in CM1: `mean_agreement(gold, answers)`
= mean 1.0/0.0 agreement with gold labels over the shared question names
(None on empty overlap, booked honestly).

## INTERFACE

```
Gate(questions, fallback=None, judge=None, seed=2718)
```

- `questions` — frozen at construction. A `list[str]` (auto-wrapped as `noul`
  questions keyed by the string) or a dict `{name: {type, question,
  instructions}}` in the proven typesafe_batch shape. `type` ∈ {noul, bool,
  int, float, str}; `noul` = float in [0,1], finite (the CM1 gate-score type).
  Names must be unique and non-empty; anything else is a construction-time
  ValueError (config bugs fail before any judge call).
- `fallback` — `Callable[[qname], value] | None`. Deterministic local answer
  for unanswered questions after a persistent format failure. The value is
  coerced to the question's declared type; a fallback that fails coercion
  raises GateError (never books a garbage answer). `None` → fail loud instead.
- `judge` — injected `JudgeClient`: an object with
  `.batch(state, questions, feedback=None)` or a plain callable with the same
  signature. May return a `JudgeResponse`, a wire dict `{"answers": {...},
  "usage": {"input_tokens", "output_tokens"}, "_wall_s": ...}` (proven
  typesafe shape, answers may be `{qname: {"noul": 0.77}}` or bare values), or
  a JSON string of the same. May raise on transport failure. **This block
  ships no transport**: no network, no secrets, no tokens — the judge is
  injected by the caller. A real transport must use list-form argv
  (list-form curl / urllib), never `shell=True`, and must never print or copy
  API tokens.
- `seed` — house default 2718, stored on the gate. The block is deterministic
  given its judge; the seed is reserved for downstream stochastic extensions.
  House rule carried for consumers: std==0 across repeats ⇒ INCONCLUSIVE,
  never PASS (see tools/verdict_gate.py DEGENERATE class) — determinism here
  means any real signal comes from the judge, not this layer.

```
receipt = gate.run(state) -> GateReceipt
```

- `state: str | dict` — passed through verbatim to the judge (r4 put the RULE
  canon + reports object here; r5 the per-cell roster). One `run` = at most 2
  judge calls (initial + retry-once).
- `GateReceipt` fields (all JSON-serializable via `.to_dict()`):
  `answers {qname: typed value}`, `flow {qname: state}`, `counts` (all three
  states, zero-filled), `retries` (0 or 1), `pinched: bool`, `judge_calls`,
  `wall_s` (measured, seconds), `tokens_in` / `tokens_out` (summed over calls
  when the judge reported usage, else None), `error` (None on success; on
  PINCHED_FALLBACK the persistent complaint is carried for honest booking).

Exceptions: `GateError` (transport-after-retry, no-fallback-after-retry,
fallback-coercion failure) carries `.receipt`. `FormatComplaint` (internal)
signals strict-parse rejection and is never raised across `run`'s boundary —
it is converted into the retry or the booked pinch.

```
mean_agreement(gold, answers, tol=1e-9) -> float | None   # alias: calibration
```
1.0/0.0 per shared key; bools never equal ints; floats compare within tol;
empty overlap → None.

## THE RECEIPT

Provenance numbers (verified against the committed artifacts):

- **CM1 r4 (2026-09-29)**, `results/cm1/round_004_out.json` (read directly):
  Arm A rule-blind @0.5 — 12/12 correct but flow {3 DRAFT_PASS, 6 RETRY_PASS,
  3 PINCHED_FALLBACK}, judge 6965/702 tokens, judge wall 6.92s over 18 calls,
  calibration 0.648. Arm B rule-rich batched (24 named noul questions, ONE
  call, RULE canon in state) — 12/12, flow {12 DRAFT_PASS}, judge 1559/490
  tokens, batch wall 0.28s, calibration 0.767. Accuracy TIE_NOISE (diff +0);
  P1 direction +0.119 calibration confirmed but missed the frozen +0.15 band
  by 0.031 — booked honestly. 25x judge-wall, 4.5x judge-input-token
  reductions. Round wall 414.3s. Hypothesis pushed pre-fire
  (CM1-r4-plan.md, 7a388a3).
- **CM1 r3 (2026-09-29)**, RESULTS.md: TIE_NOISE at pinch 0.3/0.5/0.7 —
  competent GEN holds; gates cost without benefit and never hurt (doubt rose
  to 12/12 at p0.7 yet accuracy held). 780.8s wall.
  `results/cm1/round_003_out.json` (numbers cited from the RESULTS.md entry,
  not re-derived here).
- **CM1 r5 (2026-09-30)**, farm-fed, 350.9s wall — judge swap jev-preview →
  jev-latest + 3-cell roster, artifact `results/cm1/round_005_out.json` (key
  fields re-verified): H2 TRANSFERS — Arm A 12/12 all DRAFT_PASS, jev
  1595/562, batch wall 0.32s; H1 KEEP (bar ≥11) — Arm B 11/12 but all 12
  records DOUBTED_PINCH, served_from {c0:7, c1:3, c2:1}; H3 ROSTER_HURTS, 3x
  token cost (4770/1678). Controlled finding: identical Seed drafts passed the
  12-report/24-question state and failed the 36-report/72-question state —
  jev-latest judgment degrades with judge-state size; "80q ≈ flat latency"
  holds for latency, not judgment quality. Pinch-fallback carried a round for
  the third time (CURL-1 r1, CM1 r1, CM1 r5): the deterministic router is the
  load-bearing safety net — which is why PINCHED_FALLBACK is a first-class,
  honestly-booked state here, not a silent fallback.

This block reproduces the r4 arm-B gate mechanics standalone (strict named
parse, retry-once, pinch-to-fallback, flow receipt, token ledger) minus the
network; it does not re-run any judge.

## COMPOSITION

- **Upstream — any batched judge transport plugs into `JudgeClient`.** The
  proven transport is `tools/typesafe_batch.py` (`tsafe_batch(state,
  questions)` → wire dict with `answers`/`usage`/`_wall_s`); an adapter is a
  one-liner: call it inside a `.batch(state, questions, feedback=None)` and
  fold `feedback` into the transport's feedback channel (e.g. append to state
  or a feedback field). The question spec dict this gate hands over is exactly
  the typesafe question format, so no translation layer is needed. Transport
  contract injected here: list-form subprocess/argv only, never `shell=True`;
  tokens read at use-time from the caller's own secret store and never
  printed, copied, or embedded.
- **Downstream — adjudication.** `GateReceipt.answers` (typed, trusted only
  after format-first) feeds a verdict/adjudication layer over the answers
  dict, e.g. `tools/verdict_gate.py`'s `finalize(gates=[Gate(name, value,
  minimum=...)], stats={...}, completeness=..., status_source=...)` — its
  lattice (VOID / DEGENERATE / INCONCLUSIVE / FAIL / PASS) is where this
  block's house rule lands: std==0 across repeats ⇒ never PASS. A pinch-aware
  adjudicator should treat `counts[PINCHED_FALLBACK] > 0` as declared
  provenance (the r5 served_from ledger pattern), not as a pass.
- **Downstream — receipts.** `GateReceipt.to_dict()` (wall_s, tokens_in/out,
  judge_calls, flow counts, pinched, seed-adjacent metadata) is the cost/provenance
  payload a g7-style wrapper folds into a `g7-watt-receipt@1` document
  (schema seen in results/b1b_kink/guard/g7-wr-*.json: task_id, energy,
  cost, determinism/seed=2718, gate/verdict). Contract: the wrapper consumes
  the receipt dict verbatim; `error != None` or `pinched: true` must survive
  into the wrapped receipt untruncated.

## SELF-TEST

Command (from the lab root, CPU-only, ~0.05s):

```
python3 blocks/format_first_gate/block.py
```

Scripted fake judges, no network: (a) always well-formed → all 24 questions
DRAFT_PASS, zero retries, exactly ONE judge call for N=24, tokens 130/41
booked; (b) malformed once (missing key + out-of-range noul + extra prose) then
well-formed → all RETRY_PASS, exactly one re-ask, and the re-ask carries a
FORMAT_COMPLAINT naming the missing key and the extra; (c) persistently
garbage → all PINCHED_FALLBACK with fallback answers, pinched booked with the
carried error, and the no-fallback configuration raises GateError whose
`.receipt` shows judge_calls=2; (d) transport error → GateError even with a
fallback configured, plus transport-then-wellformed → RETRY_PASS; (e)
calibration 0.8 on a 5-item gold set, None on empty overlap, bool≠int strict.
Also asserts the r4 ordering lesson is representable (one call for N
questions), the seed defaults to 2718, and repeat runs are deterministic.

Final stdout line is exactly one JSON object with exactly one top-level
`"verdict"` field; exit 0 iff PASS. Expected: `{"verdict": "PASS"}`.
