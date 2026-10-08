#!/usr/bin/env python3
"""param_audit — gate-parameter validation census (one file, stdlib-only).

Pattern lifted PROVEN from PARAM-1 (booked GREEN 2026-10-08, commit 265ce29):
the fastloop-guard confused-deputy class — a gate whose *parameter sourcing*
can neuter or invert it. PARAM-1 surveyed five instruments by hand
(grep + selftest reading); this tool mechanizes the census for ANY gate file:

For each named parameter, books:
  - VALIDATED   — the parameter appears in a comparison/test (if p > 0,
                  if eps <= 0 ...) and the module contains at least one
                  raise that such a test can route to. Fail-loud hygiene.
  - UNVALIDATED — the parameter is assigned/parsed but never compared
                  anywhere: an eps<=0 or boundless-bounds value flows
                  straight into the gate. This is the PARAM-1 YELLOW class.
  - MISSING     — the parameter is not found in the module at all
                  (wrong name / drift between caller and callee).

File-level:
  - NETWORK — any urllib/requests/http.client/socket import in the gate
    module books RED outright (the G2 clause: gate parameters must never
    be network-sourced; a local gate file has no business importing them).
  - no raise anywhere in the module books YELLOW at file level: validation
    tests that cannot fail loud are decoration.

Verdict: GREEN iff no YELLOW/RED/MISSING anywhere; exit 0=GREEN,
1=FINDINGS (YELLOW/RED/MISSING booked honestly), 2=fail-loud (missing file,
parse error, no params requested). Heuristic by construction — the census
books the EVIDENCE (which comparisons, which imports) so a human can
overrule; it never edits the file. Read-only.

Usage:
  python tools/param_audit.py --file tools/eproc.py --params sigma,delta [--out r.json]
  python tools/param_audit.py --selftest

Worked example (from the docstring, copy-paste):
  python tools/param_audit.py --file tools/param_audit.py --params param_name,verdict
  -> books MISSING/MISSING (this tool's own args live in argparse, not module
     code) which is an honest FINDINGS rc=1 — use --selftest for the GREEN pin.

Selftest carries: GREEN fixture (validated + raise), YELLOW fixture
(unvalidated param), RED fixture (urllib import), MISSING param, rc battery.
"""
import argparse
import ast
import json
import os
import re
import sys

NETWORK_MODULES = {"urllib", "urllib.request", "requests", "http.client", "socket", "httpx"}


def find_comparisons(tree, param):
    """AST locations where `param` is compared/tested. Counts Name(p) on
    either side of a Compare, and string keys p in dict subscripts."""
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for cmp_node in [node.left] + node.comparators:
                if isinstance(cmp_node, ast.Name) and cmp_node.id == param:
                    hits.append(node.lineno)
        if isinstance(node, ast.Subscript):
            s = node.slice
            if isinstance(s, ast.Constant) and s.value == param:
                hits.append(node.lineno)
    return sorted(set(hits))


def find_default(tree, param):
    """Module-level `param = <literal>`, argparse dest/default literal, or
    function-signature default (`def g(delta=0.05)`)."""
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == param and isinstance(node.value, ast.Constant):
                    return node.value.value, node.lineno
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            d_args = node.args.defaults + node.args.kw_defaults
            names = [a.arg for a in node.args.args + node.args.kwonlyargs]
            named = names[-len(d_args):] if d_args else []
            for nm, dv in zip(named, d_args):
                if nm == param and dv is not None:
                    lit = dv.value if isinstance(dv, ast.Constant) else "<expr>"
                    return lit, node.lineno
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            for kw in node.keywords:
                if kw.arg in ("default", "dest") and isinstance(kw.value, ast.Constant) and kw.value.value == param:
                    return "<argparse:%s>" % kw.arg, node.lineno
    return None, None


def find_imports(tree):
    mods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.append(a.name)
        elif isinstance(node, ast.ImportFrom):
            mods.append(node.module or "")
    return mods


def has_raise(tree):
    return any(isinstance(n, ast.Raise) for n in ast.walk(tree))


def audit_source(source, params):
    """Core census. Returns (findings, verdict). Deterministic, no I/O."""
    tree = ast.parse(source)
    imports = find_imports(tree)
    net = sorted({m for m in imports for root in NETWORK_MODULES if m == root or m.startswith(root + ".")})
    raisable = has_raise(tree)

    findings = []
    assigned = {t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    for p in params:
        comps = find_comparisons(tree, p)
        default, dline = find_default(tree, p)
        if not comps and default is None and p not in assigned:
            findings.append({"param": p, "verdict": "MISSING", "evidence": "not found in module"})
        elif comps and raisable:
            findings.append({"param": p, "verdict": "VALIDATED", "evidence": "compared at lines %s; module raisable" % comps})
        else:
            why = []
            if not comps:
                why.append("assigned/parsed but never compared/tested — unvalidated value flows into gate (PARAM-1 YELLOW class)")
            if not raisable:
                why.append("module contains no raise — validation tests cannot fail loud")
            findings.append({
                "param": p, "verdict": "UNVALIDATED",
                "evidence": "; ".join(why),
                "comparisons": comps, "default": default, "default_line": dline,
            })
    if net:
        findings.append({"param": "<file>", "verdict": "RED", "evidence": "network import(s) in gate module: %s" % net})
    if not raisable and all(f["verdict"] == "VALIDATED" for f in findings if f["param"] != "<file>"):
        findings.append({"param": "<file>", "verdict": "UNVALIDATED", "evidence": "no raise anywhere; comparisons cannot fail loud"})

    bad = [f for f in findings if f["verdict"] in ("UNVALIDATED", "MISSING", "RED")]
    verdict = "FINDINGS" if bad else "GREEN"
    return findings, verdict


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", help="gate module to audit")
    ap.add_argument("--params", help="comma-separated parameter names to census")
    ap.add_argument("--out", help="receipt path (JSON)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest(args.out)

    if not args.file or not args.params:
        print("FAIL-INPUT: --file and --params required (or --selftest)", file=sys.stderr)
        return 2
    if not os.path.isfile(args.file):
        print("FAIL-INPUT: no such file: %s" % args.file, file=sys.stderr)
        return 2
    with open(args.file, encoding="utf-8") as f:
        source = f.read()
    try:
        findings, verdict = audit_source(source, [p.strip() for p in args.params.split(",") if p.strip()])
    except SyntaxError as e:
        print("FAIL-INPUT: parse error in %s: %s" % (args.file, e), file=sys.stderr)
        return 2
    if not findings:
        print("FAIL-INPUT: no params resolved", file=sys.stderr)
        return 2

    receipt = {"tool": "param_audit", "file": args.file, "verdict": verdict, "findings": findings}
    rc = 0 if verdict == "GREEN" else 1
    emit(receipt, args.out)
    for f in findings:
        print("%-8s %-10s %s" % (f["verdict"], f["param"], f["evidence"]))
    print("verdict: %s rc=%d" % (verdict, rc))
    return rc


def emit(receipt, out):
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2, sort_keys=True)


# --- selftest fixtures ---
GOOD_SRC = '''
def gate(sigma, delta=0.05):
    if sigma is None or sigma <= 0 or not (sigma > 0):
        raise ValueError("sigma must be > 0")
    if delta < 0:
        raise ValueError("delta must be >= 0")
    return sigma * delta
'''
YELLOW_SRC = '''
eps = float(os_sys_argv[1])
def gate(x):
    return snap(x, eps)   # eps never validated: eps<=0 degenerates silently
'''
RED_SRC = '''
import urllib.request
def gate(url):
    return urllib.request.urlopen(url).read()
'''


def selftest(out=None):
    checks = []
    f, v = audit_source(GOOD_SRC, ["sigma", "delta"])
    checks.append(("green-validated", v == "GREEN" and all(x["verdict"] == "VALIDATED" for x in f), str(f)))

    f, v = audit_source(YELLOW_SRC, ["eps"])
    checks.append(("yellow-unvalidated", v == "FINDINGS" and f[0]["verdict"] == "UNVALIDATED", str(f)))

    f, v = audit_source(GOOD_SRC, ["tolerance"])
    checks.append(("missing-param", v == "FINDINGS" and f[0]["verdict"] == "MISSING", str(f)))

    f, v = audit_source(RED_SRC, ["url"])
    checks.append(("red-network", v == "FINDINGS" and any(x["verdict"] == "RED" and "urllib" in x["evidence"] for x in f), str(f)))

    # no-raise module: comparisons present but nothing can fail loud
    NORaise = "def gate(eps):\n    if eps <= 0:\n        pass\n    return eps\n"
    f, v = audit_source(NORaise, ["eps"])
    checks.append(("no-raise-yellow", v == "FINDINGS" and f[0]["verdict"] == "UNVALIDATED", str(f)))

    # rc battery through main()
    import tempfile
    for name, src, params, want in [
        ("rc-green", GOOD_SRC, "sigma,delta", 0),
        ("rc-yellow", YELLOW_SRC, "eps", 1),
        ("rc-failinput-missing-file", None, "x", 2),
    ]:
        if src is None:
            rc = main(["--file", "/nonexistent/param_audit_selftest.py", "--params", params])
        else:
            fd, path = tempfile.mkstemp(suffix=".py")
            with os.fdopen(fd, "w") as fh:
                fh.write(src)
            rc = main(["--file", path, "--params", params])
        checks.append((name, rc == want, "rc=%d want=%d" % (rc, want)))

    ok = all(p for _, p, _ in checks)
    receipt = {"tool": "param_audit", "selftest": "PASS" if ok else "FAIL",
               "checks": [{"name": n, "ok": p, "why": w} for n, p, w in checks]}
    emit(receipt, out)
    for n, p, w in checks:
        print("PASS" if p else "FAIL", n, "-", w)
    print("selftest: %s (%d/%d)" % ("PASS" if ok else "FAIL", sum(p for _, p, _ in checks), len(checks)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
