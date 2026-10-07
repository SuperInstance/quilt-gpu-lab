#!/usr/bin/env python3
"""json-gate — generic fail-loud JSON input validator for the tool fleet.

Pattern lifted from the fleet-wide convention (every tool here re-implements
this inline): receipts and inputs must carry REQUIRED KEYS with REQUIRED
TYPES (and optional finite-number / non-empty constraints) or the tool must
refuse loudly BEFORE any computation. This mechanizes that refusal.

Rules format (JSON or --rules JSON string): a dict of key-path (dot-notation
for nested) -> type name, one of:
    str, int, float, num (int or float, non-finite fails), bool,
    list, dict, any
Optional per-key flags via "<type>!"  -> must be non-empty (str/list/dict)
                             "<type>?" -> may be missing (None also ok)
Non-finite floats (NaN/Inf) always fail for num/float regardless of flags.

Exit codes: 0=PASS, 1=GATE-FAIL (booked honestly, JSON receipt), 2=FAIL-INPUT
(bad rules, unreadable/invalid JSON, missing file).

Stdlib-only, deterministic, read-only on inputs.

Worked example:
    $ echo '{"verdict":"KEEP","tau":0.5,"gates":[true,false]}' > r.json
    $ python tools/json_gate.py --file r.json \
        --rules '{"verdict":"str!","tau":"num","gates":"list!"}'
    -> exit 0, receipt written, keys checked.
    $ echo '{"verdict":"KEEP"}' > bad.json
    $ python tools/json_gate.py --file bad.json --rules '{"tau":"num"}'
    -> exit 1 (missing key "tau"), receipt names the violation.

Selftest: python tools/json_gate.py --selftest   (positive + RED battery)
"""
import argparse
import json
import math
import os
import sys
import tempfile

RC_PASS, RC_FAIL, RC_INPUT = 0, 1, 2
TYPES = {"str", "int", "float", "num", "bool", "list", "dict", "any"}


def _get_path(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None, "missing"
        cur = cur[part]
    return True, cur, ""


def _check_type(val, tname):
    """Return error string or '' if ok."""
    if tname == "any":
        return ""
    if tname == "num":
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            return f"expected num, got {type(val).__name__}"
        if not math.isfinite(val):
            return "non-finite number (NaN/Inf)"
        return ""
    checks = {
        "str": lambda v: isinstance(v, str),
        "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "float": lambda v: isinstance(v, float) and math.isfinite(v),
        "bool": lambda v: isinstance(v, bool),
        "list": lambda v: isinstance(v, list),
        "dict": lambda v: isinstance(v, dict),
    }
    if tname not in checks:
        return f"unknown type {tname!r}"
    return "" if checks[tname](val) else f"expected {tname}, got {type(val).__name__}"


def run_gate(doc, rules):
    """Validate doc against rules. Returns (ok, violations:list[str])."""
    violations = []
    for dotted, spec in rules.items():
        spec = str(spec)
        optional = spec.endswith("?")
        nonempty = spec[:-1].endswith("!") if optional else spec.endswith("!")
        tname = spec.rstrip("!?")
        if tname not in TYPES:
            return False, [f"FAIL-INPUT: bad rule {dotted!r}: unknown type {tname!r}"]
        if nonempty and optional:
            return False, [f"FAIL-INPUT: bad rule {dotted!r}: ! and ? are exclusive"]
        found, val, why = _get_path(doc, dotted)
        if why == "missing":
            if optional:
                continue
            violations.append(f"{dotted}: missing (required {tname})")
            continue
        if optional and val is None:
            continue
        err = _check_type(val, tname)
        if err:
            violations.append(f"{dotted}: {err}")
            continue
        if nonempty:
            if val is None or len(val) == 0:
                violations.append(f"{dotted}: empty but required non-empty ({tname}!)")
    return (len(violations) == 0), violations


def _write_receipt(out_path, receipt):
    d = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(receipt, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, out_path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description="json-gate: fail-loud JSON key/type validator")
    ap.add_argument("--file", help="JSON document to validate")
    ap.add_argument("--doc", help="JSON document as a literal string")
    ap.add_argument("--rules", help='rules JSON literal, e.g. \'{"verdict":"str!"}\'')
    ap.add_argument("--rules-file", help="path to rules JSON")
    ap.add_argument("--out", help="receipt path (JSON)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    try:
        if args.file:
            with open(args.file) as f:
                doc = json.load(f)
        elif args.doc is not None:
            doc = json.loads(args.doc)
        else:
            print("json-gate: need --file or --doc", file=sys.stderr)
            return RC_INPUT
        if args.rules:
            rules = json.loads(args.rules)
        elif args.rules_file:
            with open(args.rules_file) as f:
                rules = json.load(f)
        else:
            print("json-gate: need --rules or --rules-file", file=sys.stderr)
            return RC_INPUT
        if not isinstance(rules, dict) or not rules:
            print("json-gate: rules must be a non-empty object", file=sys.stderr)
            return RC_INPUT
    except (OSError, json.JSONDecodeError) as e:
        print(f"json-gate: FAIL-INPUT: {e}", file=sys.stderr)
        return RC_INPUT

    ok, violations = run_gate(doc, rules)
    receipt = {
        "tool": "json-gate",
        "verdict": "PASS" if ok else "FAIL",
        "n_rules": len(rules),
        "violations": violations,
        "doc_source": args.file or "<literal>",
    }
    if args.out:
        _write_receipt(args.out, receipt)
    print(json.dumps(receipt, indent=2))
    return RC_PASS if ok else RC_FAIL


def selftest():
    checks = []

    def pin(name, cond):
        checks.append((name, bool(cond)))

    # 1. positive control: good doc passes
    ok, v = run_gate({"verdict": "KEEP", "tau": 0.5, "gates": [True]},
                     {"verdict": "str!", "tau": "num", "gates": "list!"})
    pin("good-doc-PASS", ok and not v)
    # 2. RED: missing key fails
    ok, v = run_gate({"verdict": "KEEP"}, {"tau": "num"})
    pin("missing-key-FAIL", not ok and any("missing" in x for x in v))
    # 3. RED: wrong type fails
    ok, v = run_gate({"tau": "high"}, {"tau": "num"})
    pin("wrong-type-FAIL", not ok and any("expected num" in x for x in v))
    # 4. RED: NaN fails num even though it's a float
    ok, v = run_gate({"tau": float("nan")}, {"tau": "num"})
    pin("nan-FAIL", not ok and any("non-finite" in x for x in v))
    # 5. non-empty flag: empty string/list/dict fail with !
    ok, v = run_gate({"gates": []}, {"gates": "list!"})
    pin("empty-list-FAIL", not ok)
    ok2, _ = run_gate({"gates": [1]}, {"gates": "list"})
    pin("empty-allowed-without-bang", ok2)
    # 6. optional: missing ok with ?, None ok, wrong type still fails
    ok, _ = run_gate({}, {"note": "str?"})
    ok2, _ = run_gate({"note": None}, {"note": "str?"})
    ok3, v = run_gate({"note": 5}, {"note": "str?"})
    pin("optional-semantics", ok and ok2 and not ok3)
    # 7. nested dotted path
    ok, _ = run_gate({"a": {"b": {"c": "x"}}}, {"a.b.c": "str!"})
    ok2, v = run_gate({"a": {"b": 1}}, {"a.b.c": "str"})
    pin("dotted-nested", ok and not ok2 and any("missing" in x for x in v))
    # 8. bool is not int (Python gotcha pinned)
    ok, v = run_gate({"n": True}, {"n": "int"})
    pin("bool-not-int", not ok)
    # 9. bad rule -> FAIL-INPUT
    ok, v = run_gate({}, {"x": "complex"})
    pin("bad-rule-FAIL-INPUT", not ok and any("FAIL-INPUT" in x for x in v))
    # 10. ! and ? exclusive -> FAIL-INPUT
    ok, v = run_gate({}, {"x": "str!?"})
    pin("bang-quest-FAIL-INPUT", not ok and any("FAIL-INPUT" in x for x in v))

    fails = [n for n, c in checks if not c]
    print(json.dumps({"selftest": "PASS" if not fails else "FAIL",
                      "total": len(checks), "failed": fails}, indent=2))
    return RC_PASS if not fails else RC_FAIL


if __name__ == "__main__":
    sys.exit(main())
