# INSTRUMENT-01 — characterize the WSL2 GPU burst-timing law

owner: any  (deliberately raceable: a second witness on an instrument law is worth wanting)
Context: Wave-73 bench falsification (2026-10-01 morning) found empirically that after ≥10 s idle,
short GPU bursts measure 2–10× slow on this box, and ~0.6 s of sustained synced load restores full
speed. Every future benchmark on this rig depends on that law — characterize it properly.
Runner (to write): `experiments/instrument_ramp_law.py` — elephant-gpu venv, ≤15 min GPU total,
measurement only, NO clock/driver/state changes. Receipt: `results/instrument_ramp_law.json`.

## Probes (frozen)
- **Shape**: idle {5, 10, 20, 40, 80} s → burst slowdown vs hot baseline (mean of 3 bursts per idle
  draw). Standard burst = fixed torch matmul sequence (~30 ms), identical across all probes.
- **Recovery**: after a fixed 30 s idle, ramp {0.1, 0.3, 0.6, 1.2} s of sustained synced load →
  post-ramp burst time.
- **Portability (R3, declared exploratory — no gate)**: repeat the shape probe with a second kernel
  type (elementwise cupy kernel vs matmul). Is the law kernel-agnostic (box-level) or kernel-specific?

## Gates (frozen, mechanical)
- **R1**: slowdown > 1.5× for idle ≥ 10 s in ≥ 2/3 idle draws.
- **R2**: the 0.6 s ramp restores ≥ 90% of hot baseline in 3/3 trials.
- **LAW_CALIBRATED** if R1 AND R2 → ramp table written into TOOLS.md + bench docstrings as the official
  instrument recipe (follow-up commit, declared).
- **LAW_FUZZY** otherwise → per-block ramps become mandatory + ramp receipts reported in every bench
  JSON (follow-up commit, declared).
Honesty note: this morning's law rests on ONE B/C-series. If the law fails to replicate here, that is
a booked finding, not an embarrassment — the bench fix stays valid either way (ramping never hurts).
