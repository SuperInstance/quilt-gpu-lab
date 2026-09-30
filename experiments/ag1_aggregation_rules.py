#!/usr/bin/env python3
"""AG1 — Aggregation-rule repair: consensus vs union vs track record (CPU).

Converts the Syzygy d158 holarchy finding into a falsifiable test on kNN judgment fields:
G1 consensus repairs substitution; G2 union beats consensus under omission; G3 track-record
rule selection beats momentary-agreement selection on mixed defects. See
proposals/runs/AG1-aggregation-rules.md (frozen gates).
"""
import json
import os
import sys
import zlib

import numpy as np

SEEDS = [8811, 8812, 8813, 8814, 8815]
N_MEMBERS = 7
N_POOL = 2500
N_LIVE = 1500                     # shared live pool; each member samples N_CORPUS from it
N_CORPUS, N_CALIB, N_DEV, N_TEST = 1200, 300, 200, 500
K = 9
ROOM = 16
SUB_FRAC = OM_FRAC = 0.15
MIX_SUB = MIX_OM = 0.08
TAU_PCT = 85          # abstention percentile on calibration nearest-distances
TAU_GRID = [0.40, 0.45, 0.50, 0.55, 0.60]
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "ag1_aggregation_rules")

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


class Member:
    def __init__(self, mseed, boards, labels, pool_idx):
        rng = np.random.default_rng(mseed)
        self.idx = rng.choice(len(pool_idx), N_CORPUS, replace=False)
        src = [pool_idx[j] for j in self.idx]
        self.proj = rng.normal(size=(27, ROOM)) / np.sqrt(ROOM)
        self.boards = [boards[j] for j in src]
        self.rooms = np.stack([onehot(b) for b in self.boards]) @ self.proj
        self.labels = np.array([labels[j] for j in src], dtype=int)
        self.calib_acc = 0.0

    def answer(self, oh, tau_abs, med_margin):
        q = oh @ self.proj
        d = np.linalg.norm(self.rooms - q, axis=1)
        if d.min() > tau_abs:
            return None, 0.0, False          # abstain
        idx = np.argsort(d)[:K]
        w = 1.0 / (1.0 + d[idx])
        votes = np.zeros(3)
        for j, wij in zip(idx, w):
            votes[int(self.labels[j]) + 1] += wij
        p = votes / votes.sum()
        s = np.sort(p)
        margin = float(s[-1] - s[-2])
        return int(np.argmax(votes)) - 1, margin, margin >= med_margin


def defect_member(m, cond, rng):
    """Return a defect view of member m: (rooms, labels) after SUB/OM/MIX."""
    rooms, labels = m.rooms, m.labels.copy()
    n = len(labels)
    if cond in ("SUB", "MIX"):
        f = SUB_FRAC if cond == "SUB" else MIX_SUB
        nflip = int(round(f * n))
        flip = rng.choice(n, nflip, replace=False)
        labels = labels.copy()
        labels[flip] = -labels[flip]
    if cond in ("OM", "MIX"):
        f = OM_FRAC if cond == "OM" else MIX_OM
        ndel = int(round(f * n))
        keep = rng.choice(n, n - ndel, replace=False)
        rooms, labels = rooms[keep], labels[keep]
    return rooms, labels


def eval_member(m, rooms, labels, tau_abs, med_margin, qs):
    """qs: list of (oh, truth). Returns (correct_count, n, margins, dists)."""
    correct = 0
    margins, dists = [], []
    saved_rooms, saved_labels = m.rooms, m.labels
    m.rooms, m.labels = rooms, labels
    for oh, truth in qs:
        ans, margin, _ = m.answer(oh, tau_abs, med_margin)
        margins.append(margin)
        correct += int(ans == truth)
    m.rooms, m.labels = saved_rooms, saved_labels
    return correct / len(qs)


def calibrate(m, rooms, labels, calib_qs):
    """Compute tau_abs (85th pct nearest-dist), median margin, accuracy on calib."""
    saved = (m.rooms, m.labels)
    m.rooms, m.labels = rooms, labels
    dists, margins = [], []
    for oh, _ in calib_qs:
        q = oh @ m.proj
        d = np.linalg.norm(m.rooms - q, axis=1)
        dists.append(float(d.min()))
        idx = np.argsort(d)[:K]
        w = 1.0 / (1.0 + d[idx])
        votes = np.zeros(3)
        for j, wij in zip(idx, w):
            votes[int(m.labels[j]) + 1] += wij
        p = votes / votes.sum()
        s = np.sort(p)
        margins.append(float(s[-1] - s[-2]))
    m.rooms, m.labels = saved
    tau = float(np.percentile(dists, TAU_PCT))
    med = float(np.median(margins))
    correct = 0
    for oh, truth in calib_qs:
        ans, _, _ = m.answer(oh, tau, med)
        correct += int(ans == truth)
    return tau, med, correct / len(calib_qs)


def pool_answers(members_defected, calib_params, qs):
    """All three rule answers + momentary share for each query board."""
    out = []
    for oh, _truth in qs:
        votes, weights, decisive = [], [], []
        for m, (tau, med, _acc) in zip(members_defected, calib_params):
            ans, margin, is_dec = m.answer(oh, tau, med)
            if ans is None:
                continue
            votes.append(ans)
            weights.append(np.exp(m.calib_acc / 0.05))
            decisive.append((ans, is_dec))
        if not votes:
            out.append({"cons": 0, "unio": 0, "trac": 0, "share": 0.0})
            continue
        arr = np.array(votes)
        counts = np.bincount(arr + 1, minlength=3)
        cons = int(np.argmax(counts)) - 1
        share = float(counts.max() / counts.sum())
        dec_votes = [v for v, d in decisive if d]
        if dec_votes:
            dc = np.bincount(np.array(dec_votes) + 1, minlength=3)
            unio = int(np.argmax(dc)) - 1
        else:
            unio = 0
        w = np.array(weights)
        wv = np.zeros(3)
        for v, wi in zip(votes, w):
            wv[v + 1] += wi
        trac = int(np.argmax(wv)) - 1
        out.append({"cons": cons, "unio": unio, "trac": trac, "share": share})
    return out


def acc_of(preds, qs):
    return float(np.mean([p == t for p, (_oh, t) in zip(preds, qs)]))


def run_seed(seed, smoke=False):
    global N_LIVE
    n_pool = 800 if smoke else N_POOL
    n_corpus = 400 if smoke else N_CORPUS
    n_calib, n_dev, n_test = (100, 80, 120) if smoke else (N_CALIB, N_DEV, N_TEST)
    if smoke:
        N_LIVE = 500
    rng = np.random.default_rng(seed)
    memo = {}
    boards, labels = [], []
    seen = set()
    while len(boards) < n_pool:
        b, tm = random_playout(rng, memo)
        t = tuple(b)
        if t in seen:
            continue
        seen.add(t)
        boards.append(b)
        labels.append(solved(b, tm, memo))

    perm = rng.permutation(len(boards))
    live_idx = perm[:N_LIVE]
    calib_idx = perm[N_LIVE:N_LIVE + n_calib]
    dev_idx = perm[N_LIVE + n_calib:N_LIVE + n_calib + n_dev]
    test_idx = perm[N_LIVE + n_calib + n_dev:N_LIVE + n_calib + n_dev + n_test]
    calib_qs = [(onehot(boards[i]), labels[i]) for i in calib_idx]
    dev_qs = [(onehot(boards[i]), labels[i]) for i in dev_idx]
    test_qs = [(onehot(boards[i]), labels[i]) for i in test_idx]

    members = []
    for m in range(N_MEMBERS):
        members.append(Member(seed * 100 + m, boards, labels, live_idx))

    conds = {}
    for cond in ("CLEAN", "SUB", "OM", "MIX"):
        crng = np.random.default_rng(seed * 7 + zlib.crc32(cond.encode()))  # deterministic salt
        params, dms = [], []
        for m in members:
            rooms, lab = defect_member(m, cond, crng)
            tau, med, acc = calibrate(m, rooms, lab, calib_qs)
            m2 = Member.__new__(Member)
            m2.proj, m2.rooms, m2.labels, m2.calib_acc = m.proj, rooms, lab, acc
            dms.append(m2)
            params.append((tau, med, acc))
        conds[cond] = {"members": dms, "tau_med": params}

    res = {}
    # G1: consensus vs mean single member on SUB
    sub = conds["SUB"]
    pool = pool_answers(sub["members"], sub["tau_med"], test_qs)
    cons_pred = [p["cons"] for p in pool]
    g1_cons = acc_of(cons_pred, test_qs)
    single = [p for (t, md, a) in sub["params"]]
    g1_single = float(np.mean(single))
    res["g1"] = {"cons": g1_cons, "single_mean": g1_single, "pass": g1_cons > g1_single}

    # G2: union vs consensus on OM
    om = conds["OM"]
    pool = pool_answers(om["members"], om["tau_med"], test_qs)
    g2_unio = acc_of([p["unio"] for p in pool], test_qs)
    g2_cons = acc_of([p["cons"] for p in pool], test_qs)
    res["g2"] = {"unio": g2_unio, "cons": g2_cons, "pass": g2_unio > g2_cons}

    # G3: SEL-track vs SEL-momentary on MIX (dev-frozen selections)
    mx = conds["MIX"]
    dev_pool = pool_answers(mx["members"], mx["tau_med"], dev_qs)
    test_pool = pool_answers(mx["members"], mx["tau_med"], test_qs)
    # SEL-momentary: tau_m frozen on dev
    best_tau, best_acc = None, -1
    for tau_m in TAU_GRID:
        preds = [(p["cons"] if p["share"] >= tau_m else p["unio"]) for p in dev_pool]
        a = acc_of(preds, dev_qs)
        if a > best_acc:
            best_tau, best_acc = tau_m, a
    mom_pred = [(p["cons"] if p["share"] >= best_tau else p["unio"]) for p in test_pool]
    g3_mom = acc_of(mom_pred, test_qs)
    # SEL-track: stream-level rule chosen by dev accuracy of each rule
    cons_dev = acc_of([p["cons"] for p in dev_pool], dev_qs)
    unio_dev = acc_of([p["unio"] for p in dev_pool], dev_qs)
    track_rule = "cons" if cons_dev >= unio_dev else "unio"
    g3_trk = acc_of([p[track_rule] for p in test_pool], test_qs)
    res["g3"] = {"track": g3_trk, "momentary": g3_mom, "rule": track_rule,
                 "tau_m": best_tau, "pass": g3_trk > g3_mom}

    # context: track rule + clean reference
    res["trac_acc_mix"] = acc_of([p["trac"] for p in test_pool], test_qs)
    clean = conds["CLEAN"]
    cp = pool_answers(clean["members"], clean["tau_med"], test_qs)
    res["clean_cons"] = acc_of([p["cons"] for p in cp], test_qs)
    res["single_clean"] = float(np.mean([a for (t, md, a) in clean["params"]]))
    return res


def main(smoke=False):
    seeds = SEEDS[:2] if smoke else SEEDS
    rows = []
    for seed in seeds:
        r = run_seed(seed, smoke=smoke)
        rows.append(r)
        print(f"[seed {seed}] G1 {'PASS' if r['g1']['pass'] else 'fail'} "
              f"(cons {r['g1']['cons']:.3f} vs single {r['g1']['single_mean']:.3f}) | "
              f"G2 {'PASS' if r['g2']['pass'] else 'fail'} "
              f"(unio {r['g2']['unio']:.3f} vs cons {r['g2']['cons']:.3f}) | "
              f"G3 {'PASS' if r['g3']['pass'] else 'fail'} "
              f"(trk-sel {r['g3']['track']:.3f} vs mom {r['g3']['momentary']:.3f}, rule={r['g3']['rule']}) | "
              f"trackvote {r['trac_acc_mix']:.3f} clean {r['clean_cons']:.3f}", flush=True)

    g = lambda k: sum(1 for r in rows if r[k]["pass"])
    verdict = "KEEP" if g("g1") >= 4 and g("g2") >= 4 and g("g3") >= 4 else (
        "PARTIAL-" + "+".join(x for x, k in [("SUB", "g1"), ("OM", "g2"), ("SEL", "g3")] if g(k) >= 4)
        if any(g(k) >= 4 for k in ("g1", "g2", "g3")) else "KILL")

    out = {
        "experiment": "AG1-aggregation-rules",
        "smoke": smoke,
        "seeds": seeds,
        "rows": rows,
        "gate_wins": {"g1": g("g1"), "g2": g("g2"), "g3": g("g3")},
        "verdict": verdict,
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "results.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"[VERDICT] {verdict} (G1 {g('g1')}/5 G2 {g('g2')}/5 G3 {g('g3')}/5)", flush=True)


if __name__ == "__main__":
    main(smoke="--smoke" in sys.argv)
