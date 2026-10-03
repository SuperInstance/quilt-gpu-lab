# EXOJ-IMITATOR V0 — the endless artist loop (design, 2026-10-02)

Casey directive (17:14–17:16): "iterate a system that can sound like an artist in MIDI
through JEV as a decomposition tool for building a stable imitator … a quilt of logic for
how to mimic an artist endlessly … the more artists we do the more dials we learn."
Duke-lab (Ellington/Evans/Monk) predates exoj; exoj adds the WHY-legibility layer.

## The loop (five stages)

A — CORPUS. Per-artist MIDI collections. widening lane: /home/eileen/projects/midi-corpus
(public-domain fetch, per-artist dirs, CORPUS.md index) + midi_to_trace.py adapter
(mido → dial_ruler trace format).

B — DECOMPOSITION (JEV + LLM together). dial_ruler.py extracts the 16 seed dials from a
per-note trace. LLM lanes propose NEW dials where the ruler is blind (feel, intent).
Each proposed dial becomes a typesafe JEV cell, calibrated: separate ≥2 artists above
chance, else journaled as learned failure. LAW #1 (measured 2026-10-02): AUTHORED ≠
MEASURED — duke-lab's published centroids are design targets, not facts (duke
trebleActivity authored .72, takes measure 0.000). Real corpus is the only referee.

C — STABILIZE. Frozen cell set + corpus-measured centroid + hash_spec → tipnotary anchor.
The imitator's "soul" is a receipted, externally-witnessed artifact (KV + i2i twin).

D — GENERATE (endless). Engine params ← centroid → plainsong (word layer) → MIDI
(byte layer). Every take receipted (corr = generation session). JEV cells gate; rejects
feed back as generation guidance — the quilt of logic compounding.

E — SPLINE + GROW. Interpolate artist fields (SPLINE protocol in tools/dial-lib/DIALS.md):
dist(extracted, (1−λ)A+λB) ≤ ε = the dial explains the output = ExoJ legibility, measured.
REUSE-LEDGER: dials reused / new / cloud-calls per artist — cloud-calls-per-artist must
DECREASE with N (the compounding claim, falsifiable).

## Honest gates
- Cells can't separate artists → decomposition failed for that dial; journal, don't re-roll.
- Spline ε fails → generator doesn't explain the dial; flag un-legible.
- Failed dial + journaled = still a learned dial.

## Next moves
1. corpus lane returns → real centroid medians per composer (COLLECT receipt)
2. Ellington→Monk spline demo (ε-gated)
3. artist #4 ledger row (Count Basie or Casey's pick)
4. wire field faces into exoj core.mjs (visible field)
