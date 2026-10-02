# H5-MEASURE-REPAIR — prereg (frozen BEFORE any run)

*Lane H5-REPAIR, 2026-10-01 ~17:0x AKDT. CPU-first. Follows D2-V1b booking (results/d2_v1/).
Lanes never commit.*

## 0. The booked problem

D2-V1b booked **H5 INCONCLUSIVE**: the per-socket I/O-determinacy measure was unstable on
**4/6 sockets** (offenders `world.surprise`, `sensors.vision`, `policy.action`,
`memory.semantic`). H5's instability statistic was

    spread(s) = max_w det_w(s) − min_w det_w(s),  w ∈ {operational, uniform, degenerate}

with the gate `spread_excess_over_synth_floor ≤ 0.15`. The two loudest rows:
`policy.action` op-det **0.901** with spread **0.924** (degenerate weight = 0.058);
`memory.semantic` op-det 0.120 with spread 0.587 (degenerate = 0.587).

EST-FREEZE (results/est_freeze/README.md) already showed the *estimator itself* has
intrinsic 3-weight spread ≤ 0.039 on a stationary-truth synthetic, i.e. the D2-V1 spreads
are **data-level**, not estimator noise. So the booked question:

> Is the H5 instability itself the KEEP-grade finding — I/O determinacy is
> **distribution-relative**, not a state property — or can the measure be repaired into
> something stable that preserves (or kills) the H1 direction?

## 1. Material (CPU-only, reuse persisted artifacts — NO new traces, NO GPU)

- `results/d2_v1/d2_v1_traces.json` — 200 worlds × 1000 evals × 19-int records, arms `real`
  and `sto` (frozen, sha256 pinned by the D2-V1 twin receipt).
- `results/d2_v1/d2_v1_twins_result.json` — per-socket `nerr_per_world` over the 60 held-out
  REAL test worlds × 3 seeds × 3 conditions (the transfer gaps for G-H5b / H1-v2).
- Frozen encoders `results/d2_v1/scripts/d2_v1_common.py`; estimator `results/est_freeze/estimators.py`.
- GPU: **NOT used.** Traces are sufficient ⇒ 0 Wh. (If, contrary to preflight, a repair needs
  regeneration, guard.py-wrapped mini re-run ≤2 Wh, preflight <1 GB free → retry once after 60 s → NOT-RUN.)

Baseline is *reproduced* first: pooled-sto E3 op/uniform/degenerate per socket must match
`d2_v1_result.json.determinacy` (else the lane books VOID and stops).

## 2. Step 1 — instability decomposition (diagnosis, no repair)

For each socket, B = 1000 world-resample bootstraps (seed **2718**, resample the 200 sto
worlds with replacement, pool their records, compute E3 operational):

- `res_std`, `res_ci95`, `res_width = p97.5 − p2.5` — **within-socket-across-resamples** variance.
- `def_var` / `def_spread` — variance / range across the 3 weight definitions at the full corpus
  (**between-definition** variance).

Headline datum: per-socket ratio `def_var / res_var` and the aggregate. If `res_width` is tiny
everywhere while `def_spread` is large on the 4 offenders, the booked instability was
**between-definition (distribution-relative), never a sampling-noise problem.**

## 3. Step 2 — three repair candidates (ALL preregistered, ALL evaluated)

**R1 — per-world conditional determinacy.** `det_w(s)` = E3 operational on world *w*'s own 1000
records; repaired value = mean over the 200 worlds. Conditioning on world identity kills
corpus-mixing (pooled bins are a mixture of per-world regimes). Definition spread = range over
the 3 weights of the world-averaged per-world value.

**R2 — op-split near-1 / mid-band.** Sockets with baseline op-det ≥ 0.80 are *near-1 ops*
(`reflex.orient` 1.000, `policy.action` 0.901); the rest are *mid-band*. A near-1 op must be
measured with a near-1 estimator, not a mid-band entropy: repaired statistic = **E1**
(excess mode-agreement vs permutation floor; EST-FREEZE stat-spread 0.008, the smallest) for
near-1 sockets, **E3** for mid-band sockets. The band assignment is frozen from the D2-V1
baseline (not re-fit). Report the band split explicitly.

**R3 — paired-world delta determinacy.** Align `real` and `sto` per (world, tick) (both have
1000 evals/world). Per socket build the run-to-run **difference channel**:
`Δout(t) = psi_sto(t) − psi_real(t)` (offset to 0..2O−2, declared alphabet 2O−1),
`Δin(t) = (phi_real(t), phi_sto(t))`. Repaired value = mean over worlds of the per-world E3
operational determinacy of Δout | Δin. Differencing within a world removes world-level
confounds. Definition spread = range over the 3 weights of the world-averaged value.

## 4. Step 3 — gates (frozen)

**G-H5a — repaired stability.** For each repair and each socket: recompute the repaired
per-socket statistic under B = 1000 world-resample bootstraps (seed 2718).
A socket is **STABLE** iff
`res_std > 0` **AND** `res_width ≤ 0.15` **AND** `def_spread ≤ 0.15`
(the original H5 band, retained; std == 0 ⇒ **INCONCLUSIVE, never PASS** — house law).
`stable_count = # STABLE sockets`. **Gate PASS iff stable_count ≥ 5** (one socket may be the
degenerate `reflex.orient`, which is exactly 1.0 ⇒ std == 0 ⇒ INCONCLUSIVE by law).

**G-H5b — repaired measure keeps a signed relationship with the D2 transfer gap.**
Spearman ρ(repaired_det, gap_sim) over the 6 sockets, with a bootstrap-over-the-60-test-worlds
95% CI (determinacy held fixed; gaps recomputed — same method as D2-V1 H1).
Either sign books; **flat-over-range kills** (if `range(repaired_det) < 0.5` the measure is
uninformative and cannot book a direction).

**G-H5c — the repair is not a relabeling.** Spearman between the old D2-V1 op-det socket
ranking and the repaired ranking; itemise which sockets moved. A repair that reorders nothing
(`ρ = 1` on 6 sockets) and has the same definition fragility is a relabel ⇒ rejected.

## 5. Step 4 — verdict tree (frozen)

1. If any repair has `stable_count ≥ 5` (G-H5a PASS) **and** passes G-H5c: book it as
   **H5-v2** and state what it says about H1 — the repaired-measure ρ and CI vs the original
   H1 `ρ = −0.371 [−0.600, 0.600]` (does the direction survive / sharpen / reverse?).
   Choice rule if several pass: highest `stable_count`, then larger `|ρ|`, then precedence R1 > R3 > R2.
2. If **all** repairs fail G-H5a: book the KEEP-grade closure
   **"instability IS the finding: I/O determinacy is distribution-relative, not a state
   property"** — the static-I/O construct of COG-THESIS §3/§4.2 does not exist as a
   socket-level scalar at this scope, and H1's FAIL is therefore not evidence against the
   *thesis*, only against the *measure*.
3. Either way the R1/R2/R3 numbers and the decomposition ship as datums.

## 6. Failure modes

- F-H5-1 baseline reproduction mismatch ⇒ VOID, stop.
- F-H5-2 a repaired statistic landing on exactly 0 or 1 for every world on ≥4 sockets ⇒ the
  repair is degenerate (all-constant), report as INCONCLUSIVE not PASS.
- F-H5-3 R3 channel declared alphabet ≠ 2O−1 ⇒ assert.
- F-H5-4 world-id misalignment between `real` and `sto` arms ⇒ assert same `i` set and 1000 evals/world.

## 7. Deliverables

`results/h5_repair/` (result JSON + run log + script), a RESULTS.md entry, a QUEUE.md line.
CPU-only, 0 Wh, ~20 min. DO NOT COMMIT.
