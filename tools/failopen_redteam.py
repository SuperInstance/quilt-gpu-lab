"""failopen-redteam — fail-open injection red-team for any verdict surface
(pattern lifted PROVEN from VNaN-1, booked 2026-10-09 commit bbd4752: a
verdict gate accepted float('nan') against bounds and returned PASS — "gate
passes bounds" is fail-open against non-numeric garbage; this mechanizes the
red-team for ANY callable).

For each (field, injection) pair: call target(**base + {field: inj}) and
classify the outcome —
  REFUSE  raised (any exception is loud = safe)
  LATTICE returned a verdict != "PASS" (non-PASS verdict = also safe)
  ALLOWED a RED with a documented allowlist entry (by design, cited)
  RED     returned verdict == "PASS" on garbage (fail-open — the bug class)

Exit 0 iff no un-allowlisted RED. Fail-loud rc=2 on bad inputs.
Stdlib-only. Never echoes secrets; runs in-process, read-only on the target.

CLI:
  python tools/failopen_redteam.py --module tools/verdict_gate.py \
      --target finalize --base '{"name":"g","value":0.9,"minimum":0.8}' \
      --fields value,minimum --verdict-key verdict [--allow 'minimum:nan'] [--out r.json]
  python tools/failopen_redteam.py --selftest

Library:
    from tools.failopen_redteam import redteam
    rep = redteam(fn, base={"value":0.9,"minimum":0.8}, fields=["value","minimum"],
                  probes=None, verdict_key="verdict")
    assert rep["reds"] == [], rep["why"]
"""
import argparse
import importlib.util
import json
import math
import sys

DEFAULT_PROBES = [float("nan"), float("inf"), float("-inf"),
                  "NaN", "nan", "None", None, ""]
PASS_WORDS = ("PASS", "KEEP", "GREEN", "OK", "TRUE", "1")


def _is_pass(verdict):
    return str(verdict).strip().upper() in PASS_WORDS


def _classify(out, verdict_key):
    if out is None:
        return "REFUSE", "returned None"
    try:
        verdict = out.get(verdict_key) if isinstance(out, dict) else out
    except Exception as e:  # noqa: BLE001
        return "REFUSE", f"{type(e).__name__}"
    if verdict is None:
        return "REFUSE", "no verdict field"
    if _is_pass(verdict):
        return "RED", f"verdict={verdict}"
    return "LATTICE", f"verdict={verdict}"


def redteam(fn, base, fields, probes=None, verdict_key="verdict",
            allow=None, surface="target"):
    """Run the injection battery. Returns receipt dict; exit logic in cli()."""
    probes = DEFAULT_PROBES if probes is None else probes
    allow = set(allow or [])
    cells, reds = [], []
    for field in fields:
        if field not in base:
            raise ValueError(f"fail-loud: field {field!r} not in base kwargs")
        for inj in probes:
            kwargs = dict(base)
            kwargs[field] = inj
            try:
                out = fn(**kwargs)
            except Exception as e:  # noqa: BLE001
                cells.append({"field": field, "inj": repr(inj),
                              "outcome": "REFUSE", "detail": f"{type(e).__name__}"})
                continue
            outcome, detail = _classify(out, verdict_key)
            key = f"{field}:{repr(inj)}"
            if outcome == "RED" and key in allow:
                outcome, detail = "ALLOWED", detail + " [allowlisted]"
            cell = {"field": field, "inj": repr(inj),
                    "outcome": outcome, "detail": detail}
            cells.append(cell)
            if outcome == "RED":
                reds.append(cell)
    verdict = "CLEAN" if not reds else "FAIL-OPEN"
    return {"tool": "failopen_redteam", "surface": surface,
            "verdict": verdict, "n_injections": len(cells),
            "reds": reds, "cells": cells,
            "why": (f"{len(reds)} fail-open injection(s)" if reds
                    else "no un-allowlisted RED across the battery")}


def _load(module_path, target):
    spec = importlib.util.spec_from_file_location("_frt_target", module_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"fail-loud: cannot load module {module_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, target, None)
    if not callable(fn):
        raise ValueError(f"fail-loud: {target!r} not callable in {module_path}")
    return fn


def _selftest():
    checks = []

    def fail_open_gate(value, minimum):  # the VNaN-1 bug class
        try:
            if float(value) >= float(minimum):
                return {"verdict": "PASS"}
            return {"verdict": "FAIL"}
        except (TypeError, ValueError):
            return {"verdict": "PASS"}  # <- fail-open: garbage PASSes

    def fail_closed_gate(value, minimum):
        v, m = float(value), float(minimum)
        if math.isnan(v) or math.isnan(m) or math.isinf(v) or math.isinf(m):
            raise ValueError("non-finite input refused")
        return {"verdict": "PASS" if v >= m else "FAIL"}

    rep = redteam(fail_open_gate, {"value": 0.9, "minimum": 0.8},
                  ["value", "minimum"])
    # NOTE (selftest-caught pin bug): nan books LATTICE here, not RED —
    # float('nan') >= 0.8 is False so the gate honestly FAILs it. The real
    # fail-open reds are inf/None/'' (garbage that PASSes). Pin those.
    checks.append(("fail-open gate caught", rep["verdict"] == "FAIL-OPEN"
                   and any(c["field"] == "value" and c["inj"] == "inf"
                           for c in rep["reds"])
                   and any(c["field"] == "value" and c["inj"] == "nan"
                           and c["outcome"] == "LATTICE"
                           for c in rep["cells"])))  # nan must NOT count as RED
    def allow_gate(value, minimum):  # REDs only on inf (documented by design)
        import math as _m
        try:
            v, m = float(value), float(minimum)
        except (TypeError, ValueError):
            return {"verdict": "FAIL"}  # garbage refused as FAIL, not PASS
        if _m.isnan(v) or _m.isnan(m):
            raise ValueError("nan refused")
        if _m.isinf(v) or _m.isinf(m):
            return {"verdict": "PASS"}  # documented allow-by-design
        return {"verdict": "PASS" if v >= m else "FAIL"}

    rep2 = redteam(fail_closed_gate, {"value": 0.9, "minimum": 0.8},
                   ["value", "minimum"])
    checks.append(("fail-closed gate CLEAN", rep2["verdict"] == "CLEAN"))
    rep3 = redteam(allow_gate, {"value": 0.9, "minimum": 0.8},
                   ["value"], allow=["value:inf", "value:-inf"])  # both infinities
    checks.append(("allowlist books ALLOWED", rep3["verdict"] == "CLEAN"
                   and any(c["outcome"] == "ALLOWED" for c in rep3["cells"])))
    rep4 = redteam(allow_gate, {"value": 0.9, "minimum": 0.8}, ["value"])
    checks.append(("un-allowlisted RED still fires", rep4["verdict"] == "FAIL-OPEN"
                   and any(c["inj"] == "inf" and c["outcome"] == "RED"
                           for c in rep4["reds"])))
    try:
        redteam(fail_closed_gate, {"value": 0.9}, ["nope"])
        checks.append(("bad field fail-loud", False))
    except ValueError:
        checks.append(("bad field fail-loud", True))
    ok = all(p for _, p in checks)
    print(json.dumps({"tool": "failopen_redteam", "selftest": ok,
                      "checks": [n for n, p in checks if not p]}))
    return 0 if ok else 1


def cli():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--module", help="path to .py containing the target")
    ap.add_argument("--target", help="callable name (called with **kwargs)")
    ap.add_argument("--base", help="base kwargs JSON object")
    ap.add_argument("--fields", help="comma-separated fields to inject into")
    ap.add_argument("--verdict-key", default="verdict")
    ap.add_argument("--allow", action="append", default=[],
                    help="allowlist entry field:repr (repeatable)")
    ap.add_argument("--out", help="receipt path")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(_selftest())
    if not (a.module and a.target and a.base and a.fields):
        ap.error("--module --target --base --fields required (or --selftest)")
    base = json.loads(a.base)
    if not isinstance(base, dict):
        ap.error("--base must be a JSON object")
    fn = _load(a.module, a.target)
    rep = redteam(fn, base, [f.strip() for f in a.fields.split(",")],
                  verdict_key=a.verdict_key, allow=a.allow,
                  surface=f"{a.module}:{a.target}")
    text = json.dumps(rep, indent=2)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text + "\n")
    print(text)
    sys.exit(0 if rep["verdict"] == "CLEAN" else 1)


if __name__ == "__main__":
    cli()
