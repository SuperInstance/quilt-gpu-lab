# SCOUT-59 — 2026-10-07 10:14Z (02:1x AKDT day-conductor slice). Read-only sweep.

## Window
Pushes since 2026-10-07T08:15Z (post-SCOUT-58): NONE external (latest fleet event 07:49Z).
But this sweep found a **SCOUT-58 MISS**: `git.pp` created 06:22Z (inside SCOUT-58's declared
06:15Z window) and pushed 06:41→07:49Z — absent from SCOUT-58's notes. Lesson: creator events
(CreateEvent) must be enumerated, not just PushEvents on watched repos.

## Findings
1. **git.pp (NEW repo, 5 commits, classify: TOOL/STEAL + CORROBORATE)** — "git projected as an
   agent substrate: the tick, the projector, the bodies." Key commits: c266f23 projector with
   soul/axes + `project.sh` + **post-receive hook with 40 checks** ("Opus draft") + test-pp.sh;
   3c1b1b0 question-loop.md — "the Jev-scored process for projecting to next questions";
   6fbbc92 glossary: demarcation as first-class act; 83db864 tick.sh fix (temp file not process
   substitution — MiniMax cold-user playtest).
   - STEAL → RC-5 delta: their post-receive 40-check inventory is a live reference design for
     exactly our RC-5 remaining layer (push-time `--check`: sealed digests vs tracked files,
     exit 2 on drift). PP-1 spawned below.
   - CORROBORATE: Jev-scored question-loop = our queue/spool doctrine (pre-reg → fire → book)
     restated as a git projection; demarcation-as-act mirrors "a check that cannot fail"
     (fleet-triage epitaph / DEGENERATE class).
   - No CONTRADICT: QO2 stack, receipt doctrine, QG3+QG6, QG1c, W5a/W5b/W5c, DECIDE-1/2 all
     unthreatened.
2. **unoq-node (NEW repo, 1 commit, classify: CORROBORATE, LOW)** — "git-native body package
   for Arduino Uno Q (task 007)". Hardware-edge witness for the hundred-boats doctrine;
   relevant to W5c edge-mine seed (git-native receipts at the edge = receipt doctrine pushed
   downstream). Docs note only; no queue item.
3. PRs: 0 open across quilt-gpu-lab / micrograd-quilt / pong-quilt / canons / delta-shape.
   Issues: zero-msg-test self-escalation spam (known noise). [EMBASSY] pong #49 unchanged.

## Spawned queue item
- **PP-1** (CPU reading ~20m, docs): read git.pp projector post-receive checks (c266f23) +
  question-loop.md; produce a mapped checklist — which of the 40 checks overlap RC-5's
  push-time --check delta, which are new instruments worth stealing (tick verify_one pattern),
  which are decoration (RC-1b class). Gate: RC-5 spec amended with a cited check-by-check
  table or an explicit "nothing to steal" verdict.

## (C) mandatory repro — newest OURS booking ST1-AUDIT
- Committed runner `experiments/st1_audit_op_leakage.py` re-run from the committed tree,
  output to /tmp/st1audit_repro/results.json (scratch, ext4 path not used; /tmp acceptable for
  a throwaway compare). **REPRO PASS: 30/30 flat result fields identical** to committed
  results/st1_audit/results.json (seed 2718 deterministic; verdict KEEP-AUDIT, LEAKY
  verdict_flip + tau_off at AUC 1.000 confirmed). Manifest: foreign untracked d12x/d12y lane
  persists — re-seal deferred per standing precedent; no sealed paths touched.
