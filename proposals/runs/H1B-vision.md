# H1B-VISION — prereg (lane H1B-VISION, arm (i) of the H1-WORLDGRAN resurrection fork)

**Frozen before fire.** Author: lane H1B-VISION. Date: 2026-10-01. CPU-only, 0 Wh, no GPU, no guard/watt
receipt required. Budget ≈15 min wall.

## 0. Where this comes from (booked context, not re-litigated)

- **H5-REPAIR** (committed `e0ba4d1`): the D2-V1 measure instability is **distribution-relative**, not
  sampling noise — between-definition variance is **71×–3663×** the world-resample variance; pooled
  resample width ≤ **0.056** on every socket at nW=200, while definition spread reached **0.9237**. All
  three repairs failed the stability gate (`res_std>0 ∧ res_width≤0.15 ∧ def_spread≤0.15`); R3
  paired-world-Δ stabilized only `policy.action` (def 0.081); R3 vision = 0.7594 with **def_spread 0.450**.
- **H1-WORLDGRAN** (committed `a1ae1c6`): determinacy→transfer is DEAD at every granularity. The one
  H5-stable socket (`policy.action`) is **floor-confounded**: its transfer gap is ≈ 0 (+0.0030 ± 0.0236)
  so there is nothing to explain there. `sensors.vision` is the only socket with BOTH a real gap
  (mean **+0.0615, std 0.2185**) AND a significant world-level ρ (**−0.3252**, CI [−0.5803, −0.0566],
  B=1000 seed 2718) — but its per-world scalar **fails the H5 stability gate (def-spread 0.450)**.
- **Booked test (mission):** build an **H5-stable** per-world determinacy measure on `sensors.vision`,
  THEN and only then test ρ. This is **confound-removal**, not a re-roll: the floor confound of
  `policy.action` is removed by moving to a socket with a real gap, but the measure confound must be
  removed first. **This thread dies permanently if the stability gate fails.**

## 1. Question and frozen decision tree

Q0 (G0): **does an H5-stable per-world vision determinacy scalar exist** — i.e. one whose value does not
move > 0.15 when the *definition* is changed, and whose world-resample width is ≤ 0.10?
Q1 (G1, gated on G0 green): **do worlds with higher vision determinacy transfer better**,
ρ ≤ −0.30 with bootstrap CI excluding 0?

```
G0 red   -> TERMINAL: "no H5-stable per-world vision determinacy exists — measure thread closes
             PERMANENTLY."  rho is NOT tested. No resurrection, no re-roll, no third attempt on vision.
G0 green -> report power bar, then test rho.
   G1 green -> H1 RESURRECTED on a stable measure with a real gap.
   G1 red   -> death booking STANDS at higher confidence (floor confound removed, null persisted).
   std==0   -> INCONCLUSIVE (frozen degeneracy rule; never PASS).
```

## 2. Data (reused byte-for-byte, no new data, no GPU)

- `results/d2_v1/d2_v1_traces.json` — 200 worlds × 1000 evals × 19 ints, arms `real`/`sto`.
- `results/d2_v1/d2_v1_twins_result.json` — 60 held-out real test worlds (ids 140..199) × 3 seeds ×
  cond ∈ {real, sim}, `nerr_per_world`.
- Frozen encoders `results/d2_v1/scripts/d2_v1_common.py`; R3 machinery `results/h5_repair/h5_repair.py`
  (`encode_pair`, `det_E3`, `det_E1`, SEED 2718, NPERM 120). Socket: **sensors.vision**
  (`phi_vision(r)=(r[0],r[1])`, `psi_vision(r)=win9(r)`, O=512 ⇒ O_Δ=1023).

**Wiring gate (must pass before any verdict):** my count-based reimplementation of `det_E3`/`det_E1`
must reproduce `H.det_E3`/`H.det_E1` to **< 1e-12** on world 140; and the C1 per-world vector must
reproduce `results/h1_worldgran/h1_worldgran_result.json` `table['sensors.vision']` operational per-world
stats (mean 0.7893 / std 0.2107) to ≤ 5e-4. If the wiring gate fails, the lane reports WIRING-FAIL and
books nothing.

## 3. Per-world determinacy: the R3 paired-world-Δ construction

For world w: `pr` = real cell-bin ids, `ps` = sto cell-bin ids (per-world local factorization of the
joint `(bin_real, bin_sto)` → `ploc`), `yr=ψ(real)`, `ys=ψ(sto)`, `d = ys − yr + (O−1)` (0..1022).
Determinacy = how concentrated the Δ-output distribution is within a Δ-input state, permutation-corrected
(permutation null = the same statistic under a random reshuffle of `d` within the world).

## 4. Candidate family (all evaluated; definitions fixed HERE)

**Gating family `F_gate` — reasonable definitions of the SAME target quantity:**

| id | definition | new? |
|---|---|---|
| `e3_op` | E3 entropy determinacy, **operational** input-bin weight (the incumbent R3 measure) | reference |
| `e3_uni` | E3 entropy determinacy, **uniform** input-bin weight | — |
| `e1_acc` | E1 agreement/accuracy determinacy, **uniform** weight (different estimator, same target) | — |
| `nmi` | **weight-free normalized MI**: `(MI_obs − MI_null)/(H_obs(d) − MI_null)`, clipped [0,1]; permutation-corrected; no weighting knob at all | **new (H5-motivated)** |
| `rank` | **threshold-free rank-based Δ-determinacy**: let `r` = global average-ranks of `d` in the world; `W = Σ_bins Σ_{n∈bin}(r_n − r̄_bin)²`; `det = clip(1 − W_obs/W_null, 0, 1)`; permutation null. Uses no output binning threshold and sample-uniform weighting | **new (H5-motivated)** |

**Reported diagnostics (NOT in the gating spread — they are different constructions, not alternative
definitions of the same scalar):**

| id | definition |
|---|---|
| `e3_deg` | E3 with the **degenerate** weight (all mass on the argmax input bin). Reported because H5's 0.450 vision def-spread included it; excluded from `F_gate` because concentrating a 500-bin world onto one input state is not a tenable determinacy definition. |
| `bits` | **per-output-bit Δ before aggregation**: for each of the 9 window bits, Δbit = ys_b − yr_b + 1 (O=3), E3 uniform, then mean over the 9 bits. |
| `perch` | **per-input-channel Δ before aggregation**: det of `d` from Δx-only then Δy-only, uniform, then mean. |
| `coarse` | collapsed Δ-output sign (O=3), E3 uniform. |

## 5. G0 STABILITY GATE (the gate everything else is conditioned on)

For each variant V: per-world scalar `A_V(w)`, w over 60 held-out worlds; world aggregate `A_V = mean_w`.

- **Non-degeneracy:** `std_w(A_V) > 0` (else INCONCLUSIVE by the frozen law).
- **Resample width `w_V`:** world-resample bootstrap (B=1000, **seed 2718**) of `A_V`; width =
  q97.5 − q2.5. Threshold **≤ 0.10**.
- **Definition spread `D_gate`:** `max_V A_V − min_V A_V` over `V ∈ F_gate`. Threshold **≤ 0.15**
  (H5's own definitional tolerance; vision failed it at 0.450 ≈ 3×).
- (also reported, non-gating: `D_full` over all variants, the op/uni/deg triple-spread, and each variant's
  own width.)

**G0 GREEN ⟺ ∃ V ∈ F_gate with std>0 AND w_V ≤ 0.10 AND D_gate ≤ 0.15.**

**Threshold justification (vs h5_repair's measured spreads):** h5_repair's pooled resample widths were
**≤ 0.056 at nW=200**; the natural n-scaling of a mean's bootstrap width is `4σ/√nW`, and
`√(200/60) = 1.83`, so **0.056 × 1.83 ≈ 0.102 ≈ 0.10** — the ≤0.10 bar is the *n-adjusted equivalent* of
H5's measured precision at our n=60 (it corresponds to `σ_world ≤ 0.194`). The definitional bar is kept
at H5's own **0.15**: that is the number the incumbent vision scalar failed (0.450), so it is the exact
hurdle this lane must clear. Both thresholds are frozen before any candidate value is computed.

**Frozen winner rule (if G0 green):** among passing V's, winner = smallest `w_V`; ties → the V whose `A_V`
is closest to the median of `F_gate` (most representative). Report ρ for **every** passing V
(family-robustness of the G1 verdict).

## 6. G1 (only if G0 green)

`G(w)` = booked twin transfer delta = mean over 3 seeds of (`nerr_sim − nerr_real`) on held-out world w
(60 worlds, out-of-sample). `ρ_W = Spearman(A_winner, G)`, tie-corrected; bootstrap 95% CI from
**B=2000 world-resamples, seed 2718**.

**G1 GREEN ⟺ ρ_W ≤ −0.30 AND CI upper bound < 0 AND std_w(A_winner) > 0.**
Secondary (pre-registered, not gating): same ρ for every other passing V.

**Power bar (reported BEFORE testing ρ):** n = 60 pairs, Fisher-z se = 1/√57 → detectable |ρ| =
**0.355** two-sided / **0.318** one-sided at α=0.05, 80% power; power *at* the bar ρ=−0.30 = **0.756**
one-sided / **0.647** two-sided. The bar −0.30 sits 0.018 below the one-sided 80%-power bar; it is the
mission-specified effect-size gate and is **not moved after seeing ρ**.

## 7. Honesty gates (frozen)

1. **Noise floor of the y-axis.** Report the vision gap's own dispersion (σ = 0.2185 booked) and its
   **seed-mean reliability** (between-world var / (between + within/3) = 0.911 booked from H1-WORLDGRAN
   §3). State explicitly whether **n=60 worth of signal is extractable** given that floor, and report the
   standard error of the mean gap. If the per-world gap were seed-noise, G1 would be uninterpretable —
   the reliability number is the receipt that it is not.
2. **std == 0 ⇒ INCONCLUSIVE** (frozen degeneracy rule) on any deciding statistic; never PASS.
3. If G0 is red, **ρ is not computed at all** — no exploratory ρ may be reported as a finding.
4. Every candidate's raw value is written to JSON so the family spread can be audited.
5. Interpretation risk pre-disclosed: if the mission intended the definition spread over *all*
   constructions (incl. `bits`/`perch`/`coarse`), the gating spread `D_full` is reported alongside
   `D_gate`; the gating reading is `F_gate` as tabulated above.

## 8. Verdict tree and booked sentences (frozen)

- **G0 red** → TERMINAL booking:
  > *"No H5-stable per-world vision determinacy exists — the measure thread closes PERMANENTLY."*
- **G0 green, G1 green** →
  > *"H1 RESURRECTED on a stable measure with a real gap."*
- **G0 green, G1 red** →
  > *"Death booking STANDS at higher confidence: the floor confound was removed and the null persisted."*

## 9. Artifacts

`results/h1b_vision/{h1b_vision.py, h1b_vision_result.json, h1b_vision_run.out, RESULTS-ENTRY.md}`;
RESULTS.md entry; QUEUE.md line. **NOT COMMITTED** (per mission).
