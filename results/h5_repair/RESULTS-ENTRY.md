# H5-REPAIR — RESULTS (lane H5-REPAIR, 2026-10-01 17:0x–17:2x AKDT)

Prereg: `proposals/runs/H5-measure-repair.md` (frozen before fire). **CPU-only, 0 Wh, no GPU**
(traces sufficient — GPU lane never opened; no guard.py needed, no watt receipt: no GPU).
Inputs reused byte-for-byte: `results/d2_v1/d2_v1_traces.json` (200 worlds × 1000 evals × 19-int,
arms real/sto) + `results/d2_v1/d2_v1_twins_result.json` (60 held-out real test worlds × 3 seeds × 3
conditions). Baseline **reproduced exactly** against `d2_v1_result.json.determinacy` (e.g. policy.action
op-det 0.9012 ✓, memory.semantic 0.1201 ✓). Wall 491 s. Script `results/h5_repair/h5_repair.py`.

## The booked question
Is D2-V1b's **H5 instability (4/6 sockets) itself the KEEP-grade finding** — I/O determinacy is
*distribution-relative*, not a state property — or can the measure be repaired into something stable?

## 1. Instability decomposition — WHERE does it live? (decisive)

B = 1000 world-resample bootstraps (seed 2718) of the pooled operational E3 determinacy vs the
3-weight *definition* spread (operational/uniform/degenerate) at the full corpus.
Bootstrap surrogate nperm = 24 validated against the point-value nperm = 120: **|Δ| ≤ 0.0001 on every
socket** (no surrogate contamination).

| socket | resample std | resample 95% width | **definition spread** | def_var/res_var |
|---|---|---|---|---|
| reflex.orient | 0.00000 | 0.00000 | 0.0000 | — (std==0) |
| world.surprise | 0.01350 | 0.05228 | **0.4476** | **244×** |
| sensors.vision | 0.01398 | 0.05544 | **0.2816** | **71×** |
| policy.action | 0.00690 | 0.02746 | **0.9237** | **3663×** |
| memory.semantic | 0.00710 | 0.02766 | **0.5874** | **1274×** |
| memory.episodic | 0.01406 | 0.05332 | 0.0765 | 5× |

**HEADLINE: the H5 instability is 71–3663× larger in the BETWEEN-DEFINITION component than in the
within-socket-across-resamples component.** Resample width is ≤0.056 on every socket (the estimator is
*precise*); the spread is entirely the choice of input-distribution weighting. **The booked D2-V1b
instability was never a sampling-noise problem — it is distribution-relativity.** This also decides the
G-H5a reading: a resample-only G-H5a would have PASSED the *original* D2-V1 measure (its resample width
is ≤0.056 too) — contradicting the booked H5 INCONCLUSIVE. Therefore G-H5a must include the definitional
component (as prereg'd: `res_std>0 ∧ res_width ≤ 0.15 ∧ def_spread ≤ 0.15`).

## 2. Repairs (all three preregistered, all evaluated)

**R1 — per-world conditional** (E3 op-det per world, mean over 200 worlds):
surprise 0.6788 (def 0.775) · vision 0.7118 (0.633) · action 0.8494 (**0.277**) · semantic 0.2255 (0.294) ·
episodic 0.1736 (0.261) · reflex 1.0000 (0.000, std==0). **stable_count 0/6.**
R1 *moves* the definition spread (fixes action 0.924→0.277 and semantic 0.587→0.294) but *worsens* it on
surprise (0.448→0.775) and vision (0.282→0.633) → conditioning on world identity re-weights, it does not remove.

**R2 — op-split near-1 (E1) / mid-band (E3):** band frozen from the D2-V1 baseline →
near-1 {reflex.orient, policy.action}, mid {surprise, vision, semantic, episodic}. Mid-band is unchanged by
construction (def 0.448/0.282/0.587/0.077); near-1 with E1: action 0.8955 but **def 0.9811** (E1 does not
fix it), reflex 1.0000 (a numerical-ε std≈0 — an epsilon pass, counted as INCONCLUSIVE by law in spirit).
**G-H5c: R2 is a RELABEL** — Spearman(old, new) = **1.000**, zero sockets moved → **rejected** per prereg.
Honest stable_count ≤ 2 (episodic alone is genuinely stable; reflex is ε).

**R3 — paired-world delta** (E3 op-det of Δout | Δin per world, mean over worlds):
surprise 0.6967 (def 0.663) · vision 0.7594 (0.450) · action 0.8448 (**0.081**) · semantic 0.4795 (0.355) ·
episodic 0.3582 (0.151) · reflex 1.0000 (0.000, std==0). **stable_count 1/6** (policy.action only).
Differencing within a world nails policy.action but leaves the other four definition-fragile.

| repair | stable (prereg'd conjunction) | resample-only (for transparency) | G-H5c |
|---|---|---|---|
| R1 per-world | **0/6** | 5/6 | ρ=0.943, not a relabel |
| R2 op-split | **≤2/6** | 6/6 | **ρ=1.000 → RELABEL, rejected** |
| R3 paired-delta | **1/6** | 5/6 | ρ=0.943, not a relabel |

Gate G-H5a (≥5/6) is met by **none**. F-H5-2: no repair went all-constant.

## 3. G-H5b — does the repaired measure keep a signed relationship with the D2 transfer gap?

ρ(repaired per-socket determinacy, per-socket gap_sim), bootstrap-over-60-test-worlds CI:
- **R1 ρ = −0.2571 [−0.600, 0.600]**, range 0.826 (not flat)
- **R2 ρ = −0.3714 [−0.657, 0.486]**, range 0.880
- **R3 ρ = −0.2571 [−0.600, 0.487]**, range 0.642
- OLD (D2-V1) ρ = −0.3714 [−0.600, 0.486]

All repairs preserve the **negative sign** of H1 but every CI straddles 0 — i.e. the repairs do **not**
sharpen the H1 direction either; the H1 FAIL is robust to the repair choice. Not flat over range.

## 4. VERDICT TREE → `NO-REPAIR-PASSES`

No repair reaches stable_count ≥ 5 (best honest: R1 0, R3 1, R2 relabel). Per the frozen tree, this books
the KEEP-grade closure of the D2 measure thread:

> **Instability IS the finding: I/O determinacy is DISTRIBUTION-RELATIVE, not a state property of the
> socket.** The static-I/O construct of COG-THESIS §3/§4.2 does not exist as a socket-level scalar at D2
> scope (estimator intrinsic spread 0.039 per EST-FREEZE vs data spreads up to 0.924). D2-V1's H1 FAIL is
> therefore evidence against the **measure**, not against the **thesis** — a socket's determinacy is a
> function of (input distribution, output), and any single scalar must fix a weighting (operational /
> uniform / degenerate) whose choice moves it by up to 0.92.

Consequences booked: (a) the **1000-world ×5 extension stays FROZEN** — no stable scalar exists to buy
precision for (this lane's answer to the QUEUE precondition); (b) H1 should be re-derived at **world
granularity** (60 points) where the conditioning is explicit and the distribution is the world's own.

## 5. Repro / artifacts
`results/h5_repair/{h5_repair.py, h5_repair_result.json, h5_repair_run.out}`. Prereg
`proposals/runs/H5-measure-repair.md`. CPU-only 0 Wh, wall 491 s, no GPU, no guard receipt (none required).
Baseline reproduction gate PASS (matched D2-V1 to 4 dp). **NOT COMMITTED.**
