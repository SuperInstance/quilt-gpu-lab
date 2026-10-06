# CC-1 prereg — "comfortable collapse" census on the QO6t desert-fence population

Spawned by SCOUT-53 (2026-10-06, lucineer-workspace 13efdd2): fleet paper-anti-collapse-guard
found "comfortable collapse" — math indicators restored while the judgment layer still reads
averaged. Transfer question for our substrate: in the QG3/QO6t desert-fence population, are
doomed streams (never cross by gen 24) INDISTINGUISHABLE from late-fenced streams (cross only
at gens 13-24) on ALL cheap champion-feature views at a matched pre-fate generation — while
their fates differ maximally? If yes, our substrate has a comfortable-collapse instance and
QG3b (statevector-distance basins) is mandatory, not optional. If any cheap view separates,
name it (it is a free oracle feature QO1 does not yet use).

Honest relation to booked results: QG7 booked P1 FAIL (gen-1 AUC 0.546-0.663 for late vs
hopeless) — that was the ORACLE view at gen 1. CC-1 is a CENSUS at matched mid-lane gens
(gen 12 primary) across the raw feature family {v, rank, len, rate}, not a new model claim.
CORROBORATE of QG7 is the expected outcome; CONTRADICT would be a cheap feature with
separation AUC >= 0.75 at gen 12 (which would threaten the "gen-1 signal cannot separate"
framing, not any booked number — QG7 booked gen-1, CC-1 tests gen-12).

## Instrument (pinned, reused)
- Lane: experiments/qo6t_transient_stress.py `run_lane_trajectory` VERBATIM (itself QG6
  run_lane + champ_v trajectory recording). Plus per-gen capture of champion len and
  per-gen population rank of v (same rank_series construction as QO6t prereg).
- Config: W=6, gens=24, S=512, bar=0.45, seeds {11,12,13,14} (4-seed ensemble, QG7 lesson).

## Groups (defined BEFORE firing)
At the primary census gen g*=12 (pre-fence for late bloomers by construction):
- HOPELESS: not crossed by gen 24 (champ_v < bar at gen 23).
- FENCED: crossed at gen >= 13.
- EARLY (control): crossed at gen <= 12. Excluded from the primary contrast, kept as anchor.

## Pre-registered gates (words frozen here)
- G1 CONSTRUCTION: per seed, crossed-by-24 rate in 0.755 ± 0.05 and crossed-by-gen-12 rate
  in 0.578 ± 0.05 (QO6t/QG3 anchors, small-S CP95 slack). Fail => lane broken, STOP.
- G2 MECHANICS: FENCED count per pooled seed >= 40 (else the contrast is starved; book
  INDETERMINATE, do not re-roll with new seeds).
- G3 PRIMARY CENSUS: per feature f in {v, rank, len, rate(v over last 8 gens)}, pooled-over-seeds
  AUC(FENCED vs HOPELESS) at g*=12, reported per seed AND pooled. Verdicts:
  - ALL features AUC in [0.45, 0.60] => COMFORTABLE-COLLAPSE CONFIRMED (feature-blind at fence
    time); QG3b priority RAISED.
  - Any feature pooled AUC >= 0.75 => NEW-FEATURE named; QO1 feature-augmentation spawned.
  - Mixed / intermediate => INCONCLUSIVE, book the table, no model fit.
- G4 SANITY: EARLY control must separate strongly at g*=12 on v (AUC > 0.9 vs HOPELESS) —
  else the census view itself is broken and nothing is claimable.

## Cost
GPU one lane serial, 4 seeds x ~1-2 min each on the 4050 (QO6t precedent). Ramp receipt per
INSTRUMENT-01. ~10 min total.

## Failure/anchor notes
Fail-loud anchors: lane construction errors raise, never silently widen gates. Results to
results/cc1_comfortable_collapse/. Booking in RESULTS.md with QUEUE mark regardless of verdict.
