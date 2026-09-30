# W5a — re-observation vs trace-reading (pre-registration)

**Fired from:** SPOOL wave 6 seed W5a (M10, score 64: "failure diagnosis needs re-observation, not
trace-reading" — Video-RSI's claim arriving independently; QO6's "cannot retract = p-value in disguise"
is the same doctrine. This seed can KILL OUR OWN DOCTRINE's generalization).
**Status:** FROZEN before fire. Post-fire changes = documented amendment only.

## Question
A trace is a sample from the harness, not the world. QO6 predicts that diagnosis from a RETRACTABLE
re-observation of the world strictly dominates diagnosis from the recorded trace. Does that advantage
survive when the trace is only mildly lossy? Or is there a regime where trace-reading matches
re-observation — refuting the generalization?

## Frozen design
- **World:** x_t = μ_t + σ·z_t, σ=1, T=200, drift onset t0=50, μ ∈ {0 (no drift), 0.2σ, 0.5σ, 1.0σ},
  sign ∈ {+1,−1} (sign only meaningful for μ>0). z from numpy default_rng, frozen seed per (cell, rep).
- **Recording (the trace):** quantize to q ∈ {0 (raw), 0.5σ, 1.0σ} and subsample every k ∈ {1, 4} —
  the harness's log is what the trace-reader gets, nothing else.
- **Arms (SAME detector on different data — isolates the information, not the statistic):**
  1. `trace` — the recorded trace (T/k samples, quantized): what trace-reading has.
  2. `rawsame` — raw (unquantized) values at the SAME recorded positions: isolates quantization loss.
  3. `fresh` — FRESH raw draws from the same world at the same count (new noise): pure re-observation,
     budget-matched.
  4. `freshfull` — fresh raw draws, all T positions: re-observation at full power (upper bound).
- **Detector (matched, frozen):** drift statistic = mean(after t0 positions) − mean(before t0 positions)
  with sign; decision |stat| ≥ 0.2σ; t0 estimate = max-|stat| split point (grid over candidate splits);
  sign = sign(stat). Identical code path for all four arms.
- **Grid:** 4 μ × 2 sign × 2 q(nonzero) × 2 k = 28 drift cells + 4 μ=0 cells (detection-only), 200 reps
  each, 3 global seed blocks. Metrics: detection error, sign error, |t0 error|>10 rate.

## Gates (frozen)
- **CONFIRM (QO6 generalizes):** error(`fresh`) < error(`trace`) − 2pp (absolute) on ≥8/12 primary drift
  cells (μ=0.2/0.5/1.0 × q=0.5/1.0 × k=1/4, paired reps) AND no cell where `trace` beats `fresh` by >2pp.
- **REFUTED (doctrine does not generalize to this regime):** |error(`fresh`) − error(`trace`)| ≤ 2pp
  overall AND no consistent direction across cells — trace-reading matches re-observation here.
- **MIXED otherwise:** book the regime map (which q/k open the gap); the map IS the result.

## Honest risks
- The detector is deliberately simple; a smarter trace-reader could shrink the gap. This tests the
  information available, not detector ingenuity — matched detectors are the point.
- The recording model (quantize+subsample) is one loss model. Other harness losses (dropped spans,
  clipping) are future cells; this run covers the two canonical ones.
- If QO6 is REFUTED here it does not die — it loses the claim to GENERALIZE; the regime map says where
  retraction still pays.

## Compute
CPU-only, ~200 reps × 28 cells × 4 arms × O(T) — minutes. Artifacts:
`experiments/w5a_reobserve_vs_trace.py`, `results/w5a_reobserve_vs_trace/{results.json,run.log}`.
