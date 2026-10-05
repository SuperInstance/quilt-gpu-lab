#!/usr/bin/env python3
"""det-witness — determinism witness: run a command N times, hash its output,
book bit-identical vs drift (pattern lifted from the DET-1 determinism-witness
census, booked 2026-10-05: a REST-EM rerun claimed identical but shipped no
receipt — "deterministic" is a measurement, not an assertion).

Given a command, runs it N times (list-form subprocess, never shell), hashes
each run's combined stdout+stderr bytes (sha256), and books:
  - IDENTICAL : all N run hashes match run[0]
  - DRIFT     : any hash differs (first divergent run + both hashes booked)
  - ERROR     : any run exits nonzero (fail-loud, its stderr booked)
Exit 0=IDENTICAL / 1=DRIFT / 2=ERROR-or-fail-loud-input. One JSON receipt.

Stdlib-only. Keys are never handled. Memory is O(output) per run — outputs
are hashed streaming-free but never accumulated across runs (only hashes are).

Usage:
  python tools/det_witness.py --cmd python tools/det_witness.py --args --selftest-cmd --runs 3 --out r.json
  python tools/det_witness.py --cmd python --args my_script.py --seed 7 [--runs 2] [--cwd DIR]
  python tools/det_witness.py --selftest

Worked example:
  $ python tools/det_witness.py --cmd sh --args -c,echo deterministic --runs 2
  -> verdict IDENTICAL, rc=0, receipt printed to stdout.

Selftest carries a positive control (deterministic command -> IDENTICAL) and
a RED control (nondeterministic command -> DRIFT), so a broken witness books
FAIL against its own controls.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time


def run_once(cmd, args, cwd, timeout_s):
    """Run cmd+args once (list-form only). Returns (rc, out_bytes, err_bytes, wall_s)."""
    t0 = time.time()
    proc = subprocess.run(
        [cmd] + list(args),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_s,
    )
    return proc.returncode, proc.stdout, proc.stderr, time.time() - t0


def witness(cmd, args, runs, cwd=None, timeout_s=300):
    """Core: run `runs` times, compare sha256 of stdout+stderr bytes.

    Returns (verdict, receipt_dict). verdict in {"IDENTICAL", "DRIFT", "ERROR"}.
    """
    if runs < 2:
        raise ValueError("need --runs >= 2 to witness determinism (got %d)" % runs)
    if not cmd:
        raise ValueError("need --cmd")
    if any(not isinstance(a, str) for a in args):
        raise ValueError("all args must be strings")

    hashes = []
    walls = []
    for i in range(runs):
        rc, out, err, wall = run_once(cmd, args, cwd, timeout_s)
        walls.append(round(wall, 3))
        if rc != 0:
            receipt = {
                "tool": "det-witness",
                "verdict": "ERROR",
                "cmd": [cmd] + list(args),
                "failed_run": i,
                "rc": rc,
                "stderr_tail": err.decode("utf-8", "replace")[-2000:],
                "runs": runs,
            }
            return "ERROR", receipt
        hashes.append(
            hashlib.sha256(out + b"\x00-stderr-\x00" + err).hexdigest()
        )

    first = hashes[0]
    drift = next((i for i, h in enumerate(hashes) if h != first), None)
    verdict = "IDENTICAL" if drift is None else "DRIFT"
    receipt = {
        "tool": "det-witness",
        "verdict": verdict,
        "cmd": [cmd] + list(args),
        "runs": runs,
        "hash0": first,
        "walls_s": walls,
    }
    if drift is not None:
        receipt["first_divergent_run"] = drift
        receipt["hash_divergent"] = hashes[drift]
    return verdict, receipt


def selftest():
    """Positive control (deterministic -> IDENTICAL) + RED control (drifting -> DRIFT)."""
    checks = []
    v, _ = witness(sys.executable, ["-c", "print('stable')"], runs=3)
    checks.append(("positive-IDENTICAL", v == "IDENTICAL"))
    v, _ = witness(
        sys.executable, ["-c", "import time;print(time.time_ns())"], runs=3
    )
    checks.append(("red-DRIFT", v == "DRIFT"))
    try:
        witness(sys.executable, ["-c", "print('x')"], runs=1)
        checks.append(("runs>=2 fail-loud", False))
    except ValueError:
        checks.append(("runs>=2 fail-loud", True))
    v, r = witness(sys.executable, ["-c", "import sys;sys.exit(3)"], runs=2)
    checks.append(("error-loud", v == "ERROR" and r["rc"] == 3))

    ok = all(ok for _, ok in checks)
    print(json.dumps({"selftest": "PASS" if ok else "FAIL",
                      "checks": checks}, indent=2))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="det-witness: run a command N times, book bit-identical vs drift."
    )
    ap.add_argument("--cmd", help="executable to run (no shell)")
    ap.add_argument("--args", default="",
                    help="comma-separated args (use ,x,, for a literal comma)")
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--cwd", default=None)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--out", default=None, help="receipt path (default: stdout)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()

    args = [x for x in a.args.split(",")] if a.args else []
    try:
        verdict, receipt = witness(a.cmd, args, a.runs, a.cwd, a.timeout)
    except (ValueError, OSError, subprocess.TimeoutExpired) as e:
        receipt = {"tool": "det-witness", "verdict": "ERROR",
                   "fail_loud": repr(e)}
        verdict = "ERROR"

    blob = json.dumps(receipt, indent=2)
    if a.out:
        with open(a.out, "w") as f:
            f.write(blob + "\n")
        print("receipt -> %s" % a.out)
    print(blob)
    return {"IDENTICAL": 0, "DRIFT": 1, "ERROR": 2}[verdict]


if __name__ == "__main__":
    sys.exit(main())
