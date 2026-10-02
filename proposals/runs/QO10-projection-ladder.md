# QO10 — projection-ladder ablation for the QO1/QO3 oracle (pre-registered 2026-10-02)

Spawned by SCOUT-11 (fleet-triage projection-doctrine results, 2026-10-01 18:59Z).
**Premise amendment (SCOUT-16):** fleet-triage 88e30b3 RETRACTED their L1>L0-under-shift ordering
(max-selection artifact over Kish n_eff 1.48). We therefore strike the directional premise
"later-gen features beat low-gen features under shift" and pre-register **BOTH directions**:
either L0>L1 (low projection survives/ beats under shift) or L1>L0 is a finding. Their rule
"no gap smaller than the spread is a finding" is adopted as the verdict rule below.

## Question
How much of the oracle's signal lives in each projection rung of the state
(gen, len, v, cv, gate histogram), and does the ranking of rungs change between a
random-stream split (same generation distribution) and a later-generation holdout split
(train early gens, test late gens — regime shift)?

## Design
- Lane: QO1-identical regeneration (seed 1234, verbatim `run_lane_states` from
  experiments/qo3_horizon.py), G1 anchor re-checked per below.
- Ladders at forecast gens g∈{1,3} (QO3 horizon: g=1 is the routing point):
  - L_full: gen, len, v, cv, hist (QO3's `build(g)`)
  - L_cvvgen: gen, len, v, cv (no histogram)
  - L_cv: cv only
  - L_gen: gen only (QO1 "features cv>v>gen >> gates" naive floor check)
- Splits: S_stream = QO3's 80/20 random-stream split; S_genregime = train on gens ≤ g0
  pooled (g0=3), test on gens > 3 (same streams, regime shift in generation).
- MLP: QO3's fit_mlp verbatim; **ensemble of 4 torch seeds** per (ladder, split, g) —
  QG7 lesson: subpopulation/split verdicts are ensembles, never single draws.
  cv-only rung also gets the closed-form logit for reference.

## Pre-registered gates (fail-loud, no re-roll)
- **G1 (lane anchor):** reproduced MLP AUC at gen 1 and gen 3 must be within ±0.02 of the
  committed QO3 booking (0.8922 / 0.9355). Outside → FAIL-DIVERGED, book and STOP.
- **G2 (degenerate):** any ladder/split arm whose ensemble AUC std == 0 across seeds AND
  matches a trivial constant predictor → DEGENERATE, not PASS (murmuration std==0 rule).
- **Verdict rule (adopted from 88e30b3):** a rung ordering is only claimable if the gap
  between adjacent rungs exceeds the ensemble spread (max std across the two rungs' seeds)
  AND holds in BOTH forecast gens. Otherwise: INDISTINGUISHABLE.
- **Both directions live:** for S_genregime we pre-register that EITHER direction of
  (L_full vs L_cvvgen vs L_cv) reordering vs S_stream is a booking. No directional premise.

## What each outcome means
- Rung ordering stable across splits → oracle signal is representational, QO2 unchanged.
- Ordering flips under regime shift (either way) → oracle signal is partly REGIME; QO2
  router must train on matched-generation data; cite in QO7 integration spec.
- gen-only competitive anywhere → alarm (context alone would be the signal); if gen-only
  is at chance (expected), records the floor.

## Cost
One 12-gen × 4096-stream lane regeneration (~2 min GPU) + 2×4×4 MLP fits (~10 min). Serial, solo.
