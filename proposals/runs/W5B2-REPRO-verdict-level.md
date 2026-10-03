# W5B2-REPRO — verdict-level reproduction of W5b2 booking (spawned by FW-1 tranche 2, 2026-10-03)

## Motivation
FW-1 tranche 2 (commit d97f765) marked W5b2 (KEEP, mean_rel +8.35%, wins 4/5) **YELLOW**:
verdict-level coverage rests on a single nondeterministic GPU draw. This run closes that gap.

## Scope
Re-run the COMMITTED `experiments/w5b2_antirank_primacy.py` (pin c6e5b0f, sealed in
receipts/manifest.json at fire time) UNCHANGED: same arms {antirank, random}, seeds
[5291..5295], T_WARM=4000 / T_MAIN=6000, committed W5b machinery via
`w5b_lifetime_precision`. Output redirected to scratch (`--out` scratch/w5b2_repro/ if
supported; else back up committed artifact to ext4 first and restore byte-identically,
QO10 14:4x safe pattern). ~42-45 min GPU, serial lane (RTX 4050 6GB).

## Pre-registered gates (verdict-level, lane nondeterminism acknowledged)
- **REPRO-PASS** if: verdict reproduces (mean_rel >= 0.005 AND wins >= 4/5) AND every
  seed's rel_improvement sign matches the booking (5/5 signs) — margin huge, so a flip
  on any seed would be a real anomaly, not draw noise.
- **REPRO-SOFT** if: verdict reproduces but some seed sign flips while mean_rel >= 0.005
  and wins >= 4 — booking stands; record per-seed spread as the honest draw-width.
- **REPRO-FAIL** if: verdict does not reproduce (mean_rel < 0.005 or wins < 4) →
  open AMENDMENT on the W5b2 booking, mark FW-1 W5b2 entry RED, STOP.

## Discipline
Fired after this file + RESULTS.md QUEUE mark are committed and pushed. GPU instrument
law: ramp receipt per INSTRUMENT-01 (bench harness prints it; note it here on booking).
No keys echoed; archive-never-delete; fail-loud.
