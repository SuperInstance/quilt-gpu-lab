# exact_minimax_labels

## WHAT IT DOES

Exact, set-valued ground truth for game states: a standalone memoized NxN
tic-tac-toe minimax solver that emits, for every reachable OUR-TO-MOVE board,
the FULL SET of optimal moves M(b) = {m : m achieves the memoized full-depth
minimax value} — never a single tie-broken choice. The set-valued contract is
the whole point (the reference repo's own documented defect: tie-broken
single-move labels poisoned its decision-tree ceiling by relabelling
equally-correct moves as mistakes).

Harvested from the A1-PIE lane (`results/a1_pie/a1_pie_closure.py`,
2026-10-01), itself a clone of the read-only reference
`~/projects/pie-minimax/minmax.py`. Two booked recon corrections travel with
the block as laws:

1. **Path rows ≠ distinct states.** The full walk from the empty board
   re-emits a board once per move order that reaches it: 3x3 gives
   **180,361 path rows but only 2,423 distinct boards**. Both counts are
   reported, always. (The reference README's "180,361 is impossible, 3^9 =
   19,683" correction was itself a miscorrection — it misread a path-row
   count as a distinct-state count.)
2. **"COMPOSED" is two non-equivalent partitions.** ≥2 immediate winning
   moves (task wording; 320 boards) vs ≥2 threat lines (repo `ceiling2`
   convention; 1,230 boards); they agree on 1,513/2,423. Both are exposed;
   any downstream claim must name which partition it means.

Also baked in: the FNV-1a-64 parity lesson from A1's VOID-of-record — every
our-to-move board hashes ODD under raw `fnv1a64(board_bytes)` (stone bytes
{0xFF, 0, 1} and even stone count), so `% 10` splits produce an EMPTY even
bucket. `to_key()` renders boards into chars with the same parity structure
('!'/'#' odd, '.' even), and the docstring spells out the exact recipe
(high-32 bits) that fixes it.

Board encoding: tuple of n*n ints in {-1, 0, +1} (-1 = opponent, 0 = empty,
+1 = ours), flattened row-major. Values: +1 we win with perfect play, 0 draw,
-1 we lose. Learner loss shape from the receipt:
`L = -log sum_{m in Opt(b)} softmax(z)_m`.

Environment: python 3.14, stdlib only. No torch, no GPU, no subprocess.
n=3 solves in ~1 s; n=4 is supported but much larger.

## INTERFACE

- **`solve(n=3) -> LabelSet`** — solve the NxN game from the empty board,
  memoized per n. This is the entry point.
- **`labels(board, n=None) -> set[int]`** — module-level convenience: optimal
  move set for one our-to-move board (infers n from len(board); non-square
  length fails loud).
- **`LabelSet`** (immutable after construction):
  - counts: `n_path_rows`, `n_distinct_boards` (report both — law 1);
  - `boards() -> list[board]`, `rows() -> iter (board, frozenset[optimal])`
    over DISTINCT boards, `path_row_iter()` over all move-order duplicates;
  - `labels(board) -> set[int]`, `board_value(board) -> int` (value with us
    to move; wrong-length board raises);
  - partitions: `immediate_wins(board)`, `threat_count(board, player=1)`,
    `is_composed_imm(board)` (≥2 immediate wins), `is_composed_thr(board)`
    (≥2 threat lines) — law 2, both definitions;
  - baselines: `chance(boards=None)` = mean(|optimal|/|empty|) (PREREG §3
    chance definition), `floor_random_empty(seed=2718, draws=8)` = measured
    random-empty-cell floor (expectation == chance);
  - `stats() -> dict` — the whole receipt bundle in one JSON-serializable
    dict (counts, both partitions, agreement, chance, floor).
- **`ExactMinimax(n)`** — the raw solver (n < 2 fails loud):
  `winner(board)`, `empties(board)`, `play(board, mv, stone)`,
  `value(board, turn)` (lru_cached), `optimal(board) -> tuple` (() if
  terminal/full), `enumerate_reachable(max_plies=None)`.
- **`to_key(board) -> str`** — stable string key with the FNV-parity
  structure of the receipt's raw board_bytes, feedable to
  blocks/board_disjoint_cv (high-32 scheme). The docstring gives the exact
  recipe to reproduce the receipt's literal bucket counts.

**House contracts baked in:** seed 2718 default (pinned in
results/a1_pie/PREREG.md) · fail loud (assert/exception, no silent
degenerate output) · single JSON verdict line on the self-test's final
stdout · stdlib-only · CPU-only · no subprocess · never prints secrets.

## THE RECEIPT

- Cite: **RESULTS.md A1-PIE entry (2026-10-01)** (lines 4105–4220); full
  entry `results/a1_pie/RESULTS-ENTRY.md`; pre-registration
  `results/a1_pie/PREREG.md` (written before training); code
  `results/a1_pie/a1_pie_closure.py`; all numbers
  `results/a1_pie/a1_pie_metrics.json`.
- **Corpus counts (re-proven by this block's self-test, 2026-10-01):**
  180,361 path rows / 2,423 distinct our-to-move boards; composed-imm 320,
  composed-thr 1,230, agreement 1,513; universe chance 0.5865 (matches the
  metrics artifact digit-for-digit; test-set chance 0.5566).
- **What the labels bought in A1-PIE (the KILL-of-prediction):** a
  1,225-param ReLU net (9→64→9, purely local board→scores, no search) trained
  on these set-valued labels reaches **0.9494 board-disjoint top-1**
  (5-fold CV 0.9392 ± 0.0094) with **composed 0.9643** — nonlinearity does
  NOT collapse on the ≥2-win COMPOSED partition; the reference repo's
  "local voting can't count threats" prediction is falsified, while the
  linear half survives (linear arms collapse 0.14–0.36 on COMPOSED).
- **The 20-epoch frozen PRIMARY gate is INCONCLUSIVE (0.3502 inside the
  predicted [0.25, 0.40])** — a 60-step budget measures the optimiser, not
  capacity; the pre-registered plateau control supplies the honest number.
  That transferable lesson (always run a convergence control) is why the
  solver here is exact and memoized rather than budget-limited.
- **Instrument bug → law 2 of the block:** the first split used raw
  `fnv1a64(board) % 10`, which returned an EMPTY test set (every 3x3
  our-to-move board hashes odd). That attempt was VOIDed before any number
  existed (`results/a1_pie/g7-wr-a1-pie-closure-1790891323.json`, kept
  deliberately as the VOID-of-record); fixed to FNV-1a-64 HIGH-32 bits
  (validated bucket counts 217–261 over 2,423 boards).
- Empty-board fact (verified against the reference): value = 0 (draw) and
  ALL 9 opening moves are optimal — the "center + corners" folk guess is
  wrong under exact minimax.

## COMPOSITION

- **Upstream of any learner lane:** `rows()` yields (board, optimal_set)
  pairs ready for set-valued training (`-log Σ_{m∈Opt} softmax(z)_m`); the
  receipt's chance/floor baselines make headroom arithmetic one-liners.
- **Feeds blocks/board_disjoint_cv:** `to_key(board)` (same FNV parity
  structure) or the raw-bytes recipe in its docstring, under the high-32
  scheme — the split that does not void itself on FNV low-bit parity.
- **Ground truth for judgment lanes:** `labels(board)` is the exact oracle a
  format_first_gate-style judge is scored against (e.g. mean_agreement over
  "is move m optimal?" questions); `stats()` books the corpus numbers a
  receipt needs (both partitions named — law 2).
- **Feeds ternary_transition_kernel-style perception:** board tuples are
  already in {-1, 0, +1}, the ternary codec's alphabet; a perception lane
  can ternary-encode continuous state and score against these exact labels.
- Contracts the consumer must honor: keep labels SET-VALUED (never
  tie-break); report path rows AND distinct boards; name the partition
  (imm vs thr) in any COMPOSED claim; never split on raw FNV low bits.

## SELF-TEST

Command (from the lab root, CPU-only, ~0.9 s):

```
python3 blocks/exact_minimax_labels/block.py
```

Checks (all fail loud on drift):

1. **Full 3x3 enumeration re-proves the booked receipt counts**: path rows
   180,361 / distinct 2,423 / composed-imm 320 / composed-thr 1,230 /
   agreement 1,513 — assert-equal against the RESULTS.md numbers.
2. **Empty board**: value 0 (draw) and optimal set = all 9 moves (the
   "center + corners" guess refuted, from the reference solver).
3. **Independent memo-free brute force** on a seed-2718 random sample of 64
   distinct boards + the empty board (65 total): plain recursion sharing no
   state with the memoized solver agrees on every optimal set.
4. **Baselines**: chance in (0.5, 0.6) (measured 0.5865 = the artifact's
   universe chance); floor_random_empty within 0.02 of chance (0.5908).
5. **Iterator/count coherence**: rows() == n_distinct_boards,
   path_row_iter() == n_path_rows, boards really distinct, every label set
   non-empty.

Recorded output (2026-10-01, python 3.14, 0.83 s):

```
counts OK: path_rows=180361 distinct=2423 comp_imm=320 comp_thr=1230 agree=1513
empty board OK: value=0 (draw), optimal = all 9 moves (every opening move draws — 'center + corners' guess refuted)
brute-force cross-check OK: 65 boards agree (memo-free independent recursion)
baselines OK: chance=0.5865 (universe, receipt 0.5865; test-set 0.5566), floor_random_empty=0.5908 (expectation == chance)
{"verdict": "PASS"}
```

Expected verdict: **PASS**, final stdout line exactly `{"verdict": "PASS"}`,
exit 0.
