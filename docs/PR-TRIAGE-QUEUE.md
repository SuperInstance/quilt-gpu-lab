# PR Triage — standing lane (playbook + live queue)

Casey's directive (2026-10-01 10:19): work through all the pull requests, learn from
what others are pushing, resolve and merge — and let it enhance our own understanding
and applications. This file is the lane: playbook above, live queue and learnings
log below. Companion tool: `tools/pr_sweep.py` (read-only triage; NEVER merges).

## The loop (every PR, no exceptions)
1. **INVENTORY** — `python tools/pr_sweep.py --out scratch/pr-sweep-<date>.md`.
2. **READ THE DIFF** before any verdict. Others' pushes are mining input, not noise.
3. **LEARN** — extract anything stealable (technique, config, test pattern, workflow
   trick) into a learnings-log row. "Nothing new — routine bump" is a valid row: it
   makes the learning a decision, not an omission.
4. **VERIFY** — CI green or diagnosed. Fast-fail (<90s total) = config-break suspect:
   diff `.github/workflows` vs the last green commit, fix forward in ONE commit.
5. **RESOLVE** — merge (repo's convention), rebase, or close-with-reason. Merges need
   hands/approvals; the sweep tool never acts.
6. **BOOK** — append the learnings row here; anything mine-grade goes to the
   spool/mines pipeline (edge-mine convention).

## Rules
- Never merge red. Never merge without reading the diff. Never leave a learning unstated.
- Dependabot: patch/minor + green => batch-merge; majors get a real breaking-change scan.
- `.github/workflows` or security-sensitive paths in a diff => read the FULL diff,
  not the summary. Supply-chain rule.

## Live queue (2026-10-01 morning state — pre-sweep)
- **pong-quilt #90** — CI red: build-and-test + merge-gate (flagged by
  superinstance-watch ~06:4x). Hypothesis: workflow/config break. Plan: `gh pr view 90
  --repo SuperInstance/pong-quilt` + failed-log tail → diff workflows vs last green →
  fix forward → merge.
- **quilt-fleet #16–20** (dependabot, five bumps) — CI fails in 15–50s each. That
  runtime profile = workflow parse error / missing secret / deprecated action version,
  NOT the bumped deps. Plan: diagnose ONE run's failed log; single fix-forward commit;
  re-run all five; batch-merge whatever is green.
- **Everything else** — unknown until the first `pr_sweep` run. The sweep is a
  first-exec-pass action, alongside pushing the staged experiment batch.

## Learnings log (the "enhance our own applications" half — append per PR)
| date | PR | what it did | stole/learned | plugs into |
|------|----|-------------|---------------|------------|
| — | — | *(format example: retry-with-jitter on webhook delivery)* | *backoff pattern* | *cron wake retries* |

Mine-grade steals (novel technique, not just a fix) also get a one-line referral to
the edge-mine spool so Wave scoring sees them.
