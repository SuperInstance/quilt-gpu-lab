# B1-DISTILL — policy distillation of the pong derived law

Harvest of `fleet-triage/docs/RTX4050-WORKLIST.md` item B1. Pre-registration
FROZEN before fire: `proposals/runs/B1-pong-law-distill.md` (2026-10-01 ~14:20
AKDT). Seed 2718. No commit (keeper commits).

## Verdict — **KILL as stated** (Gate A FAIL, Gate B PASS)

- **Gate A (per-tick action agreement, held-out traces, frozen tol 1e-3):** **FAIL**,
  `0.05679 ± 0.00876` over 3 training seeds (2718/2719/2720).
- **Gate B (h2h vs the law, 100 seeds × 2 swapped sides × 3 seeds = 600 games,
  0 draws):** **PASS**, win-rate `0.5500 ± 0.0212`.
- **Control (law-vs-law, same swap protocol, 200 games, 0 draws):** `0.5000` exact.

The headline claim — a tiny MLP reaches **near-100% per-tick action agreement** —
is **falsified at the pre-registered tolerance**. The honest gap IS the receipt,
and it is sharp: the net always gets the *direction* right and is behaviourally
indistinguishable from the law, but it cannot reproduce the law's **exact float
action** at 1e-3.

## The teacher and the frozen frame

- Teacher = **shipped** `quilt-arcade games/pong/sheet.mjs` cell `ai.track`
  (`paddle.<side>`, `ball.y` → new paddle y; deadzone 1.5, speed 0.85/0.70,
  clamp `[6,54]`). Labels produced by **executing the unmodified cell under the
  engine** (Node child, list-form subprocess) — never reimplemented in Python.
  Control: the playing harness's `law` branch vs the pristine sheet's `ai.track`
  on 4,000 holdout states → **max|Δ| = 0, 0/4000 differ** (bit-identical).
- **Frame (frozen): uniform-random reachable states**, engine-driven (both
  paddles uniform-random {−1,0,+1}). 240 traces (`seed 900000+i`, ≤1200 ticks,
  79% closed), held out **by whole trace** (`i % 5 == 0` → 48 holdout). 366,346
  train / 90,930 holdout law actions. `Δlaw == 0` (deadzone + clamp-at-rest) on
  **7.92%** of the holdout.
- Model: MLP `3→64→64→1` tanh, **4,481 params**, inputs `((p−30)/30,(b−30)/30,side)`,
  Adam lr 1e-3, 40 epochs, batch 4096, **CUDA**. Peak VRAM **64.8 MB** (ceiling 1.5 GB).

## Gate A detail (held-out, 3 seeds)

| seed | agree@1e-3 | agree@1e-6 | letter | **direction (law-moving)** | rms | max |
|---|---|---|---|---|---|---|
| 2718 | 0.05670 | 3.7e-05 | 0.9211 | **1.0000** | 0.0624 | 0.801 |
| 2719 | 0.06756 | 3.5e-05 | 0.9210 | **1.0000** | 0.0790 | 0.785 |
| 2720 | 0.04610 | 3.7e-05 | 0.9218 | **1.0000** | 0.0477 | 0.782 |

Mean agreement-vs-tolerance curve: `1e-6 3.7e-5 · 1e-4 0.0055 · 1e-3 0.0568 ·
1e-2 0.6163 · 5e-2 0.8715 · 1e-1 0.9114 · 2e-1 0.9658`.

**Reading:** where the law actually moves, the net's step **sign is exact,
always** (`direction = 1.0000`, all three seeds). The `0.9213` letter score is
exactly `1 − 0.0792`, i.e. the whole letter deficit is the deadzone: there the
law is at rest (Δ=0) and the net emits a small non-zero that crosses the 1e-3
classifier. So the failure is **value fidelity**, not decision fidelity.

## Optimization vs representation (EXPLORATORY, never folded into the gate)

`results/b1_distill/sensitivity.json` — same arch/data/seed 2718, **300 epochs**:
rms 0.0208, `agree@1e-3 = 0.349`, `@1e-2 = 0.880`, **`@5e-2 = 0.9902`**,
`@1e-1 = 0.9952`. Longer training moves 1e-3 from 0.057 → **0.349** (×6) but not
to 1.0: the residual 1e-3 gap is **representational** (deadzone/saturation/clamp
kinks under a 64×64 tanh basis), not merely an optimization plateau. Near-100%
agreement (`≥0.99`) holds at **5e-2**, which is ≈6–7% of a typical 0.7-step.

## Gate B detail (h2h, frozen seeds 2718..2817, sides swapped)

| training seed | wins/200 | rate |
|---|---|---|
| 2718 | 107 | 0.535 |
| 2719 | 116 | 0.580 |
| 2720 | 107 | 0.535 |

mean **0.5500 ± 0.0212**, aggregate **330/600 = 0.550** (0 draws). Control
law-vs-law swapped = **0.5000** exactly (the protocol's exactness is fixed by the
construction). **Secondary (not adjudicated):** the aggregate sits 2.45σ above
0.50 — a mild hint that the inexact policy *edges* the exact law rather than
matching it; booked, not explained here.

## Harness controls (§0 worklist)

1. **Pristine-vs-switch law equivalence** — `max|Δ| = 0` on 4,000 states (PASS).
2. **JS-vs-torch net port** — per side, `max|Δ_js−Δ_torch|` = **7.15e-07 (left) /
   6.28e-07 (right)** on 45,465 states each, `< 1e-6` (PASS).
3. **Booked defect (mine):** the first port attempt fed `netforward` a state list
   mixing left/right rows while the command applies ONE side flag per call →
   `0.1620`, a **false FAIL**. Fixed to per-side; re-run in
   `port_control_rerun.json`. The defect never touched the measured gates (h2h
   calls the net with the correct per-side flag), but it is booked, not hidden.
4. **Law provenance:** every sampled state and every label emitted by the engine.

## Receipts / energy / artifacts (`results/b1_distill/`)

- **G7 receipt `g7-wr-b1-pong-law-distill-1790894147`** — `g7-watt-receipt@1`,
  gate **PASS**, validator exit 0, `source: measured`.
- Energy **26,711.52 J = 7.4199 Wh**, **381.43 GPU-s**, $0.001707 @ $0.23/kWh.
  Preflight clean (1,820 MiB free ≥ 1024 floor, 70 °C ≤ 80). **Co-tenancy:** the
  7B ollama seat (`qwen2.5:7b-instruct-q4_K_M`, ~4.18 GiB resident) held the card
  throughout; the distilled net is tiny (64.8 MB peak) and ran beside it — seat's
  share NOT subtracted, idle floor not subtracted.
- Artifacts: `result.json`, `agreement.json`, `h2h.json`, `controls.json`,
  `sensitivity.json`, `traces_meta.json`, `holdout_samples.npz`,
  `model_seed{2718,2719,2720}.pt`, `port_control_rerun.json`,
  `guard/` (receipt + summary + ledger).
- Code: `experiments/b1_pong_law_engine.mjs`, `experiments/b1_distill.py`.

## House laws

seed 2718 · fail loud (1 harness defect booked) · std==0 → INCONCLUSIVE (n/a; both
stds > 0) · receipt or VOID (receipt sealed, gate PASS) · list-form subprocess only,
never shell=True · O(chunk) data-gen (engine traces streamed to the harness, no
corpus-scale buffering) · no commit · other lanes' lines untouched.

## What this means / follow-up

Distilling the pong derived law into a tiny MLP gives a policy that is
**behaviourally exact** (direction 1.000, h2h 0.55 ∈ [0.40,0.60]) but **not
value-exact**: 0.057 @1e-3 frozen, 0.349 @1e-3 with 10× training, 0.990 @5e-2.
The derived law's kinked shape (deadzone + saturation + clamp) is the thing a
smooth small net cannot cash. Next: (a) a ReLU/learned-kink basis or a
delta-vs-position residual head to test whether exactness is representational;
(b) `1e-2`/`5e-2` as the pre-registered tolerance *with* a stated rationale
(the 1e-3 knife-edge measures the basis, not the distillation); (c) the kink
loci as a named per-region agreement breakdown (deadzone / ramp / saturation /
clamp), which is where any residual will live.
