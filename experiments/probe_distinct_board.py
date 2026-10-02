#!/usr/bin/env python3
"""PROBE-BATTERY #4 — distinct-board re-evaluation of minimax closure (pie-minimax #2).

GATE (from pr_harvest/SUMMARY.md top-10 table, #4):
    "global/composed top-1 on 2,423 distinct boards >= 0.99 (or the drop is the finding)"
CARD (pie-minimax #2): same MLP (9-64-9 relu, set-valued loss, Adam full-batch lr 0.01,
    patience 200), but train/eval on the 2,423 DISTINCT boards instead of the
    180,361 duplicated path rows. If global top-1 stays >= 0.99 on distinct-only eval,
    P1 FAIL-HIGH is not a duplicate artifact; if it drops, the closure claim had a
    sampling leak. PASS = a clean verdict either way (branch is the finding).
VERDICT LAW (board): std==0 on a gated seed-mean -> INCONCLUSIVE, never PASS.

Self-contained: exact minimax solver re-implemented here from the pie-minimax
semantics (alternating walk from the empty board, our-turn states, SET-valued
optimal moves). CPU-only, torch-CPU. Seed 2718 (+2719, 2720 for the seed mean).
Booked to results/probe_battery/distinct_board.json. No commit.
"""
from __future__ import annotations

import json
import os
import sys
import time
from functools import lru_cache

import numpy as np
import torch

SEEDS = [2718, 2719, 2720]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "results", "probe_battery", "distinct_board.json")

LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8),
         (0, 3, 6), (1, 4, 7), (2, 5, 8),
         (0, 4, 8), (2, 4, 6))


def winner(b):
    for a, c, d in LINES:
        if b[a] == b[c] == b[d] != 0:
            return b[a]
    return 0


def moves(b):
    return [i for i in range(9) if b[i] == 0]


def play(b, mv):
    nb = list(b)
    nb[mv] = 1
    return tuple(nb)


def respond(b, mv):
    nb = list(b)
    nb[mv] = -1
    return tuple(nb)


@lru_cache(maxsize=None)
def _opp_best_after(b):
    """Value after WE just moved on b: opponent replies optimally (their best = our worst)."""
    w = winner(b)
    if w:
        return w
    replies = moves(b)
    if not replies:
        return 0
    return min(value(respond(b, r)) for r in replies)


@lru_cache(maxsize=None)
def value(b):
    """Exact minimax value with US to move: +1 win, 0 draw, -1 loss."""
    w = winner(b)
    if w:
        return w
    legal = moves(b)
    if not legal:
        return 0
    return max(_opp_best_after(play(b, m)) for m in legal)


@lru_cache(maxsize=None)
def optimal(b):
    """The SET of optimal moves (several are frequently equally correct)."""
    if winner(b) or not moves(b):
        return ()
    vals = {m: _opp_best_after(play(b, m)) for m in moves(b)}
    best = max(vals.values())
    return tuple(m for m, v in vals.items() if v == best)


def enumerate_reachable(max_plies=9):
    """Every our-turn position reachable in alternating play, with exact optimal sets.
    Returns the PATH-WEIGHTED list (duplicates = multiple paths reach the board)."""
    out = []

    def walk(b, plies, our_turn):
        if plies > max_plies or winner(b) or not moves(b):
            return
        if our_turn:
            opt = optimal(b)
            if opt:
                out.append((b, opt))
        step = play if our_turn else respond
        for m in moves(b):
            walk(step(b, m), plies + 1, not our_turn)

    walk((0,) * 9, 0, True)
    return out


def fnv1a64(data: bytes) -> int:
    h = 0xCBF29CE484222325
    for c in data:
        h ^= c
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def bucket(b, m=10):
    # high 32 bits of FNV-1a-64 (raw low bits are weak on 3x3 boards -- a1_pie lesson)
    return (fnv1a64(bytes((int(v) & 0xFF) for v in b)) >> 32) % m


def build_data():
    states = enumerate_reachable()
    n_path_rows = len(states)
    uniq = {b: opt for b, opt in states}
    boards = sorted(uniq.keys())
    X = np.array([b for b in boards], dtype=np.float32)
    M = np.zeros((len(boards), 9), dtype=np.float32)
    for r, b in enumerate(boards):
        for m in uniq[b]:
            M[r, m] = 1.0

    def imm_wins(b):
        return [m for m in range(9) if b[m] == 0 and winner(play(b, m)) == 1]

    composed = np.array([len(imm_wins(b)) >= 2 for b in boards], dtype=bool)
    return states, n_path_rows, boards, uniq, X, M, composed


def train_mlp(Xtr, Mtr, seed, hidden=64, lr=0.01, max_steps=4000, patience=200,
              wtr=None):
    """Their protocol: Adam full-batch, set-valued loss -log sum_{m in Opt} softmax(z)_m,
    early stop on train-loss plateau (min_delta 1e-6, patience 200).
    wtr: optional per-row weights — the mean over 20k with-replacement draws equals
    the draw-count-weighted mean over unique boards (CPU speed; same loss value)."""
    torch.manual_seed(seed)
    model = torch.nn.Sequential(
        torch.nn.Linear(9, hidden), torch.nn.ReLU(), torch.nn.Linear(hidden, 9))
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    Xt = torch.tensor(Xtr)
    Mt = torch.tensor(Mtr)
    Wt = torch.tensor(wtr) if wtr is not None else None
    best, since, steps = float("inf"), 0, 0
    for step in range(max_steps):
        P = torch.softmax(model(Xt), dim=1)
        row = -torch.log((P * Mt).sum(dim=1).clamp_min(1e-12))
        loss = (row * Wt).sum() / Wt.sum() if Wt is not None else row.mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
        steps += 1
        lv = float(loss.detach())
        if lv < best - 1e-6:
            best, since = lv, 0
        else:
            since += 1
            if since >= patience or lv < 1e-5:
                break
    model.eval()
    return model, {"steps": steps, "final_train_loss": best}


def top1(model, X, opt_sets):
    with torch.no_grad():
        top = model(torch.tensor(X)).argmax(dim=1).numpy()
    return float(np.mean([int(top[r]) in opt_sets[r] for r in range(len(opt_sets))]))


def main() -> int:
    t0 = time.time()
    torch.set_num_threads(4)
    states, n_path_rows, boards, uniq, X, M, composed = build_data()
    n_distinct = len(boards)
    opt_sets = [frozenset(uniq[b]) for b in boards]

    # sanity: the published state-space priors (probe #8 re-measures these formally)
    print(f"[data] path_rows={n_path_rows} distinct_boards={n_distinct} "
          f"composed(imm>=2 wins)={int(composed.sum())}")

    # distinct-world analog of their 20k train draw: sample WITH REPLACEMENT from the
    # 2,423 DISTINCT boards (their run sampled from 180,361 path-weighted rows).
    test_mask = np.array([bucket(b, 10) == 0 for b in boards], dtype=bool)
    tr_idx = np.nonzero(~test_mask)[0]
    te_idx = np.nonzero(test_mask)[0]

    per_seed = []
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        draw = rng.choice(tr_idx, size=20000, replace=True)
        # compress the 20k with-replacement draw to unique boards + counts (same loss)
        uniq_idx, counts = np.unique(draw, return_counts=True)
        model, info = train_mlp(X[uniq_idx], M[uniq_idx], seed, wtr=counts.astype(np.float64))
        # eval 1: ALL 2,423 distinct boards (their "global" semantics, distinct-only)
        g_all = top1(model, X, opt_sets)
        # eval 2: composed subset (>=2 simultaneous immediate wins, 320 boards)
        g_comp = top1(model, X[composed], [opt_sets[i] for i in np.nonzero(composed)[0]])
        # eval 3: board-disjoint held-out (the honest generalization number)
        g_ho = top1(model, X[te_idx], [opt_sets[i] for i in te_idx])
        # eval 4: unseen-board coverage check — boards never drawn into train
        seen = np.zeros(n_distinct, dtype=bool)
        seen[draw] = True
        unseen = np.array([i for i in range(n_distinct) if not seen[i]])
        g_unseen = (top1(model, X[unseen], [opt_sets[i] for i in unseen])
                    if len(unseen) else float("nan"))
        per_seed.append({"seed": seed, "top1_all_distinct": round(g_all, 4),
                         "top1_composed320": round(g_comp, 4),
                         "top1_board_disjoint_heldout": round(g_ho, 4),
                         "unseen_boards_n": int(len(unseen)),
                         "top1_unseen_only": round(g_unseen, 4) if len(unseen) else None,
                         **info})
        print(f"[seed {seed}] all={g_all:.4f} composed={g_comp:.4f} "
              f"heldout={g_ho:.4f} unseen({len(unseen)})={g_unseen:.4f} steps={info['steps']}")

    all_top1 = np.array([s["top1_all_distinct"] for s in per_seed])
    comp_top1 = np.array([s["top1_composed320"] for s in per_seed])
    mean_all, std_all = float(all_top1.mean()), float(all_top1.std())
    mean_comp, std_comp = float(comp_top1.mean()), float(comp_top1.std())

    # GATE (table #4): global/composed top-1 on 2,423 distinct boards >= 0.99,
    # or the drop is the finding. std==0 on the gated seed-mean -> INCONCLUSIVE.
    gate_sat = bool(mean_all >= 0.99 and mean_comp >= 0.99)
    branch = ("P1 FAIL-HIGH is NOT a duplicate artifact (distinct-only top-1 holds >=0.99)"
              if gate_sat else
              "the drop IS the finding: distinct-only top-1 fell below 0.99 — the 0.9996 "
              "closure number leaned on path-duplicate sampling")
    if std_all == 0.0 or std_comp == 0.0:
        verdict = "INCONCLUSIVE"  # murmuration law: zero seed variance, never PASS
        branch += f" [std==0 law: std_all={std_all:.4f} std_comp={std_comp:.4f}]"
    else:
        verdict = "PASS"  # clean verdict either way per the card; branch carries the reading

    result = {
        "probe": "distinct-board re-evaluation of minimax closure",
        "source": "pr_harvest/SUMMARY.md #4 / CARDS.md pie-minimax #2",
        "gate": "global/composed top-1 on 2,423 distinct boards >=0.99 (or the drop is the "
                "finding); std==0 on gated seed-mean -> INCONCLUSIVE",
        "verdict": verdict,
        "branch": branch,
        "numbers": {
            "state_space_rederived": {"path_rows": n_path_rows,
                                      "distinct_our_turn_boards": n_distinct,
                                      "composed_imm2win_boards": int(composed.sum())},
            "protocol": "MLP 9-64-9 relu, set-valued loss, Adam full-batch lr 0.01, "
                        "patience 200; train = 20k draws WITH replacement from the 2,423 "
                        "distinct boards (their run drew from 180,361 path-weighted rows)",
            "per_seed": per_seed,
            "mean_top1_all_distinct": round(mean_all, 4),
            "std_top1_all_distinct": round(std_all, 4),
            "mean_top1_composed320": round(mean_comp, 4),
            "std_top1_composed320": round(std_comp, 4),
            "published_prior": {"mlp_top1_global": 0.9996, "mlp_top1_composed": 1.0,
                                "split": "20k/8k with-replacement from 180,361 path rows"},
        },
        "seed": SEEDS,
        "runtime_seconds": round(time.time() - t0, 1),
        "device": "cpu",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=2)
    print(f"VERDICT: {verdict} — {branch}")
    print(f"mean_all={mean_all:.4f}±{std_all:.4f} mean_composed={mean_comp:.4f}±{std_comp:.4f}")
    print(f"booked -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
