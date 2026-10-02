# d13d_correlation_keys

## WHAT IT IS

Between-cell routing keys by **correlation, not reward**. Two halves of
one primitive:

1. **Shared-key discovery (D13d)** — each cell observes a stream of ±1
   atoms; true partner pairs share a hidden base with a persistent
   POLARITY (the shared key: partner atom = `polarity * base` with prob
   `p_corr`, else an independent coin). A cell finds its partner by
   argmax |mean(a·b)| over the other cells — **zero parameters, zero
   reward**. Anti-correlated partners key as strongly as correlated ones;
   the `|·|` read is the doctrine.
2. **Centroid-correlation routing (COMP0/COMP1)** — the same correlation
   read as the 0-parameter between-cell ROUTER: per-cell keys are the
   mean of that cell's train features; an item routes to the cell whose
   key has the highest Pearson correlation with it (across feature
   dimensions).

## WHY (the booked receipts)

- **D13 → D13c** (RESULTS.md, 2026-09-27, all KILL) — Hebbian,
  confidence-weighted, and REINFORCE-with-baseline reward all fail to
  learn the relational partner (edge concentration 0.217–0.30 vs chance
  0.143; ~32 reward updates per edge, a 0.5 signal buried in coin-flip
  noise). The D13 arc's point: reward accumulation is the wrong
  mechanism, not the wrong hyperparameters.
- **D13d (KEEP)** — shared-key discovery cracks it at **1.0**
  (8 cells, 200 observations, p_corr 0.9, target ≥ 0.90). "The
  relational primitive is CORRELATION DETECTION (mutual information), not
  reward accumulation. O(1) information, not gradient descent over
  reward." (Booked bug at source: first run used cyclic pairing —
  scrambled streams, 0.375; fixed to disjoint pairs, which this block
  enforces by construction.)
- **D18 (INCONCLUSIVE, two findings)** — correlation confirmed and
  STRONGER than claimed: identification 1.0 on the whole grid (N=8..300 ×
  p_corr=0.55..0.9 at T=200); the real SNR floor sits near 0.25, not
  0.5 — `p_corr` IS the expected key strength, so any `p_corr>0` is
  discoverable given enough observations. The contrast half FALSIFIED:
  REINFORCE also reaches concentration 1.0 on CONSISTENT partners (D13c's
  0.217 was one policy chasing ~7 conflicting targets). **The primitive
  is "consistent relational target"; correlation is the O(1) way to FIND
  it.**
- **COMP0/COMP1** (2026-10-01) — as the router: COMP0 routing saturated
  (1.0/1.0 train/held-out, top1–top2 gap 0.49 — the corpus gave the
  router a free pass); COMP1 desaturated exactly to spec (held-out
  0.7356, gap 0.041) — correlation routing is merely decent under real
  ambiguity, and a saturated router means the federation ceiling is its
  weakest cell.

## INTERFACE

```python
make_atom_world(n_cells=8, t_obs=200, p_corr=0.9, seed=2718,
                polarity="shared"|"anti"|"mixed")
    -> (streams (n_cells, t_obs) int8, partners {cell: cell})
    # disjoint pairs; BadWorldError on odd n_cells / bad params (fail loud)

correlation_key(stream_a, stream_b) -> float   # |mean(a*b)| — the key
key_matrix(streams) -> (n, n)                  # diagonal -1 (never wins argmax)
discover_partners(streams) -> {cell: cell}     # D13d: argmax |corr|, no reward
partner_accuracy(true, hat) -> float
key_margin(streams, partners_true) -> [float]  # key(true) - best distractor, per cell

pearson(x, y) -> float                         # zero-variance guard: keys 0
build_centroid_keys(features_by_cell) -> {cell: mean-feature key}
route(keys, x) -> cell                         # argmax-Pearson routing
```

## PROPERTIES

- Deterministic, seed 2718 default; CPU-only, stdlib+numpy, seconds.
- Fail loud: impossible worlds (odd cells, empty streams) raise
  `BadWorldError`; cross-shaped inputs raise, never broadcast.
- The self-test gates a cross-seed key-MARGIN seed-mean (continuous, so
  the frost law is satisfiable): **std == 0 ⇒ INCONCLUSIVE, never PASS**.
- Honest floor: `p_corr=0` (fully independent partner atoms) is the
  chance control — `p_corr=0.5` is NOT chance (expected key 0.5); that
  distinction is D18's "stronger than claimed" finding.

## COMPOSITION

- **Upstream of `ternary_transition_kernel`**: its `FieldWorld(edge_source=...)`
  hook accepts discovered acting edges — a `discover_partners` map can
  drive the world's pair stream (cells that discovered each other act on
  each other), closing the D13d→D19 loop the composition map anticipated
  ("shared_key_discovery upstream block").
- **The routing half of a federation lane**: `ie3_dedicated_trunks`
  supplies the dedicated cells this block routes BETWEEN (the COMP0/COMP1
  wiring: dedicated cells + correlation router + look-again escape hatch).
- D12 note (booked at source): with HAND-GIVEN perfect addressing the
  graph already reaches 1.0 — this block is the mechanism that EARNS the
  address instead of being handed it.

## SELF-TEST

From the lab root, CPU-only, <2s:

```
python3 blocks/d13d_correlation_keys/block.py
```

(1) D13d reproduction at seed 2718 and on 3 seeds (acc ≥ 0.90 each, all
1.0); (2) D18 grid subset — (8,0.75), (32,0.6), (32,0.55), (100,0.6) all
1.0; (3) chance control p_corr=0, N=32 × 5 seeds — collapses to the
floor (booked ≈0.01 vs floor 0.032); (4) polarity: anti and mixed shared
keys still discovered at 1.0; (5) centroid router: 3 cells × D=32
patterns, 450 held-out items, routing 1.0; (6) fail-loud contracts;
(7) frost law on the gated margin seed-mean (booked margin ≈ 0.78 ±
0.05). Final stdout line is exactly one JSON object with one top-level
`"verdict"`; exit 0 iff PASS.
