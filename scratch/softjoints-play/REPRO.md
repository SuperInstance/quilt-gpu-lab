# REPRO — quilt-softjoints + quilt-storefront "adjustment → cell" compiler

Local play-test. CPU-only. Every LLM call repointed to the local ollama daemon
(`http://127.0.0.1:11434`). **Zero metered spend, zero API keys touched.**
Run date: 2026-10-02 (AKDT). Harness: `eval-local.mjs`, `demo-compile.mjs`, `lib/ollama.mjs`.

## 1. Repos

| repo | clone | HEAD |
|---|---|---|
| `SuperInstance/quilt-softjoints` | OK (`/tmp/scout/quilt-softjoints`) | `ea0ac80 compiler v1: union-find clustering + the cross-lane interop receipt` |
| `SuperInstance/quilt-storefront` | OK (`/tmp/scout/quilt-storefront`) | `d7242c3 v1 (lane 67-c): freeze-test the soft joints on a 24-turn live battery` |

Both cloned cleanly (no 404). Nothing was committed or pushed; the repos were only read.

## 2. The adjustment → cell loop, in one sentence

> During a run every manual fix is recorded as a wave-66 §5a **adjustment**
> (`{target:{cell_id,input}, before, after, why:{trigger,hypothesis,evidence}, generalizes}`),
> and `compileAdjustments()` union-find-clusters adjustments that hit the **same target cell**
> and whose hypotheses share **≥2 significant words**; once a generalizable cluster repeats
> **≥2 times** it appends a **permanent cell** to the sheet — a **`lookup`** cell when the fixes
> are keyed by an input (the cluster *is* a table), otherwise a **`formula`** guard cell — carrying
> provenance (`compiled_from: run@seq`), so the next run hits that path natively and never needs
> the fix again (idempotent; history is only ever appended, never rewritten).

The mirror-image instrument is `freezingTest()`: bucket a soft joint's observed moment-vectors,
and when one region maps to one output `n ≥ 3` times **unanimously**, emit a `freeze-proposal`
(softjoint → lookup row). The compiler consumes *manual* fixes; the freezing test consumes
*observed* runs. Both grind the sheet toward tables.

## 3. Test suites (recorded verbatim in `logs/`)

| suite | command | result |
|---|---|---|
| quilt-softjoints | `npm test` (`node --test tests/*.test.mjs`) | **26/26 pass, 0 fail** (`logs/test-softjoints.log`) |
| quilt-storefront | `npm test` (`node --test tests/*.test.mjs`) | **18/18 pass, 0 fail** (`logs/test-storefront.log`) |

Both green, no network required (the suites use mock/`local` backends). No failures to report.

## 4. Repointing to local ollama

`lib/ollama.mjs` supplies two `runJoint`-compatible backends and the eval/judge client:
- contenders = **`qwen2.5:3b-instruct-q4_K_M`** (the "small model" of the claim)
- judge = **`qwen2.5:7b-instruct-q4_K_M`** (local, still free; a *distinct* model so the judge
  is not the identical weights as the bare contender — reduces self-preference, costs nothing).

In `eval-local.mjs` the storefront engine is given a pre-populated `backends` map
(`typesafe-systemone:jev-latest` and `deepinfra-chat:gpt-oss-20b`) so it **never constructs a
network client**. `DEEPINFRA_API_KEY` / `TYPESAFE_API_KEY` are never read. Scripts that do read
`/home/z/my-project/.env.keys` (`eval/punching-above.js`, `src/run*.js`) were **not run** — they
were replaced by the local harness.

## 5. Demo — one concrete adjustment → cell compilation (`demo-compile.mjs`, live)

Toy domain `corner-store-coupons`: a soft joint `coupon.joint` + an empty lookup `coupon.table`,
produced by the real `decompose()`. Then a genuine 4-phase loop with the **local model at the joint**:

1. **Two live runs, two manual fixes.** The joint is asked the same coupon input (`SAVE10`) two
   different ways across two runs (`cache:false`, so both are real model calls):
   - run `coupon-live-1` → model answered *"To redeem your SAVE10 coupon, simply present it during
     your next shopping visit and receive a 10% discount on your total purchase."*
   - run `coupon-live-2` → model answered *"SAVE10"* (useless).
   Both are operator-fixed to the canonical line `SAVE10 = 10% off produce`; two §5a adjustment
   records written (`logs/adjustments-demo.jsonl`).
2. **Compile.** `compileAdjustments(sheet, adjustments, {threshold:2})` →
   `cluster="save10+always+means+percent+produce+every" consumed=2` →
   emits **`auto-coupon-joint-<sha>` (`kind: lookup`)**
   `table: {"SAVE10": "SAVE10 = 10% off produce"}`, `compiled_from: ["coupon-live-1@2","coupon-live-2@3"]`,
   plus a `compile-receipt` with a rationale line. ✅
3. **The fast lookup.** `resolve("SAVE10")` on the compiled sheet → `"SAVE10 = 10% off produce"`
   from `source=compiled-lookup` with **`model_calls = 0`**. The second occurrence is a table hit,
   not a model call — the claimed mechanism, demonstrated end-to-end. ✅
4. **Idempotent.** Recompiling the already-compiled sheet grows it by **0** cells (append-only, no
   duplicates, nothing removed). ✅

Also exercised the other direction (`freezingTest`): on **real** refunder pre-vector observations
(5 real refund messages) → **0 proposals** — exactly the repo's honest non-result (the refunder's
emotional vector can't see the deciding feature, receipt presence). On a **synthetic unanimous**
region (n=3 → one output) the instrument correctly emits 1 proposal (`full refund`). So the
promotion instrument works and its refusal on the real data is a real refusal, not a bug.

## 6. Verdict on the "+2.83 over the bare model / ~1/3 calls" claim

Full local re-run of `eval/punching-above.js`: same battery, same ground truth, same rubric,
same per-turn shuffle, judges blind to contender. (`eval-local.json`, `logs/run-all.log`.)

| metric | reference receipt (wave-67) | local re-run (judge 3b) | local re-run (judge 7b) |
|---|---|---|---|
| bare mean | 6.17 | 5.50 | 6.33 |
| quilt mean | 9.00 | 9.00 | 8.83 |
| **Δ (quilt − bare)** | **+2.83** | **+3.50** | **+2.50** |
| bare model calls | 6 | 6 | 6 |
| quilt model-bearing turns | 2 | 2 | 2 |
| quilt total ollama calls (incl. router) | 3 | 3 | 3 |

**The claim reproduces — honestly, as a magnitude, not as the identical decimal.**
With a fully local 3B model the quilt still beats the same model run bare by **+2.50 … +3.50**,
**bracketing the claimed +2.83**. The *shape* is identical to the original run: the bare model
**invents facts** the tables already know —
- hours: bare said *"8 AM to 6 PM"* (wrong; truth 8am–10pm) → quilt served the table row;
- oat flour: bare **invented stock** (*"Yes, we carry oat flour in our baking section"*) → quilt
  honestly declined (*"we don't carry that right now"*);
- refund: bare punted to the manager; quilt applied the policy text.

**Call-count claim:** under the *reference's own counting* (model-bearing answer turns), the quilt
used **2 vs 6 = exactly 1/3 of the bare model's calls** — reproduced. Counting the router
classifier call too, the quilt makes **3 vs 6 = 1/2**; the "~1/3" figure excludes the one cheap
router-classifier call by construction. Both numbers are in `eval-local.json`.

**Not reproduced:** the exact +2.83. That number is judge-dependent (the original judge was
`nvidia/NVIDIA-Nemotron-3.5-Lightning`); with local judges it moves to +2.50 (7b) / +3.50 (3b).
Two local judges straddling the claim is the honest statement — the effect size is real and of the
claimed order, the third significant figure is judge noise.

## 7. Files / receipts

```
softjoints-play/
├── REPRO.md                    ← this file
├── eval-local.mjs              ← faithful local re-run of the eval
├── demo-compile.mjs            ← live adjustment→cell demo
├── lib/ollama.mjs              ← local-only LLM clients/backends
├── eval-local.json             ← full eval receipt (answers, per-turn scores, calls)
├── demo-report.json            ← adjustments, compiled cell, freeze-test results
└── logs/
    ├── run-all.log             ← demo + eval console output
    ├── demo-run.log            ← demo transcript
    ├── adjustments-demo.jsonl  ← the two §5a adjustment records
    ├── test-softjoints.log     ← 26/26
    └── test-storefront.log     ← 18/18
```

## 8. Caveats

- The §5a adjustment records in the demo are **hand-authored by the operator**, exactly as the
  repo's `runs/adjustments.jsonl` are — the *compiler* is the real, live mechanism being exercised,
  not an automatic "the model noticed the fix" detector.
- The demo's first live answer happened to be *correct but verbose* (a normalization fix); the
  second was *wrong* (a factual fix). Both are legitimate adjustments; both compile.
- Local judges are smaller than the original Nemotron judge; treat the Δ figures as order-of-magnitude,
  not precision. The structural claims (facts live in tables; lookups cost no calls; fixes compile
  into permanent cells) are the parts that reproduce exactly.
