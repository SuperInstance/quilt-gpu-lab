#!/usr/bin/env python3
"""verdict_repro — verdict-level repro witness (pattern lifted from DETERM-1, booked
2026-10-07: rerun REPRO was claimed at VERDICT level, not bit level — determin_witness's
sha256 bar is stronger than what lane verdicts need, and nothing mechanized the weaker,
correct claim). Runs a command N times (list-form subprocess, no shell), extracts a
verdict field from each run's JSON stdout (or `--receipt-key path.to.field` from a JSON
receipt file each run writes), and books:
  STABLE  rc=0 — every run produced the same verdict
  DRIFT   rc=1 — runs produced >=2 distinct verdicts (first divergence + values booked)
  ERROR   rc=2 — a run failed (nonzero exit, bad JSON, missing field) or input invalid
Fail-loud, JSON receipt, never echoes secrets, never mutates the repo.

Usage:
  python tools/verdict_repro.py --cmd python --args script.py,--flag --runs 3 \
      [--verdict-key verdict --out r.json]
  python tools/verdict_repro.py --selftest

Worked example (hermetic, no dependencies):
  python - <<'EOF' > /tmp/vr_demo.py
  import json,sys
  json.dump({"verdict":"KEEP" if int(sys.argv[1])%2==0 else "KILL"},sys.stdout)
  EOF
  python tools/verdict_repro.py --cmd python --args /tmp/vr_demo.py,4 --runs 2
  -> STABLE rc=0 (verdict KEEP both runs)
"""
import argparse, json, subprocess, sys, time, hashlib

EXIT = {"STABLE": 0, "DRIFT": 1, "ERROR": 2}


def get_field(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(f"missing field {dotted!r} (at {part!r})")
        cur = cur[part]
    return cur


def one_run(cmd, args, verdict_key):
    full = [cmd] + list(args)
    try:
        p = subprocess.run(full, capture_output=True, text=True, timeout=300)
    except FileNotFoundError as e:
        raise RuntimeError(f"command not found: {cmd}") from e
    except subprocess.TimeoutExpired:
        raise RuntimeError("run timed out (300s)")
    if p.returncode != 0:
        raise RuntimeError(f"run exited {p.returncode}")
    try:
        payload = json.loads(p.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"stdout is not valid JSON: {e}") from e
    try:
        return str(get_field(payload, verdict_key))
    except KeyError as e:
        raise RuntimeError(str(e)) from e


def run_repro(cmd, args, runs, verdict_key):
    if runs < 2:
        raise ValueError("runs must be >= 2 (a repro needs at least two runs)")
    verdicts, first_div = [], None
    for i in range(runs):
        t0 = time.time()
        try:
            v = one_run(cmd, args, verdict_key)
        except RuntimeError as e:
            return {"verdict": "ERROR", "runs_done": i, "error": str(e), "run_index": i}
        verdicts.append(v)
        if i > 0 and v != verdicts[0] and first_div is None:
            first_div = {"run_index": i, "run0": verdicts[0], "run": v}
    if first_div:
        book = "DRIFT"
    else:
        book = "STABLE"
    return {"verdict": book, "runs": runs, "verdicts": verdicts,
            "distinct": sorted(set(verdicts)), "first_divergence": first_div}


def _selftest():
    """FAIL-FIRST pins: each negative control exhibits the failure it guards."""
    py = sys.executable
    stable = f'import json,sys;json.dump({{"verdict":"KEEP"}},sys.stdout)'
    drift = f'import json,random,sys;json.dump({{"verdict":random.choice(["KEEP","KILL"])}},sys.stdout)'
    badjson = 'import sys;sys.stdout.write("not json")'
    nofield = 'import json,sys;json.dump({"other":1},sys.stdout)'
    fail = "import sys;sys.exit(3)"
    checks = []

    r = run_repro(py, ["-c", stable], 3, "verdict")
    checks.append(("stable->STABLE", r["verdict"] == "STABLE", r))

    r = run_repro(py, ["-c", drift], 4, "verdict")
    checks.append(("random->DRIFT", r["verdict"] == "DRIFT" and r["first_divergence"], r))

    r = run_repro(py, ["-c", badjson], 2, "verdict")
    checks.append(("badjson->ERROR", r["verdict"] == "ERROR" and "JSON" in r["error"], r))

    r = run_repro(py, ["-c", nofield], 2, "verdict")
    checks.append(("missing-field->ERROR", r["verdict"] == "ERROR" and "missing field" in r["error"], r))

    r = run_repro(py, ["-c", fail], 2, "verdict")
    checks.append(("nonzero->ERROR", r["verdict"] == "ERROR" and "exited 3" in r["error"], r))

    try:
        run_repro(py, ["-c", stable], 1, "verdict")
        checks.append(("runs<2 fail-loud", False, "no exception"))
    except ValueError as e:
        checks.append(("runs<2 fail-loud", True, str(e)))

    ok = all(c[1] for c in checks)
    print(json.dumps({"selftest": "PASS" if ok else "FAIL",
                      "checks": [{"pin": n, "ok": o, "detail": str(d)[:120]} for n, o, d in checks]},
                     indent=2))
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser(description="verdict-level repro witness (DETERM-1 pattern)")
    ap.add_argument("--cmd", help="executable to run (list-form subprocess, no shell)")
    ap.add_argument("--args", default="", help="comma-separated args for cmd")
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--verdict-key", default="verdict", help="dotted JSON path of the verdict field")
    ap.add_argument("--out", default=None, help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(_selftest())

    if not a.cmd:
        print("FAIL-INPUT: --cmd required (or --selftest)", file=sys.stderr)
        sys.exit(2)
    args = [x for x in a.args.split(",") if x != ""] if a.args else []
    rec = run_repro(a.cmd, args, a.runs, a.verdict_key)
    rec.update({"tool": "verdict-repro", "cmd": a.cmd, "args": args,
                "verdict_key": a.verdict_key, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    rec["receipt_sha256"] = hashlib.sha256(
        json.dumps({k: v for k, v in rec.items() if k != "receipt_sha256"}, sort_keys=True).encode()
    ).hexdigest()
    line = json.dumps(rec, indent=2)
    print(line)
    if a.out:
        with open(a.out, "w") as f:
            f.write(line + "\n")
    sys.exit(EXIT[rec["verdict"]])


if __name__ == "__main__":
    main()
