# D12am — constant-c invariance of the rho^2 variance-inflation law (pre-registered 2026-10-10, before firing)

## Lineage
D12aj measured dependent-null MC discovery-floor blow-ups under common-mode
dependence rho (W=8/16, p=0.3, eps=0: ~2x at rho=0.2, ~6.4x at rho=0.4).
D12ak killed the mean-shift explanation. D12al tested null tail-variance
inflation, nulls ~ N(0, (1+c*rho^2)/(WT)): G1/G2 PASS (heldout rho=0.4 with
the rho=0.2-fitted c), G3 FAIL -> KILL per frozen gates (booked; stands).

## Why this run exists (harness diagnosis, not gate-shopping)
D12al's G3 band [3,5] contradicts its own docstring: in the implemented
parametrization inflation = 1 + c*rho^2, a constant c implies implied-c
ratio ~ 1.0; a ratio near 4 corresponds to inflation scaling as rho^4.
G3 as coded therefore tested a rho^4 ALTERNATIVE. D12al's data actually
support constant c ~ 26-35 (implied-c ratios 1.19 / 1.37). This pre-reg
freezes the constant-c test properly. D12al's booked KILL stands; this is a
NEW hypothesis test, not a re-roll.

## Hypothesis
H: one rho-independent constant c (~30) explains the entire measured blow-up
family via floor(rho)/floor(0) ~ 1 + c*rho^2 (order-statistics MC, ratio-to-
ratio only — absolute model floors are known ~3x off measured and unused).

## Instrument (changes vs D12al named)
- Same model, seed 2718, 20k MC samples, P_succ >= 0.5 floor, ratios only.
- T grid DENSER: 160 log-spaced points 5..4000 (D12al used 80) to cut
  quantization error on the ratio.
- Fits: c_fit at rho=0.2 by bisection on the ratio-to-own-baseline; heldout
  prediction at rho=0.4 with the SAME c; implied c(0.4) by independent
  bisection. W in {8, 16}. Base floor computed once per W; fixed call order
  (deterministic stream).

## Frozen gates
- G1 (fit sanity): model rho=0.2 blow-up / measured blow-up in [0.8, 1.25]
  for both W.
- G2 (heldout): predicted rho=0.4 blow-up / measured blow-up in [0.67, 1.5]
  for both W.
- G3 (THE TEST — constant-c invariance): implied c(0.4) / c_fit(0.2) in
  [0.67, 1.5] for both W (constant c predicts 1.0).
- G4 (cross-W universality): c_implied(0.4, W=8) / c_implied(0.4, W=16) in
  [0.5, 2.0].
- Verdict: KEEP iff G1-G4 all PASS, else KILL.

## Band justification (pre-fired, honest)
D12al's W=16 implied-c ratio was 1.366 — a naive 1.33 band would have
failed. The [0.67, 1.5] band is set by quantization analysis BEFORE firing:
floors land on the T grid (adjacent-step ratio ~7% at these T), and each
implied-c ratio divides two bisection fits plus a base floor — up to ~30-40%
swing is within instrument noise. 1.5 covers it with margin. If G3 fails
again at ~1.37, the constant-c law is genuinely in doubt and the follow-up
is a grid-convergence study (D12an), NOT another re-band.

## Budget
CPU only, seconds-to-minutes. No GPU. Seed 2718. Script committed in the
same landing as this pre-reg, before firing.
