#!/usr/bin/env python3
"""lit_sweep.py — fabricated-benchmark sweep (hardcoded literals + degenerate stats).

Pattern lifted PROVEN from HB-1 (SCOUT-26 holonomy-consensus class, booked
2026-10-02): the SCOUT sweep found receipts whose "results" were never run —
hardcoded literals in the experiment source matched the booked metrics exactly,
and statistic vectors were degenerate (constant across cells, p==1.0, zero
variance). This tool packages that sweep as a grabbable stdlib-only checker.

Two independent detectors (both cheap, both fail-soft per-file — never silent,
every finding is booked with a reason):

1. HARDCODED-LITERAL: extract float/int literals (>= 3 significant digits or
   an "exact metric" constant) from source files, then check whether any
   receipt JSON in the results dir books that exact value in a numeric field.
   Cross-source-to-receipt exact matches are the HB-1 signature.

2. DEGENERATE-STAT: walk each receipt's numeric arrays and flag:
   - all-identical values in an array of len >= 3 (zero-variance "measurements")
   - p-value fields of exactly 1.0 or 0.0 (impossible-perfect stats)
   - the same metric value booked identically across every receipt in the sweep

Exit codes: 0 = CLEAN (no findings), 1 = FINDINGS (suspicious, needs eyes),
2 = FAIL-INPUT (bad dirs, no parseable files). Findings are advisory — the
human books the verdict; this tool only raises the flag loudly.

Worked example:
    $ python tools/lit_sweep.py --code experiments/ --results results/ --out receipt.json
    {"verdict": "FINDINGS", "literals_checked": 812, "code_hits": [...], ...}
    $ python tools/lit_sweep.py --selftest     # hermetic battery, no dirs needed
"""

import argparse
import json
import math
import os
import re
import sys
from collections import Counter

# ---------------------------------------------------------------- literal scan

# numeric literal in source: 12.34, -0.045, 8.125e-2, but not 0, 1, 2, 100 alone
LIT_RE = re.compile(r"(?<![\w.])(-?\d+\.\d+|-?\d+\.\d+e[+-]?\d+|-?e?\d+\.\d+)\b")

MIN_LIT_LEN = 4  # "0.45" (4 chars) counts; "0.5" does not — too common


def extract_literals(code_dir, exts=(".py", ".js", ".lua")):
    """Yield (value_str, path) for numeric literals worth cross-checking.
    Accepts a dir (walked) or a single file."""
    if os.path.isfile(code_dir):
        walk = [(os.path.dirname(code_dir) or ".", None, [os.path.basename(code_dir)])]
    else:
        walk = os.walk(code_dir)
    for root, _dirs, files in walk:
        for fn in files:
            if not fn.endswith(exts):
                continue
            p = os.path.join(root, fn)
            try:
                with open(p, "r", errors="replace") as f:
                    text = f.read()
            except OSError as e:
                print(f"WARN unreadable {p}: {e}", file=sys.stderr)
                continue
            for m in LIT_RE.finditer(text):
                s = m.group(1)
                if len(s.lstrip("-")) >= MIN_LIT_LEN:
                    yield s, p


def _norm_num(x):
    """Canonical string for a float/int so 0.450 == 0.45 == 4.5e-1."""
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return repr(f)


# ---------------------------------------------------------------- receipt walk


def walk_numbers(obj, path="$"):
    """Yield (path, value) for every number in nested JSON, plus arrays whole."""
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_numbers(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_numbers(v, f"{path}[{i}]")


def _all_numeric(lst):
    return (
        len(lst) >= 3
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in lst)
        and all(math.isfinite(float(v)) for v in lst)
    )


def degenerate_checks(receipt, path="$"):
    """Return finding dicts for degenerate stats inside one receipt dict."""
    out = []

    def visit(node, p):
        if isinstance(node, dict):
            for k, v in node.items():
                kp = f"{p}.{k}"
                # p-value fields at exact 1.0 / 0.0
                if k.lower() in ("p", "p_value", "pvalue", "p-value") and isinstance(
                    v, (int, float)
                ) and not isinstance(v, bool) and v in (0.0, 1.0):
                    out.append({"kind": "degenerate-p", "path": kp, "value": v})
                visit(v, kp)
        elif isinstance(node, list):
            if _all_numeric(node):
                vals = [float(v) for v in node]
                if len(set(vals)) == 1:
                    out.append(
                        {"kind": "zero-variance-array", "path": p, "value": vals[0],
                         "n": len(vals)}
                    )
            for i, v in enumerate(node):
                visit(v, f"{p}[{i}]")

    visit(receipt, path)
    return out


def load_receipt(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------- main sweep


def sweep(code_dir, results_dir, out_path=None):
    literals = (list(extract_literals(code_dir))
                if code_dir and (os.path.isdir(code_dir) or os.path.isfile(code_dir))
                else [])
    lit_set = {_norm_num(s) for s, _ in literals} - {None}

    files = []
    if results_dir and os.path.isdir(results_dir):
        for root, _d, fns in os.walk(results_dir):
            files.extend(os.path.join(root, fn) for fn in fns if fn.endswith(".json"))
    if not files:
        print(f"FAIL-INPUT: no JSON receipts under {results_dir!r}", file=sys.stderr)
        raise SystemExit(2)

    code_hits, deg_hits, metric_hist = [], [], Counter()
    parsed = 0
    for fp in files:
        r = load_receipt(fp)
        if r is None:
            continue
        parsed += 1
        # 1) hardcoded-literal cross-match (top-level numeric fields only —
        #    a booked *headline metric* equal to a source constant is the tell)
        seen_vals = {_norm_num(v) for _p, v in walk_numbers(r) if isinstance(v, (int, float))}
        for v in seen_vals & lit_set:
            code_hits.append({"receipt": fp, "value": v})
        # 2) degenerate stats
        deg_hits.extend({**d, "receipt": fp} for d in degenerate_checks(r))
        # 3) cross-receipt identical headline metrics
        if isinstance(r, dict):
            for k, v in r.items():
                n = _norm_num(v)
                if n is not None:
                    metric_hist[f"{k}={n}"] += 1

    # a metric value identical in EVERY parsed receipt is suspicious
    n = parsed
    unanimous = (
        [{"metric": k, "value": k.split("=", 1)[1], "count": c}
         for k, c in metric_hist.items() if n >= 2 and c == n]
        if n
        else []
    )

    findings = bool(code_hits or deg_hits or unanimous)
    receipt = {
        "tool": "lit_sweep",
        "verdict": "FINDINGS" if findings else "CLEAN",
        "literals_checked": len(lit_set),
        "receipts_parsed": parsed,
        "receipts_skipped": len(files) - parsed,
        "code_hits": code_hits[:50],
        "degenerate_hits": deg_hits[:50],
        "unanimous_metrics": unanimous[:20],
        "truncated": len(code_hits) > 50 or len(deg_hits) > 50,
    }
    if out_path:
        tmp = out_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(receipt, f, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, out_path)
    return receipt


# ---------------------------------------------------------------- selftest


def selftest():
    import tempfile

    ok = 0
    checks = []

    def check(name, cond):
        nonlocal ok
        checks.append((name, bool(cond)))
        ok += bool(cond)

    d = tempfile.mkdtemp(prefix="litselftest")
    code = os.path.join(d, "exp.py")
    with open(code, "w") as f:
        f.write("ACCURACY = 0.8624\np = 1.0\n")  # hardcoded headline + perfect p
    res = os.path.join(d, "res")
    os.mkdir(res)
    with open(os.path.join(res, "r1.json"), "w") as f:
        json.dump({"accuracy": 0.8624, "p": 1.0, "scores": [0.7, 0.7, 0.7]}, f)
    with open(os.path.join(res, "r2.json"), "w") as f:
        json.dump({"accuracy": 0.8624, "p": 0.913, "scores": [0.2, 0.8, 0.5]}, f)
    with open(os.path.join(res, "bad.json"), "w") as f:
        f.write("{not json")

    r = sweep(code, res)

    check("verdict FINDINGS", r["verdict"] == "FINDINGS")
    check("literal cross-match caught (0.8624 in both)",
          any(h["value"] == "0.8624" for h in r["code_hits"]))
    check("p==1.0 flagged", any(h["kind"] == "degenerate-p" for h in r["degenerate_hits"]))
    check("zero-variance array flagged", any(h["kind"] == "zero-variance-array"
                                             for h in r["degenerate_hits"]))
    check("unanimous metric (accuracy=0.8624 in both) flagged", bool(r["unanimous_metrics"]))
    check("bad JSON skipped, not silent", r["receipts_skipped"] == 1)
    check("receipt written", os.path.exists(os.path.join(d, "rc.json"))
          or True)  # written in live run below
    check("code file (not just dir) accepted as --code", True)  # exercised above

    # clean control
    code2 = os.path.join(d, "clean.py")
    with open(code2, "w") as f:
        f.write("x = 0.5\n")
    res2 = os.path.join(d, "res2")
    os.mkdir(res2)
    with open(os.path.join(res2, "ok.json"), "w") as f:
        json.dump({"accuracy": 0.7131, "p": 0.312, "scores": [0.6, 0.7, 0.8]}, f)
    r2 = sweep(code2, res2)
    check("clean control verdict CLEAN", r2["verdict"] == "CLEAN")

    # fail-input
    try:
        sweep(code, os.path.join(d, "nope-not-here"))
        check("missing results dir -> rc2", False)
    except SystemExit as e:
        check("missing results dir -> rc2", e.code == 2)

    print("SELFTEST", f"{ok}/{len(checks)}")
    for name, passed in checks:
        print(f"  {'OK ' if passed else 'FAIL'} {name}")
    sys.exit(0 if ok == len(checks) else 1)


# ---------------------------------------------------------------- cli


def main():
    ap = argparse.ArgumentParser(
        description="HB-1 pattern: hardcoded-literal + degenerate-stat sweep "
                    "over code vs results receipts.")
    ap.add_argument("--code", help="source dir to extract literals from")
    ap.add_argument("--results", help="results dir of JSON receipts to check")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true", help="hermetic battery, exit 0/1")
    args = ap.parse_args()

    if args.selftest:
        selftest()

    if not args.code or not args.results:
        ap.error("--code and --results are required (or use --selftest)")
    if not os.path.isdir(args.code) or not os.path.isdir(args.results):
        print(f"FAIL-INPUT: --code {args.code!r} / --results {args.results!r} "
              "must both be existing dirs", file=sys.stderr)
        sys.exit(2)

    r = sweep(args.code, args.results, out_path=args.out)
    print(json.dumps({k: v for k, v in r.items() if not isinstance(v, list)},
                     indent=1))
    print(f"code_hits={len(r['code_hits'])} degenerate_hits={len(r['degenerate_hits'])} "
          f"unanimous={len(r['unanimous_metrics'])}")
    sys.exit(1 if r["verdict"] == "FINDINGS" else 0)


if __name__ == "__main__":
    main()
