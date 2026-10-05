# EP-1c — pointer arm v3 (machine-checkable pointers; pre-registered BEFORE fire)

Spawned by EP-1b booking (21:2x Oct 4). Parent pre-reg: `proposals/runs/EP-1b-seal-census-v2-prereg.md`.

## Motivation
EP-1b's two standing REDs (#5 sha 61b9e04, #6 sha 6d3a1162) fired because the v2 WARN_POINTER
classifier is keyword-narrow, while the underlying pointer reality is machine-checkable:
a receipt-hit actually holds for both. Lesson booked in EP-1b: classifying-by-keyword
re-imports the prose-understanding problem the census exists to avoid.

## Tool
`tools/ep1c_pointer_census.py` (new file; v2 tool stays frozen as-fired).

## Delta from EP-1b (ONLY this; no other deltas)
WARN_POINTER is now **machine-checkable**, satisfied iff any of:
1. **Path-hit**: the citing line names a repo-relative path under
   `results/|receipts/|tools/|experiments/` that EXISTS on disk or is tracked in git
   (`git ls-files --error-unmatch`, cached once).
2. **Receipt-hit**: the sha appears in any COMMITTED receipt file (`receipts/*.md`
   tracked at HEAD — untracked working-tree receipts do not count).
3. **Remote-hit**: the citing line names a remote + sha pair
   (`github\.com|SuperInstance/|workers\.dev|\.git\b|remote` within the line).

WARN_FOREIGN / WARN_SELFSCAN / RED classifications, resolution arms (manifest →
git-object → recursive artifact → historical blob), scope, gates G1–G4, and the
declared no-network deviation are byte-for-byte EP-1b semantics.

## Frozen gate / prediction
Verdict GREEN iff RED=0. **Expected at fire time**: EP-1b's 2 standing REDs reclassify
to WARN_POINTER via arm 2 (receipt-hit for 61b6e04-pairing/QO6 receipt and the
6d3a1162 manifest-history narrative); verdict flips RED → GREEN. Ledger will have grown
since EP-1b (census-over-growing-ledger caveat carries forward); any NEW RED = finding,
booked honestly, no re-roll.

## Hazards carried forward
Read-only by default; explicit `--out` only; refuse overwrite without `--force`.

## Cost
CPU only, ~10–20 min (same bounds as EP-1b).
