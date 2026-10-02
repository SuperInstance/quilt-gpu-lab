# SWEEP — `coercion-before-??` bug class (GROUNDED)

Lane DOGFOOD-ITERATORS. This is the **deterministic** sweep (`grounded_sweep.py`,
regex over `.js/.mjs/.ts` in the named roots). It was produced because MiMo's
model-authored `SWEEP.md` (see `reply_r2.txt`) cites file:line hits in files it
cannot read — its 13-BUG/26-site table is **fabricated** (see D15 for the
finding). Ground truth below.

Bug class: unary `+`/`-`/`!` or `Number()`/`parseInt()`/`parseFloat()` binds
tighter than `??`, so a missing/invalid operand → `NaN`, and `NaN ?? d` → `NaN`
(only `null`/`undefined` short-circuit `??`). `NaN` serializes to JSON `null`.

## Hits

| root | files scanned | BUG | SANE (canonical) |
|---|---|---|---|
| /home/eileen/projects/superinstance-api/src | 1 | **0** | 0 |
| /home/eileen/projects/superinstance-api/scripts | 0 (.js/.mjs/.ts) | **0** | 0 |
| quilt-edge-lab/src (pre-fix tree `edge-lab-buggy`) | 1 | **1** | 0 |
| quilt-edge-lab/tools (clone) | 1 | **0** | 0 |
| quilt-gpu-lab/experiments | 10 | **0** | 4 |

**The only real instance fleet-wide** (in the swept roots):
```
quilt-edge-lab src/worker.js:183   const quality = +body.quality_score ?? 0.5;
```
(Scanned in the PRESERVED PRE-FIX tree `workers/edge-lab-buggy/`; the read-only
clone `edge-lab/` now carries the applied patch on branch
`dogfood/promote-precedence-fix`, uncommitted, and therefore reports 0.)
→ fixed by `PATCH.diff` (MiMo's patch is CORRECT): `const quality = +(body.quality_score ?? 0.5);`
→ pinned by `PIN.mjs` + lane control `pin_promote_ref.mjs` (both: buggy → `quality_score:null`; fixed → `0.5`).

## Why superinstance-api is clean
`src/worker.js` contains **zero `??`** (grep -c = 0). Its numeric ingress uses
explicit guards, the correct idiom:
```js
function normalizeTs(v) { const n = Number(v); if (!Number.isFinite(n) || n <= 0) return nowSec(); ... }
function clampInt(v, lo, hi, dflt) { const n = parseInt(v, 10); if (!Number.isFinite(n)) return dflt; ... }
const factSurvival = args.fact_survival == null ? null : Number(args.fact_survival);
```
These are **SANE** (`Number.isFinite` guard after coercion — the complete fix).

## Canonical pattern (near-miss, SANE)
`const x = +(url.searchParams.get("k") ?? default);` — parenthesize so `??` runs
**before** the coercion. Already used correctly in edge-lab on `/bench` and `/run`.

## Limits of this sweep
- `.py` files were excluded (the `??` operator is JS-only). The Python analogue
  `int(os.environ.get("X") or d)` already has correct short-circuit ordering.
- The regex anchors a coercion to an expression start (`=` `(` `,` `:` `[` `{`
  `return`), which suppresses string-concatenation false positives; it does NOT
  catch a coercion split across lines (rare; not found here).
