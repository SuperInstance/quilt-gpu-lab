# QG7b — rerun-ensemble correlation census (spawned by SCOUT-34 / NEURO-QUILT n_eff≈2 threat)

## Question
What is the effective n of QG7's 4-rerun AUC ensemble? QG7 booked subpopulation verdicts as
">=4 rerun ensembles" (G3 AUC 0.546/0.663/0.636/0.580, mean 0.606, 1/4 clears 0.65). Those reruns
share the skeleton draw and differ only in unseeded tie-break RNG / lane nondeterminism — correlated
votes. NEURO-QUILT (fleet-triage 47d3239) measures n_eff≈2 for correlated judges ACROSS vendors;
transfer to identical-computation reruns is unproven. Threatened booking: QG7 P1 FAIL confidence and
the QO2 routing law's "gen-1 signal cannot reliably separate late-bloomers" clause.

## Instrument
experiments/qg7b_rerun_correlation.py — refire the QG7 lane (gens=24, S=2048, identical pinned
qcell_sim 8c82d4bcc88370c0 / qcell_oracle.pt fed2c15fb506899f) R=5 times; per run record:
per-stream frozen-QO1-oracle scores on the not-crossed-by-12 subpopulation, late/hopeless labels,
G3 fresh-MLP AUC, G4 oracle AUC. (QG7 saved only aggregates — no per-stream scores — so the refire
arm is mandatory per the SCOUT-34 spec. Lane is ~4.5 s/rep; 5 reps well inside timebox.)

## Pre-registered gates (frozen before fire)
Primary: mean pairwise Spearman rho of per-stream oracle scores across the 5 reruns (on the
subpopulation, aligned by stream index — same skeleton draw, so alignment is positional).
- rho > 0.9 → the ensemble is ~1-2 effective draws. Re-state QG7 P1 verdict confidence: FAIL
  stands (the point estimate is still ~0.6), but the 1/4-clears-0.65 spread is intra-computation
  noise, NOT judge diversity; the ensemble adds no independent evidence.
- rho < 0.5 → correlated-judge transfer REFUTED for identical-computation reruns; QG7 booking
  gains a robustness note (ensemble draws are effectively independent given shared skeleton).
- 0.5 <= rho <= 0.9 → INTERMEDIATE: report rho, change no verdict language either way.
Secondary (report-only): per-stream late/hopeless label agreement across reruns (fraction of
streams with identical label in all 5); per-run G3/G4 AUC vs the booked ensemble ranges.

## Fail-loud anchors
G1: per-run rate@12 within the QG2 band [0.567, 0.598] on every rerun (lane-divergence guard,
same as QG7). G2: subpopulation size within 820-880 of booked 846. If the committed script ever
disagrees with its own recorded results.json, STOP and book the discrepancy.

## Cost
GPU ~1 min compute; slice time ~20 min including booking + seal.
