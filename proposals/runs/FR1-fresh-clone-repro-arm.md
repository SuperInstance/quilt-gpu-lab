# FR-1 — FRESH-CLONE REPRO ARM (pre-register; spawned by SCOUT-42 / quilt-tools#45 fresh-audit)

## Motivation
Our mandatory (C) repro runs in the author tree — it cannot catch the R85 untracked-artifact
subclass (booking depends on a file that was never committed; in-tree rerun still passes because
the file is present locally). quilt-tools#45 fresh-audit catches this class by re-running from a
pristine clone.

## Policy change (docs/PREREG-CLAIM-PROTOCOL.md)
Mandatory (C) repro = in-tree rerun (current) PLUS a fresh-clone arm for BOOKED results whose
producing artifacts are gitignored-adjacent or whose tool imports untracked scratch paths.
Fresh-clone arm: `git clone --depth 1 <repo> <ext4 scratch>` (NOT /tmp — tmpfs), run the committed
entry point with no PYTHONPATH tricks, compare verdict. GREEN = verdict reproduces; RED names the
phantom artifact. In-tree-only results (data in results/, sealed) may note "fresh-clone N/A: data
sealed" instead of running.

## Smoke gate (this fire)
Fresh-clone HEAD cad3e5c to /home/eileen/scratch-ext4/fr1-clone (create if absent; ext4 under /home),
run `python tools/verdict_index.py selftest` + the 3 taint queries from VX-1's booking.
- FR1-G1 PASS if selftest G1-G4 PASS and taint sets identical to booking (QO6 / VSB-1 / []).
- FR1-G2 (policy guard) PASS if the smoke's scratch dir contains no untracked-from-author-tree files
  (i.e. everything the run needed came from the clone). RED => name the phantom.
- Cost: CPU, <2 min.
