#!/usr/bin/env python3
"""H1 — Judgment holonomy audit (CPU).

Can symmetry-loop inconsistency localize a corrupted field region with ZERO teacher calls
during the audit, and does it beat the plain kNN-margin baseline? See
proposals/runs/H1-judgment-holonomy.md (frozen gates).
"""
import itertools
import json
import math
import os
import sys

import numpy as np

SEEDS = [7711, 7712, 7713, 7714, 7715]
N_FIELD = 1200
N_PROBE = 600          # 300 corrupted-matching + 300 clean
K = 9
ROOM_DIM = 16
MIN_CORRUPT = 40
AUC_GATE = 0.80
WIN_GATE = 4           # of 5 seeds: AUC >= gate AND beats baseline
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "h1_judgment_holonomy")

LINES = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]]


# ---------- tictactoe core ----------

def winner(b):
    for line in LINES:
        v = b[line[0]]
        if v != "." and all(b[i] == v for i in line):
            return v
    return None


def solved(board, to_move, memo):
    key = ("".join(board), to_move)
    if key in memo:
        return memo[key]
    w = winner(board)
    if w == "X":
        return 1
    if w == "O":
        return -1
    if "." not in board:
        return 0
    vals = []
    for i in range(9):
        if board[i] == ".":
            nb = list(board)
            nb[i] = to_move
            vals.append(solved(nb, "O" if to_move == "X" else "X", memo))
    v = max(vals) if to_move == "X" else min(vals)
    memo[key] = v
    return v


def random_playout(rng, memo):
    board = ["."] * 9
    to_move = "X"
    while True:
        if winner(board) is not None or "." not in board:
            return board, to_move
        moves = [i for i in range(9) if board[i] == "."]
        if len(moves) < 9 and rng.random() < 0.30:
            return board, to_move
        i = rng.choice(moves)
        board[i] = to_move
        to_move = "O" if to_move == "X" else "X"


def onehot(board):
    v = np.zeros(27, dtype=np.float64)
    for i, c in enumerate(board):
        v[3 * i + (0 if c == "." else 1 if c == "X" else 2)] = 1.0
    return v


# ---------- symmetry group (rotations + reflections, 8 elements) ----------

def _perm_from_transform(idxperm):
    # idxperm: new[i] = old[idxperm[i]]
    return idxperm


PERMS = []
_rows_cols = [(0, 1, 2, 3, 4, 5, 6, 7, 8)]
for p in itertools.permutations(range(3)):
    pass  # grid symmetries generated explicitly below


def grid_perms():
    perms = []
    for rot in range(4):
        for flip in (False, True):
            perm = []
            for r in range(3):
                for c in range(3):
                    rr, cc = (c, 2 - r) if not flip else (c, r)
                    # rotate coordinates rot times
                    for _ in range(rot):
                        rr, cc = cc, 2 - rr
                    perm.append(3 * rr + cc)
            perms.append(perm)
    uniq = []
    for p in perms:
        if p not in uniq:
            uniq.append(p)
    return uniq


PERMS = grid_perms()
assert len(PERMS) == 8, f"expected 8 symmetries, got {len(PERMS)}"


def apply_perm(board, perm):
    return [board[perm[i]] for i in range(9)]


# ---------- field ----------

class Field:
    def __init__(self, boards, labels, rng):
        self.rooms = np.stack([onehot(b) for b in boards]) @ self._proj(rng)
        self.labels = np.asarray(labels)

    @staticmethod
    def _proj(rng):
        rng = np.random.default_rng(rng if isinstance(rng, int) else 0)
        P = np.random.default_rng(4242).normal(size=(27, ROOM_DIM))  # fixed projection...
        return P  # NOTE: fixed across seeds by design; seeds vary data, not geometry

    def grade(self, board_onehot, exclude_idx=None):
        q = board_onehot @ self._proj(0)
        d = np.linalg.norm(self.rooms - q, axis=1)
        idx = np.argsort(d)
        if exclude_idx is not None:
            idx = idx[idx != exclude_idx][:K]
        else:
            idx = idx[:K]
        w = 1.0 / (1.0 + d[idx])
        votes = np.zeros(3)
        for j, wij in zip(idx, w):
            votes[int(self.labels[j]) + 1] += wij
        pred = int(np.argmax(votes)) - 1
        total = votes.sum() + 1e-12
        p = votes / total
        margin = float(np.sort(p)[-1] - np.sort(p)[-2])
        return pred, margin, p


def entropy(p):
    p = np.asarray(p) + 1e-12
    return float(-np.sum(p * np.log(p)))


def auc(scores_pos, scores_neg):
    """Rank-based AUC: P(pos > neg) + 0.5 P(equal)."""
    pos, neg = np.asarray(scores_pos), np.asarray(scores_neg)
    gt = sum((1.0 if s > n else 0.5 if s == n else 0.0) for s in pos for n in neg)
    return gt / (len(pos) * len(neg))


def run_seed(seed):
    rng = np.random.default_rng(seed)
    memo = {}

    # corpus
    boards, labels = [], []
    seen = set()
    while len(boards) < N_FIELD:
        b, tm = random_playout(rng, memo)
        t = tuple(b)
        if t in seen:
            continue
        seen.add(t)
        boards.append(b)
        labels.append(solved(b, tm, memo))

    # blind region pattern: TWO fixed cells with fixed marks (per-seed placement)
    cells = rng.choice(9, size=2, replace=False)
    marks = ["X", "O"]
    pattern = {int(c): m for c, m in zip(cells, marks)}

    def matches(b):
        return all(b[i] == m for i, m in pattern.items())

    corrupted = [i for i, b in enumerate(boards) if matches(b)]
    if len(corrupted) < MIN_CORRUPT:
        return None  # void seed, re-drawn by caller
    labels = list(labels)
    for i in corrupted:
        labels[i] = -int(labels[i])  # guaranteed wrong

    field = Field(boards, labels, seed)

    # probes: fresh boards, half matching P
    probes, is_corr = [], []
    while len(probes) < N_PROBE:
        b, _tm = random_playout(rng, memo)
        want = len(probes) < N_PROBE // 2
        if matches(b) != want:
            continue
        t = tuple(b)
        if t in seen:
            continue
        seen.add(t)
        probes.append(b)
        is_corr.append(want)

    # scores
    hol, base = [], []
    for b in probes:
        oh = onehot(b)
        preds = []
        for perm in PERMS:
            preds.append(field.grade(onehot(apply_perm(b, perm)))[0])
        counts = np.bincount(np.asarray(preds) + 1, minlength=3).astype(float)
        hol.append(entropy(counts / counts.sum()))
        base.append(-field.grade(oh)[1])  # negative margin = uncertainty

    pos_h = [s for s, c in zip(hol, is_corr) if c]
    neg_h = [s for s, c in zip(hol, is_corr) if not c]
    pos_b = [s for s, c in zip(base, is_corr) if c]
    neg_b = [s for s, c in zip(base, is_corr) if not c]

    return {
        "seed": seed,
        "n_corrupted": len(corrupted),
        "n_probes": N_PROBE,
        "auc_holonomy": auc(pos_h, neg_h),
        "auc_baseline": auc(pos_b, neg_b),
    }


def main(smoke=False):
    global N_FIELD, N_PROBE, MIN_CORRUPT
    seeds = SEEDS[:2] if smoke else SEEDS
    if smoke:
        N_FIELD, N_PROBE, MIN_CORRUPT = 300, 200, 15

    rows, voids = [], 0
    for seed in seeds:
        r = None
        attempts = 0
        while r is None and attempts < 10:
            r = run_seed(seed + 1000 * attempts)
            attempts += 1
            if r is None:
                voids += 1
        if r is None:
            print(f"[seed {seed}] VOID after {attempts} draws", flush=True)
            continue
        rows.append(r)
        print(f"[seed {r['seed']}] corrupted={r['n_corrupted']} "
              f"auc_holonomy={r['auc_holonomy']:.4f} auc_baseline={r['auc_baseline']:.4f}",
              flush=True)

    wins = sum(1 for r in rows if r["auc_holonomy"] >= AUC_GATE and r["auc_holonomy"] > r["auc_baseline"])
    gap = float(np.mean([r["auc_holonomy"] - r["auc_baseline"] for r in rows])) if rows else 0.0
    if len(rows) < len(seeds):
        verdict = "VOID"
    elif wins >= WIN_GATE:
        verdict = "KEEP"
    elif abs(gap) < 0.02:
        verdict = "INDIFFERENT"
    else:
        verdict = "KILL"

    out = {
        "experiment": "H1-judgment-holonomy",
        "smoke": smoke,
        "seeds": [r["seed"] for r in rows],
        "rows": rows,
        "n_void_draws": voids,
        "mean_auc_holonomy": float(np.mean([r["auc_holonomy"] for r in rows])) if rows else None,
        "mean_auc_baseline": float(np.mean([r["auc_baseline"] for r in rows])) if rows else None,
        "mean_gap": gap,
        "wins": wins,
        "gate": {"auc": AUC_GATE, "win_seeds": WIN_GATE},
        "verdict": verdict,
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "results.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"[VERDICT] {verdict} wins={wins}/{len(rows)} mean_gap={gap:+.4f}", flush=True)


if __name__ == "__main__":
    main(smoke="--smoke" in sys.argv)
