# DETERM-1 — lattice-snap determinism: are QG7-type lanes single-draw bookable?

Spawned by SCOUT-60 (proof-game-sync lattice-snap primitive). QG7 booked the ensemble law
(≥4 reruns, spread 0.546–0.663) because lane torch-nondeterminism is MATERIAL for
subpopulation questions. Hypothesis: rounding the per-round champion state to a pinned
grid (eps-lattice) after each selection round collapses the divergence, making the lane
bit-reproducible without changing the physics verdict. PASS ⇒ propose amending the QG7
ensemble law to "lattice-snap lanes are single-draw bookable".

## Setup
- Lane = committed `experiments/qg7_gen_asymmetry.py` verbatim (S=2048, GENS=24, seed
  skeleton 1234, BAR 0.45), refactored into a function with flags only — no other edits.
- Arm A: lane verbatim, NO snap. 4 fresh-process reruns.
- Arm B: same lane + after each selection round round `v` and `champ_v` to the grid
  `eps * round(x/eps)` (float64, ties-to-even). ε sweep NARROWED for the slice timebox
  to {1e-2, 1e-4} (SCOUT-60 listed {1e-2..1e-5}; if both fail G2/G3, book PARTIAL and
  defer the remaining ε to a follow-up — no silent extension). 4 fresh-process reruns
  per ε.
- Per run, digest = sha256 over a canonical JSON containing: rate12, rate24, subpop/
  late/hopeless counts, full crossed_gen array (int64 bytes), final champ_v (float64
  bytes), auc_fresh, auc_oracle, wall time EXCLUDED from the digest.

## Gates (frozen before fire; no re-rolls)
- **G1 (arm A reproduces the spread)**: across the 4 arm-A reruns, the tuple
  (rate12, auc_fresh) takes ≥2 distinct values. If arm A comes out fully deterministic
  in this window, G1 FAIL — no baseline to diverge from; book as-is (the ensemble law's
  spread is cross-invocation, QG7b — a clean-window run may not reproduce it) and STOP.
- **G2 (snap kills divergence)**: for a given ε, all 4 arm-B reruns have IDENTICAL
  digests (bit-identical outputs, wall time excluded).
- **G3 (snap preserves the physics verdict)**: for an ε that passes G2, arm-B
  (rate12, auc_fresh) lies within arm-A ensemble mean ± max pairwise spread
  (mean of a possibly-degenerate set = the single value). If arm B is bit-identical
  AND inside the band, snap changed variance only, not verdicts.
- **G4 (cost)**: arm-B mean wall time ≤ 1.5× arm-A mean wall time.

## Verdict rules
- G1∧G2∧G3∧G4 PASS ⇒ book PASS; propose QG7-law amendment (docs item, cites DETERM-1).
- G3 FAIL at every swept ε ⇒ book CONTRADICT-class against naive determinism-by-
  quantization (snap changes the physics); keep ensembles; do NOT sweep more ε in-slice.
- G1 FAIL ⇒ book INDETERMINATE for this window; ensemble law stands.
- Fail-loud anchors throughout; GPU serial, one lane at a time; results to
  results/determ1_lattice_snap/; book in RESULTS.md with QUEUE mark.
