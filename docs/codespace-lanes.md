# Codespace Lanes — ephemeral agent bodies

**Status:** design + feasibility receipt, 2026-09-29 (Casey's idea, 18:22 AKDT).
**One-line:** any agent with a GitHub PAT can fire up a Codespace, run a quick
job, and put it away — a rented body per task, for the kinds of multi-agent
work our permanent boxes are wrong for.

## Why this fills a real hole

Our lanes today:

| Lane | Shape | Good at |
|---|---|---|
| Local RTX 4050 (WSL) | one box, 6 GB VRAM | GPU work, sleep-less iteration |
| z.ai / DeepSeek subagents | token work | thinking, writing, review |
| Cloudflare Workers | always-on edge | tiny, fast, global reflexes |

Missing: **burst CPU capacity** — builds, test matrices, multi-repo refactors,
dataset prep, doc pipelines, long deterministic jobs. That is exactly what
Codespaces sells: a disposable dev container with a real toolchain, attached to
a repo you already trust. Same opcodes on every boat — but this boat is rented
by the minute and scuttled after the trip.

## The economics ARE the design (this is the whole trick)

Verified 2026-09-29 (GitHub docs):

- Free personal tier: **120 core-hours/month + 15 GB-month storage**
  (Pro: 180 core-hours + 20 GB). Past that it bills — and with no payment
  method on file, usage is simply blocked.
- 2-core machine = **2 core-hours per wall hour** → ~60 wall hours/month free.
  A 10-minute 2-core job ≈ 0.33 core-hours → **~350 jobs/month free**.
- **Storage is billed while the codespace EXISTS, not while it runs.** The
  default 32 GB is larger than the entire free 15 GB-month allowance.

⇒ Stopping a codespace saves nothing. Leaving one up for two weeks eats the
month's storage by itself. "Put it away" therefore has to be **mechanical**:
create with a short `idle_timeout` and an explicit `retention_period`, and
`delete` (never `stop`) in a `finally`. Orphan sweep = a reaper job.

## Credential / security model

- Classic PAT needs the **`codespace`** scope (fine-grained tokens don't cover
  Codespaces yet): `gh auth refresh -h github.com -s codespace`.
- Prefer a **per-agent PAT** with minimal repo access; inject job secrets as
  Codespaces secrets (user/repo/org), never into the repo or the container's
  git config.
- No inbound network by default; ports must be forwarded explicitly — a good
  default for a fleet of autonomous agents.
- **No GPUs.** CPU jobs only. GPU work stays on the 4050 (or rented silicon).

## The pattern (same shape as every other lane we run)

```
ledger claim → create/start → sync brief → exec → collect artifacts → receipt → DELETE
```

- **Claim**: book the job to the fleet ledger (`books_to: codespace:<slug>`).
  Our coordinator-free locking already works this way — two agents cannot
  claim the same gist twice.
- **Body**: a template repo with `.devcontainer/devcontainer.json` pinning the
  fleet toolchain (python3, node, wrangler, gh, our scripts) plus a
  `postCreateCommand`.
- **Brief**: the job text + a pre-registered gate, carried in the ledger entry
  or a file in the repo.
- **Exec**: `gh codespace ssh -c NAME -- <cmd>`.
- **Receipt**: same fail-loud JSON receipt discipline as local runs (receipt
  written even when the job dies, verdict booked either way).
- **Put away**: `delete` in `finally`; a sweep (`gh codespace list` → delete
  anything older than `retention_period`) for agents that crashed mid-job.

## Prebuilds are the pinch

A prebuilt devcontainer is the **pinch layer for infrastructure**: a known job
shape starts in seconds (prebuild) instead of minutes (cold build). Unknown
shapes pay full cold-start once and are then compiled back into a prebuild.
Same reflex doctrine as the model side — known answers pinch off, unknown ones
escalate and compile back.

## Fits / doesn't fit

- **Fits**: CI-like jobs, multi-repo work, builds/tests/typecheck, dataset prep,
  doc pipelines, long CPU experiments, "this agent needs a real machine for
  ten minutes".
- **Doesn't fit**: GPU training, latency-sensitive paths, always-on services
  (Cloudflare Workers), high-volume token generation (z.ai lanes).

## Minimal PoC (three phases)

1. **Template** — `SuperInstance/codespace-lane`: devcontainer + `postCreate.sh`
   + `run-lane.sh` (reads `JOB.md`, runs it, writes `receipt.json`, pushes
   artifacts, self-deletes).
2. **Driver** — `tools/codespace_lane.sh` in this lab:
   `create → wait ready → exec → fetch receipt → delete`, forcing
   `idle_timeout` / `retention_period` and enforcing `--max-core-hours`.
3. **Falsifiable test** — fire 3 trivial lanes in parallel from 3 different
   PATs. Assert: 3 receipts land in the ledger, total spend < 1 core-hour, and
   `gh codespace list` is **EMPTY** afterwards. If anything survives, the
   "put away" contract is false and the pattern is not ready.

## Verified blocker (2026-09-29)

Local `gh` (2.46.0) holds an invalid token and lacks the `codespace` scope:
`gh codespace list` → 403 "This API operation needs the 'codespace' scope".
Fix: `gh auth refresh -h github.com -s codespace`, or a PAT carrying
`codespace`. Also confirm Codespaces is enabled for the org (org-owned
codespaces are billed to the org and must be allowed).

## Open questions

- **Org-owned vs user-owned**: org codespaces bill the org; user ones spend the
  personal quota. "Any agent" probably means member agents with their own PATs —
  needs a decision on whose quota is the fleet's.
- **Yard repo per project, or one generic lane repo that mounts the target?**
  The latter is more grabbable; the former gives better prebuilds.
- **Retention ceiling** is 30 days; a crashed agent's body should expire in
  hours, not days — requires the reaper, since `retention_period` is a floor
  for our purposes, not a guarantee.
- **Storage as a currency**: if a job's artifacts are large, pushing them to
  the repo (history cost) vs an R2 bucket (cheap, already ours) vs artifacts.
