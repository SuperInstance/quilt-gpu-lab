# CM1 r4 — Rule-Blind vs Rule-Rich Batched Gates

**Frozen pre-registration. Pushed before fire. Single factor vs r3: gate call pattern.**

## Discovery being tested
r3's semantic gates were **rule-blind**: `arm_b` built gate state as
`"Report: <report>\nDraft answer: <draft>"` — the RULE text was absent (r1 included
it: `state_text = RULE + "\n\nReport: ..."`). The gate was asked "does the draft's
DOMAIN follow the rule?" without being shown the rule. Hypothesis: this blindness,
not intrinsic conservatism, caused r3's doubting texture (9/12 correct drafts
doubted at p=0.5; 12/12 at p=0.7).

## Arms (same GEN: DeepInfra Seed-2.0-mini temp 0; same 12 stimuli; PINCH=0.5)
- **Arm A** — r3 `arm_b` verbatim at 0.5 (rule-blind, per-stimulus sequential Jev
  calls, retry loop, pinch fallback). Judgment wall-time instrumented via wrapper.
- **Arm B** — **rule-rich batched**: generate+format-fix 12 drafts, then ONE
  typesafe call with `state = {rule_canon: RULE+format spec, reports: [12×{sid,
  report, draft}]}` and 24 named noul questions (per-sid domain/urgency). Doubted
  drafts retry once (r3-style feedback), re-judged in a single second batch; still
  below threshold → pinch to keyword router. jev-quilt batching pattern (80q ≈
  flat ~0.44s latency measured by CCC 09-24).

## Pre-registered predictions (falsifiable)
- **P1 (calibration):** mean domain-noul on correct drafts, B − A ≥ +0.15.
- **P2 (flow):** B DRAFT_PASS count ≥ 8 (A replicated r3 texture: ≤ 4 at 0.5).
- **P3 (throughput):** B judgment wall < A judgment wall (24 answers ≈ 1 batch
  vs 12+ sequential calls).
- **P4 (invariant):** accuracy 12/12 both arms — accuracy never degrades under
  gating (r3 invariant).
Falsification of P1 with P2 also failing ⇒ blindness hypothesis wrong; Jev's
doubting is intrinsic ⇒ bookable either way.

## Verdict
Primary: accuracy diff B−A (bands: ≥+2 RICH_WINS / ≤−2 RICH_HURTS / else
TIE_NOISE). Secondary texture booked regardless: calibration delta, path census,
judgment wall delta, token deltas. Per-record token counts in arm B are split
evenly (gen cost is shared across the batch) — noted in output json.

## Fail-loud
- Batch response missing any of the 24 named answers ⇒ one retry ⇒ RuntimeError
  (loud FAIL booked, no silent partials).
- Arm B never invents answers: PARSE_FAIL after retry ⇒ FORMAT_PINCHED path with
  keyword_router fallback, same census semantics as r3.

## Cost
Typesafe jev-preview: ~2 batched calls (24 + ≤2×doubted questions). DeepInfra
Seed: ≤ 12 + ≤12(retries) + format retries. Wall estimate 4–8 min.
