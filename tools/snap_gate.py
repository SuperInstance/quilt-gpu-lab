#!/usr/bin/env python3
"""snap-gate — eps-resolution identity gate for two numeric runs.

Pattern lifted PROVEN from DETERM-1 (lattice-snap determinism probe, booked
2026-10-07: Arm B snapped v/champ_v to an eps-lattice each selection round and
the lane stayed within noise of Arm A — "same computation" for a noisy float
pipeline means the SAME EPS-CELLS, not bit-identity). det_witness is sha256
bit-strict (too strong for seeded-GPU reruns); verdict_repro compares one
verdict field (too weak). This is the middle rung: snap both runs to the
eps-lattice and gate the fraction of lattice-cell disagreements.

Cell index = round(x / eps) (ties-to-even, Python round semantics —
deterministic and order-independent per value). A pair (a, b) MISMATCHES iff
their cells differ. Books SAME rc=0 iff mismatch fraction <= bar (default 0.0:
every value must land in the same cell), DRIFTED rc=1 otherwise, FAIL-INPUT
rc=2 for non-finite values, length mismatches, eps <= 0, or unparseable JSON.

Input: JSON flat array of numbers, or an object of (nested) objects/arrays of
numbers — leaves are flattened to stable dotted paths so structure drift
(added/missing/renamed fields) fails loud as a mismatch-class error, not a
silent PASS. Stdlib-only, deterministic, one JSON receipt.

Usage:
  python tools/snap_gate.py --a run1.json --b run2.json [--eps 0.01 --bar 0.0 --out r.json]
  python tools/snap_gate.py --a '[1.004, 2.0]' --b '[1.001, 2.009]' --eps 0.01
  python tools/snap_gate.py --selftest

Worked example: a=[1.004, 2.0], b=[1.001, 2.009], eps=0.01 -> cells
[100,200] vs [100,201] -> 1 mismatch / 2 = 0.5 -> DRIFTED rc=1 (2.009 rounds
to cell 201, one quantum away — the gate sees it even though |diff| is tiny).
"""

import argparse
import json
import math
import sys

EXIT_SAME, EXIT_DRIFTED, EXIT_FAIL = 0, 1, 2


def flatten(obj, path=""):
    """Flatten nested lists/dicts of numbers to {dotted.path: value}. Fail loud on non-numbers."""
    out = {}
    if isinstance(obj, dict):
        if not obj:
            raise ValueError(f"empty object at '{path or '<root>'}'")
        for k, v in obj.items():
            out.update(flatten(v, f"{path}.{k}" if path else str(k)))
    elif isinstance(obj, list):
        if not obj:
            raise ValueError(f"empty array at '{path or '<root>'}'")
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{path}[{i}]"))
    elif isinstance(obj, bool) or not isinstance(obj, (int, float)):
        raise ValueError(f"non-number at '{path or '<root>'}': {type(obj).__name__}")
    elif not math.isfinite(obj):
        raise ValueError(f"non-finite value at '{path or '<root>'}'")
    else:
        out[path or "value"] = float(obj)
    return out


def cell(x, eps):
    """Lattice-cell index; ties-to-even via Python round (deterministic)."""
    return round(x / eps)


def compare(a, b, eps, bar):
    """Gate two parsed JSON docs. Returns (rc, receipt_dict)."""
    fa, fb = flatten(a), flatten(b)
    keys_a, keys_b = set(fa), set(fb)
    if keys_a != keys_b:
        only_a = sorted(keys_a - keys_b)[:5]
        only_b = sorted(keys_b - keys_a)[:5]
        return EXIT_FAIL, {
            "verdict": "FAIL-INPUT", "why": "structure drift",
            "only_in_a": only_a, "only_in_b": only_b,
        }
    n = len(fa)
    mismatches, max_abs, max_rel_path = [], 0.0, ""
    for k in sorted(fa):
        va, vb = fa[k], fb[k]
        ca, cb = cell(va, eps), cell(vb, eps)
        d = abs(va - vb)
        if d > max_abs:
            max_abs, max_rel_path = d, k
        if ca != cb:
            mismatches.append({
                "path": k, "a": va, "b": vb, "cell_a": ca, "cell_b": cb,
                "cells_apart": abs(ca - cb), "abs_diff": d,
            })
    frac = len(mismatches) / n
    rc = EXIT_SAME if frac <= bar else EXIT_DRIFTED
    receipt = {
        "tool": "snap-gate", "verdict": "SAME" if rc == EXIT_SAME else "DRIFTED",
        "eps": eps, "bar": bar, "n_values": n,
        "mismatch_count": len(mismatches), "mismatch_frac": frac,
        "max_abs_diff": max_abs, "max_abs_diff_path": max_rel_path,
        "quantum": eps / 2.0,
        "mismatches": mismatches[:20],
        "note": "cell = round(x/eps), ties-to-even; mismatch = differing lattice cell",
    }
    return rc, receipt


def selftest():
    """Positive + RED battery. Each pin names the failure it guards."""
    checks = []

    def pin(name, cond):
        checks.append((name, bool(cond)))

    # 1. identical arrays -> SAME
    rc, r = compare([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], 0.01, 0.0)
    pin("identical-SAME", rc == EXIT_SAME and r["mismatch_count"] == 0)

    # 2. same-cell jitter -> SAME (the DETERM-1 Arm-B class)
    rc, r = compare([1.0049, 2.0], [1.0051 - 0.009, 2.0], 0.01, 0.0)
    pin("same-cell-jitter-SAME", rc == EXIT_SAME)

    # 3. one-quantum boundary cross -> DRIFTED (the worked example)
    rc, r = compare([1.004, 2.0], [1.001, 2.009], 0.01, 0.0)
    pin("one-quantum-DRIFTED", rc == EXIT_DRIFTED and r["mismatch_count"] == 1
        and abs(r["mismatches"][0]["abs_diff"] - 0.009) < 1e-12)

    # 4. bar allows tolerated drift -> SAME (bar is a real knob, honest at 0)
    rc, r = compare([1.004, 2.0], [1.001, 2.009], 0.01, 0.5)
    pin("bar-tolerates", rc == EXIT_SAME)

    # 5. nested dicts flatten to stable paths
    rc, r = compare({"m": {"v": [1.0, 2.0]}}, {"m": {"v": [1.0, 2.0]}}, 0.01, 0.0)
    pin("nested-paths-SAME", rc == EXIT_SAME and "m.v[0]" in flatten({"m": {"v": [1.0, 2.0]}}))

    # 6. structure drift -> rc=2 (a renamed key must never silently PASS)
    rc, r = compare({"v": 1.0}, {"w": 1.0}, 0.01, 0.0)
    pin("structure-drift-rc2", rc == EXIT_FAIL and r["verdict"] == "FAIL-INPUT")

    # 7. length mismatch -> rc=2
    rc, r = compare([1.0, 2.0], [1.0], 0.01, 0.0)
    pin("length-mismatch-rc2", rc == EXIT_FAIL)

    # 8. NaN -> rc=2 (non-finite never gates)
    try:
        rc, r = compare([1.0, float("nan")], [1.0, 2.0], 0.01, 0.0)
        pin("nan-rc2", False)
    except ValueError:
        pin("nan-rc2", True)

    # 9. bool is never a number (JSON true must not sneak through as 1)
    try:
        compare([True], [1.0], 0.01, 0.0)
        pin("bool-rc2", False)
    except ValueError:
        pin("bool-rc2", True)

    # 10. opposite lattice cells across zero -> DRIFTED (cells_apart booked)
    rc, r = compare([0.006], [-0.006], 0.01, 0.0)
    pin("zero-crossing-DRIFTED", rc == EXIT_DRIFTED and r["mismatches"][0]["cells_apart"] == 2)

    # 11. within-half-quantum around zero is honestly SAME (bad-pin guard for #10:
    # +-0.004 both tie to cell 0 — a sub-half-quantum sign flip is not drift)
    rc, r = compare([0.004], [-0.004], 0.01, 0.0)
    pin("zero-subquantum-SAME", rc == EXIT_SAME)

    ok = all(c for _, c in checks)
    print(json.dumps({
        "selftest": "PASS" if ok else "FAIL",
        "checks": [{"name": n, "ok": c} for n, c in checks],
    }, indent=1))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="eps-resolution identity gate (DETERM-1 lattice-snap pattern)")
    ap.add_argument("--a", help="run A: JSON file path or inline JSON literal")
    ap.add_argument("--b", help="run B: JSON file path or inline JSON literal")
    ap.add_argument("--eps", type=float, default=0.01, help="lattice quantum (default 0.01)")
    ap.add_argument("--bar", type=float, default=0.0, help="max tolerated mismatch fraction (default 0.0)")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true", help="run the pin battery and exit")
    args = ap.parse_args()

    def load(spec):
        try:
            with open(spec) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return json.loads(spec)

    if args.selftest:
        sys.exit(selftest())
    if args.a is None or args.b is None:
        ap.error("--a and --b are required (or --selftest)")
    if not (args.eps > 0) or not math.isfinite(args.eps):
        print("FAIL-INPUT: --eps must be finite and > 0", file=sys.stderr)
        sys.exit(EXIT_FAIL)
    if not (0.0 <= args.bar <= 1.0) or not math.isfinite(args.bar):
        print("FAIL-INPUT: --bar must be in [0, 1]", file=sys.stderr)
        sys.exit(EXIT_FAIL)

    try:
        a, b = load(args.a), load(args.b)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"FAIL-INPUT: unparseable JSON: {e}", file=sys.stderr)
        sys.exit(EXIT_FAIL)

    try:
        rc, receipt = compare(a, b, args.eps, args.bar)
    except ValueError as e:
        print(f"FAIL-INPUT: {e}", file=sys.stderr)
        sys.exit(EXIT_FAIL)
    receipt["eps"] = args.eps
    receipt["bar"] = args.bar

    if args.out:
        with open(args.out, "w") as f:
            json.dump(receipt, f, indent=1)
            f.write("\n")
    print(json.dumps(receipt, indent=1))
    sys.exit(rc)


if __name__ == "__main__":
    main()
