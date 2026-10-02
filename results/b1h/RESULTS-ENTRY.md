# B1H — NAME THE HYBRID'S OWN RAMP FLOOR & THE TWO-KNOT ATOM TEST (the B1-family coda)

Lane **B1H-CODA** (prereg `proposals/runs/B1H-coda.md`, frozen 2026-10-01 18:3x
AKDT, before fire). 2026-10-01. **NOT COMMITTED.** The **B1-family coda**,
booked at B1G's landing.

## Verdict: **KILL (TAIL-QUANTIZED)** — the hybrid's own ramp floor is **w72**; the two-knot atom does **not** buy the @1e-3 tail (it *costs* it 0.41) → **B1 closes with the tail booked as a limit**

B1G reversed B1F (the ramp is epochs/loss-shaped, not representational) and
named the **crossing width** as the dominant lever, leaving two follow-ups: name
the **hybrid's own** ramp atom-gate floor, and test whether the residual @1e-3
ramp tail (`h96_mse_ep160` = 0.8247) is **interface-shaped** (a two-knot atom
buys it) or the **map's intrinsic quantization**.

**Design (frozen):** B1G driver imported **wholesale**, B1C engine **unchanged**;
single seed **2718**, loss **MSE** (B1G's deployed objective verbatim), **160ep**
(B1G's best recipe). Arms (5): **Part A** bisection `{64, 72, 80, 88}`; **Part B**
`w96_2knot_ep160` — `HybridV2MLP` with the ramp atom replaced by a **two-knot**
piecewise linear `sign(b−p)·[a1·relu(u−k1) + a2·relu(u−k2)]`, `k2 =
k1 + softplus(gap) > k1` (**structural**), `a2` **init 0** so the first forward is
**bit-identical** to the single-knot family (RNG-identical init for seed 2718).
Part B baseline = **B1G's reused** `h96_mse_ep160` checkpoint > **paired**
bootstrap on the ramp region.

### Part A — the hybrid's own ramp floor = **72** (held-out, seed 2718, boot CI)

Region fractions identical to the family: clamp 0.13 %, deadzone 7.80 %,
saturation 88.39 %, ramp 3.69 % (ramp n = 3,354).

| arm (hybridv2, MSE, 160ep) | w | params | deadzone @5e-2 (CI) | **ramp @5e-2 (CI)** | ramp @1e-2 | ramp @1e-3 | learned k1 | learned a1 | clears |
|---|---|---|---|---|---|---|---|---|---|
| `w64_mse_ep160` | 64 | 8,773 | 0.9748 [0.9709,0.9784] | 0.8933 [0.8831,**0.9034**] | 0.2361 | 0.0119 | 1.5120 | 1.0027 | ✗ (CI_low < 0.90) |
| `w72_mse_ep160` | 72 | 11,021 | 0.9779 [0.9746,0.9811] | **0.9401 [0.9317,0.9484]** | 0.7513 | 0.0200 | 1.5010 | 0.9846 | ✅ |
| `w80_mse_ep160` | 80 | 13,525 | 0.9784 [0.9752,0.9818] | 0.8852 [0.8745,0.8962] | 0.0686 | 0.0072 | 1.5193 | 0.9694 | ✗ |
| `w88_mse_ep160` | 88 | 16,285 | **1.0000 [1.0000,1.0000]** | **0.9997 [0.9991,1.0000]** | 0.9750 | 0.7976 | 1.5006 | 1.0016 | ✅ |
| *ref* `h96` (B1G, reused) | 96 | 19,301 | 1.0000 | 0.9979 | 0.9535 | 0.8247 | 1.4993 | 0.9991 | ✅ |

**Named hybrid floor = 72** (smallest width with `ramp@5e-2 ≥ 0.90` **and**
`CI_low > 0.90` **and** deadzone intact). **Non-monotone: w80 is a local trough**
(0.8852, CI [0.8745,0.8962], non-overlapping with w72's CI) — the crossing rises
to w72, dips at w80, then saturates at w88. Pairing: B1F's hybrid w64 40ep
**0.2930** → B1H's w64 160ep **0.8933** (epochs moved w64 a lot but it still does
**not** clear 0.90); plain references b1e w64 0.5675, b1f w96 0.9617. So the
**hybrid floor (72) sits below the plain crossing (96)** — the hybrid atom-gate
recovers the ramp at *less* width than the linear head, but only ~24 units less,
and not monotonically.

### Part B — two-knot atom: **fails, and backwards** (paired, ramp n = 3,354)

| atom | ramp @5e-2 | ramp @1e-3 | deadzone @5e-2 | params | learned |
|---|---|---|---|---|---|
| **single-knot** (B1G `h96_mse_ep160`, reused) | 0.9979 | **0.8247** | 1.0000 | 19,301 | k1 **1.4993**, a1 0.9991 |
| **two-knot** `w96_2knot_ep160` | 0.9982 | **0.4174** | 1.0000 | 19,303 (+0.010 %) | k1 1.5029, a1 1.0067, **a2 −0.0198**, **k2 3.0886** |

**Paired gain @1e-3 = −0.4073, CI [−0.4246, −0.3888]** (boot_std 0.0094, B=1000,
seed 2718) — CI **excludes 0 on the negative side**: the second knot **costs**
≈0.41 of the sharp tail. Deadzone stays 1.0000 (no regression) and the 5e-2
crossing is untouched (0.9982). **G-B1H2 FAIL** (bar was gain ≥ +0.05, CI excl 0).

**Learned-knots story (the mechanism):** the two-knot atom **found the law's
single knot** (k1 = 1.5029 vs law 1.5; a1 = 1.0067 vs law 1.0) — and then **made
the second knot inert and pushed it out of the band**: a2 = −0.0198 (≈0), k2 =
**3.0886**, which lands **beyond the saturation edge** (ramp band is
u ∈ (1.5, ≈2.35)). The optimizer did **not** want a second break; it wanted the
single law knot. The extra atom freedom therefore did not add expressiveness where
the tail lives — it re-routed the composition (gates + regression head + atom
blend) into a basin with a **worse** sharp tail at equal 5e-2/1e-2-ish bulk.
**The @1e-3 tail is not an atom-shape deficit** — it is the residual of the whole
deployed map (gate blending + head), i.e. **quantization of the map, not a missing
interface knot**.

## Controls (all pass — no gate number read before these)

| control | result | pass |
|---|---|---|
| C1 law equivalence (switch vs pristine `ai.track`, 4,000 states) | max\|Δ\| = 0 (n_diff 0) | ✅ |
| C4 frame cross-check | bit-identical vs **B1C, B1E, B1b-runB AND B1** (max\|ΔX\| = max\|ΔY\| = max\|ΔMETA\| = **0.0**) | ✅ |
| C6 anchor vs B1C booked `cap@ep40` | max\|Δ\| = **4.7015e-05** (< 0.05) | ✅ |
| C7 anchor re-score vs B1D booked `anchor_cap128` | max\|Δ\| = **0.0** (bit-exact net-reuse proof) | ✅ |

**Safeguards kept (B1D/B1E/B1F/B1G):** the verdict code **asserts** the counted
set == the 5 preregistered arms (anchor + single-knot ref never counted); each
Guard window's `guard_summary.json` is **snapshotted** to
`guard_summary.window1.json`. Reuse declared: B1G driver imported wholesale,
B1C engine unchanged, B1D width-128 anchor nets reused (C6/C7), B1G's
`h96_mse_ep160` checkpoint reused as the Part B single-knot arm.

## Budget / receipt (no receipt → run VOID)

- **1.4203 Wh measured ≤ 3 Wh envelope** (5,112.97 J), 285.3 s wall / 91.7 GPU-s,
  mean power 17.92 W, peak VRAM **123.5 MB**, min free VRAM 5,344 MiB, max temp
  **61 C**. **INSTRUMENT-01 ramp 0.657 s synced** before the measured window.
  Receipt **`g7-wr-b1h-coda-1790908561`** (valid, gate **PASS**).
- **Seat free — no co-tenancy.**

## What this books

1. **The hybrid's own ramp atom-gate floor is w72** (ramp@5e-2 ≥ 0.90 with
   CI_low > 0.90 and the deadzone intact) — *below* the plain crossing (w96), so
   the ramp atom-gate buys the ramp at less width than the linear head. The
   crossing is **non-monotone** (w80 trough) — at this seed the "floor" is a
   by-width curve, not a step.
2. **The @1e-3 ramp tail is NOT interface-shaped.** A two-knot atom (structurally
   ordered, budget-neutral, bit-identical at init) **lowered** the sharp tail
   **−0.4073 CI[−0.4246,−0.3888]** while leaving the 5e-2 crossing and the
   deadzone untouched; its learned solution is the **law's single knot**
   (k1 1.5029, a1 1.0067) plus an **inert** second knot parked outside the band
   (a2 −0.0198, k2 3.0886). **Per the frozen mapping this books:**
   > **"the tail is the map's intrinsic quantization — B1 closes with the tail
   > booked as a limit."**
3. **The B1 family closes.** Capacity/crossing width gates the ramp (B1G); the
   ramp atom-gate names its own floor at **w72**; and the residual sharp tail is
   the composed map's floor, not a missing knot. No further atom-shape work is
   booked.

Artifacts: `results/b1h/` (`crossing.json`, `tail.json`, `regions.json`,
`controls.json`, `result.json`, `run_config.json`, `traces_meta.json`,
`holdout_samples.npz`, `model_{w64,w72,w80,w88}_mse_seed2718_ep160.pt`,
`model_w96_2knot_seed2718_ep160.pt`, `guard/`). Code:
`experiments/b1h_coda.py` (imports the B1G driver wholesale; reuses the B1C
engine unchanged; B1D anchor nets + B1G checkpoint reused). B1/B1b/B1C/B1D/B1E/
B1F/B1G artifacts untouched. **NOT COMMITTED.** Next: none for B1 — the family
is closed. If the sharp tail ever matters again, it is a **composition** question
(gate blending / head), not an atom-shape question: test the `g_r`/`g_dz` blend
or a hard-routed (non-blended) ramp branch, not another knot.
