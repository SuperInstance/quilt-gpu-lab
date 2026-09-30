# ISING-1 — criticality on the lattice (the falsifiable projection effect)

**Pre-registered: 2026-09-29 ~18:50 AKDT, BEFORE the run (this file pushed first).**
**Lineage:** `docs/lattice-projections.md` effect #4 (lattice-hamiltonian seed).
**Question:** does the projection layer's *thermodynamic* reading of a fabric —
dials as spins, links as couplings — rest on a reproducible critical point, or
is "phase" a metaphor we cannot measure?

## Method (frozen before firing)

- 2D Ising, 128×128, periodic, J=1, Metropolis on GPU (torch, elephant-gpu venv),
  checkerboard sublattices so updates stay vectorized.
- Temperature sweep T ∈ [1.5, 3.5] step 0.1 (21 points), ascending.
- Per T: 300 equilibration sweeps, then 300 measurement sweeps.
  `|m| = |⟨s⟩|` per sweep; susceptibility χ = N·(⟨m²⟩ − ⟨|m|⟩²)/T.
- Tc estimate = argmax χ (parabolic refinement over the peak triplet).
- Fleet-fabric mini-case (not the science, the demo): the 9 live board cells,
  spins = sign(dial − channel median), J=1 on the 7 real links, 50 sweeps at
  T ∈ {0.5, 2.0}; receipt records final |m| — ordered vs disordered on OUR graph.

## Gates (frozen — no tuning after seeing data)

- Analytic Tc(∞) = 2/ln(1+√2) = **2.269 J**.
- `|Tc_est − 2.269| ≤ 0.15` → **REPLICATED** (finite-size 128² should land
  within ~±0.05 with a χ-peak estimator).
- `0.15 < |Tc_est − 2.269| ≤ 0.4` → **MARGINAL** (report; investigate finite-size
  and sweep-count effects before believing anything).
- else → **DEVIATES** (the harness is wrong until proven otherwise — K3b:
  diagnose the measurement, never re-roll blind).
- Guard: NaN/OOM → receipt says so, verdict `INVALID_HARNESS`. A missing verdict
  is a bug.

## What would make it interesting (if REPLICATED)

The fleet's lanes then have a defensible "temperature": the coupling strength at
which the board goes from noise to consensus is *measured*, not asserted — and
the projection layer can render proximity-to-criticality as a first-class visual.

## Receipt

`results/ising_criticality.json` — Tc_est, χ curve, |m| curve, gate verdict,
GPU/timing receipt, fabric demo. Booked to the ledger either way.
