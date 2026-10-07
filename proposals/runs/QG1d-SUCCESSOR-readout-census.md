# QG1d-SUCCESSOR — readout-function census on the 28 swap-only misses (analysis-only, frozen candidate set)

Spawned by QG1d-micro-recon (2026-10-07): endianness is real but CANNOT explain the 28 (symmetric
targets => min-balance invariant under global relabel). All 6 wire-order candidates (C0–C5, QG1c)
leave ≥28 misses. This census freezes ONE new axis: the **readout function** applied to (p000, p111).

Corpus: exp022 telemetry k3–k7 (960 cells x 2 observables = 1920 pairs), read-only. TOL 0.044 unchanged.
Shot evidence: recorded values are multiples of 1/512 (e.g. 0.498047 = 255/512) => shot-derived counts.

## Frozen candidates (NO post-hoc expansion)
- R0: min(p000, p111)           — current convention (reproduces C0 booking)
- R1: p000                       — marginal on |000>
- R2: p111
- R3: (p000 + p111) / 2          — mean balance
- R4: p000 * p111 * 4? NO — frozen set is R0–R3 only, plus the wire candidates C3 (both-reversed)
  crossed with each readout (C3xR0..R3), since endianness x readout is the one interaction QG1c
  could not test. Total evaluated: 4 readouts x 2 wire conventions = 8 cells.

## Gates (pre-registered, words)
- G1 (named-convention): a cell reaches anchor 1920/1920 (every pair within TOL) => verdict NAMED,
  name the cell. Full re-anchor required, not just the 28.
- G2 (readout-28): a readout f under C0 puts ALL 28 C0-failing pairs in-band AND keeps the 1892
  C0-anchored pairs in-band => verdict READOUT:f (even if G1 fails on other candidates).
- G3 (stochastic-vs-systematic): for pairs still failing under the best cell, test
  |exact - recorded| <= 4*sigma, sigma = sqrt(p(1-p)/512) with p = exact; report count outside.
  All-outside => SYSTEMATIC (a convention/semantics difference remains); any in-band => mixed.
- STOP: regardless of outcome, one fire, no re-rolls, no candidate additions. Verdict booked
  honestly in RESULTS.md either way; NONE is an acceptable booking.

Cost: ~2 min GPU (batched statevectors, n=3, ~few hundred unique genomes). Reuses
experiments/qg1c_swap_convention.py machinery (import; main-guarded).
