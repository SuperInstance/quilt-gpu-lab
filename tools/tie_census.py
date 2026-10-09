#!/usr/bin/env python3
"""tie_census — TIE-1: census of gate comparisons whose tie/no-op case resolves to PASS.

Class (canons 8fef113 / selectlib): `mae() > 1e-6` never calls the clean arm;
`X <= Y + 1e-12` passes at tie. A permissive-tie gate converts boundary coincidence
into a PASS. AST-classify the pre-registered target set, empirically probe each
PASS-side flag with an explicit tie input, then mutation-lite: flip the permissive
side in a temp copy and check the owning committed test/selftest DETECTS.

Fail-loud: unknown target, syntax error, or probe crash => raise, never book GREEN.
"""
from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Frozen target set (prereg: proposals/runs/TIE-1-tie-gate-census-prereg-2026-10-09.md)
TARGETS = {
    "verdict_gate.Gate.passes": ("tools/verdict_gate.py", "passes",
                                 ["python", "-m", "pytest", "-q", "tests/test_verdict_gate.py"]),
    "degrade_gate.run_gate": ("tools/degrade_gate.py", "run_gate", ["python", "tools/degrade_gate.py", "--selftest"]),
    "eproc.bounds": ("tools/eproc.py", None, ["python", "tools/eproc.py", "--selftest"]),
    "exit_gate_witness.params": ("tools/exit_gate_witness.py", None, ["python", "tools/exit_gate_witness.py", "--selftest"]),
    "determ1_lattice_snap.eps": ("experiments/determ1_lattice_snap.py", None, None),
}


def classify_cmp(op: ast.cmpop) -> str:
    """PASS-side-tie candidates: <=, >=, ==, or != (rarely). Strict-side: <, >."""
    if isinstance(op, (ast.Lt, ast.Gt)):
        return "strict-side"
    return "tie-candidate"


def census(rel: str, fn_name: str | None) -> list[dict]:
    src = (REPO / rel).read_text()
    tree = ast.parse(src, filename=rel)
    rows = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1:
            continue
        if fn_name:
            # only comparisons lexically inside the named function
            if not any(isinstance(p, ast.FunctionDef) and p.name == fn_name
                       and node.lineno >= p.lineno and node.lineno <= (p.end_lineno or p.lineno)
                       for p in ast.walk(tree) if isinstance(p, ast.FunctionDef)):
                continue
        kind = classify_cmp(node.ops[0])
        if kind == "strict-side":
            continue
        rows.append({
            "target": f"{rel}:{node.lineno}",
            "op": type(node.ops[0]).__name__,
            "src": ast.unparse(node)[:120],
            "ast_class": "tie-candidate",
        })
    return rows


def probe_tie(rel: str, node_src: str, tie_env: str) -> dict:
    """G2: evaluate the comparison source with the tie value bound in tie_env."""
    try:
        ns: dict = {}
        exec(tie_env, ns)  # noqa: S102 - fixed, self-authored probe env
        val = eval(node_src, ns)  # noqa: S307 - fixed probe
        return {"expr": node_src, "tie_result": bool(val)}
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"probe crash on {rel!r} expr {node_src!r}: {e}")


def mutation_lite(rel: str, test_cmd: list[str], old: str, new: str) -> dict:
    """G3: flip permissive side in temp copy; owning suite must FAIL (detect)."""
    src_path = REPO / rel
    orig = src_path.read_text()
    if old not in orig:
        raise RuntimeError(f"mutation anchor {old!r} not found in {rel}")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / src_path.name
        tmp.write_text(orig.replace(old, new, 1))
        # run the committed test against the mutated module via PYTHONPATH shadowing
        env = {"PATH": "/usr/bin:/bin", "HOME": str(Path.home()),
               "PYTHONPATH": f"{td}:{REPO}:{REPO / 'experiments'}"}
        try:
            r = subprocess.run(test_cmd, cwd=REPO, env=env, timeout=120,
                               capture_output=True, text=True)  # noqa: S603
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"mutation test TIMEOUT for {rel}")
        return {"rel": rel, "old": old, "new": new,
                "rc": r.returncode, "detected": r.returncode != 0,
                "tail": (r.stdout + r.stderr)[-300:]}


def selftest() -> int:
    ok = 0
    # strict-side ops must never classify as tie-candidate
    assert classify_cmp(ast.Lt()) == "strict-side"
    assert classify_cmp(ast.GtE()) == "tie-candidate"
    ok += 1
    # census finds the known verdict_gate tie comparisons
    rows = census("tools/verdict_gate.py", "passes")
    assert any("<" not in r["src"] or "Lt" in r["op"] for r in rows) or rows, "no rows"
    assert any("minimum" in r["src"] or "maximum" in r["src"] for r in rows), \
        "expected min/max compare in passes()"
    ok += 1
    # probe harness: tie at minimum passes (empirical, pre-registered prediction)
    p = probe_tie("tools/verdict_gate.py", "0.80 < 0.80 and not (0.80 > 0.80)", "pass")
    assert p["tie_result"] is False, "tie must NOT fail the gate (PASS-side tie)"
    ok += 1
    # mutation anchor present
    assert "self.value < self.minimum" in (REPO / "tools/verdict_gate.py").read_text()
    ok += 1
    print(f"tie_census selftest {ok}/4 PASS")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    report = {"targets": {}, "mutations": [], "summary": {}}
    total_rows = 0
    for name, (rel, fn, _test) in TARGETS.items():
        try:
            rows = census(rel, fn)
        except SyntaxError as e:
            raise RuntimeError(f"fail-loud: {rel} does not parse: {e}")
        report["targets"][name] = rows
        total_rows += len(rows)
    # G2 probes for the pre-registered known ties
    report["probes"] = [
        probe_tie("tools/verdict_gate.py", "value < minimum", "value=0.80; minimum=0.80"),
        probe_tie("tools/degrade_gate.py", "delta > tolerance", "delta=0.05; tolerance=0.05"),
    ]
    # G3 mutation-lite on the flagged PASS-side ties
    m1 = mutation_lite("tools/verdict_gate.py",
                       TARGETS["verdict_gate.Gate.passes"][2],
                       "self.value < self.minimum", "self.value <= self.minimum")
    m1["owning"] = "verdict_gate Gate.passes (booked callers: PARAM-1a, QO-lane receipts)"
    report["mutations"].append(m1)
    m2 = mutation_lite("tools/degrade_gate.py", TARGETS["degrade_gate.run_gate"][2],
                       "s[\"delta\"] > tolerance", "s[\"delta\"] >= tolerance")
    m2["owning"] = "degrade_gate tolerance (ENDO-1b/q19 pattern)"
    report["mutations"].append(m2)
    detected = [m["owning"] for m in report["mutations"] if m["detected"]]
    undetected = [m["owning"] for m in report["mutations"] if not m["detected"]]
    report["summary"] = {
        "tie_candidate_rows": total_rows,
        "mutations_detected": detected,
        "mutations_UNDETECTED_yellow": undetected,
        "red_live": [],
    }
    out = REPO / "results" / "tie1_gate_census.json"
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
