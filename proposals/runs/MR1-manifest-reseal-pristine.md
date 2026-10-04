# MR-1 — Manifest re-seal from pristine clone (spawned by FR-2, 2026-10-04)

Mandated by FR-2 booking (G2 RED-FOUND): the committed receipts/manifest.json at HEAD no
longer matches committed tracked files, so a fresh clone REDs on
tests/test_receipts.py (2 failures). Root cause: manifest re-seal deferred since SCOUT-25
because foreign untracked live-lane files (d12k2–d12t) make the sealer refuse in the
author tree. Separately, HEAD ab72e0e (soc-probe lane) added tools/soc_probe.py and an
uncommitted manifest edit exists in the author tree — both confirm the seal is stale.

## Procedure (frozen before fire)
1. Fresh `git clone file:///home/eileen/projects/quilt-gpu-lab /home/eileen/scratch-ext4/mr1-clone`
   at HEAD (ext4, not /tmp). Author tree untouched during sealing.
2. In the clone: `python3 tools/receipt_manifest.py` (regenerate + seal). Must NOT need
   --allow-dirty; if it refuses, STOP and book the refusal.
3. In the clone: `python3 -m pytest tests/test_receipts.py -q` — gate MR1-G1: all PASS.
4. Copy ONLY receipts/manifest.json back to the author tree (supersedes the stale
   uncommitted re-seal), commit + push.
5. Gate MR1-G2: second fresh clone of the NEW HEAD; pytest tests/test_receipts.py all
   PASS (the FR-2 RED is closed fleet-visibly).

## Gates
- MR1-G1: sealed manifest in pristine clone; tests green there.
- MR1-G2: fresh-clone witness at new HEAD green (FR-2 G2 complement flips RED→GREEN).
- No numeric booking verdict is touched (FR-2 already established this); docs/bookkeeping only.
- Keys never echoed; no foreign live-lane files modified; archive-never-delete.
