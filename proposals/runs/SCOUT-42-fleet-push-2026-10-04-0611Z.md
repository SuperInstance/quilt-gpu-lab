# SCOUT-42 — SuperInstance fleet push sweep 2026-10-04 0611Z (22:1x AKDT day-conductor slice)

Window: post-SCOUT-41 (0411Z) → 0611Z, via `users/SuperInstance/events`. Read-only; no comments/PRs filed.

## HEADLINE — fleet-witness (NEW repo, created 01:29Z): RFC 6962 Merkle checkpoints over five-opcode receipts
- Witnessing study landed as a repo: Merkle-tree checkpoint layer over receipt chains, L0 truncate-demo
  (silent truncation caught by checkpoint), sibling-seal digest embedding (PR #3, branch sibling-seal-embedding
  pushed 05:10Z), documented Ed25519 signer seam (#5, open v0.1 seam), L3 witness-quorum designed-not-built.
- Classification: **TOOL / CORROBORATE**. This is the 5th converging witness on the seal-chain/reseal-forgery
  class (receiptd tipnotary 3-valued + limit-pin; MM #32 seal-pin --check; delta-shape sha256-pinned vendored
  consumption; now RFC 6962 inclusion proofs + truncate detection). Directly feeds **RC-4** (seal-chain /
  reseal-forgery resistance, still open): Merkle checkpoint over manifest seals gives O(log n) inclusion
  proofs and catches truncation — RC-4 spec amendment candidate. No threat to any booked result.

## TOOL/STEAL — quilt-tools #45: fresh-audit v0, phantom-RED detector
- "Run pins pristine, not in the author's tree": fresh depth-1 clone → run every discovered runner →
  RED-in-clone + GREEN-in-author-tree = phantom. Born from pong-quilt R85 (pin claimed gitignored `dist/`).
- Caught its own blind spot at birth (runners inherited caller CWD — fixed, CWD anchored). FAIL-first earned.
- Classification: **STEAL — this operationalizes OUR dirty-tree booking class** (3 instances found 2026-09-30,
  which is why mandatory (C) repro exists). Gap in our convention: our (C) repro runs in the author tree; a
  fresh-clone repro arm would catch the R85 untracked-artifact subclass our in-tree rerun cannot. Spawned
  **FR-1** below.

## Quiet / classified no-action
- pong-quilt #108 (R86 receipt audit re-land, first build) + #109 (R87 v1 baseline as GENERATED artifact):
  their lane, corroborates receipt-audit doctrine; no conflict with our bookings.
- the-tap #11: negative-space GAN edge fixes — no overlap with our assets.
- quilt-gpu-lab 05:09/05:20Z pushes on main = foreign conductor lanes (PIDFIRE-1 pre-fire stack, corr-floor-probe,
  bdf1444) — PW-1/foreign-live precedent; our newest OURS booking remains QG7b (repro PASS 12:2x Oct 3).

## No CONTRADICT this sweep
QO2 routing stack, DECIDE-1/2, receipt-manifest doctrine, QG3+QG6 time-law, QG1c swap census, W5a/W5b/W5c —
all unthreatened. [EMBASSY] pong #49 unchanged (Casey day item).

## SPAWNED QUEUE ITEMS
- [ ] **FW-2** (CPU reading ~30m): read fleet-witness docs/ + src/ (read-only); map RFC 6962 checkpoint
  structure (STH, inclusion proofs, truncate detection) onto our receipt-manifest; write RC-4 spec amendment
  (Merkle-seal-chain option) with the Ed25519 seam left explicit-and-unfilled. Gate: amendment must state
  what truncation/tamper case each existing pin misses.
- [ ] **FR-1** (CPU ~30m + policy): adopt quilt-tools#45 fresh-audit into our mandatory (C) repro convention —
  in-tree rerun (current) + fresh-clone arm for BOOKED results whose outputs are gitignored-adjacent;
  pre-register the policy line in docs/PREREG-CLAIM-PROTOCOL.md. Gate: fresh-audit smoke on our own HEAD
  (expect GREEN — all booking scripts tracked) else RED names the phantom.
