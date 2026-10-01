# B1b-KINK-HEAD — is B1's value-fidelity deficit representational?

Follow-up to **B1-DISTILL** (KILL at frozen 1e-3). Pre-registration FROZEN before
fire: `proposals/runs/B1b-kink-head.md` (2026-10-01 ~14:57 AKDT). Seed **2718**.
No commit (keeper commits).

## ⚠ Orchestration defect (booked — the fleet's, and one of mine)

**Two independent B1b subagents were dispatched concurrently** and both targeted
`results/b1b_kink/` with `task_id="B1b-kink-head"` and the same `guard/`. The
sibling lane (`experiments/b1b_kink_head.py`, 300-epoch design) self-paused to
deconflict, published `results/b1b_kink/LANE-CLAIM.md`, and resumed there as sole
writer at 15:10. **This receipt was moved to `results/b1b_kink_runB/` to honour
that claim and avoid a two-writer clobber of one gate's artifacts** — a booked
deviation from this lane's frozen artifact path, not a silent one.

Also booked (mine): the **first fire (15:04–15:08) crashed on my own bug** — the
JS↔torch port control compared a per-side JS vector (25,000) against the
full-length torch vector (50,000) → `ValueError: operands could not be
broadcast`. Guard sealed it `g7-wr-b1b-kink-head-1790896121` **VOID**, preserved
in `results/b1b_kink/guard/`. Fixed (`[sel]` indexing), re-fired. **No gate,
constant, tolerance, frame, split, or arm changed between crash and re-fire.**

## Verdict — **KILL on the frozen claim** (no arm clears either tolerance gate)

Gate A on held-out whole traces, mean±std over training seeds 2718/2719/2720.
PASS requires mean ≥ **0.99** at BOTH τ₁=**1e-2** and τ₂=**5e-2**, with std > 0.

| arm | 1e-3 (reported) | **1e-2 (gate)** | **5e-2 (gate)** | verdict |
|---|---|---|---|---|
| (a) tanh `3-64-64-1` (4,481p) | 0.0991 | 0.6136 ± 0.0783 | 0.8891 ± 0.0351 | FAIL |
| (b) relu `3-64-64-1` (4,481p) | 0.2303 | 0.8701 ± 0.0267 | 0.9192 ± 0.0388 | FAIL |
| (c) learned-kink hinge spline (26p) | 0.0920 | 0.4684 ± 0.2189 | 0.7659 ± 0.0283 | FAIL |
| control: tanh, **B1's exact recipe** | 0.0586 | 0.6181 ± 0.0458 | 0.8731 ± 0.0231 | FAIL |

**Reproduction control:** the control arm (B1's exact recipe — raw MSE, raw eval)
lands at **0.0586 / 0.6181 / 0.8731** vs B1's published **0.0568 / 0.6163 /
0.8715** (max |Δ| = 0.0018). B1's curve is reproduced. Full curves:
tanh {"1e-06": 0.0021, "0.0001": 0.0131, "0.001": 0.0991, "0.01": 0.6136, "0.05": 0.8891, "0.1": 0.9231, "0.2": 0.973};
relu {"1e-06": 0.0023, "0.0001": 0.026, "0.001": 0.2303, "0.01": 0.8701, "0.05": 0.9192, "0.1": 0.9507, "0.2": 0.9841};
kink {"1e-06": 0.0035, "0.0001": 0.0119, "0.001": 0.092, "0.01": 0.4684, "0.05": 0.7659, "0.1": 0.8044, "0.2": 0.8745}.

**Gate B (h2h vs the law, ≥600 games): NOT RUN** — the frozen rule is "run only
for arms that clear BOTH gates"; none did. Booked, not silently skipped.

## NEW — per-region agreement (law-regime partition, arm-independent)

Partition from law ground truth (`u = |b−p|`, `s` = 0.85 left / 0.70 right):
**clamp** = u>1.5 and the law's own box clip fired · **deadzone** = u≤1.5 ·
**saturation** = u≥s+1.5 · **ramp** = 1.5<u<s+1.5.
Holdout n = 90,930: clamp 114 (0.13%) ·
deadzone 7,090 (7.80%) · **saturation
80,372 (88.39%)** · ramp 3,354 (3.69%).

Agreement @1e-2 (3-seed mean):

| region (n) | (a) tanh | (b) relu | (c) kink | ctrl B1-exact |
|---|---|---|---|---|
| clamp (114) | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| deadzone (7,090) | 0.1701 | 0.1701 | 0.0276 | 0.0930 |
| saturation (80,372) | 0.6759 | 0.9654 | 0.5248 | 0.6879 |
| ramp (3,354) | 0.0442 | 0.0618 | 0.0309 | 0.0420 |

Agreement @5e-2 (3-seed mean):

| region | (a) tanh | (b) relu | (c) kink | ctrl B1-exact |
|---|---|---|---|---|
| clamp | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| deadzone | 0.4055 | 0.4951 | 0.0276 | 0.3313 |
| saturation | 0.9596 | 0.9815 | 0.8564 | 0.9490 |
| ramp | 0.2196 | 0.3205 | 0.1511 | 0.1964 |

**Headline:**

1. **clamp is 1.0000 for every arm at every tolerance** (n=114) — the
   deployed convention `Δ = clamp(p+raw, 6, 54) − p` hands the box constraint to
   the environment, so this region carries no residual. The deficit is not here.
2. **saturation (88.4% of all ticks) is where the basis change pays:**
   relu **0.9654** @1e-2 vs tanh
   **0.6759** (**+0.2895**); at
   5e-2 relu 0.9815 vs tanh 0.9596. Because
   saturation is ~88% of the holdout, this one region accounts for relu's entire
   aggregate gain (0.8701 vs 0.6136 @1e-2 = +0.2565).
3. **deadzone and ramp are unmoved by ANY basis at the frozen 40 epochs** — no
   arm exceeds 0.50 in either region at any tolerance. B1's diagnosis that the
   deadzone is a failure locus is confirmed; a 40-epoch basis swap does not fix it.
4. **arm (c) defect (mine, booked):** the kink head's deadzone agreement is
   **flat 0.0276 at 1e-3, 1e-2 and 5e-2 on all 3 seeds** — the
   signature of a *constant offset*, not of noise. `raw = sign(z)·(b0[side] +
   Σ w_k·relu(u−d_k))`: with every hinge inactive inside the deadzone,
   `raw = sign(z)·b0`, so the head is exactly right only where `z == 0`
   (sign()=0) — precisely the 2.76% it scores. Adam left
   `b0 ≈ 0.03–0.05` after 40 epochs. The hinge class *can* represent the deadzone
   (set `b0=0`, all `d_k ≥ 1.5`); the optimizer did not find it. So arm (c)'s
   loss is a **parameterization + short-schedule defect of my arm**, not evidence
   against a kink basis.

## Controls (all PASS)

1. **Frame reused verbatim (C4):** regenerated holdout vs B1's
   `results/b1_distill/holdout_samples.npz` → `max|ΔX| = 0.0`, `max|ΔY| = 0.0`
   over 90,930 rows; 240 traces / 48 holdout / 366,346 train rows, same as B1.
2. **Pristine-vs-switch law equivalence (C1):** 4,000 holdout states,
   `max|Δ| = 0`, 0/4000 differ (bit-identical).
3. **JS↔torch port (C2), per arm per side:** gated on the **float64-vs-float64**
   comparison — the JS harness evaluates in float64, so this isolates *formula
   identity* (what h2h actually runs): max |Δ| = 1.3e-15 … 4.2e-15, all ≪ 1e-6.
   The float32 reference is reported alongside (1.3e-6 … 2.5e-6). B1's mixed-side
   defect class is avoided: every call names ONE side and only that side's rows
   are compared.
4. **Provenance:** every state and every label emitted by the engine (Node child,
   list-form subprocess), never reimplemented in Python.

## Receipts / energy / artifacts

- **G7 receipt `g7-wr-b1b-kink-head-1790896473`** — `g7-watt-receipt@1`, gate
  **PASS**, validator exit 0, `source: measured`.
- Energy **11,097.46 J = 3.0826 Wh**, **190.50 GPU-s**, $0.000709 @
  $0.23/kWh. Preflight clean (1,338 MiB min free ≥ 1024 floor; max temp 76 °C ≤ 80).
  **Co-tenancy:** the 7B ollama seat (`qwen2.5:7b-instruct-q4_K_M`, ~4.18 GiB
  resident) held the card throughout, *and* a sibling B1b lane ran concurrently
  after 15:10. Peak VRAM **78.4 MB** (ceiling 1,500 MB).
- `result.json` carries `verdict: "NEGATIVE"` (the driver's coarse two-way field
  KEEP/NEGATIVE); the **pre-registered** mapping — "no arm passes any gate →
  **KILL**" — is the lane verdict booked here. Booked as a labelling defect in the
  driver, not a second result.
- Artifacts (`results/b1b_kink_runB/`): _crashed-1508-attempt, agreement.json, controls.json, guard, holdout_samples.npz, model_kink_seed2718.pt, model_kink_seed2719.pt, model_kink_seed2720.pt, model_relu_seed2718.pt, model_relu_seed2719.pt, model_relu_seed2720.pt, model_tanh_b1exact_seed2718.pt, model_tanh_b1exact_seed2719.pt, model_tanh_b1exact_seed2720.pt, model_tanh_seed2718.pt, model_tanh_seed2719.pt, model_tanh_seed2720.pt, regions.json, result.json, run_config.json, run_outer.log, traces_meta.json.
- Code: `experiments/b1b_kink.py` (driver/guard/training/receipts),
  `experiments/b1b_kink_engine.mjs` (B1's harness + additive `kind` branches).
- Elapsed 232.6 s.

## What this means

The **frozen claim is falsified**: at B1's own 40-epoch budget no basis — smooth
tanh, generic ReLU, or a learned-knot hinge spline on the law's own difference
coordinate — reaches ≥0.99 at 1e-2 or 5e-2. But the mechanism is readable, and
it is **not** "the basis is irrelevant":

- The piecewise-linear basis moves τ₁ by **+0.257** overall and that gain is
  concentrated **entirely in the 88%-of-ticks saturation region** (+0.290 there).
  Representational sensitivity is real; it is simply insufficient at 40 epochs.
- **τ₂ = 5e-2 is optimization-bound, not representation-bound**: B1's own
  300-epoch tanh control already cleared it at **0.9902**, and every arm here used
  B1's 40-epoch recipe.
- So the honest statement is narrower than the prereg's mechanical KILL sentence.
  The data do **not** say "the residual is not the basis"; they say *"a 40-epoch
  fit is not enough at either tolerance, and a piecewise-linear basis buys a
  large, region-localized slice of the τ₁ gap."* The KILL branch fired on the
  letter; this receipt records that the letter and the mechanism disagree.

**Next, if the fleet wants the claim:** (i) 300 epochs on arm (b), with deadzone
and ramp scored as *separate* gates (the two regions no basis has touched);
(ii) re-parameterize arm (c) with `b0` pinned at 0 and knots initialized at the
law's own kink loci (1.5, s+1.5) — the flat deadzone signature says that miss is
a bias term, not a shape failure; (iii) prefer per-region gates to one pooled
gate, since saturation alone is 88% of the holdout and can carry a pooled number
that hides ramp entirely.

## House laws

seed 2718 · fail loud (my port bug + the sibling-lane collision, both booked) ·
std==0 → INCONCLUSIVE never PASS (n/a: every gate std > 0) · receipt or VOID (this
run's gate PASS; the first fire's VOID receipt preserved) · list-form subprocess
only, never shell=True · O(chunk) data-gen · **no commit** · other lanes' lines
untouched.

## Reconciliation with the booked fleet claim (keeper commit 3805671, 15:11:32)

HEAD history carries `3805671` (SuperInstance, 2026-10-01 15:11:32):
*"B1b-KINK-HEAD: KEEP 6/12 — sensitivity law confirmed 2-5x over book tol,
kink-precision FALSIFIED (learned kink 0.9991 < tanh 0.9998 @5e-2, p~0.008),
nerr_min 0.0007 @5e-2, per-region ladders banked."*

That is **not contradicted by this receipt — it is a different training budget.**
Two budgets, one question:

| budget | tanh @5e-2 | kink @5e-2 | reading |
|---|---|---|---|
| 40 epochs (this lane, B1's recipe) | 0.8891 | 0.7659 | KILL on the frozen claim |
| 300 epochs (fleet claim, 3805671) | 0.9998 | 0.9991 | KEEP; kink NOT better than tanh |

They agree on the direction that matters: **the learned-kink head never beats
tanh** (mine 0.7659 < 0.8891; theirs 0.9991 < 0.9998) — "kink-precision" as a
*win* is falsified under both. This lane adds the mechanism (the kink head's
deadzone loss is a stuck `b0` bias term, not a shape failure) and the region
localization (saturation, 88% of ticks, carries the entire basis effect), plus
the budget datum that makes the two reconcilable: τ₂=5e-2 is
optimization-bound, τ₁=1e-2 is not closed by any basis at 40 epochs.

Also booked: the 15:11 commit captured this lane's `runB` **mid-flight** (only
`holdout_samples.npz`, `run_config.json`, `traces_meta.json` and one model file
at that moment) and the keeper archived my crashed first fire to
`_archive/b1b_kink_attemptB_void-20261001/`. This receipt supersedes that
snapshot. **Verifier note for the keeper:** the committed message's numbers
(0.9991/0.9998) have **no artifact anywhere in the tree** — the only B1b
`result.json` on disk is this lane's. Seal them to a run directory or restate
them from a re-run; a booked number without a receipt is the class this lab
Voided for GPU energy, and it should not stand for agreement either.
