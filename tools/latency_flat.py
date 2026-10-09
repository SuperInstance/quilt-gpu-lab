#!/usr/bin/env python3
"""latency-flat — batched-call flat-latency gate.

Pattern lifted PROVEN from cm1_relay_r4/r5 (booked 2026-10-01: 80-question
batches came back at ~flat wall time vs 12q — batching beats the per-call
latency wall only if wall does NOT scale with item count; "80q ~= flat
latency" was observed, not gated — this mechanizes the gate).

Given per-batch {n: item count, wall_s: wall-clock seconds}, fit wall vs n
by least squares. The slope s (seconds per additional item) is compared to
the mean per-item time m: the FLATNESS RATIO s/m must be <= bar (default
0.10) — i.e. each extra item costs <=10% of what a per-item-time world
would predict. A ratio near 1.0 means wall is linear in n: no batching win.
Requires >= 2 distinct batch sizes with span ratio >= 2 (a gate on one
point is a tautology, booked FAIL-INPUT, never PASS).

Stdlib-only, deterministic, fail-loud rc=2, one JSON receipt.
Exit 0=FLAT / 1=SCALING / 2=FAIL-INPUT.

Usage:
  python tools/latency_flat.py \
      --batches '[{"n":12,"wall_s":0.45},{"n":36,"wall_s":0.52},{"n":80,"wall_s":0.61}]' \
      [--bar 0.10 --out r.json]
  python tools/latency_flat.py --batches-file b.json | --selftest

Worked example: 12/36/80q batches at 0.45/0.52/0.61s -> slope ~0.0022 s/item,
per-item mean ~0.0093, ratio ~0.24 at bar 0.10 -> honest SCALING (these are
illustrative walls, not booked data); run --selftest for the proven pins.
"""

import argparse
import json
import math
import sys
import time


def fit(batches, bar):
    """Gate flatness of wall vs n. Returns (rc, receipt_dict)."""
    if not isinstance(batches, list) or len(batches) < 2:
        raise ValueError("need a list of >=2 batch records {n, wall_s}")
    pts = []
    for b in batches:
        if not isinstance(b, dict) or "n" not in b or "wall_s" not in b:
            raise ValueError("each batch needs keys n and wall_s: %r" % (b,))
        n, w = b["n"], b["wall_s"]
        if not isinstance(n, (int, float)) or isinstance(n, bool) or n <= 0:
            raise ValueError("bad n: %r" % (n,))
        if not isinstance(w, (int, float)) or isinstance(w, bool):
            raise ValueError("bad wall_s: %r" % (w,))
        if not math.isfinite(n) or not math.isfinite(w) or w < 0:
            raise ValueError("non-finite or negative input: n=%r wall_s=%r" % (n, w))
        pts.append((float(n), float(w)))

    ns = sorted(set(p[0] for p in pts))
    if len(ns) < 2:
        raise ValueError("need >=2 DISTINCT batch sizes; one point gates nothing")
    if ns[-1] / ns[0] < 2.0:
        raise ValueError(
            "batch-size span ratio %.2f < 2 — too narrow to distinguish "
            "flat from linear" % (ns[-1] / ns[0]))

    # least squares slope/intercept over all points
    m = len(pts)
    mx = sum(p[0] for p in pts) / m
    my = sum(p[1] for p in pts) / m
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    if sxx == 0:
        raise ValueError("degenerate x spread")
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    slope = sxy / sxx
    intercept = my - slope * mx

    per_item = [w / n for n, w in pts]
    m_pi = sum(per_item) / len(per_item)
    if m_pi <= 0:
        raise ValueError("zero mean per-item time — walls are all 0, nothing to gate")
    ratio = slope / m_pi
    flat = ratio <= bar

    return 0 if flat else 1, {
        "tool": "latency-flat",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": "FLAT" if flat else "SCALING",
        "slope_s_per_item": round(slope, 6),
        "intercept_s": round(intercept, 4),
        "mean_per_item_s": round(m_pi, 6),
        "flatness_ratio": round(ratio, 4),
        "bar": bar,
        "n_batches": m,
        "distinct_n": ns,
        "batches": [{"n": n, "wall_s": w} for n, w in pts],
    }


def _selftest():
    checks = []
    # 1. flat control: wall ~ constant regardless of n -> FLAT
    flat = [{"n": 12, "wall_s": 0.50}, {"n": 36, "wall_s": 0.52}, {"n": 80, "wall_s": 0.53}]
    rc, rec = fit(flat, 0.10)
    checks.append(("flat-control", rc == 0 and rec["verdict"] == "FLAT", rec))
    # 2. linear control: wall proportional to n -> SCALING
    lin = [{"n": 10, "wall_s": 0.5}, {"n": 40, "wall_s": 2.0}, {"n": 80, "wall_s": 4.0}]
    rc, rec = fit(lin, 0.10)
    checks.append(("linear-control", rc == 1 and rec["verdict"] == "SCALING", rec))
    # 3. single point -> fail-loud (one-point gate is a tautology)
    try:
        fit([{"n": 10, "wall_s": 0.5}], 0.10)
        checks.append(("one-point", False, None))
    except ValueError:
        checks.append(("one-point", True, None))
    # 4. narrow span -> fail-loud
    try:
        fit([{"n": 10, "wall_s": 0.5}, {"n": 11, "wall_s": 0.5}], 0.10)
        checks.append(("narrow-span", False, None))
    except ValueError:
        checks.append(("narrow-span", True, None))
    # 5. negative wall -> fail-loud
    try:
        fit([{"n": 10, "wall_s": -1}, {"n": 40, "wall_s": 2.0}], 0.10)
        checks.append(("negative-wall", False, None))
    except ValueError:
        checks.append(("negative-wall", True, None))

    ok = all(c[1] for c in checks)
    out = {"tool": "latency-flat", "selftest": "PASS" if ok else "FAIL",
           "checks": [{"name": c[0], "ok": c[1]} for c in checks]}
    print(json.dumps(out, indent=2))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="flat-latency gate for batched calls")
    ap.add_argument("--batches", help='JSON list of {"n": int, "wall_s": float}')
    ap.add_argument("--batches-file", help="read --batches JSON from a file")
    ap.add_argument("--bar", type=float, default=0.10,
                    help="max slope/mean-per-item ratio (default 0.10)")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(_selftest())
    try:
        if a.batches_file:
            with open(a.batches_file) as f:
                raw = f.read()
        elif a.batches:
            raw = a.batches
        else:
            ap.error("one of --batches / --batches-file / --selftest is required")
        rc, rec = fit(json.loads(raw), a.bar)
    except (ValueError, json.JSONDecodeError, OSError) as e:
        print(json.dumps({"tool": "latency-flat", "verdict": "FAIL-INPUT",
                          "why": str(e)}))
        sys.exit(2)
    print(json.dumps(rec, indent=2))
    if a.out:
        with open(a.out, "w") as f:
            f.write(json.dumps(rec, indent=2) + "\n")
    sys.exit(rc)


if __name__ == "__main__":
    main()
