#!/usr/bin/env python3
"""k-curve-gate — interpolated one-parameter calibration coverage gate.

Pattern lifted PROVEN from D12v (experiments/d12v_keff_p045.py, booked 2026-10-06):
the calibrated lumped parameter k was fit from exactly TWO p-points (0.3, 0.4),
and the midpoint claim was "a LINEARLY INTERPOLATED k covers the harness floors
within band". This mechanizes that claim: given calibration anchors (x -> k)
and probe cells (name, x, base, measured), compute model = base * k_interp(x),
ratio = model/measured, and KEEP iff every ratio lands inside the band
(default [0.5, 2.0]). x outside the anchor range uses the edge anchor and is
flagged EXTRAPOLATED (never silently). Optional per-cell monotone check on an
implied field (e.g. implied k_eff must be monotone in eps — structural drift,
not per-cell noise).

Stdlib-only, deterministic, fail-loud rc=2, one JSON receipt either verdict.
Exit codes: 0=KEEP, 1=FAIL, 2=FAIL-INPUT.

Usage:
  python tools/k_curve_gate.py --anchors '[{"x":0.3,"k":0.657},{"x":0.4,"k":0.8963}]' \
      --cells cells.json [--lo 0.5 --hi 2.0] [--mono-field implied_k --mono-var eps] \
      [--out r.json] | --example | --selftest

Worked example (docstring-embedded, mirrors D12v):
  python tools/k_curve_gate.py --example
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone


def fail_input(msg, out=None):
    if out:
        write_receipt(out, "FAIL-INPUT", {}, {"error": msg})
    print(f"FAIL-INPUT: {msg}", file=sys.stderr)
    sys.exit(2)


def write_receipt(path, verdict, result, extras):
    rec = {
        "tool": "k-curve-gate",
        "verdict": verdict,
        "utc": datetime.now(timezone.utc).isoformat(),
        **result,
        **extras,
    }
    with open(path, "w") as f:
        json.dump(rec, f, indent=2, sort_keys=True)
        f.write("\n")
    return rec


def interp_k(anchors, x):
    """Linear interpolation between the two nearest anchors; edge-anchored
    (flagged) outside the range. Anchors: [{x, k}]. Returns (k, extrapolated)."""
    pts = sorted((a["x"], a["k"]) for a in anchors)
    if not pts:
        raise ValueError("no anchors")
    xs = [p[0] for p in pts]
    if x <= xs[0]:
        return pts[0][1], x < xs[0]
    if x >= xs[-1]:
        return pts[-1][1], x > xs[-1]
    for (x0, k0), (x1, k1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return k0, False
            t = (x - x0) / (x1 - x0)
            return k0 + t * (k1 - k0), False


def run_gate(anchors, cells, lo, hi, mono_field=None, mono_var=None):
    """anchors: [{x,k}]; cells: [{name, x, base, measured, ...}].
    Returns (verdict, result)."""
    if len(anchors) < 2:
        fail_input("need >=2 anchors to interpolate")
    if not cells:
        fail_input("empty cells list")
    xs = [a["x"] for a in anchors]
    if len(set(xs)) != len(xs):
        fail_input("duplicate anchor x values")
    ks = [a["k"] for a in anchors]
    if not all(isinstance(v, (int, float)) and v > 0 for v in ks + xs):
        fail_input("anchor x/k must be positive numbers")
    if not (0 < lo < hi):
        fail_input("band must satisfy 0 < lo < hi")

    results, ratios = [], []
    for c in cells:
        for f in ("name", "x", "base", "measured"):
            if f not in c:
                fail_input(f"cell missing field '{f}': {c.get('name', '?')}")
        if not (c["measured"] > 0 and c["base"] > 0):
            fail_input(f"cell '{c['name']}' base/measured must be positive")
        k, extrap = interp_k(anchors, c["x"])
        model = c["base"] * k
        ratio = model / c["measured"]
        implied_k = c["measured"] / c["base"] if c["base"] else None
        in_band = lo <= ratio <= hi
        results.append({
            "name": c["name"], "x": c["x"], "k": round(k, 6),
            "extrapolated": extrap,
            "model": round(model, 6), "measured": c["measured"],
            "ratio": round(ratio, 6), "in_band": in_band,
            "implied_k": round(implied_k, 6) if implied_k else None,
        })
        ratios.append(ratio)

    worst = max(abs(round(r, 10) - 1.0) for r in ratios)
    band_ok = all(r["in_band"] for r in results)
    mono = None
    if mono_field:
        if not mono_var:
            fail_input("--mono-field requires --mono-var")
        keyed = {}
        for c, r in zip(cells, results):
            if mono_var not in c or r.get(mono_field) is None:
                fail_input(f"cell '{c['name']}' missing {mono_var}/{mono_field} for mono check")
            keyed[c[mono_var]] = r[mono_field]
        pairs = sorted(keyed.items())
        vals = [v for _, v in pairs]
        diffs = {round(b - a, 12) for a, b in zip(vals, vals[1:])}
        if len(diffs) == 1 and 0.0 in diffs:
            mono = {"ok": True, "why": "constant (degenerate but not anti-monotone)"}
        else:
            direction = diffs.pop() if len(diffs) == 1 else None
            if direction is None:
                ok = all(b >= a for a, b in zip(vals, vals[1:])) or \
                     all(b <= a for a, b in zip(vals, vals[1:]))
                mono = {"ok": ok, "why": "monotone" if ok else "non-monotone sequence"}
            else:
                mono = {"ok": True, "why": f"constant slope {direction}"}

    verdict = "KEEP" if band_ok and (mono is None or mono["ok"]) else "FAIL"
    result = {
        "anchors": sorted(anchors, key=lambda a: a["x"]),
        "band": [lo, hi],
        "cells": results,
        "worst_dev_from_1": round(worst, 6),
        "band_ok": band_ok,
        "mono_check": mono,
        "n_extrapolated": sum(1 for r in results if r["extrapolated"]),
    }
    return verdict, result


def example(out=None):
    # D12v-shaped: anchors at p=0.3 (k=0.657) and p=0.4 (k=0.8963);
    # probe at midpoint x=0.35 -> interpolated k = 0.77665.
    anchors = [{"x": 0.3, "k": 0.657}, {"x": 0.4, "k": 0.8963}]
    cells = [
        {"name": "w4-e0.0", "x": 0.35, "eps": 0.0, "base": 100.0, "measured": 100.0},
        {"name": "w4-e0.1", "x": 0.35, "eps": 0.1, "base": 100.0, "measured": 110.0},
        {"name": "w8-e0.2", "x": 0.35, "eps": 0.2, "base": 200.0, "measured": 240.0},
    ]
    v, r = run_gate(anchors, cells, 0.5, 2.0, mono_field="implied_k", mono_var="eps")
    if out:
        write_receipt(out, v, r, {})
    print(json.dumps({"verdict": v, **r}, indent=2))
    return 0 if v == "KEEP" else 1


def selftest():
    checks = []
    def ck(name, cond):
        checks.append((name, bool(cond)))

    A = [{"x": 0.3, "k": 0.657}, {"x": 0.4, "k": 0.8963}]
    # 1. interpolation pin: midpoint x=0.35 -> k=(0.657+0.8963)/2=0.77665;
    #    x=0.45 is OUTSIDE the range -> edge-anchored + flagged EXTRAPOLATED
    k, ex = interp_k(A, 0.35)
    ck("midpoint-k-interp", abs(k - 0.77665) < 1e-9 and not ex)
    k2, ex2 = interp_k(A, 0.45)
    ck("outside-edge-flagged", abs(k2 - 0.8963) < 1e-9 and ex2)
    # 2. clean cells PASS
    cells = [{"name": "c1", "x": 0.35, "base": 10.0, "measured": 10.0},
             {"name": "c2", "x": 0.4, "base": 10.0, "measured": 11.0}]
    v, r = run_gate(A, cells, 0.5, 2.0)
    ck("clean-keep", v == "KEEP" and r["band_ok"])
    # 3. off-band cell FAIL (ratio 5x)
    v, r = run_gate(A, [{"name": "bad", "x": 0.35, "base": 10.0, "measured": 1.5}], 0.5, 2.0)
    ck("offband-fail", v == "FAIL" and not r["cells"][0]["in_band"])
    # 4. extrapolation is flagged, not silent
    v, r = run_gate(A, [{"name": "ex", "x": 0.9, "base": 10.0, "measured": 10.0}], 0.5, 2.0)
    ck("extrap-flagged", r["n_extrapolated"] == 1 and r["cells"][0]["extrapolated"])
    # 5. monotone check catches anti-monotone implied_k
    cells = [{"name": "a", "x": 0.35, "eps": 0.0, "base": 10.0, "measured": 10.0},
             {"name": "b", "x": 0.35, "eps": 0.1, "base": 10.0, "measured": 12.0},
             {"name": "c", "x": 0.35, "eps": 0.2, "base": 10.0, "measured": 11.0}]
    v, r = run_gate(A, cells, 0.5, 2.0, mono_field="implied_k", mono_var="eps")
    ck("anti-mono-fail", v == "FAIL" and r["mono_check"] and not r["mono_check"]["ok"])
    # 6. fail-loud inputs
    for bad in ([{"x": 0.3, "k": 1.0}], []):
        try:
            run_gate(bad, [{"name": "c", "x": 0.3, "base": 1.0, "measured": 1.0}], 0.5, 2.0)
            ck("fail-input", False)
        except SystemExit as e:
            ck("fail-input", e.code == 2)

    ok = all(c for _, c in checks)
    for name, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {name}")
    print(f"selftest {'OK' if ok else 'FAILED'} ({sum(c for _, c in checks)}/{len(checks)})")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="k-curve-gate: interpolated-k coverage gate")
    ap.add_argument("--anchors", help='JSON [{"x":..,"k":..},...] (2+ points)')
    ap.add_argument("--anchors-file")
    ap.add_argument("--cells", help="JSON [{name,x,base,measured,...}] or path to JSON file")
    ap.add_argument("--lo", type=float, default=0.5)
    ap.add_argument("--hi", type=float, default=2.0)
    ap.add_argument("--mono-field", help="optional monotone check field (e.g. implied_k)")
    ap.add_argument("--mono-var", help="variable to sort by for mono check (e.g. eps)")
    ap.add_argument("--out", help="receipt path")
    ap.add_argument("--example", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(selftest())
    if a.example:
        sys.exit(example(a.out))

    try:
        anchors = json.loads(a.anchors) if a.anchors else json.load(open(a.anchors_file))
    except Exception as e:
        fail_input(f"bad anchors: {e}")
    if a.cells and os.path.exists(a.cells) and a.cells.endswith(".json"):
        try:
            cells = json.load(open(a.cells))
        except Exception as e:
            fail_input(f"bad cells file: {e}")
    else:
        try:
            cells = json.loads(a.cells) if a.cells else None
        except Exception as e:
            fail_input(f"bad cells JSON: {e}")
    if not isinstance(anchors, list) or not isinstance(cells, list):
        fail_input("anchors and cells must be JSON arrays")

    extras = {}
    if a.out:
        def _gated_write(verdict, result, ex):
            write_receipt(a.out, verdict, result, ex)
    else:
        _gated_write = None

    try:
        verdict, result = run_gate(anchors, cells, a.lo, a.hi, a.mono_field, a.mono_var)
    except SystemExit:
        raise
    except Exception as e:
        fail_input(str(e), a.out)

    if a.out:
        write_receipt(a.out, verdict, result, extras)
    print(json.dumps({"verdict": verdict, **result}, indent=2))
    sys.exit(0 if verdict == "KEEP" else 1)


if __name__ == "__main__":
    main()
