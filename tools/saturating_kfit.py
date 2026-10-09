#!/usr/bin/env python3
"""saturating-kfit — fit a saturating curve k(p) = k0 + A*tanh((p-p0)/tau) to anchors.

Lifted from the proven D12ac saturating k_eff(p) fit
(experiments/d12ac_saturating_kfit_certify.py): given measured anchors
(p_i, k_i), grid-search the saturating tanh family with k0 PINNED to the
first (lowest-p) anchor, then report params, SSE, per-anchor predictions,
and optionally a comparison against the linear (chord) fit. Use when a
measured curve rises steeply then flattens and you need interpolated
k values at unmeasured p.

Stdlib-only, deterministic, fail-loud JSON receipt either way.

Usage:
  python tools/saturating_kfit.py --anchors 0.3,0.657 0.4,0.896 0.55,1.20 0.7,1.20 \
      [--eval 0.35,0.45 --out receipt.json]
  python tools/saturating_kfit.py --example

Input:
  --anchors : list of p,k pairs (comma-separated), >= 3 required, p ascending
  --eval    : optional p values to evaluate the fitted curve at
  --out     : optional JSON receipt path (always also printed to stdout)

Output receipt: {"ok", "params": {k0, A, pmid, tau, sse}, "pred": {p: k},
                 "eval": {p: k}, "chord_sse", "beats_chord"}

Exit 0 on fit success, 1 on failure (reason on stderr).

Worked example (the D12ac anchors — reproduces the booked fit):
  $ python tools/saturating_kfit.py --example
"""
import argparse
import json
import math
import sys

TAU_GRID = [0.05 * (1.0 + 29.0 * i / 59.0) for i in range(60)]  # 0.05..1.50
PMID_GRID = [0.3 + 0.5 * i / 50.0 for i in range(51)]           # 0.30..0.80


def fit_saturating(anchors):
    """Grid-search k(p)=k0+A*tanh((p-pmid)/tau), k0 pinned to first anchor."""
    p0, k0 = anchors[0]
    ks = [k for _, k in anchors]
    best = None
    for tau in TAU_GRID:
        for pmid in PMID_GRID:
            ts = [math.tanh((p - pmid) / tau) for p, _ in anchors]
            # least-squares slope A through origin of centered ts->k
            mean_t = sum(ts) / len(ts)
            mean_k = sum(ks) / len(ks)
            denom = sum((t - mean_t) ** 2 for t in ts)
            if denom <= 0:
                continue
            A = sum((t - mean_t) * (k - mean_k) for t, k in zip(ts, ks)) / denom
            if A <= 0:
                continue
            resid = [k0 + A * math.tanh((p - pmid) / tau) - k
                     for (p, _), k in zip(anchors, ks)]
            sse = sum(r * r for r in resid)
            if best is None or sse < best[0]:
                best = (sse, A, pmid, tau)
    if best is None:
        raise ValueError("no valid saturating fit found (A<=0 everywhere); "
                         "check that anchors are non-decreasing in k")
    sse, A, pmid, tau = best
    return (lambda p: k0 + A * math.tanh((p - pmid) / tau),
            {"k0": k0, "A": A, "pmid": pmid, "tau": tau, "sse": sse})


def fit_chord(anchors):
    """Linear (chord) least-squares fit for SSE comparison."""
    ps = [p for p, _ in anchors]
    ks = [k for _, k in anchors]
    n = len(ps)
    mp, mk = sum(ps) / n, sum(ks) / n
    denom = sum((p - mp) ** 2 for p in ps)
    if denom <= 0:
        raise ValueError("degenerate anchors: need >= 2 distinct p values")
    slope = sum((p - mp) * (k - mk) for p, k in zip(ps, ks)) / denom
    b = mk - slope * mp
    return (lambda p: slope * p + b,
            sum((slope * p + b - k) ** 2 for p, k in anchors))


def parse_anchors(pairs):
    anchors = []
    for raw in pairs:
        try:
            p_s, k_s = raw.split(",")
            anchors.append((float(p_s), float(k_s)))
        except ValueError:
            raise SystemExit(f"bad anchor '{raw}' — expected 'p,k' floats")
    if len(anchors) < 3:
        raise SystemExit("need >= 3 anchors to pin k0 and fit 3 params")
    ps = [p for p, _ in anchors]
    if any(b <= a for a, b in zip(ps, ps[1:])):
        raise SystemExit("anchors must be strictly ascending in p")
    return anchors


def run(anchors, eval_ps):
    f, params = fit_saturating(anchors)
    fc, chord_sse = fit_chord(anchors)
    receipt = {
        "ok": True,
        "params": params,
        "pred": {str(p): f(p) for p, _ in anchors},
        "eval": {str(p): f(p) for p in eval_ps},
        "chord_sse": chord_sse,
        "beats_chord": params["sse"] < chord_sse,
    }
    print(json.dumps(receipt, indent=2))
    return receipt


def main():
    ap = argparse.ArgumentParser(
        description="saturating-kfit — fit k0+A*tanh((p-p0)/tau) to anchors")
    ap.add_argument("--anchors", nargs="+", metavar="P,K")
    ap.add_argument("--eval", nargs="*", type=float, default=[],
                    metavar="P", help="p values to evaluate the fit at")
    ap.add_argument("--out", help="write JSON receipt here too")
    ap.add_argument("--example", action="store_true",
                    help="run the D12ac worked example")
    args = ap.parse_args()

    if args.example:
        print("== saturating-kfit example: D12ac anchors ==")
        anchors = parse_anchors(["0.3,0.657", "0.4,0.896",
                                 "0.55,1.20", "0.7,1.20"])
        receipt = run(anchors, [0.35, 0.45, 0.55])
    elif args.anchors:
        anchors = parse_anchors(args.anchors)
        receipt = run(anchors, args.eval)
    else:
        ap.error("need --anchors or --example")

    if args.out:
        with open(args.out, "w") as fh:
            json.dump(receipt, fh, indent=2)


if __name__ == "__main__":
    main()
