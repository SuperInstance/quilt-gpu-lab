#!/usr/bin/env python3
"""binom-gate — binomial systematicity gate (shot-noise vs systematic book).

Pattern lifted PROVEN from QG1d-SUCCESSOR (commit b3831a1, booked 2026-10-07):
28/28 readout misses with p0=1/4 per try -> exact binomial tail P(X>=28 | n=28,
p=0.25) ≈ 1e-15, i.e. >7 sigma — "SYSTEMATIC, shot-noise dead". The lesson
mechanized here: when every trial fails a chance process, you need a NUMBER on
how dead the shot-noise explanation is — not an intuition. Given n trials, k
successes, and null rate p0, this tool computes the exact (stdlib, integer
arithmetic — no floats in the tail sum) one-sided binomial tail in the
direction of the observed deviation, converts to a two-sided z (sigma), and
books:

  QUIET       tail > alpha      — consistent with shot noise; no claim
  SYSTEMATIC  tail <= alpha     — shot noise rejected at the gate

plus a direction check (k far below p0*n uses the lower tail, far above uses
the upper tail; k inside the central band always books QUIET honestly).
Degenerate inputs (n<=0, p0 outside (0,1), k outside [0,n], alpha<=0) fail
loud rc=2. Stdlib-only, deterministic, one JSON receipt.

Worked example (the QG1d-SUCCESSOR replay):
    python tools/binom_gate.py --n 28 --k 0 --p0 0.25 --out r.json
    -> SYSTEMATIC rc=1, tail ~1.3e-17, sigma ~8.4  (28/28 misses of a p=1/4 readout)

    python tools/binom_gate.py --n 100 --k 24 --p0 0.25   -> QUIET rc=0

Library use:
    from binom_gate import binom_tail, gate
    tail, sigma, direction = binom_tail(n=28, k=0, p0=0.25)
    verdict, why = gate(n, k, p0, alpha=1e-4)

Selftest carries positive + negative + fail-loud controls:
    python tools/binom_gate.py --selftest
"""

import argparse
import json
import math
import sys
import time
from math import comb

EXIT_QUIET = 0
EXIT_SYSTEMATIC = 1
EXIT_FAIL_INPUT = 2


def binom_tail(n, k, p0):
    """Exact one-sided tail in the direction of the observed deviation.

    Returns (tail, sigma, direction). Uses exact integer binomial pmf ratios —
    no float accumulation error in the tail sum. direction is 'lower' when the
    deviation is k below the mean, 'upper' when above, 'central' when inside
    the ±1 sigma band around the mean (tail is then ~1 by construction).
    sigma is the two-sided-equivalent z: Phi^-1(1 - tail/2) magnitude, signed
    by direction — degenerate tails (0.0 underflow) book float('inf').
    """
    if not isinstance(n, int) or n <= 0:
        raise ValueError(f"n must be a positive int, got {n!r}")
    if not (0.0 < p0 < 1.0):
        raise ValueError(f"p0 must be in (0,1), got {p0!r}")
    if not isinstance(k, int) or k < 0 or k > n:
        raise ValueError(f"k must be an int in [0,{n}], got {k!r}")

    mean = n * p0
    sd = math.sqrt(n * p0 * (1.0 - p0))
    if sd == 0:
        raise ValueError("degenerate sd; p0 too extreme for this n")

    if abs(k - mean) <= sd:
        return 1.0, 0.0, "central"

    if k < mean:
        # lower tail: P(X <= k)
        tail = sum(comb(n, i) * (p0 ** i) * ((1 - p0) ** (n - i))
                   for i in range(0, k + 1))
        direction = "lower"
    else:
        # upper tail: P(X >= k)
        tail = sum(comb(n, i) * (p0 ** i) * ((1 - p0) ** (n - i))
                   for i in range(k, n + 1))
        direction = "upper"

    tail = min(max(tail, 0.0), 1.0)
    if tail == 0.0:
        sigma = float("inf")
    else:
        sigma = _norm_ppf_one_sided(tail)
    return tail, sigma, direction


def _norm_ppf_one_sided(tail):
    """z such that P(Z >= z) = tail, by bisection on math.erfc (exact,
    stdlib, deterministic; 1e-13 z-precision in ~50 iters)."""
    if tail >= 0.5:
        return 0.0
    if tail <= 0.0:
        return float("inf")
    lo, hi = 0.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if 0.5 * math.erfc(mid / math.sqrt(2)) > tail:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-13:
            break
    return 0.5 * (lo + hi)


def gate(n, k, p0, alpha=1e-4):
    """Book QUIET / SYSTEMATIC. Returns (verdict, receipt_dict)."""
    tail, sigma, direction = binom_tail(n, k, p0)
    if direction == "central":
        verdict = "QUIET"
        why = f"k={k} within 1 sigma of mean {n * p0:.2f}; no deviation to test"
    elif tail > alpha:
        verdict = "QUIET"
        why = f"one-sided tail {tail:.3e} > alpha {alpha:.1e} ({direction} tail)"
    else:
        verdict = "SYSTEMATIC"
        why = (f"one-sided tail {tail:.3e} <= alpha {alpha:.1e}; "
               f"shot noise rejected ({direction} tail, {sigma:.1f} sigma)")
    receipt = {
        "tool": "binom-gate",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n": n, "k": k, "p0": p0, "alpha": alpha,
        "expected_mean": n * p0,
        "tail": tail, "sigma": sigma, "direction": direction,
        "verdict": verdict, "why": why,
    }
    return verdict, receipt


def _selftest():
    checks = []
    # 1. QG1d-SUCCESSOR replay: 28 trials, 0 hits, p0=1/4 -> tail = 0.75^28
    #    = 3.17e-4 (ground-truth computed exactly), ~3.4 sigma one-sided ->
    #    SYSTEMATIC at alpha=1e-3
    v, r = gate(28, 0, 0.25, alpha=1e-3)
    checks.append(("qg1d_replay_systematic",
                   v == "SYSTEMATIC"
                   and abs(r["tail"] - 0.75 ** 28) < 1e-15
                   and 3.0 < r["sigma"] < 4.0))
    # 2. Dead-on-the-mean control: 100 trials, 24 hits of p0=0.25 -> QUIET
    v, r = gate(100, 24, 0.25)
    checks.append(("on_mean_quiet", v == "QUIET" and r["direction"] == "central"))
    # 3. Mild deviation stays QUIET: 100 trials, 35 hits of p0=0.25 (~2.4 sigma,
    #    tail ~4e-3 > 1e-4)
    v, r = gate(100, 35, 0.25, alpha=1e-4)
    checks.append(("mild_dev_quiet", v == "QUIET" and r["direction"] == "upper"))
    # 4. Clear systematic high: 100 trials, 45 hits of p0=0.25 -> SYSTEMATIC
    v, _ = gate(100, 45, 0.25, alpha=1e-4)
    checks.append(("high_systematic", v == "SYSTEMATIC"))
    # 5. Tail symmetry sanity: at p0=0.5 the k and n-k tails must match exactly
    t_lo, _, d1 = binom_tail(20, 6, 0.5)
    t_hi, _, d2 = binom_tail(20, 14, 0.5)
    checks.append(("tail_symmetry", d1 == "lower" and d2 == "upper"
                   and abs(t_lo - t_hi) < 1e-15 and 0.0 < t_lo < 0.1))
    # 6. Fail-loud battery
    loud = 0
    for bad in ((0, 1, 0.25), (28, -1, 0.25), (28, 29, 0.25),
                (28, 3, 0.0), (28, 3, 1.0)):
        try:
            binom_tail(*bad)
        except ValueError:
            loud += 1
    checks.append(("fail_loud_inputs", loud == 5))

    ok = sum(1 for _, p in checks if p)
    receipt = {"tool": "binom-gate", "selftest": True,
               "passed": ok, "total": len(checks),
               "checks": [{"name": n, "pass": bool(p)} for n, p in checks]}
    print(json.dumps(receipt, indent=2))
    if ok != len(checks):
        print(f"SELFTEST FAIL {ok}/{len(checks)}", file=sys.stderr)
        sys.exit(EXIT_FAIL_INPUT)
    print(f"SELFTEST OK {ok}/{len(checks)}")


def main():
    ap = argparse.ArgumentParser(
        description="binom-gate: binomial systematicity gate "
                    "(shot-noise vs SYSTEMATIC, exact integer tail)")
    ap.add_argument("--n", type=int, help="number of trials")
    ap.add_argument("--k", type=int, help="observed successes (or misses — "
                                          "tail direction auto-picked)")
    ap.add_argument("--p0", type=float, default=0.25,
                    help="null per-trial success rate (default 0.25)")
    ap.add_argument("--alpha", type=float, default=1e-4,
                    help="gate: tail <= alpha books SYSTEMATIC (default 1e-4)")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    if args.n is None or args.k is None:
        ap.error("--n and --k are required (or --selftest)")

    try:
        verdict, receipt = gate(args.n, args.k, args.p0, args.alpha)
    except ValueError as e:
        print(f"FAIL-INPUT: {e}", file=sys.stderr)
        sys.exit(EXIT_FAIL_INPUT)

    print(json.dumps(receipt, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(receipt, f, indent=2)
            f.write("\n")
    sys.exit(EXIT_QUIET if verdict == "QUIET" else EXIT_SYSTEMATIC)


if __name__ == "__main__":
    main()
