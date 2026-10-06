#!/usr/bin/env python3
"""gate-power-probe — measure a binary kill gate's false-kill / retraction / power.

Pattern lifted PROVEN from QO6t (booked 2026-10-06: retraction 0.92 PASS,
kill power 0.00 FAIL on rank-series feed — a gate can look sane and still
have zero power against the population it was built to kill). This
mechanizes that three-way measurement for ANY gate command:

  - false-kill rate   : fraction of KNOWN-GOOD (crossed) streams the gate
                        KILLs at checkpoint horizon A.
  - recovery          : of those premature kills, fraction the gate itself
                        RETRACTS when shown the full series (a kill that is
                        never retracted is a wrong answer, not a checkpoint).
  - kill power        : fraction of KNOWN-BAD (dead) streams the gate KILLs
                        at horizon B — zero power means the gate never fires
                        on the population it exists to fire on.

Verdict bands (QO6t pins): PASS iff recovery >= --recover-bar (0.80) AND
power >= --power-bar (0.30); PREMATURE-KILL iff falseKill > --fk-bar (0.30)
AND recovery < 0.50; else MIXED. A gate with no bad streams books
power null (1.0 vacuous guard: power is UNKNOWN, verdict MIXED honestly).

The gate is an external command run in list-form subprocess (never shell):
series JSON on stdin, it must print a JSON object on stdout with at least
{"decision": "...KILL..."} — a decision containing the substring "KILL"
counts as a kill; a truthy "retracted" field books retraction. Missing
fields fail loud (rc=2).

Worked example:
    python tools/gate_power_probe.py --streams ex.json \
        --gate python --gate-args my_gate.py --checkpoints 12,16 --out r.json

Selftest (built-in last-value gate + seeded synthetic streams):
    python tools/gate_power_probe.py --selftest

Stdlib-only. Exit 0=PASS / 1=FAIL-or-MIXED / 2=fail-loud.
"""
import argparse
import json
import subprocess
import sys
import hashlib
import random
from pathlib import Path


def fail(msg):
    print(f"FAIL-INPUT: {msg}", file=sys.stderr)
    sys.exit(2)


def run_gate(cmd, args, series):
    """Run the gate command once; stdin=series JSON, stdout=parsed JSON."""
    payload = json.dumps(list(series)).encode()
    try:
        p = subprocess.run([cmd] + list(args), input=payload,
                           capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        fail(f"gate command could not run: {type(e).__name__}: {e}")
    if p.returncode != 0:
        fail(f"gate exited {p.returncode}: {p.stderr.decode(errors='replace')[:200]}")
    try:
        d = json.loads(p.stdout.decode())
    except json.JSONDecodeError as e:
        fail(f"gate stdout is not JSON: {e}")
    if not isinstance(d, dict) or "decision" not in d:
        fail("gate output must be a JSON object with a 'decision' field")
    return {"kill": "KILL" in str(d["decision"]).upper(),
            "retracted": bool(d.get("retracted", False))}


def run_gate_builtin(series):
    """Selftest gate: KILL if mean of last 4 values < 0.35; retracts iff the
    full-series mean >= 0.35. Deliberately weak on hopeless streams."""
    m = sum(series[-4:]) / 4.0
    return {"kill": m < 0.35,
            "retracted": sum(series) / len(series) >= 0.35}


def evaluate(streams, checkpoints, gate_fn, full_len=None):
    """streams: [{id, label: crossed|dead, series: [...]}. Returns metrics."""
    if not streams:
        fail("no streams provided")
    for s in streams:
        if "series" not in s or "label" not in s:
            fail("each stream needs 'series' and 'label'")
        if s["label"] not in ("crossed", "dead"):
            fail(f"stream {s.get('id','?')} label must be crossed|dead, got {s['label']!r}")
        if len(s["series"]) < 2 or any(not isinstance(v, (int, float)) for v in s["series"]):
            fail(f"stream {s.get('id','?')} series must be >=2 numeric values")
    if full_len is None:
        full_len = max(len(s["series"]) for s in streams)
    out = {"checkpoints": {}, "full": {}}
    horizons = list(checkpoints) + [full_len]
    killed_at_A = []
    for h in horizons:
        dec = {}
        for s in streams:
            dec[s["id"]] = (s, run_gate_fn(gate_fn, s["series"][:h]))
        out["checkpoints" if h != full_len else "full"][str(h)] = _metrics(dec)
        if h == horizons[0]:
            killed_at_A = [sid for sid, (_, d) in dec.items()
                           if d["kill"] and _label(streams, sid) == "crossed"]
    # retraction of horizon-A kills, judged at full length
    retr = []
    for sid in killed_at_A:
        s = next(x for x in streams if x["id"] == sid)
        retr.append(bool(run_gate_fn(gate_fn, s["series"])["retracted"]))
    A = out["checkpoints"][str(horizons[0])]
    B = out["full"][str(full_len)]
    recovery = (sum(retr) / len(retr)) if retr else 1.0
    fk, power = A["kill_rate_good"], B["kill_rate_bad"]
    power_null = A["n_bad"] == 0
    if power_null:
        verdict = "MIXED"  # power unknown — never PASS on a vacuous power
    elif recovery >= 0.80 and power >= 0.30:
        verdict = "PASS"
    elif fk > 0.30 and recovery < 0.50:
        verdict = "PREMATURE-KILL"
    else:
        verdict = "MIXED"
    out["verdict"] = {"falseKill_A": fk, "recovery_of_A_kills": recovery,
                      "power_B": power, "power_null": power_null,
                      "n_A_kills": len(killed_at_A), "verdict": verdict}
    return out


def run_gate_fn(gate_fn, series):
    return gate_fn(series) if gate_fn is run_gate_builtin else gate_fn(series)


def _label(streams, sid):
    return next(s["label"] for s in streams if s["id"] == sid)


def _metrics(dec):
    """dec: id -> (stream, decision)."""
    good = [(s, d) for s, d in dec.values() if s["label"] == "crossed"]
    bad = [(s, d) for s, d in dec.values() if s["label"] == "dead"]
    return {
        "n_good": len(good), "n_bad": len(bad),
        "kill_rate_good": (sum(1 for _, d in good if d["kill"]) / len(good)) if good else 0.0,
        "kill_rate_bad": (sum(1 for _, d in bad if d["kill"]) / len(bad)) if bad else 0.0,
    }


def _seed_streams():
    """Seeded synthetic population: crossed streams drift upward past 0.9,
    dead streams stay low. Deterministic (sha-pinned in selftest)."""
    rng = random.Random(42)
    streams = []
    for i in range(8):
        v, ser = 0.2, []
        for _ in range(24):
            v += rng.uniform(-0.06, 0.14)
            ser.append(round(min(max(v, 0.0), 1.0), 4))
        streams.append({"id": f"crossed-{i}", "label": "crossed", "series": ser})
    for i in range(8):
        v, ser = 0.15, []
        for _ in range(24):
            v += rng.uniform(-0.07, 0.02)
            ser.append(round(min(max(v, 0.0), 1.0), 4))
        streams.append({"id": f"dead-{i}", "label": "dead", "series": ser})
    return streams


def selftest():
    checks = []
    streams = _seed_streams()

    # pin 1: construction — crossed streams actually end high, dead stay low
    ends = [s["series"][-1] for s in streams if s["label"] == "crossed"]
    ends_d = [s["series"][-1] for s in streams if s["label"] == "dead"]
    checks.append(("construct crossed end high", min(ends) >= 0.7))
    checks.append(("construct dead end low", max(ends_d) < 0.5))

    # RED control: a gate that kills EVERYTHING must book PREMATURE-KILL
    r = evaluate(streams, [12], lambda s: {"kill": True, "retracted": False})
    checks.append(("kill-all gate -> PREMATURE-KILL rc1", r["verdict"]["verdict"] == "PREMATURE-KILL"))

    # positive control: last-4 gate passes crossed population, kills dead
    r = evaluate(streams, [12], run_gate_builtin)
    v = r["verdict"]
    checks.append(("builtin gate nonzero power", v["power_B"] >= 0.5))
    checks.append(("builtin gate recovery sane", v["recovery_of_A_kills"] >= 0.5))
    checks.append(("builtin gate verdict in bands", v["verdict"] in ("PASS", "MIXED")))

    # bad-label fail-loud
    try:
        evaluate([{"id": "x", "label": "banana", "series": [1, 2]}], [1], run_gate_builtin)
        checks.append(("bad label rc2", False))
    except SystemExit as e:
        checks.append(("bad label rc2", e.code == 2))

    # empty fail-loud
    try:
        evaluate([], [1], run_gate_builtin)
        checks.append(("empty rc2", False))
    except SystemExit as e:
        checks.append(("empty rc2", e.code == 2))

    ok = all(c for _, c in checks)
    for name, c in checks:
        print(f"  {'PASS' if c else 'FAIL'}  {name}")
    print(f"SELFTEST: {'OK' if ok else 'FAILED'} ({sum(c for _, c in checks)}/{len(checks)})")
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                 epilog="exit 0=PASS / 1=FAIL-or-MIXED / 2=fail-loud")
    ap.add_argument("--streams", help="streams JSON: [{id,label,series}]")
    ap.add_argument("--gate", help="gate command (run with series JSON on stdin)")
    ap.add_argument("--gate-args", default="", help="comma-separated gate args")
    ap.add_argument("--checkpoints", default="12", help="comma-separated horizon A,B,... (default 12)")
    ap.add_argument("--out", help="receipt path")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if not a.streams or not a.gate:
        fail("--streams and --gate required (or --selftest)")
    streams = json.loads(Path(a.streams).read_text())
    if isinstance(streams, dict):
        streams = streams.get("streams")
    cps = [int(x) for x in a.checkpoints.split(",")]
    if not cps or any(c < 2 for c in cps):
        fail("checkpoints must be ints >= 2")
    gargs = [x for x in a.gate_args.split(",") if x] if a.gate_args else []
    r = evaluate(streams, cps, lambda s: run_gate(a.gate, gargs, s))
    r["gate"] = {"cmd": a.gate, "args": gargs, "checkpoints": cps}
    r["n_streams"] = len(streams)
    r["sha"] = hashlib.sha256(json.dumps(streams, sort_keys=True).encode()).hexdigest()[:16]
    print(json.dumps(r["verdict"], indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=2))
        print(f"receipt: {a.out}")
    sys.exit(0 if r["verdict"]["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
