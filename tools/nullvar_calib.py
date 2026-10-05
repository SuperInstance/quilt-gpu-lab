#!/usr/bin/env python3
"""nullvar-calib — one-parameter null-variance calibrator for order-statistics floor models.

Pattern lifted PROVEN from D12u1 (booked KEEP 2026-10-04): the ideal-Gaussian
order-statistics model (partner ~ N(s^alpha, sigma), nulls ~ N(0, sigma),
sigma = k/sqrt(W*T)) reproduced qualitative behavior but floors sat ~400x off
the harness. ONE variance multiplier k, fit on a designated subset of cells
and validated on held-out cells, closed the gap: k=0.657, 4/4 held-out
covered within 1.5x.

Contract:
  cells = list of {name, mu (partner mean, e.g. s^alpha), scale (1/sqrt(W*T)),
                   floor (harness-measured T-floor), role: "fit"|"holdout"}
  For each cell the MODEL floor is the T where P(partner > max of n_nulls
  nulls) first reaches `threshold` (0.5), with sigma = k * scale * sqrt(T).
  Fit: minimize worst-cell |log(model_floor/harness_floor)| over a
  deterministic coarse log-grid + golden-section refine of k (no RNG needed:
  the discovery probability uses an ANALYTIC null-max via Monte-Carlo with a
  seeded, cell-independent stream — bit-identical reruns).

  Gates:
    G1 coverage: every held-out cell within --cover band (ratio in
      [1/cover, cover]); a held-out set with <1 cell books FAIL-INPUT.
    G2 spread: fitted k must serve ALL cells (fit subset worst ratio <=
      --spread band); if k needs to vary per cell by more than that, the
      one-parameter hypothesis fails and the gap is structural — honest FAIL.

Stdlib-only, seeded, deterministic, fail-loud rc=2, JSON receipt.
Exit 0=KEEP / 1=FAIL / 2=FAIL-INPUT.

Worked example (D12u1 data, s=0.3*(1-2eps), alpha=1.92, N=32 -> 31 nulls):
  python tools/nullvar_calib.py --example
  -> KEEP, k_hat ~= 0.657, 4/4 held-out covered, receipt written.

CLI:
  python tools/nullvar_calib.py --cells cells.json [--alpha 1.92 --p 0.3
        --eps 0.1 --n-nulls 31 --cover 1.5 --spread 1.3 --out r.json]
        | --example | --selftest

cells.json format:
  [{"name": "W4_eps0.0", "mu": 0.129, "scale": 0.5, "floor": 40,
    "role": "fit"},
   {"name": "W16_eps0.0", "mu": 0.129, "scale": 0.25, "floor": 15,
    "role": "holdout"}]
(mu = s**alpha for the cell; scale = 1/sqrt(W); floor = harness T-floor.)
"""
import argparse
import json
import math
import os
import random
import sys
import time

PHI = (math.sqrt(5.0) - 1.0) / 2.0  # 0.618...; golden-section


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# ---------------------------------------------------------------- MC engine
_MC_CACHE = {}


def _null_max_quantiles(n_mc, n_nulls, seed):
    """Cached sorted draws of max-of-nulls in standard units; cell-independent."""
    key = (n_mc, n_nulls, seed)
    if key not in _MC_CACHE:
        rng = random.Random(seed)
        draws = []
        for _ in range(n_mc):
            draws.append(max(rng.gauss(0.0, 1.0) for _ in range(n_nulls)))
        draws.sort()
        _MC_CACHE[key] = draws
    return _MC_CACHE[key]


def disc_prob(mu, sigma, null_q, threshold=0.5):
    """P(partner > null_max) via MC quantile walk, analytic partner CDF."""
    if sigma <= 0.0:
        return 1.0 if mu > 0 else 0.0
    n = len(null_q)
    # null_q are standard-unit draws of max-of-nulls; partner ~ N(mu, sigma)
    # P(partner > q) = 1 - Phi((q*sigma - mu)/sigma) = 1 - Phi(q - mu/sigma)
    z = mu / sigma
    total = 0.0
    for q in null_q:
        total += 1.0 - norm_cdf(q - z)
    return total / n


def model_floor(mu, scale, k, n_nulls, n_mc=4000, threshold=0.5, seed=2718):
    """Smallest T with discovery prob >= threshold, coarse grid + bisection."""
    if mu <= 0.0:
        return float("inf")
    null_q = _null_max_quantiles(n_mc, n_nulls, seed)

    def p_at(t):
        return disc_prob(mu, k * scale / math.sqrt(t), null_q, threshold)

    lo, hi = 1.0, 1.0e6
    if p_at(hi) < threshold:
        return float("inf")
    if p_at(lo) >= threshold:
        return lo
    # coarse geometric grid
    prev = lo
    for _ in range(60):
        cur = prev * 1.5
        if p_at(cur) >= threshold:
            hi, lo = cur, prev
            break
        prev = cur
    else:
        hi, lo = prev, prev / 1.5
    for _ in range(40):
        mid = math.sqrt(lo * hi)
        if p_at(mid) >= threshold:
            hi = mid
        else:
            lo = mid
    return hi


# ------------------------------------------------------------------- fitting
def worst_ratio(k, cells, n_nulls):
    worst = 0.0
    for c in cells:
        m = model_floor(c["mu"], c["scale"], k, n_nulls)
        if not math.isfinite(m):
            return float("inf")
        r = abs(math.log(m / c["floor"]))
        if r > worst:
            worst = r
    return worst


def fit_k(fit_cells, n_nulls):
    """Deterministic coarse log-grid + golden-section refine of log(k)."""
    best_k, best_r = None, float("inf")
    k = 0.05
    while k <= 20.0:
        r = worst_ratio(k, fit_cells, n_nulls)
        if r < best_r:
            best_k, best_r = k, r
        k *= 1.15
    lo, hi = best_k / 1.15, best_k * 1.15
    # golden-section on log(k)
    a, b = math.log(lo), math.log(hi)
    c = b - PHI * (b - a)
    d = a + PHI * (b - a)
    fc = worst_ratio(math.exp(c), fit_cells, n_nulls)
    fd = worst_ratio(math.exp(d), fit_cells, n_nulls)
    for _ in range(40):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - PHI * (b - a)
            fc = worst_ratio(math.exp(c), fit_cells, n_nulls)
        else:
            a, c, fc = c, d, fd
            d = a + PHI * (b - a)
            fd = worst_ratio(math.exp(d), fit_cells, n_nulls)
    k_hat = math.exp((a + b) / 2.0)
    return k_hat, math.exp(best_r) if False else math.exp(-worst_ratio(k_hat, fit_cells, n_nulls))


# -------------------------------------------------------------------- runner
def run(cells, alpha=None, p=None, eps=None, n_nulls=31, cover=1.5, spread=1.3,
        n_mc=4000, seed=2718):
    rc = 0
    if not isinstance(cells, list) or not cells:
        return {"verdict": "FAIL-INPUT", "rc": 2, "why": "cells must be a non-empty list"}
    if (alpha is None) != (p is None) or (p is None) != (eps is None):
        return {"verdict": "FAIL-INPUT", "rc": 2,
                "why": "--alpha/--p/--eps must be given together (or not at all)"}
    norm = []
    for c in cells:
        try:
            name = str(c["name"])
            floor = float(c["floor"])
            role = str(c["role"])
        except Exception:
            return {"verdict": "FAIL-INPUT", "rc": 2, "why": f"bad cell: {c!r}"}
        if floor <= 0 or not math.isfinite(floor):
            return {"verdict": "FAIL-INPUT", "rc": 2, "why": f"{name}: floor must be positive finite"}
        if role not in ("fit", "holdout"):
            return {"verdict": "FAIL-INPUT", "rc": 2, "why": f"{name}: role must be fit|holdout"}
        if "mu" in c and c["mu"] is not None:
            mu = float(c["mu"])
            scale = float(c["scale"])
        else:
            if alpha is None:
                return {"verdict": "FAIL-INPUT", "rc": 2,
                        "why": f"{name}: no mu and no --alpha/--p/--eps to derive it"}
            s = p * (1.0 - 2.0 * eps)
            if s <= 0:
                return {"verdict": "FAIL-INPUT", "rc": 2,
                        "why": f"{name}: degenerate signal p*(1-2eps) <= 0"}
            if "w" not in c:
                return {"verdict": "FAIL-INPUT", "rc": 2,
                        "why": f"{name}: derived mu needs 'w' (streams) in the cell"}
            mu = s ** alpha
            scale = 1.0 / math.sqrt(float(c["w"]))
        if mu <= 0 or not math.isfinite(mu) or scale <= 0:
            return {"verdict": "FAIL-INPUT", "rc": 2, "why": f"{name}: mu/scale must be positive finite"}
        norm.append({"name": name, "mu": mu, "scale": scale, "floor": floor, "role": role})

    fit_cells = [c for c in norm if c["role"] == "fit"]
    hold = [c for c in norm if c["role"] == "holdout"]
    if not fit_cells or not hold:
        return {"verdict": "FAIL-INPUT", "rc": 2,
                "why": "need >=1 fit cell AND >=1 holdout cell"}

    k_hat, fit_qual = fit_k(fit_cells, n_nulls)

    fit_detail, hold_detail = {}, {}
    n_covered = 0
    worst_any = 0.0
    for c in fit_cells:
        m = model_floor(c["mu"], c["scale"], k_hat, n_nulls, n_mc=n_mc, seed=seed)
        ratio = m / c["floor"] if math.isfinite(m) else float("inf")
        worst_any = max(worst_any, max(ratio, 1.0 / ratio))
        fit_detail[c["name"]] = {"model": m, "harness": c["floor"], "ratio": ratio}
    for c in hold:
        m = model_floor(c["mu"], c["scale"], k_hat, n_nulls, n_mc=n_mc, seed=seed)
        ratio = m / c["floor"] if math.isfinite(m) else float("inf")
        ok = math.isfinite(ratio) and (1.0 / cover) <= ratio <= cover
        n_covered += ok
        hold_detail[c["name"]] = {"model": m, "harness": c["floor"],
                                  "ratio": ratio, "covered": ok}

    g1 = n_covered == len(hold)
    g2 = worst_any <= spread
    verdict = "KEEP" if (g1 and g2) else "FAIL"
    rc = 0 if verdict == "KEEP" else 1
    return {
        "verdict": verdict, "rc": rc,
        "k_hat": k_hat, "n_nulls": n_nulls,
        "g1_holdout": f"{n_covered}/{len(hold)}", "g1_pass": g1,
        "g2_worst_fit_ratio": worst_any, "g2_band": spread, "g2_pass": g2,
        "fit_cells": fit_detail, "holdout": hold_detail,
        "why": None if (g1 and g2) else
               (("held-out coverage missed" if not g1 else "") +
                ("; fit-subset spread over band" if not g2 else "")).strip("; "),
    }


# ------------------------------------------------------------------- extras
def _example_cells():
    """D12u1: s = 0.3*(1-2eps), alpha=1.92, N=32 (31 nulls)."""
    alpha, p, n = 1.92, 0.3, 32
    eps_list = [0.0, 0.05, 0.1, 0.2]
    floors = {4: [40, 60, 120, 320], 8: [20, 30, 60, 160], 16: [15, 15, 30, 80]}
    cells = []
    for w, fl in floors.items():
        for i, eps in enumerate(eps_list):
            role = "holdout" if w == 16 else "fit"
            cells.append({"name": f"W{w}_eps{eps}", "mu": (p * (1 - 2 * eps)) ** alpha,
                          "scale": 1.0 / math.sqrt(w), "floor": fl[i], "role": role})
    return cells


def selftest():
    checks = []
    # 1. D12u1 data reproduces a KEEP with k near 0.657
    r = run(_example_cells(), n_nulls=31)
    checks.append(("example-KEEP", r["verdict"] == "KEEP" and r["g1_pass"],
                   f"k={r['k_hat']:.4f} g1={r['g1_holdout']}"))
    checks.append(("k-sane", 0.4 < r["k_hat"] < 1.0, f"k_hat={r['k_hat']:.4f} (D12u1 booked 0.657)"))
    # 2. law-break: holdout floors 10x off -> FAIL on coverage
    bad = _example_cells()
    for c in bad:
        if c["role"] == "holdout":
            c["floor"] *= 10
    r2 = run(bad, n_nulls=31)
    checks.append(("holdout-break-FAIL", r2["verdict"] == "FAIL" and not r2["g1_pass"],
                   f"g1={r2['g1_holdout']}"))
    # 3. structural: fit cells mutually 10x-inconsistent -> FAIL on spread (G2)
    structural = _example_cells()
    for i, c in enumerate(structural):
        if c["role"] == "fit" and i % 2 == 0:
            c["floor"] *= 6.0
    r3 = run(structural, n_nulls=31, spread=1.3)
    checks.append(("structural-FAIL-G2", r3["verdict"] == "FAIL" and not r3["g2_pass"],
                   f"g2_worst={r3['g2_worst_fit_ratio']:.2f}"))
    # 4. determinism: same run twice, bit-identical
    ra = run(_example_cells(), n_nulls=31)
    checks.append(("determinism", ra == r, "bit-identical rerun"))
    # 5. fail-loud inputs
    for label, payload in [
        ("empty", []), ("bad-role", [{"name": "x", "mu": 1, "scale": 1, "floor": 1, "role": "nope"}]),
        ("neg-floor", [{"name": "x", "mu": 1, "scale": 1, "floor": -1, "role": "fit"}]),
        ("no-holdout", [{"name": "x", "mu": 1, "scale": 1, "floor": 1, "role": "fit"}]),
    ]:
        rx = run(payload, n_nulls=31)
        checks.append((f"rc2:{label}", rx["rc"] == 2, str(rx.get("why", ""))[:50]))

    ok = 0
    for name, passed, note in checks:
        print(f"  [{'OK' if passed else 'PIN-FAIL'}] {name}: {note}")
        ok += passed
    print(f"selftest: {ok}/{len(checks)}")
    return 0 if ok == len(checks) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="one-parameter null-variance floor calibrator (D12u1 pattern)")
    ap.add_argument("--cells", help="cells JSON file")
    ap.add_argument("--alpha", type=float, help="correlation exponent (with --p/--eps)")
    ap.add_argument("--p", type=float)
    ap.add_argument("--eps", type=float)
    ap.add_argument("--n-nulls", type=int, default=31)
    ap.add_argument("--cover", type=float, default=1.5, help="held-out coverage band")
    ap.add_argument("--spread", type=float, default=1.3, help="G2 fit-spread band")
    ap.add_argument("--out", help="receipt path")
    ap.add_argument("--example", action="store_true", help="run the D12u1 worked example")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        sys.exit(selftest())
    if args.example:
        result = run(_example_cells(), n_nulls=args.n_nulls)
        result["example"] = "D12u1 floors (s=0.3*(1-2eps), alpha=1.92, N=32)"
    elif args.cells:
        try:
            with open(args.cells) as f:
                cells = json.load(f)
        except Exception as e:
            print(f"FAIL-INPUT: cannot read cells: {e}", file=sys.stderr)
            sys.exit(2)
        result = run(cells, alpha=args.alpha, p=args.p, eps=args.eps,
                     n_nulls=args.n_nulls, cover=args.cover, spread=args.spread)
    else:
        ap.print_help()
        sys.exit(2)

    result.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    print(json.dumps(result, indent=1))
    if args.out:
        tmp = args.out + ".tmp"
        with open(tmp, "w") as f:
            json.dump(result, f, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, args.out)
        print(f"receipt: {args.out}", file=sys.stderr)
    sys.exit(result["rc"])


if __name__ == "__main__":
    main()
