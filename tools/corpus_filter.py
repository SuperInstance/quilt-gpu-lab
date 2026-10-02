#!/usr/bin/env python3
"""corpus_filter — validity filter for results-corpus receipts.

Lifted from the S6a two-witness reconciliation (experiments/s6a_delta_direction.py,
commit 6cf6c41): a poisoned corpus (harness-invalid runs, KILL receipts, bad JSON,
NaN values) silently poisons every downstream fit. This tool makes the filter
reusable: point it at a directory of JSON receipts and get back a clean corpus
plus an auditable exclusion report.

Rules (each exclusion is booked with a reason, never silent):
  1. filename contains "harness-invalid" or "KILL" -> excluded (validity filter)
  2. file is not valid JSON                        -> excluded ("bad json")
  3. any numeric value in the receipt is NaN/Inf   -> excluded ("non-finite")
  4. rows are extracted tolerantly: any list-of-dicts
     (like s6a's `grid:` / `probe:` extractors)

Exit codes: 0 ok, 1 usage/file error, 2 fail-loud gate (e.g. corpus below --min-rows).

Usage:
  python tools/corpus_filter.py --dir results --out scratch/corpus.json
  python tools/corpus_filter.py --dir results --min-rows 40   # S6a-style gate
  python tools/corpus_filter.py --selftest

Worked example (doctest-style):
  >>> import json, tempfile, os
  >>> d = tempfile.mkdtemp()
  >>> _ = open(os.path.join(d, "a_KEEP.json"), "w").write(
  ...     json.dumps({"experiment": "d1a", "grid": [{"W": 8, "N": 2, "p": 0.3,
  ...               "T": 40, "acc": 0.95}]})
  ... )
  >>> _ = open(os.path.join(d, "b_KILL.json"), "w").write('{"grid": []}')
  >>> _ = open(os.path.join(d, "c_broken.json"), "w").write("{not json")
  >>> rc = main(["--dir", d, "--out", os.path.join(d, "_corpus.json")])
  corpus_filter: 1 rows kept, 2 files excluded, corpus -> ...
"""
import argparse
import json
import math
import os
import sys


def nonfinite_paths(obj, path="$"):
    """Yield JSON paths of any non-finite numeric value in obj."""
    if isinstance(obj, bool):
        return
    if isinstance(obj, float):
        if not math.isfinite(obj):
            yield path
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from nonfinite_paths(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from nonfinite_paths(v, f"{path}[{i}]")


def extract_rows(data):
    """Tolerant row extractor: returns (rows, how) — list-of-dicts anywhere."""
    if isinstance(data.get("grid"), list) and data["grid"]:
        return data["grid"], "grid"
    for key, val in data.items():
        if isinstance(val, list) and val and isinstance(val[0], dict):
            return val, f"probe:{key}"
    return None, "no list-of-dicts found"


def filter_corpus(results_dir, min_rows=1):
    """Returns (rows, exclusions, stats). Raises RuntimeError on fail-loud gates."""
    if not os.path.isdir(results_dir):
        raise RuntimeError(f"not a directory: {results_dir}")
    rows, exclusions, parsed = [], [], 0
    for base in sorted(os.listdir(results_dir)):
        if not base.endswith(".json"):
            continue
        if "harness-invalid" in base or "KILL" in base:
            exclusions.append({"file": base,
                               "reason": "validity filter: invalid/KILL receipt excluded"})
            continue
        try:
            with open(os.path.join(results_dir, base)) as fh:
                data = json.load(fh)
        except Exception as exc:
            exclusions.append({"file": base, "reason": f"bad json: {exc.__class__.__name__}"})
            continue
        bad = next(nonfinite_paths(data), None)
        if bad is not None:
            exclusions.append({"file": base, "reason": f"non-finite at {bad}"})
            continue
        got, how = extract_rows(data)
        if got:
            rows.extend(got)
            parsed += 1
        else:
            exclusions.append({"file": base, "reason": f"unparsed: {how}"})
    if len(rows) < min_rows:
        raise RuntimeError(
            f"corpus too small: {len(rows)} rows < min {min_rows} — aborting, no fake data")
    return rows, exclusions, {"files_parsed": parsed, "rows": len(rows),
                              "excluded": len(exclusions)}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Validity-filter a directory of JSON experiment receipts.")
    ap.add_argument("--dir", default="results", help="directory of JSON receipts")
    ap.add_argument("--out", help="write filtered corpus + exclusion report here")
    ap.add_argument("--min-rows", type=int, default=1,
                    help="fail-loud (exit 2) if fewer rows survive")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        import tempfile
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "a.json"), "w") as fh:
            json.dump({"experiment": "x", "grid": [{"acc": 0.9, "T": 1}]}, fh)
        with open(os.path.join(d, "b_KILL.json"), "w") as fh:
            fh.write("{}")
        with open(os.path.join(d, "c.json"), "w") as fh:
            fh.write('{"v": NaN}')
        with open(os.path.join(d, "d.json"), "w") as fh:
            fh.write("{broken")
        rows, exc, stats = filter_corpus(d)
        assert stats["rows"] == 1 and stats["excluded"] == 3, stats
        print("SELFTEST OK:", json.dumps(stats))
        return 0

    try:
        rows, exclusions, stats = filter_corpus(args.dir, args.min_rows)
    except RuntimeError as exc:
        print(f"corpus_filter: FAIL: {exc}", file=sys.stderr)
        return 2
    report = {"stats": stats, "exclusions": exclusions, "rows": rows}
    print(f"corpus_filter: {stats['rows']} rows kept, {stats['excluded']} files "
          f"excluded", end="")
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as fh:
            json.dump(report, fh, indent=2)
            fh.write("\n")
        print(f", corpus -> {args.out}")
    else:
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
