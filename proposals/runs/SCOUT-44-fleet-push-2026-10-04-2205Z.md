# SCOUT-44 — fleet-push sweep, 2026-10-04 2205Z (day conductor, ~20m slice)

Window: post-SCOUT-43 (2004Z). Scope: SuperInstance pushes 0411Z→2205Z, but SCOUT-42/43
already consumed 0411Z→~1959Z; this sweep's NEW substance = the org-wide merge wave
21:4x-21:5x ("push-everything sweep day", per lucineer-system 764c665) + repos SCOUT-43
didn't cover.

## State changes in window
- Org-wide merge wave ~21:42-21:58Z: most repos show batch merges of PRs already reviewed
  by SCOUT-42/43 (MM #33-#41, pong playtest rounds #102-#113, fleet-triage edge-watch
  #14-#22). Merge-only, no new content beyond what was read.
- fleet-triage PR #12 (merged, 8187868): cite-only adoption note (unfalsifiable-gates
  antidote → fleet-kit L9/L10 canary). CORROBORATE of CI-1/DEGENERATE bill; no action.
- pong-quilt #113 R91: lag-count regex 1→\d+ "the count is a garnish" — test-narrowing
  note; matches our FW-1 field-write sensitivity class (a pin stricter than the contract).
  LOW, recorded only.
- quilt-research-canons 3595add wave-69 knowledge package: docs mirror, no findings.

## HEADLINE — fleet-witness L1-L5 witnessing study LANDED (PRs #1-#6 merged 21:4x)
- L1: witness-repo git anchoring (anchor.js scoped to checkpoints/ tree).
- L2 part 2 (#3) sibling-seal digest embedding: `embedRow(seal)` emits ONE ordinary WAL
  row `BIND witness-anchor origin=... digest=<sha256 of note body>`; `verifyRow` NEVER
  trusts the row's digest field — re-derives from the PRESENTED note (catches truncation
  and forged-note). 10 pins.
- L3 (#4): witness quorum DESIGNED-NOT-BUILT (C2SP tlog-witness v1.0.0 shape, n=3 across
  3 trust domains k=2, strict-majority t ≥ ⌈(n+m+1)/2⌉, persist-before-cosign, honest
  semantics: "split-view resistance = fail-closed freezing, not convergence").
- L4 rejected. #5: Ed25519 signer seam; **the sig line never enters the anchored digest —
  anchors bind canonical body only** (they DELETED a byte-drift pin; canonical bytes are
  the doctrine, not exact bytes).
- #6 L2 dup-check: fleet-witness-checkpoints is data-only, anchor.js not taken (honest
  scope note).

### Classification vs our assets
- **TOOL/STEAL (primary): L2 sibling-seal embedding is the external anchor our RC-4
  residual lacks.** Our receipt-manifest re-seals are SELF-attested — SCOUT-16/RC-4 noted
  a valid RE-seal of modified content is currently undetectable in-repo. Embedding our
  seal digest as a BIND row into a git-anchored witness note makes post-hoc re-seal
  detectable (anchor digest freezes the sealed bytes). Spawned **FW-W1** below.
- CORROBORATE x2: (a) canonical-body-not-exact-bytes for anchored digests matches our
  manifest canonicalization (seal over canonical content, presentational bytes free);
  (b) L3 "designed-not-built with FAIL-first pins so the design cannot silently rot" is
  the pre-reg doctrine applied to design records — same shape as our FT-D1/SS-1 items.
- No CONTRADICT: QO2 stack, QO6c, receipt doctrine, QG3+QG6, QG1c, W5a/W5b all unthreatened.
  Their L2 threat model (sibling truncation/forgery) is about EXTERNAL notes, not our
  bookings.
- [EMBASSY] not re-checked this slice (pong #49 was unchanged through SCOUT-43; day item).

## Spawned
- [ ] **FW-W1** (CPU ~30m, pre-reg first): adopt L2 embedding one-way — after each manifest
  re-seal, emit a BIND row (origin=SuperInstance/quilt-gpu-lab, digest=manifest seal sha256)
  into a local witness-note file staged for Casey to anchor (no push without him). Gate:
  a verifyRow-style checker re-derives the digest from the SEALED manifest and catches
  (i) post-embedding re-seal drift (ii) truncated manifest (iii) forged digest row.
  Closes: RC-4 residual. Cost: zero metered; pure file work.

## Slice bookkeeping
- (C) not due: newest OURS booking QO6c (4b610ab/d9dc6cd, 13:2x) already verdict-repro'd
  PASS in its closing slice (6cea835). HEAD since is foreign lanes + spool/docs.
- Untracked foreign live lane in tree: `experiments/d12u_orderstats_model.py` +
  `results/d12u_orderstats_model.json` (d12u, untracked, not ours) — PW-1 precedent,
  NOT touched, flagged for the owner lane.
- GPU lane idle; nothing fired (scout was the rotation slot).
- Rotation next wake: (B) FW-W1 (new, top — cheap and closes RC-4) or VX-1/SS-1 per
  queue order; GPU open (QG1d/QG4/MC-1).
