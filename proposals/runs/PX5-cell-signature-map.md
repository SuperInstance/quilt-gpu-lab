# PX5 — cell-signature map (routing structure BETWEEN cells)

FROZEN 2026-09-30 ~17:26 AKDT, before any scoring run.
Class: **EXPLORATORY_MAP** — no confirmatory branch; findings feed router-cell design (CM1 r4+, superinstance-api reflex layer).

## Question

IE3 (intrinsic-emergence line) found: cells are dedicated specialists and routing happens BETWEEN cells. Nobody has measured the between directly. Does the per-state pattern of WHICH registry cells place their top-1 in the optimal set — the cell signature — segment the state space into interpretable regions?

## Instrument

- PX2 registry at depths (1,2,3,4,5,6) + pinch cell; PX1 seed-0 split; trees trained on TRAIN split ONLY.
- Per test state: 6-bit tree signature (per-cell top1-in-optimal: 1/0), × pinch axis (fired-correct / fired-wrong / abstain), × px1b class (WIN/BLOCK/NON_LOCAL), × composition-correct (exact MajorityVote combiner).
- Full 36,073-state test split (never trained on). Terrain digest asserted (`0x75f652bc1d8464b8`).

## Analyses (fixed before scoring)

1. Signature census: n unique, size distribution.
2. MI(signature, class) and MI(signature, composition-correct), bits — how much does WHO-succeeds-WHERE tell you about the state?
3. Unanimous partitions: 6/6-correct (reflex-compile candidates), 0/6-correct (systematic-bias candidates), mixed — sizes, class mix, composition top1 within each.
4. Router ceiling: any-cell-correct rate (incl. pinch), overall + per class, vs composition top1 — the headroom a signature-router could claim.
5. Per-cell × class correctness matrix — quantifies "dedicated cells" and which classes each owns.

## Honesty rules

No outcome switching. Deviations get a dated amendment before results are booked. Results book to `results/px5_disagreement/px5_map.json` + RESULTS.md entry marked EXPLORATORY_MAP.
