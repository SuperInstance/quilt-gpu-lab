# SEAL-1 — seal-scope deadlock fix (tracked-files-only seal surface)

Spawned by GOLDEN-PIN 2026-10-09 15:4x audit (AUDIT RED): committed seal stale
23 commits, CI red since Oct 6. Root cause: the PW-1 foreign untracked lane
(experiments/d12*, d12y/d12z/SUBSTRATE-SYNTHESIS) lives inside a SEALED path;
`dirty_sealed_paths()` counts untracked files → every re-seal refused since the
lane appeared → permanent staleness, and RC-5 `--check` fired red at every push.

## Fix (candidate A, preferred per spawn note)
`tools/receipt_manifest.py` change of seal SURFACE, doctrine-preserving:

1. `build()` seals **git-tracked files only** (`git ls-files` filter within
   experiments/ + tools/, plus RESULTS.md/QUEUE.md ledgers which are always
   tracked). Rationale (from GOLDEN-PIN): "what git saw" is the sealable
   surface — the d23b phantom-seal autopsy was about hashing UNCOMMITTED
   bytes; untracked foreign-lane bytes were never claimable by us anyway.
2. `dirty_sealed_paths()` narrows to tracked-file drift only (modified/staged
   tracked files under sealed paths). Untracked files under sealed paths no
   longer refuse the seal; they are printed as an advisory row (no exit).
3. `--allow-dirty` admission row semantics unchanged (tracked drift only).
4. No changes to check() logic — it compares via build(), so the surface
   change propagates.

## Pre-registered gates (frozen words, before firing)
- **G1**: fresh clone at HEAD --check exits 0 after fix + re-seal + commit+push.
- **G2**: mutation reds M1 (single-byte flip of a pinned experiment file),
  M2 (RESULTS.md truncation), M3 (seal-recipe self-modification) all still
  REFUSE under the new surface, in a throwaway clone.
- **G3**: dirty-guard refuses a tracked-but-uncommitted edit to a sealed path
  (exit 2); an untracked file appearing under experiments/ does NOT refuse
  (advisory only).
- **G4**: `pytest tests/test_receipts.py` green locally (currently FAIL 2/49);
  CI green on the next push.
- **Verification arm (no verdict text changes)**: prior bookings' committed
  scripts are unchanged by the surface filter — enumerate any booked-verdict
  scripts dropped vs kept by the tracked filter; expected: all committed
  booking scripts are tracked, so seal membership only GROWS-CLEANER (removes
  only never-committed foreign bytes).

Cost: CPU ~20 min. Honest-fail plan: if G3 shows the narrowed guard now misses
a phantom-seal class, record as FAIL, do not weaken the admission semantics
further; fallback is Casey-gated relocation of the foreign lane (candidate B).
