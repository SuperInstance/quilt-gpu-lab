#!/usr/bin/env python3
"""A2-ga4444-4x4 — composition + capacity on 4x4 four-in-a-row (Gale's game, gravity).

Lane A2-HARVEST (quilt-gpu-lab), worklist item A2 (fleet-triage/docs/RTX4050-WORKLIST.md).
Pre-registration: proposals/runs/A2-ga4444-4x4.md (written BEFORE this file's measured run).

WHAT THIS IS. One smoke arm today: a tiny MLP on exact set-valued minimax labels at 4x4,
with the matched linear/additive arm as the frozen contrast the gate needs, 5-fold
board-disjoint CV, chance COMPUTED not assumed. Full arm matrix (convergence control,
capacity sweep, seeds) is the follow-up.

GAME CHOICE (recon, recorded in the prereg). The repo ships two move spaces:
  * ga4444.py `legal_moves` — FREE placement (a stone may land in a gap); its reachable
    non-terminal graph exceeds 8e6 states (>8M, measured) and ga4444.py caps labels at
    MAX_PLY=9. NOT "complete ground truth" in a session.
  * gt4444.c — GRAVITY (column drop). Its `walk` prunes with `return` where `continue`
    belongs, so its 3,338-row export is an INCOMPLETE walk, but its VALUES are exact.
The reachable non-terminal GRAVITY graph is 139,625 states — enumerable exactly. This lane
uses the gravity game (the "rung with complete ground truth") and builds its OWN complete
enumeration, using the repo's C solver only as a differential control (verify.py shape).

RULES HONOURED. Four device's §0 rules: exact labels (rule 3), variance reported (rule 2),
control by a different path (rule 5 — C --probe vs this Python solver), seed pinned
(rule 7), device string recorded (rule 1).

No shell=True anywhere. Data-gen shards are list-form subprocesses (fleet Critical Path).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import time
from functools import lru_cache

W = H = 4
SEED = 2718
HERE = os.path.dirname(os.path.abspath(__file__))
SHARDS = os.path.join(HERE, "shards")
DATASET = os.path.join(HERE, "dataset.jsonl")
C_SOLVER = os.environ.get("A2_C_SOLVER", "/tmp/gt4444")

# ---------------------------------------------------------------- game (gravity)
def bit(r: int, c: int) -> int:
    return 1 << (r * W + c)


LINES = []
for _r in range(H):
    LINES.append(sum(bit(_r, _c) for _c in range(W)))
for _c in range(W):
    LINES.append(sum(bit(_r, _c) for _r in range(H)))
LINES.append(sum(bit(_i, _i) for _i in range(W)))
LINES.append(sum(bit(_i, W - 1 - _i) for _i in range(W)))
COLMASK = [sum(bit(_r, _c) for _r in range(H)) for _c in range(W)]
FULL = (1 << (W * H)) - 1


def has_line(s: int) -> bool:
    for L in LINES:
        if s & L == L:
            return True
    return False


def drop_cell(occ: int, c: int):
    """Lowest empty cell bit in column c (gravity), or None if full."""
    for r in range(H):
        m = bit(r, c)
        if not (occ & m):
            return m
    return None


def legal_cols(occ: int):
    return [c for c in range(W) if (occ & COLMASK[c]) != COLMASK[c]]


def popcount(x: int) -> int:
    return bin(x).count("1")


def to_board(a: int, b: int):
    """16-tuple, +1 p0 / -1 p1 / 0 empty, row-major. Mover = p0 iff |p0|==|p1|."""
    return tuple(1 if (a >> i) & 1 else (-1 if (b >> i) & 1 else 0) for i in range(W * H))


def board_to_masks(board):
    a = b = 0
    for i, v in enumerate(board):
        if v == 1:
            a |= 1 << i
        elif v == -1:
            b |= 1 << i
    return a, b


def fnv1a64(data: bytes) -> int:
    h = 0xCBF29CE484222325
    for byte in data:
        h ^= byte
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


# ------------------------------------------------------- exact memoized solver
def make_solver():
    @lru_cache(maxsize=None)
    def value(a: int, b: int) -> int:
        """Value from the side-to-move's POV: +1 win, 0 draw, -1 loss. FULL depth."""
        occ = a | b
        turn_is_p0 = popcount(a) == popcount(b)
        # Did the player who just moved win? (they are the one NOT to move)
        if turn_is_p0:
            if has_line(b):
                return -1
            me = a
        else:
            if has_line(a):
                return -1
            me = b
        mv = legal_cols(occ)
        if not mv:
            return 0
        best = -1
        for c in mv:
            m = drop_cell(occ, c)
            if turn_is_p0:
                v = -value(a | m, b)
            else:
                v = -value(a, b | m)
            if v > best:
                best = v
            if best == 1:
                break
        return best

    return value


def reachable_states():
    """Complete BFS over the reachable non-terminal gravity graph. Returns sorted list."""
    seen = {(0, 0)}
    frontier = [(0, 0)]
    while frontier:
        nxt = []
        for (a, b) in frontier:
            occ = a | b
            turn_is_p0 = popcount(a) == popcount(b)
            for c in legal_cols(occ):
                m = drop_cell(occ, c)
                if turn_is_p0:
                    na, nb = a | m, b
                    if has_line(na):
                        continue
                else:
                    na, nb = a, b | m
                    if has_line(nb):
                        continue
                s = (na, nb)
                if s not in seen:
                    seen.add(s)
                    nxt.append(s)
        frontier = nxt
    return sorted(seen)


# --------------------------------------------------------------- labels
def label_board(value_fn, a: int, b: int):
    """Exact set-valued optimal moves for the p0-to-move board (a,b)."""
    occ = a | b
    per = {}
    for c in legal_cols(occ):
        m = drop_cell(occ, c)
        per[c] = -value_fn(a | m, b)  # child: p1 to move
    best = max(per.values())
    opt = sorted(c for c, v in per.items() if v == best)
    return opt, per, best


def immediate_wins_p0(a: int, b: int):
    """Columns where dropping NOW makes 4 for p0 (gravity, so this is unblockable)."""
    occ = a | b
    out = []
    for c in legal_cols(occ):
        m = drop_cell(occ, c)
        if has_line(a | m):
            out.append(c)
    return out


def own_threat_lines(a: int):
    """DEF-A count: lines with exactly 3 own stones + 1 empty (dead lines included)."""
    n = 0
    for L in LINES:
        if popcount(a & L) == 3 and popcount(L & ~a & FULL) == 1:
            n += 1
    return n


# ------------------------------------------------------- data-gen shard (subprocess)
def gen_shard(idx: int, nshards: int):
    """Solve the boards assigned to this shard and stream them to a JSONL checkpoint."""
    os.makedirs(SHARDS, exist_ok=True)
    value_fn = make_solver()
    states = reachable_states()
    # our-turn = p0 to move; EXCLUDE terminal boards (no legal drop -> no decision to label)
    our = [(a, b) for (a, b) in states
           if popcount(a) == popcount(b) and legal_cols(a | b)]
    our.sort()
    out = os.path.join(SHARDS, f"shard-{idx}.jsonl")
    rows = 0
    with open(out, "w") as f:
        for i, (a, b) in enumerate(our):
            if i % nshards != idx:
                continue
            board = to_board(a, b)
            opt, per, best = label_board(value_fn, a, b)
            n_legal = len(legal_cols(a | b))
            iw = immediate_wins_p0(a, b)
            rec = {
                "board": board,
                "opt": opt,
                "n_legal": n_legal,
                "value": best,
                "imm_wins": len(iw),
                "defA_threats": own_threat_lines(a),
                "ply": popcount(a) + popcount(b),
                "fnv": fnv1a64(bytes([v + 1 for v in board])),
            }
            f.write(json.dumps(rec) + "\n")
            rows += 1
    print(f"[shard {idx}/{nshards}] wrote {rows} rows -> {out}", flush=True)


def merge_shards(nshards: int):
    recs = []
    for i in range(nshards):
        p = os.path.join(SHARDS, f"shard-{i}.jsonl")
        with open(p) as f:
            for ln in f:
                recs.append(json.loads(ln))
    seen = set()
    uniq = []
    for r in recs:
        k = tuple(r["board"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    uniq.sort(key=lambda r: tuple(r["board"]))
    with open(DATASET, "w") as f:
        for r in uniq:
            f.write(json.dumps(r) + "\n")
    return uniq


# --------------------------------------------------------------- training
def train_arm(recs, fold_of, arm: str, epochs: int, lr: float, device: str):
    import torch
    import torch.nn as nn
    import numpy as np

    torch.manual_seed(SEED)
    np.random.seed(SEED)

    X = torch.tensor([r["board"] for r in recs], dtype=torch.float32)
    # legal mask: a column is legal iff not full; recompute from board
    Lg = torch.zeros((len(recs), W), dtype=torch.bool)
    for i, r in enumerate(recs):
        occ = sum((1 << j) for j, v in enumerate(r["board"]) if v != 0)
        for c in range(W):
            Lg[i, c] = (occ & COLMASK[c]) != COLMASK[c]
    folds = torch.tensor([fold_of(r["fnv"]) for r in recs], dtype=torch.long)
    # target matrix: T[i,c] = 1 iff column c is an exact optimal move for board i
    T = torch.zeros((len(recs), W), dtype=torch.bool)
    for i, r in enumerate(recs):
        for c in r["opt"]:
            T[i, c] = True

    if arm == "mlp":
        net = nn.Sequential(nn.Linear(W * H, 64), nn.ReLU(), nn.Linear(64, W))
    else:
        net = nn.Linear(W * H, W)
    net = net.to(device)
    opt = torch.optim.Adam(net.parameters(), lr=lr)

    def masked_logsoftmax(z, mask):
        neg = torch.finfo(z.dtype).min
        z = z.masked_fill(~mask, neg)
        return z - torch.logsumexp(z, dim=1, keepdim=True)

    def setval_loss(z, mask, tgt):
        ls = masked_logsoftmax(z, mask)
        neg = torch.finfo(ls.dtype).min
        return -ls.masked_fill(~tgt, neg).logsumexp(dim=1).mean()

    per_fold = {}
    for k in range(5):
        tr = (folds != k).nonzero(as_tuple=True)[0]
        te = (folds == k).nonzero(as_tuple=True)[0]
        net.train()
        torch.manual_seed(SEED + k)
        # fresh init per fold for a clean reading
        if arm == "mlp":
            for m in net.modules():
                if isinstance(m, nn.Linear):
                    nn.init.kaiming_uniform_(m.weight, nonlinearity="relu")
                    nn.init.zeros_(m.bias)
        else:
            nn.init.normal_(net.weight, 0, 0.1)
            nn.init.zeros_(net.bias)
        opt = torch.optim.Adam(net.parameters(), lr=lr)
        Xtr, Ltr, Ttr = X[tr].to(device), Lg[tr].to(device), T[tr].to(device)
        n = Xtr.shape[0]
        bs = 1024
        g = torch.Generator(device="cpu").manual_seed(SEED + k)
        for ep in range(epochs):
            perm = torch.randperm(n, generator=g)
            net.train()
            for s in range(0, n, bs):
                b = perm[s:s + bs]
                z = net(Xtr[b])
                loss = setval_loss(z, Ltr[b], Ttr[b])
                opt.zero_grad()
                loss.backward()
                opt.step()
        net.eval()
        with torch.no_grad():
            Xte, Lte = X[te].to(device), Lg[te].to(device)
            z = net(Xte)
            neg = torch.finfo(z.dtype).min
            pred = z.masked_fill(~Lte, neg).argmax(dim=1).cpu().numpy()
        res = {"n_test": int(te.numel()), "top1": {}, "chance": {}}
        recs_te = [recs[i] for i in te.tolist()]
        correct = np.array([pred[j] in recs_te[j]["opt"] for j in range(len(recs_te))])
        # partitions
        def frac(mask, name):
            m = np.array(mask)
            if m.sum() == 0:
                return
            res["top1"][name] = round(float(correct[m].mean()), 4)
            ch = np.mean([len(recs_te[j]["opt"]) / recs_te[j]["n_legal"]
                          for j in range(len(recs_te)) if m[j]])
            res["chance"][name] = round(float(ch), 4)
        frac([True] * len(recs_te), "overall")
        frac([r["imm_wins"] >= 2 for r in recs_te], "COMPOSED_B")
        frac([r["imm_wins"] <= 1 for r in recs_te], "SIMPLE_B")
        frac([r["defA_threats"] >= 2 for r in recs_te], "COMPOSED_A")
        frac([r["defA_threats"] <= 1 for r in recs_te], "SIMPLE_A")
        fr = {
            "COMPOSED_B": int(sum(1 for r in recs_te if r["imm_wins"] >= 2)),
            "COMPOSED_A": int(sum(1 for r in recs_te if r["defA_threats"] >= 2)),
        }
        res["n_partition"] = fr
        per_fold[k] = res
        print(f"[{arm}] fold {k}: top1={res['top1']} n={res['n_test']} "
              f"n_compB={fr['COMPOSED_B']} n_compA={fr['COMPOSED_A']}", flush=True)
    return per_fold


# --------------------------------------------------------------- orchestration
def orchestrate():
    t0 = time.time()
    nshards = 5
    # --- parallel data-gen: one list-form subprocess per shard (never shell=True)
    procs = []
    for i in range(nshards):
        procs.append(subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--gen-shard", str(i), str(nshards)]))
    for p in procs:
        p.wait()
    recs = merge_shards(nshards)
    # --- hash the dataset (data provenance)
    with open(DATASET, "rb") as f:
        digest = fnv1a64(f.read())
    summary = {
        "n_boards": len(recs),
        "dataset_fnv1a64": hex(digest),
        "gen_seconds": round(time.time() - t0, 2),
        "ply_hist": {},
        "imm_wins_hist": {},
        "defA_hist": {},
        "mult_opt": 0,
    }
    for r in recs:
        summary["ply_hist"][str(r["ply"])] = summary["ply_hist"].get(str(r["ply"]), 0) + 1
        summary["imm_wins_hist"][str(r["imm_wins"])] = summary["imm_wins_hist"].get(str(r["imm_wins"]), 0) + 1
        summary["defA_hist"][str(r["defA_threats"])] = summary["defA_hist"].get(str(r["defA_threats"]), 0) + 1
        if len(r["opt"]) > 1:
            summary["mult_opt"] += 1
    summary["mult_opt_frac"] = round(summary["mult_opt"] / max(1, len(recs)), 4)
    summary["chance_overall"] = round(sum(len(r["opt"]) / r["n_legal"] for r in recs) / max(1, len(recs)), 4)
    with open(os.path.join(HERE, "dataset_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))

    # --- differential control vs the repo's C solver (rule 5: different path)
    control = {"ran": False}
    if os.path.exists(C_SOLVER):
        rng = random.Random(SEED)
        sample = rng.sample(recs, min(500, len(recs)))
        # C layout: column-major, STRIDE=5. Convert row-major (r,c) -> (c*5+r)
        def cmask(a, b):
            mp = 0
            for src in (a, b):
                for r in range(H):
                    for c in range(W):
                        if (src >> (r * W + c)) & 1:
                            mp |= 1 << (c * 5 + r)
            return mp

        def cpos_p0(a, b, p0_to_move):
            # C reports from the POV of the PLAYER TO MOVE; we feed pos = to-move stones
            mp = 0
            src = a if p0_to_move else b
            for r in range(H):
                for c in range(W):
                    if (src >> (r * W + c)) & 1:
                        mp |= 1 << (c * 5 + r)
            return mp

        lines = []
        for r in sample:
            a, b = board_to_masks(r["board"])
            lines.append(f"{cmask(a, b)} {cpos_p0(a, b, True)}")
        inp = "\n".join(lines) + "\n"
        try:
            pr = subprocess.run([C_SOLVER, "--probe"], input=inp, capture_output=True,
                                text=True, timeout=600)
            cv = [int(x) for x in pr.stdout.split()]
            agree = sum(1 for r, v in zip(sample, cv) if r["value"] == v)
            control = {"ran": True, "n": len(sample), "agreements": agree,
                       "disagreements": len(sample) - agree}
        except Exception as e:  # noqa: BLE001
            control = {"ran": False, "error": repr(e)}
    print("control:", control)
    with open(os.path.join(HERE, "control.json"), "w") as f:
        json.dump(control, f, indent=2)

    return recs, summary, control


def fold_of(fnv: int) -> int:
    return (fnv >> 32) % 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen-shard", nargs=2, type=int)
    ap.add_argument("--train", action="store_true")
    ap.add_argument("--arm", default="mlp")
    ap.add_argument("--epochs", type=int, default=120)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()

    if args.gen_shard:
        gen_shard(args.gen_shard[0], args.gen_shard[1])
        return

    if args.train:
        recs = [json.loads(l) for l in open(DATASET)]
        import torch
        dev = args.device if torch.cuda.is_available() else "cpu"
        info = {
            "torch": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device_used": dev,
            "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
            "arm": args.arm, "epochs": args.epochs, "lr": args.lr, "seed": SEED,
            "n_boards": len(recs),
        }
        print("DEVICE:", json.dumps(info))
        per_fold = train_arm(recs, fold_of, args.arm, args.epochs, args.lr, dev)
        out = os.path.join(HERE, f"smoke_{args.arm}_metrics.json")
        with open(out, "w") as f:
            json.dump({"info": info, "per_fold": per_fold}, f, indent=2)
        print("wrote", out)
        return

    orchestrate()


if __name__ == "__main__":
    main()
