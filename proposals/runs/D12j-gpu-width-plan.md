# D12j — GPU-scale width: does the W·T product rule survive W=64/128?

Pre-registered 2026-10-01 ~05:55 AKDT, BEFORE fire. Frozen gates; the verdict
is booked either way (results/d12j_gpu_width.json + journal + commit).

## Motivation

D12i (KEEP) found the partner-discovery floor is governed by the
bandwidth-time product W·T (~400 at p=0.3), not T alone — but only tested
W ≤ 16 on CPU. Open the GPU lane: same stream/correlation/discovery model
vectorized in torch on the 4050, at widths the CPU sweep could not reach.

## Model (D12i semantics, vectorized)

- Pairing: seeded shuffle, consecutive pairing (as D12i).
- Streams: per pair, per channel, per timestep — correlated with prob p_corr
  (both cells get the same ±1 base sign), else each cell gets an independent
  ±1 draw. Exactly D12i's `streams_for` logic.
- corr(a,b) = |Σ products| / (W·T) over all channels and steps; discovery =
  per-cell argmax over others with FIRST-index tie-break (D12i's
  `max(others, key=corr)` semantics, replicated deterministically).
- partner_id_acc = fraction discovered; bar 0.90; floor = min T on the ladder
  with mean acc ≥ bar.
- Streams are RE-DRAWN (torch CUDA generator, seeds SEED*100000 + w*10000 +
  n*1000 + int(p*100)*10 + t*2 + draw, SEED=2718 — the D12i formula family).
  Not bit-matched to D12i; claims are about the floor RULES, not per-draw
  identity.

## Grid

W ∈ {32, 64, 128} × N ∈ {32, 64, 128} × p ∈ {0.3, 0.5, 0.7} ×
T ∈ {1, 2, 3, 5, 10, 25, 50, 100} × 3 draws = 648 runs (GPU, ~minutes).

## Frozen predictions

- **J1 (monotone extension):** T_floor is non-increasing in W at every (N, p)
  through W=128 (None floors count as +∞; number→None is improvement, the
  reverse is an inversion). D12i's claim extended to scale.
- **J2 (product rule boundary):** at the hardest corner (N=128, p=0.3),
  **T_floor(128) ≤ 3** — the linear product rule's honest ladder prediction
  given D12i measured floor(16) ∈ [10, 25].
- **J3 (the pre-registered alternative — kill clause):** **T_floor(128) ==
  T_floor(32) at (N=128, p=0.3)** ⇒ the floor has PLATEAUED at the
  message-exchange floor: it is steps-bound, not bandwidth-bound, and the
  product rule is KILLED at high width.

## Verdict mapping (mechanical)

- J1 PASS + J2 PASS → **KEEP** (product rule survives to W=128).
- J1 PASS + J2 FAIL + J3 not triggered → **PARTIAL** (floor keeps shrinking
  but sub-linearly — record the full curve; the rule bends, not breaks).
- J3 triggered → **KILL-product-rule / PLATEAU** (the finding is the floor
  value and the plateau width).
- J1 FAIL → **KILL-monotonicity** (D12i's rule broken at scale — diagnose).

## Guard + receipt

Preflight: VRAM ≥ 1024 MiB free, GPU temp ≤ 80 °C; fail-loud JSON receipt
written even on exception (traceback booked, verdict KILL-harness). Cost:
single-digit minutes, < 50 MB device memory.
