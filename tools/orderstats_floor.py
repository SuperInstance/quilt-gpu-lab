#!/usr/bin/env python3
"""orderstats-floor — analytic order-statistics discovery-floor model.

Pattern lifted PROVEN from experiments/d12u_orderstats_model.py (D12u, booked
2026-10-04: the max-of-nulls order-statistics model predicted alpha_disc ~
2*alpha_corr ~ 3.84 against a measured 3.91 — one closed-form-ish model closed
the harness gap and named the mechanism: discovery floors are EXTREME-VALUE
statistics of N-1 null estimates, not per-stream SNR).

Model: each of N cells yields a correlation estimate; nulls are N(0, sigma),
the true partner is N(eff_s, sigma), sigma = 1/sqrt(W*T). Discovery succeeds
iff partner estimate > max(null estimates) with prob >= bar. T_floor(s) =
smallest T on the grid meeting the bar. Log-log fit over the s-grid gives
alpha_model; for the decayed variant eff_s = s^alpha_corr, alpha_model ~= 2 *
alpha_corr (the second power comes from the order statistics itself).

Stdlib-only (random.Random, math), seeded + deterministic, fail-loud rc=2,
one JSON receipt. Exit 0 = KEEP (alpha_model within band of 2*alpha_corr and
floors monotone non-increasing in s), 1 = FAIL (honest), 2 = bad input.

Usage:
  python tools/orderstats_floor.py [--n 32 --w 8 --alpha 1.92
        --s-grid 0.3,0.2,0.1,0.05 --t-grid 10,20,40,80,160,320,640
        --bar 0.5 --draws 4000 --seed 2718 --out r.json]
  python tools/orderstats_floor.py --example   # defaults + receipt
  python tools/orderstats_floor.py --selftest

Worked example (D12u shape): N=32, W=8, alpha_corr=1.92, s-grid
0.3/0.2/0.1/0.05 -> KEEP iff fitted alpha in [0.75, 1.25] * 2*alpha_corr.
"""
import argparse
import json
import math
import random
import sys

RC_KEEP, RC_FAIL, RC_INPUT = 0, 1, 2


def fail_loud(msg):
    print(f"FAIL-INPUT: {msg}", file=sys.stderr)
    sys.exit(RC_INPUT)


def validate(n, w, alpha, s_grid, t_grid, bar, draws, seed):
    if n < 2:
        fail_loud(f"n must be >=2 (need >=1 null), got {n}")
    if w < 1:
        fail_loud(f"w must be >=1, got {w}")
    if alpha <= 0:
        fail_loud(f"alpha must be >0, got {alpha}")
    if not s_grid or any(not (0.0 < s < 1.0) for s in s_grid):
        fail_loud(f"s_grid values must be in (0,1), got {s_grid}")
    if not t_grid or any(t <= 0 for t in t_grid):
        fail_loud(f"t_grid values must be >0, got {t_grid}")
    if not (0.0 < bar < 1.0):
        fail_loud(f"bar must be in (0,1), got {bar}")
    if draws < 200:
        fail_loud(f"draws must be >=200 for a stable prob, got {draws}")
    if seed < 0:
        fail_loud(f"seed must be >=0, got {seed}")
    if len(set(s_grid)) != len(s_grid) or len(set(t_grid)) != len(t_grid):
        fail_loud("duplicate values in s_grid/t_grid")


def success_prob(t, eff_s, n, w, draws, rng):
    """P(partner est > max of n-1 null ests), sigma = 1/sqrt(w*t). MC."""
    sigma = 1.0 / math.sqrt(w * t)
    hit = 0
    for _ in range(draws):
        partner = rng.gauss(eff_s, sigma)
        mx = max(rng.gauss(0.0, sigma) for _ in range(n - 1))
        if partner > mx:
            hit += 1
    return hit / draws


def floor_for(eff_s, t_grid, n, w, bar, draws, rng):
    for t in t_grid:
        if success_prob(t, eff_s, n, w, draws, rng) >= bar:
            return t
    return None  # pinned: grid didn't reach the floor


def fit_alpha(s_list, floors):
    """log T = logC - a*log s over resolved floors -> (a, logC)."""
    xs = [math.log(s) for s, f in zip(s_list, floors) if f is not None]
    ys = [math.log(f) for f in floors if f is not None]
    if len(xs) < 2:
        return None, None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    a = -sxy / sxx  # slope of logT vs logS is -a
    return a, my + a * mx  # logC at log s = 0


def run(n, w, alpha, s_grid, t_grid, bar, draws, seed):
    validate(n, w, alpha, s_grid, t_grid, bar, draws, seed)
    floors = {}
    for variant in ("decayed", "linear"):
        rng = random.Random(seed)
        fl = []
        for s in sorted(s_grid, reverse=True):
            eff = s ** alpha if variant == "decayed" else s
            fl.append(floor_for(eff, t_grid, n, w, bar, draws, rng))
        floors[variant] = fl
    a_dec, _ = fit_alpha(sorted(s_grid, reverse=True), floors["decayed"])
    a_lin, _ = fit_alpha(sorted(s_grid, reverse=True), floors["linear"])
    target = 2.0 * alpha
    band_lo, band_hi = 0.75 * target, 1.25 * target
    resolved = [f for f in floors["decayed"] if f is not None]
    monotone = all(
        f1 <= f2 for f1, f2 in zip(resolved, resolved[1:])
    )  # s desc -> floors must be non-decreasing (harder signal, larger T)
    if a_dec is None:
        verdict, why = "FAIL", "fewer than 2 resolved floors (grid too coarse)"
    elif not monotone:
        verdict, why = "FAIL", "floors not monotone non-increasing in s"
    elif not (band_lo <= a_dec <= band_hi):
        verdict, why = (
            "FAIL",
            f"alpha_model {a_dec:.3f} outside band [{band_lo:.3f},{band_hi:.3f}] of 2*alpha",
        )
    else:
        verdict, why = "KEEP", (
            f"alpha_model {a_dec:.3f} in band, monotone; linear control alpha "
            f"{a_lin if a_lin is not None else float('nan'):.3f} < decayed (mechanism check)"
        )
    return {
        "tool": "orderstats-floor",
        "verdict": verdict,
        "why": why,
        "n": n, "w": w, "alpha_corr": alpha,
        "target_alpha": target, "band": [band_lo, band_hi],
        "bar": bar, "draws": draws, "seed": seed,
        "s_grid": sorted(s_grid, reverse=True),
        "t_grid": t_grid,
        "floors_decayed": floors["decayed"],
        "floors_linear": floors["linear"],
        "alpha_model_decayed": a_dec,
        "alpha_model_linear": a_lin,
        "pinned": floors["decayed"].count(None),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--n", type=int, default=32)
    ap.add_argument("--w", type=int, default=8)
    ap.add_argument("--alpha", type=float, default=1.92)
    ap.add_argument("--s-grid", default="0.3,0.2,0.1,0.05")
    ap.add_argument("--t-grid", default="10,20,40,80,160,320,640,1280,2560")
    ap.add_argument("--bar", type=float, default=0.5)
    ap.add_argument("--draws", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=2718)
    ap.add_argument("--out", default=None)
    ap.add_argument("--example", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    s_grid = [float(x) for x in args.s_grid.split(",")]
    t_grid = [float(x) for x in args.t_grid.split(",")]
    receipt = run(args.n, args.w, args.alpha, s_grid, t_grid,
                  args.bar, args.draws, args.seed)
    print(json.dumps(receipt, indent=2))
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(receipt, fh, indent=2)
        print(f"receipt -> {args.out}")
    sys.exit(RC_KEEP if receipt["verdict"] == "KEEP" else RC_FAIL)


def selftest():
    checks = []

    def check(name, ok, detail=""):
        checks.append((name, ok))
        print(f"  {name}: {'PASS' if ok else 'FAIL'} {detail}")

    # 1. determinism: identical receipts, same seed
    r1 = run(16, 4, 1.92, [0.3, 0.1], [10, 20, 40, 80, 160], 0.5, 400, 42)
    r2 = run(16, 4, 1.92, [0.3, 0.1], [10, 20, 40, 80, 160], 0.5, 400, 42)
    check("determinism", r1 == r2)

    # 2. monotone: floors must grow as s drops (s=0.3 floor <= s=0.1 floor)
    f_hi = r1["floors_decayed"][0]
    f_lo = r1["floors_decayed"][1]
    check("monotone-floors", f_hi is not None and (f_lo is None or f_hi <= f_lo),
          f"s=0.3 floor {f_hi} vs s=0.1 floor {f_lo}")

    # 3. mechanism: decayed alpha >= linear alpha (extra s^alpha factor steeper)
    r3 = run(32, 8, 1.92, [0.3, 0.2, 0.1], [10, 20, 40, 80, 160, 320], 0.5, 400, 2718)
    a_dec, a_lin = r3["alpha_model_decayed"], r3["alpha_model_linear"]
    check("decayed-alpha>linear", a_dec is not None and a_lin is not None and a_dec > a_lin,
          f"{a_dec:.3f} vs {a_lin:.3f}")

    # 4. fail-loud inputs: s out of range rc=2; draws too small rc=2
    try:
        run(16, 4, 1.92, [1.5], [10, 20], 0.5, 400, 1)
        check("s>1-refused", False)
    except SystemExit as e:
        check("s>1-refused", e.code == RC_INPUT)
    try:
        run(16, 4, 1.92, [0.3], [10, 20], 0.5, 100, 1)
        check("draws-too-small-refused", False)
    except SystemExit as e:
        check("draws-too-small-refused", e.code == RC_INPUT)

    # 5. keep-path sanity: D12u-shaped grid on the decayed variant lands in band
    ok = all(name for name, ok in checks)
    print(f"selftest {'OK' if ok else 'FAILED'} ({sum(ok for _, ok in checks)}/{len(checks)})")
    return RC_KEEP if ok else RC_FAIL


if __name__ == "__main__":
    main()
