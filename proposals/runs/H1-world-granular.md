# H1-WORLDGRAN — H1 re-derived at WORLD granularity (lane H1-WORLDGRAN)

**Frozen before fire.** 2026-10-01 17:2x AKDT. CPU-only, 0 Wh, no GPU. Follow-up to H5-REPAIR.

## 0. Motivation (the booked hand-off)

H5-REPAIR proved the D2-V1b "determinacy" measure is **distribution-relative**, not a socket-level
static: the between-definition spread (0.076–0.924) is 71–3663× the world-resample spread (≤0.056).
H5's consequence line was: *the 1000-world ×5 extension stays FROZEN (no stable scalar to buy precision
for), and **H1 should be re-derived at WORLD granularity (60 points) where the conditioning is explicit
and the distribution is the world's own**.* This lane executes exactly that hand-off.

H1 (corpus-level, D2-V1) was **ρ(per-socket determinacy, per-socket transfer gap) = −0.371 [−0.600, 0.486]**
over **n=6 sockets** — FAIL (CI straddles 0; and n=6 is hopeless for a −0.60 bar). The question here is
different and stronger: not "do sockets with higher determinacy transfer better", but **"within a fixed
socket, do worlds with higher determinacy transfer better"** — where the world's own empirical
distribution *is* the conditioning, so the H5 distribution-relativity objection cannot bite.

## 1. Inputs (reused byte-for-byte; no new data, no GPU)

- `results/d2_v1/d2_v1_traces.json` — 200 paired worlds (real & sto), i = 0..199, 1000 evals × 19-int.
- `results/d2_v1/d2_v1_twins_result.json` — the 60 held-out test worlds (i = 140..199) × 3 seeds
  (2718/2719/2720) × conditions {real, sim, sim_mis}, `nerr_per_world` per world.
- Code reuse **wholesale**: `results/h5_repair/h5_repair.py` (E3 estimator, encoders via
  `results/d2_v1/scripts/d2_v1_common.py`), same `SEED = 2718`, same `NPERM = 120`. No estimator is
  re-derived here; only the *granularity* of the summary changes (per-socket → per-world).

## 2. Frozen definitions

**Per-world determinacy** `D_s(w)` (the H5-**R3 paired-world delta** measure, computed WITHIN world w):
for socket s with declared I/O (φ, ψ, O), and paired worlds (real_w, sto_w) each with 1000 ticks,
factor the 1000 within-world pairs `(φ(real_i), φ(sto_i))` locally (exact: φ bins are injective), and
measure the E3 determinacy of the **Δout** channel `ψ(sto_i) − ψ(real_i) + (O−1)` against that pair
factorization. E3 = 1 − observed/pooled-permutation-null conditional entropy, `operational` weight.
`D_s(w) = det_E3(ploc_w, d_w, Bnw, 2O−1, "operational", SEED + w, NPERM=120)`.

> **Why R3 and only R3 is measure-valid here.** H5-REPAIR's stability gate (res_std>0 ∧ res_width≤0.15
> ∧ def_spread≤0.15) is passed by **R3 on policy.action only** (def_spread **0.081**, down from the
> D2-V1 0.924). R3 fails on the other five (surprise 0.663 · vision 0.450 · semantic 0.355 · episodic
> 0.151 · reflex std==0). So **the primary per-world test is a single socket: `policy.action`**; the
> other five sockets' per-world ρs are reported as **EXPLORATORY (their per-world scalar inherits R3's
> definition-fragility)** with the fragility flagged. This asymmetry is fixed BEFORE looking at any ρ.

**Per-world transfer gap** `G_s(w)` = the booked twin transfer delta on world w:
`G_s(w) = mean over the 3 seeds of ( nerr_sim(seed, w) − nerr_real(seed, w) )` (positive ⇒ the sim-trained
twin transfers *worse* on that world). Twins were trained on real_tr/sto_tr (i < 140) and evaluated on the
60 held-out worlds (i ≥ 140), so `G_s` is out-of-sample per world.

## 3. Primary test (n = 60 paired worlds)

`ρ_W = Spearman( D_policy.action(w) , G_policy.action(w) )`, w over the 60 held-out worlds.
CI: 1000 bootstrap world-resamples (seed 2718), **tie-corrected (average-rank) Spearman**.
Null: H1-W is directional (expected negative, as in H1).

## 4. Power analysis — REPORTED BEFORE TESTING (bar justification)

Two-sided α = 0.05, power 0.80, n = 60 (Fisher-z, se = 1/√(n−3) = 1/√57):

| test | detectable \|ρ\| |
|---|---|
| two-sided α=0.05, 80% power | **0.355** |
| one-sided α=0.05, 80% power (directional — correct here) | **0.318** |

Power at the mission bar ρ = −0.30: **one-sided ≈ 0.756 · two-sided ≈ 0.647.**

> **Honest consequence (pre-registered):** the mission bar **|ρ| ≥ 0.30 is marginally below the
> power-justified bar** (0.318 one-sided / 0.355 two-sided at 80% power). A true ρ = −0.30 is detected
> only ~76% of the time one-sided. We therefore **pre-register the mission bar −0.30 as the effect-size
> gate** (task-specified, and only 0.018 below the one-sided 80%-power bar), and **additionally report the
> verdict at the power bar |ρ| ≥ 0.318 (one-sided)** so the reader can see both readings. We do **not**
> move the bar after seeing ρ.

## 5. Gate G-W1 (frozen tree)

- **std==0 guard:** if `std(D_policy.action)` across the 60 worlds == 0 → **INCONCLUSIVE** (never PASS).
- **PASS (H1-W survives):** `ρ ≤ −0.30` **and** CI95 upper bound `< 0` →
  book *"H1 survives at world granularity — determinacy buys transfer where distributions are matched."*
- **SIGN-REVERSAL (anti-selection guard):** `ρ ≥ +0.30` **and** CI95 lower `> 0` →
  book *"the determinacy→transfer sign REVERSES at world granularity"* (reported, not forced into either
  fixed sentence).
- **DEATH:** otherwise (|ρ| < 0.30, or CI includes 0) →
  book *"no world-level relationship either — the determinacy→transfer story is dead at every granularity."*

Also recorded: the power-bar reading, and the same ρ under the three definition weights
(operational / uniform / degenerate) as a robustness band for the primary.

## 6. Secondary / descriptive (pre-registered, exploratory)

1. **6-socket × world-level ρ table** — `ρ_W` per socket (policy.action primary; the other five flagged
   EXPLORATORY, with each socket's R3 def_spread reproduced alongside).
2. **Variance-exists check** — per-world determinacy distribution per socket (n, mean, std, min, max,
   range, #distinct). If std == 0 there is nothing to correlate (→ INCONCLUSIVE for that socket).
3. **Gap distribution** per socket (mean, std, range) to show scale.
4. Reference: the corpus-level H1 ρ (−0.371) and H5's G-H5b R3 ρ (−0.257) for continuity.

## 7. Discipline / non-goals

- No new traces, no GPU, no estimator change, seed fixed at 2718 (H5 lineage).
- No post-hoc bar movement; no socket selected on observed ρ (primary named above by the *H5 stability
  gate*, not by results).
- Artifacts: `results/h1_worldgran/{h1_worldgran.py, h1_worldgran_result.json, h1_worldgran_run.out,
  RESULTS-ENTRY.md}`. **NOT COMMITTED.**
