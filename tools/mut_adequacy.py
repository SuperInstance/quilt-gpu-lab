#!/usr/bin/env python3
"""mut_adequacy.py -- mutation-scored test-suite adequacy for any module.

Pattern lifted from SPOOL entry W15b (booked 2026-10-10) + the mutation-testing
literature it mines (ESEM 2026 Test-Aware Mutant Generation; Meta LLM mutation
testing): test adequacy is measured by MUTATION KILL RATE, not coverage. The
fleet-murmur-worker receipt is the zero-kill-rate case -- a suite 27/27 GREEN
over an INVERTED gate because the tests transcribed the implementation. A green
suite over a wrong gate is exactly a suite with zero kill power. This tool is
that measurement.

Contract: generate ALL single-point AST mutants of a target module (one
semantic flip per mutant: comparison-op swap, and/or swap, True/False swap,
not-removal, integer off-by-one), run a test command (list-form subprocess,
no shell) against each mutant on a COPY -- the original file is never
touched -- and classify each mutant KILLED (command exits nonzero) or
SURVIVED (command exits 0). Gate:
  G1 kill rate >= --bar (default 0.80)
  G2 at least --min-mutants mutants generated (a mutant-free module is
     untestable by this oracle, never a silent PASS)
ADEQUATE iff both clauses; otherwise INADEQUATE. Survivors are named (line +
flip) so each can be pinned with a new test or justified as equivalent -- an
unjustified survivor is the murmur class in miniature.

Stdlib-only, seeded/deterministic (mutations in stable AST order), fail-loud
rc=2 (missing file, syntax error, zero mutants, bad command), exit 0=ADEQUATE
/ 1=INADEQUATE. JSON receipt either way. Read-only on the target; mutants
live in a throwaway tempdir keyed by module basename so imports resolve.

Worked example (docstring self-check):
  python tools/mut_adequacy.py --module my_gate.py \
      --test-cmd python3 --test-args -m,pytest,tests/test_my_gate.py
    -> every mutant of my_gate.py is copied to <tmpdir>/my_gate.py and the
       test command runs with PYTHONPATH=<tmpdir>:<existing> (copy shadows
       the original); kill rate gated at 0.80.

  python tools/mut_adequacy.py --selftest
"""
import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TOOL = "mut_adequacy"

# Comparison-op swaps: each entry (from_op, to_op, name)
CMP_SWAPS = [
    (ast.Gt, ast.LtE, "gt->lte"),
    (ast.Lt, ast.GtE, "lt->gte"),
    (ast.GtE, ast.Lt, "gte->lt"),
    (ast.LtE, ast.Gt, "lte->gt"),
    (ast.Eq, ast.NotEq, "eq->noteq"),
    (ast.NotEq, ast.Eq, "noteq->eq"),
    (ast.Is, ast.IsNot, "is->isnot"),
    (ast.IsNot, ast.Is, "isnot->is"),
    (ast.In, ast.NotIn, "in->notin"),
    (ast.NotIn, ast.In, "notin->in"),
]


def fail_input(msg):
    print(json.dumps({"tool": TOOL, "verdict": "FAIL-INPUT", "why": msg}))
    sys.exit(2)


class _MutantCollector(ast.NodeVisitor):
    """Yield (description, mutator) for every single-point flip in the tree."""

    def __init__(self):
        self.mutants = []  # (desc, apply_fn) where apply_fn(node) mutates in place

    def visit_Compare(self, node):
        self.generic_visit(node)
        for i, op in enumerate(node.ops):
            for src, dst, name in CMP_SWAPS:
                if isinstance(op, src):
                    self.mutants.append((f"L{node.lineno} cmp {name}",
                                         self._swap_op(node, i, dst)))

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        new_type = ast.Or if isinstance(node.op, ast.And) else ast.And
        name = "and->or" if isinstance(node.op, ast.And) else "or->and"
        self.mutants.append((f"L{node.lineno} boolop {name}",
                             self._swap_boolop(node, new_type)))

    def visit_Constant(self, node):
        self.generic_visit(node)
        if node.value is True:
            self.mutants.append((f"L{node.lineno} const True->False",
                                 self._swap_const(node, False)))
        elif node.value is False:
            self.mutants.append((f"L{node.lineno} const False->True",
                                 self._swap_const(node, True)))
        elif isinstance(node.value, int) and not isinstance(node.value, bool):
            self.mutants.append((f"L{node.lineno} off-by-one {node.value}->{node.value + 1}",
                                 self._swap_const(node, node.value + 1)))

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Not):
            self.mutants.append((f"L{node.lineno} not-removal",
                                 self._drop_not(node)))

    # -- in-place mutators (capture via default args) ----------------------
    def _swap_op(self, node, i, dst):
        def apply():
            node.ops[i] = dst()
        return apply

    def _swap_boolop(self, node, new_type):
        def apply():
            node.op = new_type()
        return apply

    def _swap_const(self, node, new_value):
        def apply():
            node.value = new_value
        return apply

    def _drop_not(self, node):
        def apply():
            raise _DropNot(node)
        return apply


class _DropNot(Exception):
    """Signal to replace `not X` with X."""

    def __init__(self, node):
        self.node = node


def generate_mutants(source):
    """Parse source; return list of (desc, mutated_source). Deterministic order."""
    tree = ast.parse(source)
    collector = _MutantCollector()
    collector.visit(tree)
    out = []
    for desc, apply in collector.mutants:
        tree2 = ast.parse(source)  # fresh tree per mutant
        # re-locate the same mutation point in the fresh tree (stable order)
        c2 = _MutantCollector()
        c2.visit(tree2)
        idx = [d for d, _ in collector.mutants].index(desc)
        desc2, apply2 = c2.mutants[idx]
        assert desc2 == desc
        try:
            apply2()
        except _DropNot as e:
            # e.node belongs to tree2: replace `not X` with X in place.
            class _T(ast.NodeTransformer):
                def visit_UnaryOp(self, n):
                    self.generic_visit(n)
                    return n.operand if n is e.node else n
            _T().visit(tree2)
        mutated = ast.unparse(tree2)
        out.append((desc, mutated))
    return out


def run_cmd(cmd, cwd, env, timeout):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           cwd=cwd, env=env, timeout=timeout)
        return p.returncode, p.stdout[-2000:], p.stderr[-2000:]
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, "", f"{type(e).__name__}: {e}"


def run_suite_against(module_path, test_cmd, test_args, mutant_source, timeout):
    """Copy the mutant to a tempdir named after the module; run tests with the
    tempdir first on PYTHONPATH. If the module lives in a package (parent dir
    has __init__.py), mirror that layout (tmp/<pkg>/<name>.py) so package
    imports (e.g. tools.verdict_gate) shadow the original too.
    Returns (rc, stderr_tail)."""
    mod_path = Path(module_path).resolve()
    with tempfile.TemporaryDirectory(prefix="mut_adequacy_") as tmp:
        t = Path(tmp)
        shadow = t / mod_path.name
        shadow.write_text(mutant_source, encoding="utf-8")
        if (mod_path.parent / "__init__.py").is_file():
            pkg = t / mod_path.parent.name
            pkg.mkdir()
            pkg.joinpath("__init__.py").write_text(
                (mod_path.parent / "__init__.py").read_text(encoding="utf-8"))
            pkg.joinpath(mod_path.name).write_text(mutant_source, encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONPATH"] = tmp + os.pathsep + env.get("PYTHONPATH", "")
        # Robust shadow: test files commonly sys.path.insert(0, repo_root)
        # AFTER sitecustomize runs, so sys.path order cannot win. Install a
        # meta-path hook (runs before path finders regardless of later
        # sys.path edits) that redirects any import resolving to the ORIGINAL
        # file to the mutant copy.
        t.joinpath("sitecustomize.py").write_text(
            "import sys\n"
            "import importlib.util\n"
            "from importlib.machinery import PathFinder\n"
            f"_orig = {str(mod_path)!r}\n"
            f"_shadow = {str(shadow)!r}\n"
            "class _Redir:\n"
            "    def find_spec(self, name, path=None, target=None):\n"
            "        spec = PathFinder.find_spec(name, path, target)\n"
            "        if spec and getattr(spec, 'origin', None) == _orig:\n"
            "            # swap the LOADER, not just origin: the original\n"
            "            # SourceFileLoader captured the original file path.\n"
            "            return importlib.util.spec_from_file_location(name, _shadow)\n"
            "        return spec\n"
            "sys.meta_path.insert(0, _Redir())\n", encoding="utf-8")
        return run_cmd([*test_cmd, *test_args], cwd=os.getcwd(), env=env,
                       timeout=timeout)


def run_adequacy(module_path, test_cmd, test_args, bar, min_mutants, timeout):
    src_path = Path(module_path)
    if not src_path.is_file():
        fail_input(f"module not found: {module_path}")
    source = src_path.read_text(encoding="utf-8")
    try:
        mutants = generate_mutants(source)
    except SyntaxError as e:
        fail_input(f"target module does not parse: {e}")

    if len(mutants) < min_mutants:
        fail_input(f"only {len(mutants)} mutants generated (< min {min_mutants}); "
                   "a mutant-free module is untestable by this oracle")

    # Positive control: the suite MUST pass on the unmutated module. A
    # baseline failure means every "kill" below is just the broken harness.
    rc0, _o, err0 = run_suite_against(module_path, test_cmd, test_args,
                                      source, timeout)
    if rc0 != 0:
        fail_input(f"suite does not pass on the UNMUTATED module (rc={rc0}); "
                   f"fix the harness first. stderr: {err0}")

    results = []
    killed = 0
    for desc, mut_src in mutants:
        rc, _out, err = run_suite_against(module_path, test_cmd, test_args,
                                          mut_src, timeout)
        is_killed = (rc is None) or (rc != 0)  # harness death IS a kill
        killed += is_killed
        results.append({"mutant": desc, "killed": is_killed,
                        "rc": rc, "stderr_tail": err})

    kill_rate = killed / len(mutants)
    survivors = [r["mutant"] for r in results if not r["killed"]]
    g1 = kill_rate >= bar
    adequate = g1
    verdict = "ADEQUATE" if adequate else "INADEQUATE"
    return {
        "tool": TOOL,
        "module": str(module_path),
        "test_cmd": [*test_cmd, *test_args],
        "bar": bar,
        "min_mutants": min_mutants,
        "n_mutants": len(mutants),
        "killed": killed,
        "kill_rate": round(kill_rate, 4),
        "g1_kill_rate_ge_bar": g1,
        "survivors": survivors,
        "results": results,
        "verdict": verdict,
    }, (0 if adequate else 1)


def selftest():
    """Positive + RED control battery. Returns (receipt, rc)."""
    checks = []

    # Fixture: module with a comparison, a boolop, a constant, a not.
    fixture = ("def ok(a, b):\n"
               "    return a > b and not (a == 0)\n")
    # Suite: a transcription-grade suite that asserts only the one behavior
    # it transcribed. Kills the cmp/eq/not flips it exercises, but is blind
    # to the boolop and constant mutants it never probes.
    suite = ("import sys, my_fix\n"
             "sys.exit(0 if my_fix.ok(2, 1) is True else 1)\n")
    # Thorough suite: boundary + degenerate inputs (kills everything except
    # the genuinely equivalent off-by-one mutant of this fixture).

    with tempfile.TemporaryDirectory() as tmp:
        mod = Path(tmp) / "my_fix.py"
        mod.write_text(fixture)
        mutants = generate_mutants(fixture)
        descs = [d for d, _ in mutants]
        checks.append(("generates >=5 mutants", len(mutants) >= 5))
        checks.append(("comparison swap present",
                       any("cmp gt->lte" in d for d in descs)))
        checks.append(("not-removal present",
                       any("not-removal" in d for d in descs)))

        # Pin: mutated source differs from original for every mutant.
        checks.append(("every mutant changes source",
                       all(m != fixture for _, m in mutants)))

        # Kill battery: transcription suite kills the flips it exercises...
        results = []
        for desc, mut_src in mutants:
            rc, _o, _e = run_suite_against(
                str(mod), [sys.executable], ["-c", suite], mut_src, 30)
            results.append((desc, rc))
        killed_cmp = sum(1 for d, rc in results if ("cmp" in d or "not" in d) and rc != 0)
        survived_boolop = sum(1 for d, rc in results if "boolop" in d and rc == 0)
        survived_offby = sum(1 for d, rc in results if "off-by-one" in d and rc == 0)
        checks.append(("strict suite kills cmp+not flips", killed_cmp >= 3))
        checks.append(("transcription-suite spares boolop", survived_boolop >= 1))
        checks.append(("transcription-suite spares off-by-one", survived_offby >= 1))

        # Full run: thorough suite is ADEQUATE at the 0.80 bar (only the
        # equivalent off-by-one mutant survives).
        thorough = ("import sys, my_fix\n"
                    "ok = (my_fix.ok(2, 1) is True and my_fix.ok(1, 2) is False\n"
                    "      and my_fix.ok(0, 1) is False and my_fix.ok(2, 2) is False)\n"
                    "sys.exit(0 if ok else 1)\n")
        receipt, rc = run_adequacy(str(mod), [sys.executable], ["-c", thorough],
                                   bar=0.8, min_mutants=3, timeout=30)
        checks.append(("thorough suite ADEQUATE", receipt["verdict"] == "ADEQUATE" and rc == 0))

        # RED control: transcription suite is INADEQUATE (spares boolop and
        # off-by-one survivors; 3/5 = 0.6 < 0.8).
        receipt2, rc2 = run_adequacy(str(mod), [sys.executable], ["-c", suite],
                                     bar=0.8, min_mutants=3, timeout=30)
        checks.append(("strict suite INADEQUATE", receipt2["verdict"] == "INADEQUATE" and rc2 == 1))
        checks.append(("survivors named", len(receipt2["survivors"]) >= 2))

        # Fail-loud: missing module.
        try:
            run_adequacy(str(Path(tmp) / "nope.py"), [sys.executable], ["-c", "pass"],
                         0.8, 1, 30)
            checks.append(("missing module fail-loud", False))
        except SystemExit as e:
            checks.append(("missing module fail-loud", e.code == 2))

    receipt = {"tool": TOOL, "selftest": checks,
               "verdict": "PASS" if all(ok for _, ok in checks) else "FAIL"}
    return receipt, (0 if receipt["verdict"] == "PASS" else 1)


def main():
    ap = argparse.ArgumentParser(
        prog=TOOL,
        description="Mutation-scored test-suite adequacy (kill rate, not coverage).")
    ap.add_argument("--module", help="target module .py file to mutate (never modified)")
    ap.add_argument("--test-cmd", nargs="+", help="test command, list-form")
    ap.add_argument("--test-args", default="",
                    help="comma-separated args appended to --test-cmd")
    ap.add_argument("--bar", type=float, default=0.80, help="kill-rate bar (default 0.80)")
    ap.add_argument("--min-mutants", type=int, default=3,
                    help="minimum mutant count to run at all (default 3)")
    ap.add_argument("--timeout", type=float, default=120.0,
                    help="per-mutant test timeout seconds (default 120)")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        receipt, rc = selftest()
        print(json.dumps(receipt, indent=2))
        if args.out:
            Path(args.out).write_text(json.dumps(receipt, indent=2))
        sys.exit(rc)

    if not (args.module and args.test_cmd):
        ap.error("--module and --test-cmd required (or --selftest)")
    test_args = [a for a in args.test_args.split(",") if a] if args.test_args else []

    receipt, rc = run_adequacy(args.module, args.test_cmd, test_args,
                               args.bar, args.min_mutants, args.timeout)
    print(json.dumps({k: v for k, v in receipt.items() if k != "results"}, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(receipt, indent=2))
    sys.exit(rc)


if __name__ == "__main__":
    main()
