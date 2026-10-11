#!/usr/bin/env python3
"""rho-hazard-gate — common-mode null-dependence hazard gate.

Pattern lifted PROVEN from D12am/D12an (booked 2026-10-11): under common-mode
null dependence (inter-stream corr rho), discovery floors blow up super-
linearly: blowup(rho) = floor(rho)/floor(0), delta = blowup - 1 ~ rho^gamma
with fitted gamma ~ 1.6-2.4 (D12am dense grid), and the hazard magnitude was
shown p-UNIVERSAL within a 2x band across coupling strengths (D12an, p in
{0.5, 0.7} vs the p=0.3 reference). This tool mechanizes that gate battery
for any (x, floor) hazard sweep:

  G1 MONOTONE: blowup is monotone non-decreasing in x (no inversions).
  G2 EXPONENT: fitted gamma from log-log OLS of delta vs x lands in a band
     (default [1.0, 3.5]); delta=0 at the lowest x (no hazard) books VOID,
     never a silent fit.
  G3 UNIVERSALITY (optional, multi-group): blowup at a reference x must land
     within [lo, hi]x across groups — a hazard that swings wildly with an
     untested variable is not a law.

Stdlib-only, deterministic, fail-loud rc=2, one JSON receipt,
exit 0=KEEP / 1=FAIL / 2=FAIL-INPUT.

Usage:
  python tools/rho_hazard_gate.py --points '[[0.1,40],[0.15,40],[0.2,70],[0.3,140],[0.4,220]]' --base 25 [--gamma-lo 1.0 --gamma-hi 3.5 --out r.json]
  python tools/rho_hazard_gate.py --groups '{"0.3":[[...]],"0.5":[[...]]}' --ref-x 0.3 --band 0.5,2.0
  python tools/rho_hazard_gate.py --replay-d12am | --selftest

Worked example (--replay-d12am): feeds the booked D12am W=8 p=0.3 eps=0
floors, expects KEEP with gamma in band. --selftest carries monotone-KEEP,
inversion-FAIL, exponent-FAIL, degenerate-VOID, universality controls, and
must exit 0.
"""
import argparse
import json
import math
import sys
import time

def ols(xs, ys):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        raise ValueError("degenerate x variance in exponent fit")
    b = sxy / sxx
    return b, my - b * mx

def r2(xs, ys, b, a):
    my = sum(ys) / len(ys)
    ssres = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    sstot = sum((y - my) ** 2 for y in ys)
    return 1.0 - ssres / sstot if sstot > 0 else 1.0

def blowups(points):
    """points: [(x, floor)] -> sorted [(x, blowup)] with base = floor at min x."""
    pts = sorted(points)
    if not pts or not all(isinstance(pt, (list, tuple)) and len(pt) == 2
                          and all(isinstance(v, (int, float))
                                  and not isinstance(v, bool) for v in pt)
                          for pt in pts):
        raise ValueError("points must be [[x, floor], ...] pairs of numbers")
    base = pts[0][1]
    if base <= 0:
        raise ValueError("base floor must be positive, got %r" % base)
    return [(x, f / base) for x, f in pts]

def check_group(points, gamma_lo, gamma_hi):
    """One (x, floor) sweep -> gate dict."""
    bl = blowups(points)
    inversions = sum(1 for i in range(1, len(bl)) if bl[i][1] < bl[i - 1][1])
    g1 = inversions == 0
    fit_pts = [(x, b - 1.0) for x, b in bl if b > 1.0]
    if len(fit_pts) < 2 or all(d <= 0 for _, d in fit_pts):
        return ({"g1_monotone": g1, "inversions": inversions,
                 "g2_exponent": None, "void": "no hazard: delta=0 at every x"},
                False, None)
    xs = [math.log(x) for x, _ in fit_pts if x > 0]
    ys = [math.log(d) for x, d in fit_pts if x > 0]
    if len(xs) < 2:
        return ({"g1_monotone": g1, "inversions": inversions,
                 "g2_exponent": None, "void": "fewer than 2 log-fittable points"},
                False, None)
    gamma, intercept = ols(xs, ys)
    g2 = gamma_lo <= gamma <= gamma_hi
    return {"g1_monotone": g1, "inversions": inversions,
            "gamma": round(gamma, 4), "gamma_band": [gamma_lo, gamma_hi],
            "r2": round(r2(xs, ys, gamma, intercept), 4),
            "n_fit_points": len(xs)}, g1 and g2, gamma

def run(points=None, groups=None, gamma_lo=1.0, gamma_hi=3.5,
        ref_x=None, band=(0.5, 2.0)):
    receipt = {"tool": "rho_hazard_gate", "ts": time.time(),
               "gamma_band": [gamma_lo, gamma_hi]}
    if groups is not None:
        if ref_x is None:
            raise ValueError("--groups requires --ref-x")
        gate = {}
        g_all = True
        per = {}
        for name, pts in sorted(groups.items()):
            r, ok, _ = check_group(pts, gamma_lo, gamma_hi)
            per[name] = r
            g_all = g_all and ok
        refvals = []
        for name, pts in sorted(groups.items()):
            bl = dict(blowups(pts))
            if ref_x not in bl:
                raise ValueError("ref_x %r not on grid of group %s" % (ref_x, name))
            refvals.append((name, bl[ref_x]))
        lo, hi = band
        ref0 = refvals[0][1]
        uni = all(lo <= v / ref0 <= hi for _, v in refvals[1:])
        g3 = uni and len(refvals) > 1
        verdict = "KEEP" if (g_all and g3) else "FAIL"
        receipt.update({"mode": "groups", "per_group": per,
                        "ref_x": ref_x, "ref_blowups": refvals,
                        "band": list(band), "g3_universality": g3,
                        "verdict": verdict})
        return verdict, receipt
    if points is None:
        raise ValueError("need --points or --groups")
    r, ok, _ = check_group(points, gamma_lo, gamma_hi)
    verdict = "KEEP" if ok else "FAIL"
    receipt.update({"mode": "single", "result": r, "verdict": verdict,
                    "points": points})
    return verdict, receipt

def replay_d12am():
    pts = [[0.0, 25], [0.1, 40], [0.15, 40], [0.2, 70],
           [0.3, 140], [0.4, 220], [0.5, 330], [0.6, 430]]
    return run(points=pts)

def selftest():
    checks = []

    def pin(name, cond):
        checks.append((name, bool(cond)))

    v, r = run(points=[[0.1, 40], [0.2, 70], [0.4, 220]], gamma_lo=1.0, gamma_hi=3.5)
    pin("monotone superlinear KEEP", v == "KEEP" and r["result"]["g1_monotone"]
        and 1.0 <= r["result"]["gamma"] <= 3.5)

    v, r = run(points=[[0.1, 90], [0.2, 70], [0.4, 220]])
    pin("inversion FAIL", v == "FAIL" and r["result"]["inversions"] == 1)

    v, r = run(points=[[0.1, 40], [0.2, 42], [0.4, 43]], gamma_lo=1.0, gamma_hi=3.5)
    pin("sublinear exponent FAIL", v == "FAIL" and r["result"]["gamma"] < 1.0)

    v, r = run(points=[[0.1, 25], [0.2, 25]])
    pin("no-hazard VOID", v == "FAIL" and r["result"].get("void"))

    v, r = run(groups={"a": [[0.1, 40], [0.2, 70], [0.3, 140]],
                        "b": [[0.1, 40], [0.2, 72], [0.3, 160]]},
               ref_x=0.3, band=(0.5, 2.0))
    pin("universality KEEP", v == "KEEP" and r["g3_universality"])

    v, r = run(groups={"a": [[0.1, 40], [0.2, 70], [0.3, 140]],
                        "b": [[0.1, 40], [0.2, 70], [0.3, 500]]},
               ref_x=0.3, band=(0.5, 2.0))
    pin("universality swing FAIL", v == "FAIL" and not r["g3_universality"])

    for bad in ([], [[0.1, 0]], "junk"):
        try:
            run(points=bad)
            pin("fail-loud %r" % (bad,), False)
        except (ValueError, TypeError):
            pin("fail-loud %r" % (bad,), True)

    failed = [n for n, ok in checks if not ok]
    print(json.dumps({"selftest": "PASS" if not failed else "FAIL",
                      "total": len(checks), "failed": failed}, indent=1))
    return 0 if not failed else 1

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--points", help="JSON [[x, floor], ...] single sweep")
    ap.add_argument("--groups", help="JSON {name: [[x, floor], ...], ...}")
    ap.add_argument("--ref-x", type=float, help="reference x for G3 universality")
    ap.add_argument("--band", default="0.5,2.0", help="G3 band lo,hi (ratio)")
    ap.add_argument("--gamma-lo", type=float, default=1.0)
    ap.add_argument("--gamma-hi", type=float, default=3.5)
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--replay-d12am", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    try:
        if args.replay_d12am:
            verdict, receipt = replay_d12am()
        else:
            band = tuple(float(t) for t in args.band.split(","))
            points = json.loads(args.points) if args.points else None
            groups = json.loads(args.groups) if args.groups else None
            verdict, receipt = run(points=points, groups=groups,
                                   gamma_lo=args.gamma_lo,
                                   gamma_hi=args.gamma_hi,
                                   ref_x=args.ref_x, band=band)
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        print(json.dumps({"tool": "rho_hazard_gate", "verdict": "FAIL-INPUT",
                          "error": str(e)}))
        return 2
    out = json.dumps(receipt, indent=1, sort_keys=True)
    if args.out:
        with open(args.out, "w") as f:
            f.write(out + "\n")
    print(out)
    return 0 if verdict == "KEEP" else (1 if verdict == "FAIL" else 2)

if __name__ == "__main__":
    sys.exit(main())
