# FR-2 — fresh-audit external witness of quilt-gpu-lab HEAD (spawned by SCOUT-43 / quilt-tools#45)

## Question
Does an INDEPENDENT phantom-RED auditor (quilt-tools#45 `fresh-audit.mjs`, read-only, fetched
from the open PR) find any RED runner on a pristine checkout of our HEAD that our own
bookings saw GREEN — i.e. the R85 author-tree-blind class, checked by someone else's tool?

## Instrument
`node fresh-audit.mjs --local <dir>` (quilt-tools PR #45 head 67f4db29, diff vendored to
scratch, never installed into our tree). v0 limits inherited honestly: convention-based
runner discovery (tests/pins*.sh, test*/run.js, demo/*.js, npm test w/ committed
node_modules) — it may discover ZERO of our pytest-based pins; that is a TOOL-gap finding,
not a pass.

## Deviation from SCOUT-43 wording (declared BEFORE fire)
SCOUT-43 said `--local` against our own tree. Author-tree mode defeats the phantom purpose
(the tool's own docstring says pristine). Target = pristine `git clone` of our HEAD
(file:// local clone, FR-1 arm, ext4 scratch). If the tool's discovery finds nothing, we
complement with the FR-1 fresh-clone probe on the booked-result-producing scripts it missed
(the VX-1 selftest is the newest OURS booking instrument) so the slot produces signal either way.

## Gates (frozen before fire)
- FR2-G1: fresh-audit runs to completion against the pristine clone of HEAD, exit code recorded, no crash.
- FR2-G2: every runner it discovers on our tree gets a verdict; any FAIL (RED) names the booking it threatens or is booked as a finding — zero unexplained RED.
- FR2-G3 (complement, only if discovery gap): committed VX-1 selftest (tools/verdict_index.py) passes in the pristine clone — identical to FR-1 smoke; if it FAILS in pristine but passed in author tree, that is a phantom (RED) and contradicts FR-1.
- FR2-G4: no writes to our tree, no GPU, no network beyond gh pr diff fetch.

Cost: CPU, ~15m. STOP rule: any RED on a booked result → book the RED, no fixes this slice.
