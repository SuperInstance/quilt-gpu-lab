#!/usr/bin/env python3
"""minimax-calib — one-parameter minimax calibration fit (stdlib-only).

Pattern lifted PROVEN from d12u++ (booked 2026-10-04, CALIBRATED):
kappa=0.246 closed a 2.7x worst-cell gap on all 12 d12t cells with ONE
lumped parameter, fitted by minimizing the worst-cell |log ratio|.

What it does
------------
Given measured values and a model skeleton that depends on a single
correction parameter kappa:

    model_i(kappa) = skeleton_i * kappa**exp        (exp fixed, default 1)

fit kappa by MINIMAX: minimize over kappa the worst-cell
|log(model_i(kappa) / measured_i)| — chosen because the acceptance gate is
itself worst-cell; one parameter, no other dof. Search is deterministic:
coarse geometric grid on [lo, hi], then golden-section ternary refine on
log(kappa) to a relative tolerance. GATES (fail loud, honest receipts):

    G1  worst-cell ratio model/measured <= band on BOTH sides (default 1.3)
    G2  kappa_hat inside the pre-declared sane band [lo, hi]

Exit 0 = CALIBRATED (G1 and G2), 1 = FAIL (booked honestly — no refit
without a new pre-registration), 2 = fail-loud input error.

Why minimax: gates on the worst cell, so fit the worst cell. |log| makes
over- and under-prediction symmetric, so a scale error of 2x costs the
same as 0.5x.

Usage
-----
    python tools/minimax_calib.py --cells cells.json [--exp 1.0]
        [--lo 0.1 --hi 1.0 --band 1.3 --steps 33 --tol 0.005 --out r.json]

    cells.json: [{"name": "w4_eps0", "skeleton": 53.0, "measured": 220.0}, ...]
    (skeleton = model value at kappa = 1; measured > 0; names unique)

    python tools/minimax_calib.py --example     # worked example below
    python tools/minimax_calib.py --selftest    # negative-control battery

Worked example (--example)
--------------------------
True scale error 0.25 planted on 3 cells of a skeleton; fit should
recover kappa_hat ~= 0.25 within the 1.3x band and book CALIBRATED.

Library API
-----------
    from tools.minimax_calib import fit_minimax, load_cells, run_fit
    cells = load_cells(json.loads(s))
    res = run_fit(cells, lo=0.1, hi=1.0, band=1.3, exp=1.0)
    res["verdict"], res["param_hat"], res["worst_ratio"]
"""
import argparse
import json
import math
import sys

INV_PHI = (math.sqrt(5.0) - 1.0) / 2.0   # 0.618034 = 1/phi (golden ratio complement)


# ---------------------------------------------------------------- input

def load_cells(raw):
    """Validate + normalize the cell list. Fail loud (ValueError)."""
    if not isinstance(raw, list) or not raw:
        raise ValueError("cells must be a non-empty JSON list")
    seen, cells = set(), []
    for i, c in enumerate(raw):
        if not isinstance(c, dict):
            raise ValueError(f"cell[{i}] is not an object")
        name = str(c.get("name", f"cell{i}"))
        sk, me = c.get("skeleton"), c.get("measured")
        for label, v in (("skeleton", sk), ("measured", me)):
            if not isinstance(v, (int, float)) or isinstance(v, bool) \
               or not math.isfinite(float(v)) or float(v) <= 0:
                raise ValueError(f"cell[{i}] '{name}': {label} must be finite > 0, got {v!r}")
        if name in seen:
            raise ValueError(f"duplicate cell name '{name}'")
        seen.add(name)
        cells.append({"name": name, "skeleton": float(sk), "measured": float(me)})
    return cells


# ---------------------------------------------------------------- fit

def _model(cell, kappa, exp):
    return cell["skeleton"] * (kappa ** exp)


def objective(kappa, cells, exp):
    """Worst-cell |log(model/measured)|; inf if any ratio is non-finite."""
    worst = 0.0
    for c in cells:
        m = _model(c, kappa, exp)
        if not math.isfinite(m) or m <= 0.0:
            return math.inf
        worst = max(worst, abs(math.log(m / c["measured"])))
    return worst


def fit_minimax(cells, lo, hi, exp=1.0, steps=33, tol=5e-3):
    """Deterministic coarse log-grid + golden-section refine on log(kappa).

    Returns (kappa_hat, best_worstloggap). Grid + local bracket + ternary:
    no RNG, bit-identical across runs for the same inputs.
    """
    if not (0.0 < lo < hi):
        raise ValueError(f"require 0 < lo < hi, got lo={lo} hi={hi}")
    if exp == 0.0:
        raise ValueError("exp=0 makes the model kappa-independent — no fit")
    grid = [math.exp(math.log(lo) + (math.log(hi) - math.log(lo)) * i / (steps - 1))
            for i in range(steps)]
    vals = [objective(k, cells, exp) for k in grid]
    best = min(range(steps), key=lambda i: vals[i])
    blo = grid[max(0, best - 1)]
    bhi = grid[min(steps - 1, best + 1)]
    for _ in range(200):                       # golden-section on log scale
        if bhi / blo <= 1.0 + tol:
            break
        m1 = math.exp(math.log(blo) + (1.0 - INV_PHI) * (math.log(bhi) - math.log(blo)))
        m2 = math.exp(math.log(blo) + INV_PHI * (math.log(bhi) - math.log(blo)))
        if objective(m1, cells, exp) < objective(m2, cells, exp):
            bhi = m2
        else:
            blo = m1
    khat = math.exp(0.5 * (math.log(blo) + math.log(bhi)))
    return khat, objective(khat, cells, exp)


def run_fit(cells, lo, hi, band=1.3, exp=1.0, steps=33, tol=5e-3):
    """Fit + frozen gates. Returns a JSON-ready receipt dict; caller books."""
    khat, gap = fit_minimax(cells, lo, hi, exp=exp, steps=steps, tol=tol)
    rows, worst_hi, worst_lo = [], 0.0, 0.0
    for c in cells:
        m = _model(c, khat, exp)
        r = m / c["measured"]
        rows.append({"name": c["name"], "skeleton": c["skeleton"],
                     "measured": c["measured"], "model": m, "ratio": r,
                     "abs_log_gap": abs(math.log(r))})
        worst_hi = max(worst_hi, r)
        worst_lo = max(worst_lo, 1.0 / r)
    g1 = worst_hi <= band and worst_lo <= band
    g2 = lo <= khat <= hi
    return {
        "tool": "minimax_calib",
        "exp": exp, "search_band": [lo, hi], "gate_band": band,
        "param_hat": khat, "worst_abs_log_gap": gap,
        "worst_ratio_high": worst_hi, "worst_ratio_low_inv": worst_lo,
        "cells": rows,
        "g1_worst_cell": {"pass": g1, "band": band},
        "g2_param_in_band": {"pass": g2},
        "verdict": "CALIBRATED" if (g1 and g2) else "FAIL",
    }


# ---------------------------------------------------------------- CLI

def _example():
    cells = [{"name": "w4", "skeleton": 400.0, "measured": 102.5},
             {"name": "w8", "skeleton": 400.0, "measured": 98.75},
             {"name": "w16", "skeleton": 400.0, "measured": 100.5}]
    return run_fit(cells, lo=0.05, hi=1.0, band=1.3, exp=1.0)


def _selftest():
    state = {"ok": 0, "total": 0}

    def check(name, cond):
        state["total"] += 1
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if cond:
            state["ok"] += 1

    # 1. clean scale error -> recovered within band, CALIBRATED
    cells = load_cells([{"name": "a", "skeleton": 1.0, "measured": 0.247},
                        {"name": "b", "skeleton": 2.0, "measured": 0.503},
                        {"name": "c", "skeleton": 4.0, "measured": 0.999}])
    r = run_fit(cells, lo=0.05, hi=1.0, band=1.3, exp=1.0)
    check("scale-error recovery CALIBRATED", r["verdict"] == "CALIBRATED")
    check("kappa_hat ~= 0.25", abs(r["param_hat"] - 0.25) < 0.01)

    # 2. 5x gap with band 1.3 -> honest FAIL (G1), not PASS
    cells = load_cells([{"name": "x", "skeleton": 1.0, "measured": 5.0},
                        {"name": "y", "skeleton": 1.0, "measured": 5.0}])
    r = run_fit(cells, lo=0.05, hi=1.0, band=1.3, exp=1.0)
    check("unfittable gap books FAIL", r["verdict"] == "FAIL")

    # 3. optimum pinned at the sane-band edge, still unfittable -> honest FAIL (G1)
    cells = load_cells([{"name": "a", "skeleton": 1.0, "measured": 0.01},
                        {"name": "b", "skeleton": 1.0, "measured": 0.01}])
    r = run_fit(cells, lo=0.05, hi=1.0, band=1.3, exp=1.0)
    check("unfittable-in-band books FAIL via G1",
          r["verdict"] == "FAIL" and not r["g1_worst_cell"]["pass"])

    # 4. exp-2 model recovers sqrt factor
    cells = load_cells([{"name": "a", "skeleton": 1.0, "measured": 0.16},
                        {"name": "b", "skeleton": 1.0, "measured": 0.16}])
    r = run_fit(cells, lo=0.05, hi=1.0, band=1.3, exp=2.0)
    check("exp=2 recovers sqrt", r["verdict"] == "CALIBRATED"
          and abs(r["param_hat"] - 0.4) < 0.01)

    # 5. determinism: two fits identical
    r2 = run_fit(load_cells([{"name": "a", "skeleton": 1.0, "measured": 0.247},
                             {"name": "b", "skeleton": 2.0, "measured": 0.503}]),
                 lo=0.05, hi=1.0, exp=1.0)
    r3 = run_fit(load_cells([{"name": "a", "skeleton": 1.0, "measured": 0.247},
                             {"name": "b", "skeleton": 2.0, "measured": 0.503}]),
                 lo=0.05, hi=1.0, exp=1.0)
    check("deterministic (bit-identical receipts)", r2 == r3)

    # 6. fail-loud inputs
    for bad, label in (([{"name": "a", "skeleton": 0.0, "measured": 1.0}], "zero skeleton"),
                       ([{"name": "a", "skeleton": 1.0, "measured": -2.0}], "negative measured"),
                       ([{"name": "a", "skeleton": 1.0, "measured": 1.0},
                         {"name": "a", "skeleton": 2.0, "measured": 1.0}], "duplicate name"),
                       ([], "empty list")):
        try:
            load_cells(bad)
            check(f"fail-loud: {label}", False)
        except ValueError:
            check(f"fail-loud: {label}", True)

    print(f"SELFTEST: {state['ok']}/{state['total']}")
    return 0 if state["ok"] == state["total"] else 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="One-parameter minimax calibration fit "
                    "(worst-cell |log ratio| objective, d12u++ pattern).")
    ap.add_argument("--cells", help="JSON file of {name, skeleton, measured} cells")
    ap.add_argument("--cells-json", help="inline JSON cells (alternative to --cells)")
    ap.add_argument("--exp", type=float, default=1.0,
                    help="model = skeleton * kappa**exp (fixed, default 1)")
    ap.add_argument("--lo", type=float, default=0.1, help="sane-band low")
    ap.add_argument("--hi", type=float, default=1.0, help="sane-band high")
    ap.add_argument("--band", type=float, default=1.3, help="G1 worst-cell band")
    ap.add_argument("--steps", type=int, default=33, help="coarse grid points")
    ap.add_argument("--tol", type=float, default=5e-3, help="ternary rel. tolerance")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--example", action="store_true", help="worked example")
    ap.add_argument("--selftest", action="store_true", help="negative-control battery")
    a = ap.parse_args(argv)

    if a.selftest:
        sys.exit(_selftest())
    if a.example:
        receipt = _example()
    else:
        if a.cells:
            with open(a.cells) as f:
                raw = json.load(f)
        elif a.cells_json:
            raw = json.loads(a.cells_json)
        else:
            ap.error("need --cells FILE, --cells-json '[...]', --example, or --selftest")
        try:
            cells = load_cells(raw)
        except ValueError as e:
            print(f"FAIL-INPUT: {e}", file=sys.stderr)
            sys.exit(2)
        if not (0.0 < a.lo < a.hi) or not (a.band > 1.0):
            print(f"FAIL-INPUT: require 0<lo<hi and band>1, got "
                  f"lo={a.lo} hi={a.hi} band={a.band}", file=sys.stderr)
            sys.exit(2)
        receipt = run_fit(cells, a.lo, a.hi, band=a.band, exp=a.exp,
                          steps=a.steps, tol=a.tol)

    if a.out:
        with open(a.out, "w") as f:
            json.dump(receipt, f, indent=2)
        print("wrote", a.out)
    print(f"param_hat={receipt['param_hat']:.4f} "
          f"worst_ratio={receipt['worst_ratio_high']:.3f} / "
          f"1/{receipt['worst_ratio_low_inv']:.3f} (band {receipt['gate_band']})")
    print(f"G1 worst-cell: {'PASS' if receipt['g1_worst_cell']['pass'] else 'FAIL'}  "
          f"G2 in-band: {'PASS' if receipt['g2_param_in_band']['pass'] else 'FAIL'}")
    print(f"VERDICT: {receipt['verdict']}")
    sys.exit(0 if receipt["verdict"] == "CALIBRATED" else 1)


if __name__ == "__main__":
    main()
