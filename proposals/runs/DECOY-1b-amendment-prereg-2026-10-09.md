# DECOY-1b — amendment pre-registration (two rows from SCOUT-90)

Amends proposals/runs/DECOY-1-decoy-metric-census-prereg-2026-10-09.md (GREEN, 1 YELLOW-latent,
booked 01:5x Oct 9). Spawned by SCOUT-90 finding (2): fleet-murmur-worker's keyword gate ranks
soup 5.2x ABOVE a correct observation (27/27 green, zero discrimination pin, empty string ==
nonsense score). Committed+pushed BEFORE firing; verdict reliance only after push.

## New frozen gates (in words)
- G5 EMPTY-INPUT-DEGENERATE: for every metric site cited by a booked verdict (DECOY-1 G1
  survey table), call the metric with empty/degenerate input (empty list, empty string, None
  where the signature allows). Flag any site where empty input does NOT raise loudly, or where
  the owning gate would treat the degenerate value as a pass. Positional/exempt clamps keep
  their DECOY-1 classification.
- G6 INVERSION-DISCRIMINATION PIN: the mutation-lite witness (G4) is extended — a DELIBERATELY
  INVERTED assignment (worst-case: labels flipped) must score strictly WORSE than true labels
  and no better than shuffled (auc_inverted < auc_true and auc_inverted <= auc_shuffled + 0.05).
  A metric that cannot distinguish inverted from true at instrument level = RED on the witness
  (bookings remain GREEN unless a cited live gate is affected — same verdict rule as DECOY-1).

## Scope
Same survey table as DECOY-1 (13 sites + 6 docs-only). No new sites; VNaN-1 (verdict_gate
__post_init__ NaN/inf validation, booked 18:4x Oct 9) covers the numeric-path class; G5 here
covers the EMPTY-structural class beneath it.

## Verdict rule
Inherited from DECOY-1: RED only when a live cited gate's metric is empty-input-passable or
inversion-blind. Otherwise YELLOW notes.

## Cost
CPU only, ~10 min extension of tools/decoy_census.py. No GPU lane.

## Prior
Expected GREEN: every surveyed site takes lists over which any()/len() raises or returns a
degenerate value that no booking cites as a gate; rank-statistic AUC must be inversion-blind-
PROOF (flipping labels drives AUC to 1-AUC, strictly below true for a_true > 0.5).
