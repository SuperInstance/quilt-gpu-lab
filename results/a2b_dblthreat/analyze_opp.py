#!/usr/bin/env python3
"""A2B recon 2: what distinguishes the NON-degenerate double-threat boards?"""
from __future__ import annotations
import json, os, collections

W = H = 4
HERE = os.path.dirname(os.path.abspath(__file__))
A2 = os.path.join(os.path.dirname(HERE), "a2_ga4444", "dataset.jsonl")
bit = lambda r, c: 1 << (r * W + c)
COLMASK = [sum(bit(r, c) for r in range(H)) for c in range(W)]
LINES = []
for r in range(H):
    LINES.append(("row%d" % r, sum(bit(r, c) for c in range(W))))
for c in range(H):
    LINES.append(("col%d" % c, sum(bit(r, c) for r in range(H))))
LINES.append(("diag\\", sum(bit(i, i) for i in range(W))))
LINES.append(("diag/", sum(bit(i, W - 1 - i) for i in range(W))))


def has_line(s):
    return any((s & L) == L for _n, L in LINES)


def masks(board):
    a = b = 0
    for i, v in enumerate(board):
        if v == 1:
            a |= 1 << i
        elif v == -1:
            b |= 1 << i
    return a, b


def drop(occ, c):
    for r in range(H):
        if not (occ & bit(r, c)):
            return bit(r, c), r
    return None, None


def lc(occ):
    return [c for c in range(W) if (occ & COLMASK[c]) != COLMASK[c]]


def imm(mine, occ):
    out = []
    for c in lc(occ):
        m, r = drop(occ, c)
        if has_line(mine | m):
            out.append(c)
    return out


def main():
    tab = collections.Counter()
    det = collections.Counter()
    for ln in open(A2):
        rec = json.loads(ln)
        if rec["imm_wins"] < 2:
            continue
        a, b = masks(rec["board"])
        occ = a | b
        o = len(imm(b, occ))            # opponent's immediate wins
        ch = len(rec["opt"]) / rec["n_legal"]
        tab[(o, round(ch, 2))] += 1
        if o >= 1:
            det[(rec["ply"], rec["n_legal"], round(ch, 2))] += 1
    print("rows=opp_imm_wins, cols=chance")
    print(f"{'opp':>4} | " + " ".join(f"{c:>5}" for c in ["0.5", "0.67", "1.0"]))
    for o in sorted({k[0] for k in tab}):
        print(f"{o:>4} | " + " ".join(f"{tab[(o,c)]:>5}" for c in [0.5, 0.67, 1.0]))
    print()
    print("non-degenerate (chance<1) with opp threats:", sum(v for k, v in tab.items() if k[1] < 1.0 and k[0] >= 1))
    print("non-degenerate total:", sum(v for k, v in tab.items() if k[1] < 1.0))
    print("details (ply,n_legal,chance) for opp>=1:", det.most_common())


if __name__ == "__main__":
    main()
