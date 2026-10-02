# B1C — VALUE FIDELITY: deadzone/ramp deficit — results entry

Lane **B1C-VALUE-FIDELITY** (prereg `proposals/runs/B1C-value-fidelity.md`, frozen
2026-10-01 15:30 AKDT). 2026-10-01. **NOT COMMITTED.**

## Verdict: **KEEP** — `cap@ep40` clears the per-region gate

`cap@ep40` is the single arm that PASSes the frozen primary gate
(deadzone ≥ 0.90 **AND** ramp ≥ 0.90 @5e-2, 3-seed mean, both std > 0). The
deadzone/ramp deficit is **not** a permanent floor of the recipe: it is
**capacity-bound at 40 epochs** and **budget-bound** (any ReLU-family arm closes
it at 300 epochs, but only by reaching the ceiling with std == 0 — which the
frozen degeneracy rule books as INCONCLUSIVE).

## Resume provenance (booked — this lane is a post-kill resume)

The prior B1C subagent was infra-killed at 15:45 AKDT mid-run. Inventory found
**12 nets already trained and saved** (`model_{relu_ref,reweight,cap,binned}_seed{2718,2719,2720}_ep40.pt`,
15:33–15:36) plus `holdout_samples.npz`, `traces_meta.json`, `run_config.json`.
The prereg existed and was honoured unchanged. This resume:

- **REUSED (not retrained): 12 models** — all four arms × 3 seeds at ep40,
  loaded from their saved `state_dict` (`result.json:resume.reused_models`).
- **RETRAINED: 12 models** — the same four arms × 3 seeds at ep300 (the budget
  the killed run never reached).
- A minimal `--resume` plumbing flag was added to `experiments/b1c_value_fidelity.py`
  (skip training where a `.pt` exists → load + score). **No gate, arm, frame,
  split, seed, margin, or tolerance was changed.** Banked in `result.json:resume`.
- The frame was regenerated deterministically and re-verified bit-identical to
  both B1b and B1 (control C4 below) — the reuse is on the prereg's frame.

## Per-region table (held-out, 3-seed mean ± std @5e-2) — the headline

| arm | budget | deadzone @5e-2 | ramp @5e-2 | saturation @5e-2 | aggregate | verdict |
|---|---|---|---|---|---|---|
| relu_ref | 40 | 0.4951 ± 0.3102 | 0.3205 ± 0.0987 | 0.9815 | 0.9192 | FAIL |
| reweight | 40 | 0.7553 ± 0.3413 | 0.6950 ± 0.3669 | 0.9815 | 0.9533 | FAIL (mech win) |
| **cap** | **40** | **0.9957 ± 0.0061** | **0.9186 ± 0.1109** | **0.9992** | **0.9959** | **PASS** |
| binned | 40 | 1.0000 ± 0.0000 | 0.1200 ± 0.0012 | 0.9994 | 0.9670 | INCONCLUSIVE (std==0 on deadzone) |
| relu_ref | 300 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 | 1.0000 | INCONCLUSIVE (std==0) |
| reweight | 300 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 | 1.0000 | INCONCLUSIVE (std==0) |
| cap | 300 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 1.0000 | 1.0000 | INCONCLUSIVE (std==0) |
| binned | 300 | 1.0000 ± 0.0000 | 0.8670 ± 0.0300 | 1.0000 | 0.9951 | INCONCLUSIVE (std==0 on deadzone) |

Region fractions (holdout, n = 90,930): clamp 0.13%, deadzone 7.80%,
saturation 88.39%, ramp 3.69% — identical to B1b's partition.

Mechanism-effect bar vs same-budget `relu_ref` (deadzone ≥ +0.15 AND ramp ≥ +0.20):

| arm@budget | deadzone lift | ramp lift | mechanism win |
|---|---|---|---|
| reweight@40 | +0.2602 | +0.3745 | **yes** |
| cap@40 | +0.5006 | +0.5981 | **yes** |
| binned@40 | +0.5049 | −0.2006 | no (ramp collapsed) |
| all @300 | +0.0000 | +0.0000 or −0.1330 | no (ceiling) |

## Findings

1. **The deficit is capacity-bound, and the claim survives.** `cap`
   (3-128-128-128-1, 33,665 params) clears BOTH regions at the *same 40-epoch
   budget* where every ReLU-width-64 basis failed — ramp +0.598, deadzone +0.501
   over the reference. No saturation rot (cap sat 0.9992 > ref 0.9815). This
   directly refutes B1b's "unmoved by ANY basis" as a *representational* floor:
   the piecewise-linear family did contain the deadzone/ramp kinks; the width-64
   net simply could not fit them in 40 epochs.
2. **Signal reweighting moves it, but not to the bar.** Inverse-region-frequency
   weighting (deadzone 7.8%, ramp 3.7% of ticks) lifts deadzone +0.260 and ramp
   +0.375 at 40ep — confirming the *dilution* hypothesis directionally — yet
   lands at 0.755/0.695, short of 0.90. Signal helps; capacity helps more.
3. **The binned head is a trap for the ramp.** A softmax-over-105-bins head
   emits the deadzone atom *exactly* (1.0000 at both budgets) but **destroys the
   ramp continuum** (0.1200 at 40ep, 0.8670 at 300ep — the only arm that never
   reaches ramp 0.90 at either budget, and the only 300ep arm that is not at the
   ceiling). Converting value-fidelity into classification fixes the atom and
   loses the continuous region; the grid made ramp an under-resolved class.
4. **Budget-conditional is a first-class result.** At 300ep, `relu_ref`,
   `reweight`, and `cap` ALL reach deadzone 1.0000 / ramp 1.0000 — but with
   **std == 0 across the 3 seeds** (every seed saturates to the ceiling). The
   frozen rule (`std == 0 → INCONCLUSIVE, never PASS`) correctly refuses to call
   this a PASS; the honest reading is that at 300 epochs the deficit is gone and
   the metric has run out of resolution. This independently corroborates B1's own
   300-epoch control (0.990 aggregate) as an optimisation-budget effect.
5. **Aggregate would have hidden all of it** (as B1b warned): at 40ep the
   aggregate ranks binned 0.9670 < cap 0.9959 while binned's *ramp* is 0.12 —
   saturation's 88.4% mass masks a total ramp collapse.

## Controls (all pass)

- **C1 law equivalence** — `max_abs_diff = 0`.
- **C2 JS↔torch port**, per arm per side, f64 — max 4.11e-15 (< 1e-6); f32 line
  ≤ 3.42e-06; binned exact (0.0).
- **C4 frame cross-check** — regenerated holdout vs **both**
  `results/b1b_kink_runB/` and `results/b1_distill/`: `max|ΔX| = max|ΔY| =
  max|ΔMETA| = 0.0`.
- **C5 reference reproduction** — `relu_ref@ep40` per-region cells match runB's
  relu with **max|Δ| = 0.0000** (tol 0.05). The same-budget comparison is valid.

## Guard / receipt

`Guard(task_id="B1C-value-fidelity", seed=2718, receipt_dir=results/b1c/guard)`.
Receipt `g7-wr-b1c-value-fidelity-1790899870.json` — **valid, PASS**. Preflight
free VRAM **1475 MiB** ≥ 1024; max temp **79 °C** ≤ 80; peak VRAM **124.1 MB**
(ceiling 1500, device 6 GB); gpu 979.8 s; mean power 45.57 W;
**16.11 Wh measured** (58.0 kJ).

### ⚠ Booked discrepancy — Wh envelope constant

`run_config.json` / code constant `WH_ENVELOPE = 12.0` (stale; written before
prereg AMENDMENT-1 corrected the envelope to **≤ 20 Wh**). Measured **16.11 Wh**
is **within the amended 20 Wh envelope** but **above the stale 12.0 constant**.
Booked, not silently passed: the run's authority for the envelope is the prereg
amendment, not the code constant; the constant was not edited post-fire. Both
budgets ran, as the amendment intended.

## Artifacts (`results/b1c/`)

`result.json` (verdict + resume ledger + controls), `regions.json` (per-region
table — the headline), `agreement.json` (full curve), `controls.json`,
`run_config.json`, `traces_meta.json`, `holdout_samples.npz`,
`model_<arm>_seed{2718,2719,2720}_ep{40,300}.pt` (24 nets),
`guard/{g7-wr-...json, guard_summary.json, ledger.jsonl}`, `run_resume.log`.
Code: `experiments/b1c_value_fidelity.py` (+`--resume`),
`experiments/b1c_value_fidelity_engine.mjs`.

## Seed for B1D

- **Primary:** capacity is the lever — sweep width/depth *at fixed 40ep* to find
  the minimum capacity that clears both regions (is 128×128 needed, or 96×64?),
  and pair it with reweighting (signal + capacity together, untested in
  combination).
- **Interface:** do not ship the pure binned head. If the atom-exactness is
  wanted, try a **hybrid head** (regression + a deadzone atom gate) so ramp keeps
  a continuous output; the binned-only ramp collapse is booked here.
- **Metric:** at 300ep the gate is unmet-and-degenerate; B1D should measure the
  bottleneck at a *higher-resolution* tolerance (1e-3 / 1e-2) or report the
  ceiling as a resolved outcome, otherwise any 300ep arm is structurally
  INCONCLUSIVE.
- Deferred B1C arms: mixed ReLU-body/tanh-head; tanh with scaled pre-activation
  gain β·z (both rejected in the prereg, deferred here).
