# B1C — VALUE FIDELITY: close the deadzone/ramp deficit (per-region gates)

Lane **B1C-VALUE-FIDELITY**. Direct follow-up to the **B1b RECONCILIATION**
(`RESULTS.md` keeper fold + commit `2f123d9`). Pre-registered **2026-10-01
15:30 AKDT, BEFORE fire** — before any trace was regenerated, any arm built, or
any parameter trained. Gates frozen here; the verdict is booked either way
(`results/b1c/` + `RESULTS.md` + `QUEUE.md`). Seed **2718**. **NO COMMIT.**

## Where B1b left the question (why this lane exists)

B1b's artifact-backed record (`results/b1b_kink_runB/`) localised the B1
value-fidelity deficit to two regions and exonerated a third:

| region | frac of holdout | ReLU @5e-2 | tanh @5e-2 | verdict |
|---|---|---|---|---|
| clamp | 0.125% | 1.0000 | 1.0000 | **solved** (deployed box clamp) |
| saturation | **88.39%** | 0.9815 | 0.9596 | **solved** (ReLU 0.9654 vs tanh 0.6759 @1e-2) |
| deadzone | **7.80%** | **0.4951** | 0.4055 | **OPEN — all bases < 0.50 @40ep** |
| ramp | **3.69%** | **0.3205** | 0.2196 | **OPEN — unmoved by ANY basis** |

The aggregate metric hid this: saturation is 88.4% of ticks, so the aggregate
"ReLU 0.9192 @5e-2" is mostly saturation and cannot see deadzone/ramp. B1b also
booked that **B1's own 300-epoch tanh control hit 0.990 @5e-2 aggregate** —
which, arithmetically, is only reachable if deadzone AND ramp are near 0.90 at
that budget (0.884·1 + 0.078·0.9 + 0.037·0.9 + 0.001 ≈ 0.990). So the gap is at
least partly **optimization/dilution-bound**, not purely representational.

## Claim (falsifiable)

The deadzone/ramp deficit is **closable to ≥0.90 @5e-2 in BOTH regions by a
targeted intervention** — specifically by attacking the training *signal*
(region reweighting), the *capacity*, or the *output interface* (binned head) —
and NOT (as B1b's negative suggested) permanently unmoved by any choice of
hidden basis. If no arm clears, the deficit survives every cheap intervention
and is booked as a genuine floor of the deployed recipe.

## Primary gate — PER-REGION (frozen; the aggregate is NOT the claim)

On held-out whole traces, per arm, per budget, mean over **3 seeds
2718/2719/2720**:

- **PASS** iff `A_deadzone(5e-2) ≥ 0.90` **AND** `A_ramp(5e-2) ≥ 0.90`
  **AND both stds > 0**. `std == 0 → INCONCLUSIVE`, never PASS.
- **Stated margins** (frozen): at 40ep the reference ReLU deficits are
  deadzone 0.4951 (needs **+0.4049**) and ramp 0.3205 (needs **+0.5795**). A PASS
  additionally reports its margin `mean − 0.90`.
- **Mechanism-effect bar (secondary, ≤ PASS):** an arm is called a *mechanism
  win* even below 0.90 iff it beats the same-budget `relu_ref` by **≥ +0.15 on
  deadzone and ≥ +0.20 on ramp**. This separates "the knob did nothing" from
  "the knob moved it, not far enough".
- Reported, not gated: `saturation` and `clamp` agreement (watch for *rot* —
  any arm whose saturation drops below 0.90 @5e-2 is booked as a trade), the
  full agreement curve at 1e-6…2e-1, and the aggregate.

## Budgets (frozen) — BOTH, subject to a declared Wh envelope

Run at **EPOCHS ∈ {40, 300}** (everything else frozen). The Wh envelope is
**≤ 20 Wh measured** for the whole lane. If the 40-epoch sweep is projected to
push the lane past 20 Wh, the **300-epoch sweep is the one that runs** (it is
the budget at which B1's own control reached the target); the dropped budget is
**booked, not silently skipped**. Same frame, same seeds, same splits at both.

> **AMENDMENT 1 (2026-10-01 15:34 AKDT, BEFORE the real-frame fire — only a
> reduced-frame plumbing smoke had run).** The envelope above was first written
> as **≤ 12 Wh**, which was mis-set: a measured per-net timing probe
> (`40ep = 6.3–9.1 s/net`, so `300ep ≈ 47–68 s/net` over the same ~354k train
> rows) projects the full 4-arm × 3-seed × 2-budget lane at **≈13–15 Wh**, so the
> 12 Wh figure would have excluded *both* budgets and defeated itself. Envelope
> **corrected to ≤ 20 Wh measured**; both budgets therefore run. No gate, arm,
> tolerance, frame, split, seed, or margin changed. Booked because a frozen
> constant was edited before fire — the edit and its reason are in the record.

## Arms (frozen) — 4 arms × 3 seeds × 2 budgets

Every arm's Gate-A action is the **deployed** convention
`Δ_pred = clamp(p + raw, 6, 54) − p`, identical to B1/B1b and to how the JS
harness acts in play.

1. **`relu_ref`** *(REFERENCE, not a new mechanism)* — B1b's ReLU net verbatim:
   `3→64→64→1`, ReLU hidden, deployed-MSE, Adam lr 1e-3, batch 4096. Serves two
   roles: the same-budget baseline for every comparison, and **control C5**
   (must reproduce `results/b1b_kink_runB`'s relu per-region numbers at 40ep).

2. **`reweight`** *(arm (c); my primary pick)* — identical `3→64→64→1` ReLU body
   and optimizer, but the MSE is **reweighted per tick by the inverse frequency
   of the tick's law region** (region from ground truth on the *train* split,
   weights normalised to mean 1, clipped to [0.5, 30]). Justification: deadzone
   is 7.8% of ticks and ramp 3.7%, so plain MSE spends ≈88% of its gradient on
   saturation — the exact signature of "unmoved by ANY basis at 40ep". Inverse-
   frequency weighting makes the loss landscape proportional to per-region
   *agreement* rather than per-region *mass*; it is the direct test of the
   dilution hypothesis and changes **no** representational degree of freedom.

3. **`cap`** *(arm (b))* — capacity bump: ReLU MLP `3→128→128→128→1`
   (**2× width, 3 hidden layers**, ≈33k params ≈ 7.4× `relu_ref`). Deployed MSE.
   Justification: tests pure underfitting — if the 40ep deficit is optimisation,
   more piecewise-linear units should buy sharper deadzone/ramp edges; if not,
   capacity is exonerated and the deficit is signal/interface, not size.

4. **`binned`** *(arm (d))* — **binned/quantised target head**: ReLU body
   `3→64→64` followed by a **softmax head over K = 105 uniform bins** on
   `Δ ∈ [−1.05, +1.05]` (bin width 0.02, a bin centre exactly at 0), trained
   with cross-entropy on the binned target; prediction = argmax bin centre,
   then the deployed clamp. Justification: the law's *value set* has **atoms**
   (Δ ≡ 0 in deadzone, Δ ≡ ±s in saturation) plus a continuum (ramp). A
   regression head approximates the atoms only asymptotically; a binned head
   can emit them **exactly**, converting "value fidelity" into classification.
   Nearest-bin error ≤ 0.01 < 5e-2, so a correct classification clears the gate
   in every region; the risk is classification accuracy, not resolution. The
   grid range is the only law assumption and it is booked as such.

**Arms considered and REJECTED (frozen, with reason):** (a) mixed basis
ReLU-body/tanh-head — a smooth *output* activation re-introduces the asymptotic-
zero problem the deadzone needs solved, and it confounds two changes; (e) tanh
with scaled pre-activation gain β·z — a sharper smooth sigmoid still cannot emit
the atom Δ≡0, and its expressiveness is already spanned by `cap`. Both are
**deferred to B1D**, not silently dropped.

## Frame (reused VERBATIM from B1/B1b — no new degrees of freedom)

- teacher = the **shipped** `quilt-arcade games/pong/sheet.mjs` cell `ai.track`,
  labels **executed** by the engine (Node child, list-form subprocess), never
  reimplemented in Python;
- frame **uniform-random reachable states** (both paddles U{−1,0,+1},
  engine-driven), **240 traces**, seed `900000+i`, ≤1200 ticks;
- split **held out by WHOLE trace**: `i % 5 == 0` → 48 holdout traces
  (~90,930 law actions); rest train;
- inputs `((p−30)/30, (b−30)/30, side)`; Adam lr 1e-3; batch 4096; **3 seeds
  2718/2719/2720**; **CUDA**.

Regeneration is deterministic in `(seed, rngSeed)`, so the frame is
bit-comparable to B1b's and B1's frozen holdouts (control C4).

## Regions (frozen partition — arm-independent, from law ground truth)

`z = b − p`, `u = |z|`, `s = 0.85 (left) | 0.70 (right)`, checked in order:
**clamp** (`u>1.5` AND `p+Δ_law ≤ 6+1e-6` or `≥ 54−1e-6`); **deadzone**
(`u ≤ 1.5`); **saturation** (`u ≥ s+1.5`); **ramp** (`1.5 < u < s+1.5`).
Identical to B1b — the per-region table is apples-to-apples with runB.

## Controls (frozen — must pass before any Gate-A number is read)

1. **C1 law equivalence** — switch `law` branch vs pristine `ai.track` on 4,000
   holdout states: **bit-identical** (`max|Δ| = 0`).
2. **C2 JS↔torch port**, per arm per side, on 50,000 holdout states, **float64
   vs float64**: `max|Δ| < 1e-6` (the float32 line is reported alongside). The
   engine gains **strictly additive** forward branches for `cap` and `binned`;
   `tanh`/`relu`/`kink` forwards and every `collect`/`labels`/`laweq`/`h2h`
   path stay byte-identical in behaviour. A port failure VOIDs only that arm's
   h2h (Gate A is torch-side and unaffected) — and **h2h is NOT in this lane**.
3. **C4 trace-frame cross-check** — regenerated holdout `(X, Y, META)` compared
   to **both** `results/b1b_kink_runB/holdout_samples.npz` and
   `results/b1_distill/holdout_samples.npz`: `max|ΔX| = max|ΔY| = 0` required.
4. **C5 reference reproduction** — `relu_ref` @40ep per-region means must match
   runB's relu within **|Δ| < 0.05** on every region; the raw `max|Δ|` is booked.
   A miss VOIDs the same-budget comparison claim (the arms' absolute numbers
   still stand, booked with the control's failure).

**h2h is explicitly OUT OF SCOPE** for B1C (frozen): no gate-clearing secondary
without a booking, and the claim is per-region *agreement*, not play strength.

## Guard + receipt (G7) — no receipt → run VOID

`Guard(task_id="B1C-value-fidelity", seed="2718", receipt_dir=results/b1c/guard)`.
Preflight: free VRAM ≥ 1024 MiB, temp ≤ 80 °C. Retry once after 60 s; still
short → **NOT-RUN**, booked. G7 watt receipt (`g7-watt-receipt@1`,
validator `../fleet-seeds/scripts/g7_validate.mjs`) sealed over the whole
measured window. **Device VRAM < 1.5 GB.** **Co-tenancy:** the 7B ollama seat
holds the card; these nets are tiny (<100 MB peak) and run beside it.

## Verdict mapping (mechanical)

- ≥1 arm PASS (deadzone ≥0.90 AND ramp ≥0.90 @5e-2, both std>0) → lane **KEEP**;
  name the arm(s) and the **budget** at which they clear (40ep vs 300ep is booked
  as a first-class result — "budget-conditional" is a finding, not a footnote).
- No PASS but ≥1 arm clears the **mechanism-effect bar** → lane **PARTIAL**:
  the knob moves deadzone/ramp but not to the bar; the per-region table is the
  finding; the strongest knob is named as B1D's seed.
- No PASS and no mechanism effect → **KILL**: the deadzone/ramp deficit survives
  reweighting, capacity, AND a binned interface; it is a floor of the recipe.
- Any arm with `std == 0` on a gated region → **INCONCLUSIVE** for that arm.

## Artifacts (frozen paths, `results/b1c/`)

`run_config.json`, `traces_meta.json`, `holdout_samples.npz`,
`model_<arm>_seed{2718,2719,2720}_ep{budget}.pt` (24 nets),
`agreement.json` (aggregate curve per arm×budget), `regions.json` (the
per-region table per arm×budget — the headline), `controls.json`
(C1/C2/C4/C5), `result.json` (combined verdict), `RESULTS-ENTRY.md`, `guard/`
(g7 receipt + guard_summary). Code: `experiments/b1c_value_fidelity.py`,
`experiments/b1c_value_fidelity_engine.mjs` (B1b engine + additive `cap`/`binned`
forwards). Code and B1/B1b artifacts are left untouched.

**Do NOT commit** — the keeper commits. Other lanes' lines untouched.
