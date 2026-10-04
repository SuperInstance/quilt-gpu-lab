# PIDFIRE-1 — PID-driven suppression reaching SOC in the forest-fire CA (servo composition)

Pre-registered 2026-10-03 21:1x AKDT by conductor-spawned subagent. Provenance: composition
idea mined 2026-10-03 (3) (ternary-pid × ternary-fire × ternary-irradiate), journaled but
NOT previously committed — this pre-reg + run makes it real. CPU-only, no GPU fired.

## Composition lineage (pinned upstreams, source-fetched this session)

| Crate | Upstream commit | src/lib.rs sha256 | README sha256 |
|---|---|---|---|
| SuperInstance/ternary-pid | 6fbaf738f01296d1c4f69728cafac305864e2268 | 9a13e326332e3b1991e3c72af5184d7782caf4345c00121db44bbc798eac5bfa | ffd9f724c213b864e1af3c01192af79483ea4e1008d7d60b1272f892fb8e8530 |
| SuperInstance/ternary-fire | ab69abde05fb804b5581f1df8154210450877f40 | 1a0c4dc121e6f2c72f87d60fb498187d689d78c5ab7c60ea11db853d0851d2e4 | b62af3deed47ac14c7debdb4352a0699927397d0db57352bc454e964fb8137f9 |
| SuperInstance/ternary-irradiate | 1010fd20d901ea68d083f1391deead743bf57102 | b2ffe72ff08011e818d22adbcba332f24f00ddbb882282a5ad26eaf1d2ae2500 | e8515cdc1e420b0927a6e696477af460b50add7425e782148f2d55319cc18feb |

Local vendored copies: `scratch/pinch0/_raw/ternary-{pid,fire,irradiate}/` (README+Cargo
from the pinch0 crawl; `src_lib.rs` fetched + pinned this session).

## The claim (frozen, falsifiable)

Run the forest-fire CA (ternary-fire) as a servo problem — burn rate = process variable,
ternary-pid bang-bang trit output gates irradiate-style shadow/firebreak cells, anti-windup
PID integrator repurposed as the FUEL SCHEDULE (windup = fuel growth) — then **PID-driven
suppression reaches the canonical SOC power-law avalanche-size distribution from ≥90% of
random initial conditions, vs a <5%-area corner for fixed-rule (p,q) sweeps.**

## Semantics ported verbatim (from the pinned sources)

**ternary-fire step** (128×128, von Neumann 4-neighborhood, non-wrapping; states
+1 tree / 0 empty / −1 burning):
1. forced ignitions first: listed cells that are TREE in the *incoming* grid → BURN;
2. BURN(t) → EMPTY(t+1);
3. TREE(t) with k burning OLD-grid neighbors catches w.p. `1−(1−p)^k`
   (distribution-equal to the crate's sequential per-edge trials with break-on-success);
4. EMPTY(t) → TREE(t+1) w.p. q.
Newly ignited cells do NOT spread the same step (spread reads the old grid only).

**ternary-pid TernaryPid::update** (discrete, Δt=1), ported field-for-field:
e = SP − PV; if |e| < deadband: integral ×= 0.95, prev_error ← e, initialized ← true,
return 0. Else: P = kp·e; integral ← clamp(integral + e, ±Ilim); I = ki·integral;
D = kd·(α·(e−prev) + (1−α)·filt_d) (0 on first-ever sample); prev ← e; u = sign(P+I+D)
(+1 if >0, −1 if <0, else 0).

**ternary-irradiate composition mapping**: u=+1 = primary-knock point event (one forced
ignition — the fire CA itself is the cascade). u=−1 = shadow/firebreak: one EMPTY cell
(adjacent to a uniformly-random BURN cell if any exist, else uniformly random EMPTY)
becomes SHADOW for k_shadow steps — SHADOW cannot grow and cannot burn (obstacle blocks
propagation, README semantics), then anneals back to EMPTY (recovery, source semantics).
SHADOW exists only in the PID arm.

**Fuel schedule (the anti-windup repurpose)**: q_t = clip(g_scale·integral, 0, q_cap)
evaluated every step; windup (integral > 0, burn deficit) = fuel growth; integral ≤ 0 ⇒
q_t = 0 (growth suppressed). Fixed arm uses constant q.

## Frozen protocol

Common: N=128 (16384 cells), T=60,000 steps, transient 10,000 (avalanches spanning the
boundary excluded), measure 50,000. RNG numpy PCG64 seeded per run (declared deviation
from per-cell xorshift64: vectorized draws; transition RULES identical). Avalanche = total
burned cells over one quiet-gated fire interval (ignition admitted only when zero burning
cells). Memory O(grid): sizes streamed to JSONL per cell/IC, no corpus held.

**Phase 0 — fixed-rule sweep** (experiments/pidfire_sweep.py):
- Lightning: quiet-gated, per-step admission f_step = 1/150, target = uniform random TREE.
- Grid 21×21: p = linspace(0.05, 1.0, 21); q = logspace(1e-4, 1e-1, 21) (21 pts).
  Cell seeds 10,000 + cell_index.
- Per cell: n_sizes; discrete-MLE power-law fit τ̂ = 1 + n[Σ ln(s/(s_min−0.5))]^−1 with
  s_min scan (unique sizes ≤ s_max/4, ≤40 candidates) minimizing one-sample KS vs the
  fitted discrete CCDF on [s_min, s_max_obs]; mean burn fraction; mean tree density.
- **Cell-SOC gate**: n_sizes ≥ 100 AND self-KS ≤ 0.06 AND τ̂ ∈ [1.0, 1.4].

  ANNOTATED AMENDMENT (2026-10-03 21:4x, BEFORE phase 0 fired — no outcome data seen;
  evidence = synthetic pin in tests/test_pidfire.py): self-KS ≤ 0.06 is inoperable in
  expectation — one-sample KS at the (bounded-support-biased) MLE floors at ≈0.11 on
  pure finite-support PL synthetic (τ=1.2, S=16384), and the n≈300 noise floor alone is
  ≈0.08. Amended gate: **self-KS ≤ 0.10** AND n_sizes ≥ 100 AND τ̂ ∈ [1.0, 1.4].
  Symmetric loosening (applies to fixed-rule cells and any would-be corner alike) —
  it can only ENLARGE the fixed-rule corner area, i.e. it works against the claim's
  C2, not for it. Frozen from this line on.
- **Corner rule**: among gate-passing cells, argmin self-KS, tie-break larger n.
  REFERENCE = corner's size sample; τ_ref = corner τ̂; SP = corner's MEAN burn fraction
  over the measure window. **Mid-freeze**: results/pidfire_sweep/phase0_freeze.json
  committed+pushed BEFORE phase 1 fires.
- Corner-area fraction = gate-passing coarse cells / 441.
- Phase 0b refine (report-only, after freeze): 5×5 around corner at 0.1× coarse spacing
  (p clamped, q log-spaced), same protocol; sharpens the corner map; C2 stays on coarse.

**Phase 1a — PID calibration** (experiments/pidfire_pid.py, seeds 900,000..900,007,
ρ ∈ [0.05, 0.95] per seed): PV = burning_count/16384 per step. Frozen at freeze-time:
deadband = 0.25·SP, Ilim = 1.0, α = 0.2, kd = 1.0, k_shadow = 128. Grid (12):
kp ∈ {1, 2, 5} × ki ∈ {5e-4, 2e-3} × q_cand ∈ {0.5, 2.0}·q_corner with
g_scale = q_cand/Ilim, q_cap = 2·q_cand. Objective: RMSE(PV, SP) over steps 10k..60k;
disqualification: mean tree density < 0.01 in window (deadlock ⇒ RMSE = ∞). Pick argmin;
tie-break lower |mean PV − SP|. Calibration tunes SERVO ERROR ONLY — never the size
distribution (declared honest limitation). All-deadlock ⇒ calibration FAIL, C1 fails.

**Phase 1b — eval** (200 ICs, seeds 1,000,000..1,000,199, ρ random per seed, frozen combo):
- **Reaches-SOC per IC**: n_sizes ≥ 100 AND two-sample KS D vs REFERENCE ≤
  max(0.10, 1.358·√((n₁+n₂)/(n₁·n₂))) AND |τ̂_IC − τ_ref| ≤ 0.15.
- Borderline (|D − D_gate| ≤ 0.15·D_gate): rerun with seeds+10⁶, +2·10⁶; majority vote.

## Gates (frozen — no post-hoc edits; failures booked loudly)

- **C1 PID-REACH**: reaches-SOC fraction over the 200 eval ICs ≥ 0.90.
- **C2 FIXED-CORNER**: 0 < coarse corner-area fraction < 0.05.
- **C3 EXPONENT**: median eval τ̂ within ±0.10 of τ_ref. (Literature anchor 2D DS
  τ ≈ 1.19 reported as context, non-gating — variant semantics shift exponents.)
- **CLAIM VERDICT: PASS iff C1 ∧ C2 ∧ C3**, else FAIL with diagnosis. Substrate/protocol
  abort ⇒ ABORTED (never quietly patched mid-run).

## Annotation (2026-10-03 21:2x, BEFORE phase 1 fired — phase 0 is p-agnostic)

The frozen grid above under-specifies the PID arm's spread probability `p`. Clarified
(not a gate change): **the PID arm runs at p = p_corner** — the same substrate point whose
size distribution is the REFERENCE; only ignition timing (servo trit vs Poisson lightning)
and the growth schedule (q_t from the integrator vs constant q_corner) differ between the
arms. Recorded here because the freeze file carries p_corner explicitly.

## Predicted failure modes (predictions, not gates)

(i) u=−1 firebreaks cast mid-fire truncate the large-size tail ⇒ KS fails; (ii) integrator
-dominated sign regime chain-fires the forest to low density (servo holds, distribution
doesn't); (iii) deadband+bleed starvation deadlocks regrowth. Calibration mitigates
(ii)/(iii) via RMSE+deadlock-dq only.

## Non-goals

No GPU, no cascade PID, no feedforward arm, no exponent-theory work, no QUEUE claim.

## Receipts

results/pidfire_sweep/{coarse.jsonl, refine.jsonl, phase0_freeze.json};
results/pidfire_pid/{calib.json, eval.jsonl, eval_summary.json}; tests/test_pidfire.py
pins the ported semantics (textbook-formula parity with upstream's own test, deadband
regression, anti-windup, CA fixtures, avalanche accounting, fit recovery). Seal via
tools/receipt_manifest.py committed with the booking.
