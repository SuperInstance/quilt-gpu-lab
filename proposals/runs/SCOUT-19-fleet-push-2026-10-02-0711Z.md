# SCOUT-19 — fleet push sweep, 2026-10-02 0711Z (day conductor slice A)

Method: read-only `gh api` over SuperInstance repos, commits last 48h, focus on pushes after SCOUT-18
(0511Z). No comments/PRs filed. Read-only throughout.

## Notable pushes and classification (against live assets)

### 1. breakthrough-prospector f0034fd (2026-10-01 2354Z) — FALSE PASS voided: **STEAL + CORROBORATE**
Their slice-2 repair receipt documents a gate bug we must name: the inherited pass line computed
`M >= 0.05x baseline` instead of `M >= 1.05x baseline` (relative-margin off-by-one, missing the `1+`).
It FIRED A FALSE PASS (promoted A5, cost rule PAID), then was voided with the buggy receipt preserved
verbatim and the repaired runner pinned. This is the single most instructive fleet event this sweep:
- CORROBORATE: SYN-1 (gate base-rate/vacuity audit) is not paranoia — gate-arithmetic bugs producing
  false passes are REAL and fleet-wide. Our committed gates (QO6 eproc V1-V4, QG3/QG6 paired-CI code,
  comp2 G-IL2 paired-gain CI) are exposed to exactly this class.
- STEAL: their doctrine — voided receipt preserved verbatim, repaired runner sha pinned, named
  `mutation_space_inert` flag, "future slices must copy the repaired form". Maps onto our
  archive-never-delete + fail-loud anchors. Adopted into the spawn below.
- Threat check: no booked result contradicted YET — that is precisely why the audit must run.

### 2. fleet-triage ce125d6 (0441Z) "IT-DEPARTMENT: the harness is broken, and that is the report" — **CORROBORATE**
Plus 2399226 GRACEFUL-FAIL (degradation axis attached to provenance) and dc61dcf THE-LOOP. The fleet is
converging on "a broken harness reported honestly is a finding." Second independent witness this window
for SYN-1's premise (first was their own 88e30b3 retraction). No CONTRADICT of our bookings.

### 3. cf-native-backend e2d419a/d697dc6 (0710Z, minutes before this sweep) — **CORROBORATE + TOOL**
B3.6 wires the git-api surface LIVE into the membrane router (POST /diff, /merge) + B2 live receipt:
wake-on-URL on real Artifacts, 178 ms, tipMatch. First live (not offline) deploy of the fleet's
merge-that-cannot-be-committed-silently lineage. B3.5 N-agent concurrent merge rig (d07d1eb) is a TOOL
candidate for our RC-4 seal-chain design (concurrent forks landing through one merge surface = the exact
reseal-race RC-4 worries about). Read-by-execution recon when a lane frees.

### 4. doubt-ledger 549c395 (0239Z) selective-disclosure export + Ed25519 root signing — **TOOL for RC-4**
Second fleet implementation of cryptographic seal-chaining (with quilt-jev-toolkit c9840b2 checkpoint
signatures + partial-custody replay seeds as the third). RC-4 is no longer greenfield: fold these two as
prior art and consume their key-handling conventions (keys never echoed — matches house rule).

### 5. quilt-adjudication a6c3508 (0655Z) "the record's handle pointed at nowhere and named the wrong target" — **WATCH-REF update**
Bug fix on the REFERRAL_GRAPH record schema (v1 merged 04:57Z via PR #2). Our WATCH-REF item should
re-read the schema before drafting any RESULTS.md->referral-edge mapping; the handle semantics just moved.

### 6. quilt-jev-toolkit d943d27 (0653Z) bootChrono — **TOOL (noted)**
Sealed chrono sheet boots as an organ. Relevant to SEAL-2 (crash-safe sealing) and RC-4; no conflict.

### CONTRADICT scan: **none.**
QO2 routing stack (QO1 oracle + QG3/QG6 triage + QO6 eproc), DECIDE-1/2 post-mortems, receipt-manifest
doctrine, QG3+QG6 time-law, QG1c swap census, W5a/W5b/W5c edge-mine seeds — all unthreatened by anything
pushed. INSTRUMENT-01 corroborated again implicitly (quilt-mojo-lab 0d8efa8 fp16 curves output follows
the ramp law their receipt cites).

## SPAWNED ITEMS
1. **GATE-MARGIN** (CPU ~30m, audit, spawned by #1): sweep every committed gate arithmetic site
   (experiments/*.py gate/verdict blocks, tools/eproc.mjs thresholds, comp2 paired-CI) for the
   relative-margin off-by-one class (`x*k` vs `x*(1+k)`), and for vacuous always-true/always-false gates
   (SYN-1 fold-in). Gates in words: (G1) enumerate gate predicate sites mechanically, list file:line;
   (G2) for each, assert the comparison direction against its booked intent quote; (G3) any site where
   removing the gate flips no verdict = vacuous, name the booking it props up; (G4) findings booked even
   if clean (null result is the point). Cost: 0 GPU-Wh, one Python pass + reading.
2. **RC-4 prior-art fold** (docs-only, ~10m): amend proposals/runs RC-4 spec with doubt-ledger Ed25519
   root signing + jev c9840b2 checkpoint signatures as fleet prior art; consume their key conventions.
3. **WATCH-REF** amendment: re-read quilt-adjudication schema after a6c3508 before any mapping draft.

## Costs
0 GPU-Wh, CPU-only sweep + writes. No rate limits hit (one 404 on repo name guess, not retried).

## SEAL STATUS (post-booking)
Manifest re-seal REFUSED by the sealer (correct): live D12K2 lane carries untracked
experiments/d12k2_entangled_certified.py + results/d12k2_entangled_certified.json (another agent's
active work; untouched per 18:1x precedent). `--check` at HEAD is RED as designed: RESULTS.md drift
(sealed df9ba8… live aec182…) + the UNSEALED d12k2 file. Seal rides the D12K2 lane's next clean
point; the RED is the honest state, not a failure to hide.
