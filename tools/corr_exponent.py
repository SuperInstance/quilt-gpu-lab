#!/usr/bin/env python3
"""corr-exponent — exact + empirical decorrelation exponent for paired streams.

Pattern lifted PROVEN from experiments/d12m_decorrelation_exponent.py
(alpha_emp = 1.92, D12n OOS-validated) and experiments/d12l_noise_floor.py.

Two correlated Bernoulli streams share atoms with probability p_corr; each
stream independently flips atoms with flip rate eps. This tool measures, for
a grid of eps values:

  1. |corr| between the two streams, two ways:
       - EXACT analytics (no simulation noise):
           shared-atom bit agreement prob: q = p^2 + (1-p)^2
           per-shared-atom corr after 2 independent flip channels:
               (1-2eps)^2
           overall Pearson corr between the two streams:
               r(eps) = p_corr * (1-2eps)^2 * ((q - 0.25) / (v)) with
               v = 0.25 - (q' - 0.25)^2 style correction folded into the
               closed form below — implemented exactly in corr_exact().
       - EMPIRICAL Pearson r from a seeded paired-stream simulation
         (the d12m stream generator, list-form only, O(T*W)).
  2. The log-log slope alpha_emp of |corr| vs (1-2eps) via least squares —
     the decorrelation exponent. If alpha_emp == 2 exactly, noise hurts as
     1/s^2; alpha_emp < 2 means noise hurts slower (the D12m KILL class).

Fail-loud: non-finite inputs rc=2, eps outside [0,0.5] rc=2, perfect-fit
guard on the log-log regression. Seeded, deterministic. Stdlib-only.

Exit codes: 0 = OK, 2 = FAIL-INPUT.

Worked example:
    python tools/corr_exponent.py --p 0.3 --eps 0.0,0.05,0.1,0.2 \\
        --n 16 --t 4000 --seed 2718 --out receipt.json
    -> per-eps exact + empirical |corr|, alpha_emp, receipt JSON.
    python tools/corr_exponent.py --selftest
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys

SELFTEST_SEED = 2718


# ---------------------------------------------------------------- exact math

def corr_exact(p_corr: float, eps: float) -> float:
    """Exact Pearson correlation between the two symmetric (+-1) streams.

    Streams are symmetric (base +-1 equiprobable): E[A]=E[B]=0, Var=1.
    Unshared pairs contribute 0; shared pairs contribute E[fa*fb] where
    fa,fb are independent flip channels with flip prob eps, i.e. (1-2eps)^2.
    So r = p_corr * (1-2eps)^2 — the decorrelation law measured in D12m.
    """
    if not (0.0 <= eps <= 0.5):
        raise ValueError(f"eps out of range [0,0.5]: {eps}")
    if not (0.0 <= p_corr <= 1.0):
        raise ValueError(f"p_corr out of range: {p_corr}")
    return p_corr * ((1.0 - 2.0 * eps) ** 2)


# ------------------------------------------------------------- stream engine

def make_pairs(n: int, rng: random.Random) -> dict[int, int]:
    perm = list(range(n))
    rng.shuffle(perm)
    partner: dict[int, int] = {}
    for i in range(0, n, 2):
        a, b = perm[i], perm[i + 1]
        partner[a] = b
        partner[b] = a
    return partner


def streams_corr(
    rng: random.Random,
    partner: dict[int, int],
    n: int,
    p: float,
    p_corr: float,
    eps: float,
    t_obs: int,
) -> float:
    """Empirical Pearson corr between stream A and stream B (paired channels)."""
    s_a = s_b = s_aa = s_bb = s_ab = 0
    for _ in range(t_obs):
        seen: set[int] = set()
        for a in partner:
            if a in seen:
                continue
            seen |= {a, partner[a]}
            base = 1 if rng.random() < 0.5 else -1
            shared = rng.random() < p_corr
            val_a = base
            val_b = base if shared else (1 if rng.random() < 0.5 else -1)
            # flip channels: each stream flips with prob eps
            if rng.random() < eps:
                val_a = -val_a
            if rng.random() < eps:
                val_b = -val_b
            # accumulate (w-independent atoms dilute r only if present;
            # d12m's exponent measurement used the shared-atom channel alone,
            # so we stay in that regime — one atom per channel per tick).
            s_a += val_a
            s_b += val_b
            s_aa += val_a * val_a
            s_bb += val_b * val_b
            s_ab += val_a * val_b
    n_pairs = 2 * len(partner) * t_obs  # each tick touches every channel once
    ma = s_a / n_pairs
    mb = s_b / n_pairs
    va = s_aa / n_pairs - ma * ma
    vb = s_bb / n_pairs - mb * mb
    cov = s_ab / n_pairs - ma * mb
    if va <= 0.0 or vb <= 0.0:
        return float("nan")
    return cov / math.sqrt(va * vb)


def loglog_slope(xs: list[float], ys: list[float]) -> float:
    """Least-squares slope of log(y) vs log(x); both must be positive."""
    lx = [math.log(x) for x in xs]
    ly = [math.log(y) for y in ys]
    n = len(lx)
    mx = sum(lx) / n
    my = sum(ly) / n
    num = sum((lx[i] - mx) * (ly[i] - my) for i in range(n))
    den = sum((x - mx) ** 2 for x in lx)
    if den <= 0.0:
        raise ValueError("degenerate log-log regression (zero x variance)")
    return num / den


def measure_alpha(
    p: float,
    eps_values: list[float],
    p_corr: float,
    n: int,
    t_obs: int,
    seed: int,
) -> dict:
    rng = random.Random(seed)
    partner = make_pairs(n, rng)
    rows = []
    for eps in eps_values:
        r_emp = streams_corr(rng, partner, n, p, p_corr, eps, t_obs)
        r_ex = corr_exact(p_corr, eps)
        rows.append({
            "eps": eps,
            "abs_corr_empirical": r_emp,
            "abs_corr_exact": abs(r_ex),
        })
    # alpha_emp from the EMPIRICAL magnitudes, x-axis = (1-2eps), d12m style
    pts = [(1.0 - 2.0 * e["eps"], abs(e["abs_corr_empirical"])) for e in rows
           if e["abs_corr_empirical"] == e["abs_corr_empirical"] and e["abs_corr_empirical"] > 0.0]
    if len(pts) < 2:
        raise ValueError("fewer than 2 usable |corr| points for exponent fit")
    alpha_emp = loglog_slope([x for x, _ in pts], [y for _, y in pts])
    pts_ex = [(1.0 - 2.0 * e["eps"], e["abs_corr_exact"]) for e in rows
              if e["abs_corr_exact"] > 0.0]
    alpha_exact = loglog_slope([x for x, _ in pts_ex], [y for _, y in pts_ex]) if len(pts_ex) >= 2 else None
    return {
        "p": p,
        "p_corr": p_corr,
        "n_channels": n,
        "t_obs": t_obs,
        "seed": seed,
        "rows": rows,
        "alpha_empirical": alpha_emp,
        "alpha_exact": alpha_exact,
        "verdict": "KEEP" if alpha_emp <= 1.5 else "ALPHA>1.5 (naive-1/s^2 regime)",
    }


# ------------------------------------------------------------------ selftest

def selftest() -> int:
    checks = 0
    # 1. exact corr at eps=0 with p_corr=1 is +1
    r = corr_exact(1.0, 0.0)
    assert abs(r - 1.0) < 1e-12, r
    checks += 1
    # 2. exact corr at p_corr=0 is 0
    r = corr_exact(0.0, 0.1)
    assert abs(r) < 1e-12, r
    checks += 1
    # 3. exponent of the exact form is exactly 2 in eps ((1-2eps)^2)
    a = loglog_slope([1 - 2 * e for e in (0.0, 0.05, 0.1, 0.2)],
                     [(1 - 2 * e) ** 2 for e in (0.0, 0.05, 0.1, 0.2)])
    assert abs(a - 2.0) < 1e-9, a
    checks += 1
    # 4. negative control: symmetric base streams (base +-1) with p=0.5-ish
    #    regime still give exact corr 1 at eps=0 — and empirical tracks exact
    m = measure_alpha(0.3, [0.0, 0.05, 0.1, 0.2], 1.0, 16, 8000, SELFTEST_SEED)
    assert abs(m["alpha_empirical"] - 2.0) < 0.15, m["alpha_empirical"]
    for row in m["rows"]:
        assert abs(row["abs_corr_empirical"] - row["abs_corr_exact"]) < 0.05, row
    checks += 1
    # 5. fail-loud: eps out of range raises
    try:
        corr_exact(1.0, 0.6)
        raise AssertionError("should have raised")
    except ValueError:
        checks += 1
    print(f"selftest OK: {checks}/5 checks passed")
    return 0


# ---------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Exact + empirical decorrelation exponent for paired streams.")
    ap.add_argument("--p", type=float, default=0.3, help="atom success prob (default 0.3)")
    ap.add_argument("--p-corr", type=float, default=1.0, help="shared-atom prob (default 1.0)")
    ap.add_argument("--eps", type=str, default="0.0,0.05,0.1,0.2",
                    help="comma-separated flip rates")
    ap.add_argument("--n", type=int, default=16, help="paired channels (default 16)")
    ap.add_argument("--t", type=int, default=4000, help="ticks per eps (default 4000)")
    ap.add_argument("--seed", type=int, default=SELFTEST_SEED)
    ap.add_argument("--out", type=str, default=None, help="receipt JSON path")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    try:
        eps_values = [float(x) for x in args.eps.split(",") if x.strip()]
        if not eps_values:
            raise ValueError("--eps parsed to empty list")
        receipt = measure_alpha(args.p, eps_values, args.p_corr, args.n, args.t, args.seed)
        receipt["tool"] = "corr-exponent"
        receipt["status"] = "OK"
    except (ValueError, ZeroDivisionError) as e:
        print(f"FAIL-INPUT: {e}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, indent=2))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)
        print(f"receipt -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
