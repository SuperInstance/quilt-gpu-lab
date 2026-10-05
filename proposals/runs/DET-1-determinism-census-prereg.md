# DET-1 — Determinism-witness census (pre-registration)

Spawned by SCOUT-45 (2026-10-05 1915Z), citing jev-quilt r6 PRs #50–#53 (G1/F1 bimodality on identical
bytes): a verdict booked from a single draw of a nondeterministic lane would false-green our committed-repro
gate, which today has no explicit determinism requirement.

## Question
For every BOOKED verdict in RESULTS.md, which determinism class is the producing lane in, and does any
class-(c) (torch-GPU nondeterministic) booking rest on a single draw without an ensemble or nondeterminism
receipt?

## Classes (exactly one per booking)
- (a) EXACT — statevector/integer/text arithmetic; deterministic by construction (e.g. qcell_sim.py exact
  statevector, EP-1 text censuses, eproc.mjs port, REPORTER-DEFAULT probes).
- (b) SEEDED — committed RNG seed + pinned generator; deterministic IF seed+generator are in the committed
  artifact (verify: seed literal present in committed tool).
- (c) NONDET — torch-GPU / cuDNN nondeterministic path. Verdict MUST be an ensemble (QG7 law) or carry an
  explicit nondeterminism receipt (e.g. QO1's ±0.006 CP95 note). Single-draw class-(c) booking = RED.

## Scope (timeboxed, staged)
- Tranche 1 (this slice): all `## [BOOKED` entries from 2026-10-04 onward (post-doctrine era, ~16 entries).
- Tranche 2 (open, next wake if time expires): legacy D/E-series bookings (2026-09-27 → 10-03), same gates.

## Gates (pre-registered)
- G1: every tranche-1 BOOKED entry appears in the census table with exactly one class and an evidence pointer
  (tool file + determinism mechanism named).
- G2: every class-(b) classification is backed by a seed literal found in the COMMITTED tool (git show HEAD,
  not working tree).
- G3: every class-(c) booking names either an ensemble (≥2 draws or replicates) or a booked nondeterminism
  margin; otherwise it is a RED row.
- G4: verdict = PASS iff zero RED rows in the tranche; RED rows are named with booking line numbers and a
  proposed remedy (ensemble re-fire or margin receipt), never silently re-rolled.

## Method
Read-only over RESULTS.md + git show of committed tools; no GPU fired; no instrument code written. Output
census table appended to RESULTS.md as a BOOKED entry; this file is the pre-reg.

## Cost estimate
CPU, ~25 min reading + greps. No network beyond local git.
