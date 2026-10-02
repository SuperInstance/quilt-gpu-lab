# A2B-DBLTHREAT — pre-registration: designed double-threat boards (A2's booked fix)

- lane: **A2B-DBLTHREAT** (`quilt-gpu-lab`), the A2-HARVEST booked follow-up (worklist **A2**, fix #1)
- date frozen: **2026-10-01** — written **before** the measured training run of this lane
- device: **CPU only** (`torch` CPU tensors; no CUDA call is made) · **0 Wh by construction** · seed **2718**
- source of truth for arms: `results/a2_ga4444/` (disk is truth) — MLP 16→64→4 ReLU, LINEAR 16→4,
  Adam lr 1e-3, batch 1024, **120 epochs**, seed 2718, 5-fold board-disjoint CV (`(fnv1a64(board)>>32) mod 5`)
- source of truth for boards+labels: `results/a2_ga4444/dataset.jsonl` (66,297 our-turn non-terminal
  gravity boards, exact set-valued labels, `dataset_fnv1a64 = 0x98219e9d0dd0d382`)
- **not committed — keeper folds.**

## 0. The claim under test

A2 booked: the pre-registered composition-collapse contrast had **no executable positive instance** at
natural-walk sampling (COMPOSED-B chance **0.9696**), so its frozen gate was **INCONCLUSIVE** and the
linear arm showed **no** composition penalty (`Δ_linear = −0.1762`). A2's own follow-up §5.1:
**generate double-threat boards by design** — "the only design that makes COMPOSED-B's chance well below 1".

**Question:** does a *designed* double-threat set host the composition contrast
(nonlinear absorbs composition / linear penalised) that A2's natural sample could not host?

## 1. Recon (run downstream of A2, before any training number of this lane)

Recon scripts: `analyze_geom.py`, `analyze_opp.py`, `analyze_recon3.py` (this dir).

| finding | number |
|---|---|
| boards with **≥2 immediate winning threats** for the mover (A2's `imm_wins≥2`) | **763** (1.15% of 66,297) |
| of those, boards whose **chance = 1.000** (every legal move is optimal) | **675 / 763 = 88.4%** |
| boards with chance ∈ {0.50, 0.67} | **88** |
| **the discriminator**: chance < 1 ⟺ the **opponent also has ≥1 immediate win** | exact coincidence (88/88) |
| boards with ≥2 mover threats **and** ≥1 opponent threat | **196** |
| single-threat controls available at matched (ply, n_legal) | 13,762 total; matching **feasible** (§3) |

**Recon correction (recorded before any measured number).** The mission's literal rule ("≥2 immediate
winning threats", D, n=763) is **88.4% degenerate**: on those boards a uniformly-random legal move is
already optimal 95.3% of the time on average. The *executable* positive instances are the boards where
the mover is **also under threat** — that is the "must-convert-or-lose" double threat (a fork where any
non-winning move loses). Natural walk **does** produce them (88, and 196 with the weaker
opponent-threat flag), contrary to "never" — but at 0.13–0.30% of the corpus.

Also booked: under gravity each column has exactly one legal drop, so a **same-column ("stacked") pair of
immediate threats is impossible**; the gravity analogue of "stacked-column" is a pair of **vertical**
threat lines (two columns each one stone from a stack win), which occurs.

## 2. Construction rules (verbatim)

- **Threat / probe (verbatim):** for a board `x` with mover `m` and occupancy `occ`, enumerate every
  legal drop (gravity: lowest empty cell of a non-full column); a drop `c` is a **threat** iff placing
  `m` at `c` completes a 4-in-line for `m` **immediately** (exhaustive legal-move probe; no search).
  `n_threats(x)` = number of such columns; `n_opp_threats(x)` for the opponent likewise.
- **Stratification rule (verbatim, from the two winning threat cells `(r1,c1),(r2,c2)` and their
  completed line orientations):**
  - `stacked-column` — both threat lines are **vertical** (col/col);
  - `cross-quadrant` — not both vertical, and row-half differs **and** column-half differs
    (cells in diagonally opposite 2×2 quadrants);
  - `split-column` — everything else (two distinct threat columns, not diagonally opposite).
- **D (mission rule).** `{x : n_threats(x) ≥ 2}` over A2's 66,297 — **n = 763**.
  Strata: stacked-column 6 · split-column 623 · cross-quadrant 134.
- **D\* (designed set, primary).** `{x ∈ D : n_opp_threats(x) ≥ 1}` — **n = 196**.
  ("the mover has ≥2 wins and the opponent has ≥1: convert or lose"). Strata: stacked-col 6 · split-col 190 · cross-quad 0.
- **D\*\* (fully executable sub-set).** `{x ∈ D\* : chance(x) < 1}` — **n = 88**, chance ∈ {0.50, 0.67}.
- **S (matched single-threat controls).** `{x : n_threats(x) = 1}` over the same corpus, greedily
  pair-matched to D\* on **(ply, n_legal, opp-threat flag)** — equal stone count, equal `|empty|`,
  equal legal-move count — without replacement, seeded 2718.
- **Target note (fail loud).** The mission target 200–500 items is met by D (763, complete class, not
  sampled) and by D\* (196, effectively at target); it is **not reachable** for D\*\* (88): the
  complete gravity graph contains exactly 88 such our-turn positions, and no sampling can exceed a
  complete class. Booked, not hidden.

## 3. Arms (A2's exact arms, booked checkpoints — read from `results/a2_ga4444/`)

- `MLP` = `Linear(16,64) → ReLU → Linear(64,4)` · `LINEAR` = `Linear(16,4)` · Adam lr 1e-3, batch 1024,
  **120 epochs**, set-valued loss `−log Σ_{m∈Opt} masked_softmax(z)_m`, seed 2718, 5-fold board-disjoint CV.
- **PRIMARY arms `MLP-full` / `LIN-full`:** trained on the whole 66,297 corpus (A2's booked configuration),
  evaluated **out-of-fold** on: the **D\* partitions** (composed), their **matched S siblings** (single),
  D, D\*\*, and the full original eval (**continuity check**).
- **SECONDARY arms `MLP-DESIGN` / `LIN-DESIGN`:** identical config trained only on `D* ∪ S` (196+196),
  out-of-fold evaluation on the same D\*/S partitions.
- **TERTIARY task-only siblings** `MLP-D*`, `MLP-S`, `LIN-D*`, `LIN-S`: trained on one partition only.

## 4. FROZEN GATES (no goalpost migration)

Let `C_a(P)` = arm `a`'s out-of-fold top-1 accuracy on partition `P` (`1[pred ∈ Opt(board)]`), and
`chance(P) = mean_board(|Opt| / n_legal)`. Per matched pair `i` (D\* board ↔ S board):
`d_i = (C_MLP(D*_i) − C_MLP(S_i)) − (C_LIN(D*_i) − C_LIN(S_i))`, `S̄ = mean_i d_i`.
Bootstrap: **B = 2000 resamples of pairs, seed 2718**, percentile 95% CI.

| gate | condition |
|---|---|
| **G-A2b1 (composition penalty EXISTS on the designed set)** — PASS iff | `S̄ > 0.05` **AND** the paired-bootstrap 95% CI **excludes 0** |
| **G-A2b2 (the set has signal)** — PASS iff | on the designed set, `∃` arm with `C_a(D*) − chance(D*) ≥ 0.05` **and** its board-level bootstrap CI excludes 0 |
| **INCONCLUSIVE** | `std == 0` on any gate column, a NOT-RUN, or any gate unmet |
| **second strike** | if G-A2b2 fails on **D\*** (and on D and D\*\*), the *composition-collapse construct* takes its second strike — booked as the finding |

Reported alongside (secondary, A1's direction so both readings are visible):
`Δ_a = C_a(D*) − C_a(S)` and the differential `Δ_LIN − Δ_MLP` (A1: linear collapses, MLP absorbs).
Stated in advance: **either verdict is a result.** Both are booked with the computed floor for scale.

## 5. Controls

- **Continuity check:** `MLP-full` / `LIN-full` on the full original eval must reproduce A2's booked
  numbers (0.9712 ± 0.0036 / 0.8130 ± 0.0021 overall) within ±0.02 — CPU re-run of the booked config.
- **Solver ground truth (rule 5, different path):** a 100-board sample of the designed corpus is
  re-solved by the repo's independent C solver `gt4444 --probe` (list-form subprocess, never `shell=True`);
  must agree 100/100. Designed/label numbers are the exact labels in the A2 dataset.
- seed 2718 · fail loud · `std == 0 → INCONCLUSIVE` · no commit · other lanes' lines untouched.
- **Energy:** CPU-only, no CUDA call → **0 Wh**; no G7 receipt is issued for a 0 J run (recorded as such).
