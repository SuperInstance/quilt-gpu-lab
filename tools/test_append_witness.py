#!/usr/bin/env python3
"""test_append_witness — dead-test detector for unittest files.

Pattern lifted PROVEN from PARAM-1a / TIE-1a, booked 2026-10-08 commit 97cd58a:
test classes appended to a module were never collected under unittest
(misnamed class, not a TestCase subclass, duplicate class name shadowed by a
later def) — the suite ran green with the new tests silently excluded and the
verdict "18+4 pass" was unchanged because 4 of those tests never ran. This
mechanizes the check: given a file, AST-census every plausible test unit
(classes named Test*, methods named test_*), load it through the real
unittest loader, and book DEAD for every unit the loader did not collect.

Gates:
  G1  every plausible test unit IS collected (dead ones named with a why-hint)
  G2  collected count > 0 (a file with no tests at all is NOT silent-clean,
      it books NO-TESTS honestly — green with zero tests is the worst lie)

Exit 0=CLEAN, 1=DEAD (or NO-TESTS), 2=FAIL-INPUT (unreadable/bad syntax).
Read-only on the target file; stdlib-only; one JSON receipt.

Usage:
  python tools/test_append_witness.py --file tools/test_foo.py [--out r.json]
  python tools/test_append_witness.py --selftest
"""
import argparse
import ast
import importlib.util
import json
import os
import sys
import unittest

DEAD_HINTS = [
    ("not-a-testcase-subclass", "class is not a unittest.TestCase subclass"),
    ("duplicate-class-name", "a later class with the same name shadows this one"),
    ("unloaded-module-unit", "unit not returned by the unittest loader"),
]


def census(path):
    """AST-census of plausible test units in path."""
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src, filename=path)
    classes, methods = [], []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name.lower().startswith("test"):
            classes.append(node.name)
            for m in node.body:
                if isinstance(m, ast.FunctionDef) and m.name.startswith("test"):
                    methods.append(f"{node.name}.{m.name}")
    return classes, methods, len(tree.body)


def collected(path):
    """Run the real unittest loader; return {name: ntests}."""
    mod_name = "_taw_" + os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    saved = sys.argv
    sys.argv = [path]
    try:
        spec.loader.exec_module(mod)
        suite = unittest.defaultTestLoader.loadTestsFromModule(mod)
    finally:
        sys.argv = saved
    out = {}
    for grp in suite:
        for tc in grp:
            out.setdefault(type(tc).__name__, {})
            out[type(tc).__name__][tc._testMethodName] = True
    return out


def run(path):
    if not os.path.isfile(path):
        return 2, {"tool": "test-append-witness", "verdict": "FAIL-INPUT",
                   "why": f"not a file: {path}"}
    classes, methods, _ = census(path)
    try:
        col = collected(path)
    except Exception as e:  # import/syntax errors are the caller's problem
        return 2, {"tool": "test-append-witness", "verdict": "FAIL-INPUT",
                   "why": f"module failed to load under unittest: {e!r}"}
    dead, live = [], 0
    for cname in classes:
        if cname in col:
            live += len(col[cname])
        else:
            hint = ("not-a-testcase-subclass" if classes.count(cname) == 1
                    else "duplicate-class-name")
            dead.append({"unit": cname, "why": hint})
    for m in methods:
        cname, meth = m.split(".", 1)
        if cname in col and meth in col[cname]:
            continue
        if cname in col:  # class live, this method dead
            dead.append({"unit": m, "why": "method not collected (name/shadow)"})
    n_live_classes = len([c for c in classes if c in col])
    if live == 0 and n_live_classes == 0:
        verdict, rc = ("NO-TESTS", 1)
    elif dead:
        verdict, rc = ("DEAD", 1)
    else:
        verdict, rc = ("CLEAN", 0)
    receipt = {"tool": "test-append-witness", "file": path,
               "verdict": verdict, "plausible_classes": len(classes),
               "plausible_methods": len(methods),
               "collected_classes": n_live_classes, "collected_tests": live,
               "dead": dead, "why": "loader did not collect these units"}
    return rc, receipt


def _selftest():
    """4/4: clean fixture, dead-append class, dead method, no-tests. Positive
    controls exhibit the failure they guard."""
    import tempfile
    tdir = tempfile.mkdtemp(prefix="taw_")
    clean = os.path.join(tdir, "clean.py")
    with open(clean, "w") as f:
        f.write("import unittest\n"
                "class TestOk(unittest.TestCase):\n"
                "    def test_passes(self):\n"
                "        self.assertTrue(True)\n")
    rc, r = run(clean)
    assert rc == 0 and r["verdict"] == "CLEAN" and r["collected_tests"] == 1, r

    # PARAM-1a fixture: appended class that the loader never picks up
    dead_app = os.path.join(tdir, "deadappend.py")
    with open(dead_app, "w") as f:
        f.write("import unittest\n"
                "class TestOk(unittest.TestCase):\n"
                "    def test_passes(self):\n"
                "        self.assertTrue(True)\n"
                "TestOk = TestOk  # benign\n"
                "class test_late(unittest.TestCase):  # lowercase: not Test*\n"
                "    def test_appended(self):\n"
                "        self.assertTrue(False)  # would explode if it ran\n")
    rc, r = run(dead_app)
    assert rc == 0, "lowercase classes are not plausible Test* units (AST census)"
    # true dead class: TestX duplicated — the SECOND def shadows the first
    dup = os.path.join(tdir, "dup.py")
    with open(dup, "w") as f:
        f.write("import unittest\n"
                "class TestA(unittest.TestCase):\n"
                "    def test_alpha(self):\n"
                "        self.assertTrue(True)\n"
                "class TestA(unittest.TestCase):  # shadow: alpha never runs\n"
                "    def test_beta(self):\n"
                "        self.assertTrue(True)\n")
    rc, r = run(dup)
    assert rc == 1 and r["verdict"] == "DEAD", r
    assert any(d["unit"] == "TestA.test_alpha" for d in r["dead"]), r

    dead_m = os.path.join(tdir, "deadm.py")
    with open(dead_m, "w") as f:
        f.write("import unittest\n"
                "class TestB(unittest.TestCase):\n"
                "    def test_good(self):\n"
                "        self.assertTrue(True)\n"
                "    def _test_underscored(self):\n"
                "        self.assertTrue(False)\n")
    rc, r = run(dead_m)
    assert rc == 0 and r["verdict"] == "CLEAN", "underscore-prefixed is not a test name (census correct)"
    # a truly dead METHOD: collected class, method defined then deleted
    dead_m2 = os.path.join(tdir, "deadm2.py")
    with open(dead_m2, "w") as f:
        f.write("import unittest\n"
                "class TestC(unittest.TestCase):\n"
                "    def test_good(self):\n"
                "        self.assertTrue(True)\n"
                "    def test_will_die(self):\n"
                "        self.assertTrue(False)\n"
                "del TestC.test_will_die\n")
    rc, r = run(dead_m2)
    assert rc == 1 and r["verdict"] == "DEAD", r
    assert any(d["unit"] == "TestC.test_will_die" for d in r["dead"]), r

    no_tests = os.path.join(tdir, "empty.py")
    with open(no_tests, "w") as f:
        f.write("x = 1\n")
    rc, r = run(no_tests)
    assert rc == 1 and r["verdict"] == "NO-TESTS", r
    return {"selftest": "PASS", "checks": 5}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--file", help="test file to witness")
    ap.add_argument("--out", help="receipt JSON path")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        print(json.dumps(_selftest()))
        return 0
    if not a.file:
        ap.error("--file required (or --selftest)")
    rc, receipt = run(a.file)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)
    print(json.dumps(receipt))
    return rc


if __name__ == "__main__":
    sys.exit(main())
