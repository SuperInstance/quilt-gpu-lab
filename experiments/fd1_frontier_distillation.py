#!/usr/bin/env python3
"""FD1 — Frontier distillation (CPU).

Student trained only on frontier (low-consensus) episodes vs uniform training, plus an
eval-time hybrid (field answers easy, student answers hard). Teacher = minimax solver.
See proposals/runs/FD1-frontier-distillation.md (frozen gates).
"""
import json
import os
import sys

import numpy as np

SEEDS = [7721, 7722, 7723, 7724, 7725]
N_CORPUS = 3000
N_FIELD = 2000
K = 9
ROOM_DIM = 16
EPOCHS = 60
LR = 1e-2
FRONTIER_FRAC = 1.0 / 3.0
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "fd1_frontier_distillation")

LINES = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]]


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
            return board
        moves = [i for i in range(9) if board[i] == "."]
        if len(moves) < 9 and rng.random() < 0.30:
            return board
        i = rng.choice(moves)
        board[i] = to_move
        to_move = "O" if to_move == "X" else "X"


def onehot(board):
    v = np.zeros(27, dtype=np.float64)
    for i, c in enumerate(board):
        v[3 * i + (0 if c == "." else 1 if c == "X" else 2)] = 1.0
    return v


PROJ = np.random.default_rng(4242).normal(size=(27, ROOM_DIM))  # fixed geometry across seeds


def room(board):
    return onehot(board) @ PROJ


def margins(rooms_q, field_rooms, field_labels):
    """Leave-one-out margins + field predictions. Returns (margins_list, preds_list)."""
    out_m, out_p = [], []
    for q in rooms_q:
        d = np.linalg.norm(field_rooms - q, axis=1)
        idx = np.argsort(d)[: K + 1]
        # drop self-match if distance ~0 and label present
        idx = [j for j in idx if d[j] > 1e-9][:K] or idx[:K]
        w = 1.0 / (1.0 + d[idx])
        votes = np.zeros(3)
        for j, wij in zip(idx, w):
            votes[int(field_labels[j]) + 1] += wij
        p = (votes + 1e-12) / (votes.sum() + 1e-12)
        s = np.sort(p)
        out_m.append(float(s[-1] - s[-2]))
        out_p.append(int(np.argmax(votes)) - 1)
    return out_m, out_p


def train_mlp(X, Y, rng, epochs=EPOCHS, lr=LR):
    """27->48->24->3, tanh, softmax CE, Adam. Y in {0,1,2} (label+1)."""
    rng = np.random.default_rng(rng)
    n, d = X.shape
    W1 = rng.normal(size=(d, 48)) * np.sqrt(2.0 / d)
    b1 = np.zeros(48)
    W2 = rng.normal(size=(48, 24)) * np.sqrt(2.0 / 48)
    b2 = np.zeros(24)
    W3 = rng.normal(size=(24, 3)) * np.sqrt(2.0 / 24)
    b3 = np.zeros(3)
    params = [W1, b1, W2, b2, W3, b3]
    m = [np.zeros_like(p) for p in params]
    v = [np.zeros_like(p) for p in params]
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    Yoh = np.eye(3)[Y]
    t = 0
    for _ in range(epochs):
        # forward
        h1 = np.tanh(X @ W1 + b1)
        h2 = np.tanh(h1 @ W2 + b2)
        logits = h2 @ W3 + b3
        z = logits - logits.max(axis=1, keepdims=True)
        p = np.exp(z) / np.exp(z).sum(axis=1, keepdims=True)
        g = (p - Yoh) / n
        # backward
        gW3 = h2.T @ g
        gb3 = g.sum(axis=0)
        gh2 = g @ W3.T * (1 - h2 ** 2)
        gW2 = h1.T @ gh2
        gb2 = gh2.sum(axis=0)
        gh1 = gh2 @ W2.T * (1 - h1 ** 2)
        gW1 = X.T @ gh1
        gb1 = gh1.sum(axis=0)
        grads = [gW1, gb1, gW2, gb2, gW3, gb3]
        t += 1
        for i, (p_, g_) in enumerate(zip(params, grads)):
            m[i] = beta1 * m[i] + (1 - beta1) * g_
            v[i] = beta2 * v[i] + (1 - beta2) * g_ ** 2
            mh = m[i] / (1 - beta1 ** t)
            vh = v[i] / (1 - beta2 ** t)
            p_ -= lr * mh / (np.sqrt(vh) + eps)
    return predict_mlp, params


def predict_mlp(params, X):
    W1, b1, W2, b2, W3, b3 = params
    h1 = np.tanh(X @ W1 + b1)
    h2 = np.tanh(h1 @ W2 + b2)
    logits = h2 @ W3 + b3
    return np.argmax(logits, axis=1)


def run_seed(seed):
    rng = np.random.default_rng(seed)
    memo = {}
    boards, labels = [], []
    seen = set()
    while len(boards) < N_CORPUS:
        b = random_playout(rng, memo)
        t = tuple(b)
        if t in seen:
            continue
        seen.add(t)
        boards.append(b)
        labels.append(solved(b, "X", memo))
    field_b, field_l = boards[:N_FIELD], labels[:N_FIELD]
    eval_b, eval_l = boards[N_FIELD:], labels[N_FIELD:]

    f_rooms = np.stack([room(b) for b in field_b])
    e_rooms = np.stack([room(b) for b in eval_b])
    fm, _ = margins(f_rooms, f_rooms, field_l)          # leave-one-out field margins
    em, epred = margins(e_rooms, f_rooms, field_l)      # eval-board margins + field predictions
    fm = np.asarray(fm)
    thr = np.quantile(fm, FRONTIER_FRAC)
    frontier_idx = np.where(fm <= thr)[0]
    easy_idx = np.where(fm > thr)[0]

    Y = np.asarray(field_l) + 1
    X_all = f_rooms
    _, params_u = train_mlp(X_all, Y, seed)                      # uniform
    _, params_f = train_mlp(X_all[frontier_idx], Y[frontier_idx], seed)  # frontier

    Yu = predict_mlp(params_u, e_rooms)
    Yf = predict_mlp(params_f, e_rooms)
    eval_Y = np.asarray(eval_l) + 1
    Yh = np.where(np.asarray(em) <= thr, Yf, np.asarray(epred))  # hybrid

    acc = lambda Yh_: float(np.mean(Yh_ == eval_Y))
    field_only = float(np.mean(np.asarray(epred) == eval_Y))
    return {
        "seed": seed,
        "n_frontier": int(len(frontier_idx)),
        "acc_uniform": acc(Yu),
        "acc_frontier": acc(Yf),
        "acc_hybrid": acc(Yh),
        "acc_field_only": field_only,
    }


def main(smoke=False):
    global N_CORPUS, N_FIELD
    seeds = SEEDS[:2] if smoke else SEEDS
    if smoke:
        N_CORPUS, N_FIELD = 400, 200

    rows = []
    for seed in seeds:
        r = run_seed(seed)
        rows.append(r)
        print(f"[seed {seed}] uniform={r['acc_uniform']:.4f} frontier={r['acc_frontier']:.4f} "
              f"hybrid={r['acc_hybrid']:.4f} field_only={r['acc_field_only']:.4f} "
              f"(n_frontier={r['n_frontier']})", flush=True)

    a = lambda k: float(np.mean([r[k] for r in rows]))
    wins = sum(1 for r in rows
               if r["acc_frontier"] >= r["acc_uniform"] - 0.005
               and r["acc_hybrid"] >= r["acc_uniform"] + 0.010)
    wins_a = sum(1 for r in rows if r["acc_frontier"] >= r["acc_uniform"] - 0.005)
    wins_b = sum(1 for r in rows if r["acc_hybrid"] >= r["acc_uniform"] + 0.010)

    if wins >= 4:
        verdict = "KEEP"
    elif wins_a >= 4 and wins_b < 4:
        verdict = "HALF"
    else:
        verdict = "KILL"

    out = {
        "experiment": "FD1-frontier-distillation",
        "smoke": smoke,
        "seeds": [r["seed"] for r in rows],
        "rows": rows,
        "mean": {k: a(k) for k in ["acc_uniform", "acc_frontier", "acc_hybrid", "acc_field_only"]},
        "wins": {"both": wins, "a_frontier_safe": wins_a, "b_hybrid_wins": wins_b},
        "gate": {"frontier_loss_max_pp": 0.5, "hybrid_gain_min_pp": 1.0, "win_seeds": 4},
        "verdict": verdict,
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "results.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"[VERDICT] {verdict} wins={wins}/{len(rows)} "
          f"(a={wins_a}/5 b={wins_b}/5)", flush=True)


if __name__ == "__main__":
    main(smoke="--smoke" in sys.argv)
