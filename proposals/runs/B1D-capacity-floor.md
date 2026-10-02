# B1D — CAPACITY FLOOR: the minimum capacity that clears the per-region gate

Lane **B1D-CAPACITY-FLOOR**. Direct follow-up to **B1C** (`results/b1c/`, commit
`5eed498`), the B1 family's first PASS. Pre-registered **2026-10-01 16:2x AKDT,
BEFORE fire** — before any trace was regenerated, any net built, or any parameter
trained. Gates frozen here; the verdict is booked either way
(`results/b1d/` + `RESULTS.md` + `QUEUE.md`). Seed **2718**. **NO COMMIT.**

## The open question (handed to us by B1C)

B1C booked that the deadzone/ramp value-fidelity deficit is **capacity-bound at
40 epochs, not representational**: its `cap` arm (`3→128→128→128→1` ReLU, 33.7k
params) cleared BOTH frozen per-region gates @5e-2 at 40ep (deadzone
0.9957 ± 0.0061 / ramp 0.9186 ± 0.1109), while every width-64 ReLU basis failed
there (deadzone 0.4951 / ramp 0.3205) and B1b's tanh was worse. B1C's own
seed for B1D: **sweep capacity at fixed 40ep to find the MINIMUM capacity that
clears both regions, and pair it with reweighting.**

Two questions, both frozen:

1. **Q1 — the capacity floor.** What is the smallest body width that clears
   BOTH regions (deadzone ≥ 0.90 **AND** ramp ≥ 0.90 @5e-2, 3-seed mean,
   std > 0) at 40ep?
2. **Q2 — does loss reweighting lower it?** B1C's reweight moved deadzone
   +0.260 / ramp +0.375 at width-64 but not to the bar. Does it buy a *smaller*
   clearing width?

## Architecture (frozen) — B1C cap-arm body, width swept, TANH HEAD

Per the lane brief: *"Architecture otherwise identical to B1C cap arm (body
width varied, tanh head)."* Frozen as:

- **body** = the B1C `cap` arm's shape: **3 hidden ReLU layers**, each of width
  `w` (B1C used 128×128×128; B1D sweeps `w`);
- **head** = a **bounded tanh head**: `raw = A·tanh(z_out)`, `A = 1.05`,
  `z_out` = the body's linear output. The law's Δ ∈ [−0.85, +0.85] (holdout
  max|Δ| = 0.8500; the B1C binned grid was already frozen on [−1.05, +1.05] and
  the tanh scale `A` is that same law value-range assumption, booked as such).
  Rationale: B1C's own interface advice — a *continuous* bounded output, unlike
  the binned head which collapses the ramp (0.1200 @40ep).
- **deployed action** = B1/B1b/B1C's convention verbatim:
  `Δ_pred = clamp(p + raw, 6, 54) − p`. MSE on `Δ_pred` (deployed MSE).
- Adam lr 1e-3, batch 4096, CUDA, 3 seeds 2718/2719/2720.

> **BOOKED INTERPRETATION RISK.** B1C's `cap` arm used a *linear* head, so
> B1D's absolute tanh-head numbers are **not** directly comparable to B1C's
> booked `cap@ep40` cells. Both B1D arms share the tanh head, so the *within-
> lane* plain-vs-reweight comparison and the *absolute* ≥0.90 gate are clean
> claims; the cross-lane tie is carried by control **C6** below, not by
> arithmetic. This deviation is mandated by the lane brief and frozen here
> before fire.

## The sweep (frozen) — 40ep ONLY

Budget **40 epochs only**. B1C booked that the **300-epoch regime is
structurally `std == 0`** (every arm saturates to the ceiling → the frozen
degeneracy rule books INCONCLUSIVE), so a 300ep sweep cannot resolve a floor.
The mission brief fixes 40ep; we do **not** run 300ep.

| axis | values | count |
|---|---|---|
| body width `w` | 24, 32, 48, 64 | 4 |
| weighting | `plain`, `reweight` | 2 |
| seeds | 2718, 2719, 2720 | 3 |

**24 nets** for the sweep, all tanh-head, depth-3 ReLU body, 40ep.

- **`plain`** — unweighted deployed MSE.
- **`reweight`** — the **B1C `reweight` mechanism verbatim**: per-tick weights =
  inverse frequency of the tick's ground-truth law region (regions computed on
  the *train* split), normalised to mean 1, clipped to [0.5, 30], applied to the
  deployed-MSE. On this split that multiplies the deadzone error weight by
  ≈4.76× and ramp by ≈9.65× (saturation ×0.37). The brief names the arm
  "+deadzone-reweight"; this is read as **B1C's region-reweight** (the deadzone
  is the primary target; the same mechanism also upweights ramp, which is the
  other gated region). No new degree of freedom: identical to B1C.

## Controls (frozen — must pass before any Gate-A number is read)

1. **C1 law equivalence** — switch `law` branch vs pristine `ai.track` on 4,000
   holdout states: **bit-identical** (`max|Δ| = 0`).
2. **C4 frame cross-check** — regenerated holdout `(X, Y, META)`
   deterministically from the **B1C engine** (`b1c_value_fidelity_engine.mjs`,
   B1C/B1b code unchanged) must equal **all three** of
   `results/b1c/holdout_samples.npz`, `results/b1b_kink_runB/holdout_samples.npz`
   and `results/b1_distill/holdout_samples.npz` with
   `max|ΔX| = max|ΔY| = max|ΔMETA| = 0` required. This is the reuse proof: the
   frame is bit-identical to B1C's, and B1C's to B1b's and B1's.
3. **C6 anchor reproduction** — a **width-128, depth-3, LINEAR-head, plain**
   body = B1C's `cap` arm *by construction*. Retrained from scratch at 40ep on
   the regenerated frame with the same seeds; its per-region @5e-2 means must
   match B1C's **booked** `cap@ep40` (deadzone 0.9957 / ramp 0.9186) within
   **|Δ| < 0.05** on every gated region. Raw `max|Δ|` is booked. This proves the
   whole pipeline (frame + training + scoring) reproduces B1C end-to-end; a
   miss VOIDs the cross-lane tie (B1D's own absolute numbers still stand,
   booked with the control's failure). **C6 is a control, NOT an arm of the
   floor sweep.**
4. *(No C2 JS↔torch port: h2h is out of scope for B1D, as it was for B1C's gate.)*

## Primary gate (frozen) — per-region, absolute

On held-out whole traces, per **arm = (weighting, width)**, mean over **3 seeds**:

- **PASS** iff `A_deadzone(5e-2) ≥ 0.90` **AND** `A_ramp(5e-2) ≥ 0.90`
  **AND both stds > 0**. `std == 0 → INCONCLUSIVE`, never PASS.
- Secondary, **reported not gated**: the same table at **@1e-2** (resolution —
  B1C's B1D seed: "measure at 1e-3 / 1e-2") and @1e-3; `saturation` and `clamp`
  agreement (**rot watch**: any arm whose saturation drops below 0.90 @5e-2 is
  booked as a trade); the aggregate; the full curve at 1e-6…2e-1.
- **The capacity floor** = the **minimum width** w (over {24,32,48,64}) whose arm
  clears both regions — reported **separately for `plain` and for `reweight`**
  (Q1 and Q2).
- **Mechanism bar (secondary, ≤ PASS)**: `reweight` at width w is a *mechanism
  win* over `plain` at the same w iff it beats it by **≥ +0.15 deadzone AND
  ≥ +0.20 ramp**. Separates "reweighting did nothing" from "it moved the floor".

## Optional arm — hybrid head (ONLY if the Wh envelope allows)

If, after the frozen sweep, the measured envelope still allows (~3 cheap nets
remaining ≤ 18 Wh), run **one** extra arm at the **found floor width** (plain
weighting only, 3 seeds):

- **`hybrid`** — the same width-w depth-3 ReLU body + **two heads**:
  (i) a **regression head** `A·tanh(z_reg)` (as above), and
  (ii) a **deadzone atom gate** `g = σ(z_gate)` trained with BCE against the
  ground-truth deadzone label (`u ≤ 1.5`, computable in closed form from the
  inputs); the shipped `raw = (1 − g)·A·tanh(z_reg)` — in the deadzone the
  output is driven to the **exact atom 0**, outside it the continuous regression
  is untouched. Loss = deployed-MSE + 1.0·BCE. Rationale: B1C's interface seed
  ("regression + a deadzone atom gate so ramp keeps a continuous output").
  Gated identically. Purpose: can the atom gate push the floor **below** the
  regression floor? This is a **secondary interface probe**, not part of Q1/Q2.

If the envelope does not allow it, the arm is **booked as not-run**, not skipped
silently.

## Budget + guard (frozen) — no receipt → run VOID

- **Wh envelope ≤ 18 Wh measured** for the whole lane (B1C's 40ep-only work
  projects ≈6–10 Wh; the envelope is declared, not tuned post-fire).
- `Guard(task_id="B1D-capacity-floor", seed="2718", receipt_dir=results/b1d/guard)`.
  Preflight: free VRAM ≥ 1024 MiB, temp ≤ 80 °C. **< 1 GB free → retry once
  after 60 s → still short → NOT-RUN** (booked). G7 watt receipt
  (`g7-watt-receipt@1`, validator `../fleet-seeds/scripts/g7_validate.mjs`)
  sealed over the measured window.
- **Co-tenancy declared:** the 7B ollama seat + the pong grind hold the card;
  these nets are tiny (<100 MB peak) and run beside them under the guard.

## Verdict mapping (mechanical)

- ≥1 `(weighting, w)` arm PASS → lane **KEEP**; name the **plain floor** and the
  **reweight floor** (the headline is whichever question resolves).
- No PASS but ≥1 mechanism win → lane **PARTIAL**: reweighting moves the regions
  but does not lower the floor below max width; the table is the finding.
- No PASS and no mechanism win → lane **KILL**: the floor is ≥ 64 at 40ep (or
  the tanh head raises it out of range); booked honestly.
- Any arm with `std == 0` on a gated region → **INCONCLUSIVE** for that arm.

## Artifacts (frozen paths, `results/b1d/`)

`run_config.json`, `traces_meta.json`, `holdout_samples.npz`,
`model_<arm>_seed{2718,2719,2720}_ep40.pt`, `regions.json` (per-region table —
the headline), `agreement.json` (full curve), `controls.json` (C1/C4/C6),
`result.json` (verdict + floor + resume ledger), `RESULTS-ENTRY.md`, `guard/`
(g7 receipt + guard_summary + ledger). Code:
`experiments/b1d_capacity_floor.py` (imports the B1C driver for frame/gen/regions;
reuses `experiments/b1c_value_fidelity_engine.mjs` **unchanged**).

B1/B1b/B1C artifacts and code are left untouched. **Do NOT commit.**
