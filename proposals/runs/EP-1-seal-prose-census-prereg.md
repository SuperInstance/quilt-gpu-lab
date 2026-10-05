# EP-1 — seal/event-prose census (pre-registration)

Spawned by SCOUT-42 (jev-quilt PR #49 F4 fabricated-temporal-anchor / event-shaped assertions doctrine).
Frozen BEFORE fire. Cost: CPU ~15 min. No GPU. Owner: day-conductor 2026-10-04 17:0x AKDT.

## Question
Do all seal/event-shaped prose claims in our ledger (RESULTS.md, receipts/) resolve to real,
verifiable anchors — a manifest entry, a git object, or a committed receipt — or do we carry
F4-class fabricated event anchors ("sealed at the seventy-fifth wipe") of our own?

## Instrument
`tools/ep1_seal_census.py` (committed in this same commit, pre-fire, per doctrine).

Scope (fixed at pre-reg):
- RESULTS.md (full, 6001 lines)
- receipts/*.md (manifest-repair, tool_pins)
- Receipts authority: receipts/manifest.json (all embedded digests) + git object store.

## Frozen gates (words)
- **G1 census completeness**: tool extracts every 64-hex token from scope files and every
  short-sha seal/event claim matching `(seal(ed)?|commit(ited)?)\s+[0-9a-f]{7,40}` in a
  seal/event-prose line; counts reported; fail-loud on unreadable scope file.
- **G2 digest resolution**: every 64-hex token is RESOLVED iff it (a) appears anywhere in
  receipts/manifest.json, (b) is a live git object (`git cat-file -t` succeeds), or (c) is
  the sha256 of a named artifact file present in the tree at fire time. Otherwise RED.
- **G3 seal-prose resolution**: every seal/event-shaped named commit/short-sha resolves to a
  git commit or a committed receipt line. Unresolvable seal-prose = RED (the F4 class).
- **G4 fail-loud verdict**: GREEN iff RED=0 across G2+G3; any RED names the file:line.
  STOP rule: no re-roll, no scope widening after fire; REDs are booked honestly and either
  repaired by commit or amended-in-place with cause.

## Predicted outcome (pre-registered risk)
Expect GREEN with a small census (≤10 digest claims, ≤30 seal-commit claims); known-risk
lines: the sha256 `0e3f424c…` (line ~5809, from a foreign-lane citation) and the corpus
sha256-sequence `5bc6b78f…` (line 5221 — a derived-data digest, not a tree file) — both may
need the git/receipt arm to resolve. If either REDs, verdict is FAIL and repair is a commit
(never a silent edit, per QO6b lesson).
