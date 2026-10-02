# H1B-VISION — RESULTS (lane H1B-VISION, arm (i) of the H1-WORLDGRAN resurrection fork, 2026-10-01 17:4x AKDT)

Prereg: `proposals/runs/H1B-vision.md` (frozen before fire). **CPU-only, 0 Wh, no GPU** (no guard/watt
receipt required). Reuses byte-for-byte `results/d2_v1/d2_v1_traces.json`, `results/d2_v1/d2_v1_twins_result.json`,
the frozen encoders (`d2_v1_common.py`), and the R3 machinery (`h5_repair.py`: `encode_pair`, `det_E3`,
`det_E1`, SEED 2718, NPERM 120). Script `results/h1b_vision/h1b_vision.py`. **Wall 41.3 s.**

## The booked question
`policy.action` (the only H5-stable socket) is **floor-confounded** — its transfer gap is ≈ 0
(+0.0030 ± 0.0236), so H1 cannot be tested where its measure is valid. `sensors.vision` is the only socket
with **both a real gap (+0.0615 ± 0.2185) AND a significant world-level ρ (−0.3252 [−0.5803, −0.0566])** —
but its per-world scalar **fails the H5 stability gate (def-spread 0.450)**. Mission: build an
**H5-stable** per-world vision determinacy measure, THEN and only then test ρ. **Dies permanently if the
stability gate fails.**

## 0. Wiring gate PASS (before any verdict)
My count-based reimplementation of `det_E3`/`det_E1` reproduces `H.det_E3`/`H.det_E1` on world 140 across
all three weights to **max |Δ| = 5.274e-16**. The reference candidate `e3_op` reproduces
`results/h1_worldgran/...`'s booked `sensors.vision` operational per-world stats **exactly** (mean 0.7893,
std 0.2107). Pair-bin count 1…501.

## 1. G0 STABILITY GATE — candidate family on `sensors.vision` (R3 paired-world-Δ)

Per-world determinacy = R3 paired-Δ construction (`ploc` = per-world local factorization of the joint
(real-cell, sto-cell); `d = ψ(sto) − ψ(real) + 511`, 0..1022), aggregate = mean over the **60 held-out
worlds** (ids 140..199); **resample width** = world-resample bootstrap (B=1000, seed 2718) of the aggregate;
**D** = definition spread max−min over the family.

| variant | definition | agg | world std | resample width | gating |
|---|---|---|---|---|---|
| `e3_op` | E3 entropy det, operational weight (**incumbent R3**) | 0.7893 | 0.2107 | **0.1089** ✗ | yes |
| `e3_uni` | E3 entropy det, uniform weight | 0.3926 | 0.4090 | 0.2078 ✗ | yes |
| `e1_acc` | E1 agreement det, uniform (different estimator) | 0.1009 | 0.1764 | **0.0888 ✓** | yes |
| `nmi` | **weight-free normalized MI** (permutation-corrected) | 0.5280 | 0.3614 | 0.1903 ✗ | yes |
| `rank` | **threshold-free rank-based Δ-det** (within-bin rank dispersion) | 0.5166 | 0.4295 | 0.2210 ✗ | yes |
| `e3_deg` | E3 with degenerate (argmax-bin) weight — *reported, non-gating* | 0.8591 | 0.1814 | 0.0895 | diag |
| `bits` | **per-output-bit Δ before aggregation** (9 bits, O=3) — *diag* | 0.5226 | 0.3513 | 0.1706 | diag |
| `perch` | **per-input-channel Δ before aggregation** (Δx-only, Δy-only) — *diag* | 0.3029 | 0.4274 | 0.2258 | diag |
| `coarse` | collapsed Δ-output sign (O=3) — *diag* | 0.5510 | 0.4006 | 0.1987 | diag |

- **D_gate = 0.6884** (gating family) · **D_full = 0.7582** (all nine) · **D_triple(op/uni/deg) = 0.4665**
  — the last one **reproduces H5-REPAIR's booked R3-vision def-spread 0.450 on a fully disjoint
  subsample (60 held-out worlds)**, confirming the instability is intrinsic, not a subsample artefact.
- **Decisive minimal-family check: the two most reasonable weights alone span 0.3967** (`e3_op` 0.7893 vs
  `e3_uni` 0.3926) — the ≤0.15 bar is already missed *before* any exotic construction is considered.
- Only **`e1_acc`** clears the width bar (0.0888 ≤ 0.10) — and it is a *different estimator* whose value
  (0.1009) sits near its own floor, ~0.69 away from `e3_op`. `e3_op` itself **fails width** (0.1089).

**G0 = RED.** (∃ width-passer = `e1_acc`, but `D_gate` 0.6884 ≫ 0.15 ⇒ no candidate passes the conjunction.)

## 2. VERDICT — G0-RED-TERMINAL (frozen tree)

Per the frozen tree, **ρ is NOT tested** (no exploratory ρ may be reported as a finding). Booked:

> **"No H5-stable per-world vision determinacy exists — the measure thread closes PERMANENTLY."**

## 3. Honesty gates

- **Noise floor of the y-axis (the gap):** vision gap mean **+0.0615**, std **0.2185**, sem **0.0282**
  (mean = **2.18σ** from 0); seed-mean reliability **0.911** booked (between-world var 3.40× the within-world
  var, H1-WORLDGRAN §3). So **n=60 of signal IS extractable on the y-axis** — the termination is a statement
  about the **x-axis (the measure)**, not about a missing transfer gap. That is the point: this socket had a
  real gap and still could not be given a stable measure.
- **No std==0 degeneracy** on any deciding statistic (min world std 0.1764 on a gating variant); the
  INCONCLUSIVE branch was not reached.
- All candidate raw per-world scalars are written to JSON (`candidates[*].per_world`) so the family spread
  is auditable.
- Interpretation risk pre-disclosed and reported: `D_full` (over *all* constructions) = 0.7582 vs
  `D_gate` = 0.6884 — both far above tolerance, so the red verdict is insensitive to which family reading
  is used.
- **Why the new H5-motivated constructions did not rescue it:** the instability is not an artefact of the
  entropy estimator or of output binning — the weight-free `nmi` (0.1903), the threshold-free `rank`
  (0.2210), and the count-sparsity-killing `bits` (0.1706) all scatter just as widely across definitions
  (and, for `bits`/`perch`, land far from the incumbent value). The measure is distribution-relative in a
  way no re-definition at this granularity repaired.

## 4. Power bar (pre-registered; moot — ρ not tested)
n=60, Fisher-z se=1/√57: detectable |ρ| = **0.355** two-sided / **0.318** one-sided (α=0.05, 80% power);
power *at* the bar ρ=−0.30 = **0.756** one-sided / **0.647** two-sided. Reported as required; carried
forward for any future socket that clears G0.

## 5. Continuity and consequences
- Corroborates **H5-REPAIR** (`e0ba4d1`): instability is **distribution-relative**, not sampling noise; the
  R3 repair stabilized only `policy.action` (def 0.081) and leaves vision at 0.45 — here 0.4665.
- Corroborates **H1-WORLDGRAN** (`a1ae1c6`): the determinacy→transfer death stands; its §6 next-question
  branch **(i) is now closed** — no stable per-world vision measure exists. Branch **(ii)** (engineer a
  transfer stressor on `policy.action`, where the measure *is* stable) is the only surviving path to a
  testable H1 at world granularity.
- **Per the mission, the vision measure thread is now CLOSED PERMANENTLY** — no re-roll, no third attempt.

## 6. Repro / artifacts
`results/h1b_vision/{h1b_vision.py, h1b_vision_result.json, h1b_vision_run.out, RESULTS-ENTRY.md}`.
Prereg `proposals/runs/H1B-vision.md`. CPU-only 0 Wh, wall 41.3 s, no GPU. **NOT COMMITTED.**

## 7. Next question
Does a transfer stressor on `policy.action` (widening the sim→real shift until its gap leaves the floor,
where the R3 measure is *already* stable at def-spread 0.081) finally host a testable ρ — or is H1 dead at
world granularity even where both axes are clean?
