#!/usr/bin/env python3
"""A2B-DBLTHREAT recon: geometry of the >=2-threat boards inside A2's 66,297.

Read-only analysis. Prints the threat-pair taxonomy before any pre-registration.
"""
from __future__ import annotations

import json
import os
import collections

W = H = 4
HERE = os.path.dirname(os.path.abspath(__file__))
A2 = os.path.join(os.path.dirname(HERE), "a2_ga4444", "dataset.jsonl")


def bit(r, c):
    return 1 << (r * W + c)


LINES = []
for _r in range(H):
    LINES.append(("row%d" % _r, sum(bit(_r, _c) for _c in range(W))))
for _c in range(W):
    LINES.append(("col%d" % _c, sum(bit(_r, _c) for _r in range(H))))
LINES.append(("diag\\", sum(bit(_i, _i) for _i in range(W))))
LINES.append(("diag/", sum(bit(_i, W - 1 - _i) for _i in range(W))))
COLMASK = [sum(bit(_r, _c) for _r in range(H)) for _c in range(W)]


def has_line(s):
    for _n, L in LINES:
        if s & L == L:
            return True
    return False


def board_to_masks(board):
    a = b = 0
    for i, v in enumerate(board):
        if v == 1:
            a |= 1 << i
        elif v == -1:
            b |= 1 << i
    return a, b


def drop_cell(occ, c):
    for r in range(H):
        m = bit(r, c)
        if not (occ & m):
            return m, r
    return None, None


def legal_cols(occ):
    return [c for c in range(W) if (occ & COLMASK[c]) != COLMASK[c]]


def threat_lines(a, occ, c):
    """Lines completed by dropping p0's stone in column c (immediate win)."""
    m, r = drop_cell(occ, c)
    na = a | m
    return [(n, L) for n, L in LINES if (na & L) == L]


def main():
    n_threat = 0
    line_pair = collections.Counter()
    same_row = collections.Counter()
    col_adj = collections.Counter()
    quad = collections.Counter()
    threes = 0
    chance_hist = collections.Counter()
    chance_by_stratum = collections.defaultdict(list)
    ply_hist = collections.Counter()
    examples = collections.defaultdict(list)

    for ln in open(A2):
        rec = json.loads(ln)
        if rec["imm_wins"] < 2:
            continue
        n_threat += 1
        board = rec["board"]
        a, b = board_to_masks(board)
        occ = a | b
        tc = []
        for c in legal_cols(occ):
            tl = threat_lines(a, occ, c)
            if tl:
                tc.append((c, drop_cell(occ, c)[1], tl))
        assert len(tc) >= 2, (board, rec["imm_wins"])
        if len(tc) > 2:
            threes += 1
        (c1, r1, L1), (c2, r2, L2) = tc[0], tc[1]
        t1 = L1[0][0]
        t2 = L2[0][0]
        key = tuple(sorted([t1.split("0")[0].rstrip("\\/"), t2.split("0")[0].rstrip("\\/")]))
        line_pair[key] += 1
        same_row[r1 == r2] += 1
        col_adj[abs(c1 - c2)] += 1
        q = lambda r, c: (0 if r < 2 else 1) * 2 + (0 if c < 2 else 1)
        quad[(q(r1, c1), q(r2, c2))] += 1
        ch = len(rec["opt"]) / rec["n_legal"]
        chance_hist[round(ch, 2)] += 1
        ply_hist[rec["ply"]] += 1
        # candidate strata
        # stacked-column: both threats complete a VERTICAL line (two stacked columns)
        both_col = (t1.startswith("col") and t2.startswith("col"))
        cross_q = (q(r1, c1) != q(r2, c2)) and (q(r1, c1) % 2 != q(r2, c2) % 2) and (q(r1, c1) // 2 != q(r2, c2) // 2)
        if both_col:
            s = "stacked-column"
        elif cross_q:
            s = "cross-quadrant"
        else:
            s = "split-column"
        chance_by_stratum[s].append((ch, rec["n_legal"], rec["ply"]))
        if len(examples[s]) < 3:
            examples[s].append((board, rec["opt"], rec["n_legal"], round(ch, 3), [t1, t2]))

    print("n boards with imm_wins>=2:", n_threat, " (3-threat boards:", threes, ")")
    print("line-type pairs:", line_pair.most_common())
    print("same row:", dict(same_row))
    print("col distance:", dict(sorted(col_adj.items())))
    print("quadrant pairs:", quad.most_common())
    print("ply hist:", dict(sorted(ply_hist.items())))
    print("chance hist:", dict(sorted(chance_hist.items())))
    print()
    for s, rows in sorted(chance_by_stratum.items()):
        chs = [x[0] for x in rows]
        print(f"{s}: n={len(rows)} chance mean={sum(chs)/len(chs):.4f} "
              f"min={min(chs):.3f} max={max(chs):.3f} "
              f"n_legal={collections.Counter(x[1] for x in rows).most_common()} "
              f"ply={collections.Counter(x[2] for x in rows).most_common()}")
    print()
    for s in sorted(examples):
        print("---", s)
        for e in examples[s]:
            print("   ", e)


if __name__ == "__main__":
    main()
