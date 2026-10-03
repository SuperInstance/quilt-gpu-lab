#!/usr/bin/env python3
"""holdout-gate — held-out prediction gate for power-law bounds (stdlib-only).

Pattern lifted PROVEN from D12o (results/d12o_law_p_generalization.json) and
D12p (experiments/d12p_cp_fit.py): a fitted bound is only trusted after it
PREDICTS points it never saw. Given measured floors y at drivers x and a law
y <= C / x^alpha, fit C on the FIT subset only (conservative max, the D12o
recipe), then gate on the held-out points:

  G1 coverage     — every held-out point satisfies y <= C_fit / x^alpha.
  G2 non-vacuous  — the tightest held-out ratio y*x^alpha / C_fit >= min_ratio
                    (default 0.02). A bound 100x loose predicts everything and
                    is vacuous; D12p books that as a fail, and so do we.

Why grabbable: "did the fitted constant actually generalize?" recurs across
scaling-law lanes (D12l/D12m/D12o/D12p, ramp curves) and this is the one-file
verdict: PASS (both gates), FAIL (a gate trips — booked, first-class), or
FAIL-INPUT (no fit points, no held-out points, non-finite / non-positive
values, alpha < 0). Exit 0 / 1 / 2. One JSON receipt either way. Seeded
bootstrap on the ratio is deterministic; no numpy, no deps.

Usage:
  python tools/holdout_gate.py \
      --pairs '[{"x":0.28,"y":100,"role":"fit"},
                {"x":0.56,"y":300,"role":"fit"},
                {"x":1.12,"y":900,"role":"hold"},
                {"x":2.24,"y":2600,"role":"hold"}]' \
      --alpha 1.5 --out r.json
  python tools/holdout_gate.py --pairs-file pairs.json --alpha 2.0
  python tools/holdout_gate.py --selftest

Worked example: y = 400/x^1.5 measured with noise; the fit subset pins
C near 400, held-out points clear coverage and the ratio stays > 0.02 ->
PASS. Halve C in the data (law broke at scale) -> held-out coverage trips
-> FAIL rc=1. Selftest pins both directions fail-first.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import datetime, timezone

DEFAULT_MIN_RATIO = 0.02
SEED = 2718


def fail_input(msg: str) -> None:
    print(json.dumps({"verdict": "FAIL-INPUT", "error": msg},
                     sort_keys=True), file=sys.stderr)
    sys.exit(2)


def parse_pairs(raw: str) -> list:
    try:
        pairs = json.loads(raw)
    except json.JSONDecodeError as e:
        fail_input(f"pairs not valid JSON: {e}")
    _validate(pairs)
    return pairs


def _validate(pairs) -> None:
    if not isinstance(pairs, list) or not pairs:
        fail_input("pairs must be a non-empty JSON list")
    roles = set()
    for i, p in enumerate(pairs):
        if not isinstance(p, dict) or not {"x", "y", "role"} <= set(p):
            fail_input(f"pair {i} needs x, y, role keys")
        for k in ("x", "y"):
            v = p[k]
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                fail_input(f"pair {i}.{k} not a number")
            if not math.isfinite(v) or v <= 0:
                fail_input(f"pair {i}.{k}={v} must be finite and > 0 "
                           "(law domain is positive reals)")
        if p["role"] not in ("fit", "hold"):
            fail_input(f"pair {i}.role must be 'fit' or 'hold'")
        roles.add(p["role"])
    if "fit" not in roles:
        fail_input("no 'fit' points: cannot fit C")
    if "hold" not in roles:
        fail_input("no 'hold' points: a gate with nothing held out is a "
                   "tautology, VOID — never PASS")


def run_gate(pairs: list, alpha: float, min_ratio: float,
             bootstrap: int = 2000) -> dict:
    if not math.isfinite(alpha) or alpha < 0:
        fail_input(f"alpha={alpha} must be finite and >= 0")
    if not math.isfinite(min_ratio) or min_ratio <= 0:
        fail_input(f"min_ratio={min_ratio} must be finite and > 0")

    fits = [(p["x"], p["y"]) for p in pairs if p["role"] == "fit"]
    holds = [(p["x"], p["y"]) for p in pairs if p["role"] == "hold"]
    for i, (x, y) in enumerate(fits + holds):
        for k, v in (("x", x), ("y", y)):
            if not math.isfinite(v) or v <= 0:
                fail_input(f"point {i}.{k}={v} must be finite and > 0 "
                           "(law domain is positive reals)")
    if not holds:
        fail_input("no 'hold' points: a gate with nothing held out is a "
                   "tautology, VOID — never PASS")
    if not fits:
        fail_input("no 'fit' points: cannot fit C")

    # D12o recipe: conservative C = max measured y * x^alpha over fit subset.
    c_emp = {i: y * x ** alpha for i, (x, y) in enumerate(fits)}
    c_fit = max(c_emp.values())

    results = []
    for x, y in holds:
        bound = c_fit / x ** alpha
        ratio = y * x ** alpha / c_fit
        results.append({"x": x, "y": y, "bound": bound, "ratio": ratio,
                        "covered": y <= bound})

    coverage_ok = all(r["covered"] for r in results)
    tightest = min(r["ratio"] for r in results)
    nonvacuous_ok = tightest >= min_ratio
    verdict = "PASS" if (coverage_ok and nonvacuous_ok) else "FAIL"

    # Deterministic bootstrap on the tightest ratio: drop each fit point in
    # resamples, refit C, recompute tightest held-out ratio -> stability CI.
    rng = random.Random(SEED)
    boot = []
    for _ in range(bootstrap):
        sample = [fits[rng.randrange(len(fits))] for _ in fits]
        c_b = max(y * x ** alpha for x, y in sample)
        boot.append(min(y * x ** alpha / c_b for x, y in holds))
    boot.sort()
    lo = boot[int(0.025 * (bootstrap - 1))]
    hi = boot[int(0.975 * (bootstrap - 1))]

    return {
        "tool": "holdout_gate",
        "ts": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "alpha": alpha,
        "c_fit": c_fit,
        "c_source": "max over fit subset (D12o conservative recipe)",
        "min_ratio": min_ratio,
        "gates": {
            "G1_coverage": {"pass": coverage_ok,
                            "violations": [r for r in results if not r["covered"]]},
            "G2_nonvacuous": {"pass": nonvacuous_ok,
                              "tightest_ratio": tightest,
                              "ratio_ci95_seeded": [lo, hi]},
        },
        "heldout": results,
        "n_fit": len(fits),
        "n_hold": len(holds),
    }


def selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        ok = ok and cond

    # Pin 1: clean law y = 400/x^1.5, fit + hold -> PASS, CI brackets ratio.
    pairs = [{"x": 0.25, "y": 400 / 0.25 ** 1.5, "role": "fit"},
             {"x": 0.5, "y": 400 / 0.5 ** 1.5, "role": "fit"},
             {"x": 1.0, "y": 400 / 1.0 ** 1.5, "role": "hold"},
             {"x": 4.0, "y": 400 / 4.0 ** 1.5, "role": "hold"}]
    r = run_gate(pairs, 1.5, DEFAULT_MIN_RATIO)
    check("clean law PASS", r["verdict"] == "PASS")
    check("CI contains tightest ratio",
          r["gates"]["G2_nonvacuous"]["ratio_ci95_seeded"][0]
          <= r["gates"]["G2_nonvacuous"]["tightest_ratio"]
          <= r["gates"]["G2_nonvacuous"]["ratio_ci95_seeded"][1])

    # Pin 2: law breaks at scale (C doubles beyond the fit range) -> FAIL on G1.
    pairs2 = [dict(pairs[0]), dict(pairs[1]),
              {"x": 1.0, "y": 800 / 1.0 ** 1.5, "role": "hold"},
              {"x": 4.0, "y": 800 / 4.0 ** 1.5, "role": "hold"}]
    r2 = run_gate(pairs2, 1.5, DEFAULT_MIN_RATIO)
    check("law-break FAIL on coverage",
          r2["verdict"] == "FAIL" and not r2["gates"]["G1_coverage"]["pass"])

    # Pin 3: vacuous bound (held-out absurdly loose vs fit C) -> FAIL on G2.
    pairs3 = [dict(pairs[0]), dict(pairs[1]),
              {"x": 1.0, "y": 0.0001, "role": "hold"}]
    r3 = run_gate(pairs3, 1.5, DEFAULT_MIN_RATIO)
    check("vacuous bound FAIL on G2",
          r3["verdict"] == "FAIL" and not r3["gates"]["G2_nonvacuous"]["pass"])

    # Pin 4: no hold points is VOID (rc=2), not PASS.
    try:
        run_gate([dict(pairs[0]), dict(pairs[1])], 1.5, DEFAULT_MIN_RATIO)
        check("no-hold VOID rc=2", False)
    except SystemExit as e:
        check("no-hold VOID rc=2", e.code == 2)

    # Pin 5: non-finite/non-positive input rc=2.
    try:
        run_gate([{"x": -1, "y": 1, "role": "fit"},
                  {"x": 1, "y": 1, "role": "hold"}], 1.5, DEFAULT_MIN_RATIO)
        check("negative x rc=2", False)
    except SystemExit as e:
        check("negative x rc=2", e.code == 2)

    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(
        description="held-out prediction gate for power-law bounds y <= C/x^alpha")
    ap.add_argument("--pairs", help="JSON list of {x, y, role:'fit'|'hold'}")
    ap.add_argument("--pairs-file", help="same JSON from a file")
    ap.add_argument("--alpha", type=float, default=None,
                    help="known exponent in y <= C / x^alpha")
    ap.add_argument("--min-ratio", type=float, default=DEFAULT_MIN_RATIO,
                    help=f"G2 floor, default {DEFAULT_MIN_RATIO}")
    ap.add_argument("--out", help="write JSON receipt here (also stdout summary)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if args.alpha is None:
        ap.error("--alpha is required (unless --selftest)")

    if args.pairs_file:
        try:
            with open(args.pairs_file) as f:
                pairs = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            fail_input(f"cannot read pairs file: {e}")
        _validate(pairs)
    elif args.pairs:
        pairs = parse_pairs(args.pairs)
    else:
        ap.error("one of --pairs / --pairs-file / --selftest is required")

    receipt = run_gate(pairs, args.alpha, args.min_ratio)
    if args.out:
        with open(args.out, "w") as f:
            json.dump(receipt, f, indent=2, sort_keys=True)
        receipt["receipt_path"] = args.out
    print(json.dumps(receipt, indent=2, sort_keys=True))
    sys.exit(0 if receipt["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
