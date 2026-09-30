# ISING-2 — criticality, with a statistic that can actually carry the claim

**Pre-registered: 2026-09-29 ~19:05 AKDT, BEFORE the run (pushed first).**
**Parent:** ISING-1 (proposals/runs/ISING-1-plan.md) — verdict MARGINAL, but the
real finding was a **harness diagnosis**: a single 300-sweep sample per
temperature gave a χ curve that is not a curve (χ = 0.00 at T=1.6, 29.5 at 1.8,
48.5 at 2.0, 33.7 at 2.3). Tc_est 2.0014 lands in the right *neighbourhood* of
2.2692 but with no error bars there is nothing to believe. Per K3b: the gate
stays frozen; the estimator gets fixed and the round is re-registered.

## What changes (declared before data)

1. **RUNS = 8 independent runs per temperature** (each: fresh random init,
   300 eq + 300 meas sweeps). Report mean ± std of |m| and χ.
2. **Binder cumulant** U = 1 − ⟨m⁴⟩/(3⟨m²⟩²) per run, averaged — a
   variance-based order parameter that is far less noisy than raw χ.
3. **Unimodality sanity gate (new, pre-registered):** the *mean* χ curve must be
   unimodal with the peak at least 2× the value at both sweep ends. If it is not,
   the verdict is **ESTIMATOR_UNSTABLE** — fail loud, do not report a Tc.
4. Tc = argmax of the mean χ with parabolic refinement; the receipt carries the
   χ std band so the peak's width is visible.
5. Fabric demo corrected: proper Metropolis acceptance per node
   (ΔE = 2·J·s_a·Σ_neighbours) instead of the v1 approximation, 200 sweeps,
   and the demo is labelled illustrative — it is not evidence about Tc.

## Gates (frozen)

- `ESTIMATOR_UNSTABLE` if the unimodality gate fails (checked first).
- `|Tc_est − 2.269185| ≤ 0.15` → **REPLICATED**.
- `≤ 0.4` → **MARGINAL**. else → **DEVIATES** (harness wrong until proven).
- NaN/OOM → **INVALID_HARNESS**.

## Note on honesty

ISING-1 stands on the record as MARGINAL. This round does not retroactively
repair it: a better estimator getting closer to 2.269 is *not* the same
measurement, and the receipt says so.
