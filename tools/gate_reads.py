#!/usr/bin/env python3
"""gate-reads — AST census of what a gate function DECIDES on vs merely RECORDS.

Pattern lifted PROVEN from QO6n (experiments/qo6n_noise_gap.py, booked GREEN
2026-10-06): the QO6 kill-evidence gate was suspected of "consuming" E_max
(a depth-like magnitude) when its verdict is actually pure duration (stop_t).
The audit proved duration-purity by (a) AST-extracting the string constants
the gate function reads, and (b) grep-classifying every repo occurrence of the
suspicious field into dict-key construction / producer / diagnostic recording
vs DECISION reads (compared, asserted, branched on). This tool mechanizes it.

Usage:
  python tools/gate_reads.py --file tools/eproc.py --func kill_gate \
      [--suspicious E_max --root .] [--out r.json] | --selftest

Exit codes: 0 = census clean (no suspicious field is a decision read),
1 = RED (a suspicious field IS decided on, or the reads differ from --expect),
2 = fail-loud (missing file/function, parse error).

Stdlib-only. Read-only (grep census, never mutates). List-form subprocess only.
"""
import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile


# ---------- library ----------

def _func_node(src, name):
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name:
            return n
    raise ValueError(f"function {name!r} not found")


def _walk_fields(node):
    """Yield (fieldname, ast_node, kind) for attribute/subscript field reads."""
    for n in ast.walk(node):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
            yield (n.attr, n, "attr")
        elif isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) \
                and isinstance(n.slice.value, str):
            yield (n.slice.value, n, "key")


def _in_decision_ctx(field_node, fn):
    """True if field_node sits inside a decision context: comparison, boolop,
    if/while test, assert, or ternary. Returning a field value as part of a
    receipt dict is RECORDING, not deciding (QO6n lesson — selftest-pinned)."""
    class V(ast.NodeVisitor):
        def __init__(self):
            self.hits = []
        def _check(self, node, exprs):
            for e in exprs:
                if any(n is field_node for n in ast.walk(e)):
                    self.hits.append(type(node).__name__)
        def visit_Compare(self, node):
            self._check(node, [node.left] + node.comparators); self.generic_visit(node)
        def visit_BoolOp(self, node):
            self._check(node, node.values); self.generic_visit(node)
        def visit_If(self, node):
            self._check(node, [node.test]); self.generic_visit(node)
        def visit_While(self, node):
            self._check(node, [node.test]); self.generic_visit(node)
        def visit_Assert(self, node):
            self._check(node, [node.test]); self.generic_visit(node)
        def visit_IfExp(self, node):
            self._check(node, [node.test]); self.generic_visit(node)
    v = V(); v.visit(fn)
    return bool(v.hits)


def census_function(src, func_name):
    """Return {field: [ctx kinds]} of every field read inside func."""
    fn = _func_node(src, func_name)
    reads = {}
    for field, node, kind in _walk_fields(fn):
        ctx = "decision" if _in_decision_ctx(node, fn) else "recorded"
        reads.setdefault(field, []).append(ctx)
    return {k: sorted(set(v)) for k, v in sorted(reads.items())}


def grep_census(pattern, root, excludes=()):
    """Census of `pattern` lines in one file (or dir tree if root is a dir)."""
    if os.path.isfile(root):
        cmd = ["grep", "-n", "-e", pattern, root]
    else:
        cmd = ["grep", "-rn", "-e", pattern, "--include=*.py", "--include=*.mjs", root]
    g = subprocess.run(cmd, capture_output=True, text=True, cwd=None)
    return [l for l in g.stdout.splitlines()
            if not any(f"/{e}/" in l for e in excludes)]


def classify_lines(lines, field):
    """Split raw grep lines into decision candidates vs recording lines
    (dict-key construction / producer / receipt assignment are recording)."""
    decision, recorded = [], []
    for l in lines:
        cp = l.split("#", 1)[0]  # strip comment
        if f'"{field}":' in cp or f"'{field}':" in cp or f'"{field}" :' in cp:
            recorded.append((l, "dict-key construction"))
        elif f".{field}" in cp and ("=" in cp and not any(op in cp for op in
                ("==", "!=", "<=", ">=", "< ", "> "))):
            recorded.append((l, "attribute write/record"))
        elif any(op in cp for op in ("==", "!=", "<=", ">=")) or re.search(r"[<>]", cp):
            decision.append(l)
        else:
            recorded.append((l, "unclassified read"))
    return decision, recorded


def run_audit(path, func, suspicious, root, expect_decision=None):
    src = open(path).read()
    reads = census_function(src, func)
    R = {"file": path, "func": func, "reads": reads, "suspicious": suspicious}
    red = []
    for f in suspicious:
        dec, rec = classify_lines(grep_census(f, path), f)
        R[f"{f}_decision_lines"] = dec
        R[f"{f}_recorded"] = [l for l, _ in rec]
        # a field with 'decision' ctx inside the gate OR repo-wide comparison = RED
        if "decision" in reads.get(f, []) or dec:
            red.append(f)
    R["RED_fields"] = red
    if expect_decision is not None:
        got = sorted(f for f, ctxs in reads.items() if "decision" in ctxs)
        if got != sorted(expect_decision):
            red.append(f"__expect_mismatch: decision-reads {got} != expected {sorted(expect_decision)}")
            R["RED_fields"] = red
    R["VERDICT"] = "RED" if red else "GREEN"
    return R


# ---------- selftest ----------

FIXTURE_CLEAN = '''
def gate(d):
    verdict = d["verdict"] == "KILL"          # decision read
    receipt = {"E_max": d["E_max"]}           # recorded only
    if len(receipt) < 1:
        raise ValueError("empty")
    return {"verdict": verdict, "E_max": receipt["E_max"]}
'''
FIXTURE_RED = '''
def gate(d):
    verdict = d["verdict"] == "KILL" or d["E_max"] < 5   # E_max DECIDED on — RED
    return {"verdict": verdict}
'''


def selftest():
    checks = []
    # 1. clean fixture: E_max recorded-only, verdict decided
    R = run_audit.__wrapped__ if False else None
    reads = census_function(FIXTURE_CLEAN, "gate")
    checks.append(("clean: E_max recorded-only", reads.get("E_max") == ["recorded"], reads.get("E_max")))
    checks.append(("clean: verdict decision-read", reads.get("verdict") == ["decision"], reads.get("verdict")))
    # 2. clean audit end-to-end GREEN, with expect pin
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(FIXTURE_CLEAN); p = f.name
    R = run_audit(p, "gate", ["E_max"], root=".", expect_decision=["verdict"])
    checks.append(("clean: audit GREEN", R["VERDICT"] == "GREEN", R["RED_fields"]))
    # 3. RED fixture: E_max compared -> caught
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(FIXTURE_RED); p2 = f.name
    R2 = run_audit(p2, "gate", ["E_max"], root=".")
    checks.append(("red: E_max compared -> RED", R2["VERDICT"] == "RED", R2["RED_fields"]))
    # 4. expect-pin mismatch caught live
    R3 = run_audit(p2, "gate", [], root=".", expect_decision=["verdict"])
    ok3 = R3["VERDICT"] == "RED" and any("expect_mismatch" in x for x in R3["RED_fields"])
    checks.append(("expect-pin mismatch -> RED", ok3, R3["RED_fields"]))
    # 5. fail-loud on missing function
    try:
        census_function("def other():\n    pass\n", "gate")
        checks.append(("missing func raises", False, "no raise"))
    except ValueError:
        checks.append(("missing func raises", True, "ValueError"))
    for name, ok, info in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {info if not ok else ''}")
    if not all(ok for _, ok, _ in checks):
        sys.exit(1)
    print("selftest: ALL PASS")


run_audit.__wrapped__ = None  # noqa (kept minimal)


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                 epilog="Exit 0 GREEN / 1 RED / 2 fail-loud.")
    ap.add_argument("--file", help="python file holding the gate function")
    ap.add_argument("--func", help="gate function name")
    ap.add_argument("--suspicious", default="", help="comma-separated fields that must never be decision-reads")
    ap.add_argument("--expect", default="", help="comma-separated fields expected to be decision-reads (pin; mismatch = RED)")
    ap.add_argument("--root", default=".", help="repo root for grep census")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest(); return
    if not (a.file and a.func):
        ap.error("--file and --func required (or --selftest)")
    rc = 2
    try:
        expect = [x for x in a.expect.split(",") if x] or None
        R = run_audit(a.file, a.func, [x for x in a.suspicious.split(",") if x],
                      root=a.root, expect_decision=expect)
        rc = 1 if R["VERDICT"] == "RED" else 0
    except (OSError, ValueError, SyntaxError) as e:
        R = {"VERDICT": "FAIL-LOUD", "error": repr(e)}
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w") as f:
            json.dump(R, f, indent=1)
    print(json.dumps({k: R[k] for k in ("VERDICT", "RED_fields", "error") if k in R}))
    sys.exit(rc)


if __name__ == "__main__":
    main()
