#!/usr/bin/env python3
"""param-liveness — unwired-parameter AST gate for scored/loss/metric functions.

Pattern lifted PROVEN from SCOUT-98 (slackwater-cognition, booked 2026-10-10,
commit d1a5d7a): the loop's entire training signal `score_quality(game_state)`
took `game_state` in its signature and AST-verified NEVER read it — keyword-soup
input reached mean 1.000 vs 0.562 for substantive input. "The loss that never
watched the game." A parameter that is accepted but never read means the metric
is blind to that input BY CONSTRUCTION, no experiment needed to show it.

For every --func in a module (or every top-level function with --all), walks the
AST and books each parameter as:
  READ      — name is loaded somewhere in the body (or is *args/**kwargs,
              or has a deliberate `_`-prefix = documented dead)
  UNWIRED   — never read: RED. The metric cannot see this input.
  PASSTHRU  — only passed through verbatim to one callee call (the slackwater
              line-140 shape: `return other_fn(x, game_state)`) — YELLOW,
              reported with the call named so a human can judge the chain.
Fail-loud rc=2 on bad module/function/args; exit 0=CLEAN (all READ), rc=1 = any
UNWIRED (PASSTHRU alone books CLEAN with warnings). `--selftest` carries the
slackwater fixture (takes game_state, reads only the other arg) as its RED pin.

Stdlib-only, read-only, no network. Keys/secrets never touched.

Usage:
  python tools/param_liveness.py --file journal.py --func score_quality
  python tools/param_liveness.py --file tools/eproc.py --func kill_gate --out r.json
  python tools/param_liveness.py --file F.py --all [--allow fn:param,fn:param]
  python tools/param_liveness.py --selftest

Worked example (docstring self-test, also run by --selftest):

    def score_quality(thought_text, game_state):        # game_state unwired
        hits = sum(w in thought_text for w in ("good", "great"))
        return min(1.0, hits / 2)

    -> rc=1, game_state booked UNWIRED.

Library API:
    from param_liveness import audit_function
    rows = audit_function(open("journal.py").read(), "score_quality")
    # rows: list of {param, status, detail}
"""
import argparse
import ast
import json
import sys

USAGE = __doc__


def _collect_reads(fn_node):
    """Names Loaded in the function body, EXCLUDING its own name bound/used."""
    reads = set()
    passthru = {}  # param -> first call expression that merely passes it on
    params = {a.arg for a in fn_node.args.args + fn_node.args.kwonlyargs}
    if fn_node.args.vararg:
        params.add(fn_node.args.vararg.arg)
    if fn_node.args.kwarg:
        params.add(fn_node.args.kwarg.arg)

    # Walk body (skip the args themselves), tracking Load vs Store context.
    for node in ast.walk(ast.Module(body=fn_node.body, type_ignores=[])):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            reads.add(node.id)
        # nested function defs: their reads count too (closure use is a read)
    return params, reads, passthru


def _passthru_uses(fn_node, params):
    """Params used ONLY as a plain argument passed through in exactly one call."""
    only = {p: [] for p in params}
    all_uses = {p: 0 for p in params}

    class V(ast.NodeVisitor):
        def visit_Call(self, node):
            for arg in node.args:
                if isinstance(arg, ast.Name) and arg.id in params and isinstance(arg.ctx, ast.Load):
                    all_uses[arg.id] += 1
                    only[arg.id].append(_call_name(node))
            for kw in node.keywords:
                if isinstance(kw.value, ast.Name) and kw.value.id in params:
                    all_uses[kw.value.id] += 1
                    only[kw.value.id].append(_call_name(node))
            self.generic_visit(node)

    for stmt in fn_node.body:
        V().visit(stmt)
    return {p: calls for p, c in only.items()
            for calls in [c] if all_uses[p] > 0 and len(c) == all_uses[p]}


def _call_name(node):
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return "<expr>"


def audit_function(src, func_name):
    """Audit one function's parameters. Returns list of rows; raises SystemExit(2)
    on missing function / parse failure."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        raise SystemExit(json.dumps({"verdict": "FAIL-INPUT", "rc": 2,
                                     "why": f"syntax error: {e}"}))
    fn = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            fn = node
            break
    if fn is None:
        raise SystemExit(json.dumps({"verdict": "FAIL-INPUT", "rc": 2,
                                     "why": f"function {func_name!r} not found at module top level"}))

    params, reads, _ = _collect_reads(fn)
    passthru = _passthru_uses(fn, params)
    rows = []
    for a in fn_node_args(fn):
        name = a.arg
        if name in ("self", "cls") or name.startswith("_"):
            rows.append({"param": name, "status": "READ",
                         "detail": "conventional/underscore-documented dead param"})
        elif name in reads and name not in passthru:
            rows.append({"param": name, "status": "READ", "detail": "loaded in body"})
        elif name in passthru:
            rows.append({"param": name, "status": "PASSTHRU",
                         "detail": "passed through verbatim to: " + ", ".join(sorted(set(passthru[name])))})
        else:
            rows.append({"param": name, "status": "UNWIRED",
                         "detail": "never read anywhere in the body"})
    return rows


def fn_node_args(fn):  # helper keeps audit_function readable
    return (fn.args.args + fn.args.kwonlyargs
            + ([fn.args.vararg] if fn.args.vararg else [])
            + ([fn.args.kwarg] if fn.args.kwarg else []))


SLACKWATER_FIXTURE = '''
def score_quality(thought_text, game_state):
    """Slackwater-shaped: signature takes game_state, body reads only text."""
    hits = sum(w in thought_text for w in ("good", "great", "insight"))
    return min(1.0, hits / 3)
'''

WIRE_FIXTURE = '''
def score_quality(thought_text, game_state):
    hits = sum(w in thought_text for w in ("good", "great"))
    n = len(game_state.get("moves", []))
    return min(1.0, hits / 2 + n * 0.01)
'''

PASSTHRU_FIXTURE = '''
def score_quality(thought_text, game_state):
    return base_score(thought_text, game_state)
'''


def run_selftest():
    checks = []

    def book(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    r = audit_function(SLACKWATER_FIXTURE, "score_quality")
    unwired = [x["param"] for x in r if x["status"] == "UNWIRED"]
    book("slackwater-fixture-RED", unwired == ["game_state"], f"unwired={unwired}")

    r = audit_function(WIRE_FIXTURE, "score_quality")
    unwired = [x["param"] for x in r if x["status"] == "UNWIRED"]
    book("wired-fixture-CLEAN", unwired == [], f"unwired={unwired}")

    r = audit_function(PASSTHRU_FIXTURE, "score_quality")
    pt = {x["param"]: x["detail"] for x in r if x["status"] == "PASSTHRU"}
    unwired = [x["param"] for x in r if x["status"] == "UNWIRED"]
    book("passthru-named-not-silent",
         set(pt) == {"thought_text", "game_state"}
         and all("base_score" in d for d in pt.values()) and unwired == [], f"rows={r}")

    # underscore prefix = documented dead, books READ not silent UNWIRED
    r = audit_function("def f(_dead, live):\n    return live\n", "f")
    st = {x["param"]: x["status"] for x in r}
    book("underscore-documented", st.get("_dead") == "READ" and st.get("live") == "READ", f"{st}")

    for name, src, fn in [("missing-fn rc2", "def a():\n    pass\n", "nope"),
                          ("bad-src rc2", "def f(:\n", "f")]:
        try:
            audit_function(src, fn)
            book(name, False, "no SystemExit raised")
        except SystemExit as e:
            try:
                payload = json.loads(str(e))
                book(name, payload.get("rc") == 2, str(payload))
            except Exception:
                book(name, False, f"non-JSON exit: {e}")

    failed = [c for c in checks if not c["ok"]]
    return {"verdict": "PASS" if not failed else "FAIL", "rc": 0 if not failed else 1,
            "checks": checks, "tool": "param-liveness", "date": "2026-10-10"}


def main(argv=None):
    ap = argparse.ArgumentParser(description="unwired-parameter AST gate (SCOUT-98 pattern)")
    ap.add_argument("--file", help="python module to audit")
    ap.add_argument("--func", help="function name(s), comma-separated")
    ap.add_argument("--all", action="store_true", help="audit every top-level function")
    ap.add_argument("--allow", default="", help="comma list fn:param to allow as documented-dead")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        rep = run_selftest()
        print(json.dumps(rep, indent=2))
        if args.out:
            with open(args.out, "w") as f:
                json.dump(rep, f, indent=2)
        sys.exit(rep["rc"])

    if not args.file or (not args.func and not args.all):
        print(json.dumps({"verdict": "FAIL-INPUT", "rc": 2,
                          "why": "need --file and --func (or --all), or --selftest"}))
        sys.exit(2)
    try:
        src = open(args.file).read()
    except OSError as e:
        print(json.dumps({"verdict": "FAIL-INPUT", "rc": 2, "why": f"cannot read {args.file}: {e}"}))
        sys.exit(2)

    allows = set(x.strip() for x in args.allow.split(",") if x.strip())
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        print(json.dumps({"verdict": "FAIL-INPUT", "rc": 2, "why": f"syntax error: {e}"}))
        sys.exit(2)

    names = ([n.name for n in tree.body
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
             if args.all else [x.strip() for x in args.func.split(",") if x.strip()])

    report = {"tool": "param-liveness", "file": args.file, "date": "2026-10-10",
              "functions": {}, "verdict": "CLEAN", "rc": 0, "why": ""}
    reds = []
    for name in names:
        try:
            rows = audit_function(src, name)
        except SystemExit as e:
            payload = json.loads(str(e))
            payload["function"] = name
            print(json.dumps(payload))
            sys.exit(payload["rc"])
        for row in rows:
            if f"{name}:{row['param']}" in allows:
                row["status"] = "ALLOWED"
        report["functions"][name] = rows
        unwired = [x["param"] for x in rows if x["status"] == "UNWIRED"]
        if unwired:
            reds.append((name, unwired))
    if reds:
        report["verdict"] = "RED"
        report["rc"] = 1
        report["why"] = "; ".join(f"{fn} never reads: {', '.join(ps)}" for fn, ps in reds)
    print(json.dumps(report, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(report, f, indent=2)
    sys.exit(report["rc"])


if __name__ == "__main__":
    main()
