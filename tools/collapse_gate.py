#!/usr/bin/env python3
"""collapse-gate — monotone-collapse + leave-one-group-out prediction gate.

Pattern lifted PROVEN from D12w (booked 2026-10-06: k_eff collapses onto a
single function of s_eff — G1 inversions<=2, G2 max leave-one-p-out error
13.9% vs 25% bar, verdict KEEP). Mechanizes the general claim: "y is a
single function of x across my cells, not a per-group artifact."

Input: points [{x, y, group}] (group optional but required for the G2 clause
to run; single-group input books G2 VOID, not PASS — a prediction that is
never held out proves nothing).

  G1 (collapse): counting inversions over x-sorted pairs — pairs where y
      RISES by more than `--jitter` while x rises are violations. Monotone
      direction: decreasing by default (D12w semantics), flip with
      `--direction increasing`. KEEP iff inversions <= `--max-inv`.
  G2 (LOO power law): fit log y = a + b log x pooled; b<=0 (decreasing) is
      required; then leave-one-GROUP-out — refit without each group, predict
      its points, KEEP iff max relative error <= `--err-bar`.

Both clauses must pass; a VOID clause degrades honestly (rc=0 with verdict
"KEEP-PARTIAL" only if the other clause passed and void was structural).
Stdlib-only, deterministic, fail-loud rc=2, one JSON receipt.

Worked example (D12w-shaped data, decreasing):
    python tools/collapse_gate.py --points '[{"x":0.3,"y":0.658,"group":"p0.3"},
      {"x":0.24,"y":0.56,"group":"p0.3"},{"x":0.4,"y":0.9,"group":"p0.4"},
      {"x":0.32,"y":0.71,"group":"p0.4"}]' --out r.json
Selftest: python tools/collapse_gate.py --selftest
"""
import argparse, json, math, sys, time

def fit_loglog(pts):
    xs = [math.log(p["x"]) for p in pts]
    ys = [math.log(p["y"]) for p in pts]
    n = len(xs)
    if n < 2:
        raise ValueError("need >=2 points to fit")
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        raise ValueError("degenerate x spread (all equal)")
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return my - b * mx, b

def count_inversions(pts, jitter, direction):
    # pts: list of dicts; violation = x rises but y moves the wrong way
    sgn = -1.0 if direction == "decreasing" else 1.0
    inv = 0
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            hi, lo = pts[i], pts[j]
            if hi["x"] == lo["x"]:
                continue
            if lo["x"] > hi["x"]:
                hi, lo = lo, hi
            # x rises from lo to hi; y must fall (decreasing) / rise (increasing)
            if sgn * (lo["y"] - hi["y"]) > jitter:
                inv += 1
    return inv

def run_gate(points, direction="decreasing", jitter=0.02, max_inv=2,
             err_bar=0.25, require_b_nonpos=True):
    if not points:
        raise ValueError("no points")
    for p in points:
        for k in ("x", "y"):
            v = p.get(k)
            if not isinstance(v, (int, float)) or math.isnan(v) or v <= 0:
                raise ValueError(f"point {p!r}: {k} must be positive finite")
    for k in ("group",):
        for p in points:
            p.setdefault(k, "g0")
    inv = count_inversions(points, jitter, direction)
    g1 = inv <= max_inv

    groups = sorted({p["group"] for p in points})
    a, b = fit_loglog(points)
    b_ok = (b <= 0) if direction == "decreasing" else (b >= 0)
    void = False
    if not b_ok:
        g2 = False
        max_err = None
    elif len(groups) < 2:
        g2, max_err, void = None, None, True  # VOID: nothing held out
    else:
        errs = []
        for hold in groups:
            tr = [p for p in points if p["group"] != hold]
            te = [p for p in points if p["group"] == hold]
            ah, bh = fit_loglog(tr)
            for p in te:
                pred = math.exp(ah + bh * math.log(p["x"]))
                errs.append(abs(pred - p["y"]) / p["y"])
        max_err = max(errs)
        g2 = max_err <= err_bar

    if g1 and g2 is True:
        verdict = "KEEP"
    elif g1 and g2 is None:
        verdict = "KEEP-PARTIAL_G2_VOID"
    elif g1 is False:
        verdict = "KILL"
    else:
        verdict = "KILL"
    return dict(direction=direction, jitter=jitter, max_inv=max_inv,
                err_bar=err_bar, n_points=len(points),
                n_groups=len(groups), inversions=inv, G1=bool(g1),
                fit_a=round(a, 4), fit_b=round(b, 4),
                max_loo_err=(round(max_err, 4) if max_err is not None else None),
                G2=g2, G2_VOID=bool(void), verdict=verdict)

def selftest():
    ok = 0
    def check(name, cond):
        nonlocal ok
        if not cond:
            print(f"  FAIL {name}")
            raise SystemExit(f"selftest failed at: {name}")
        ok += 1
        print(f"  ok {name}")

    # 1. clean decreasing collapse -> KEEP
    pts = [{"x": x, "y": 1.0 / x, "group": f"g{i % 2}"}
           for i, x in enumerate([0.2, 0.3, 0.5, 0.7, 0.9])]
    r = run_gate(pts)
    check("clean-collapse KEEP", r["verdict"] == "KEEP" and r["G1"] and r["G2"])

    # 2. rising violator -> KILL on G1 (max_inv=0 so ANY inversion trips)
    pts2 = pts + [{"x": 0.25, "y": 100.0, "group": "g0"}]
    r2 = run_gate(pts2, max_inv=0)
    check("violator KILL G1", r2["verdict"] == "KILL" and not r2["G1"])

    # 3. single group -> G2 VOID, never fake PASS
    r3 = run_gate([{"x": 0.3, "y": 3.0, "group": "only"}, {"x": 0.5, "y": 2.0, "group": "only"}])
    check("single-group VOID", r3["G2"] is None and r3["G2_VOID"] and r3["verdict"] == "KEEP-PARTIAL_G2_VOID")

    # 4. increasing direction flips semantics
    pts4 = [{"x": x, "y": 2.0 * x, "group": f"g{i % 2}"} for i, x in enumerate([0.2, 0.4, 0.6, 0.8])]
    r4 = run_gate(pts4, direction="increasing")
    check("increasing KEEP", r4["verdict"] == "KEEP")

    # 5. increasing default mis-set -> G1 kills (wrong-direction slope)
    r5 = run_gate(pts4)  # decreasing expected, data increases
    check("wrong-direction KILL", not r5["G1"] or r5["fit_b"] > 0 and r5["verdict"] == "KILL")

    # 6. fail-loud: zero/negative x
    try:
        run_gate([{"x": 0, "y": 1, "group": "a"}, {"x": 0.5, "y": 1, "group": "b"}])
        check("zero-x fail-loud", False)
    except ValueError:
        check("zero-x fail-loud", True)

    # 7. fail-loud: NaN y
    try:
        run_gate([{"x": 0.3, "y": float("nan"), "group": "a"}, {"x": 0.5, "y": 1, "group": "b"}])
        check("NaN-y fail-loud", False)
    except ValueError:
        check("NaN-y fail-loud", True)

    # 8. determinism
    check("determinism", run_gate(pts) == run_gate(pts))

    print(f"selftest {ok}/8 PASS")
    return ok

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--points", help='JSON array of {"x":>0,"y":>0,"group":str}')
    ap.add_argument("--points-file")
    ap.add_argument("--direction", choices=["decreasing", "increasing"], default="decreasing")
    ap.add_argument("--jitter", type=float, default=0.02)
    ap.add_argument("--max-inv", type=int, default=2)
    ap.add_argument("--err-bar", type=float, default=0.25)
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(0 if selftest() == 8 else 1)
    if not (args.points or args.points_file):
        ap.error("need --points or --points-file (or --selftest)")
    raw = open(args.points_file).read() if args.points_file else args.points
    try:
        points = json.loads(raw)
        if not isinstance(points, list):
            raise ValueError("points must be a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        sys.exit(f"FAIL-INPUT rc=2: bad points JSON: {e}")
    try:
        r = run_gate(points, args.direction, args.jitter, args.max_inv, args.err_bar)
    except ValueError as e:
        sys.exit(f"FAIL-INPUT rc=2: {e}")
    r["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(json.dumps(r, indent=1))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(r, f, indent=1)
        print(f"receipt -> {args.out}")
    # rc: 0 = KEEP/PARTIAL (G2 void is honest), 1 = KILL, 2 = fail-loud (above)
    sys.exit(0 if r["verdict"].startswith("KEEP") else 1)

if __name__ == "__main__":
    main()
