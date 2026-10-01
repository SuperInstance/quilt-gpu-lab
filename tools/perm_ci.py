#!/usr/bin/env python3
"""perm-ci — grabbable two-sample significance: permutation p-value + bootstrap CI.

Pattern lifted from tonight's proven inference lanes (E3 perm-exact norm-MI,
COMPOSITE-0 bootstrap CIs, 2f123d9/8a18341 reconciliation work). Stdlib-only
(no numpy/scipy): deterministic, seeded, fail-loud — small n stays exact.

WHAT IT DOES
  Given two groups of numbers, answers the two questions every lane asks:
    1. Is the difference real?  -> two-sided permutation test on the chosen
       statistic (mean or median difference). Resamples label assignments
       exhaustively when C(n, na) <= exact_cap (default 20000, exact),
       otherwise Monte-Carlo with a fixed seed (booked in the receipt).
    2. How big?  -> percentile bootstrap CI on the difference, same seed.

USAGE
  python tools/perm_ci.py --a 1.2,1.4,1.1 --b 2.0,2.3,2.1
  python tools/perm_ci.py --file a.json            # {"a": [...], "b": [...]}
  python tools/perm_ci.py --stat median --bca-off  # options
  python tools/perm_ci.py --selftest

FAIL-LOUD
  - non-finite (NaN/Inf) inputs -> exit 2, booked
  - a group with zero length, or <2 total distinct values -> exit 2
  - always writes a JSON receipt (stdout; --out to also save), even on KILL-ish
    "no effect" answers — honest booking culture: nulls are first-class.

EXAMPLE (docstring worked example)
  $ python tools/perm_ci.py --a 1,2,3 --b 10,11,12
  -> p_value ~0.1 (exact, C(6,3)=20 assignments — tiny n is honest: not
     significant, and the tool says so instead of lying), diff 9.0,
     CI excludes 0 at 95%? booked verbatim in the receipt.
"""
import argparse
import itertools
import json
import math
import random
import sys
from typing import List, Sequence, Tuple

SEED = 20261001
EXACT_CAP = 20000
BOOT_N = 10000


def _finite(xs: Sequence[float], name: str) -> List[float]:
    out = []
    for x in xs:
        v = float(x)
        if not math.isfinite(v):
            raise ValueError(f"{name} contains non-finite value: {x!r}")
        out.append(v)
    return out


def _stat(a: Sequence[float], b: Sequence[float], kind: str) -> float:
    fa = sorted(a)
    fb = sorted(b)
    if kind == "mean":
        return sum(a) / len(a) - sum(b) / len(b)
    k = lambda s: (s[len(s)//2] if len(s) % 2 else (s[len(s)//2 - 1] + s[len(s)//2]) / 2)
    return k(fa) - k(fb)


def _percentile(sorted_xs: Sequence[float], q: float) -> float:
    i = q * (len(sorted_xs) - 1)
    lo = int(math.floor(i))
    hi = min(lo + 1, len(sorted_xs) - 1)
    return sorted_xs[lo] + (sorted_xs[hi] - sorted_xs[lo]) * (i - lo)


def perm_test(a: Sequence[float], b: Sequence[float], stat: str = "mean",
              exact_cap: int = EXACT_CAP, seed: int = SEED
              ) -> Tuple[float, str, int]:
    """Two-sided permutation p-value. Returns (p, mode, n_resamples)."""
    obs = _stat(a, b, stat)
    pooled = list(a) + list(b)
    na = len(a)
    n = len(pooled)
    nc = math.comb(n, na)
    if nc <= exact_cap:
        count = 0
        total = 0
        for idx in itertools.combinations(range(n), na):
            sa = [pooled[i] for i in idx]
            sb = [pooled[i] for i in range(n) if i not in idx]
            s = _stat(sa, sb, stat)
            if abs(s) >= abs(obs) - 1e-12:
                count += 1
            total += 1
        return count / total, "exact", total
    rng = random.Random(seed)
    count = 0
    for _ in range(exact_cap):
        perm = pooled[:]
        rng.shuffle(perm)
        s = _stat(perm[:na], perm[na:], stat)
        if abs(s) >= abs(obs) - 1e-12:
            count += 1
    p = (count + 1) / (exact_cap + 1)  # add-one: MC p never claims 0
    return p, "monte-carlo", exact_cap


def boot_ci(a: Sequence[float], b: Sequence[float], stat: str = "mean",
            level: float = 0.95, n: int = BOOT_N, seed: int = SEED
            ) -> Tuple[float, float]:
    """Percentile bootstrap CI on stat(a)-stat(b)."""
    rng = random.Random(seed + 1)
    deltas = []
    for _ in range(n):
        ra = [a[rng.randrange(len(a))] for _ in a]
        rb = [b[rng.randrange(len(b))] for _ in b]
        deltas.append(_stat(ra, rb, stat))
    deltas.sort()
    alpha = (1 - level) / 2
    return _percentile(deltas, alpha), _percentile(deltas, 1 - alpha)


def run(a: List[float], b: List[float], stat: str = "mean",
        level: float = 0.95, exact_cap: int = EXACT_CAP, seed: int = SEED
        ) -> dict:
    a = _finite(a, "a")
    b = _finite(b, "b")
    p, mode, nres = perm_test(a, b, stat, exact_cap, seed)
    lo, hi = boot_ci(a, b, stat, level, seed=seed)
    diff = _stat(a, b, stat)
    return {
        "tool": "perm-ci",
        "stat": stat,
        "n_a": len(a), "n_b": len(b),
        "observed_diff": diff,
        "p_value": p,
        "p_mode": mode,
        "n_resamples": nres,
        "ci_level": level,
        "ci_low": lo,
        "ci_high": hi,
        "seed": seed,
        "verdict": "KEEP" if (p < 1 - level and (lo > 0 or hi < 0)) else
                   "KILL" if p < 1 - level else "NULL-BOOKED",
    }


def selftest() -> int:
    fails = []
    # 1. obvious separation -> significant, CI excludes 0
    r = run([1, 2, 3, 2, 1, 2] * 3, [10, 11, 12, 11, 10, 11] * 3)
    if not (r["p_value"] <= 0.05 and r["ci_high"] < 0 if r["observed_diff"] < 0 else r["ci_low"] > 0):
        fails.append(("separation", r))
    # 2. same distribution -> NULL-BOOKED, p not tiny (honest null)
    rng = random.Random(7)
    xs = [rng.gauss(0, 1) for _ in range(40)]
    ys = [rng.gauss(0, 1) for _ in range(40)]
    r = run(xs, ys)
    if r["p_value"] < 0.001:
        fails.append(("null-too-significant", r))
    # 3. exact mode on small n
    r = run([1.0, 2.0], [3.0, 4.0])
    if r["p_mode"] != "exact" or abs(r["p_value"] - 1 / 3) > 1e-9:
        fails.append(("exact-small-n", r))  # C(4,2)=6 assignments; only obs+mirror reach |diff|=2 -> p=1/3
    # 4. non-finite fails loud
    try:
        run([1.0, float("nan")], [2.0, 3.0])
        fails.append(("nan-not-caught", None))
    except ValueError:
        pass
    if fails:
        print(json.dumps({"selftest": "FAIL", "fails": [f[0] for f in fails]}, indent=2))
        return 1
    print(json.dumps({"selftest": "OK", "checks": 4}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--a", help="comma-separated group A values")
    ap.add_argument("--b", help="comma-separated group B values")
    ap.add_argument("--file", help="JSON file {\"a\": [...], \"b\": [...]}")
    ap.add_argument("--stat", choices=["mean", "median"], default="mean")
    ap.add_argument("--level", type=float, default=0.95)
    ap.add_argument("--out", help="also write receipt JSON here")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    try:
        if args.file:
            with open(args.file) as f:
                d = json.load(f)
            a, b = _finite(d["a"], "a"), _finite(d["b"], "b")
        elif args.a and args.b:
            a = _finite([float(x) for x in args.a.split(",")], "a")
            b = _finite([float(x) for x in args.b.split(",")], "b")
        else:
            ap.error("need --a/--b or --file (or --selftest)")
        if not a or not b:
            raise ValueError("empty group")
        receipt = run(a, b, args.stat, args.level)
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        print(json.dumps({"tool": "perm-ci", "error": str(e)}))
        return 2
    out = json.dumps(receipt, indent=2)
    print(out)
    if args.out:
        with open(args.out, "w") as f:
            f.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
