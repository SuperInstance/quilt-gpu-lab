#!/usr/bin/env python3
"""horizon_witness.py — evidence-expiry audit for decision gates.

Pattern lifted PROVEN from QO6h (booked 2026-10-06: the q10 failure mode —
evidence expiring before decision latency — was audited structurally, and the
QO6 kernel was PROVEN immune because E(t) is a cumsum over the FULL prefix).
This mechanizes that audit for ANY gate via a RECENCY FLIP: the decisive
early evidence is relocated to the END of the series (levels re-anchored, so
within-block increments, direction, and total evidence are preserved — only
WHEN the evidence occurs changes). A gate whose decision moves is weighting
evidence by recency: its readable horizon expires, old evidence silently
drives the call. A gate whose decision is flip-invariant reads the full
prefix: no expiry, structurally (QO6h's proof, mechanized).

Interface contract (same shape as gate_power_probe): the gate is any command
run via list-form subprocess (no shell) that reads the series as a JSON array
on stdin and writes a JSON object with a "decision" key on stdout.

Verdict:
  CLEAN    rc=0  decision is recency-flip invariant (full-prefix reader)
  EXPIRES  rc=1  recency flip changed the decision (both decisions booked)
  FAIL-INPUT rc=2 fail-loud: bad JSON, no decision key, gate crash, or the
                 gate is decision-DEAD (identical decision on the series and
                 both strongly-perturbed controls — a gate that never looks
                 at the data is trivially expiry-proof and proves nothing)

Stdlib-only, read-only on the gate, fail-loud rc=2, one JSON receipt.

Worked example (with the QO6 eproc gate):
  # adapter (stdin series -> JSON decision), e.g. scratch/hw_eproc_gate.py:
  #   import sys, json; sys.path.insert(0, ".")
  #   from tools.eproc import kill_gate
  #   print(json.dumps(kill_gate(json.load(sys.stdin), sigma=4.0)))
  python tools/horizon_witness.py --gate python --gate-args scratch/hw_eproc_gate.py \
      --series '[400,398,396,394,392,390,388,386,384,382,380,378]' \
      --out r.json

Selftest: python tools/horizon_witness.py --selftest
  pins: full-prefix gate -> CLEAN, last-k windowed gate -> EXPIRES,
  constant-output gate -> FAIL-INPUT (decision-dead), gate crash -> FAIL-INPUT.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import os
from pathlib import Path


def run_gate(cmd, args, series, timeout=60):
    """Run the gate via list-form subprocess; series JSON on stdin, JSON out."""
    proc = subprocess.run(
        [cmd] + list(args),
        input=json.dumps(series),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gate exited rc={proc.returncode}: {proc.stderr.strip()[:400]}")
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"gate stdout is not JSON: {e}: {proc.stdout[:200]!r}")
    if not isinstance(out, dict) or "decision" not in out:
        raise RuntimeError("gate output missing 'decision' key")
    return out


def recency_flip(series):
    """Move the FIRST HALF of the evidence to the END. Levels of the moved
    block are re-anchored to continue from the retained block, so within-block
    increments, direction, and total evidence are preserved — only timing
    changes. This is the probe: does WHEN evidence occurs change the call?"""
    if len(series) < 4:
        raise ValueError("series too short for a recency flip")
    mid = len(series) // 2
    early, late = list(series[:mid]), list(series[mid:])
    offset = late[-1] - early[0]
    return late + [v + offset for v in early]


def audit(gate_cmd, gate_args, series, timeout=60):
    full = run_gate(gate_cmd, gate_args, series, timeout)
    # decision-dead control: gate must react to data in SOME direction
    dead = True
    for direction in (+1, -1):
        ctrl = list(series)
        ctrl[-1] = ctrl[-1] + direction * 1000.0 * (abs(ctrl[-1]) + 1.0)
        r = run_gate(gate_cmd, gate_args, ctrl, timeout)
        if r.get("decision") != full.get("decision"):
            dead = False
            break
    if dead:
        raise RuntimeError(
            "gate is decision-DEAD: identical decision on series and perturbed controls"
        )
    flipped_series = recency_flip(series)
    flipped = run_gate(gate_cmd, gate_args, flipped_series, timeout)
    expires = flipped.get("decision") != full.get("decision")
    return {
        "verdict": "EXPIRES" if expires else "CLEAN",
        "full_decision": full.get("decision"),
        "flipped_decision": flipped.get("decision"),
    }


WINDOWED_GATE = '''\
import sys, json
k = int(sys.argv[1])
s = json.load(sys.stdin)
tail = [b - a for a, b in zip(s, s[1:])][-k:]
dec = "KILL_CANDIDATE" if sum(tail) < -40 else "KEEP"
print(json.dumps({"decision": dec, "window": k}))
'''

FULLPREFIX_GATE = '''\
import sys, json
s = json.load(sys.stdin)
tot = sum(b - a for a, b in zip(s, s[1:]))
dec = "KILL_CANDIDATE" if tot < -20 else "KEEP"
print(json.dumps({"decision": dec}))
'''

DEAD_GATE = '''\
import sys, json
json.load(sys.stdin)
print(json.dumps({"decision": "KEEP"}))
'''

CRASH_GATE = '''\
import sys, json
json.load(sys.stdin)
sys.exit(3)
'''


def _write_fixture(d, name, src):
    p = os.path.join(d, name)
    with open(p, "w") as f:
        f.write(src)
    return p


def selftest():
    checks = []
    series = [400.0 - 20.0 * i for i in range(9)] + [240.0] * 7
    # early drop, flat tail: full-prefix reads the whole thing, a last-k
    # window forgot the drop — the recency flip moves it where it CAN see it.
    with tempfile.TemporaryDirectory() as d:
        win = _write_fixture(d, "win_gate.py", WINDOWED_GATE)
        fullp = _write_fixture(d, "full_gate.py", FULLPREFIX_GATE)
        dead = _write_fixture(d, "dead_gate.py", DEAD_GATE)
        crash = _write_fixture(d, "crash_gate.py", CRASH_GATE)

        r = audit(sys.executable, [fullp], series)
        checks.append(("full-prefix gate CLEAN", r["verdict"] == "CLEAN"
                       and r["full_decision"] == r["flipped_decision"] == "KILL_CANDIDATE"))

        r = audit(sys.executable, [win, "4"], series)
        checks.append((
            "windowed gate EXPIRES (flip moves the drop)",
            r["verdict"] == "EXPIRES" and r["full_decision"] == "KEEP"
            and r["flipped_decision"] == "KILL_CANDIDATE",
        ))

        try:
            audit(sys.executable, [dead], series)
            checks.append(("dead gate FAIL-INPUT", False))
        except RuntimeError as e:
            checks.append(("dead gate FAIL-INPUT", "decision-DEAD" in str(e)))

        try:
            audit(sys.executable, [crash], series)
            checks.append(("crash gate FAIL-INPUT", False))
        except RuntimeError as e:
            checks.append(("crash gate FAIL-INPUT", "rc=3" in str(e)))

    ok = all(v for _, v in checks)
    print(json.dumps({"selftest": "PASS" if ok else "FAIL",
                      "checks": [{"name": n, "ok": v} for n, v in checks]}, indent=2))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="evidence-expiry audit for decision gates")
    ap.add_argument("--gate", help="gate command (list-form, no shell)")
    ap.add_argument("--gate-args", default="", help="comma-separated gate args")
    ap.add_argument("--series", help="series as JSON array")
    ap.add_argument("--series-file", help="or path to JSON array")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(selftest())

    receipt = {"tool": "horizon_witness"}
    try:
        if a.series:
            series = json.loads(a.series)
        elif a.series_file:
            with open(a.series_file) as f:
                series = json.load(f)
        else:
            raise ValueError("need --series or --series-file")
        if not isinstance(series, list) or len(series) < 4:
            raise ValueError("series must be a JSON array of length >= 4")
        if not a.gate:
            raise ValueError("need --gate")
        r = audit(a.gate, [x for x in a.gate_args.split(",") if x], series, a.timeout)
        receipt.update(r)
        rc = 0 if r["verdict"] == "CLEAN" else 1
    except Exception as e:  # fail-loud
        receipt["verdict"] = "FAIL-INPUT"
        receipt["error"] = f"{type(e).__name__}: {e}"
        rc = 2

    print(json.dumps(receipt, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(receipt, indent=2) + "\n")
    sys.exit(rc)


if __name__ == "__main__":
    main()
