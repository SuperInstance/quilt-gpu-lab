# B1G — IS THE 40ep RAMP NUMBER AN EPOCHS ARTIFACT OR A LOSS-SHAPE ARTIFACT?

Lane **B1G-EPOCHS-VS-RAMP-LOSS** (prereg
`proposals/runs/B1G-epochs-vs-ramp-loss.md`, frozen 2026-10-01 17:3x AKDT,
before fire). 2026-10-01. **NOT COMMITTED.** The **B1-family closer**.

## Verdict: **KEEP (RAMP-CLOSES)** — the ramp atom gate clears G-B1G1 **and** the crossing stays intact (G-B1G2); B1F's representational call does **not** survive at the crossing width

B1F left the B1 family with *"the ramp is genuinely representational at 40ep"*
from **hybrid-v2 at width 64** (ramp atom gate **0.2930**, worse than plain
regression 0.5675; learned knot k 1.35–1.42 vs the law 1.5). B1G tests the two
untested confounds — **EPOCHS** and **LOSS SHAPE** — at **width 96, the plain
crossing point named by B1F**, so capacity is *not* a free variable.

**Design (frozen):** architecture `hybridv2` (B1F's class, reused unchanged) at
w96, single seed **2718**, arms = **{MSE, ramp-weighted} × {40, 80, 160} epochs
= 6**. Each loss trains once to 160ep and is snapshotted at the three
milestones; every snapshot is a first-class arm. `ramp-weighted` = b1f's
deployed MSE weighted by `1 + 10·1[ramp]` (train ramp fraction 3.40 % ⇒ ramp
carries 27.9 % of the weighted-MSE mass), BCE gate terms unweighted.

### Headline — per-arm table (held-out, single seed 2718, n = 90,930)

Region fractions **identical to B1C/B1b/B1D/B1E/B1F**: clamp 0.13 %, deadzone
7.80 %, saturation 88.39 %, ramp 3.69 % (ramp n = 3,354).

| arm | loss | w | ep | params | deadzone @5e-2 (boot CI) | ramp @5e-2 (boot CI) | ramp @1e-2 | ramp @1e-3 | learned k | learned a | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `h96_mse_ep40`  | MSE | 96 | 40  | 19,301 | 0.9958 [0.9944,0.9972] | 0.9562 [0.9487,0.9630] | 0.1437 | 0.0125 | 1.4671 | 0.9697 | **PASS** |
| `h96_mse_ep80`  | MSE | 96 | 80  | 19,301 | 0.9999 [0.9996,1.0000] | 0.9943 [0.9917,0.9967] | 0.8679 | 0.1026 | 1.4890 | 0.9715 | **PASS** |
| `h96_mse_ep160` | MSE | 96 | 160 | 19,301 | **1.0000** [1.0000,1.0000] | **0.9979** [0.9961,0.9994] | 0.9535 | 0.8247 | **1.4993** | **0.9991** | **PASS** |
| `h96_rw_ep40`   | ramp-wtd | 96 | 40  | 19,301 | 0.9932 [0.9913,0.9951] | 0.9940 [0.9911,0.9964] | 0.7123 | 0.0733 | 1.4903 | 0.9703 | **PASS** |
| `h96_rw_ep80`   | ramp-wtd | 96 | 80  | 19,301 | 0.9760 [0.9725,0.9795] | 0.9416 [0.9335,0.9496] | 0.6550 | 0.0671 | 1.4966 | 0.9707 | **PASS** |
| `h96_rw_ep160`  | ramp-wtd | 96 | 160 | 19,301 | 0.9886 [0.9862,0.9911] | 0.9502 [0.9430,0.9574] | 0.8784 | 0.0671 | 1.4993 | 0.9842 | **PASS** |
| **_CONTROL_ anchor_cap128** *(linear = B1C cap, C6/C7; reused B1D nets, 3 seeds)* | linear | 128 | 40 | 33,665 | 0.9957 ± 0.0061 | 0.9186 ± 0.1109 | 0.2597 | — | — | — | **PASS** |

Reference cells: **b1f `hybridv2_w64` ramp 0.2930 / dz 0.9848**;
**b1e plain w64 ramp 0.5675**, reweight w64 0.7977; **b1f `linear_plain_w96`
ramp 0.9617 / dz 0.9979**.

### Ramp trajectory across epochs (the frozen headline)

| loss | 40ep | 80ep | 160ep | learned k @40/80/160 |
|---|---|---|---|---|
| **MSE** | 0.9562 | 0.9943 | **0.9979** | 1.467 → 1.489 → **1.499** |
| **ramp-weighted** | **0.9940** | 0.9416 | 0.9502 | 1.490 → 1.497 → **1.499** |

**Best ramp arm overall = `h96_mse_ep160` (0.9979 @5e-2, 0.9535 @1e-2,
0.8247 @1e-3).** No arm is degenerate: every gated CI is narrow and strictly
inside its gate (min deadzone @5e-2 = 0.9760, min ramp @5e-2 = 0.9416).

### Gates (frozen, mechanical)

- **G-B1G1 (the ramp moves) — PASS, 6/6 arms.** Every arm clears
  `ramp@5e-2 ≥ 0.80` **and** bootstrap `CI_low > 0.5175` (= 0.5675 − 0.05).
  The weakest arm (`h96_rw_ep80`, 0.9416, CI_low 0.9335) still sits **0.14 above
  the bar** and **0.42 above the CI floor**.
- **G-B1G2 (no crossing trade-off) — PASS, 6/6 arms.** Every arm keeps
  `deadzone@5e-2 ≥ 0.90` **and** bootstrap `CI_low > 0.90` (min 0.9760,
  CI_low 0.9725). The w96 crossing is intact in every arm.

**Per the frozen mapping (G-B1G1 ∧ G-B1G2) this books:**

> **"the ramp is epochs/loss-shaped after all — B1F's representational call was
> undertrained."**

### Mechanism / honest caveat (recorded, not gate-affecting)

- **The bar is already cleared at the FIRST checkpoint.** `h96_mse_ep40` ramp =
  **0.9562** — i.e. B1F's 0.2930 was measured **below the crossing (w64)** and
  does not reproduce at the crossing width. So the *dominant* lever is
  **capacity / the crossing width itself**, exactly the B1E/B1F "width is the
  threshold" reading — not epochs. Epochs and loss shape then buy **margin**.
- **Epochs buy margin, monotonically (MSE):** ramp 0.9562 → 0.9943 → 0.9979;
  the sharp tail improves most: **@1e-2 0.144 → 0.868 → 0.954**, **@1e-3
  0.013 → 0.103 → 0.825**.
- **Loss shape is a FAST lever, not a deeper one:** ramp-weighting hits 0.9940 at
  **40ep** (what MSE needs 80+ epochs for) but does **not** improve with more
  epochs (0.9940 → 0.9416 → 0.9502) and costs a small deadzone margin
  (0.9932 vs 0.9958 @40ep; 0.9760 at 80ep). Ramp-weighting trades a little
  deadzone for a fast ramp — the trade is **inside** both gates here.
- **The learned atom converges to the law.** Knot **k: 1.467 → 1.489 → 1.499**
  (law **1.5**); slope **a: 0.970 → 0.972 → 0.999** (law **1.0**). The
  "k-offset" B1F blamed (1.35–1.42) is an **undertraining / undersize artifact**:
  given epochs (or width), the atom **learns the law's constants from data** (init
  was a = k = 1.0; 1.5 was never supplied).

## Controls (all pass — no gate number read before these)

| control | result | pass |
|---|---|---|
| C1 law equivalence (switch vs pristine `ai.track`, 4,000 states) | max\|Δ\| = 0 (n_diff 0) | ✅ |
| C4 frame cross-check | bit-identical vs **B1C, B1E, B1b-runB AND B1** (max\|ΔX\| = max\|ΔY\| = max\|ΔMETA\| = **0.0**) | ✅ |
| C6 anchor vs B1C booked `cap@ep40` | max\|Δ\| = **4.7015e-05** (< 0.05) | ✅ |
| C7 anchor re-score vs B1D booked `anchor_cap128` | max\|Δ\| = **0.0** (bit-exact net-reuse proof) | ✅ |

**Safeguards kept (B1D/B1E/B1F):** the verdict code **asserts** the counted set
== the 6 preregistered arms (the anchor is never counted); each Guard window's
`guard_summary.json` is **snapshotted** to `guard_summary.window1.json`.
Reuse declared: B1F driver imported wholesale, B1C engine unchanged, B1D
width-128 anchor nets reused (as in B1F).

## Budget / receipt (no receipt → run VOID)

- **0.7502 Wh measured ≤ 6 Wh envelope** (2,700.7 J), 262.1 s wall / 65.3 GPU-s,
  peak VRAM **125.2 MB**, min free VRAM 5,239 MiB, max temp **62 C**. Receipt
  **`g7-wr-b1g-epochs-vs-ramp-loss-1790905374`** (valid, gate **PASS**).
- **Seat free — no co-tenancy** (pong grind done, 7B evicted).

## What this books

1. **At the crossing width (96) the hybrid-v2 ramp atom gate works.** It clears
   the ramp bar at the **first checkpoint (40ep, 0.9562)** and saturates by 160ep
   (0.9979) — **B1F's "representational" reading was an artifact of measuring at
   w64**, below the crossing.
2. **Both levers close the ramp without breaking the crossing** (G-B1G1 ∧
   G-B1G2, 6/6 arms). **Epochs** buy the sharp tail (@1e-3 0.013 → 0.825);
   **ramp-weighting** buys speed at 40ep (0.9940) and then plateaus. The atom's
   learned constants converge to the law (k → **1.499**, a → **0.999**).
3. **The B1 family closes as CAPACITY-shaped, not representation-limited.** The
   ramp floor is neither sticky nor interface-free — it is the crossing width
   that gates it, with epochs/loss setting the margin.

Artifacts: `results/b1g/` (`regions.json`, `ramp_only.json`, `agreement.json`,
`controls.json`, `result.json`, `run_config.json`, `traces_meta.json`,
`holdout_samples.npz`, `model_hybridv2_w96_{mse,rw}_seed2718_ep{40,80,160}.pt`,
`guard/`). Code: `experiments/b1g_epochs_vs_ramp_loss.py` (imports the B1F
driver wholesale; reuses `experiments/b1c_value_fidelity_engine.mjs` unchanged;
B1D's saved width-128 anchor nets reused for C6/C7). B1/B1b/B1C/B1D/B1E/B1F
artifacts untouched. **NOT COMMITTED.** Next: bisect the **hybrid ramp
atom-gate crossing** {64, 80, 96} (w64 = 0.2930, w96 = 0.9562) to name the
hybrid's own floor — and ask whether the remaining @1e-3 ramp tail (0.825 at
160ep) is closed by a two-knot atom or is the map's intrinsic quantization.
