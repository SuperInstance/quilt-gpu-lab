# CG1 — Does the canon gate leave the oracle? (local 1.5B replication)

**Pre-registered: 2026-09-29 ~20:50 AKDT, before any run fired.**
**Source canon:** `quilt-research-canons/research/jev-gate-experiments-2026-09-29.md`
(§3 ladder, §4 shapes, §5 payoff; canon's own "what I would test next" → cross-model
agreement / portability).
**Canon claim under test:** *"The gate is a structural completeness test, not a quality
scale"* — i.e. `p > 0.7` fires when the description contains a **mechanism AND an explicit
guarantee**, and the replacement gate `min(MECHANISM, EXTERNALITY) > 0.7` separates evidence
states the composite cannot. Canon instrument: one JEV `noul` call (typesafe API).
**Question:** does any of that survive on a **local** model with no API in the loop?
If yes, fleet canon promotion becomes offline + stranger-reproducible (canon's #1 open
item). If no, "the gate is a private instrument" becomes a measured structural failure.

## Instrument

Local `Qwen/Qwen2.5-1.5B-Instruct` (HF cache, fp16 ≈3.2 GB VRAM, greedy + 3 samples at
T=0.3, mean), plus `Qwen2.5-0.5B-Instruct` as a second, smaller oracle (model-agreement
axis). Score = first number in the generation, clamped to [0,1] (`>1 and ≤100` → /100).
Prompt shapes reproduced from the canon's own text:
- **composite** — "how likely is this claim independently verifiable" (the status-quo shape)
- **mechanism** — "is there something that would physically have to break for this to be false?"
- **externality** — "could a stranger verify this with no access to this project?"
- **decomposed** — `min(mechanism, externality)` (the canon's replacement gate)
- **bare** — the claim's own guarantee asked back at it (the tautology probe)

## Tests (frozen)

- **T1 ladder (§3):** the canon's 9 monotone rungs, one clause added per rung, composite
  shape. Reproduce the curve, especially the **append-only flip**.
- **T2 saturation (§3):** rungs after the guarantee are inert.
- **T3 tautology (§4):** the bare shape scores high on a pure restatement while composite
  and min block it.
- **T4 two-axis separation (§4/§5):** does `min` block/promote the 4 evidence states
  correctly where the composite cannot? Payoff check on the canon's own 7 claims
  (M1/M4/M9/M5/M6/S1/S2) incl. the S1 signed-tag case the composite capped at ~0.700.
- **T5 model agreement:** same ladder on the 0.5B — does the *shape* of the curve survive
  a 3× smaller oracle? (Sign agreement, not absolute values.)

## Gates (frozen — all must clear for EXTERNALIZES)

- **G1 STEP:** mean(rung5) − mean(rung4) ≥ 0.4 (canon: +0.690)
- **G2 SATURATION:** |mean(rungs 6–9) − mean(rung5)| ≤ 0.15 (canon: inert)
- **G3 TAUTOLOGY:** bare(guarantee-only) ≥ 0.75 **and** composite(guarantee-only) ≤ 0.5
- **G4 MIN_SEPARATES:** min(mech,ext) ≥ 0.7 on "mechanism+guarantee" **and** ≤ 0.5 on
  "guarantee only"
- **Verdict:** `EXTERNALIZES` if G1∧G2∧G3∧G4; else `PARTIAL` (name the failing gates) or
  `ORACLE_BOUND` (G1 fails) — each names what is oracle-specific.

## Honest limits

- Prompt-level replication of a `noul` call, not the same API cell; absolutes will differ.
  The claim tested is about **structure** (step / saturation / min-separation), not values.
- 3 samples per cell at T=0.3; the canon's own phrasing-noise is ~0.10 — margin must beat it.
- 0.5B is a scale probe, not a second lineage.
