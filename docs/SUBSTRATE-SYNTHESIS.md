# Substrate Synthesis — micromoth-quilt-cudaclaw-exoj

2026-10-06 · Compiled from the D-series experiment journal and results/ JSONs
(seed 2718 throughout; all runs CPU-only or sub-15s GPU; 6GB/80C guard never touched).

## The substrate

Cellular graph where a quilt cell's memory is an n-qubit statevector (hidden phase
angles on a hidden register) and edges are ternary-quantized atom streams. Question
the D-series answered: **is there real relational structure here, and what carries it?**

## Findings, in order

### 1. Structure delta is real (D12/D12e)
With handed addressing: isolated cells A = 0.558, relational B = 1.0, permuted
control C = 0.508 → delta = 0.44 vs pre-registered margin 0.10. The delta survives
grown addressing: partner edges **discovered** by max-|corr| of atom streams (no
handing, no reward) give B' = 1.0, control C' = 0.467, delta = 0.533.

### 2. Addressing mechanism is correlation, not learning (D13 series)
Reward-based learned addressing fails at every rung: Hebbian 0.467, confidence-
weighted 0.533, REINFORCE 0.65 — all below the 0.80 bar. Correlation-based shared-key
discovery: **1.0** (target 0.90). Cells should *find* partners statistically, not be
trained to point.

### 3. The don-contract is a safe primitive, not a recovery mechanism (D11/D11b)
Gate commits/reverts (propose → holdout-validate → strict-improvement commit):
revert fidelity **1.0** across all 79 rejected dons. But no validation route (fact
holdout or stream-gain) rescues discovery at T=5 — root cause is a sample floor,
not a mechanism failure.

### 4. Hidden angles: private channel, weak relational mirror (D23 series)
Marginal readouts are exactly 0.5 in the computational basis (angles invisible to
the ternary passband), but hidden angles are readable in rotated bases: R² > 0.99
at T ≥ 25, J = 8 views (private angles — KEEP). Relationally, angle registers top
out at 0.67 partner-ID (best corner, σ=0.05, T=200) vs the 0.90 bar — a redundant,
degraded mirror of stream coupling. **Relational knowledge lives in the ternary
atom streams, not the phases.**

### 5. Entanglement adds nothing to discovery (D12k/k2, certified)
At matched |corr|, n=2 Bell-state channels vs classical channels: paired diffs'
CIs straddle 0 everywhere (certified at 20 draws). The correlation estimator is
**correlation-complete** — what matters is stream correlation structure, not the
quantum provenance. The W·T law needs no quantum upgrade.

### 6. The engineering law (D12f–j)
Discovery floor governed by **bandwidth-time product W·T**, not T alone. Floors
drop ~3× per width doubling, verified to W=128 on the RTX 4050 (T_floor = 2 at
W=128, N=128). A single practical rule: T ≥ 50 is universal for exact partner
discovery at W=4, p=0.3.

### 7. Noise damage + the discovery exponent (D12l–t)
- Raw |corr| decays as s^1.92 with s = p·(1−2ε) — the naive law was right; D12l's
  bound miss was a constant-calibration artifact (D12m corrected, D12n validated
  out-of-sample, 12/12 coverage with C=600, no refit).
- But **discovery** floors scale as s^~3.9 — roughly double the corr exponent
  (D12s measured 4.0, D12t certified 3.91 at 3.3× draws). Engineering rule:
  T_floor ≈ 1.4 / (W · s^3.9).

### 8. Mechanism + calibration (D12u–u5)
An order-statistics model (partner estimate vs max of N−1 noisy nulls) reproduces
the doubled exponent: M1 (s^1.92 signal) gives 4.18; linear-s control gives 1.43
(D12u). One variance-scale k = 0.657 calibrates it to within 16% of the entire
harness surface (D12u1), holding out-of-family at N=64 (D12u2, ratios 1.00–1.51)
and near-degenerate p=0.4 (D12u4, resolvable mid-grid floors).

### 9. The residual is k_eff(p) (D12u5–w)
Single-k refit fails out-of-sample (heldout ratios ~1.8×). k_eff is **p-local**,
not a function of s_eff (D12w: collapse test KILLED both gates, wrong-sign slope);
linear interpolation in p covers the p=0.45 midpoint (D12v, 8/8 coverage). Reading:
the null population's confusability structure changes with coupling strength per se.
Validated surface: p ∈ {0.3, 0.4, 0.45, 0.7}, N ∈ {32, 64}, W ∈ {4, 8, 16},
ε ∈ {0..0.2}, one calibration, never refit.

## One-paragraph verdict

The substrate's relational advantage (Δ ≈ 0.44–0.53) is real, carried entirely by
ternary atom-stream correlation keys (not reward learning, not hidden phases, not
entanglement), discoverable once W·T clears a floor given by
T_floor ≈ 1.4 / (W·(p(1−2ε))^3.9) with a p-local variance correction — and the
mechanism of the doubled noise exponent is order statistics over N−1 noisy
correlation estimates. This is a complete, calibrated, falsified-in-the-right-places
engineering description of the cell graph.

## Caveats carried forward

- Statevector cells at W>16 are simulated product subchannels, not a true
  entangled register (moot for discovery per D12k2, but semantics untested).
- Floors grid-quantized; 3–10 draws/point.
- k_eff(p) is a 3-point line; p=0.7 unresolvable (grid-pinned).
- The don-contract needs stream-scale validation data to act in degraded regimes.

## Suggested next life

If the journal reopens: an analytic derivation of k_eff(p) from null-population
structure would be the one remaining theory gap; otherwise this doc retires the map.
