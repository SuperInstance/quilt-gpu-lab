# CC-1b PREREG — torch-seed-pinned re-certification of CC-1 (spawned by CC-1 amendment 890dd1d-class defect)

Commit this file BEFORE firing. Fire only after this commit is pushed.

## Question
CC-1 (commit 01e7843) exposed a mixed-RNG hole: `torch.rand` in the selection key draws from the
UNSEEDED torch global RNG while mutation draws are numpy-seeded. Lane construction (c24, c12,
subpopulation counts) is therefore a torch-RNG draw, and the G1 construction gate flip-flops across
re-runs. Re-run the identical census with torch RNG pinned per (numpy seed, torch draw) and
re-certify.

## Design (CC-1 verbatim, one change)
- Kernel: experiments/cc1_comfortable_collapse.py run_lane_trajectory VERBATIM, single change:
  `torch.manual_seed(seed*10 + draw)` at lane entry (before any torch.rand), so each lane is fully
  reproducible given (seed, draw).
- 4 numpy seeds {11,12,13,14} x 3 torch draws {0,1,2} = 12 lanes, S=512, W=6, gens=24, g*=12,
  bar=0.45 — identical to CC-1 otherwise.

## Gates (frozen before firing)
- G1 (CONSTRUCTION): per-seed c24 mean across draws within 0.755±0.05 AND per-seed c12 mean within
  0.578±0.05, AND per-draw spread of c24 <= 0.10 (draw-sensitivity must vanish; CC-1 saw
  seed14 0.699/0.725 flip-flop). G1 now judged on the ENSEMBLE, not single draws (QG7 convention).
- G2: fenced pooled n >= 40 across all 12 lanes.
- G4: EARLY control v-AUC min > 0.9 across draws.
- G3 (PRIMARY, re-book): pooled v/rank/len/rate AUC at g*=12 over ALL 12 lanes; same bands as
  CC-1: all in [0.45,0.60] => CONFIRMED; any >= 0.75 => NEW_FEATURE; else INCONCLUSIVE.

## Verdict rules
- G1 PASS + G3 verdict == CC-1 verdict => CC-1 stands, amendment closed, convention (pin torch seed
  in lane kernels) booked.
- G1 FAIL (bands unrecoverable even pinned) => escalate to Casey day-item; QO6t/QG6/QG3 anchors
  inherit a stronger caveat.
- G3 verdict flips => amend CC-1 in place, never silently (protocol).
- Stop rule: one firing, no re-rolls, no gate tuning.

## Cost
GPU (RTX 4050): 12 lanes x ~1-2 s ≈ well under 5 min. Serial lane, free at slice open.
