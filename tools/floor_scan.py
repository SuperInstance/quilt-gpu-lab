#!/usr/bin/env python3
"""floor-scan — extract T_floors from accuracy-vs-T curves, flag grid-pinned floors.

Pattern lifted from tonight's D12q/D12r lanes: a floor that sits AT the edge of
the scanned T grid is not a measurement, it's a quantized bound (D12p's weak
KEEP had 0 degrees of freedom because floors pinned at the grid bottom). This
tool makes that failure class loud instead of silent.

Input: JSON curves file, either
  {"name": [[t, acc], ...], ...}
or
  {"name": {"t": [...], "acc": [...]}, ...}

For each curve it reports:
  - T_floor: smallest T with acc >= bar (first crossing), or null if none
  - status: RESOLVED | PINNED_LOW (floor == smallest scanned T — unresolved,
    true floor may be far below) | NEVER (acc never reaches bar)
  - C_emp = W * T_floor * s^alpha when --w and signal s are given
    (s from --p/--eps as s = p*(1-2eps), the D12q-corrected form, or --seff)
  - optional law check vs --c-bound: C_emp <= C_bound at every resolvable floor

Exit codes: 0 = all floors resolved (or no law gate), 1 = law gate FAIL or any
PINNED_LOW/NEVER curve when --strict, 2 = fail-loud input error.
Stdlib-only. Keys never echoed; nothing deleted.

Worked example:
  echo '{"demo": [[10,0.5],[20,0.7],[40,0.93],[80,0.96]]}' > c.json
  python tools/floor_scan.py --curves c.json --bar 0.9 --w 8 --p 0.3 --eps 0.1 --alpha 1.92 --out r.json
  -> demo: T_floor=40, C_emp = 8*40*(0.3*0.8)^1.92, RESOLVED, rc=0

Self-test:  python tools/floor_scan.py --selftest
"""
from __future__ import annotations

import argparse
import json
import math
import sys

RC_INPUT = 2


def _fail(msg: str) -> "None":
    print(f"FAIL-INPUT: {msg}", file=sys.stderr)
    sys.exit(RC_INPUT)


def load_curves(path: str) -> dict:
    try:
        with open(path) as f:
            raw = json.load(f)
    except OSError as e:
        _fail(f"cannot read {path}: {e}")
    except json.JSONDecodeError as e:
        _fail(f"bad JSON in {path}: {e}")
    if not isinstance(raw, dict) or not raw:
        _fail("curves file must be a non-empty JSON object of {name: curve}")
    return raw


def normalize(name: str, curve) -> list:
    """-> sorted list of (t, acc) tuples, validated finite."""
    if isinstance(curve, dict):
        t, a = curve.get("t"), curve.get("acc")
        if not isinstance(t, list) or not isinstance(a, list) or len(t) != len(a):
            _fail(f"curve '{name}': need parallel t[]/acc[] of equal length")
        pts = list(zip(t, a))
    elif isinstance(curve, list):
        pts = []
        for p in curve:
            if not (isinstance(p, (list, tuple)) and len(p) == 2):
                _fail(f"curve '{name}': points must be [t, acc] pairs")
            pts.append((p[0], p[1]))
    else:
        _fail(f"curve '{name}': must be a list of [t,acc] or an object with t[]/acc[]")
    out = []
    for t, acc in pts:
        if not (isinstance(t, (int, float)) and isinstance(acc, (int, float))):
            _fail(f"curve '{name}': non-numeric point ({t!r}, {acc!r})")
        if not (math.isfinite(t) and math.isfinite(acc)):
            _fail(f"curve '{name}': non-finite point ({t}, {acc})")
        out.append((float(t), float(acc)))
    if not out:
        _fail(f"curve '{name}': empty")
    out.sort()
    return out


def floor_of(pts, bar: float):
    """First-crossing floor. Returns (t_floor|None, status)."""
    tmin = pts[0][0]
    for t, acc in pts:
        if acc >= bar:
            status = "PINNED_LOW" if t == tmin else "RESOLVED"
            return t, status
    return None, "NEVER"


def seff_from(p: float, eps: float) -> float:
    if not (0.0 <= p <= 1.0) or not (0.0 <= eps <= 0.5):
        _fail(f"invalid p={p} eps={eps}")
    return p * (1.0 - 2.0 * eps)


def run_scan(args) -> dict:
    curves = load_curves(args.curves)
    if args.seff is not None:
        s = args.seff
    elif args.p is not None:
        if args.eps is None:
            _fail("--p requires --eps (or use --seff directly)")
        s = seff_from(args.p, args.eps)
    else:
        s = None
    if s is not None and s <= 0:
        _fail(f"signal strength s must be > 0 (got {s}); degenerate s makes C_emp infinite")

    receipt = {
        "tool": "floor-scan",
        "bar": args.bar,
        "s": s,
        "alpha": args.alpha,
        "c_bound": args.c_bound,
        "strict": args.strict,
        "curves": {},
    }
    any_pinned = False
    law_fail = False
    for name, curve in sorted(curves.items()):
        pts = normalize(name, curve)
        tf, status = floor_of(pts, args.bar)
        entry = {"t_floor": tf, "status": status, "n_points": len(pts)}
        if tf is not None and s is not None:
            w = args.w
            if w is None:
                _fail("--w is required when a signal strength is given (C_emp = W*T*s^alpha)")
            entry["c_emp"] = w * tf * (s ** args.alpha)
            if args.c_bound is not None and status == "RESOLVED":
                entry["within_bound"] = entry["c_emp"] <= args.c_bound
                if not entry["within_bound"]:
                    law_fail = True
        if status in ("PINNED_LOW", "NEVER"):
            any_pinned = True
        receipt["curves"][name] = entry

    receipt["verdict"] = "FAIL" if (law_fail or (args.strict and any_pinned)) else "KEEP"
    if args.out:
        with open(args.out, "w") as f:
            json.dump(receipt, f, indent=2)
            f.write("\n")
    return receipt


def print_receipt(r: dict) -> None:
    print(f"floor-scan — bar={r['bar']} s={r['s']} alpha={r['alpha']} c_bound={r['c_bound']}")
    for name, e in r["curves"].items():
        line = f"  {name}: T_floor={e['t_floor']} [{e['status']}]"
        if "c_emp" in e:
            line += f" C_emp={e['c_emp']:.3f}"
            if "within_bound" in e:
                line += f" bound={'OK' if e['within_bound'] else 'VIOLATED'}"
        print(line)
    print(f"verdict: {r['verdict']}")


def selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'} {name}")
        ok = ok and cond

    # 1: monotone crossing -> RESOLVED at 40
    pts = normalize("x", [[10, 0.5], [20, 0.7], [40, 0.93], [80, 0.96]])
    tf, st = floor_of(pts, 0.9)
    check("monotone RESOLVED t=40", tf == 40.0 and st == "RESOLVED")

    # 2: pinned at grid bottom -> PINNED_LOW (D12p failure class)
    pts = normalize("y", [[10, 0.95], [20, 0.97]])
    tf, st = floor_of(pts, 0.9)
    check("pinned-low flagged", tf == 10.0 and st == "PINNED_LOW")

    # 3: never crosses -> NEVER
    pts = normalize("z", [[10, 0.4], [800, 0.89]])
    tf, st = floor_of(pts, 0.9)
    check("never-cross", tf is None and st == "NEVER")

    # 4: corrected signal form s = p*(1-2eps)
    check("seff 0.3,0.1 = 0.24", abs(seff_from(0.3, 0.1) - 0.24) < 1e-12)

    # 5: degenerate signal (s = 0, e.g. eps=0.5) refused loud at run level
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        cp0 = os.path.join(d, "c0.json")
        with open(cp0, "w") as f:
            json.dump({"c": [[10, 0.95]]}, f)
        a0 = argparse.Namespace(curves=cp0, bar=0.9, w=8, p=0.3, eps=0.5, seff=None,
                                alpha=1.92, c_bound=None, strict=False, out=None)
        s_fail = False
        try:
            run_scan(a0)
        except SystemExit as e:
            s_fail = e.code == RC_INPUT
    check("degenerate s fails loud", s_fail)
    curves = {
        "good": [[10, 0.5], [40, 0.93]],
        "bad": [[10, 0.5], [40, 0.93]],
    }
    with tempfile.TemporaryDirectory() as d:
        cp = os.path.join(d, "c.json")
        with open(cp, "w") as f:
            json.dump(curves, f)
        # good: T=40, s=0.24, alpha=1.92 -> C=8*40*0.24^1.92 ~ 20.3 (bound 60 OK)
        a = argparse.Namespace(curves=cp, bar=0.9, w=8, p=0.3, eps=0.1, seff=None,
                               alpha=1.92, c_bound=60.0, strict=False, out=None)
        r = run_scan(a)
        check("e2e good KEEP", r["verdict"] == "KEEP" and r["curves"]["good"]["within_bound"])
        # bad: same curve but bound 10 -> violated
        a.c_bound = 10.0
        r = run_scan(a)
        check("e2e bound-violation FAIL", r["verdict"] == "FAIL")
        # strict + pinned curve books FAIL
        curves2 = {"pin": [[10, 0.99], [20, 0.99]]}
        cp2 = os.path.join(d, "c2.json")
        with open(cp2, "w") as f:
            json.dump(curves2, f)
        a2 = argparse.Namespace(curves=cp2, bar=0.9, w=8, p=0.3, eps=0.1, seff=None,
                                alpha=1.92, c_bound=None, strict=True, out=None)
        r = run_scan(a2)
        check("strict pinned FAIL", r["verdict"] == "FAIL")

    print("selftest", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(
        prog="floor_scan",
        description="Extract T_floors from accuracy-vs-T curves; flag grid-pinned floors; "
                    "optional C_emp law check (D12q-corrected s = p*(1-2eps)).",
        epilog=__doc__.split("Worked example:")[1].split("Self-test")[0] if __doc__ else None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--curves", help="JSON curves file {name: [[t,acc],...] or {t:[],acc:[]}}")
    ap.add_argument("--bar", type=float, default=0.9, help="accuracy bar (default 0.9)")
    ap.add_argument("--w", type=float, default=None, help="streams W for C_emp")
    ap.add_argument("--p", type=float, default=None, help="partner-correlation p (s = p*(1-2eps))")
    ap.add_argument("--eps", type=float, default=None, help="noise eps")
    ap.add_argument("--seff", type=float, default=None, help="signal strength directly (overrides p/eps)")
    ap.add_argument("--alpha", type=float, default=1.92, help="law exponent (default 1.92)")
    ap.add_argument("--c-bound", type=float, default=None, help="law gate: C_emp <= bound on RESOLVED floors")
    ap.add_argument("--strict", action="store_true", help="PINNED_LOW/NEVER curves book FAIL")
    ap.add_argument("--out", default=None, help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        sys.exit(selftest())
    if not args.curves:
        _fail("--curves required (or --selftest)")
    r = run_scan(args)
    print_receipt(r)
    if r["verdict"] == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
