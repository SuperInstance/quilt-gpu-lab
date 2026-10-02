#!/usr/bin/env python3
"""ci_gate — paired bootstrap CI gate for KEEP/KILL decisions (stdlib-only).

Lifted from the B1H-CODA tail-gate pattern (2026-10-01): two paired score
vectors (baseline vs treatment), bootstrap the mean delta, PASS only if the
CI excludes 0 at the frozen confidence level. No numpy needed — deliberate,
so it runs anywhere the fleet runs.

Verdicts (fail-loud, never silent):
    FAIL-INPUT   length mismatch, n < min_n, non-finite scores
    FAIL         CI contains 0 (delta not distinguishable from noise)
    PASS         CI excludes 0

Usage:
    python tools/ci_gate.py --base 0.61,0.55,0.70 --treat 0.65,0.53,0.82
    python tools/ci_gate.py --pairs-file scores.json --alpha 0.05 --n 10000 --seed 7
      # scores.json: {"base": [...], "treat": [...]}

Worked example (docstring selftest):
    base  = [0.50, 0.52, 0.48, 0.51, 0.49, 0.53, 0.50, 0.47, 0.52, 0.50]
    treat = base shifted +0.10 on every item  ->  every delta +0.10, CI cannot
    contain 0  ->  PASS. Flip the sign  ->  FAIL.

Exit codes: 0 = PASS, 1 = FAIL (gate), 2 = FAIL-INPUT.
JSON receipt printed to stdout; never prints secrets (takes none).
"""

import argparse
import json
import math
import random
import sys


def fail_input(msg: str) -> "None":
    print(json.dumps({"tool": "ci_gate", "verdict": "FAIL-INPUT", "error": msg}))
    sys.exit(2)


def bootstrap_ci(deltas, n_boot, alpha, rng):
    m = len(deltas)
    lows, highs = [], []
    stats = []
    for _ in range(n_boot):
        s = 0.0
        for _ in range(m):
            s += deltas[rng.randrange(m)]
        stats.append(s / m)
    stats.sort()
    lo_idx = int(math.floor((alpha / 2) * n_boot))
    hi_idx = int(math.ceil((1 - alpha / 2) * n_boot)) - 1
    return stats[max(0, lo_idx)], stats[min(n_boot - 1, hi_idx)]


def run_gate(base, treat, n_boot=5000, alpha=0.05, seed=0, min_n=5):
    if len(base) != len(treat):
        fail_input(f"length mismatch: base={len(base)} treat={len(treat)}")
    if len(base) < min_n:
        fail_input(f"n={len(base)} < min_n={min_n}")
    for v in base + treat:
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            fail_input("non-finite or non-numeric score present")
    deltas = [t - b for b, t in zip(base, treat)]
    mean_delta = sum(deltas) / len(deltas)
    rng = random.Random(seed)
    lo, hi = bootstrap_ci(deltas, n_boot, alpha, rng)
    # Gate semantics: PASS = CI excludes 0 in the POSITIVE direction (gain).
    # A fully-negative CI is a real (negative) effect => FAIL, not PASS.
    excludes_zero_positive = lo > 0
    return {
        "tool": "ci_gate",
        "verdict": "PASS" if excludes_zero_positive else "FAIL",
        "n": len(deltas),
        "mean_delta": round(mean_delta, 6),
        "ci_low": round(lo, 6),
        "ci_high": round(hi, 6),
        "alpha": alpha,
        "n_boot": n_boot,
        "seed": seed,
    }


def main():
    ap = argparse.ArgumentParser(description="Paired bootstrap CI gate (KEEP/KILL)")
    ap.add_argument("--base", help="comma-separated baseline scores")
    ap.add_argument("--treat", help="comma-separated treatment scores")
    ap.add_argument("--pairs-file", help='JSON {"base": [...], "treat": [...]}')
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--n", type=int, default=5000, help="bootstrap resamples")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--min-n", type=int, default=5)
    ap.add_argument("--selftest", action="store_true", help="run docstring example")
    args = ap.parse_args()

    if args.selftest:
        base = [0.50, 0.52, 0.48, 0.51, 0.49, 0.53, 0.50, 0.47, 0.52, 0.50]
        up = run_gate(base, [x + 0.10 for x in base], args.n, args.alpha, args.seed, args.min_n)
        dn = run_gate(base, [x - 0.10 for x in base], args.n, args.alpha, args.seed, args.min_n)
        ok = up["verdict"] == "PASS" and dn["verdict"] == "FAIL"
        print(json.dumps({"selftest": "OK" if ok else "BROKEN", "up": up, "down": dn}))
        sys.exit(0 if ok else 1)

    if args.pairs_file:
        with open(args.pairs_file) as f:
            d = json.load(f)
        if not isinstance(d.get("base"), list) or not isinstance(d.get("treat"), list):
            fail_input("pairs-file needs {'base': [...], 'treat': [...]}")
        base, treat = d["base"], d["treat"]
    elif args.base and args.treat:
        try:
            base = [float(x) for x in args.base.split(",")]
            treat = [float(x) for x in args.treat.split(",")]
        except ValueError as e:
            fail_input(f"bad score list: {e}")
    else:
        ap.error("need --base/--treat or --pairs-file (or --selftest)")

    r = run_gate(base, treat, args.n, args.alpha, args.seed, args.min_n)
    print(json.dumps(r))
    sys.exit(0 if r["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
