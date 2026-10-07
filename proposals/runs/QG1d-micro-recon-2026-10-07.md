# QG1d — micromoth simulator byte-level recon (read-only; spawned by QG1c verdict NONE)

Pre-registration scope (from QG1c booking, 07:1x Oct 1): read micromoth's exp022 simulator
source and report swap/crx semantics byte-level; no re-run of the census, no booked result
modified. This file is the receipt. Partial finding 07:2x Oct 1 (generator provenance gap:
`qcell` package absent from micromoth-quilt tree and ALL its branches) is superseded below.

## Where things actually live (provenance CLOSED)
- Genome builder / search loop: `micrograd-quilt@origin/main:labs/qcells/qcell/search.py`
  (MM PR #29 citation convention was right — canonical home is micrograd-quilt, NOT
  micromoth-quilt; the exp022 receipt script in micromoth-quilt imports `qcell.search`
  from a path that only resolves in the micrograd-quilt labs tree).
- Simulator: `micromoth-quilt@HEAD:micromoth.py` (MicroQiskit derivative, fleet-altered
  2026-10 for injected rng; statevector, complex-as-[re,im] pairs).

## Semantics verified (line-level)
- Angles: genomes carry PI-UNITS (`THETAS=[.25,.5,.75,1.0]`), multiplied by pi at
  `genome_circuit` build time (search.py:47-49). Matches our declared convention.
- `turn` (rx): algebrally EXACT rx = cos(θ/2)x − i·sin(θ/2)y on the pair (verified by
  expansion of the [re,im] arithmetic, lines 138-141).
- `phaseturn` (rz): exact e^{∓iθ/2}. `superpose` (h): exact.
- `crx`: RX on target pair (k[b10],k[b11]) iff source bit 1 — standard CRX, control
  semantics match ours.
- `swap`: k[b01]<->k[b10] — a STANDARD swap. No hidden convention in the gate itself.

## FINDING (differential-confirmed): global qubit-label ENDIANNESS divergence
- micromoth indexes qubit j at statevector bit weight 2^j (LSB-weighted; single-qubit
  pairing loops, lines ~180-186) while printing the n-bit index MSB-first ⇒ **genome
  qubit 0 is the RIGHTMOST character of the output bitstring**.
- Our `tools/qcell_sim.py` extracts control bits via `(s >> (n-1-c)) & 1` ⇒ qubit 0 is
  the LEFTMOST character.
- Differential test (this receipt, 7 genomes x target "100", exact + 400k-shot):
  micro_p([["x",0]]) = 0.000 vs ours = 1.000; relabel q→n-1-q arm matches micromoth
  exactly (1.000). [[x,2]] mirrored. crx/cx/swap genomes agree under relabel.
  **Endianness divergence is REAL and reproducible.**

## Does it overturn QG1c? NO — and the reason is structural:
A global qubit relabeling leaves p_target invariant for SYMMETRIC target sets
(the exp022 lane targets are ("000","111"), mode=balance). Wire relabeling permutes
probabilities among target strings; min over a symmetric pair is unchanged. The
relabel arm reproduced ours==micro on all symmetric-target probes (r4 champion
0.4261/0.4268 agreement stands). **QG1c verdict NONE is untouched** — but the census's
frozen candidate set (6 candidates, all pairwise-substitution family) never included
GLOBAL label reversal. For any FUTURE asymmetric-target lane, cross-tool genome
exchange MUST relabel q→n-1-q; this is now a named convention, not a suspicion.

## Corollary for the 28 swap-only misses (honest, no claim)
Endianness CANNOT explain them (symmetric targets ⇒ invariant). micromoth's swap and
all gates are standard. Remaining hypothesis for QG1c's 28 misses moves OFF simulator
semantics onto the PRODUCED genome corpus (which genomes the lane actually emitted /
how exp022 scored them — shot-count mode="balance" at 512 shots vs our exact
probabilities is a stochastic-vs-exact mismatch with systematic tie-band effects at
BAR). That is a QG1d-successor question (corpus-side, not simulator-side).

## FW-1-successor notes
- `tools/qcell_sim.py:73-88`: `elif name == "crx"` block appears TWICE (identical);
  second is dead code. Harmless (identical semantics) but flagged.
- micromoth `simulate` default rng=None mutates module-global `random` — any receipt
  lane not passing injected rng is cross-contaminating global state (their own docstring
  flags it; fleet fix landed 2026-10).

Status: COMPLETE (recon only; no GPU; no booked result modified; read-only on
micromoth-quilt@4268849 and micrograd-quilt@origin/main).
