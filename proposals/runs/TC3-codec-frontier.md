# TC3 — The 384-byte frontier: how far can a retrieval-trained codec compress before it loses to text?

Pre-registered 2026-09-29, fired immediately after commit+push. Follows TC2 (retrieval objective beats MSE and
the deterministic text codec at 384 bytes). TC3 asks the next question: the frontier, not a single point.

## Design (frozen)
- Corpus, embedder, and evaluation IDENTICAL to TC1/TC2 (2525 real tiles from our own docs; gte-small 384-d;
  query = question embedding, index = codec representation; top-1/top-5). Harness reuses the TC1 module.
- Arms:
  - Reference points (not swept): A deterministic text fields at its fixed 384 bytes; B int8 384 bytes.
  - Swept: retrieval-trained (InfoNCE) bottleneck at 48, 96, 192, 384 bytes (12, 24, 48, 96 float32),
    plus hybrid (MSE+InfoNCE) at 96 bytes for the readability comparison.
- Metrics: top-1, top-5 per budget; bytes per budget; the KNEE = largest budget whose top-1 is below
  the text codec's.

## Frozen gates
- G1 FRONTIER_MONOTONE: top-1 is non-decreasing as the budget grows (allow 0.01 slack for training noise);
  violation => record the inversion, do not re-roll.
- G2 CROSSES_TEXT: at SOME budget <= 192 bytes, the retrieval codec's top-1 >= 0.7164 - 0.01 (the text
  codec's score at its own 384 bytes) => a learned codec matches a 384-byte text codec in half the bytes.
- G3 KNEE_ABOVE_48B: the 48-byte arm's top-1 < 0.7164 (compression does have a floor).
- Verdict: FRONTIER_CROSSES (G2 and G3), FLAT (not G1), NO_CROSS (not G2). Report every point.

## Predicted (recorded before firing)
Retrieval should hold up at 192 bytes and degrade at 48. Guess: G2 fires, G3 fires, verdict FRONTIER_CROSSES.
