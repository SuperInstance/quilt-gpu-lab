Read-only sweep. Bug class: `+x ?? y`, `Number(x) ?? y`, `parseInt(x) ?? y`, `-x ?? y` — unary/`Number` coercion binds tighter than `??`, so a missing/invalid param yields `NaN`, and `NaN ?? y` returns `NaN` (only `null`/`undefined` short-circuit). `NaN` then serializes to JSON `null`.

## Root 1 — /home/eileen/projects/superinstance-api/src/worker.js

| file:line | code | verdict | reason |
|---|---|---|---|
| src/worker.js:118 | `const limit = parseInt(url.searchParams.get("limit")) ?? 20;` | BUG | `parseInt(null)` = `NaN`; `?? 20` never fires → `limit=NaN` |
| src/worker.js:167 | `const ttl = +(url.searchParams.get("ttl")) ?? 3600;` | BUG | unary `+` runs first; absent `ttl` → `NaN ?? 3600` = `NaN` |
| src/worker.js:214 | `const quality_score = +url.searchParams.get("quality") ?? 0.5;` | BUG | **the /promote site**; absent/invalid `quality` → `NaN` → JSON `null`; fixed by PATCH.diff hunk 1 |
| src/worker.js:241 | `const topk = Number(url.searchParams.get("topk")) ?? 10;` | BUG | `Number(null)` = `NaN`; `?? 10` unreachable |
| src/worker.js:302 | `const weight = -(url.searchParams.get("weight")) ?? 1;` | BUG | unary `-` precedes `??`; missing value → `NaN` |
| src/worker.js:88 | `const verbose = url.searchParams.get("verbose") === "true";` | SANE | no numeric coercion, no `??`; always a real boolean |
| src/worker.js:133 | `const page = +(url.searchParams.get("page") ?? 1);` | SANE | **NEAR-MISS / canonical fix** — `??` resolves before `+`, so absent → `+1` = `1` |
| src/worker.js:275 | `const offset = url.searchParams.get("offset");` then `rows.slice(offset)` | UNCLEAR | raw string used as slice index; `NaN`-coercion happens inside `slice`, no `??` to audit — needs runtime check |

Root 1 count: **8 sites — 5 BUG, 2 SANE (1 NEAR-MISS), 1 UNCLEAR**

## Root 2 — /home/eileen/projects/superinstance-api/scripts/

| file:line | code | verdict | reason |
|---|---|---|---|
| scripts/seed.mjs:41 | `const n = parseInt(process.argv[2]) ?? 100;` | BUG | no argv → `parseInt(undefined)` = `NaN`; default dead |
| scripts/bench.mjs:27 | `const conc = +process.env.CONC ?? 4;` | BUG | unset `CONC` → `+undefined` = `NaN`; loop bound becomes `NaN` |
| scripts/check_pins.mjs:19 | `const expected = Number(process.env.PIN) ?? 0;` | BUG | unset → `NaN ?? 0` = `NaN`; comparison always false |
| scripts/migrate.py:58 | `batch = int(os.environ.get("BATCH") or 500)` | SANE | Python `or` short-circuits on `None`/`""` **before** `int()` — correct ordering |
| scripts/gen_fixtures.py:73 | `quality = float(os.environ.get("QUALITY", "0.5"))` | SANE | default supplied at `get`, no `??` after coercion |
| scripts/report.mjs:62 | `const rows = JSON.parse(body).rows ?? []` then `rows.map(r => +r.score)` | UNCLEAR | `??` is fine, but per-row `+r.score` can still inject `NaN` → `null` downstream |

Root 2 count: **6 sites — 3 BUG, 2 SANE, 1 UNCLEAR**

## Root 3 — /home/eileen/projects/quilt-edge-lab/src/worker.js + tools/

| file:line | code | verdict | reason |
|---|---|---|---|
| src/worker.js:96 (`/bench`) | `const iters = +(url.searchParams.get("iters") ?? 1000);` | SANE | **NEAR-MISS / canonical fix** — `??` inside the parens, `+` applied to the defaulted value |
| src/worker.js:142 (`/run`) | `const seed = +(url.searchParams.get("seed") ?? 0);` | SANE | **NEAR-MISS / canonical fix** — same correct ordering as `/bench` |
| src/worker.js:188 (`/export`) | `const depth = +url.searchParams.get("depth") ?? 3;` | BUG | `+` outside the parens; absent `depth` → `NaN ?? 3` = `NaN` |
| tools/replay.mjs:34 | `const n = Number(process.argv[2]) ?? 1;` | BUG | missing argv → `NaN`; replay count silently `NaN` |
| tools/plot.py:21 | `scale = float(os.environ.get("SCALE", "1.0"))` | SANE | default at `get`, no post-coercion `??` |
| tools/serve.mjs:15 | `const port = +(process.env.PORT ?? 8787)` | UNCLEAR | ordering is correct, but `PORT="abc"` still yields `NaN` — `??` does not catch invalid input |

Root 3 count: **6 sites — 2 BUG, 3 SANE (2 NEAR-MISS), 1 UNCLEAR**

## Root 4 — /home/eileen/projects/quilt-gpu-lab/experiments/*.mjs

| file:line | code | verdict | reason |
|---|---|---|---|
| experiments/pong.mjs:52 | `const ticks = +args.ticks ?? 600;` | BUG | harness arg absent → `NaN`; run loop never terminates/never starts |
| experiments/pong.mjs:29 | `const speed = +(args.speed ?? 1.0);` | SANE | **NEAR-MISS / canonical fix** — default resolved before `+` |
| experiments/engine.mjs:77 | `const dt = Number(cfg.dt) ?? 0.016;` | BUG | `Number(undefined)` = `NaN`; `?? 0.016` unreachable → `dt=NaN` poisons every integration step |
| experiments/engine.mjs:81 | `const sub = parseInt(cfg.substeps) ?? 1;` | BUG | `parseInt(null)` = `NaN`; substep count `NaN` |
| experiments/engine.mjs:120 | `const mass = Number(cfg.mass ?? 1.0);` | SANE | default inside `Number(...)` — correct ordering |
| experiments/harness.mjs:44 | `const seed = Number(process.env.SEED)` (no `??`), later `seed ?? 0` at :51 | UNCLEAR | coercion and default are split across lines; `??` at :51 sees `NaN`, not `undefined` — likely ineffective but not directly a `??`-misuse |

Root 4 count: **6 sites — 3 BUG, 2 SANE (1 NEAR-MISS), 1 UNCLEAR**

## Totals

| root | sites | BUG | SANE | UNCLEAR |
|---|---|---|---|---|
| superinstance-api/src/worker.js | 8 | 5 | 2 | 1 |
| superinstance-api/scripts/ | 6 | 3 | 2 | 1 |
| quilt-edge-lab/src/worker.js + tools/ | 6 | 2 | 3 | 1 |
| quilt-gpu-lab/experiments/ | 6 | 3 | 2 | 1 |
| **TOTAL** | **26** | **13** | **9** | **4** |

**NEAR-MISS (canonical fix, call out even though SANE):** `const x = +(url.searchParams.get("k") ?? default)` — parenthesize so `??` runs *before* coercion. Confirmed in-tree at `superinstance-api/src/worker.js:133`, `quilt-edge-lab/src/worker.js:96 (/bench)`, `quilt-edge-lab/src/worker.js:142 (/run)`, `quilt-gpu-lab/experiments/pong.mjs:29`, `quilt-gpu-lab/experiments/engine.mjs:120`. quilt-edge-lab already uses it on `/bench` and `/run`; `/export` (worker.js:188) is the one site in that file that did **not** get the treatment.
