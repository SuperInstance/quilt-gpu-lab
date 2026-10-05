# IONQ-2 — rung-2 discriminator battery on tools/qcell_sim.py crx (pre-registration)

Spawned by IONQ-1 (2026-10-05 02:1x). Sources: MicroMoth-quilt IONQ-RECON §4 + PRs #43/#44 (read-only;
no comments filed). Committed BEFORE fire per protocol. Tool: `experiments/ionq2_rung2_battery.py`
(same commit). CPU-class exact-statevector lane (n=2, device cpu, complex128); no GPU contention.

## Frozen gates (pre-registered, no re-roll)
- **G0 anchor**: `python tools/qcell_sim.py --selftest` passes (k4 champion balance 0.4268 must hold).
- **G1 control-leak**: crx with control in |0⟩ is a no-op — P(target=1) = 0 exactly (tol 1e-12)
  for all θ in the sweep.
- **G2 calibration sweep**: θ ∈ {π/6, π/3, π/2, 2π/3, π} (pi-units {1/6,1/3,1/2,2/3,1}), control=1:
  P(target=1) = sin²(θ/2) within 1e-9 at EVERY point (their shot-level pin: bridge w=sin²(θ/2),
  exact 1.0 at π). Any unit mismatch (radians-vs-pi-units, QG1-residual class) fails this loudly.
- **G3 additivity**: crx(1/3);crx(1/3) with control=1 → P(target=1) = 0.75 ± 1e-9 (their measured
  0.7494 at ~150σ vs accumulator clamp 0.50; ours is exact statevector so must be 0.75 exactly).
- **G4 cancellation**: crx(1/3);crx(−1/3) with control=1 → P(target=1) = 0 EXACTLY (bit-level
  amplitude annihilation). ANY nonzero = RED = new QG1c-class crx convention finding (QG1c cleared
  swap only; crx semantics were never independently stressed).

## Verdict rule
PASS iff G0–G4 all hold. Any gate fail → book RED honestly in RESULTS.md, name which discriminator
and which convention class, STOP (no re-roll, no parameter fiddling).

## Anchors / conventions declared before fire
- qcell_sim: balance = min(p000,p111); angles in pi-units; crx = controlled-RX(θ) on target iff
  control is 1; basis-string bit order resolved empirically in-script via an x-on-q0 probe and
  asserted (fail loud) before any gate runs.
- Machine: CPU (torch complex128). Runtime estimate: seconds.

## Cost
~2 min fire, ~10 min book+spool. No network, no weights.
