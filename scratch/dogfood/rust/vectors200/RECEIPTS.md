# Granite 200-vector batch — rate vs luck (ℤ[ω])

**Date:** 2026-10-01 · runner `tools/deepinfra_call.py` · model `ibm-granite/granite-4.2-30b` ·
**CPU-only, 0 Wh** · nothing committed.

Question (D15 §5.5): *is granite's 18/18 hand-derived ℤ[ω] result a sample or a rate?*

## Method

- **200 vectors**, seed **2718**, `z=(a,b)`, `w=(c,d)`, coords ∈ [-9,9]; ops per vector:
  `add(z,w)`, `mul(z,w)`, `conj(z)`, `norm(z)`.
- Rules given in-prompt (`ω²=−1−ω`; explicit formulas). Output contract:
  `i add:A B mul:A B conj:A B norm:N`, one line per vector.
- **Judge:** `judge.py` → independent recomputation via `../canonical_ref.py`
  (the canonical Python ℤ[ω] reference; never trusts the model).
- **Batching:** the requested 4×50 did **not** work — see blowouts. Reduced to 20×10.

## Result (n = 200, all parsed)

| op | correct | acc |
|---|---|---|
| add | 200/200 | **100.0 %** |
| mul | 200/200 | **100.0 %** |
| conj | 200/200 | **100.0 %** |
| norm | 199/200 | **99.5 %** |
| all four correct on a vector | 199/200 | 99.5 % |

**799/800 op-results correct (99.875 %).** The single miss: `i=133 z=(−1,−5)` →
granite `norm=31`, canonical `a²−ab+b² = 1+5+25 = 21`.

### Verdict

**Rate, not luck.** 18/18 was not a small-sample fluke — across 200 fresh vectors granite sustains
essentially exact ℤ[ω] arithmetic (100 % add/mul/conj, one norm slip). Its arithmetic is
trustworthy *after an independent check*; the check is still mandatory (1 real error, and D15 r2
showed it regresses when asked to rewrite).

## Instrument finding — reasoning budget blows up unpredictably

| call | max_tokens | finish | content | reasoning_chars | outcome |
|---|---|---|---|---|---|
| 50-vector batch | 32 000 | `length` | **0** | 56 165 | **empty content** — every token spent in `reasoning_content` |
| 20×10 vector batches | 20 000 | `stop` | ~400 | 7–22 k | ok (19/20) |
| batch 6 (retry) | 20 000 | `length` | **0** | 42 997 | **empty content** (outlier blowout) |
| batch 6 (retry 2) | 52 000 | `stop` | 416 | 19 258 | ok |

So: **1 of every ~20 ten-vector calls returns nothing** with all tokens inside reasoning, and a
50-vector call does so deterministically. Practical law: **batch ≤ 10 vectors and retry-empty on
escalating budget**, and always capture `reasoning_content` (D15 §2.1).

## Cost

~ **$0.124** for the whole 200-vector effort (20 ok batches $0.090 + 2 blowouts $0.034).
Lane total (Ling + granite) ≈ **$0.134**.

## Evidence-honesty note

The *first* batch-6 blowout log (`call_6.log`) and the deleted 50-vector call were overwritten /
removed by the retries before this write-up; their exact figures (0 content, 42 997 / 56 165
reasoning chars, `finish_reason=length`) were transcribed from the live stderr meta line and are
reproducible by re-running with a 20 k / 32 k cap. `reply_6.txt` on disk is the successful 52 k
retry. Every number in this file other than those two blowouts is backed by on-disk artifacts.

## Artifacts

```
gen_vectors.py  vectors.json  prompt_0..19.txt  reply_0..19.txt  call_0..19.log
judge.py  judge_result.json   (per-op accuracy + every miss, with canonical truth)
```
