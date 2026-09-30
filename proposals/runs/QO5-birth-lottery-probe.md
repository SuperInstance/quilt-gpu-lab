# QO5 — birth-state insufficiency probe (analysis-only; pre-reg AMENDMENT, declared retroactive)

Spawned by QO3 (spool 04:5x). Classification: analysis-only census on the QO3 lane — no new
experimental arm, so no separate pre-reg file was written before firing. Declared here
retroactively per protocol honesty rule. The probe DID re-run the lane (seed 1234, 4096
streams, QO1-identical code path), which also produced a free replicate of QO3 (see below).

## Question
WHY is g0 oracle AUC exactly 0.500? Either (a) g0 champion states are diverse but
uninformative (landscape decides, stream state irrelevant), or (b) g0 states are
near-identical across streams (birth = shared lottery; first mutation + selection round is
the first observable branch point).

## Pre-registered decision rule
- g0 state diversity LOW (cv std ~0, identical states across streams) => (b): desert-at-birth
  means birth LOTTERY; gen-1 selection is the first branch point. Name it and close.
- g0 state diversity HIGH but AUC 0.500 => (a): landscape decides independent of stream state.

## Method
`experiments/qo5_birth_probe.py` — reuses `run_lane_states` from qo3_horizon.py verbatim
(seed 1234). Census of g0 champion state across 4096 streams: len unique values, v/cv std,
gate-histogram across-stream std, fraction of streams with byte-identical birth cv, and
birth-cv AUC vs eventual crossing.

## Result — branch (b), unambiguous
- len unique at g0: [2] (single value); v0 std 0.0; cv0 std 0.0
- frac streams with cv identical to stream 0: **1.0**
- gate-histogram across-stream std: 0.0
- birth cv mean crossed vs not: 0.0 vs 0.0; AUC 0.5 (trivially)

All streams are born from ONE shared skeleton draw with NO state divergence before the first
mutation + selection round. g0 AUC = 0.500 is not "uninformative representation" — there is
literally nothing to distinguish streams at birth. **Birth is a lottery; fate diverges at the
first selection round** (consistent with QO3: g1 AUC 0.88-0.89).

## Free QO3 replicate (honest note)
The probe's lane re-run overwrote results/qo3_horizon/results.json with a fresh sample:
rate 0.5769 -> 0.5789 (inside the recorded ±0.006 torch-nondeterminism band), g0 AUC still
exactly 0.500, g* still 1, MLP g1 AUC 0.880 -> 0.892. QO3 conclusions unchanged; replicate
strengthens them. Committed as-is (this file is the receipt for the overwrite).

## Feeds
- QO2: routing can only start at gen >= 1 (confirmed structurally, not just empirically).
- QG2 tension RESOLVED: desert is a birth-landscape property (exp018 cloud), but every stream
  samples that same landscape from the same starting point — divergence is created by
  mutation+selection, not by birth state.
- QG6 relevance sharpened: with identical births, any variance intervention (bigger
  mutations) acts on the FIRST move-set — exactly the slow-climb-vs-move-set question.

Artifacts: experiments/qo5_birth_probe.py, results/qo3_horizon/{qo5_birth_probe.json,qo5_run.log}.

## Pinned instruments

Retroactively sealed 2026-09-30 (RECEIPT-HASH): instrument hashes for the tools
used by this run are pinned in `receipts/tool_pins_2026-09-30.md` (snapshot as of
seal time, not fire time — earliest verifiable baseline). Forward-looking receipts
pin at fire time.
