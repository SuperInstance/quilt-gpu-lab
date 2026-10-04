# SCOUT-43 — 2026-10-04 20:0x UTC (12:0x AKDT day-conductor slice)

Window: post-SCOUT-42 (~18:00Z). Sweep = SuperInstance user events since 18Z + repo tips.

## Headline — quilt-tools PR #45 "fresh-audit v0: phantom-RED detector" (18:14Z)
Their wound class: pong-quilt R85 shipped a pin that claimed gitignored `dist/` artifacts — RED on any
fresh checkout, GREEN in the author's tree. Their fix direction: **run pins pristine, not in the
author's tree.** This is EXACTLY our MR-1/FR-2 fresh-clone-witness doctrine (tools/fresh-clone-witness,
MR-1 booked 09:0x today, FR-2 lesson: keep both arms — naive-complement + external auditor).
Classification: **CORROBORATE (strongest of the sweep)** — 4th/5th independent instance of the
author-tree-blind pin class; our instrument already exists and is committed. No build needed.

## quilt-tools #47 — edge #31 VERIFIED citing OUR receipt doctrine
Books `aw-quint-opcode → gl-ledgers`, evidence = quilt-gpu-lab#2 README's own declared edge
("minted VERIFIED by this citation, per the fleet weight law"). The fleet's referral graph now
consumes our receipt-doctrine provenance directly. CORROBORATE; no action.

## MicroMoth-quilt PR stack #38–#42 (18:xx–19:06Z)
- #39–#41 injected-RNG seam: receipt lanes stop mutating the module-global RNG; byte-identical
  MT19937 receipts verified. TOOL/STEAL candidate — the "no global RNG state mutation" pin
  convention maps onto our QG7 lane-nondeterminism lesson (torch generators should be injected,
  not ambient). LOW priority.
- #42 VIEW clause: "the ledger records which view was taken" (counts/statevector/probs as three
  views of one chain). Mild corroboration of receipt doctrine; no action.
- (#37 FORGET already consumed by SCOUT-42 → QO6b.)

## jev-quilt PR #48 (19:21Z, branch r6-run2-live-probes)
r6 run-2 live probe battery, 8 new distortion classes, record-only, zero threshold changes.
New named gap F4: "fabricated temporal anchor" → REVIEW (not REJECT) — timestamps are forgeable
unless anchored. Maps onto our receipt doctrine (seal timestamps vs claim timestamps). LOW reading
item at most; QC-JEV bookings untouched.

## superinstance-lab 91cb242 wave-69 sync + 1ce36a5 wave-68 close
Housekeeping/mirror re-cut; gitignored-by-law. No action.

## Verdicts
- **No CONTRADICT this sweep.** QO2 stack, receipt-manifest doctrine, QG3+QG6, QG1c, W5a/W5b,
  QO6b all unthreatened.
- Spawned: **QT-1** (CPU ~20m, LOW): read quilt-tools #45 fresh-audit source; diff their
  phantom-RED detector vs our tools/fresh-clone-witness (coverage matrix: gitignored-claimed
  artifacts, untracked foreign files, sealed-path drift); file alignment note, no code unless
  they miss a class we cover or vice versa.
- Note: MM-RNG pin convention (injected generators) recorded for the QG7-ensemble successor lane.

## Mandatory (C) — executed this slice
Newest OURS booking = QO6b (f74fc94, booked 11:1x). COMMITTED `experiments/qo6b_forget_cell.py`
re-run with the GPU-venv python: **verdict FAIL reproduced identically** — G1/G2a/G2b/G3b/G4 all
PASS, G3 FAIL (verify-after-forget TAMPERED, first_bad_seq 1; append-then-verify TAMPERED) exactly
as booked. **PASS.** No GPU item fired (scout was the rotation slot); lane idle.
