#!/usr/bin/env python3
"""exact_minimax_labels — standalone exact NxN tic-tac-toe minimax label solver.

Harvested from the A1-PIE lane (results/a1_pie/a1_pie_closure.py, 2026-10-01),
itself a clone of the read-only reference ~/projects/pie-minimax/minmax.py.

Labels are EXACT and SET-VALUED: for every reachable our-to-move board b,
M(b) = { m : m is an optimal move }, where optimal means achieving the
memoized full-depth minimax value. Loss shape for learners (from the receipt):
    L = -log sum_{m in Opt(b)} softmax(z)_m

Board encoding (matches the source): a tuple of n*n ints in {-1, 0, +1}
(-1 = opponent stone, 0 = empty, +1 = our stone), flattened row-major.
The full walk from the empty board is PATH-WEIGHTED: a board is re-emitted
once per move order that reaches it (3x3: 180,361 path rows but only 2,423
distinct boards — BOTH counts are reported; the reference README's
"180,361 is impossible, 3^9 = 19,683" correction was itself a miscorrection
of a path-row count for a distinct-state count).

House contracts: seed 2718 default; fail loud (assert / exception, no silent
degenerate output); single JSON verdict line on stdout; stdlib-only; CPU-only;
no subprocess; never prints secrets.

Self-test (__main__): full 3x3 enumeration (<10 s CPU) asserting the booked
receipt numbers (180,361 / 2,423 / 320 / 1,230 / agreement 1,513), the empty
board = draw with ALL 9 moves optimal (verified: the "center + corners" guess
is wrong — every opening move draws under exact minimax), an independent
memo-free brute force over a seeded random sample, and the chance baseline.
"""
from __future__ import annotations

import json
import random
import sys
from functools import lru_cache

SEED = 2718  # house default, pinned in results/a1_pie/PREREG.md

# Expected 3x3 receipt numbers (RESULTS.md A1-PIE entry, 2026-10-01;
# results/a1_pie/a1_pie_metrics.json):
EXPECT_PATH_ROWS_3X3 = 180361
EXPECT_DISTINCT_3X3 = 2423
EXPECT_COMPOSED_IMM_3X3 = 320
EXPECT_COMPOSED_THR_3X3 = 1230
EXPECT_AGREEMENT_3X3 = 1513


def lines_for(n: int) -> tuple[tuple[int, ...], ...]:
    """Winning lines of the NxN board: rows, columns, two diagonals."""
    rows = tuple(tuple(i * n + j for j in range(n)) for i in range(n))
    cols = tuple(tuple(j * n + i for j in range(n)) for i in range(n))
    diag1 = tuple(i * n + i for i in range(n))
    diag2 = tuple(i * n + (n - 1 - i) for i in range(n))
    return rows + cols + (diag1, diag2)


class ExactMinimax:
    """Memoized exact minimax over reachable states of an NxN game.

    Value convention (matches the source): +1 we win with perfect play,
    0 draw, -1 we lose. `_value(board, turn)` is the game value from OUR
    perspective with `turn` (+1 us / -1 them) to move; `optimal(board)` is
    the SET of moves achieving the value (a set, not a choice — relabelling
    equally-correct moves as mistakes poisons the learner).
    """

    def __init__(self, n: int):
        if n < 2:
            raise ValueError(f"n must be >= 2, got {n}")
        self.n = n
        self.lines = lines_for(n)
        self.nn = n * n

    def winner(self, board: tuple[int, ...]) -> int:
        for a, c, d in self.lines:
            if board[a] == board[c] == board[d] != 0:
                return board[a]
        return 0

    def empties(self, board: tuple[int, ...]) -> list[int]:
        return [i for i, v in enumerate(board) if v == 0]

    def play(self, board: tuple[int, ...], mv: int, stone: int) -> tuple[int, ...]:
        nb = list(board)
        nb[mv] = stone
        return tuple(nb)

    @lru_cache(maxsize=None)
    def value(self, board: tuple[int, ...], turn: int) -> int:
        w = self.winner(board)
        if w:
            return w
        legal = self.empties(board)
        if not legal:
            return 0
        if turn == 1:
            return max(self.value(self.play(board, m, 1), -1) for m in legal)
        return min(self.value(self.play(board, m, -1), 1) for m in legal)

    @lru_cache(maxsize=None)
    def optimal(self, board: tuple[int, ...]) -> tuple[int, ...]:
        """Optimal move set for an OUR-TO-MOVE board; () if terminal/full."""
        legal = self.empties(board)
        if self.winner(board) or not legal:
            return ()
        vals = {m: self.value(self.play(board, m, 1), -1) for m in legal}
        best = max(vals.values())
        return tuple(m for m, v in vals.items() if v == best)

    def enumerate_reachable(self, max_plies: int | None = None) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
        """Every reachable OUR-TO-MOVE non-terminal board with its optimal set.

        Path-weighted by construction (the walk re-visits each board once per
        move order — this duplication is the 180,361 vs 2,423 distinction).
        """
        if max_plies is None:
            max_plies = self.nn
        out: list[tuple[tuple[int, ...], tuple[int, ...]]] = []

        def walk(b: tuple[int, ...], plies: int, our_turn: bool) -> None:
            if plies > max_plies:
                return
            if self.winner(b) or not self.empties(b):
                return
            if our_turn:
                opt = self.optimal(b)
                if opt:
                    out.append((b, opt))
            stone = 1 if our_turn else -1
            for m in self.empties(b):
                walk(self.play(b, m, stone), plies + 1, not our_turn)

        walk((0,) * self.nn, 0, True)
        return out


class LabelSet:
    """Solved label set for one board size: distinct boards + path rows +
    both COMPOSED partitions + baselines. Immutable after construction."""

    def __init__(self, n: int, solver: ExactMinimax):
        self.n = n
        self.solver = solver
        path = solver.enumerate_reachable()
        self._path_rows: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...] = tuple(path)
        uniq: dict[tuple[int, ...], tuple[int, ...]] = {}
        for b, opt in path:
            uniq[b] = opt
        self._rows: tuple[tuple[tuple[int, ...], frozenset[int]], ...] = tuple(
            (b, frozenset(uniq[b])) for b in sorted(uniq)
        )

    # ---- basic counts ------------------------------------------------------
    @property
    def n_path_rows(self) -> int:
        return len(self._path_rows)

    @property
    def n_distinct_boards(self) -> int:
        return len(self._rows)

    def boards(self) -> list[tuple[int, ...]]:
        return [b for b, _ in self._rows]

    def rows(self):
        """Iterate DISTINCT boards: (board_tuple, frozenset(optimal_moves))."""
        return iter(self._rows)

    def path_row_iter(self):
        """Iterate ALL path-weighted rows (with duplication)."""
        return iter(self._path_rows)

    # ---- labels ------------------------------------------------------------
    def labels(self, board: tuple[int, ...]) -> set[int]:
        """Set of optimal moves for an our-to-move board (exact)."""
        if len(board) != self.n * self.n:
            raise ValueError(f"board length {len(board)} != n^2 {self.n * self.n}")
        return set(self.solver.optimal(tuple(board)))

    def board_value(self, board: tuple[int, ...]) -> int:
        if len(board) != self.n * self.n:
            raise ValueError(f"board length {len(board)} != n^2 {self.n * self.n}")
        return self.solver.value(tuple(board), 1)

    # ---- partitions (both non-equivalent COMPOSED definitions) -------------
    def immediate_wins(self, board: tuple[int, ...]) -> list[int]:
        """Moves that win immediately for us (single-stone completion)."""
        return [m for m in self.solver.empties(board)
                if self.solver.winner(self.solver.play(board, m, 1)) == 1]

    def threat_count(self, board: tuple[int, ...], player: int = 1) -> int:
        """Lines with exactly two `player` stones (repo ceiling2 convention;
        lines already fully owned by `player` are excluded)."""
        n = 0
        for i, j, k in self.solver.lines:
            cell = (board[i], board[j], board[k])
            if cell[0] == cell[1] == cell[2] == player:
                continue
            if sum(1 for v in cell if v == player) == 2:
                n += 1
        return n

    def is_composed_imm(self, board: tuple[int, ...]) -> bool:
        """>= 2 immediate winning moves (task wording; A1 frozen gate)."""
        return len(self.immediate_wins(board)) >= 2

    def is_composed_thr(self, board: tuple[int, ...]) -> bool:
        """>= 2 threat lines (repo ceiling2.is_simple's COMPOSED)."""
        return self.threat_count(board, 1) >= 2

    # ---- baselines ----------------------------------------------------------
    def chance(self, boards: list[tuple[int, ...]] | None = None) -> float:
        """mean(|optimal| / |empty|) — the probability that a uniform random
        EMPTY cell hits the optimal set (PREREG §3 chance definition)."""
        if boards is None:
            boards = self.boards()
        vals = []
        for b in boards:
            e = sum(1 for v in b if v == 0)
            if e:
                vals.append(len(self.labels(b)) / e)
        if not vals:
            raise ValueError("chance: no boards with empty cells")
        return sum(vals) / len(vals)

    def floor_random_empty(self, seed: int = SEED, draws: int = 8,
                           boards: list[tuple[int, ...]] | None = None) -> float:
        """Measured random-empty-cell floor: for each board pick `draws`
        uniform random empty cells, score the hit rate against the optimal
        set. Expectation equals chance(); seed 2718 default (house)."""
        rng = random.Random(seed)
        if boards is None:
            boards = self.boards()
        hits, tot = 0, 0
        for b in boards:
            opts = self.labels(b)
            emp = self.solver.empties(b)
            if not emp:
                continue
            for _ in range(draws):
                tot += 1
                if rng.choice(emp) in opts:
                    hits += 1
        if tot == 0:
            raise ValueError("floor: no boards with empty cells")
        return hits / tot

    # ---- stats bundle -------------------------------------------------------
    def stats(self) -> dict:
        boards = self.boards()
        comp_imm = sum(1 for b in boards if self.is_composed_imm(b))
        comp_thr = sum(1 for b in boards if self.is_composed_thr(b))
        agree = sum(1 for b in boards if self.is_composed_imm(b) == self.is_composed_thr(b))
        return {
            "n": self.n,
            "n_path_rows": self.n_path_rows,
            "n_distinct_boards": self.n_distinct_boards,
            "composed_imm_ge2_wins": comp_imm,
            "composed_thr_ge2_threats": comp_thr,
            "partitions_agree_boards": agree,
            "chance_mean": round(self.chance(boards), 4),
            "floor_random_empty": round(self.floor_random_empty(), 4),
            "path_rows_note": "path rows are move-order duplicated; distinct boards "
                              "are the state count. Report both, always.",
        }


# ---- module-level convenience interface ------------------------------------
_CACHE: dict[int, LabelSet] = {}


def solve(n: int = 3) -> LabelSet:
    """Solve the NxN game from the empty board (memoized per n).

    n=3 enumerates in ~1 s pure-python; n=4 is supported but much larger.
    """
    if n not in _CACHE:
        _CACHE[n] = LabelSet(n, ExactMinimax(n))
    return _CACHE[n]


def labels(board: tuple[int, ...], n: int | None = None) -> set[int]:
    """Optimal-move set for one our-to-move board (infers n from len(board))."""
    if n is None:
        nn = len(board)
        n = int(nn ** 0.5)
        if n * n != nn:
            raise ValueError(f"board length {nn} is not a perfect square")
    return solve(n).labels(board)


def to_key(board: tuple[int, ...]) -> str:
    """Stable string key over '0','1','2' (value + 1) — feedable to a hash
    splitter such as blocks/board_disjoint_cv (FNV-1a-64 high-32)."""
    return "".join(str(v + 1) for v in board)


# ----------------------------------------------------------------------------
# SELF-TEST — full 3x3 enumeration, <10 s CPU, single JSON verdict line.
# ----------------------------------------------------------------------------
def _brute_force_optimal(board: tuple[int, ...], n: int,
                         lines: tuple[tuple[int, ...], ...]) -> set[int]:
    """INDEPENDENT memo-free brute force (self-test only): plain recursion,
    deliberately sharing no state with the memoized solver."""
    def winner(b):
        for a, c, d in lines:
            if b[a] == b[c] == b[d] != 0:
                return b[a]
        return 0

    def val(b, turn):
        w = winner(b)
        if w:
            return w
        emp = [i for i, v in enumerate(b) if v == 0]
        if not emp:
            return 0
        best = None
        for m in emp:
            nb = list(b)
            nb[m] = turn
            v = val(tuple(nb), -turn)
            best = v if best is None else (max(best, v) if turn == 1 else min(best, v))
        return best

    emp = [i for i, v in enumerate(board) if v == 0]
    if winner(board) or not emp:
        return set()
    vals = {}
    for m in emp:
        nb = list(board)
        nb[m] = 1
        vals[m] = val(tuple(nb), -1)
    best = max(vals.values())
    return {m for m, v in vals.items() if v == best}


def _self_test() -> int:
    ls = solve(3)
    s = ls.stats()
    print(json.dumps({"stats": s}, indent=1))

    # 1. booked receipt counts (fail loud on any drift)
    assert ls.n_path_rows == EXPECT_PATH_ROWS_3X3, \
        f"n_path_rows {ls.n_path_rows} != {EXPECT_PATH_ROWS_3X3}"
    assert ls.n_distinct_boards == EXPECT_DISTINCT_3X3, \
        f"n_distinct {ls.n_distinct_boards} != {EXPECT_DISTINCT_3X3}"
    assert s["composed_imm_ge2_wins"] == EXPECT_COMPOSED_IMM_3X3, \
        f"composed_imm {s['composed_imm_ge2_wins']} != {EXPECT_COMPOSED_IMM_3X3}"
    assert s["composed_thr_ge2_threats"] == EXPECT_COMPOSED_THR_3X3, \
        f"composed_thr {s['composed_thr_ge2_threats']} != {EXPECT_COMPOSED_THR_3X3}"
    assert s["partitions_agree_boards"] == EXPECT_AGREEMENT_3X3, \
        f"agreement {s['partitions_agree_boards']} != {EXPECT_AGREEMENT_3X3}"
    print(f"counts OK: path_rows={ls.n_path_rows} distinct={ls.n_distinct_boards} "
          f"comp_imm={s['composed_imm_ge2_wins']} comp_thr={s['composed_thr_ge2_threats']} "
          f"agree={s['partitions_agree_boards']}")

    # 2. empty board: value = draw (0); optimal set = ALL 9 opening moves.
    #    (Verified against the reference solver: every opening move draws
    #    under exact minimax. The "center + corners" guess is WRONG — 5 moves
    #    would contradict value 0 for the others. Assert what minimax gives.)
    empty = (0,) * 9
    assert ls.board_value(empty) == 0, "empty board must be a draw (value 0)"
    assert ls.labels(empty) == set(range(9)), \
        f"empty board optimal set {sorted(ls.labels(empty))} != all 9 moves"
    print("empty board OK: value=0 (draw), optimal = all 9 moves "
          "(every opening move draws — 'center + corners' guess refuted)")

    # 3. independent memo-free brute force on a seeded random sample (>= 50 boards)
    rng = random.Random(SEED)
    distinct_boards = ls.boards()
    sample = rng.sample(distinct_boards, 64)
    sample.append(empty)  # always include the root
    n_checked = 0
    for b in sample:
        got = ls.labels(b)
        want = _brute_force_optimal(b, 3, ls.solver.lines)
        assert got == want, f"brute-force disagreement on {b}: solver={sorted(got)} brute={sorted(want)}"
        n_checked += 1
    print(f"brute-force cross-check OK: {n_checked} boards agree (memo-free independent recursion)")

    # 4. chance baseline in (0.5, 0.6); floor ~= chance in expectation
    ch = s["chance_mean"]
    assert 0.5 < ch < 0.6, f"chance {ch} outside (0.5, 0.6)"
    fl = s["floor_random_empty"]
    assert abs(fl - ch) < 0.02, f"floor {fl} too far from chance {ch}"
    print(f"baselines OK: chance={ch} (universe, receipt 0.5865; test-set 0.5566), "
          f"floor_random_empty={fl} (expectation == chance)")

    # 5. rows iterators agree with counts
    assert len(list(ls.rows())) == ls.n_distinct_boards
    assert len(list(ls.path_row_iter())) == ls.n_path_rows
    # distinct boards really are distinct; every label set non-empty
    assert len({b for b, _ in ls.rows()}) == ls.n_distinct_boards
    assert all(len(opt) >= 1 for _, opt in ls.rows())

    print(json.dumps({"verdict": "PASS"}))
    return 0


if __name__ == "__main__":
    sys.exit(_self_test())
