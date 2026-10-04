#!/usr/bin/env python3
"""power-fit — stdlib log-log power-law fit with honest receipt (pattern lifted
from experiments/d12m_decorrelation_exponent.py: fit log(y) = log(C) - alpha*log(x)
in log space; report slope, intercept, R^2, and a seeded bootstrap CI on the
slope so a claimed exponent is never just two eyeballed points).

Why grabbable: "measure the exponent / check the scaling law" recurs across
lanes (D12l noise floor, D12m decorrelation, ramp curves). This is the
one-file, no-numpy version: ordinary least squares on log-transformed data,
add-one percentile bootstrap CI (p never claims 0), fail-loud on
non-positive x/y, n < 3, or non-finite input. Deterministic under --seed.

Receipt: one JSON with verdict FIT / FAIL-INPUT, every input echoed, keys
sorted. Exit codes: 0 = fit ok, 2 = FAIL-INPUT (loud, never silent).

Worked example (from D12m's law): if floor scales as W*T = C/s^2, feed
s-values and floor values; slope should land near -2:
    python tools/power_fit.py --x 0.28,0.56,1.12,2.24 --y 4800,1200,300,75
    -> slope ~ -2.0, R^2 ~ 1.0

Selftest:
    python tools/power_fit.py --selftest

Selftest pins (fail-first): exact-slope recovery on y=x^2, slope ~ -2 on the
docstring example, FAIL-INPUT rc=2 on non-positive x, FAIL-INPUT on non-finite y,
and CI containment (true slope inside the bootstrap interval).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import datetime, timezone


def _ols(xs, ys):
    """Return (slope, intercept, r2) of OLS on (xs, ys). Caller guarantees n>=3."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx <= 0.0:
        raise ValueError("degenerate x: all log(x) identical, slope undefined")
    slope = sxy / sxx
    intercept = my - slope * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return slope, intercept, r2


def parse_nums(spec, name):
    out = []
    for tok in spec.split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            v = float(tok)
        except ValueError:
            raise ValueError(f"{name}: not a number: {tok!r}")
        if not math.isfinite(v):
            raise ValueError(f"{name}: non-finite value {tok!r}")
        out.append(v)
    if not out:
        raise ValueError(f"{name}: empty list")
    return out


def fit_power_law(xs, ys, n_boot=2000, seed=2718):
    """xs, ys: positive finite lists, equal length, n>=3.
    Returns dict receipt. Slope CI via percentile bootstrap on log-log pairs,
    add-one rank so p never claims 0."""
    if len(xs) != len(ys):
        raise ValueError(f"length mismatch: {len(xs)} x vs {len(ys)} y")
    n = len(xs)
    if n < 3:
        raise ValueError(f"n={n} < 3: an exponent fit on fewer points is a guess, not a fit")
    for name, vals in (("x", xs), ("y", ys)):
        for v in vals:
            if not math.isfinite(v) or v <= 0:
                raise ValueError(f"{name}={v}: power-law fit needs strictly positive finite values")
    lx = [math.log(x) for x in xs]
    ly = [math.log(y) for y in ys]
    slope, intercept, r2 = _ols(lx, ly)
    c = math.exp(intercept)

    rng = random.Random(seed)
    pairs = list(zip(lx, ly))
    boots = []
    for _ in range(n_boot):
        samp = [pairs[rng.randrange(n)] for _ in range(n)]
        try:
            b, _, _ = _ols([p[0] for p in samp], [p[1] for p in samp])
        except ValueError:
            continue  # resample collapsed on one x — skip, booked in count
        boots.append(b)
    boots.sort()
    # add-one ranks: CI never claims impossibly tight coverage on small n
    lo_i = max(0, int(0.025 * len(boots)) - 1)
    hi_i = min(len(boots) - 1, int(0.975 * len(boots)))
    ci_lo = boots[lo_i] if boots else None
    ci_hi = boots[hi_i] if boots else None
    return {
        "tool": "power_fit",
        "ts": datetime.now(timezone.utc).isoformat(),
        "n": n,
        "x": xs,
        "y": ys,
        "slope": slope,
        "slope_ci95": [ci_lo, ci_hi],
        "intercept": intercept,
        "C": c,
        "r2": r2,
        "n_boot": n_boot,
        "boot_ok": len(boots),
        "seed": seed,
        "verdict": "FIT",
    }


def selftest():
    checks = []
    # 1: exact slope recovery y = x^2
    xs = [1.0, 2.0, 4.0, 8.0, 16.0]
    r = fit_power_law(xs, [x ** 2 for x in xs], n_boot=500)
    checks.append(("slope==2 exact", abs(r["slope"] - 2.0) < 1e-9))
    # 2: docstring example slope ~ -2
    r2 = fit_power_law([0.28, 0.56, 1.12, 2.24], [4800, 1200, 300, 75], n_boot=500)
    checks.append(("docstring slope~-2", abs(r2["slope"] + 2.0) < 1e-9 and r2["r2"] > 0.999))
    # 3: CI contains true slope (float tolerance — exact data can sit 1 ulp outside)
    lo, hi = r2["slope_ci95"]
    checks.append(("CI contains truth", lo - 1e-9 <= -2.0 <= hi + 1e-9))
    # 4: fail-loud non-positive x
    try:
        fit_power_law([1.0, -2.0, 3.0], [1, 2, 3], n_boot=10)
        checks.append(("nonpositive-x rc2", False))
    except ValueError:
        checks.append(("nonpositive-x rc2", True))
    # 5: fail-loud non-finite y
    try:
        fit_power_law([1.0, 2.0, 3.0], [1.0, float("nan"), 3.0], n_boot=10)
        checks.append(("nan-y rc2", False))
    except ValueError:
        checks.append(("nan-y rc2", True))
    # 6: fail-loud n<3
    try:
        fit_power_law([1.0, 2.0], [1.0, 4.0], n_boot=10)
        checks.append(("n<3 rc2", False))
    except ValueError:
        checks.append(("n<3 rc2", True))

    ok = sum(1 for _, p in checks if p)
    receipt = {
        "tool": "power_fit", "mode": "selftest", "ts": datetime.now(timezone.utc).isoformat(),
        "checks": [{"name": k, "pass": bool(v)} for k, v in checks],
        "passed": ok, "total": len(checks), "verdict": "KEEP" if ok == len(checks) else "KILL",
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if ok == len(checks) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="stdlib log-log power-law fit with bootstrap slope CI and honest receipt",
        epilog="example: python tools/power_fit.py --x 0.28,0.56,1.12,2.24 --y 4800,1200,300,75",
    )
    ap.add_argument("--x", help="independent values, comma-separated (strictly positive)")
    ap.add_argument("--y", help="dependent values, comma-separated (strictly positive)")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=2718)
    ap.add_argument("--out", help="write JSON receipt here (also printed)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    try:
        xs = parse_nums(args.x or "", "--x")
        ys = parse_nums(args.y or "", "--y")
        receipt = fit_power_law(xs, ys, n_boot=args.n_boot, seed=args.seed)
    except ValueError as e:
        receipt = {
            "tool": "power_fit", "ts": datetime.now(timezone.utc).isoformat(),
            "verdict": "FAIL-INPUT", "error": str(e),
        }
        print(json.dumps(receipt, indent=2, sort_keys=True), file=sys.stderr)
        return 2

    print(json.dumps(receipt, indent=2, sort_keys=True))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(receipt, f, indent=2, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
