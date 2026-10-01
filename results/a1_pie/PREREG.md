# A1-PIE — pre-registration: does a nonlinear local rule close the minimax gap?

- lane: A1-PIE (`quilt-gpu-lab`, worklist item A1, `fleet-triage/docs/RTX4050-WORKLIST.md`)
- date frozen: 2026-10-01 (written **before** any training run in this lane)
- seed: **2718** (pinned everywhere: split, init, shuffles, vram guard)
- device: `cuda:0` (RTX 4050 Laptop, 6 GB) — `guard.py` gated, receipt or VOID
- reference clone: `~/projects/pie-minimax` (**read-only**; numbers recomputed here, not inherited)
- **not committed — keeper folds. NOT appended to RESULTS.md (parallel lanes live).**

## 0. The claim under test (their pre-registered prediction)

`pie-minimax` measured a **linear** map board→scores (9→9, 81 params) at top-1 `0.1807`
vs a random floor `0.1431`, and predicted:

> optimal play is a minimax over a tree; a linear map is a *sum of independent per-cell
> votes*, which cannot represent a *count* over separate lines. Therefore nonlinearity
> closes the gap only **a little** — **0.25–0.40 top-1** — and **collapses on the
> ≥2-simultaneous-win ("COMPOSED") partition**, because "local voting can't count threats".

THIS LANE TESTS THAT PREDICTION on a small MLP, under frozen gates (§6).

## 1. Dataset — and a correction to the correction

`minmax.enumerate_reachable()` returns **180,361 rows** of `(board, optimal_set)`. Those
rows are **path-weighted**: the walk visits each board once per move-order that reaches it,
so the same board recurs ~75×. There are only **2,423 distinct boards with us to move**.

- 180,361 = path rows (**with duplicates**), 2,423 = distinct boards.
- The repo's README "CORRECTION" asserts 180,361 is *impossible* because `3⁹ = 19,683`.
  That is itself a miscorrection: it misreads a path-row count as a distinct-state count.
  `enumerate_reachable()` is verified here: `len(...) == 180361`, `len(set(boards)) == 2423`.
- Both counts are recorded with every number below. Nothing is asserted without recompute.

Labels are **exact and set-valued** (`M[r,m]=1 ⇔ m ∈ optimal(board)`), no annotation noise.
Loss is their set-valued loss: `L = -log Σ_{m∈Opt} softmax(z)_m`.

**Partition (the pre-registered contrast).** For an us-to-move board `b`:
`immediate_wins(b) = {m empty : winner(play(b,m)) == 1}` (a single move that wins *now*).
- `COMPOSED` ⇔ `len(immediate_wins) >= 2` (two simultaneous wins — needs a *count*).
- `SIMPLE`   ⇔ `len(immediate_wins) <= 1` (one local term can express it).
Cross-checked against the repo's `ceiling2.is_simple` (`threat_count(b,1) <= 1`).
**They are NOT equivalent** (found here): "≥2 simultaneous *winning moves*" = **320** boards;
"≥2 *lines* one stone from completing" = **1230** boards; they agree on 1513/2423. Both
partitions are reported for every arm; the frozen gate uses the task's wording
(≥2 simultaneous **wins**, `immediate_wins`), with the repo's `threat_count` partition
reported alongside so no reader is misled by the choice.

## 2. Splits (recorded, because the choice moves the number)

- **PRIMARY — board-disjoint 90/10, FNV-1a-64 split (chosen; recorded per brief).**
  Bucket `= (fnv1a64(board_bytes) >> 32) mod 10`; bucket 0 → test (10%), else train.
  Board-disjoint, so **no duplicate-board leak**. This is the only split that measures
  *generalisation*; the record's own QG1d recon documents how a leaky split inflated a
  64-bit hash to 0.9586 vs 0.5045 honest.
  *Instrument note (found before any training):* the naive `fnv1a64(...) mod 10` was tried
  first and produced **an empty test set** — FNV-1a-64 low bits are weak, every 3×3 board
  hashes ODD, so `mod 10` only ever hits `{1,3,5,7,9}`. The first attempt was **VOIDed**
  (`g7-wr-a1-pie-closure-1790891323.json`) before any model trained; the fix uses the
  high 32 bits (validated bucket counts 217–261 over 2,423 boards).
- **SECONDARY (parity, declared-leaky) — the repo's `sweep.py` convention:** resample
  20,000 train / 8,000 test rows *with replacement* from the 180,361-row path corpus
  (`random.Random(2718)`). Each training board appears in both arms (≈75 copies/board) →
  this number is a *memorisation* reading, reported only for parity with their 0.1807.
- **VARIANCE (rule 2).** 5-fold board-disjoint CV (FNV-1a-64 mod 5), std across **data
  folds** (not seeds — the repo showed seed-variance is exactly 0). `std == 0` → INCONCLUSIVE.

## 3. Models

- **MLP (under test):** `9 → 64 → 9`, one hidden ReLU. `1225` params. Adam, `lr=1e-3`,
  batch `1024`, **20 epochs max**, seed 2718. (Exact brief spec — frozen as PRIMARY.)
- **LINEAR baseline (matched):** the *same* harness with `hidden=0` (`9→9`, 81 params),
  identical optimiser/split/epochs — recomputed here, **not** read from README.
- **LINEAR expert (parity):** `linear_expert.train` (their original: set-valued loss,
  300 steps, lr 0.5) evaluated on the same test boards.
- **FLOOR / chance:** uniform random empty cell; chance = `mean(|opt|/|empty|)`.
- **CONVERGENCE CONTROL (declared, secondary — so the answer is not a statement about the
  optimiser).** Identical MLP + split + seed, `lr=1e-3` run to **plateau** (≤400 epochs,
  stop when train loss < 1e-5 or 200 epochs without improvement). The repo's own lesson:
  a result that flips with learning rate "is a measurement of my optimiser, not of
  capacity". If PRIMARY and CONTROL disagree, the CONTROL number is the honest one and the
  PRIMARY is booked as an underfit artefact — recorded either way.

## 4. Metrics

`top-1` = the model's `argmax` cell is in the exact optimal set (their `evaluate`). Reported:
overall, on COMPOSED, on SIMPLE, per arm; plus chance and floor on the same boards; plus
`Δ_partition = top1_SIMPLE − top1_COMPOSED` and `Δ(MLP−LINEAR)` on each partition.

## 5. Energy / receipt

Run under `guard.Guard(task_id="A1-pie-closure", receipt_dir="results/a1_pie")`:
`preflight()` → `run()` → `emit_receipt()`. Preflight refusal → wait 90 s, retry **once**,
else **NOT-RUN**. INSTRUMENT-01: ≥0.6 s sustained synced CUDA ramp before any timing,
ramp receipt recorded. G7 rule: **no receipt → run VOID**.

## 6. FROZEN GATES (no goalpost migration — applied to the PRIMARY board-disjoint number)

| verdict | condition |
|---|---|
| **KILL-of-prediction** | MLP top-1 **overall > 0.40** (closure too good — their "closes only a little" is false) |
| **CONFIRM** | MLP top-1 **overall ∈ [0.25, 0.40]** **AND** MLP top-1 on COMPOSED **<** LINEAR top-1 on COMPOSED (same test boards) |
| **INCONCLUSIVE** | anything else (incl. std == 0, or a NOT-RUN / VOID) |

Stated in advance: **either verdict is a result.** KILL = a surprise finding (a small
nonlinear net absorbs minimax composition); CONFIRM = the "voting can't count threats"
mechanism carries. Both are booked honestly, with the ceiling (`decision tree 0.7879`,
exact solver `1.0000`) for scale.

## 7. House laws honoured

seed 2718 · fail loud · receipt or VOID · artifacts (<5 MB weights, metrics json, this
prereg) in `results/a1_pie/` · **no `RESULTS.md` append** · **no commit** · pie-minimax
clone read-only · O(chunk) memory (2,423 boards) · no shell-string subprocess (list-form
`guard.run([...])` only).
