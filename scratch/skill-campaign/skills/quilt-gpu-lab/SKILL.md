---
name: gpu-lab-law
description: Run honest GPU experiments on the fleet's 6GB RTX 4050 — pre-registration, frozen gates, guard.py watchdog, receipt-sealed ledgers, arms-as-fresh-processes. Use before ANY GPU run or when writing up results.
---

# quilt-gpu-lab — the experiment law

The standing ML loop on the fleet's RTX 4050 (6GB, WSL2) and the doctrine
every GPU run here follows. The queue is the agenda; the results are the
story; a verdict the ledger cannot re-derive is a claim, not a receipt.

## Running an experiment

1. **Pre-register FIRST** (pushed BEFORE the run fires): freeze the plan in
   `proposals/runs/<NAME>-prereg.md` — hypothesis, arms, gates, tolerances,
   known deviations. Frozen means frozen: post-hoc changes are ANNOTATED
   deviations, never edits.
2. **Claim** the first unchecked `QUEUE.md` item. Run under `guard.py`
   (refuses to start unless ≥1GB VRAM free and GPU ≤80°C; aborts on breach or
   30-min wall-clock). Cron claims one experiment per tick; no TTY.
3. **Book honestly**: append to `RESULTS.md` with verdict KEEP / KILL /
   INCONCLUSIVE / ABORTED — the ledger keeps ALL of them. std==0 ⇒
   INCONCLUSIVE, not success.
4. **Seal**: `python tools/receipt_manifest.py` → `receipts/manifest.json`
   (sha256 of RESULTS.md, QUEUE.md, experiments/*.py). Commit the seal WITH
   the change. `python -m unittest discover -s tests` re-derives everything.

## Hardware laws (paid for in crashes)

- **/tmp is tmpfs** — wiped on every crash/reboot (GSOD ×2 on 2026-10-02).
  Anything you want back lives under `/home`. Checkpoints, arm JSONs, logs.
- **One heavy-I/O lane at a time while the GPU trains.** Both 10-02 crashes
  correlated with GPU training + mass git clone/fetch concurrently.
- **Arms-as-fresh-processes**: each arm runs in its own process with its own
  out-json. A crash kills one arm, not the experiment — survivors stay valid
  for the same attempt; relaunch the dead arm solo, marker in the log,
  same frozen params.
- **GPU instrument ramp**: every measurement on this box ramps first (5-10s
  idle onset, ~4.5× slowdown by 20s idle); ≥0.3s sustained synced load
  restores ≥97%. Bench uses 0.6s warmup. No exceptions, ramp receipt in log.
- bitsandbytes NF4 train OOM → ENV fix first
  (`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`), harness change only
  as annotated deviation.

## Seal gotchas

- The seal REFUSES to run over dirty sealed paths (rc=2 `REFUSED`) — sealing
  uncommitted bytes is how the d23b phantom seal happened. `--allow-dirty`
  records an explicit `sealed_from_dirty_tree` admission instead.
- Convention-by-construction: fix the score sign in code; never import a
  scorer with implicit positive direction.
- One-clip decode round-trip before any batch run; checkpoint embeddings
  after extraction (metric bugs never lose GPU work).
- Keys at use-time from /mnt/c/Users/casey/key.txt; never echo; anthropic/*
  on metered providers is BANNED.

## Neighbors

i2i-ledger (book findings here) · superinstance-api (fleet recall) ·
git-agent (quilt_emit, the WAL shape the manifest dogfoods).
