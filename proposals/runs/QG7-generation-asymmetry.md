# QG7 — Generation-asymmetry routing test (pre-registration)

Date: 2026-09-30, fired by night conductor 06:2x wake. Parent items: QG6 (trapping is a TIME problem), QO3 (g1 AUC 0.88), QO6 (retraction gate).

## Question
Does the gen-1 oracle signal (QO3: AUC 0.88 for "crosses by gen 12") also separate streams that cross ONLY at gens 13–24 (late bloomers) from streams that never cross by gen 24 (hopeless)? If yes, QO2 routing = oracle + budget triage + QO6 gate is fully specified AND asymmetric-budget-capable (route slow climbers more generations cheaply).

## Design
- Lane: QO3-identical shot arm (512 shots, bar 0.45, W=6, C=15, skeleton h0+cx01, seed 1234) but GENS=24 and S=2048 (cost ≈ QO3's 4096×12; fits timebox).
- Labels: `early` = crossed ≤ 12; `late` = crossed 13–24; `hopeless` = not crossed at 24.
- Subpopulation of interest: not-crossed-by-12 streams.

## Gates (fail-loud, declared BEFORE firing)
- G1 lane anchor: crossing rate at gen 12 must fall in the QG2 band 0.567–0.598 (S=2048, wider CP95 tolerated — booking states exact CP95).
- G2 QG3 cross-check: crossing rate at gen 24 reported against QG3 arm C (W6,g24) 0.755 exact-arm; shot-vs-exact difference acknowledged (QG2: shot≈exact), no hard gate, honest note either way.
- G3 core: AUC of a gen-1 MLP (QO3 arch/training protocol, 80/20 split) on `late` vs `hopeless` within not-crossed-by-12.
- G4 frozen-oracle transfer: `tools/qcell_oracle.pt` (QO1, trained for cross-by-12) applied to gen-1 features of the same subpopulation; oracle input convention preserved (gen feature = 1/12 as in training; declared deviation since this lane's gen count is 24). Report AUC + calibration caveat.

## Predictions (pre-registered)
- P1: late vs hopeless gen-1 AUC > 0.65 (signal survives inside the desert subpopulation, weaker than the full-population 0.88).
- P2: frozen QO1 oracle ranks `late` above `hopeless` (AUC > 0.55) but is miscalibrated for this question (trained on cross-by-12, where `late` streams are negatives).

## Interpretation
- P1 holds → QO2 routing fully specified with budget asymmetry: kill hopeless early, grant generations to predicted-late, gate kills behind e-process retraction.
- P1 fails (AUC ~0.5) → gen-1 fate signal is binary cross-by-12 only; late bloomers are indistinguishable from hopeless at gen 1 → routing must rely on QO6 evidence accumulation instead of forecast. Both outcomes informative; no re-roll.

## Booking
results/qg7_gen_asymmetry/ + RESULTS.md + spool append; commit+push every landing. GPU python: /home/eileen/venvs/elephant-gpu/bin/python.
