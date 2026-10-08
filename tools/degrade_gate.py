#!/usr/bin/env python3
"""degrade_gate.py — graceful-degradation + contrast-arm gate for sweep results.

Pattern lifted PROVEN from rc q19 / ENDO-1b (booked 2026-10-08, prereg
proposals/runs/ENDO-1-endogenous-flip-prereg-amendment.md): a gate whose
benefit survives a scarcity/parameter sweep is only trusted when benefit
SHRINKS monotonically and NEVER INVERTS ("graceful degradation" — q19's
70/60/52/45 ladder shape), and when its EXOGENOUS CONTRAST ARM never fires
at ANY sweep point (q19 G2: exo firing anywhere falsifies the
endogenous-source claim). A gate that passes at the nominal point but
inverts under scarcity is REGIME-BRITTLE — honest RED, never a silent PASS.

Input sweeps JSON: a list of points
  [{"param": <number, capacity — the gate walks it DOWNWARD as scarcity
    grows, q19's 70→60→52→45 ladder>, "benefit": <number>,
    "exo_fired": <bool, optional — contrast arm fired? default false>}]
Points are sorted DESCENDING by param (scarcity ascending) before gating.

Verdicts (exit codes):
  0  GRACEFUL    — benefit monotone non-increasing across the sweep, never
                   negative, exo arm silent at every point.
  1  FAIL        — INVERTED (benefit rises at any step, or drops below 0:
                   regime-brittle) or EXO-FIRED (contrast arm fired).
  2  FAIL-INPUT  — non-finite numbers, <2 points, malformed records.

Stdlib-only, deterministic, one JSON receipt. Never echoes secrets.

Worked example (docstring = spec):
  cat > sweep.json <<'EOF'
  [
    {"param": 70, "benefit": 12.25},
    {"param": 60, "benefit": 10.1},
    {"param": 52, "benefit": 6.3},
    {"param": 45, "benefit": 4.0}
  ]
  EOF
  python tools/degrade_gate.py --sweep-file sweep.json --out r.json
  # -> GRACEFUL rc=0; r.json books per-step deltas + verdict GRACEFUL

Selftest carries positive + RED controls:
  python tools/degrade_gate.py --selftest
"""
import argparse
import json
import math
import sys
from pathlib import Path

RC_PASS, RC_FAIL, RC_INPUT = 0, 1, 2


def fail_input(msg, out_path=None):
    receipt = {"tool": "degrade_gate", "verdict": "FAIL-INPUT", "why": msg}
    if out_path:
        _write_receipt(receipt, out_path)
    print(json.dumps(receipt, indent=2))
    sys.exit(RC_INPUT)


def _write_receipt(receipt, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
        f.flush()
        import os
        os.fsync(f.fileno())
    Path(tmp).replace(path)


def run_gate(points, tolerance=0.0):
    """Gate a list of sweep points. Returns (rc, receipt_dict).

    Ascending scarcity is walked as DESCENDING param (q19 convention:
    capacity shrinks 70->45). Points are sorted descending by param;
    duplicate params are a fail-loud input error.
    """
    if not isinstance(points, list) or len(points) < 2:
        raise ValueError(f"need >=2 sweep points, got {len(points) if isinstance(points, list) else type(points).__name__}")

    clean = []
    for i, p in enumerate(points):
        if not isinstance(p, dict) or "param" not in p or "benefit" not in p:
            raise ValueError(f"point {i}: malformed record (need param+benefit)")
        param, benefit = p["param"], p["benefit"]
        for name, v in (("param", param), ("benefit", benefit)):
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
                raise ValueError(f"point {i}: {name} not finite number: {v!r}")
        clean.append({"param": float(param), "benefit": float(benefit),
                      "exo_fired": bool(p.get("exo_fired", False))})

    clean.sort(key=lambda r: r["param"], reverse=True)
    for a, b in zip(clean, clean[1:]):
        if a["param"] == b["param"]:
            raise ValueError(f"duplicate param {a['param']}")

    steps = []
    for a, b in zip(clean, clean[1:]):
        delta = b["benefit"] - a["benefit"]
        steps.append({"from_param": a["param"], "to_param": b["param"],
                      "delta": round(delta, 12)})

    exo_points = [r["param"] for r in clean if r["exo_fired"]]

    reasons = []
    if exo_points:
        reasons.append(f"EXO-FIRED at params {exo_points}")
    inverted = [s for s in steps if s["delta"] > tolerance]
    if inverted:
        reasons.append(f"INVERTED at {len(inverted)} step(s): benefit RISES "
                       f"(first: {inverted[0]['from_param']}->{inverted[0]['to_param']} "
                       f"delta={inverted[0]['delta']}) — regime-brittle")
    negatives = [r["param"] for r in clean if r["benefit"] < 0]
    if negatives:
        reasons.append(f"NEGATIVE benefit at params {negatives}")

    rc = RC_PASS if not reasons else RC_FAIL
    receipt = {
        "tool": "degrade_gate",
        "verdict": "GRACEFUL" if rc == RC_PASS else "REGIME-BRITTLE" if inverted or negatives else "EXO-FIRED",
        "n_points": len(clean),
        "benefit_ladder": [{"param": r["param"], "benefit": r["benefit"],
                            "exo_fired": r["exo_fired"]} for r in clean],
        "steps": steps,
        "reasons": reasons,
    }
    return rc, receipt


def _selftest():
    checks = []

    def pin(name, got, want):
        ok = got == want
        checks.append(ok)
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got rc={got}, want rc={want}")

    # 1. graceful ladder (q19 shape) -> PASS
    rc, r = run_gate([{"param": 70, "benefit": 12.25}, {"param": 60, "benefit": 10.1},
                      {"param": 52, "benefit": 6.3}, {"param": 45, "benefit": 4.0}])
    pin("graceful ladder", rc, RC_PASS)
    checks.append(r["verdict"] == "GRACEFUL")

    # 2. inversion -> FAIL REGIME-BRITTLE
    rc, r = run_gate([{"param": 70, "benefit": 5.0}, {"param": 45, "benefit": 8.0}])
    pin("inversion", rc, RC_FAIL)
    checks.append(r["verdict"] == "REGIME-BRITTLE")

    # 3. negative benefit -> FAIL
    rc, r = run_gate([{"param": 70, "benefit": 5.0}, {"param": 45, "benefit": -1.0}])
    pin("negative benefit", rc, RC_FAIL)

    # 4. exo fired anywhere -> FAIL EXO-FIRED (even with graceful ladder)
    rc, r = run_gate([{"param": 70, "benefit": 12.0}, {"param": 45, "benefit": 3.0, "exo_fired": True}])
    pin("exo-fired", rc, RC_FAIL)
    checks.append(r["verdict"] == "EXO-FIRED")

    # 5. flat benefit (all zeros delta) is graceful — shrink, never invert
    rc, _ = run_gate([{"param": 1, "benefit": 4.0}, {"param": 2, "benefit": 4.0}])
    pin("flat ladder", rc, RC_PASS)

    # 6. fail-loud inputs
    for bad in ([], [{"param": 1}], "nope",
                [{"param": 1, "benefit": 1.0}, {"param": 2, "benefit": float("nan")}],
                [{"param": 1, "benefit": 1.0}, {"param": 1, "benefit": 2.0}]):
        try:
            run_gate(bad)
            print(f"  [FAIL] fail-loud on {bad!r}: no error raised")
            checks.append(False)
        except ValueError:
            checks.append(True)
    print(f"  [PASS] fail-loud battery (5 cases)" if checks[-5:] == [True]*5 else "  [FAIL] fail-loud battery")

    n_pass = sum(1 for c in checks if c)
    print(f"selftest: {n_pass}/{len(checks)} checks pass")
    sys.exit(0 if n_pass == len(checks) else 1)


def main():
    ap = argparse.ArgumentParser(description="graceful-degradation + contrast-arm sweep gate (ENDO-1b/q19 pattern)")
    ap.add_argument("--sweep", help="sweep points as JSON string")
    ap.add_argument("--sweep-file", help="sweep points as JSON file")
    ap.add_argument("--tolerance", type=float, default=0.0,
                    help="max tolerated benefit rise per step (default 0 = any rise inverts)")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true", help="run positive+negative control battery")
    args = ap.parse_args()

    if args.selftest:
        _selftest()

    try:
        if args.sweep_file:
            raw = open(args.sweep_file, encoding="utf-8").read()
        elif args.sweep:
            raw = args.sweep
        else:
            ap.error("one of --sweep / --sweep-file / --selftest required")
        points = json.loads(raw)
    except json.JSONDecodeError as e:
        fail_input(f"bad JSON: {e}", args.out)
    except OSError as e:
        fail_input(f"cannot read sweep file: {e}", args.out)

    try:
        rc, receipt = run_gate(points, tolerance=args.tolerance)
    except ValueError as e:
        fail_input(str(e), args.out)

    if args.out:
        _write_receipt(receipt, args.out)
    print(json.dumps(receipt, indent=2))
    sys.exit(rc)


if __name__ == "__main__":
    main()
