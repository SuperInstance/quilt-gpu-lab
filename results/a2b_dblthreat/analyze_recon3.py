#!/usr/bin/env python3
"""A2B recon 3: discriminant double-threat class + matched single-threat controls."""
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


def threats(mine, occ):
    """[(col, row, [line names completed])] for immediate wins."""
    out = []
    for c in lc(occ):
        m, r = drop(occ, c)
        nm = mine | m
        ls = [n for n, L in LINES if (nm & L) == L]
        if ls:
            out.append((c, r, ls))
    return out


def stratify(t1, t2, r1, r2, c1, c2):
    """Verbatim strata: stacked-column / split-column / cross-quadrant."""
    v1 = t1.startswith("col")
    v2 = t2.startswith("col")
    if v1 and v2:
        return "stacked-column"
    q = lambda r, c: ((0 if r < 2 else 1), (0 if c < 2 else 1))
    row_half_diff = (r1 < 2) != (r2 < 2)
    col_half_diff = (c1 < 2) != (c2 < 2)
    if row_half_diff and col_half_diff:
        return "cross-quadrant"
    return "split-column"


def main():
    D = []       # >=2 threats (mission rule)
    Dstar = []   # discriminant: opp also has >=1 immediate win
    S = []       # single-threat controls (mover exactly 1 immediate win)
    for ln in open(A2):
        rec = json.loads(ln)
        a, b = masks(rec["board"])
        occ = a | b
        th = threats(a, occ)
        oth = threats(b, occ)
        if len(th) >= 2:
            t1, r1, _ = th[0]
            t2, r2, _ = th[1]
            s = stratify(th[0][2][0], th[1][2][0], r1, r2, t1, t2)
            row = dict(rec, strata=s, n_opp_threats=len(oth))
            D.append(row)
            if len(oth) >= 1:
                Dstar.append(row)
        if len(th) == 1:
            S.append(dict(rec, n_opp_threats=len(oth)))

    print("D  (>=2 mover threats, mission rule):", len(D))
    print("D* (discriminant: opp>=1 threat)   :", len(Dstar))
    print("S  (exactly 1 mover threat)        :", len(S))
    print()
    print("D strata :", collections.Counter(r["strata"] for r in D))
    print("D* strata:", collections.Counter(r["strata"] for r in Dstar))
    print()
    print("D  chance mean:", round(sum(len(r["opt"]) / r["n_legal"] for r in D) / len(D), 4))
    print("D* chance mean:", round(sum(len(r["opt"]) / r["n_legal"] for r in Dstar) / len(Dstar), 4))
    print("S  chance mean:", round(sum(len(r["opt"]) / r["n_legal"] for r in S) / len(S), 4))
    print()
    print("D* key hist (ply,n_legal,opp):",
          collections.Counter((r["ply"], r["n_legal"], r["n_opp_threats"]) for r in Dstar).most_common())
    # matching feasibility for D*: S boards with same (ply, n_legal, opp>=1)
    for flag in (True, False):
        keys = collections.Counter((r["ply"], r["n_legal"]) for r in S if (r["n_opp_threats"] >= 1) == flag)
        need = collections.Counter((r["ply"], r["n_legal"]) for r in Dstar if (r["n_opp_threats"] >= 1) == flag)
        ok = all(keys[k] >= n for k, n in need.items())
        print(f"match opp>={'1' if flag else '0'}: need={dict(need)} avail={dict(keys)} feasible={ok}")


if __name__ == "__main__":
    main()
