# QC-JEV — discriminating-control pin for the jeff oracle (pre-registered 2026-09-30 ~10:15 AKDT)

## Motivation (SCOUT-4 CONTRADICT)
murmuration (created 15:26Z 2026-09-30) published `jev_control.json`: positive "2+2=4" and
negative "2+2=5" both return argmax=unclear (0.74/0.79) on jev-1.13.0 — a positive control and
its negation read the SAME ⇒ oracle non-discriminating. Our DECIDE-1 lineage (G2 below-chance
5/64, DECIDE-1b fitted temp 1.1289, DECIDE-1d "representation-locked argmin", DECIDE-2 surgery
proposal) reads jeff's answer distribution as signal. Their control is jev-1.13.0, ours is
jeff-0.8b — threat, not refutation. This probe decides which reading holds ON OUR CHECKPOINT.
MUST fire before any DECIDE-2 work.

## Probes (frozen)
Reader: trained (shipped readout), default temperature 1.1289 (from decision_config.json —
same path as DECIDE-1). Checkpoint: /home/eileen/scratch/external/jeff-checkpoints/jeff-0.8b.
1. noul POSITIVE: state {"expression": "2+2", "claimed_result": "4"}, instructions
   "Is the claimed result of the arithmetic expression correct?" — expect TRUE.
2. noul NEGATIVE: same state, claimed_result "5" — expect FALSE.
3. choice POSITIVE: options {"4": "correct sum of 2+2", "5": "incorrect sum of 2+2"} — expect "4".
4. choice NEGATIVE: options {"4": "incorrect sum of 2+2", "5": "correct sum of 2+2"} — expect "5"
   (note: content swapped, letters fixed — also a mini content-following check).

## Gates (frozen, in words)
- DISCRIMINATING (DECIDE-2 premise stands): the positive and negative probes SEPARATE —
  noul p(true) differs by >= 0.10 between probes 1 and 2 AND argmax of the noul answer flips
  direction consistent with truth; and at least one choice probe picks the content-correct code.
- NON-DISCRIMINATING (DECIDE-2 premise VOID, DECIDE-1 G2 re-read as calibrator defect):
  positive and negative probes return (near-)identical distributions — |p(true)_+ − p(true)_-| < 0.10
  AND choice argmax identical across probes 3/4, regardless of which code wins.
- PARTIAL: anything between; book as-is, DECIDE-2 blocked pending human read.
- DEGENERATE clause (SCOUT-4 steal, applied): if the two probes return byte-identical
  distributions, verdict is NON-DISCRIMINATING-DEGENERATE and additionally flags that the cell
  output may not depend on the state at all.

No re-roll, no temperature tuning, no reader swapping (one exploratory zeroshot pass may be
BOOKED as a secondary observation but carries no verdict).

## Cost
CPU-only, 4 forward passes of a 0.8b backbone ≈ 1-2 min. No GPU lane.
