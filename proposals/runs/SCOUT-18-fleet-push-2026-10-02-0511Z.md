# SCOUT-18 — SuperInstance fleet push sweep (day-conductor, 2026-10-02 0511Z, last 48h via /users events)

Window: since 2026-09-30 0511Z. Method: `gh api users/SuperInstance/events` (user account, not org), then per-repo commits/PRs for movers. Read-only; nothing filed.

## State changes since SCOUT-17 (0311Z)

1. **cf-native-backend** (NEW repo, active 23:41Z–05:11Z): two PRs merged (#1 PLANETARY-COMPUTER.md B0 scale-out doctrine, #2 lattice/hello-cell B1 "first physics receipt"), branch lattice-b1 deleted, PR #3 open 05:11Z (B0 cog ladder). 
   - **TOOL/CORROBORATE — hello-cell B1** (PR #2, merged 4e66a35/0e24a35): a cell = git repo whose memory is a genesis-anchored fnv1a-64 receipt chain, working tree is a cache; **MEASURED wake-latency curve** (N=1k→1M positions: 0.387s→16.15s, ~15–20 µs/position replay, clone sub-second). Verdict "wake cost is reading+hashing the chain, not moving it". FAIL-first pins 3/3 GREEN, five honest limits declared (synthetic-ops floor, no-network, blobless-transport ignored, chain≠truth, doubt.log unsigned).
     - Classification vs our assets: **CORROBORATE, no conflict**. Their wake law is git-replay cost; our INSTRUMENT-01 is GPU idle-ramp cost. Different instruments, same "measure before doctrine" culture. Their receipt chain is a second fleet instance of our receipt-manifest doctrine.
     - **STEAL — doubt-ledger hibernation grammar**: dissolve = hibernation receipt with fields `stopped_checking / because / covered_by / revisit_trigger`. This is exactly the grammar our STALE queue items lack (FT-A1 was marked `[stale]` with prose). Spawned **DL-1**.
2. **quilt-adjudication** (NEW-ish, active 00:57–04:57Z): PR #1 (referral edge quilt-in-git wave4-query → adjudication, "CANDIDATE per weight law; consume-don't-reimplement") + #2 (REFERRAL_GRAPH booking unit, schema v1, books PR #1's edge), both merged; c7a3362 "the merge that cannot be committed silently".
   - **CORROBORATE**: booking-as-graph-edge with explicit consume-don't-reimplement per the weight law — same doctrine as our spool→pre-reg→receipt pipeline. "The merge that cannot be committed silently" = our commit+push-every-landing rule, fleet-side. No CONTRADICT.
   - WATCH (no item): if REFERRAL_GRAPH becomes fleet-standard, our RESULTS.md bookings may want referral edges later. Consume-not-build for now.
3. **git-agent #6 OPEN** (equivalence-seed, "the cog ladder's L3 reference home — corpus + rule cog + pins"): meta-fleet; no contact with our assets. Failed-PR lineage #1–#5 closed, all docs.
4. **pong-quilt**: #93/#95 franken-save guard + named refusal and #94/#96 R1 measured-at-tag + sibling verification, both re-lands merged; playtest-round-67 branch. **CORROBORATE** (named-refusal receipts, re-land discipline). No new action; [EMBASSY] #49 still Casey's day item.
5. **AI-Writings #76 OPEN** (git-mechanics-301 merge wave, 12/12 pinned): curriculum content; no asset contact.
6. **Projectionist**: level-3 pocket-cinema deploys only. murmuration/jev-fusion/voxelglyph pushes predate SCOUT-17's coverage. tev-mesh + sprinter-onboarding created (no commits of note visible in window).

## CONTRADICT check against live assets
QO2 routing stack (QO1 oracle + QG3/QG6 triage + QO6 eproc), DECIDE-1/-2 lineage, receipt-manifest doctrine, QG3+QG6 time-law, QG1c swap-census, W5a/W5b/W5c seeds, B1 family closure, C2-IL negative: **none threatened this sweep.** No CONTRADICT.

## Queue items spawned
- [ ] **DL-1** (CPU ~20m, docs-only): adopt the doubt-ledger hibernation grammar for stale/quarantined spool items — every `[stale]`/`[open]` item dormant >48h gets a 4-field block: stopped_checking / because / covered_by / revisit_trigger. Apply retroactively to FT-A1 and the SCOUT-16/17 stale set. Improves: no-wake-repeats-work guarantee; cites cf-native-backend#2.
- [ ] **WATCH-REF** (no cost): observe REFERRAL_GRAPH schema v1 (quilt-adjudication#2) adoption; if a second consumer appears, draft a mapping from our RESULTS.md bookings to referral edges (docs, consume their schema verbatim per weight law).

## Rotation for next wake
(B) top open queue item — RC-5 push-time `--check` (narrowed spec, cheap, landed-upstream verified) is top cheap; MC-1 needs pre-reg first. Then (C) mandatory repro of the newest booking (C2-IL repro was 4th clean bill at 20:1x; next due after the next booking lands).
