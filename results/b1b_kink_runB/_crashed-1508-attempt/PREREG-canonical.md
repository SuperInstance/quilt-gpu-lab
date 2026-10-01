# B1b — KINK-HEAD: is the B1 distillation deficit representational?

Lane **B1b-KINK-HEAD**. Direct follow-up to **B1-DISTILL**
(`proposals/runs/B1-pong-law-distill.md`, verdict **KILL as stated**).
Pre-registered **2026-10-01 ~15:00 AKDT, BEFORE fire** (before any trace was
regenerated, any arm built, or any parameter trained). Frozen gates; the verdict
is booked either way (`results/b1b_kink/` + `RESULTS.md` + `QUEUE.md`).
Seed **2718**.

## What B1 left on the table (the reason this lane exists)

B1 measured, on held-out whole traces:

- frozen tol **1e-3 → 0.0568 ± 0.0088** (FAIL), but
- **step-direction agreement where the law MOVES = 1.0000, all 3 seeds, exact**;
- letter agreement **0.9213 = 1 − 0.0792**, i.e. the entire letter deficit is the
  `Δlaw == 0` deadzone fraction (7.92%) where the net emits a small non-zero;
- the agreement-vs-tolerance **curve**: `1e-3 0.0568 · 1e-2 0.6163 · 5e-2 0.8715 ·
  1e-1 0.9114 · 2e-1 0.9658`;
- a **300-epoch control** (same arch/data/seed): `1e-3 0.349 · 1e-2 0.880 ·
  **5e-2 0.9902** · 1e-1 0.9952`.

Read: the decision is exact; the deficit is **VALUE fidelity**, and 10× training
moves it only 0.057 → 0.349 at 1e-3. B1's own conclusion, restated here as the
hypothesis under test: **the residual is representational — the kinked
(deadzone/saturation) shape of the derived law is not cashable by a smooth small
tanh basis.** This lane tests that claim three ways.

## Claim (falsifiable)

Re-scored at the tolerances the *data* actually supports (below), a
**kink-capable basis** reaches **near-100% per-tick action agreement** with the
derived law on held-out traces; a smooth tanh basis does not. If no basis closes
the gap, B1's "representational" reading is wrong and the residual is something
else (booked as the finding).

## Tolerance choice — 1e-2 and 5e-2, WITH RATIONALE (frozen)

Both gates are **mean over 3 seeds ≥ 0.99 AND std > 0** (`std == 0 →
INCONCLUSIVE`, never PASS). The 0.99 bar is B1's frozen "near-100%" bar, reused
verbatim. The two tolerances:

- **τ₁ = 1e-2** — ≈1.4% of a typical full-speed step (0.70 field units). This is
  the tolerance at which B1's *own* tanh net reached **0.616**: high enough to be
  measurable well above B1's knife-edge, low enough that "near-exact values" is a
  real claim. It is the sharp gate.
- **τ₂ = 5e-2** — ≈7% of a typical full-speed step. This is the tightest
  tolerance at which B1's *own* evidence says near-100% is even plausible: its
  300-epoch control hit **0.9902** exactly here. It is the permissive gate.

**Why NOT 1e-3 (B1's frozen tolerance).** B1 measured that a 40-epoch tanh net's
own error floor is rms 0.021–0.079 — i.e. **2–8× larger than 1e-3** — and that
300 epochs (7.5× the training) moves the 1e-3 number only 0.057 → 0.349. A
tolerance below the baseline's representational floor measures *the tanh basis*,
not the distillation. Re-freezing at 1e-3 would re-ask a question B1 already
answered. 1e-3 is **still reported** for every arm (continuity with B1), but it
is **not gated**.

## Frame — reused VERBATIM from B1 (frozen; no new degrees of freedom)

Everything about the data is B1's frozen frame, unchanged:

- teacher = the **shipped** `quilt-arcade games/pong/sheet.mjs` cell `ai.track`;
  labels **executed** by the engine (Node child, list-form subprocess), never
  reimplemented in Python;
- frame **uniform-random reachable states**: both paddles driven by uniform-random
  {−1, 0, +1} (engine-driven), **240 traces**, seed `900000+i`, ≤ **1200 ticks**;
- split **held out by WHOLE trace**: `i % 5 == 0` → **48 holdout traces** (~90,930
  law actions), rest → train (192 traces);
- inputs normalized `((p−30)/30, (b−30)/30, side)`; Adam lr 1e-3; **40 epochs**;
  batch 4096; **3 training seeds 2718/2719/2720**; **CUDA**;
- Gate B (if run) uses the same h2h protocol/harness as B1.

Because the trace generator is deterministic in `(seed, rngSeed)` and both are
frozen above, regeneration reproduces B1's traces exactly; the B1
`holdout_samples.npz` is also loaded for a **bit-equality cross-check** against
the regenerated holdout (control C4, below).

## Arms (frozen) — 3 seeds each

Prediction convention (frozen for ALL arms, apples-to-apples): every arm's
Gate-A action is the **deployed** action —
`Δ_pred = clamp(p + raw_out, 6, 54) − p` — identical to how the net drives a
paddle in play and how the JS harness already acts (B1's h2h did exactly this).
Arm (a) is **additionally** reported with the raw, unclamped output (labelled
`raw`), to connect to B1's 0.616/0.872 curve; the raw column is reported, not
gated.

**(a) TANH baseline** — B1's exact net: `3→64→64→1`, `tanh` hidden, linear head,
4,481 params. Re-scored at τ₁/τ₂. **Reproduction control:** B1's curves are
re-derived from the re-trained nets.

**(b) RELU head** — identical MLP `3→64→64→1` with `nn.ReLU` in place of `tanh`,
same inputs/optimizer/epochs. Justification: ReLU nets are **piecewise-linear**;
the derived law is piecewise-linear, so a sufficiently wide ReLU net can
represent the kinks (deadzone edge, saturation) that a globally-smooth tanh
basis cannot. If the residual is representational, (b) must beat (a) at τ₁.

**(c) LEARNED-KINK head** *(my pick; justified)* — a shallow, structured
hinge-spline head on the law's own coordinate, with **learned knot locations**:

```
z = b − p ;  u = |z| ;  sg = sign(z) ;  side ∈ {0,1}
g_side(u) = b0[side] + Σ_{k=1..K} w[side,k] · relu(u − d_k)     K = 8   (learned d_k)
raw       = sg · g_side(u)
Δ_hat     = clamp(p + raw, 6, 54) − p
```

Params ≈ 2 + 16 + 8 = 26. **Justification:** the derived law restricted to
`u ≥ 1.5` is exactly `sg · min(s_side, u − 1.5)` — a monotone piecewise-linear
function of `u` with kinks at `u = 1.5` (deadzone edge) and `u = s_side + 1.5`
(saturation onset). A hinge basis `Σ w_k·relu(u − d_k)` **is the exact function
class** of that map; learned `d_k` lets the fit *find* the knots rather than be
handed them, so this is a genuine distillation (weights from data), not a law
reimplementation. It directly tests B1's stated hypothesis: the clamp is removed
from the learning problem (it is the environment's own given box constraint,
already applied by every arm and by the game), so whatever remains at τ₁/τ₂ is
**deadzone + ramp + saturation kink fidelity** — the exact residual B1 named.

## Gate A — per-tick action agreement, held-out traces (frozen)

Per arm, over the 3 training seeds, on the **held-out whole traces** only:

- `A(τ) = fraction of held-out ticks with |Δ_pred − Δ_law| ≤ τ`, for
  `τ ∈ {1e-3 (reported), 1e-2 (GATED), 5e-2 (GATED), 1e-1, 2e-1, curve}`.
- **Arm PASS** iff `mean A(1e-2) ≥ 0.99` AND `mean A(5e-2) ≥ 0.99` AND both
  `std > 0`. Any `std == 0` → **INCONCLUSIVE** for that arm (never PASS).
  Otherwise **FAIL** (the gap is the receipt).
- Lane **KEEP** (representational hypothesis SUPPORTED) iff **≥1 arm passes both
  gates**; **NEGATIVE/KILL** if none does.

## NEW — per-region agreement breakdown (frozen partition)

Every held-out tick is labelled by **law regime** from ground truth
(`META` = (p, b, side), `Y` = Δ_law), identically for every arm (arm-independent,
so the regions are apples-to-apples). With `z = b − p`, `u = |z|`,
`s = 0.85 (left) | 0.70 (right)`:

1. **clamp** — `u > 1.5` AND `p + Δ_law ≤ 6 + 1e-6` or `p + Δ_law ≥ 54 − 1e-6`
   (the law's own box clip fired). Checked first.
2. **deadzone** — `u ≤ 1.5` (law at rest, `Δ_law == 0`).
3. **saturation** — `u ≥ s + 1.5` (law at full reflex speed `±s`, unclamped).
4. **ramp** — `1.5 < u < s + 1.5` (law ∝ `u − 1.5`, unclamped).

Reported per arm: region counts (fraction of holdout) + agreement at
1e-3/1e-2/5e-2 within each region, 3-seed mean±std. **Headline metric: the
region where each arm's τ₁ residual lives** — B1 predicts (a)'s residual sits in
**deadzone** and **clamp**; the test is whether (b)/(c) collapse it there.

## Gate B — h2h vs the law (SECONDARY; run only for arms passing BOTH gates)

Identical protocol to B1: seeds `2718..2817` (100 seeds), per training seed two
matches with **sides swapped**, **win = first to 7**, `MAX_TICKS = 20000`, draws
booked and excluded. Each qualifying arm → **600 games** (3 seeds × 100 × 2), same
harness/engine. `mean ∈ [0.40, 0.60] AND std > 0` → PASS (indistinguishable);
`std == 0 → INCONCLUSIVE`. Not part of the KEEP decision (the claim is about
agreement); booked as a secondary receipt either way. The law-vs-law swapped
control runs first and must land at 0.50.

## Harness controls (§0, frozen — must pass before any Gate-A number is read)

1. **Pristine-vs-switch law equivalence** — switch `law` branch vs the pristine
   sheet's `ai.track` on 4,000 holdout states: **bit-identical** (`max|Δ| = 0`).
2. **JS-vs-torch port**, **per arm per side**, on 50,000 holdout states:
   `max|Δ_js − Δ_torch| < 1e-6`, else that arm's h2h is VOID (Gate A is torch-side
   and unaffected). B1's mixed-side defect is guarded against: every call names
   ONE side and only that side's rows are compared.
3. **Augmentation provenance** — every state/label emitted by the engine.
4. **Trace-frame cross-check** — regenerated holdout `(X, Y, META)` compared to
   B1's `holdout_samples.npz`: `max|ΔX| = 0`, `max|ΔY| = 0` required (frame
   reused verbatim). A mismatch is booked and the run is VOID for the frame claim.

## Guard + receipt (G7) — no receipt → run VOID

`Guard(task_id="B1b-kink-head", seed="2718", receipt_dir=results/b1b_kink/guard)`.
Preflight: free VRAM ≥ 1024 MiB, temp ≤ 80 °C. G7 watt receipt (`g7-watt-receipt@1`,
validator `../fleet-seeds/scripts/g7_validate.mjs`) sealed over the whole measured
window. **Device VRAM < 1.5 GB.** **Co-tenancy:** the 7B ollama seat lane
(`qwen2.5:7b-instruct-q4_K_M`, ~4.18 GiB resident) holds the card; these nets are
tiny (<65 MB peak) and run beside it. If Guard preflight shows **< 1024 MiB free**,
retry **once after 60 s**; still short → book **NOT-RUN**, honestly.

## Verdict mapping (mechanical)

- ≥1 arm PASS both gates → lane **KEEP** (kink basis cashes the residual;
  representational hypothesis SUPPORTED); name the arm(s) and the region collapse.
- No arm passes both, but ≥1 PASS at τ₂ only → lane **NEGATIVE/PARTIAL**: the
  7%-of-a-step claim holds, the 1.4% claim does not — booked with the region table.
- No arm passes any gate → **KILL**: B1's representational reading is wrong; the
  residual is not the basis (the measured per-region table is the finding).
- Any arm with `std == 0` on a gated quantity → **INCONCLUSIVE** for that arm.

## Artifacts (frozen paths, `results/b1b_kink/`)

- `run_config.json`, `traces_meta.json`, `holdout_samples.npz` (regenerated; the
  frame cross-check vs `results/b1_distill/holdout_samples.npz`).
- `model_<arm>_seed{2718,2719,2720}.pt` — 9 nets.
- `agreement.json` — Gate A per arm (+ curve + raw-output column for (a)).
- `regions.json` — the per-region partition + per-region agreement per arm.
- `h2h_<arm>.json` — Gate B, only for arms passing both gates.
- `controls.json` — equivalence + per-arm JS/torch port + frame cross-check.
- `result.json` — combined verdict.
- `RESULTS-ENTRY.md`, `guard/` (g7 receipt + guard_summary + ledger).

Code: `experiments/b1b_kink_engine.mjs` (engine harness — B1's harness plus
**additive** `kind` branches for the relu/kink forwards; the `law`/`random`
branches and the h2h/collect/labels/laweq commands are byte-identical in
behaviour), `experiments/b1b_kink.py` (driver, guard, training, both receipts).

**Do NOT commit** — the keeper commits. Other lanes' lines untouched.
