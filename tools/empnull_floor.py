#!/usr/bin/env python3
"""empnull-floor — empirical-null discovery-floor prober (D12ah pattern).

Pattern lifted PROVEN from experiments/d12ah_empirical_null_dip.py (booked
2026-10-09: Monte-Carlo the ACTUAL estimator under the null — no Gaussian
assumption, no variance dial k — and the k_eff(p) dip vanished; all 16 cells
covered within 2x). The idealized-Gaussian null is a modeling choice that can
manufacture real-looking physics; the empirical null cannot.

Given (p, eps) cells, for each T on a grid:
  - null draws:  |corr| of independent +-1 stream pairs (pooled flat centered
    cosine, the D12u4 estimator verbatim)
  - partner draws: |corr| of true (p, eps) copy-branch pairs
  - per-pair success prob = F_n(|x_partner|)^n_nulls  (beat the max of
    n_nulls nulls; ECDF power), P_succ = mean over partners
  - floor = smallest T with P_succ >= bar
Grid-edge / never-passing floors book PINNED_LOW / NEVER honestly (floor_scan
convention) — a floor at the grid edge is a quantized bound, not a measurement.

Optional gate: supplied harness floors must satisfy every model/harness ratio
within [--lo, --hi] (default 0.5..2.0, D12ah G1 band); any ratio outside, or
any PINNED/NEVER cell, books FAIL. Degenerate p=0.5 (signal s=0) books
FAIL honestly at cell level (floor NEVER) instead of failing loud — it is a
measurement outcome, not an input error. Stdlib-only, seeded, deterministic,
fail-loud rc=2, exit 0=KEEP / 1=FAIL, one JSON receipt.

Usage:
  python tools/empnull_floor.py --cells 0.3,0 0.4,0.05 --floors 20,20 \
      [--t-grid 8,10,12,15,20,25 --w 8 --n-nulls 32 --samples 200 \
       --bar 0.9 --lo 0.5 --hi 2.0 --seed 2718 --out r.json]
  python tools/empnull_floor.py --example     # tiny worked example
  python tools/empnull_floor.py --selftest    # 6-pin battery

Worked example (docstring = contract):
  Cells (0.3, eps 0.0) and (0.4, eps 0.0), W=8, harness floors 20 and 15:
  the empirical-null MC floors land within 2x of both -> KEEP rc=0. Feed a
  tampered harness floor (2 instead of 15) and the ratio gate books FAIL rc=1.
"""
import argparse
import json
import math
import random
import sys
import time


# ---------------- estimator (D12u4 verbatim, scalar pair version) ----------

def pair_streams(n, T, W, p, eps, partner, rng):
    """n pairs of +-1 streams (n x T x W); copy-branch pairing when partner."""
    tops, bots = [], []
    for _ in range(n):
        top = [1 if rng.random() < 0.5 else -1 for _ in range(T * W)]
        if partner:
            bot = [t if rng.random() < p else (1 if rng.random() < 0.5 else -1)
                   for t in top]
        else:
            bot = [1 if rng.random() < 0.5 else -1 for _ in range(T * W)]
        if eps > 0:
            top = [-t if rng.random() < eps else t for t in top]
            bot = [-b if rng.random() < eps else b for b in bot]
        tops.append(top)
        bots.append(bot)
    return tops, bots


def corr_flat(x, y):
    """Pooled flat centered cosine, absolute value (one pair)."""
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    num = dot = 0.0
    nfx = nfy = 0.0
    for a, b in zip(x, y):
        da, db = a - mx, b - my
        num += da * db
        nfx += da * da
        nfy += db * db
    denom = math.sqrt(nfx) * math.sqrt(nfy)
    if denom == 0:
        return 0.0
    return abs(num / denom)


def ecdf_at(sorted_vals, x):
    """F(x) for an empirical CDF."""
    lo, hi = 0, len(sorted_vals)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_vals[mid] <= x:
            lo = mid + 1
        else:
            hi = mid
    return lo / len(sorted_vals)


# ---------------- core ----------------------------------------------------

def floor_for_cell(p, eps, t_grid, W, n_nulls, samples, bar, rng):
    """Empirical-null MC floor for one (p, eps) cell. Returns (floor, flag, per-T)."""
    per_t = []
    floor = None
    for T in t_grid:
        nulls = sorted(
            corr_flat(a, b)
            for a, b in zip(*pair_streams(samples, T, W, 0.0, 0.0, False, rng))
        )
        partners = [
            corr_flat(a, b)
            for a, b in zip(*pair_streams(samples, T, W, p, eps, True, rng))
        ]
        p_succ = sum(ecdf_at(nulls, x) ** n_nulls for x in partners) / len(partners)
        per_t.append({"T": T, "p_succ": round(p_succ, 6)})
        if floor is None and p_succ >= bar:
            floor = T
    if floor is None:
        flag = "NEVER" if per_t[-1]["p_succ"] < bar * 0.5 else "PINNED_LOW"
        return None, flag, per_t
    if floor == t_grid[-1] and per_t[-2]["p_succ"] < bar:
        return floor, "PINNED_LOW", per_t
    return floor, "RESOLVED", per_t


def run(cells, floors, t_grid, W, n_nulls, samples, bar, lo, hi, seed):
    t0 = time.time()
    cells = [tuple(float(v) for v in c.split(",")) for c in cells]
    if floors is not None:
        floors = [int(v) for v in floors]
        if len(floors) != len(cells):
            raise ValueError(f"--floors count {len(floors)} != cells {len(cells)}")
    if not cells:
        raise ValueError("no cells given")
    if any(not (0.0 <= p <= 1.0) or eps < 0 for p, eps in cells):
        raise ValueError("cells must have p in [0,1], eps >= 0")
    if len(t_grid) < 2 or any(t <= 0 for t in t_grid):
        raise ValueError("t-grid needs >= 2 positive T values")
    if samples < 50 or n_nulls < 2:
        raise ValueError("samples >= 50 and n_nulls >= 2 required for a usable ECDF")
    if not (0.0 < bar <= 1.0) or not (0.0 < lo < hi):
        raise ValueError("need 0<bar<=1 and 0<lo<hi")

    rows, gate_fail = [], []
    for i, (p, eps) in enumerate(cells):
        # deterministic independent stream per cell
        rng = random.Random(seed * 1000003 + i)
        floor, flag, per_t = floor_for_cell(
            p, eps, t_grid, W, n_nulls, samples, bar, rng)
        row = {"p": p, "eps": eps, "floor": floor, "flag": flag, "per_t": per_t}
        if floors is not None:
            hf = floors[i]
            row["harness_floor"] = hf
            if floor is None:
                row["ratio"] = None
                gate_fail.append(f"cell ({p},{eps}) floor {flag} cannot gate ratio")
            else:
                ratio = floor / hf
                row["ratio"] = round(ratio, 4)
                if not (lo <= ratio <= hi):
                    gate_fail.append(
                        f"cell ({p},{eps}) ratio {ratio:.3f} outside [{lo},{hi}]")
        rows.append(row)

    verdict = "FAIL" if gate_fail else "KEEP"
    receipt = {
        "tool": "empnull-floor",
        "verdict": verdict,
        "why": gate_fail or ["all gated cells within band" if floors is not None
                             else "floors measured (no harness gate given)"],
        "seed": seed, "W": W, "n_nulls": n_nulls, "samples": samples,
        "bar": bar, "band": [lo, hi],
        "cells": rows,
        "wall_s": round(time.time() - t0, 3),
    }
    return receipt, (0 if verdict == "KEEP" else 1)


# ---------------- selftest -------------------------------------------------

def selftest():
    pins = []
    # Pin 1 (positive control): strong signal p=0.3 resolves a small floor.
    r, rc = run(["0.3,0"], ["20"], [4, 6, 8, 10, 12, 15, 20, 25],
                W=8, n_nulls=16, samples=120, bar=0.9, lo=0.5, hi=2.0, seed=7)
    pins.append(("strong-signal KEEP", rc == 0 and r["cells"][0]["flag"] == "RESOLVED", r["cells"][0]["floor"]))
    # Pin 2 (honest book): degenerate p=0.5 never crosses -> NEVER, FAIL rc=1.
    # Pin 2 (honest book): zero-signal cell (copy-prob p=0.0 = independent,
    # the d12ah copy-branch convention) is indistinguishable from the nulls
    # -> NEVER, FAIL rc=1. (p=0.5 under this convention has signal 0.5 —
    # first run of the selftest pinned the wrong convention; gate untouched.)
    r, rc = run(["0.0,0"], ["999"], [4, 8, 12], W=8, n_nulls=8, samples=60,
                bar=0.9, lo=0.5, hi=2.0, seed=7)
    pins.append(("p=0 NEVER books FAIL", rc == 1 and r["cells"][0]["flag"] == "NEVER", r["cells"][0]["flag"]))
    # Pin 3 (tamper RED): corrupted harness floor trips the ratio gate.
    r, rc = run(["0.3,0"], ["3"], [4, 6, 8, 10, 12, 15, 20, 25],
                W=8, n_nulls=16, samples=120, bar=0.9, lo=0.5, hi=2.0, seed=7)
    pins.append(("tampered-floor ratio FAIL", rc == 1 and any("outside" in w for w in r["why"]), r["why"]))
    # Pin 4 (determinism): same seed -> identical floors.
    a, _ = run(["0.4,0.05"], None, [4, 6, 8, 10, 12, 15], W=8, n_nulls=8,
               samples=60, bar=0.9, lo=0.5, hi=2.0, seed=11)
    b, _ = run(["0.4,0.05"], None, [4, 6, 8, 10, 12, 15], W=8, n_nulls=8,
               samples=60, bar=0.9, lo=0.5, hi=2.0, seed=11)
    pins.append(("determinism", a["cells"][0]["floor"] == b["cells"][0]["floor"]
                 and a["cells"][0]["per_t"] == b["cells"][0]["per_t"], a["cells"][0]["floor"]))
    # Pin 5 (noise hurts, J1 convention): eps=0.2 floor >= eps=0.0 floor.
    r0, _ = run(["0.3,0.0"], None, [4, 6, 8, 10, 12, 15, 20], W=8, n_nulls=8,
                samples=60, bar=0.9, lo=0.5, hi=2.0, seed=5)
    r2, _ = run(["0.3,0.2"], None, [4, 6, 8, 10, 12, 15, 20], W=8, n_nulls=8,
                samples=60, bar=0.9, lo=0.5, hi=2.0, seed=5)
    pins.append(("noise hurts", r2["cells"][0]["floor"] is None
                 or r2["cells"][0]["floor"] >= r0["cells"][0]["floor"],
                 (r0["cells"][0]["floor"], r2["cells"][0]["floor"])))
    # Pin 6 (fail-loud): bad p books rc=2, never crashes raw.
    try:
        run(["1.5,0"], None, [4, 8], W=8, n_nulls=8, samples=60, bar=0.9,
            lo=0.5, hi=2.0, seed=1)
        pins.append(("bad-p fail-loud", False, "no raise"))
    except ValueError:
        pins.append(("bad-p fail-loud", True, "ValueError"))
    ok = sum(1 for _, passed, _ in pins if passed)
    print(json.dumps({"selftest": f"{ok}/{len(pins)}",
                      "pins": [{"name": n, "pass": p, "note": v} for n, p, v in pins]}, indent=1))
    return 0 if ok == len(pins) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1],
                                 epilog="see module docstring for the worked example")
    ap.add_argument("--cells", nargs="+", metavar="P,EPS",
                    help="cells as p,eps pairs, e.g. 0.3,0 0.4,0.05")
    ap.add_argument("--floors", nargs="+", metavar="T",
                    help="optional harness floors (measured) to gate against")
    ap.add_argument("--t-grid", type=lambda s: [int(v) for v in s.split(",")],
                    default=[4, 6, 8, 10, 12, 15, 20, 25, 30, 40])
    ap.add_argument("--w", type=int, default=8)
    ap.add_argument("--n-nulls", type=int, default=32)
    ap.add_argument("--samples", type=int, default=200)
    ap.add_argument("--bar", type=float, default=0.9)
    ap.add_argument("--lo", type=float, default=0.5)
    ap.add_argument("--hi", type=float, default=2.0)
    ap.add_argument("--seed", type=int, default=2718)
    ap.add_argument("--out", help="write JSON receipt here too")
    ap.add_argument("--example", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if args.example:
        args.cells = ["0.3,0", "0.4,0"]
        args.floors = ["20", "15"]
        args.t_grid = [4, 6, 8, 10, 12, 15, 20, 25]
        args.n_nulls = 16
        args.samples = 120

    if not args.cells:
        ap.error("--cells required (or --example / --selftest)")
    try:
        receipt, rc = run(args.cells, args.floors, args.t_grid, args.w,
                          args.n_nulls, args.samples, args.bar, args.lo,
                          args.hi, args.seed)
    except ValueError as e:
        print(json.dumps({"tool": "empnull-floor", "verdict": "FAIL-INPUT",
                          "why": str(e)}))
        sys.exit(2)
    out = json.dumps(receipt, indent=1)
    if args.out:
        with open(args.out, "w") as f:
            f.write(out + "\n")
    print(out)
    sys.exit(rc)


if __name__ == "__main__":
    main()
