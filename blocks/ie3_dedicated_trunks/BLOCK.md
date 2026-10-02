# ie3_dedicated_trunks

## WHAT IT IS

The dedicated-trunk arm layout, proven in silicon: **specialists need
dedicated trunks** — a shared trunk with two heads loses to two small
dedicated nets even when specialization is sequential. This block makes
IE3's capacity competition legible in closed form: two signal families
mixed in one input (living in orthogonal subspaces — the toy skeleton of
IE1's grating-codes-vs-blob-codes split), three arm layouts on identical
data:

- `A_joint` — ONE shared trunk (hard rank-m bottleneck) + two linear
  heads, both tasks fit jointly (reduced-rank ridge regression).
- `B_sequential` — the same single trunk: task 1 to a competence plateau,
  then an anchored fine-tune on task 2 only; task-1 forgetting is
  measurable on the same held-out streams.
- `C_split` — two small DEDICATED trunks, one per task, each the same
  width as A's one trunk (crew budget: two cells, not two heads).

Mechanism: the shared trunk is a rank-m bottleneck. Two orthogonal rank-k
tasks need 2k total trunk rank; one width-k trunk splits it (~k/2 each →
dilution on both). Two dedicated width-k trunks each cover their task's k
→ no dilution. **The contract exported to composers is the ARM LAYOUT**
(how to wire shared vs dedicated capacity), not this dataset.

## WHY (the booked receipts)

- **IE3** (RESULTS.md, 2026-09-29) — `DILUTION_CONFIRMS`: A-joint and
  B-sequential shared-trunk arms dilute; C-split-trunks specialists hit
  r2_blob 0.987 / r2_direction 0.984 at density 32. Source harness
  (`experiments/ie3_specialist_trunks.py`): IE2 sensor stack verbatim,
  gradient-trained trunk (4→12→8 tanh, 164 params) + linear heads, 600
  trunk-epoch budget, frozen gates with precedence SPECIALIZATION_WINS →
  JOINT_OK → DILUTION_CONFIRMS. Crew doctrine: "each model = its own
  dedicated cell; routes cross BETWEEN cells, never multi-role one cell."
- **COMP0** (2026-10-01, lane COMPOSITE-0) — the doctrine's first
  federation probe: FED 0.8182 > SINGLE 0.7778 (+0.0404) and FED > JOINT
  (+0.0152) at matched params, all three directions held, verdict
  INCONCLUSIVE by the std==0 law (FED pinned at 0.8182 across seeds — a
  66-item granularity artifact). Dilution showed only in the contested
  regime (counting): SINGLE 0.66 vs FED 0.70 — semantic saturates for
  everyone.
- **COMP1** (2026-10-01, lane COMPOSITE-1) — the doctrine's booked win
  under real measurement (590-item held-out, item-level bootstrap): FED >
  SINGLE ONLY on negation-scope (+0.126, CI [0.034, 0.219] excludes 0)
  where BOTH monolith arms sit BELOW regime chance (0.423/0.428 vs 0.50)
  — polarity is word-order; a BoW shared trunk cannot see it; the
  dedicated cell keys on the local cue anyway. Elsewhere federation buys
  nothing. Cheap linear cells reproduce the win at 1/13 the params
  (RING-CX-2: +0.196 on negation with 325 logistic params, 0 GPU).

## INTERFACE

```python
make_dataset(seed, d)          # two orthogonal rank-k task maps + shared streams
arm_A_joint(data) -> {task: r2}                # shared trunk, joint fit
arm_B_sequential(data) -> {task: r2, switch_blob_r2}  # + forgetting read
arm_C_split(data) -> {task: r2}                # dedicated trunks (crew baseline)
run_grid(seed)                 # the 8/16/32 density grid, all three arms
```

Frozen config at module top (`SEED=2718`, `SEEDS` = 5 seeds, `DENSITIES`
(8,16,32), `DENSITY_OF_RECORD=32`, `SUBSPACE_K=4`, `TRUNK_WIDTH=4`,
`SIGMA=0.15`, `RIDGE_ALPHA=1e-3`, `ANCHOR_LAM=n_train`, `ORDER_MARGIN=0.02`).
Fail loud: non-finite r² or degenerate subspace construction raises.

## PROPERTIES

- ≥5 seeds with mean ± std; **any cross-seed std == 0 ⇒ INCONCLUSIVE,
  never PASS** (the frozen degeneracy law) — the self-test prints the
  per-arm/task std table and applies it.
- Ordering gate at the density of record: C_split beats A_joint AND
  B_sequential by > `ORDER_MARGIN` on at least one task; B's task-1
  forgetting is booked alongside (the sequential arm's dilution + drift).
- Deterministic (seed 2718 default; closed-form fits — no optimizer
  variance beyond the data draw).
- CPU-only, stdlib+numpy, seconds.

## COMPOSITION

- **The layout half of a federation lane**: pair with
  `d13d_correlation_keys` (the 0-parameter correlation router that decides
  WHICH dedicated cell sees an item — the COMP0/COMP1 wiring), and with
  `est_freeze_interface` when the cells' determinacy must be measured.
- Downstream doctrine (COMP0/COMP1): report **per-regime boards as
  primary** (full-board compresses saturation/floor effects); if the
  federation ceiling is its weakest cell, routing saturation is a free
  pass, not a result.

## SELF-TEST

From the lab root, CPU-only, seconds:

```
python3 blocks/ie3_dedicated_trunks/block.py
```

Runs the 3 arms × densities {8, 16, 32} × 5 seeds; prints the seed-2718
receipt table, B's switch competence and forgetting, and the mean±std
table; applies the ordering gate at density 32 and the std==0 degeneracy
law. Final stdout line is exactly one JSON object with one top-level
`"verdict"` (PASS/KILL/INCONCLUSIVE); exit 0 iff PASS. Current booked
shape: C−A ≈ +0.32 / C−B ≈ +1.1 r² on both tasks, forgetting ≈ 1.09 —
dilution and sequential forgetting both visible in closed form.
