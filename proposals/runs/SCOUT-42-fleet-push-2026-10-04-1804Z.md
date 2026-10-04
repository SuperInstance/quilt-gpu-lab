# SCOUT-42 — SuperInstance push sweep, 2026-10-04 18:0xZ (day conductor slice)

Window: since SCOUT-41 (04:11Z). Method: search/commits org-wide (committer-date>=2026-10-04),
open PRs on watched repos, org issues updated >=2026-10-02. Read-only; no comments filed.

## HEADLINES (post-SCOUT-41)

### 1. MicroMoth-quilt PR #37 — FORGET shot-erasure opcode (CELL-MAPPING) — TOOL
Stacked #33→#37, main untouched. Shot-level collapse EFFECT cells are the erasure unit; counts
retained, individual collapse records FORGET-tabled; the FORGET itself is receipted
({shot, reason, erased_id}); downstream ids re-derive (tamper-evidence works THROUGH erasure);
erased_id diffs against any unforgotten copy; refuses empty reason/unknown shot/double-forget.
FAIL-first verified on pristine main; fresh-audit PRISTINE PASS; manifest 510→511.
- Classification: **TOOL / CORROBORATE** of QO6 (retractable kill-evidence gate). QO6's retraction
  currently *removes* kill-evidence from consideration; MM#37 shows the fleet convention: erasure
  is a first-class RECEIPTED event with re-derivability. Our QO6 retraction should be upgradable to
  this shape without touching the booked verdict.
- Spawned **QO6b** (see spool): FORGET-cell adaptation probe for QO6 retraction, with the
  canvas-tui #1 trapdoor as a mandatory negative-control gate.

### 2. quilt-canvas-tui issue #1 — PoEM gate trapdoor — HIGH-VALUE CAUTION (named trap)
"one FORGET seals an unverifiable receipt — every mutating op refused (LEDGER_UNVERIFIED) until
restart." I.e. receipted-erasure + seal-before-verify can WEDGE the whole ledger: the erasure
receipt is unverifiable (target gone), and a verify-first policy then blocks ALL mutation.
- Classification: **CORROBORATE of a class we don't have a booking for** — the deadlock mode of
  receipted forgetting. Threatens no booked result (we have no FORGET booking); it is the exact
  failure mode QO6b must gate against. Folded into QO6b as gate G3 (post-FORGET verify must
  return a defined FORGED/STALE-class verdict, never wedge, no restart required).

### 3. superinstance-lab wave-67/68 — SECURITY scrub + history rewrite + force-push
04c7b8e: "old typesafe key literal removed from 4 source files (env-read pattern); history rewrite
follows" (d0b9eea purge, b40dd75 gitlink refresh, 7ba022a CRITICAL lesson: commit ignore-hardening
BEFORE history rewrite). 9ebd081: live token verified, **21 repos ff-integrated (~560 commits of
others' work)**, exoj rebased onto wave-69.
- Classification: **CORROBORATE** — the 21-repo ff-integration explains the recurring FOREIGN live
  lanes in our author tree (d12k2–d12r untracked, w5a judge-board HEAD 0a5352a): integration waves
  push into fleet clones, not archaeology. PW-1/foreign-live policy validated.
- Keys: not echoed, not inspected (policy). Casey day item if our credentials were in the purged
  literal's blast radius — flagged, not acted on.
- 7ba022a lesson is steal-worthy for any future purge: harden ignores BEFORE rewrite, else the
  rewrite re-exposes via gitlinks/subrepos.

### 4. wave-68 "calibration shock (canon != good)" — TOOL/POSSIBLE CONTRADICT-ADJACENT
39e6d4d note title only read (timebox); their claim: canon (fleet reference implementations) does
not imply calibration quality. We landed tools/calib-gate (0b44bea, proper-scoring battery
ECE/Brier/AURC + KEEP/FAIL gate) hours earlier and have NOT yet pointed it at our own booked
probabilistic results.
- Spawned **CAL-1**: run calib-gate over our booked probabilistic verdicts (QO1 oracle AUC 0.9510
  headline, QO3 horizon curve). Pre-registered risk: QO1's AUC headline is discrimination, not
  calibration — if Brier/ECE says the oracle is over/under-confident, "first trained fleet
  component" needs a calibration rider. Their "canon != good" sharpens this: ours IS the canon
  for qcells.

### 5. exoj c50575c — ATLAS KIT (wave-66 decomposition as executable)
29 works, 528 elementary parts, 401 gates swept by jevs, agent-free replay. Not classified this
sweep (timebox); candidate TOOL for VX-1-style index automation. Filed as ATLAS-1 note, LOW.

## Quiet
- quilt-tools #46 (referral-graph edge #30 PENDING) — reading only.
- Issues quilt-ewitness #1 (stale duplicate witness.mjs crashes runners), selectlib #1 (loop-body
  dedent) — witnesses of the fleet DEGENERATE class; no action.
- No [EMBASSY] items found in window. pong #49 unchanged (Casey day item).
- quilt-matrix quiet since SCOUT-41's guard-bugfix coverage.

## Classification summary
- CONTRADICT: none (no booked result threatened).
- TOOL: MM#37 FORGET-cells (→QO6b); exoj ATLAS KIT (ATLAS-1, LOW).
- CORROBORATE: canvas-tui #1 trapdoor class; wave-68 ff-integration = foreign-lane mechanism;
  wave-68 security purge class (CI-1-adjacent hygiene).
- Open question: wave-68 "canon != good" vs our uncalibrated booked AUCs (→CAL-1).
