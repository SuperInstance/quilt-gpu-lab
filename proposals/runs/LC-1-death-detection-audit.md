# LC-1 prereg — conductor death-detection audit (SCOUT-56 spawn)

Date: 2026-10-07 05:1xZ (21:1x AKDT Oct 6). CPU, docs-only, ~20 min. No behavior change without Casey.

## Question
Does a heartbeat-line-per-slice + re-check-before-claiming pattern (taskable-lobster/ledger-continuity
5818938 doctrine: "recovery requires liveness in the ledger; work claims alone are insufficient — you
need a death detector") catch every historical conductor-death instance in this repo?

## Method
1. Enumerate historical mid-slice-death / unbooked-artifact instances from RESULTS.md + spool.
2. For each, ask: would (a) a heartbeat line appended at slice START to a wake-log file, plus
   (b) re-check-before-claiming (next wake verifies the previous heartbeat's slice reached its
   booking commit), have caught it within one wake?
3. Enumerate residue classes a death can leave: untracked artifacts, unbooked results, un-pushed
   commits, partial prereg (committed, never fired), fired-but-unbooked.

## Gates (frozen, words)
- G1: audit enumerates >= 3 historical instances with citations (commit/RESULTS line).
- G2: for each listed instance, heartbeat+recheck is shown to catch it at the next wake (or the
  instance is explicitly filed as UNCAUGHT with the residue class named).
- G3: verdict is a table; no protocol change is made in this run (Casey gate).
- G4: docs-only; no experiment fired; manifest may be re-sealed only if tree is clean of foreign
  live-lane paths (else deferred per PW-1 precedent).

## Bookable outcomes
- PASS: every enumerated instance caught by heartbeat+recheck at next wake.
- PARTIAL: catches with named residue class(es) uncaught.
- FAIL: pattern catches fewer than half — escalate to Casey with the gap named.

Cost: CPU seconds, docs-only. Fail-loud: audit fails if a cited instance cannot be anchored to a
commit or RESULTS line.
