# FW-2-IMPL — verify + book foreign-landed merkle_seal_chain.py against frozen spec gates

Spawned: FW-2 spec (14:2x slice). Trigger: commit 2451028 (SuperInstance, 2026-10-10 15:43 AKDT)
landed tools/merkle_seal_chain.py implementing the FW-2 v2 schema. No booking exists yet —
this prereg freezes the gates before any verdict reliance. Landing is foreign-authored but
tree-tracked; booking is ours (honest verification, not authorship).

## Gates (frozen from proposals/runs/FW-2-merkle-seal-chain-spec.md — implementation follow-on)

- **G1 vectors**: the tool's selftest battery reports PASS, AND an independent RFC 6962
  cross-check written in THIS prereg (not imported from the tool) reproduces: empty-set
  root == SHA-256(""), singleton root == SHA-256(0x00||leaf), and a 4-leaf corpus root
  computed by the spec's split-at-largest-power-of-two recursion matches
  `merkle_root_iterative` byte-equal. STOP rule: if the independent vectors disagree,
  book the divergence as RED and do not patch the tool to pass.
- **G2 chain**: the tool exposes prev_digest chaining per spec item 4; tampering
  prev_digest in a copy of a sealed manifest causes its verify path to fail loudly
  (exit != 0 / RED naming the chain field). If no verify-able chain RED exists, book RED.
- **G3 truncation**: dropping k>=1 leaf rows from a sealed v2 manifest yields RED with
  size named first (or size+root mismatch), per spec item 3. If truncation verifies
  clean, book RED — that is the exact RC-4 hole this amendment exists to close.
- **G4 non-regression**: v1 behaviors intact — `tools/receipt_manifest.py` clean-seal
  path still refuses dirty tracked sealed paths (exit 2 on a dirtied copy) and exits 0
  clean; existing tests/test_receipts.py (if present) green; GIT-ANCHOR-1 verify reports
  ANCHORED at the booking HEAD.

## Protocol

- Prereg committed+pushed BEFORE firing (this commit). Run from the committed tree.
- No GPU. CPU minutes only. No retry loops. Keys never echoed. Archive-never-delete.
- Honest booking in RESULTS.md with QUEUE mark; manifest re-seal in the SAME commit as
  the ledger append (SEAL-2 lesson).
