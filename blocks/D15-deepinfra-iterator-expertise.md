# D15 — DeepInfra Iterator Expertise Record (lane DOGFOOD-ITERATORS)

**Date:** 2026-10-01 · **Directive (Casey 17:35):** *"pick a few of your deepinfra
iterator models to dog-food to expertise for niche development where your systems
need it."*

**Method.** Four DeepInfra models were driven against **real niche work products**
(not benchmarks), ≥2 rounds each, temperature 0, with a lane-side ground-truth
harness that either *compiles* (Rust/`cargo`), *runs* (`lua5.1`/`luac`,
`node`), or *independently recomputes* (`scipy`, hand-derived ℤ[ω] reference).
Runner: `tools/deepinfra_call.py` (list-form subprocess, runtime token, retry-once,
fail-loud). All work in `scratch/dogfood/`. **CPU-only, 0 Wh. Nothing committed;
the edge-lab patch stays local (branch `dogfood/promote-precedence-fix`,
uncommitted). Total DeepInfra spend ≈ **$0.030**.

The point is *expertise from use*: what each model is **reliably good at** and
**where it needs supervision**, established by a verifier that can say no.

---

## 1. Verdict table

| model | niche seat | expertise | one-line evidence |
|---|---|---|---|
| **ibm-granite/granite-4.2-30b** | Rust / exact ℤ[ω] | arithmetic **5/5** · Rust hygiene **2/5** | 18/18 hand-derived ℤ[ω] vectors correct (0 diverge vs canonical Python), but its Rust module failed to compile (4 errors) and its round-2 rewrite broke `conj`/`mul`/`norm` (4 of 9 own tests fail) while claiming "all pass". |
| **inclusionAI/Ling-3.0-flash** | Luau / Roblox | **4/5** | typed `--!strict` pong-law module + self-contained `lua5.1` harness; after 1 correction round **PASS 22/22**, `luac -p` clean. Round-1 had 3 wrong test *oracles* (law was right). |
| **XiaomiMiMo/MiMo-V2.6-Flash** | TS / CF Workers | patch+pin **5/5** · sweep **1/5** | `PATCH.diff` + `PIN.mjs` reproduced the `/promote` NaN→null bug and verified the fix end-to-end under node; but its `SWEEP.md` **fabricated 13 BUGs across 26 sites** in files it cannot read (grounded truth: **1**). |
| **nvidia/NVIDIA-Nemotron-3.5-Lightning** | stats / adjudication | catch **4/5** · precision **2/5** | independently diagnosed the inverted Clopper–Pearson bisection with the ordering argument + the exact wrong numbers (lower≈0.9843, upper 0.0 for 38/40); but in round 1 declared `guard.py` "CLEAN" without ever seeing it, and round 2 over-called (5–6 false positives). |

---

## 2. Lane details

### 2.1 RUST — granite-4.2-30b (`scratch/dogfood/rust/`)

**Ground truth:** `canonical_ref.py` (independent ℤ[ω], hand-derived from
ω² = −1−ω) + `canonical_vectors.json`; control crate `rscheck/` wraps the **real**
`slackwater-rust/crates/lattice-core/src/eisenstein.rs` via `#[path]`.

- **Round 1 — VECTORS (excellent).** 18 vectors / 8 ops (add, sub, mul, conj,
  norm, hexdist, div_rem incl. the ±0.5 half-away-from-zero rounding edges,
  rotate_60_omega) → **18/18 agree with the canonical Python reference, 0 diverge.**
  It even nailed `rotate_60_omega(1,2) = (−2,−1)` (true ω-mult is `(−b, a−b)`).
- **Round 1 — RUST (fails).** The test module **does not compile** (rustc 1.97,
  edition 2021): `E0425` `max` out of scope (`use std::cmp::max` at file top,
  `hexdist` inside a nested `mod`), `E0277` `i64*i32` in `norm`, `E0308`, and
  `E0277` `E12: Display` (used `{z}` not `{z:?}`).
- **Round 2 — REGRESSION.** Given the 4 errors, granite *rewrote* the module,
  ignoring "keep the 18 verified vectors verbatim" (it replaced them with a bare
  point list) and **broke the math**: `conjugate` → `(a, −b)` instead of `(a−b, −b)`;
  `mul` dropped the `− b·d` term; `norm` asserted 15 for a value whose own comment
  computed 19. Result: **4 of 9 own tests FAIL** (`norm` 19≠15, `hexdist` 2≠1,
  `norm_mult` 63≠171, and its *own* identity test catches its buggy `rotate_60`).
  Its NOTES claimed "all tests pass" — **false.**
- **Real catches surfaced in slackwater-rust (compiled, run):**
  - **BUG-1** `EisensteinPoint::rotate_60` returns `(a−b, a)` but its own docstring
    derives `(−b, a−b)`; it is **not** multiplication by ω (e.g. `(1,0) → (1,1)`,
    true ω is `(0,1)`). Caught by control test `bug1_*` and by granite's own identity test.
  - **GAP-1** `EisensteinPoint` has **no `mul`/`div_rem`/`gcd`** — the ring is only
    partially implemented; the canonical ring vectors therefore cannot run against it.
- **Instrument finding.** granite is reasoning-heavy on DeepInfra: at
  `max_tokens=8000` it returned **empty content** (`finish_reason=length`, all
  8000 consumed *inside* `reasoning_content`); at 24000 it emitted 9.7 k chars
  after **50.8 k chars** of reasoning (≈21 k completion tokens). Round 2 used
  35.4 k reasoning chars. **Budget ≥ 24 000, and always capture
  `reasoning_content`.**

**Seat:** vector/oracle *generator* with a mandatory compile+test gate. Never
trust its Rust or its self-report; trust its arithmetic after independent check.

### 2.2 LUAU — Ling-3.0-flash (`scratch/dogfood/luau/`)

**Task:** the suspended-Kimi navigation seat — the pong law (track/clamp,
deadzone 1.5, per-side speeds 0.85/0.70; W1 wall reflect; W2 paddle return;
W3 score) as a typed Luau module for the Roblox bridge + a `lua5.1`-checkable harness.

- **Round 1.** Law code **behaviourally correct** and `luac -p` clean, but the
  harness ran **30/33 — 3 failures, all wrong test *oracles*** (`track(30,60)`
  expected 34.5; the law caps the step at `speed` → 30.85; likewise the two
  "clamp" cases). The law never left `[6,54]`.
- **Round 2 (2b).** After feeding it the exact failing output: **PASS 22/22**,
  `luac -p` clean, self-contained (no `require`), full typed `--!strict` module
  restored (`export type`, `export function`), including the exact-deadzone
  boundary (|d| = 1.5 → no move) and the exact band-edge landing on 54.0.
- **Supervision needed:** (a) numeric *expectations* (3 wrong in round 1 — it
  under-modelled the step cap); (b) round 2 *collapsed* sections when not
  re-anchored; (c) it **overclaimed** "both LUAU_MODULE and LUA_TEST pass
  `luac -p`" — the Luau module has types, `luac` rejects it (only the harness is
  Lua-5.1-clean). Law itself needed **zero** corrections.

**Seat:** standing Luau/Roblox author, with a test-oracle review pass and a
"don't claim a check you didn't run" rule.

### 2.3 WORKERS — MiMo-V2.6-Flash (`scratch/dogfood/workers/`)

**Task:** fix `quilt-edge-lab` `POST /promote` (`const quality = +body.quality_score ?? 0.5;`
— unary `+` binds tighter than `??`; absent field → `NaN` → JSON `null`) and pin it.

- **Round 1 — patch + pin (excellent).** `PATCH.diff` correct
  (`+(body.quality_score ?? 0.5)`). Its `PIN.mjs` (node ESM, in-memory
  RECEIPTS/SAVES/DB mock, `--against-buggy` mode) was **verified by the lane**:
  against the fixed worker → `PIN-PASS quality_score=0.5`; against the pre-fix
  worker → `BUG-REPRODUCED quality_score=null`. Lane control `pin_promote_ref.mjs`
  agrees. Repo cloned read-only; patch applied **uncommitted** on branch
  `dogfood/promote-precedence-fix`. **No push.**
- **Round 1 defect:** hit the 6000-token cap (3600 reasoning) and truncated `SWEEP.md`.
- **Round 2 — SWEEP is FABRICATED.** Asked to finish the sweep, MiMo emitted a
  confident table of **13 BUGs across 26 sites** with file:line in
  `superinstance-api/src/worker.js`, `scripts/`, the edge-lab clone and
  `experiments/*.mjs`. **A model on the API has no filesystem access.** The
  deterministic lane sweep (`grounded_sweep.py` → `SWEEP-grounded.md`) finds:
  `superinstance-api/src` = **0** (the file contains **zero `??`** and uses the
  correct `Number.isFinite` after coercion), `scripts` = 0, `experiments` = 0 BUG
  / 4 SANE, and **exactly one real BUG fleet-wide**: the `/promote` line it already
  fixed. Every other cited line is invented.
- **Supervision needed:** MiMo is trustworthy on a *concrete artifact it can
  reason about* (given the code inline) and useless-to-dangerous on "sweep the
  codebase". Sweeps must be **deterministic tools**; the model reviews the output.
  Raised budget to 9000 for round 2 (it still spent 1790 reasoning tokens).

**Seat:** conditional CF-Workers seat for *single-file fix + node regression pin*
(its pin was production-grade), under the hard rule **"never ask it to sweep"**.

### 2.4 STATS — Nemotron-3.5-Lightning (`scratch/dogfood/stats/`)

**Task:** audit `c1b_adjudicate.py` / `c1b_finalize.py` CP, `comp2_corpus_gate.py`
gate, `guard.py` bootstrap/energy for the inverted-bounds / wrong-tail /
off-by-one bug class; produce a checklist + catches.

- **Round 1 — the catch (real).** Independently diagnosed the **inverted
  Clopper–Pearson bisection**: `if binom_cdf(k-1,n,mid) > alpha/2: lo = mid`
  walks the wrong way / targets the wrong tail; it names the wrong numbers
  (lower ≈ 0.9843, upper 0.0 for 38/40) — matching the lane's `verify_cp.py`
  against `scipy.stats.beta.ppf` (truth `[0.8308, 0.9939]`). Correctly confirmed
  `c1b_finalize.py` **CLEAN** (matches scipy to 1e-6; the true fix lives there —
  `c1b_adjudicate.py` is the legacy superseded helper).
- **Round 1 defect:** declared `comp2_corpus_gate.py` and `guard.py` **CLEAN**
  — *without their source in the prompt*. Hallucinated verification.
- **Round 2 — source-grounded but low precision.** Given the real code it
  answered the numbered questions and — good — used **`NEEDS SOURCE:`** rather
  than inventing (e.g. flagged the `best.nm` attribute it could not see; real code
  is `best["knobs"]["near_miss"]`). But it **over-called**: it labelled the safe
  `min(sl[0][0], w_t0)` bound, the *declared* `gpu_s = wall` fallback, the
  *intended* `full_std > 0` degeneracy guard, and the empty-window append as
  "BUG". Genuine value: rounded-joules aggregation drift (RISK, tiny, ≤2% by
  design) and left-endpoint `gpu_seconds` bias (already commented).
- **Reusable output:** `CHECKLIST.md` (20 items, grouped Bounds&Tails /
  Bisection&Search / Indexing / Degenerate / Integration / Verdict-Inversion).

**Seat:** audit *hypothesis generator* behind a triage filter (batched, CPU, cheap);
never a verdict. Precision ≈ 1 real : 5 false positives in "find bugs" mode.

---

## 3. The supervision ledger (where each needed hand-holding)

| model | needed | did not need |
|---|---|---|
| granite | token budget ≥ 24 k; compile gate; **re-anchor "keep verified artifacts" each round**; distrust self-reports | generating correct exact-integer arithmetic & rounding-edge cases |
| Ling | test-oracle review (numeric expectations); explicit "emit all sections"; check-claim policing | writing correct law logic & idiomatic typed Luau |
| MiMo | grounded tool output for any *sweep* (never free-recall a repo); bigger token budget | a single-file fix + a runnable regression pin |
| Nemotron | a triage pass on its BUG calls; source must be in-prompt | the ordering/tail argument on a bisection; flagging unknowns |

**Cross-cutting law learned (propose to AGENTS/TOOLS):** *models reason; tools
verify.* Any "audit/sweep/review a codebase" ask must be a **deterministic scan
whose output is pasted in** — otherwise the model confabulates confidently
(MiMo 13 fabricated BUGs; Nemotron "CLEAN" on unseen source). Every generated
numeric artifact (vectors, test oracles, interval bounds) gets an **independent
recomputation** before it is trusted (granite r1 good → r2 bad; Ling r1 oracles bad).

## 4. Standing seat

**Ling-3.0-flash earns the standing niche seat — the Luau/Roblox navigation seat
vacated by the suspended Kimi lane.** It is the only model whose *final* artifact
is both functionally correct (22/22), syntactically clean (`luac -p`), properly
typed, and self-contained, and whose failures are cheap (oracle arithmetic) and
were corrected in one round with the law untouched.

**Runner-up (conditional): MiMo** for a CF-Workers *fix + regression-pin* seat —
its patch and node pin were the single most operationally-correct deliverable of
the lane — gated by the standing rule that it never performs a free-form sweep.

## 5. Open questions / next

1. **Stand up the Rust conformance block.** The compiled control already catches
   BUG-1; wire it into `blocks/parity_harness` ("cross-implementation
   conformance") as an arm and file the `rotate_60` bug + `mul`/`div_rem` gap
   upstream (no push; keeper-gated).
2. **Fix the legacy `c1b_adjudicate.py`** or delete it in favour of
   `c1b_finalize.py` (it is still on disk inverted; superseded but footgun-y).
3. **Do the other 12 MiMo-"found" sites exist?** No — confirm the grounding rule
   by having a *tool* (not a model) own the next fleet sweep.
4. **Does Ling hold the Luau seat across a second, unrelated module** (not pong)?
   Give it the Roblox bridge's actual cell API next; that is the real seat test.
5. **Granite as oracle-at-scale:** batch 200 ℤ[ω] vectors through granite with a
   canonical-check harness — is 18/18 a sample or a rate?

---
*Artifacts: `scratch/dogfood/{rust,luau,workers,stats}/`, README.md.
Ground truth: `canonical_ref.py`, `verify_cp.py`, `grounded_sweep.py`, `cargo`,
`lua5.1`, `node`. Nothing committed.*
