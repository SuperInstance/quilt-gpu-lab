# PX4 — information-through-ASCII (DRAFT — terrain check pending, NOT frozen)

**Status: draft queue. Freeze (commit-first) before any fire.**
Origin: gpu2 fleet doc "ASCII-to-Puppet" proposal — grounded here against fleet doc Exp 6
(voxelglyph) settled nulls before it gets built.

## Why this framing

The gpu2 doc proposes ASCII grids as low-rank feature latents feeding a JEPA-style
predictor. The fleet has ALREADY run this family (Exp 6): glyph/braille observations
alias — luma is a rank-1 projection (403 RGB units apart, same glyph), and alphabet
ALIGNMENT, not size, controls collisions; exp3 sat at chance for every brightness alphabet.
So the question is not "build the pipeline" — it is **how much predictive signal survives
the compression**, measured against settled failure modes.

## Arms (fixed budget, same tiny predictor per arm — GRU/MLP, CPU-scale)

- **A — raw:** downsampled grayscale grid at the same cell resolution (upper bound)
- **B — chiaroscuro:** the ASCII grid as-is (alphabet as the engine emits it)
- **C — canonical:** each glyph mapped to its byte value (the exp6 alignment correction)
- **D — ablation control:** same token budget, alphabet shuffled per frame (floor)

## Metrics

1. Held-out next-frame token/state prediction error (per arm)
2. Downstream regression: recover the sim's ground-truth control state (e.g., rudder
   angle / impact vector) from the representation alone
3. Alignment-vs-size explicitly reported (exp6 lesson)

## Terrain (pending check)

1. Synthetic game-engine stream first — exact ground truth, controlled motion; the
   digital-twin "snap" loop from gpu2 is useful HERE as the harness (sim = free truth),
   not as evidence.
2. Real camera via chiaroscuro doors second, only if arm C ≈ arm A on synthetic.

## Pre-registered branches (freeze at commit time)

- C ≈ A: compression is ~free when the alphabet is canonicalized → edge thesis earns
  its next rung; gpu2's pipeline becomes buildable with receipts.
- B << C: aliasing (not bandwidth) is the binding constraint AGAIN → exp6 correction
  replicates in a new domain; publishable as a domain-transfer confirmation.
- C << A: ASCII-class encodings cannot carry this signal at any alignment → KILL the
  glyph-latent lane on synthetic terrain; boat camera work waits for real frames.

## Guards

Palette/material collinearity (exp6 confound), unequal input widths, degenerate labels —
all four exp2 failure classes checked before any number is booked.
