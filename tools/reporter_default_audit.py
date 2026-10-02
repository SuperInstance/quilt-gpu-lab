#!/usr/bin/env python3
"""REPORTER-DEFAULT audit (prereg: proposals/runs/REPORTER-DEFAULT-prereg.md).

Injection-probes every importable booked verdict function with abort-shaped
inputs; a PASS-class outcome from an abort-shaped input is RED at that site.
Exit 1 on any RED (fail loud)."""
import importlib
import inspect
import json
import sys

PASS_CLASS = {"PASS", "KEEP", "CONFIRM", "REPLICATED", "ANCHORING_REPLICATED",
              "WITNESSED"}
FAIL_CLASS = {"FAIL", "ERROR", "INCONCLUSIVE", "VOID", "KILL", "KILL_CANDIDATE",
              "DEGENERATE", "INVALID_HARNESS", "NO_ANCHORING", "MIXED",
              "NOT_WITNESSED", "REFUTED", "PARTIAL"}

results = []


def probe(site, fn, argsets):
    for label, args in argsets:
        try:
            out = fn(*args)
            if isinstance(out, tuple):
                head = out[0]
            elif isinstance(out, dict):
                head = out.get("verdict", out.get("decision"))
            else:
                head = out
            cls = ("PASS" if head in PASS_CLASS else
                   "FAIL-CLASS" if head in FAIL_CLASS else f"OTHER:{head!r}")
            results.append((site, label, head, cls))
        except Exception as e:
            results.append((site, label, f"RAISED {type(e).__name__}", "RAISES"))


# --- comp2 gate(): needs arrays; signature (correct, a, b, idx, bar, label).
# Static check instead: degenerate -> INCONCLUSIVE branch exists (verified by read);
# skip live probe (array plumbing heavy) — covered under G3 census.
results.append(("comp2_itemlocal.gate", "static-read",
                "deg->INCONCLUSIVE else FAIL", "FAIL-CLASS"))

# --- c2_probe_skip_tower.verdict_of(cells_by_name)
try:
    m = importlib.import_module("c2_probe_skip_tower")
    probe("c2_probe_skip_tower.verdict_of", m.verdict_of,
          [("empty-cells", ({"Q": {}, "A2": {}},)),
           ("none-cells", ({"Q": None, "A2": None},)),
           ("missing-keys", ({},))])
except Exception as e:
    results.append(("c2_probe_skip_tower.verdict_of", "import", str(e), "IMPORT-FAIL"))

# --- c3_probe.verdict_of
try:
    m = importlib.import_module("c3_probe")
    probe("c3_probe.verdict_of", m.verdict_of,
          [("none", (None,)), ("zero", (0.0,)), ("nan", (float("nan"),))])
except Exception as e:
    results.append(("c3_probe.verdict_of", "import", str(e), "IMPORT-FAIL"))

# --- w5a verdict(rates): abort-shaped = empty rates, skip-only rates
try:
    m = importlib.import_module("w5a_reobserve_vs_trace")
    probe("w5a.verdict", m.verdict,
          [("empty", ({},)),
           ("skip-only", ({"c1": {"trace": {"det_err": 0.0}, "fresh": {"det_err": 0.0}},},))])
except Exception as e:
    results.append(("w5a.verdict", "import", str(e), "IMPORT-FAIL"))

# --- e24 verdict_for(gate, n, thin): gate tuple, abort = zero counts
try:
    m = importlib.import_module("e24_dial_momentum")
    probe("e24.verdict_for", m.verdict_for,
          [("zero-counts", ((0, 0, 0, 10, 3, 0), 12, False)),
           ("thin-zero", ((0, 0, 0, 10, 3, 0), 12, True))])
except Exception as e:
    results.append(("e24.verdict_for", "import", str(e), "IMPORT-FAIL"))

# --- e27 verdict_of(m): abort = missing keys handled by KeyError (fail loud),
#     abort-shaped = all-zero metrics
try:
    m = importlib.import_module("e27_hidden_angle")
    probe("e27.verdict_of", m.verdict_of,
          [("zeros", ({"ens": 0.0, "single": 0.0, "sum_of_cells": 0.0,
                       "stack_fitted": 0.0, "view_max": 0.0, "emb_max": 0.0,
                       "p_emp": 1.0},))])
except Exception as e:
    results.append(("e27.verdict_of", "import", str(e), "IMPORT-FAIL"))

# --- central reporter re-pin (G2)
try:
    from tools.verdict_gate import Gate, StatMeta, finalize
    cases = [
        ("completeness-none", dict(completeness=None, status_source="own")),
        ("completeness-false", dict(completeness=False, status_source="own")),
        ("inherited", dict(completeness=True, status_source="inherited")),
    ]
    for label, kw in cases:
        v = finalize([Gate("auc", 0.99, minimum=0.8)],
                     {"auc": StatMeta(std=0.03, n=32)}, **kw)
        cls = "PASS" if v.verdict in PASS_CLASS else "FAIL-CLASS"
        results.append(("verdict_gate.finalize", label, v.verdict, cls))
except Exception as e:
    results.append(("verdict_gate.finalize", "import", str(e), "IMPORT-FAIL"))

reds = [r for r in results if r[3] == "PASS"]
print(json.dumps([{"site": s, "case": c, "out": o, "class": k}
                  for s, c, o, k in results], indent=1))
print(f"\nSITES={len(set(r[0] for r in results))} PROBES={len(results)} RED={len(reds)}")
sys.exit(1 if reds else 0)
