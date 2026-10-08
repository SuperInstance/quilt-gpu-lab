#!/usr/bin/env python3
"""target-bisect — find x with f(x) ≈ target, robust to non-monotone f.

Pattern lifted PROVEN from D12aa2 (booked 2026-10-08): bisecting k_eff
against harness floors failed blind — the loss was U-shaped, not monotone,
and a naive bisection walked the wrong branch. The fix became the recipe:
(1) coarse grid scan over [lo,hi], (2) golden-section refine around the
best grid point, (3) bracket-gate — the scan must show the function value
CROSSES the target (or lands within tol) on the interior; an edge-best
scan books honest EDGE-BRACKET, never a silent PASS.

API:
    from target_bisect import solve
    r = solve(f, target=10.0, lo=0.0, hi=5.0, tol=0.05)
    r["verdict"] in {"HIT", "EDGE-BRACKET", "NO-HIT"}   # r["x"], r["fx"]

CLI (stdlib-only):
    python tools/target_bisect.py --expr "x*x" --target 4 --lo 0 --hi 3
    python tools/target_bisect.py --expr "abs(x-2)+3" --target 5 --lo 0 --hi 4 --tol 0.01
    python tools/target_bisect.py --selftest --out receipt.json

Exit 0=HIT / 1=EDGE-BRACKET or NO-HIT / 2=fail-loud input.
The expr may use x and math functions (sin, exp, sqrt, ...). Never eval
untrusted input; this is a lab tool for lab expressions.
"""
import argparse, json, math, os, sys, tempfile

GOLDEN = (math.sqrt(5) - 1) / 2  # 0.618..., shrink factor

_SAFE = {k: getattr(math, k) for k in
         ("sin", "cos", "tan", "asin", "acos", "atan", "exp", "log", "log10",
          "sqrt", "fabs", "floor", "ceil", "pi", "e", "tanh", "sinh", "cosh",
          "pow", "atan2", "hypot")}


def _fn(expr):
    code = compile(expr, "<expr>", "eval")
    def f(x):
        return float(eval(code, {"__builtins__": {}}, dict(_SAFE, x=x)))
    return f


def solve(f, target, lo, hi, tol=1e-3, grid=33, max_iter=60):
    """Coarse scan + golden refine. Returns receipt dict (see module doc)."""
    if not (hi > lo):
        raise ValueError(f"bracket must satisfy hi > lo (got [{lo},{hi}])")
    if tol <= 0:
        raise ValueError(f"tol must be positive (got {tol})")
    if grid < 8:
        raise ValueError(f"grid must be >= 8 (got {grid})")

    pts = [lo + (hi - lo) * i / (grid - 1) for i in range(grid)]
    fpts = [f(x) for x in pts]
    for v in fpts:
        if not math.isfinite(v):
            raise ValueError("f produced a non-finite value on the scan grid")

    # exact hit on grid? (a hit AT THE EDGE books EDGE-BRACKET — the domain
    # stops there, so no interior root is witnessed)
    for x, v in zip(pts, fpts):
        if abs(v - target) <= tol:
            i = pts.index(x)
            if i in (0, len(pts) - 1):
                return _book("EDGE-BRACKET", x, v, "grid-exact at scan edge",
                             target, lo, hi, tol, pts)
            return _book("HIT", x, v, "grid-exact", target, lo, hi, tol, pts)

    # target must be between scan extremes, else it is unreachable in [lo,hi]
    if not (min(fpts) <= target <= max(fpts)):
        return _book("NO-HIT", pts[0], fpts[0], "target-outside-interior-range",
                     target, lo, hi, tol, pts)

    # golden-section refine on the best interior neighborhood
    i_best = min(range(1, grid - 1), key=lambda i: abs(fpts[i] - target))
    a, b = pts[i_best - 1], pts[i_best + 1]
    how, x_best, v_best = "golden", None, None
    for _ in range(max_iter):
        c = b - GOLDEN * (b - a)
        d = a + GOLDEN * (b - a)
        fc, fd = f(c), f(d)
        if not (math.isfinite(fc) and math.isfinite(fd)):
            raise ValueError("f produced a non-finite value during refinement")
        if abs(fc - target) < abs(fd - target):
            b = d
        else:
            a = c
        if (b - a) < tol * 0.1:
            break
    x_best = (a + b) / 2
    v_best = f(x_best)
    if not math.isfinite(v_best):
        raise ValueError("f produced a non-finite value at the refined point")
    if abs(v_best - target) <= tol:
        # bracket witness: a scan point on each side of the target
        below = any(v < target - tol for v in fpts)
        above = any(v > target + tol for v in fpts)
        if not (below and above):
            return _book("EDGE-BRACKET", x_best, v_best,
                         "no crossing witnessed on scan", target, lo, hi, tol, pts)
        return _book("HIT", x_best, v_best, how, target, lo, hi, tol, pts)
    return _book("NO-HIT", x_best, v_best, "refine did not reach tol",
                 target, lo, hi, tol, pts)


def _book(verdict, x, fx, why, target, lo, hi, tol, pts):
    return {"verdict": verdict, "x": x, "fx": fx, "target": target,
            "tol": tol, "lo": lo, "hi": hi, "why": why,
            "scan": {"n": len(pts), "pts": [round(p, 6) for p in pts]}}


def _selftest(out=None):
    checks = []

    def chk(name, cond):
        checks.append((name, bool(cond)))
        if not cond:
            raise SystemExit(f"SELFTEST FAIL: {name}")

    # monotone quadratic: clean HIT
    r = solve(lambda x: x * x, 4.0, 0, 3, tol=1e-4)
    chk("quad-hit", r["verdict"] == "HIT" and abs(r["x"] - 2.0) < 1e-3)
    # D12aa2 lesson: U-shaped loss — blind bisection walks wrong branch; scan+refine hits
    r2 = solve(lambda x: abs(x - 2.7) + 3.0, 5.0, 0, 4, tol=1e-3)
    chk("ushape-hit", r2["verdict"] == "HIT" and abs(r2["x"] - 0.7) < 1e-2)  # x=0.7 is the in-bracket root (4.7 is outside)
    # target unreachable: honest NO-HIT
    r3 = solve(lambda x: x + 10, 1.0, 0, 2, tol=1e-3)
    chk("nohit", r3["verdict"] == "NO-HIT")
    # edge-bracket: target met ONLY at a scan edge (grid-exact there) — the
    # domain stops, so no interior root is witnessed. Control: a root merely
    # NEAR the edge, witnessed from both sides, is honestly HIT.
    r4 = solve(lambda x: x, 0.004, 0, 1, tol=0.005)
    chk("edge", r4["verdict"] == "EDGE-BRACKET")
    r5 = solve(lambda x: x, 0.004, 0, 1, tol=1e-3)
    chk("near-edge-hit", r5["verdict"] == "HIT" and abs(r5["x"] - 0.004) < 1e-3)
    # fail-loud inputs
    for bad in (lambda: solve(lambda x: x, 1, 2, 2),      # empty bracket
                lambda: solve(lambda x: x, 1, 0, 1, tol=0),  # tol<=0
                lambda: solve(lambda x: float("nan") if x > 1 else x, 0.5, 0, 2)):  # non-finite
        try:
            bad(); chk("fail-loud", False)
        except ValueError:
            pass
    chk("fail-loud", True)

    ok = all(c for _, c in checks)
    receipt = {"tool": "target_bisect", "selftest": "PASS" if ok else "FAIL",
               "n_checks": len(checks)}
    if out:
        _write_receipt(out, receipt)
    print(json.dumps(receipt))
    return 0 if ok else 1


def _write_receipt(path, receipt):
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    with os.fdopen(fd, "w") as fh:
        json.dump(receipt, fh, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="target-bisect: scan+refine solver, robust to non-monotone f")
    ap.add_argument("--expr", help="f(x) expression using x and math functions")
    ap.add_argument("--target", type=float)
    ap.add_argument("--lo", type=float)
    ap.add_argument("--hi", type=float)
    ap.add_argument("--tol", type=float, default=1e-3)
    ap.add_argument("--grid", type=int, default=33)
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return _selftest(a.out)
    if not (a.expr and a.target is not None and a.lo is not None and a.hi is not None):
        ap.error("--expr/--target/--lo/--hi are required (or --selftest)")
    try:
        r = solve(_fn(a.expr), a.target, a.lo, a.hi, tol=a.tol, grid=a.grid)
    except ValueError as e:
        print(f"FAIL-INPUT: {e}", file=sys.stderr)
        return 2
    r["expr"] = a.expr
    if a.out:
        _write_receipt(a.out, r)
    print(json.dumps(r, indent=2))
    return 0 if r["verdict"] == "HIT" else 1


if __name__ == "__main__":
    sys.exit(main())
