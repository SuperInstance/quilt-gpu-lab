# B1F — NAME THE CROSSING & IS THE RAMP AN INTERFACE PROBLEM TOO?

Lane **B1F-CROSSING-AND-RAMP-INTERFACE** (prereg
`proposals/runs/B1F-crossing-and-ramp-interface.md`, frozen 2026-10-01 16:5x
AKDT, before fire). 2026-10-01. **NOT COMMITTED.**

## Verdict: **KEEP** — the linear-head crossing is **96** (plain), **80 under the reweight**; the ramp is **REPRESENTATIONAL** (it resists a ramp-shaped atom gate)

B1E left the linear-head floor bracketed **(64, 128]**. B1F (a) **bisects the
crossing** {80, 96} under the plain linear head, adds **`linear reweight w80`**
to test whether the B1C region-reweight at width 80 clears the ramp gate, and
(b) builds **hybrid head v2** — the regression body **plus atom gates for BOTH
regions** (the B1D deadzone atom gate **and a ramp atom gate**, a ramp-shaped
output piecewise-linear in the cue) — at **width 64** to ask whether the ramp,
too, is an **interface** problem. 4 arms × 3 seeds (2718–2720), 40ep only,
bit-identical B1/B1b/B1C frame; B1C engine reused unchanged; B1D's saved
width-128 anchor nets reused for controls C6/C7.

### Q1 — the crossing is named: **96 plain / 80 reweight**

- **`linear_plain_w80` FAILS** (deadzone 0.8496 ± 0.1132, ramp 0.6961 ± 0.1702).
- **`linear_plain_w96` PASSES** (deadzone **0.9979 ± 0.0010**, ramp
  **0.9617 ± 0.0054**) → **the plain linear-head capacity crossing at 40ep is 96**
  (floor ∈ (80, 96]).
- **`linear_reweight_w80` PASSES** (deadzone **0.9917 ± 0.0118**, ramp
  **0.9656 ± 0.0484**) → **the region-reweight at width 80 clears BOTH gates**,
  dropping the effective crossing from 96 to **80**. On the ramp alone the
  reweight is worth **+0.2695** over plain w80 (0.6961 → 0.9656); on the deadzone
  **+0.1421** (0.8496 → 0.9917). This is the same B1C mechanism that B1E showed
  lifting ramp at w64 (0.5675 → 0.7977), now clearing the gate.

### Q2 — the ramp is **REPRESENTATIONAL**: the ramp atom gate fails at w64

**`hybridv2_w64`**: deadzone **0.9848 ± 0.0195 (PASS)** but ramp
**0.2930 ± 0.0804 (FAIL)** — and ramp @1e-2 is only **0.0541**. Per the frozen
mechanical rule (deadzone PASS + ramp FAIL) the booked sentence is:

> **"the ramp resists the ramp atom gate; the ramp is genuinely representational
> at 40ep."**

This is a **stronger** negative than B1D's single-gate hybrid (which reached
ramp 0.8042 by leaving the ramp to its regression head): handing the interface
the **ramp's own piecewise-linear shape family** at w64 made the ramp **worse**
than the plain w64 regression head (0.2930 vs B1E's 0.5675). The learned atom
constants landed near — but not at — the law's: **slope `a` ≈ 0.963, knot
`k` ≈ 1.35–1.42** (law: `a = 1`, `k = 1.5`; atom init was `a = k = 1.0`, so the
1.5 knot was **learned from data**, never supplied). The ramp cue band is narrow
(u ∈ (1.5, 2.35)), so a ~0.1 knot offset is worth > 5e-2 over most of the band;
meanwhile the deadzone multiply `(1 − g_dz)` bleeds across the shared u ≈ 1.5
deadzone/ramp boundary and damps the ramp output toward 0 — consistent with the
near-total ramp@1e-2 collapse (0.0541) while the deadzone gate stays sharp
(deadzone@1e-2 = 0.9344). **So: the ramp is not closed by an interface we give
it — at 40ep it is representation-bound (and, for this composition, the atom
actively costs the ramp).** The deadzone, by contrast, **is** an interface
problem (B1D's atom gate: 0.9998; here 0.9848).

## Per-region table (held-out, 3-seed mean ± std) — the headline

Holdout n = 90,930; region fractions **identical to B1C/B1b/B1D/B1E**: clamp
0.13 %, deadzone 7.80 %, saturation 88.39 %, ramp 3.69 %.

| arm | kind | w | params | deadzone @5e-2 | ramp @5e-2 | sat @5e-2 | dz @1e-2 | ramp @1e-2 | verdict |
|---|---|---|---|---|---|---|---|---|---|
| linear_plain_w80 | linear | 80 | 13,361 | 0.8496 ± 0.1132 | 0.6961 ± 0.1702 | 0.9953 | 0.1874 | 0.1537 | FAIL |
| linear_plain_w96 | linear | 96 | 19,105 | **0.9979 ± 0.0010** | **0.9617 ± 0.0054** | 0.9998 | 0.5081 | 0.3411 | **PASS** |
| linear_reweight_w80 | linear | 80 | 13,361 | **0.9917 ± 0.0118** | **0.9656 ± 0.0484** | 0.9999 | 0.6439 | 0.4743 | **PASS** |
| hybridv2_w64 | hybridv2 | 64 | 8,773 | **0.9848 ± 0.0195** | 0.2930 ± 0.0804 | 0.9966 | 0.9344 | 0.0541 | FAIL (deadzone clears; ramp short) |
| **_CONTROL_ anchor_cap128** *(linear = B1C cap, C6/C7; REUSED nets from B1D)* | anchor | 128 | 33,665 | 0.9957 ± 0.0061 | 0.9186 ± 0.1109 | 0.9992 | 0.6013 | 0.2597 | **PASS** |

No arm is degenerate: every gated std > 0 (min 0.0010) → **no INCONCLUSIVE**.

## Ramp-only table (the frozen headline) — ramp-region fidelity

| arm | w | ramp @5e-2 | ramp @1e-2 | ramp @1e-3 | clears ramp gate @5e-2 |
|---|---|---|---|---|---|
| linear_plain_w80 | 80 | 0.6961 ± 0.1702 | 0.1537 ± 0.0424 | 0.0144 | no |
| linear_plain_w96 | 96 | 0.9617 ± 0.0054 | 0.3411 ± 0.1162 | 0.0356 | **yes** |
| **linear_reweight_w80** | 80 | **0.9656 ± 0.0484** | **0.4743 ± 0.3034** | 0.0473 | **yes (best)** |
| hybridv2_w64 | 64 | 0.2930 ± 0.0804 | 0.0541 ± 0.0162 | 0.0055 | no |

**Best ramp arm = `linear_reweight_w80` (0.9656 @5e-2).** The ramp closes by
**capacity (96) or by reweight at 80** — never by the ramp atom gate.

## Controls (all pass — no gate number read before these)

| control | result | pass |
|---|---|---|
| C1 law equivalence (switch vs pristine `ai.track`, 4,000 states) | max\|Δ\| = 0 (n_diff 0) | ✅ |
| C4 frame cross-check | bit-identical vs **B1C, B1E, B1b-runB AND B1** (max\|ΔX\| = max\|ΔY\| = max\|ΔMETA\| = **0.0**) | ✅ |
| C6 anchor vs B1C booked `cap@ep40` | max\|Δ\| = **4.7015e-05** (< 0.05) | ✅ |
| C7 anchor re-score vs B1D booked `anchor_cap128` | max\|Δ\| = **0.0** (bit-exact net-reuse proof) | ✅ |

**Safeguards kept (B1D/B1E):** the verdict code **asserts** the counted set ==
the 4 preregistered arms (the anchor is never counted); each Guard window's
`guard_summary.json` is **snapshotted** to `guard_summary.window1.json`.

## Budget / receipt (no receipt → run VOID)

- **3.7494 Wh measured ≤ 6 Wh envelope** (13,497.9 J), 370 s wall / ~250 GPU-s,
  peak VRAM **121.8 MB**, max temp ≤ 80 C. Receipt
  `g7-wr-b1f-crossing-and-ramp-in-1790902708` (valid, gate **PASS**).
- Co-tenancy declared: the 7B ollama seat + the pong grind held the card.

## What this books

1. **The linear-head crossing is 96 at 40ep** (plain); **region-reweight moves
   the crossing down to 80** — capacity and signal each buy a step of the floor,
   agreeing with B1E that the width story is the threshold and the head/signal
   story is the margin.
2. **The ramp is genuinely representational at 40ep.** A two-region atom-gate
   interface (deadzone gate + ramp atom) at w64 clears the deadzone (0.9848) and
   **fails the ramp (0.2930)** — worse than plain regression at the same width.
   **The deadzone is an interface problem; the ramp is not.**
3. Naming the crossing closes the B1E bracket: floor ∈ (80, 96] plain, and
   **≤ 80 with the reweight**.

Artifacts: `results/b1f/` (`regions.json`, `ramp_only.json`, `agreement.json`,
`controls.json`, `result.json`, `run_config.json`, `traces_meta.json`,
`holdout_samples.npz`, `model_*_seed{2718,2719,2720}_ep40.pt`, `guard/`).
Code: `experiments/b1f_crossing_ramp_interface.py` (imports the B1D/B1C drivers;
reuses `experiments/b1c_value_fidelity_engine.mjs` **unchanged**; B1D's saved
width-128 anchor nets reused for C6/C7). B1/B1b/B1C/B1D/B1E artifacts untouched.
**NOT COMMITTED.** Next: does the ramp close at all given *more* epochs (the
300ep regime is std==0 → the budget, not the interface, may be the wall), or is
a ramp-specific *loss* (not head) the missing lever?
