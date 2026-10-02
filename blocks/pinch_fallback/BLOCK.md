# pinch_fallback

## WHAT IT IS

The graded-confidence safety-net router: a PRIMARY path proposes an answer,
a GRADER returns graded **noul** scores (floats in [0,1], one per named
question) for the draft, and when `min(noul) < threshold` the item is
DOUBTED — exactly one retry whose prompt carries the gate complaint, and if
the retry is still doubted, the item is **PINCHED to a deterministic
known-answer path**. The pinch is booked honestly as a first-class flow
state (`DRAFT_PASS` / `RETRY_PASS` / `PINCHED_FALLBACK` / `FORMAT_PINCHED`);
a pinch is never silently absorbed. A draft the primary itself declares
unformattable never reaches the semantic grader at all (format-first) and
pinches straight to the deterministic path.

Ships with the CM1 keyword router (rule + term lists + the 12 booked boat
stimuli, verbatim from `experiments/cm1_relay.py`) as the canonical
deterministic known-answer path — including its **pre-registered negation
blind spot**: S12 ("No AIS contacts") substring-matches the motion term
`ais contact`, so the router answers `BOOK:navigation:mid` where the truth
is `BOOK:deck:low` (11/12). The blind spot is part of the receipt, not a
surprise: the residual risk of a pinch system is the fallback's own blind
spots, which is why they are declared up front.

## WHY (the booked receipts)

- **CM1 r1** (RESULTS.md, 2026-09-29) — broken 0.5b GEN: arm A ungated
  0/12 (all PARSE_FAIL); gated relay 10/12 with 11/12 PINCHED_FALLBACK —
  "the pinch path (deterministic keyword router) carried accuracy — the
  pincher doctrine PROVEN under generative-cell failure, not just in
  theory".
- **CM1 r2** — format-first: unparseable drafts never reach semantic gates;
  with the broken cell 12/12 FORMAT_PINCHED and ALL correctness came from
  the fallback. The pinch sweep was DEGENERATE (threshold never engaged) —
  booked honestly, not dressed up.
- **CM1 r3** — competent GEN: TIE_NOISE at pinch 0.3/0.5/0.7; at p0.7 the
  gates doubted 12/12 CORRECT drafts ({11 RETRY, 1 PINCHED}) and accuracy
  STILL held 12/12 — the retry+pinch net never let a wrong answer through;
  conservatism costs tokens, not accuracy.
- **RING-CX-2** (2026-10-01) — the frost law for thresholds: a threshold
  with ZERO engagements (nothing doubted, nothing pinched) exercises no
  safety net; std==0 / 0-alert degeneracy ⇒ INCONCLUSIVE, never PASS. Fix:
  the house τ doctrine — pick the threshold as the TRAIN quantile at the
  desired doubt prevalence (`pinch_threshold_for_rate`).

## INTERFACE

```python
from block import PinchFallback, sweep, pinch_threshold_for_rate,
                   PrimaryFormatError, BadScoresError

pf = PinchFallback(primary=fn,      # fn(item, feedback=None) -> draft
                   grader=fn,       # fn(item, draft) -> {name: noul in [0,1]}
                   fallback=fn,     # fn(item) -> answer  (deterministic, no model)
                   threshold=0.5,   # pinch iff min(noul) < threshold
                   retries=1,       # CM1 wiring: 0 or 1
                   seed=2718)

receipt = pf.run(item)
#   {item, answer, flow, scores: [ {q: noul}, ... ], primary_calls,
#    grader_calls, retries, pinched, threshold, wall_s}
#   flow ∈ {DRAFT_PASS, RETRY_PASS, PINCHED_FALLBACK, FORMAT_PINCHED}

corpus = pf.run_corpus(items, truth={item: correct} | None)
#   {counts: {flow: n}, engagements, accuracy?, accuracy_by_flow?, receipts}

sw = sweep(pinch_factory, items, thresholds=(0.3, 0.5, 0.7), truth=...)
#   the CM1 pinch sweep + the frost law per level:
#   engagements == 0 -> verdict "INCONCLUSIVE" (net unexercised), else "MEASURED"

tau = pinch_threshold_for_rate(train_min_scores, rate)
#   τ doctrine: the `rate`-quantile of TRAIN min-scores, so the expected
#   pinch rate on train material equals `rate`
```

Contracts: grader output is validated strictly (`{non-empty str: finite
float in [0,1]}`) — violations raise `BadScoresError`, config bugs raise
`PinchError` at construction, never a silent default. `primary` raises
`PrimaryFormatError` to declare an unformattable draft (r2 format-first
route: the grader is never called — asserted by the self-test). No
network, no subprocess, no secrets; the transport-bearing primary/grader
are injected by the caller.

## PROPERTIES

- Deterministic given its injected callables (seed 2718 default); the
  self-test proves bit-identical behavioral receipts across repeat runs
  (timing fields excluded).
- Every doubt and pinch lands in the receipt with the score history —
  "declared provenance, never a clean pass" (the r5 `served_from` ledger
  pattern; a `PINCHED_FALLBACK` count > 0 must survive into any downstream
  RESULTS.md entry).
- Zero-engagement thresholds are booked INCONCLUSIVE, never PASS (the
  RING-CX-2 frost law, the same law as `std==0 ⇒ INCONCLUSIVE`).
- The fallback is the load-bearing safety net: it ran the round in CM1 r1,
  r2 and r5 — which is exactly why its own blind spots must be declared.

## COMPOSITION

- **Upstream of `format_first_gate`**: format_first_gate parses judge
  OUTPUT before trust and pinch-handles FORMAT failures on the judge side;
  this block pinch-handles GRADED-CONFIDENCE failures on the answer side.
  In the CM1 wiring they are one pipeline: format gate first (unparseable
  ⇒ FORMAT_PINCHED straight to the router), then semantic noul gates with
  this block's doubt/retry/pinch ladder.
- **Downstream of any graded judge**: `format_first_gate`'s typed noul
  answers plug straight into `grader`; `ring_cx2`-style trained logistic
  gates (p(alert) ∈ [0,1]) are also valid noul sources.
- **The fallback can be `exact_minimax_labels`** (exact optimal-move sets)
  in game lanes: a deterministic known-answer path stronger than any
  keyword router.

## SELF-TEST

From the lab root, CPU-only, <1s:

```
python3 blocks/pinch_fallback/block.py
```

Scripted primaries/graders, no network: (0) keyword router 11/12 with the
S12 blind spot; (1) CM1 r1 broken cell — all 12 PINCHED at 0.3/0.5/0.7,
fallback carries 11/12 where ungated arm A scores 0/12; (2) r2
format-first — 12/12 FORMAT_PINCHED, grader never called; (3) r3 p0.7 —
exactly {11 RETRY_PASS, 1 PINCHED_FALLBACK}, accuracy holds 12/12, the
pinched item's fallback correct; (3b) p0.5 calm — 12 DRAFT_PASS; (4) frost
law — dead threshold INCONCLUSIVE, live threshold MEASURED; (5) τ doctrine
— quantile threshold reproduces the requested train pinch rate to 1/n;
(6) fail-loud contracts; (7) seeded determinism (behavioral receipts
bit-identical). Final stdout line is exactly one JSON object with one
top-level `"verdict"`; exit 0 iff PASS.
