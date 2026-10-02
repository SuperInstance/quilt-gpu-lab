# The Farm — always at capacity, kept fruitful

*Casey, 09-30 21:06: "you could have a farm that's always at capacity and your job is to
keep it fruitful instead of just firing it up when experiments are run. we could always be
growing if the architecture for the work-flow was right."*

## The shape

- **`farm_runner.mjs`** — the keeper loop (60s tick): GPU free? → fire the next queued
  experiment whose **pre-reg is committed**. Nothing big ready? → run a **filler**
  (dataset builds, evals, renders). Never two at once; single-instance lock.
- **`queue.json`** — the standing queue. `experiments` need a `prereg` path; the runner
  checks the pre-reg is actually committed in git history before firing. **The doctrine
  is a gate in the code**: push-before-fire isn't a convention here, it's the scheduler.
  `fillers` have cooldowns and keep the farm fruitful between experiments.
- **`RECEIPTS.md`** — append-only: every FIRE / DONE / EXIT / ADOPT / FILLER line.
- **`state.json`** — machine-readable snapshot (running, queue, blocked-needs-prereg) for
  the workbench to render.
- **`logs/<id>.log`** — full stdout/stderr per run.

## Fruitfulness (what "growing" means here)

The farm grows four things as byproducts, never idle:
1. **Verdicts** — experiments per day, each KEEP/KILL/INCONCLUSIVE booked honestly.
2. **Corpus** — filler pair-extraction grows the (ascii, frame) dataset from every video
   on the box.
3. **Images** — a render from the other side daily, even when nothing is training.
4. **Ledger** — receipts stream into the fabric; `op.mjs since farm` gives any engine the
   delta ("everything since the last read by my engine").

## Rules

- Experiments ONLY fire with a committed pre-reg (frozen hypotheses, honest branches).
- Verdicts are booked in RESULTS.md, never re-rolled.
- The keeper keeps the card warm but does not invent experiments — a queued entry without
  a pre-reg sits visibly BLOCKED in state.json until someone (me, on Casey's word) writes
  and pushes the pre-reg.
- Dev deployment: tmux window `canvas-ctl:farm`; graduates to systemd
  (`Restart=always`, `MemoryMax`) when it earns it.
