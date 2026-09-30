# Receipt Manifest Repair — d23b phantom seal (2026-09-30)

## Symptom
`tests.test_receipts.ReceiptManifestMatches.test_manifest_matches_working_tree` RED on main tip (d5e7009):
manifest claimed `d23b_relational_hidden_angle.py = 80e545bb…` while the committed file hashes `a0a204fe…`.

## Autopsy (all hashes re-derived, per-commit)
- `80e545bb…` matches **no committed revision** of the file. Every revision from fc79ff1
  through tip hashes `a0a204fe…` (verified: fc79ff1, 3368376, 5df2739, 9e4d661, tip).
- The phantom entered at fc79ff1 (RECEIPT-HASH "retroactive night-lane pin snapshot")
  and was carried forward by d5e7009 ("re-seal after QO6 instruments") — i.e. both seals
  hashed a working-tree state of d23b that was never committed (dirty-tree seal; the
  in-flight edit was reverted or reworked before commit).

## Class
Dirty-tree seal: the manifest sealed bytes that git never saw. The pin caught it the
moment someone ran the suite on a clean clone — the receipt layer working as designed.

## Remedy
- Manifest regenerated via `tools/receipt_manifest.py` (canonical, tool-generated).
- d23b entry now `a0a204fe…` = committed bytes; no source files touched.

## Follow-up candidate (NOT this PR)
Teach `tools/receipt_manifest.py` a `--require-clean` guard: refuse to seal when
`git status --porcelain` is non-empty over sealed paths (or record a
`sealed_from_dirty_tree: true` admission row). Would convert this failure class from
pin-caught-after-the-fact to refused-at-seal-time.
