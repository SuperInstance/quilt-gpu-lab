# B1E — LINEAR-HEAD FLOOR: capacity floor > 64 even at the actual B1C recipe; the head sets the deficit, capacity sets the threshold

Lane **B1E-LINEAR-HEAD-FLOOR** (prereg `proposals/runs/B1E-linear-head-floor.md`,
frozen 2026-10-01 16:4x AKDT, before fire). 2026-10-01. **NOT COMMITTED.**

## Verdict: **PARTIAL** — no linear-head arm clears ≤ 64; the B1C-recipe floor is > 64 at 40ep

B1D booked the **tanh**-head floor as > 64 and bracketed the **linear**-head floor
as (64, 128] via its control C6 (= B1C's `cap` arm, which PASSED at width 128).
B1E runs the missing cells — B1C's **exact recipe**: B1C `cap`-arm **body**
(3 hidden ReLU layers) with B1C `cap`-arm **head (LINEAR / identity)**, width
swept {24, 32, 48, 64} × {plain, reweight} × 3 seeds, **40ep only**.

**Answer, honest and specific:**

1. **No linear-head arm clears BOTH regions at any width ≤ 64** → even at the
   *actual* B1C recipe the **capacity floor is > 64 at 40ep** (for plain and for
   reweight). The floor is now **bracketed (64, 128]**: the reused width-128
   linear-head anchor **PASSes** (deadzone 0.9957 / ramp 0.9186) = B1C's `cap`.
   **Book: "capacity floor > 64 even with the linear head."**
2. **The head is the shape/deficit lever, the width is the threshold lever.**
   At *every* width, the **linear head beats the tanh head** on holdout, and by a
   **growing** margin: w64 plain **+0.393 deadzone / +0.354 ramp**; w64 reweight
   **+0.445 / +0.369** (vs B1D's booked tanh cells, no retraining). The linear
   head also **restores monotone width-dependence** (plain deadzone
   0.178→0.229→0.457→0.637 monotone in w; B1D's tanh was non-monotone/flat).
   But the floor does not move to ≤ 64 — so B1C's PASS is **a width story at the
   threshold** (needs > 64 at 40ep) and **a head story at the margin**.
3. **Ramp stays short with capacity alone.** Best **plain** ramp @5e-2 = 0.5675
   (w64) — capacity alone does **not** close the ramp. The **region-reweight**
   lifts it to 0.7977 (w64) but still < 0.90 → **ramp needs BOTH capacity (>64)
   AND reweight.** (Deadzone, by contrast, *does* clear with reweight at w48:
   0.9087 ≥ 0.90 — but its ramp 0.7543 keeps that arm a FAIL.) Corroborates B1D:
   **the ramp is the residue.**

## Per-region table (held-out, 3-seed mean ± std) — the headline

Holdout n = 90,930; region fractions **identical to B1C/B1b/B1D**: clamp 0.13 %,
deadzone 7.80 %, saturation 88.39 %, ramp 3.69 %.

| arm | width | params | deadzone @5e-2 | ramp @5e-2 | sat @5e-2 | dz @1e-2 | ramp @1e-2 | verdict |
|---|---|---|---|---|---|---|---|---|
| plain | 24 | 1,321 | 0.1779 ± 0.0066 | 0.1839 ± 0.0182 | 0.9608 | 0.0464 | 0.0393 | FAIL |
| plain | 32 | 2,273 | 0.2289 ± 0.0619 | 0.2436 ± 0.0668 | 0.9703 | 0.0549 | 0.0545 | FAIL |
| plain | 48 | 4,945 | 0.4571 ± 0.3840 | 0.4625 ± 0.3655 | 0.9756 | 0.3551 | 0.1852 | FAIL |
| plain | 64 | 8,641 | 0.6368 ± 0.3166 | 0.5675 ± 0.3168 | 0.9888 | 0.4776 | 0.2895 | FAIL |
| reweight | 24 | 1,321 | 0.2504 ± 0.0443 | 0.2788 ± 0.1238 | 0.9368 | 0.0653 | 0.0631 | FAIL |
| reweight | 32 | 2,273 | 0.5875 ± 0.3255 | 0.5206 ± 0.3534 | 0.9556 | 0.3716 | 0.2341 | FAIL |
| reweight | 48 | 4,945 | **0.9087 ± 0.1075** | 0.7543 ± 0.1400 | 0.9883 | 0.3136 | 0.1520 | FAIL (deadzone clears; ramp short) |
| reweight | 64 | 8,641 | **0.9720 ± 0.0359** | **0.7977 ± 0.2421** | 0.9959 | 0.6475 | 0.4965 | FAIL (best sweep arm; mech win) |
| **_CONTROL_ anchor_cap128** *(linear head = B1C cap, C6/C7; REUSED nets from B1D)* | 128 | 33,665 | **0.9957 ± 0.0061** | **0.9186 ± 0.1109** | 0.9992 | 0.6013 | 0.2597 | **PASS** |

No arm is degenerate: every gated std > 0 (min 0.0066) → **no INCONCLUSIVE**.

## Head-vs-width attribution (linear − tanh, same arm, same width; tanh reused from B1D)

| arm | width | Δ deadzone @5e-2 | Δ ramp @5e-2 |
|---|---|---|---|
| plain | 24 | +0.0087 | +0.0105 |
| plain | 32 | +0.0576 | +0.0692 |
| plain | 48 | +0.1276 | +0.2210 |
| plain | 64 | **+0.3928** | **+0.3538** |
| reweight | 24 | +0.0449 | +0.1248 |
| reweight | 32 | +0.3247 | +0.2739 |
| reweight | 48 | +0.2123 | +0.2404 |
| reweight | 64 | **+0.4446** | **+0.3688** |

The head gain **grows with width** (it is not a constant offset): at small width
the bottleneck is capacity, at large width the tanh interface is the dominant
loss term — which is *why* B1D's tanh arms looked width-flat. The linear head
removes that interface penalty and reveals the underlying monotone capacity
curve, but the ≥0.90 threshold is still not crossed at w ≤ 64.

## Mechanism bar (reweight − plain at same width; needs ≥ +0.15 dz AND ≥ +0.20 ramp)

| width | Δ deadzone | Δ ramp | mechanism win |
|---|---|---|---|
| 24 | +0.0725 | +0.0949 | no |
| **32** | **+0.3587** | **+0.2770** | **yes** |
| **48** | **+0.4517** | **+0.2918** | **yes** |
| **64** | **+0.3352** | **+0.2302** | **yes** |

Reweighting is a mechanism win at w32/w48/w64 (B1D: w48/w64), and it is
**stronger at the linear head** — consistent with "the head was masking the
region signal".

## Controls (all pass)

- **C1 law equivalence** — `max|Δ| = 0` on 4,000 holdout states (bit-identical).
- **C4 frame cross-check** — regenerated holdout equals `results/b1c/`,
  `results/b1b_kink_runB/` AND `results/b1_distill/` with
  `max|ΔX| = max|ΔY| = max|ΔMETA| = 0.0` (all three). Frame reuse proven.
- **C6 anchor reproduction (cross-lane)** — the width-128 **LINEAR**-head anchor
  (= B1C `cap`, **nets REUSED from B1D**, not retrained) reproduces B1C's booked
  `cap@ep40` with **max|Δ| = 4.7e-05** (deck/deadzone 0.9957 / ramp 0.9186).
- **C7 net-reuse cross-lane proof (new)** — the same reused anchor nets
  re-scored on the regenerated frame match B1D's booked `anchor_cap128` cells
  with **max|Δ| = 0.0** (bit-exact). The pipeline is deterministic end-to-end.

## Safeguards booked (B1D warts fixed)

- **Verdict counts ONLY the 8 preregistered sweep arms** (`{plain,reweight}×
  {24,32,48,64}`); the code **asserts** the counted set equals that exact list
  before reading KEEP/PASS — the control anchor is never counted (B1D's caught
  first-fire bug).
- **Append-window guard summaries**: after receipt emission the window's
  `guard_summary.json` is snapshotted to `guard_summary.window1.json`, so a
  later `--resume` window can never overwrite the fire window's summary (B1D's
  binding-digest loss). Single window this run.

## Guard / receipt

`Guard(task_id="B1E-linear-head-floor", seed=2718, receipt_dir=results/b1e/guard)`.

- `g7-wr-b1e-linear-head-floor-1790902119` — **valid, PASS**; **4.9133 Wh**,
  277.7 GPU-s, mean 47.78 W, 71 power samples, wall 370.2 s.
- **Lane total: 4.91 Wh measured ≤ 6 Wh envelope** (17.7 kJ). Peak VRAM
  **121.1 MB** (ceiling 1500, device 6 GB); min free VRAM **1661 MiB** ≥ 1024;
  max temp **76 °C** ≤ 80. Co-tenant 7B seat + pong grind held the card
  throughout. No breach, no timeout.

## Artifacts (`results/b1e/`)

`run_config.json`, `traces_meta.json`, `holdout_samples.npz`, 24 nets
`model_{plain,reweight}_w{24,32,48,64}_seed{2718,2719,2720}_ep40.pt`,
`regions.json` (the headline table), `head_vs_head.json` (linear−tanh table),
`agreement.json` (full curve), `controls.json` (C1/C4/C6/C7), `result.json`
(verdict + floor + ramp-only), `guard/{g7 receipt, guard_summary.json,
guard_summary.window1.json, ledger.jsonl}`. Code:
`experiments/b1e_linear_head_floor.py` (imports the B1C driver for frame/
regions/engine; reuses `experiments/b1c_value_fidelity_engine.mjs` **unchanged**;
reuses B1D's saved width-128 anchor nets). B1/B1b/B1C/B1D artifacts untouched.
Prereg: `proposals/runs/B1E-linear-head-floor.md`.

## Next question

- The floor is bracketed **(64, 128]** for the linear head. Cheap follow-up:
  linear-head widths **{80, 96}** (plain) to bisect the crossing — the first
  width clearing ramp will name the B1C-recipe floor.
- **Ramp is the residue under every knob tried** (B1D hybrid ramp 0.8042; B1E
  linear+reweight ramp 0.7977). Is the ramp floor closed by **capacity alone**
  (bisect up to 128 at plain) or does it need a **ramp-specific interface** —
  the mirror of B1D's deadzone atom gate? That is the interface question B1D
  opened and B1E sharpened.
- Reconcile: B1C's `relu_ref` (3-64-**64**-1, depth-2, linear) failed at
  0.4951/0.3205 while B1E's depth-3 linear w64 reaches 0.6368/0.5675 — depth, not
  just width, contributes; a depth sweep at fixed width would separate them.
