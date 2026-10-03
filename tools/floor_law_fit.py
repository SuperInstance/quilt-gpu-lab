#!/usr/bin/env python3
"""floor-law-fit — fit and validate a discovery-floor power law, stdlib-only.

Lifted from tonight's PROVEN D12p/D12n pattern (quilt-gpu-lab): measured
floors follow W*T_floor <= C(p)/s^alpha with s=(2p-1)(1-2eps) and
C(p) ~ C0*(2p-1)^-beta. This tool takes your measured (p, T_floor) points,
fits beta by log-log regression on a designated fit subset, then checks
HELD-OUT coverage: does the fitted constant PREDICT floors at points it
never saw, without refitting? Fail-loud JSON receipt either way. Fit
quality (R^2) and coverage are reported separately so a coverage miss is
booked honestly as KILL, not buried.

Usage:
  python tools/floor_law_fit.py --points points.json \
      --fit 0.3,0.4 --heldout 0.6,0.7 [--alpha 1.92] [--w 8] [--eps 0.0] \
      [--r2-min 0.8] [--coverage-min 1.0] [--nonvacuous-min 0.02] \
      [--out receipt.json]

points.json format:
  {"points": [{"p": 0.3, "t": 40}, {"p": 0.4, "t": 55},
              {"p": 0.6, "t": 160}, {"p": 0.7, "t": 320}]}

Worked example (self-test, deterministic):
  python tools/floor_law_fit.py --example --out /tmp/floor_law_example.json
  -> builds synthetic floors T(p) = 600/((2p-1)^1.5 * 8) * 1.05 at
     p in {0.3,0.4,0.6,0.7}, fits on 0.3/0.4, predicts 0.6/0.7.
     Expect R^2 = 1.0 (exact model), coverage 2/2, verdict PASS.

Exit codes: 0 PASS, 1 KILL (gate failure), 2 usage/input error.
"""
from __future__ import annotations

import argparse
import json
import math
import sys


def fit_beta(points):
    """points: [(p, C_emp)]; model log C = log C0 - beta*log(2p-1)."""
    if len(points) < 2:
        raise ValueError(f"need >=2 fit points, got {len(points)}")
    xs = [math.log(abs(2 * p - 1)) for p, _ in points]
    ys = [math.log(c) for _, c in points]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        raise ValueError("degenerate fit: all fit points share the same p")
    slope = sxy / sxx
    intercept = my - slope * mx
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
    return math.exp(intercept), -slope, r2


def example_points():
    pts = []
    for p in (0.3, 0.4, 0.6, 0.7):
        s = abs(2 * p - 1)
        t = 600.0 / (s ** 1.5 * 8) * 1.05  # 5% slack: bound non-vacuous
        pts.append({"p": p, "t": round(t, 3)})
    return pts


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                 allow_abbrev=False)
    ap.add_argument("--points", help="JSON file with measured (p, t) points")
    ap.add_argument("--example", action="store_true",
                    help="run the built-in deterministic self-test")
    ap.add_argument("--fit", default="",
                    help="comma-separated p values used to fit beta")
    ap.add_argument("--heldout", default="",
                    help="comma-separated p values predicted, not fitted")
    ap.add_argument("--alpha", type=float, default=1.92)
    ap.add_argument("--w", type=float, default=8, help="stream width W")
    ap.add_argument("--eps", type=float, default=0.0)
    ap.add_argument("--r2-min", type=float, default=0.8)
    ap.add_argument("--coverage-min", type=float, default=1.0)
    ap.add_argument("--nonvacuous-min", type=float, default=0.02,
                    help="min measured/bound ratio; below = vacuous bound")
    ap.add_argument("--out", help="write fail-loud JSON receipt here")
    args = ap.parse_args()

    receipt = {"tool": "floor_law_fit", "verdict": "KILL", "gates": {}}
    try:
        if args.example:
            points = example_points()
            args.fit = args.fit or "0.3,0.4"
            args.heldout = args.heldout or "0.6,0.7"
        elif args.points:
            with open(args.points) as f:
                points = json.load(f)["points"]
        else:
            ap.error("one of --points or --example is required")

        def parse_ps(s):
            return [float(x) for x in s.split(",") if x.strip()]

        fit_ps, held_ps = parse_ps(args.fit), parse_ps(args.heldout)
        by_p = {}
        for pt in points:
            p, t = float(pt["p"]), float(pt["t"])
            if not (0.0 < p < 1.0) or p == 0.5:
                raise ValueError(f"p={p} invalid (need 0<p<1, p!=0.5)")
            if t <= 0:
                raise ValueError(f"T_floor must be > 0, got {t} at p={p}")
            by_p[p] = t

        missing = [p for p in fit_ps + held_ps if p not in by_p]
        if missing:
            raise ValueError(f"no measurement for p in {missing}")

        s = lambda p: abs(2 * p - 1) * (1 - 2 * args.eps)
        c_emp = {p: args.w * by_p[p] * s(p) ** args.alpha for p in by_p}
        c0, beta, r2 = fit_beta([(p, c_emp[p]) for p in fit_ps])

        preds = []
        covered = 0
        vacuous = 0
        for p in held_ps:
            bound = c0 * abs(2 * p - 1) ** (-beta) / s(p) ** args.alpha
            wt = args.w * by_p[p]
            ratio = wt / bound
            cov = wt <= bound
            nonvac = ratio >= args.nonvacuous_min
            covered += cov
            vacuous += (not nonvac)
            preds.append({"p": p, "measured_WT": wt, "bound": bound,
                          "ratio": round(ratio, 4), "covered": cov,
                          "non_vacuous": nonvac})
        n_held = len(held_ps)
        cov_frac = covered / n_held if n_held else 1.0

        g1 = r2 >= args.r2_min
        g2 = n_held > 0 and cov_frac >= args.coverage_min and vacuous == 0
        receipt["gates"] = {
            "G1_fit_quality": {"r2": round(r2, 4), "threshold": args.r2_min,
                               "pass": g1},
            "G2_heldout_coverage": {"covered": covered, "of": n_held,
                                    "vacuous": vacuous, "pass": g2},
        }
        receipt.update({"C0": round(c0, 4), "beta": round(beta, 4),
                        "alpha": args.alpha, "w": args.w, "eps": args.eps,
                        "c_emp": {str(p): round(v, 4) for p, v in
                                  sorted(c_emp.items())},
                        "heldout": preds})
        receipt["verdict"] = "PASS" if (g1 and g2) else "KILL"
    except Exception as e:
        receipt["error"] = f"{type(e).__name__}: {e}"
        print(f"FAIL-LOUD: {receipt['error']}", file=sys.stderr)

    if args.out:
        with open(args.out, "w") as f:
            json.dump(receipt, f, indent=2)
        print(f"receipt -> {args.out}")
    print(json.dumps(receipt, indent=2))
    sys.exit(0 if receipt["verdict"] == "PASS" else
             2 if "error" in receipt else 1)


if __name__ == "__main__":
    main()
