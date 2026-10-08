#!/usr/bin/env python3
"""exit_gate_witness.py -- verdict-vs-exit-code gate witness.

Pattern lifted PROVEN from SCOUT-74 / quilt-murmur (booked 2026-10-08):
28 experiments ran behind a fails-closed receipt chain, yet 9/28 experiments
EXITED 0 under a verdict-INVERTING mutation (Hedge eta*r->0 flipped
SOURCE_BEATS_ECHO 23/24 -> ECHO_STEALS_TRUST 0/24 and e17 still exited 0).
"The tree of experiments is measurement, not gate" -- and nothing mechanized
the check. This tool is that check.

Contract: run a command (list-form subprocess, no shell) on a GOOD input and
a MUTATED input; parse a verdict field (dotted --verdict-key path) from each
run's JSON stdout; gate BOTH clauses:
  G1 positive:  good input  -> verdict in PASS set  AND exit code == 0
  G2 negative:  mutated     -> verdict in FAIL set  AND exit code != 0
A FAIL verdict with exit 0 books RED (the murmur class). A mutation that
doesn't invert the verdict books NOT-INVERTING (the mutation is too weak to
witness anything -- honest book, never PASS). Command crash on the mutated
input counts as gate-fires (exit != 0), since harness death IS the gate.

Stdlib-only, fail-loud rc=2 on bad input/missing verdict/JSON errors,
exit 0=WITNESSED / 1=RED / 2=FAIL-INPUT. JSON receipt either way.
Token-free, read-only on the target.

Usage:
  python tools/exit_gate_witness.py \
      --cmd python3 --args my_gate.py,--in,{INPUT} \
      --good good.json --bad bad.json [--verdict-key verdict] [--out r.json]
    {INPUT} in --args is replaced by the good/bad file path (or inline JSON
    if you pass --good/'--bad' JSON strings with --inline).

  python tools/exit_gate_witness.py --selftest
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PASS_SET = {"PASS", "KEEP", "GREEN", "CLEAN", "OK"}
FAIL_SET = {"FAIL", "KILL", "RED", "DEGENERATE", "NOT-INVERTING"}


def fail_input(msg):
    print(json.dumps({"tool": "exit_gate_witness", "verdict": "FAIL-INPUT", "why": msg}))
    sys.exit(2)


def run_cmd(cmd, timeout):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, "", f"{type(e).__name__}: {e}"


def extract_verdict(stdout, key):
    try:
        doc = json.loads(stdout)
    except json.JSONDecodeError as e:
        fail_input(f"stdout is not JSON: {e}")
    cur = doc
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            fail_input(f"verdict key '{key}' missing from stdout JSON")
        cur = cur[part]
    if not isinstance(cur, str):
        fail_input(f"verdict at '{key}' is not a string")
    return cur


def witness(cmd_tmpl, good, bad, key, timeout):
    """cmd_tmpl: list with one element containing '{INPUT}'."""
    out = {}
    for tag, payload in (("good", good), ("bad", bad)):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write(payload)
            path = f.name
        cmd = [c.replace("{INPUT}", path) for c in cmd_tmpl]
        rc, so, se = run_cmd(cmd, timeout)
        verdict = extract_verdict(so, key)
        out[tag] = {"rc": rc, "verdict": verdict, "stdout_bytes": len(so),
                    "stderr_head": se[:200]}
        Path(path).unlink(missing_ok=True)
    g, b = out["good"], out["bad"]

    if b["verdict"] == g["verdict"]:
        return "NOT-INVERTING", 1, out, ("mutation did not flip the verdict "
               f"(both '{g['verdict']}') -- too weak to witness the gate")
    if g["verdict"] not in PASS_SET:
        fail_input(f"good-input verdict '{g['verdict']}' not in PASS set {sorted(PASS_SET)}")
    if b["verdict"] not in FAIL_SET:
        fail_input(f"mutated verdict '{b['verdict']}' not in FAIL set {sorted(FAIL_SET)}")
    if g["rc"] != 0:
        return "RED", 1, out, f"good input exits {g['rc']} (must be 0)"
    if b["rc"] == 0:
        return "RED", 1, out, ("MURMUR CLASS: FAIL verdict but exit 0 -- "
               "measurement, not gate")
    return "WITNESSED", 0, out, "PASS->exit0 and FAIL->nonzero both hold"


def selftest():
    """4 pins: witnessed, murmur-RED (FAIL prints, exits 0), not-inverting, fail-loud."""
    gate_ok = ("import json,sys;d=json.load(open(sys.argv[1]));"
               'print(json.dumps({"verdict":"PASS" if d["x"]>0 else "FAIL"}));'
               "sys.exit(0 if d['x']>0 else 1)")
    gate_murmur = gate_ok.replace("else 1)", "else 0)")  # FAIL prints but exits 0
    results = []
    for name, gate, expect_rc in (
        ("witnessed", gate_ok, 0),
        ("murmur-RED", gate_murmur, 1),
        ("not-inverting", None, None),  # bad input still passes -> NOT-INVERTING rc=1
        ("fail-loud-nokey", None, 2),
    ):
        if name == "not-inverting":
            r = witness(["python3", "-c", gate_ok, "{INPUT}"],
                        '{"x":1}', '{"x":1}', "verdict", 30)
            ok = r[1] == 1 and r[0] == "NOT-INVERTING"
        elif name == "fail-loud-nokey":
            import io, contextlib
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    witness(["python3", "-c", "print('{}')", "{INPUT}"],
                            '{"x":1}', '{"x":0}', "verdict", 30)
                ok = False
            except SystemExit as e:
                ok = e.code == 2
        else:
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
                f.write(gate)
                gp = f.name
            r = witness(["python3", gp, "{INPUT}"], '{"x":1}', '{"x":0}', "verdict", 30)
            Path(gp).unlink()
            ok = r[1] == expect_rc and r[0] == ("WITNESSED" if expect_rc == 0 else "RED")
        results.append((name, ok))
    bad = [n for n, ok in results if not ok]
    if bad:
        print(f"SELFTEST FAIL: {bad}")
        sys.exit(2)
    print(f"SELFTEST PASS {len(results)}/{len(results)}")
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--cmd", help="executable (with {INPUT} substitution in --args)")
    ap.add_argument("--args", default="", help="comma-separated args; {INPUT} replaced")
    ap.add_argument("--good", help="good input: file path, or inline JSON with --inline")
    ap.add_argument("--bad", help="mutated input: file path, or inline JSON with --inline")
    ap.add_argument("--inline", action="store_true", help="treat --good/--bad as JSON strings")
    ap.add_argument("--verdict-key", default="verdict")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--out", help="receipt path")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    if not (a.cmd and a.good and a.bad):
        fail_input("--cmd, --good, --bad required (or --selftest)")
    if "{INPUT}" not in a.args:
        fail_input("--args must contain {INPUT} exactly once")
    if a.inline:
        good, bad = a.good, a.bad
        for tag, s in (("good", good), ("bad", bad)):
            try:
                json.loads(s)
            except json.JSONDecodeError as e:
                fail_input(f"--{tag} inline JSON invalid: {e}")
    else:
        for tag, s in (("good", a.good), ("bad", a.bad)):
            if not Path(s).exists():
                fail_input(f"--{tag} file missing: {s}")
        good, bad = Path(a.good).read_text(), Path(a.bad).read_text()

    cmd = [a.cmd] + a.args.split(",")
    verdict, rc, runs, why = witness(cmd, good, bad, a.verdict_key, a.timeout)
    receipt = {"tool": "exit_gate_witness", "verdict": verdict, "rc": rc,
               "why": why, "cmd": cmd, "runs": runs}
    line = json.dumps(receipt)
    if a.out:
        Path(a.out).write_text(line + "\n")
    print(line)
    sys.exit(rc)


if __name__ == "__main__":
    main()
