# EP-1d — Pointer arm v4 (corpus cross-reference) — PRE-REGISTRATION

Committed BEFORE fire. Spawned by EP-1c (booked RED 23:2x Oct 4, prediction falsified).

## Motivation
EP-1c showed the receipts/ directory is NOT the corpus of receipts-of-record — the shas'
receipts-of-record live in proposals/runs/*.md. v4 widens the pointer arm to the whole
committed corpus.

## Pointer arm v4 (the only delta from tools/ep1c_pointer_census.py)
WARN_POINTER iff ANY of:
  - path-hit (existing/tracked repo-relative path on the citing line)  [unchanged]
  - remote-hit (remote-pattern on the citing line)                      [unchanged]
  - CORPUS-XREF: the sha/digest token appears in >= 1 OTHER committed .md file
    (any tracked *.md, anywhere in the repo — receipts-of-record included wherever
    they live), excluding the citing line itself.                        [NEW]

WARN_FOREIGN / WARN_SELFSCAN arms unchanged; resolution arms unchanged; no network.

## Frozen gates (pre-registered, no re-roll)
- G-DRY (MANDATORY, before full fire): the 3 known standing sites must classify
  WARN_POINTER (not RED) on a dry-run over exactly those sites:
    #5  61b9e04  (RESULTS.md ~:2927, QO6 receipt pairs with quilt-ewitness)
    #6  6d3a1162 (RESULTS.md ~:4367/:6024/:6064, manifest-history seal prose)
    5bc6b78f digest (formerly WARN_POINTER in v2, regressed RED in v3)
  If any classifies RED on dry-run: STOP, book the dry-run result, spawn no re-roll.
- G-FULL: full census run to scratch. Expected verdict GREEN (all prior REDs absorbed
  into WARN_POINTER / resolved). If RED: verdict stands as booked, EP-1 lane CLOSES
  per STOP rule (three arms fired; remaining REDs are declared structural).
- Cost: CPU ~15 m. Read-only; output to /home/eileen/scratch/ep1d_census.json
  (--out refuses overwrite without --force, inherited).

## Declared caveats
- Corpus-xref is a WEAK pointer (an sha mentioned in prose is not a verified receipt) —
  v4 classifies POINTER, not GREEN; resolution still requires the resolved arms.
- Ledger-growth drift caveat inherited from EP-1b repro (census over a growing ledger
  shifts line numbers and adds self-referential claims; declared, not a delta).
