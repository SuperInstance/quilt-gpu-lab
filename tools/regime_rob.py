#!/usr/bin/env python3
"""regime-rob — effect-persistence-across-regimes gate.

Pattern lifted PROVEN from D12ag (booked 2026-10-09): the mid-coupling k_eff dip
was measured only at W in {4,8}; the open question "is the dip real or a
narrow-width artifact?" was answered by re-measuring the implied effect across a
swept SECONDARY regime (W=16, eps grid) and gating on a QUORUM: the effect books
ROBUST only if it holds in >= quorum-fraction of regime cells — cells where the
effect statistic could not be resolved (harness or model floor missing) count
AGAINST the quorum, never silently dropped (an unresolved cell is not evidence
of robustness).

Inputs: cells JSON — a list of objects, each carrying any regime descriptors
(p, W, eps, ...) plus a numeric (or null) value under --value-key (default
"value"). Verdict ROBUST iff resolved-or-not, hits / len(cells) >= quorum,
where hit = value below band (--direction below, default) or above band
(--direction above). Unresolved (null/missing/str) cells book as misses and are
named in the receipt.

Stdlib-only, deterministic, fail-loud rc=2, one JSON receipt.
Exit 0=ROBUST / 1=ARTIFACT / 2=FAIL-INPUT.

Usage:
  python tools/regime_rob.py --cells '[{"p":0.5,"eps":0.0,"value":0.66},...]' \
      --band 1.0 --quorum 0.75 [--value-key value --direction below --out r.json]
  python tools/regime_rob.py --cells-file cells.json ...
  python tools/regime_rob.py --selftest

Worked example (D12ag replay, 8 cells, 7 in dip band):
  python tools/regime_rob.py --example   # -> ROBUST rc=0, hits 7/8, quorum 0.75
"""

import argparse
import json
import os
import sys

DEFAULT_VALUE_KEY = "value"


def classify(cells, value_key, band, quorum, direction):
    """Return (verdict, receipt_dict). Raises FailInput on bad input."""
    if not isinstance(cells, list) or not cells:
        raise FailInput("cells must be a non-empty JSON list")
    if not (0.0 < quorum <= 1.0):
        raise FailInput("quorum must be in (0, 1]")
    if direction not in ("below", "above"):
        raise FailInput("direction must be 'below' or 'above'")
    hits = 0
    resolved = 0
    per_cell = []
    for i, c in enumerate(cells):
        if not isinstance(c, dict):
            raise FailInput(f"cell {i} is not an object")
        v = c.get(value_key, None)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            per_cell.append({"index": i, "regime": _regime(c, value_key),
                             "value": v, "hit": None, "why": "unresolved"})
            continue
        v = float(v)
        if v != v or v in (float("inf"), float("-inf")):
            per_cell.append({"index": i, "regime": _regime(c, value_key),
                             "value": v, "hit": None, "why": "non-finite"})
            continue
        resolved += 1
        hit = (v < band) if direction == "below" else (v > band)
        hits += hit
        per_cell.append({"index": i, "regime": _regime(c, value_key),
                         "value": v, "hit": bool(hit)})
    frac = hits / len(cells)
    robust = frac >= quorum
    unresolved = [pc for pc in per_cell if pc.get("hit") is None]
    receipt = {
        "tool": "regime-rob",
        "band": band, "quorum": quorum, "direction": direction,
        "value_key": value_key,
        "n_cells": len(cells), "resolved": resolved,
        "unresolved": [pc["index"] for pc in unresolved],
        "hits": hits, "hit_fraction": round(frac, 4),
        "verdict": "ROBUST" if robust else "ARTIFACT",
        "cells": per_cell,
    }
    return robust, receipt


def _regime(c, value_key):
    return {k: v for k, v in c.items() if k != value_key}


class FailInput(Exception):
    pass


def _example_cells():
    # D12ag replay: 8 cells (p x eps), k_eff_implied at W=16; 6 in dip band <1.0
    vals = [0.66, 0.93, 0.95, 0.86, 1.08, 0.79, 0.98, 0.90]
    cells = []
    for p in (0.5, 0.525):
        for eps in (0.0, 0.05, 0.1, 0.2):
            cells.append({"p": p, "eps": eps, "value": vals.pop(0)})
    return cells


def selftest():
    fails = []
    def check(name, cond):
        if not cond:
            fails.append(name)

    # 1. all-in-band -> ROBUST
    rob, _ = classify([{"v": 0.5}, {"v": 0.6}], "v", 1.0, 0.75, "below")
    check("all-below-band ROBUST", rob)
    # 2. mostly-out -> ARTIFACT
    rob, r = classify([{"v": 0.5}, {"v": 0.6}, {"v": 5.0}, {"v": 6.0}],
                      "v", 1.0, 0.75, "below")
    check("half-miss ARTIFACT at 0.75 quorum", not rob and r["hits"] == 2)
    # 3. quorum edge exact
    rob, r = classify([{"v": 0.5}, {"v": 0.6}, {"v": 5.0}], "v", 1.0, 2 / 3, "below")
    check("exact-quorum 2/3 ROBUST", rob and r["hit_fraction"] == round(2 / 3, 4))
    # 4. unresolved counts against (named, never dropped)
    rob, r = classify([{"v": 0.5}, {"v": 0.6}, {"v": None}], "v", 1.0, 0.75, "below")
    check("unresolved counts against", not rob and r["unresolved"] == [2])
    # 5. direction above
    rob, _ = classify([{"v": 2.0}, {"v": 3.0}], "v", 1.0, 0.75, "above")
    check("direction-above hits", rob)
    for fn, exc in [
        (lambda: classify([], "v", 1.0, 0.5, "below"), True),
        (lambda: classify([{"v": 1}], "v", 1.0, 0.0, "below"), True),
        (lambda: classify([{"v": 1}], "v", 1.0, 0.5, "sideways"), True),
        (lambda: classify(["x"], "v", 1.0, 0.5, "below"), True),
    ]:
        try:
            fn()
            check("fail-loud rc2", False)
        except FailInput:
            pass
    if fails:
        print(json.dumps({"selftest": "FAIL", "failed": fails}))
        return 1
    print(json.dumps({"selftest": "PASS", "checks": 6 + 4}))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--cells", help="cells JSON inline")
    ap.add_argument("--cells-file", help="cells JSON file")
    ap.add_argument("--example", action="store_true", help="D12ag replay")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--band", type=float, default=1.0)
    ap.add_argument("--quorum", type=float, default=0.75)
    ap.add_argument("--direction", default="below", choices=["below", "above"])
    ap.add_argument("--value-key", default=DEFAULT_VALUE_KEY)
    ap.add_argument("--out", default=None, help="receipt JSON path")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()
    try:
        if a.example:
            cells = _example_cells()
        elif a.cells:
            cells = json.loads(a.cells)
        elif a.cells_file:
            with open(a.cells_file) as f:
                cells = json.load(f)
        else:
            print("FAIL-INPUT: one of --cells/--cells-file/--example/--selftest required",
                  file=sys.stderr)
            return 2
        robust, receipt = classify(cells, a.value_key, a.band, a.quorum, a.direction)
    except FailInput as e:
        print(f"FAIL-INPUT: {e}", file=sys.stderr)
        return 2
    except (json.JSONDecodeError, OSError) as e:
        print(f"FAIL-INPUT: {e}", file=sys.stderr)
        return 2
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w") as f:
            json.dump(receipt, f, indent=2)
    print(json.dumps({k: receipt[k] for k in
                      ("verdict", "hits", "n_cells", "hit_fraction",
                       "resolved", "unresolved")}))
    return 0 if robust else 1


if __name__ == "__main__":
    sys.exit(main())
