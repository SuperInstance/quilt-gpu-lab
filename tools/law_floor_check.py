#!/usr/bin/env python3
"""law-floor-check — check measured sample-size floors against a scaling-law
bound, with the D12o gate battery (pattern lifted from
experiments/d12o_law_p_generalization.py).

The law (validated in D12n/D12o): reaching a target accuracy on a
correlation-discovery task needs W*T <= C / s^alpha samples, where
s = (2p-1)*(1-2*eps) is the coupling signal (p = partner-agreement
probability, eps = flip noise). p=0.5 is the degenerate point (s=0,
discovery impossible by construction) — this tool fails loud there instead
of dividing by zero, echoing the ZeroDivisionError lesson from D12o draft 1.

Gates (all must pass for KEEP):
  G1  bound coverage: W*T_floor <= C/s^alpha for >= --min-coverage of cells
      with a measured floor
  G1b non-vacuous looseness: mean(measured W*T / bound) >= --min-ratio
  G2  monotonicity: floors non-increasing in W at fixed eps (0 inversions)

Inputs: either --floors '{"W=4,eps=0.0": 10, ...}' (null = never reached
the bar within budget, counts as infinity) or --results <d12o-style JSON>
plus --acc-bar to derive floors from the acc grid.

Receipt: one JSON, verdict KEEP/KILL or FAIL-INPUT, every input echoed,
keys sorted. Exit codes: 0 = verdict computed (KEEP or KILL are both honest
first-class results), 2 = FAIL-INPUT (loud, never silent).

Worked example (real D12o p=0.7 run):
    python tools/law_floor_check.py --c 600 --alpha 1.92 --p 0.7 \
        --eps 0.0,0.05,0.1,0.2 --w 4,8,16 \
        --floors '{"W=4,eps=0.0": 10, "W=4,eps=0.05": 10, "W=4,eps=0.1": 25,
                   "W=4,eps=0.2": 50, "W=8,eps=0.0": 10, "W=8,eps=0.05": 10,
                   "W=8,eps=0.1": 10, "W=8,eps=0.2": 25, "W=16,eps=0.0": 10,
                   "W=16,eps=0.05": 10, "W=16,eps=0.1": 10, "W=16,eps=0.2": 25}'
    -> verdict KEEP, coverage 1.0, mean ratio ~0.026

Selftest (pins real D12o receipts, plus fail-loud cases):
    python tools/law_floor_check.py --selftest

Selftest pins: KEEP on the exact D12o p=0.7 floors, bound value matches
d12o's receipt (W=4,eps=0.0 bound ~3484.9), KILL when coverage drops below
0.8, FAIL-INPUT rc=2 on p=0.5, FAIL-INPUT on missing floor keys.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone


def fail_input(msg: str) -> "None":
    print(json.dumps({"verdict": "FAIL-INPUT", "error": msg}, sort_keys=True))
    sys.exit(2)


def signal(p: float, eps: float) -> float:
    """s = (2p-1)*(1-2eps); fail loud at the degenerate p=0.5."""
    if abs(p - 0.5) < 1e-12:
        fail_input("p=0.5 is degenerate: (2p-1)=0, discovery impossible by construction")
    return (2 * p - 1) * (1 - 2 * eps)


def bound(c_const: float, alpha: float, s: float) -> float:
    if abs(s) < 1e-12:
        fail_input("signal s=0 (noise or degenerate p): bound is infinite")
    return c_const / abs(s) ** alpha


def derive_floors(results: dict, acc_bar: float) -> dict:
    """Extract T_floors from a d12o-style results JSON acc_grid.

    grid keys look like "W|eps|t"; floor per (W,eps) = smallest t with
    acc >= acc_bar, else None.
    """
    grid = results.get("acc_grid")
    if not isinstance(grid, dict) or not grid:
        fail_input("results JSON has no non-empty acc_grid")
    cells: dict = {}
    for key, acc in grid.items():
        parts = key.split("|")
        if len(parts) != 3:
            fail_input(f"bad acc_grid key: {key!r}")
        w_s, eps_s, t_s = parts
        try:
            w, eps, t = int(w_s), float(eps_s), int(t_s)
        except ValueError:
            fail_input(f"unparseable acc_grid key: {key!r}")
        cells.setdefault((w, eps), []).append((t, acc))
    floors = {}
    for (w, eps), obs in sorted(cells.items()):
        obs.sort()
        floors[f"W={w},eps={eps}"] = next(
            (t for t, a in obs if a >= acc_bar), None)
    return floors


def check_law(c_const, alpha, p, w_values, eps_values, floors,
              min_coverage=0.8, min_ratio=0.02) -> dict:
    """Run the G1/G1b/G2 gate battery. Caller validates inputs are numeric."""
    w_values = sorted(w_values)
    details = {}
    covered = cells_with_floor = 0
    for w in w_values:
        for e in eps_values:
            key = f"W={w},eps={e}"
            if key not in floors:
                fail_input(f"missing floor for cell {key}")
            fl = floors[key]
            if fl is not None and (not isinstance(fl, int) or fl <= 0):
                fail_input(f"floor for {key} must be a positive int or null, got {fl!r}")
            b = bound(c_const, alpha, signal(p, e))
            if fl is None:
                details[key] = {"floor": None, "wt": None, "bound": round(b, 1), "ok": False}
                continue
            cells_with_floor += 1
            wt = w * fl
            ok = wt <= b
            covered += ok
            details[key] = {"floor": fl, "wt": wt, "bound": round(b, 1),
                            "ratio": round(wt / b, 5), "ok": ok}

    g1 = cells_with_floor > 0 and covered / cells_with_floor >= min_coverage
    ratios = [d["ratio"] for d in details.values() if d["floor"] is not None]
    mean_ratio = sum(ratios) / len(ratios) if ratios else 0.0
    g1b = mean_ratio >= min_ratio

    inversions = 0
    for e in eps_values:
        vals = [floors.get(f"W={w},eps={e}") for w in w_values]
        vals = [10 ** 9 if v is None else v for v in vals]
        inversions += sum(1 for i in range(len(vals) - 1) if vals[i] < vals[i + 1])
    g2 = inversions == 0

    return {
        "g1_bound_coverage": covered / cells_with_floor if cells_with_floor else 0.0,
        "g1_details": details,
        "g1b_mean_ratio": round(mean_ratio, 5),
        "g2_w_inversions": inversions,
        "gates": {"G1": g1, "G1b": g1b, "G2": g2},
        "verdict": "KEEP" if (g1 and g1b and g2) else "KILL",
    }


def _selftest() -> None:
    d12o_floors = {"W=4,eps=0.0": 10, "W=4,eps=0.05": 10, "W=4,eps=0.1": 25,
                   "W=4,eps=0.2": 50, "W=8,eps=0.0": 10, "W=8,eps=0.05": 10,
                   "W=8,eps=0.1": 10, "W=8,eps=0.2": 25, "W=16,eps=0.0": 10,
                   "W=16,eps=0.05": 10, "W=16,eps=0.1": 10, "W=16,eps=0.2": 25}
    ws, es = [4, 8, 16], [0.0, 0.05, 0.1, 0.2]

    # Pin 1: real D12o p=0.7 receipt -> KEEP
    out = check_law(600.0, 1.92, 0.7, ws, es, d12o_floors)
    assert out["verdict"] == "KEEP", out
    # Pin 2: bound matches d12o receipt exactly (W=4,eps=0.0 -> 3484.9)
    assert out["g1_details"]["W=4,eps=0.0"]["bound"] == 3484.9, out
    # Pin 3: KILL when coverage collapses (tiny C makes every cell violate)
    out2 = check_law(1.0, 1.92, 0.7, ws, es, d12o_floors)
    assert out2["verdict"] == "KILL" and not out2["gates"]["G1"], out2
    # Pin 4: KILL on monotonicity inversion (floor rises with W)
    bad = dict(d12o_floors)
    bad["W=8,eps=0.0"] = 25  # now 4:10, 8:25, 16:10 -> inversion
    out3 = check_law(600.0, 1.92, 0.7, ws, es, bad)
    assert out3["verdict"] == "KILL" and not out3["gates"]["G2"], out3
    # Pin 5: FAIL-INPUT rc=2 at degenerate p=0.5
    try:
        check_law(600.0, 1.92, 0.5, ws, es, d12o_floors)
        raise AssertionError("p=0.5 should fail loud")
    except SystemExit as e:
        assert e.code == 2
    # Pin 6: FAIL-INPUT on missing cell
    try:
        check_law(600.0, 1.92, 0.7, ws + [32], es, d12o_floors)
        raise AssertionError("missing cell should fail loud")
    except SystemExit as e:
        assert e.code == 2
    # Pin 7: derive_floors recovers d12o floors from a results JSON
    with open("results/d12o_law_p_generalization.json") as f:
        res = json.load(f)
    derived = derive_floors(res, res["acc_bar"])
    assert derived == d12o_floors, derived
    print(json.dumps({"selftest": "PASS", "pins": 7}, sort_keys=True))


def main() -> None:
    ap = argparse.ArgumentParser(
        description="check measured T floors against a C/s^alpha scaling-law "
                    "bound with the D12o G1/G1b/G2 gate battery")
    ap.add_argument("--c", type=float, default=600.0, help="law constant C (default 600)")
    ap.add_argument("--alpha", type=float, default=1.92, help="law exponent (default 1.92)")
    ap.add_argument("--p", type=float, help="partner-agreement probability (NOT 0.5)")
    ap.add_argument("--eps", help="noise levels, comma-separated (e.g. 0.0,0.05,0.1,0.2)")
    ap.add_argument("--w", help="window sizes W, comma-separated (e.g. 4,8,16)")
    ap.add_argument("--floors", help="JSON object {\"W=x,eps=y\": int|null, ...}")
    ap.add_argument("--results", help="d12o-style results JSON; derive floors from acc_grid")
    ap.add_argument("--acc-bar", type=float, default=0.9,
                    help="accuracy bar for --results floor derivation (default 0.9)")
    ap.add_argument("--min-coverage", type=float, default=0.8, help="G1 threshold (default 0.8)")
    ap.add_argument("--min-ratio", type=float, default=0.02, help="G1b threshold (default 0.02)")
    ap.add_argument("--out", help="write JSON receipt here (also printed)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    if args.p is None:
        fail_input("--p is required (use --selftest for the pinned example)")
    if not (0.0 <= args.p <= 1.0):
        fail_input(f"--p must be in [0,1], got {args.p}")
    if args.alpha <= 0 or args.c <= 0:
        fail_input("--c and --alpha must be positive")

    if args.floors:
        floors = json.loads(args.floors)
        if not isinstance(floors, dict) or not floors:
            fail_input("--floors must be a non-empty JSON object")
    elif args.results:
        with open(args.results) as f:
            floors = derive_floors(json.load(f), args.acc_bar)
    else:
        fail_input("provide --floors or --results")

    if args.eps:
        eps_values = [float(x) for x in args.eps.split(",")]
    else:
        eps_values = sorted({float(k.split("eps=")[1]) for k in floors})
    if args.w:
        w_values = [int(x) for x in args.w.split(",")]
    else:
        w_values = sorted({int(k.split(",")[0].split("=")[1]) for k in floors})
    if not eps_values or not w_values:
        fail_input("could not infer non-empty eps/W lists")

    gates = check_law(args.c, args.alpha, args.p, w_values, eps_values, floors,
                      args.min_coverage, args.min_ratio)
    receipt = {
        "tool": "law-floor-check",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "inputs": {"c": args.c, "alpha": args.alpha, "p": args.p,
                   "w": w_values, "eps": eps_values, "floors": floors,
                   "min_coverage": args.min_coverage, "min_ratio": args.min_ratio},
        **gates,
    }
    rendered = json.dumps(receipt, indent=1, sort_keys=True)
    print(rendered)
    if args.out:
        with open(args.out, "w") as f:
            f.write(rendered + "\n")


if __name__ == "__main__":
    main()
