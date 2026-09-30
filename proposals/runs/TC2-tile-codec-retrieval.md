# TC2 — Does training the 384-byte bottleneck for RETRIEVAL (not reconstruction) beat both TC1 winners?

Pre-registered 2026-09-29, fired immediately after commit+push. Follows TC1's finding: cosine fidelity and
retrieval are decoupled (int8 was near-lossless yet retrieved worse than truncated text; the MSE-trained
bottleneck was worst of all). TC2 asks whether the OBJECTIVE, not the budget, was the problem.

## Design (frozen)
- Corpus + embedder + evaluation IDENTICAL to TC1 (2525 real tiles mined from our own docs; gte-small 384-d;
  query = question embedding, index = codec representation, top-1/top-5 over the whole corpus). Reuses the
  TC1 harness code directly so nothing drifts.
- Arms, each exactly 384 bytes:
  A) deterministic text fields (TC1 A, recomputed in-process)
  B) int8 full-dim (TC1 B, recomputed)
  C) MSE bottleneck 96-d (TC1 C, retrained with a fixed seed)
  E) RETRIEVAL bottleneck 96-d: encoder 384->96 trained with InfoNCE over (question, tile) pairs,
     in-batch negatives, temperature 0.07 — index = enc(tile), query = enc(question)
  F) HYBRID 96-d: MSE + InfoNCE (lambda 1.0 each)
- Metrics: top-1, top-5 (all arms); cosine fidelity where a decoder exists (A, B, C, F).

## Frozen gates
- G1 RETRIEVAL_OBJECTIVE_WINS: max(top-1 of E, F) >= top-1(A) + 0.05.
- G2 BEATS_INT8: max(top-1 of E, F) >= top-1(B) + 0.05.
- G3 RECONSTRUCTION_STILL_RULES: max(top-1 of E, F) <= top-1(A) (the objective did not help).
- Otherwise TIE. All arms reported. Harness bug -> diagnose, discard, re-fire. No re-rolls.

## Predicted (recorded before firing)
The retrieval objective will beat the MSE bottleneck, and may beat the text codec: guess G1 fires.
If G1 fails while A still leads, that is strong evidence that explicit surface terms are the real carrier
of tile identity — i.e. text fields are not merely a legacy format.
