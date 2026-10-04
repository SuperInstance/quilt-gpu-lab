#!/usr/bin/env python3
"""corr-floor-probe — discovery-floor prober for paired sign streams.

Lifted from experiments/d12q_cp_near_degenerate.py (proven 2026-10-02/03):
given N agents paired off, W parallel questions per step, correlation p and
noise eps between partners, how many observation steps T are needed before
simple max-|corr| discovery recovers the correct partner for >= --acc of
agents? That first T on the grid is the *discovery floor*; W*T_floor*|2p-1|
(1-2eps)^alpha is C_emp, comparable across (p, eps, W).

Stdlib-only (json, argparse, random). Deterministic per (seed, p, t, draw).

Usage:
  python tools/corr_floor_probe.py --p 0.45,0.5,0.55 \
      [--t-grid 5,10,...,800] [--n 32 --w 8 --eps 0.0 --draws 3 \
       --acc 0.9 --alpha 1.92 --seed 2718 --out receipt.json]
  python tools/corr_floor_probe.py --example     # tiny self-test

Worked example:
  python tools/corr_floor_probe.py --example
  -> {"floors": {"0.45": 10, "0.5": 10, "0.55": 5}, "C_emp": {...}}
  C_emp uses s=|2p-1|(1-2eps): at p=0.5 C_emp is 0 by construction — the
  |2p-1| scaling assumes the near-degenerate |2p-1| factor, while raw
  discoverability at p=0.5 depends on the stream construction. Compare
  C_emp only across p away from 0.5, or swap in your own null generator.

Exit codes: 0 receipt written; 2 bad args; 1 every requested p returned a
null floor (nothing measured — likely grid too small or acc bar too high).
"""
from __future__ import annotations

import argparse
import json
import random
import sys


def make_pairs(n, rng):
    perm = list(range(n))
    rng.shuffle(perm)
    partner = {}
    for i in range(0, n, 2):
        a, b = perm[i], perm[i + 1]
        partner[a] = b
        partner[b] = a
    return partner


def streams_for(rng, partner, n, p_corr, eps, t_obs, w):
    streams = {c: [[] for _ in range(w)] for c in range(n)}
    for _ in range(t_obs):
        seen = set()
        for a in partner:
            if a in seen:
                continue
            seen |= {a, partner[a]}
            b = partner[a]
            for q in range(w):
                base = 1 if rng.random() < 0.5 else -1
                if rng.random() < p_corr:
                    va = vb = base
                else:
                    va, vb = base, (1 if rng.random() < 0.5 else -1)
                if rng.random() < eps:
                    va = -va
                if rng.random() < eps:
                    vb = -vb
                streams[a][q].append(va)
                streams[b][q].append(vb)
    return streams


def signed_corr(streams, a, b):
    tot, n = 0.0, 0
    for sa, sb in zip(streams[a], streams[b]):
        n += len(sa)
        tot += sum(x * y for x, y in zip(sa, sb))
    return tot / n if n else 0.0


def discover(streams, n):
    return {a: max((c for c in range(n) if c != a),
                   key=lambda c: abs(signed_corr(streams, a, c)))
            for a in range(n)}


def floor_at_p(p, n, w, eps, t_values, draws, acc, seed):
    accs = {}
    for t in t_values:
        run = []
        for d in range(draws):
            r = random.Random(seed * 100000 + int(p * 1000) * 10 + t * 2 + d)
            partner = make_pairs(n, r)
            streams = streams_for(r, partner, n, p, eps, t, w)
            found = discover(streams, n)
            run.append(sum(found[c] == partner[c] for c in partner) / n)
        accs[t] = sum(run) / len(run)
    for t in t_values:
        if accs[t] >= acc:
            return t, accs
    return None, accs


def run_probe(p_list, n, w, eps, t_values, draws, acc, alpha, seed):
    floors, acc_grids, c_emp = {}, {}, {}
    for p in p_list:
        fl, accs = floor_at_p(p, n, w, eps, t_values, draws, acc, seed)
        floors[p] = fl
        acc_grids[p] = accs
        if fl is not None:
            s = abs(2 * p - 1) * (1 - 2 * eps)
            c_emp[p] = w * fl * s ** alpha
    return floors, acc_grids, c_emp


def parse_floats(s):
    return [float(x) for x in s.split(",") if x.strip()]


def main():
    ap = argparse.ArgumentParser(
        description="Paired-stream discovery-floor prober (d12q pattern).")
    ap.add_argument("--p", help="comma list of correlation values, e.g. 0.45,0.5,0.55")
    ap.add_argument("--t-grid", default="5,10,15,20,30,40,60,80,120,160,240,320,480,640,800",
                    help="comma list of observation-step grid points")
    ap.add_argument("--n", type=int, default=32, help="agent count (even)")
    ap.add_argument("--w", type=int, default=8, help="questions per step")
    ap.add_argument("--eps", type=float, default=0.0, help="flip noise prob")
    ap.add_argument("--draws", type=int, default=3, help="draws averaged per T")
    ap.add_argument("--acc", type=float, default=0.9, help="discovery accuracy bar")
    ap.add_argument("--alpha", type=float, default=1.92, help="C(p) exponent")
    ap.add_argument("--seed", type=int, default=2718)
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--example", action="store_true",
                    help="tiny self-test (p=0.45,0.5,0.55, small grid)")
    args = ap.parse_args()

    if args.example:
        args.p = "0.45,0.5,0.55"
        args.t_grid = "5,10,20,40,80,160,320"

    if not args.p:
        ap.error("--p is required (or use --example)")
    p_list = parse_floats(args.p)
    t_values = [int(t) for t in parse_floats(args.t_grid)]
    if args.n % 2:
        sys.exit(2)
    if not t_values:
        sys.exit(2)

    floors, acc_grids, c_emp = run_probe(
        p_list, args.n, args.w, args.eps, t_values, args.draws,
        args.acc, args.alpha, args.seed)

    out = {
        "tool": "corr-floor-probe",
        "seed": args.seed, "n": args.n, "w": args.w, "eps": args.eps,
        "draws": args.draws, "acc_bar": args.acc, "alpha": args.alpha,
        "t_grid": t_values,
        "floors": {str(p): floors[p] for p in p_list},
        "acc_grids": {str(p): {str(t): round(a, 4) for t, a in acc_grids[p].items()}
                      for p in p_list},
        "C_emp": {str(p): round(c_emp[p], 1) for p in c_emp},
    }
    text = json.dumps(out, indent=1)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    print(text)
    if all(floors[p] is None for p in p_list):
        print("NOTE: all floors null — widen T grid or lower --acc", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
