#!/usr/bin/env python3
"""gate-property-probe — randomized property test for any decision gate.

Pattern lifted PROVEN from PROP-1 (booked GREEN 2026-10-09, commits f92322e/d75feaf:
the eproc witness law was property-tested with a seeded null arm, an effect arm,
and mutation-verification — a gate whose H0 and H1 fire-rates are not measured
is a gate with untested laws). This mechanizes that battery for ANY gate that
reads a numeric series on stdin and prints a JSON verdict:

  1. G1 H0 safety:   N seeded null series (mu=0)  -> fire-rate <= --h0-ceil
  2. G2 H1 power:    N seeded effect series (mu=--mu1) -> fire-rate >= --h1-floor
  3. G3 mutation:    an optional MUTANT gate must BREAK at least one of G1/G2
                     (mutant passing everything = the suite is vacuous,
                     booked VACUOUS, never PASS).

Series are cumulative sums of N(mu, sigma) gaussians — the PROP-1 levels-path
convention (gates that difference internally get levels; pass increments via a
--raw-increments flag if your gate expects them). Fail-loud rc=2 on bad input,
gate crash, non-finite numbers, or missing verdict field. Stdlib-only,
list-form subprocess, seeded, deterministic, one JSON receipt.
Exit 0=PASS / 1=FAIL|VACUOUS / 2=FAIL-INPUT.

Usage:
  python tools/gate_property_probe.py --gate python3 --gate-args mygate.py \
      --n 200 --t 60 --sigma 0.3 --mu1 -0.05 --fire-verdict WITNESSED \
      [--mutant python3 --mutant-args mygate_mutant.py] [--out r.json] | --selftest

Worked example (docstring self-test inline):
  python tools/gate_property_probe.py --selftest
"""
import argparse
import json
import math
import random
import subprocess
import sys
import time

FAIL_INPUT = 2


def fail_loud(why):
    print(json.dumps({"tool": "gate_property_probe", "verdict": "FAIL-INPUT", "why": why}))
    sys.exit(FAIL_INPUT)


def make_series(mu, sigma, t, n, seed, raw_increments):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        incs = [rng.gauss(mu, sigma) for _ in range(t)]
        if raw_increments:
            out.append(incs)
        else:
            lvl, s = [], 0.0
            for x in incs:
                s += x
                lvl.append(s)
            out.append(lvl)
    return out


def run_gate(cmd, args, series, fire_verdict, verdict_key):
    """Run the gate on one series; returns 1 if it fired, 0 if not. Crash = fail-loud."""
    payload = json.dumps({"series": series})
    cmd_v = list(cmd) if isinstance(cmd, (list, tuple)) else [cmd] + list(args or [])
    try:
        p = subprocess.run(cmd_v, input=payload, capture_output=True,
                           text=True, timeout=120)
    except OSError as e:
        fail_loud(f"gate spawn failed: {e}")
    except subprocess.TimeoutExpired:
        fail_loud("gate timed out (120s)")
    if p.returncode != 0:
        fail_loud(f"gate exited {p.returncode}: {p.stderr[:400]}")
    try:
        doc = json.loads(p.stdout)
    except json.JSONDecodeError:
        fail_loud(f"gate stdout not JSON: {p.stdout[:200]!r}")
    v = doc
    for part in verdict_key.split("."):
        if not isinstance(v, dict) or part not in v:
            fail_loud(f"verdict key {verdict_key!r} missing in gate output")
        v = v[part]
    if not isinstance(v, str):
        fail_loud(f"verdict {verdict_key!r} is not a string")
    return 1 if v == fire_verdict else 0


def fire_rate(cmd, args, series_list, fire_verdict, verdict_key):
    fired = 0
    for s in series_list:
        fired += run_gate(cmd, args, s, fire_verdict, verdict_key)
    return fired / len(series_list)


def _wilson_ceil(p, n):
    """Rough 95% upper bound helper for choosing a sane default ceiling (display only)."""
    z = 1.96
    return (p + z * z / (2 * n) + z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def run_probe(gate, gargs, mutant, margs, n, t, sigma, mu1, seed,
              h0_ceil, h1_floor, fire_verdict, verdict_key, raw_increments):
    receipt = {
        "tool": "gate_property_probe", "n": n, "t": t, "sigma": sigma, "mu1": mu1,
        "seed": seed, "h0_ceil": h0_ceil, "h1_floor": h1_floor,
        "fire_verdict": fire_verdict, "raw_increments": raw_increments,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if n < 20:
        fail_loud("n < 20: fire-rate estimates too noisy to gate")
    if t < 2:
        fail_loud("t < 2: series degenerate")
    for name, v in (("sigma", sigma), ("mu1", mu1), ("h0_ceil", h0_ceil), ("h1_floor", h1_floor)):
        if not math.isfinite(v):
            fail_loud(f"{name} non-finite")
    if h0_ceil <= 0 or h0_ceil >= 1:
        fail_loud("h0_ceil must be in (0,1)")
    if h1_floor <= 0 or h1_floor > 1:
        fail_loud("h1_floor must be in (0,1]")
    if h1_floor <= h0_ceil:
        fail_loud("h1_floor must exceed h0_ceil (deadband needed)")
    if mu1 == 0:
        fail_loud("mu1 == 0: H1 arm would be another null arm (vacuous power test)")

    nulls = make_series(0.0, sigma, t, n, seed, raw_increments)
    effects = make_series(mu1, sigma, t, n, seed + 1, raw_increments)

    r_h0 = fire_rate(gate, gargs, nulls, fire_verdict, verdict_key)
    g1 = r_h0 <= h0_ceil
    receipt["h0_fire_rate"] = r_h0
    receipt["g1_h0_safety"] = "PASS" if g1 else "FAIL"

    r_h1 = fire_rate(gate, gargs, effects, fire_verdict, verdict_key)
    g2 = r_h1 >= h1_floor
    receipt["h1_fire_rate"] = r_h1
    receipt["g2_h1_power"] = "PASS" if g2 else "FAIL"

    receipt["mutations"] = []
    mutation_ok = True
    if mutant:
        m_h0 = fire_rate(mutant, margs, nulls, fire_verdict, verdict_key)
        m_h1 = fire_rate(mutant, margs, effects, fire_verdict, verdict_key)
        caught_h0 = m_h0 > h0_ceil
        caught_h1 = m_h1 < h1_floor
        caught = caught_h0 or caught_h1
        receipt["mutations"].append({
            "mutant": mutant, "h0_fire_rate": m_h0, "h1_fire_rate": m_h1,
            "caught": caught, "via": "h0" if caught_h0 else ("h1" if caught_h1 else "none"),
        })
        mutation_ok = caught
        receipt["g3_mutation"] = "CAUGHT" if caught else "MISSED"

    if not g1:
        receipt["verdict"] = "FAIL"
        why = f"H0 fire-rate {r_h0:.4f} exceeds ceiling {h0_ceil} — gate fires on noise"
    elif not g2:
        receipt["verdict"] = "FAIL"
        why = f"H1 fire-rate {r_h1:.4f} below floor {h1_floor} — gate blind to effect"
    elif mutant and not mutation_ok:
        receipt["verdict"] = "VACUOUS"
        why = "mutant passed both arms — suite cannot detect a broken gate"
    else:
        receipt["verdict"] = "PASS"
        why = "H0 quiet + H1 fires" + (" + mutant caught" if mutant else " (no mutant given)")
    receipt["why"] = why
    return receipt


def _inline_gate():
    """Deadband gate fixture: WITNESSED iff the series' last-minus-first <= -threshold."""
    code = (
        "import json,sys\n"
        "s=json.load(sys.stdin)['series']\n"
        "d=s[-1]-s[0]\n"
        "print(json.dumps({'verdict':'WITNESSED' if d<=-6.0 else 'NOT_WITNESSED'}))\n"
    )
    return [sys.executable, "-c", code]


def _inline_mutant():
    """Mutant: SAME gate but threshold always -1e9 (never fires) — must lose H1 power."""
    code = (
        "import json,sys\n"
        "s=json.load(sys.stdin)['series']\n"
        "d=s[-1]-s[0]\n"
        "print(json.dumps({'verdict':'WITNESSED' if d<=-1e9 else 'NOT_WITNESSED'}))\n"
    )
    return [sys.executable, "-c", code]


def selftest():
    checks = []
    good = _inline_gate()
    dead = _inline_mutant()

    # 1: good gate, no mutant -> PASS
    r = run_probe(good, [], None, None, 100, 40, 0.5, -0.6, 0xC0FFEE,
                  0.12, 0.8, "WITNESSED", "verdict", False)
    checks.append(("good-gate PASS", r["verdict"] == "PASS", r.get("why")))

    # 2: dead mutant (never fires) is CAUGHT via H1 power loss -> PASS with g3 CAUGHT
    r = run_probe(good, [], dead, [], 100, 40, 0.5, -0.6, 0xC0FFEE,
                  0.12, 0.8, "WITNESSED", "verdict", False)
    checks.append(("dead-mutant CAUGHT", r["verdict"] == "PASS" and
                   r["g3_mutation"] == "CAUGHT" and
                   r["mutations"][0]["via"] == "h1", r.get("why")))

    # 2b: mutant identical to the gate passes both arms -> suite VACUOUS
    r = run_probe(good, [], good, [], 100, 40, 0.5, -0.6, 0xC0FFEE,
                  0.12, 0.8, "WITNESSED", "verdict", False)
    checks.append(("identical-mutant VACUOUS", r["verdict"] == "VACUOUS", r.get("why")))

    # 3: blind gate (always NOT_WITNESSED) -> FAIL on H1 power
    blind = [sys.executable, "-c",
             "import json,sys; json.load(sys.stdin); print(json.dumps({'verdict':'NOT_WITNESSED'}))"]
    r = run_probe(blind, [], None, None, 100, 40, 0.5, -0.6, 0xC0FFEE,
                  0.12, 0.8, "WITNESSED", "verdict", False)
    checks.append(("blind-gate FAIL(power)", r["verdict"] == "FAIL" and r["g2_h1_power"] == "FAIL", r.get("why")))

    # 4: trigger-happy gate -> FAIL on H0 safety
    happy = [sys.executable, "-c",
             "import json,sys; json.load(sys.stdin); print(json.dumps({'verdict':'WITNESSED'}))"]
    r = run_probe(happy, [], None, None, 100, 40, 0.5, -0.6, 0xC0FFEE,
                  0.12, 0.8, "WITNESSED", "verdict", False)
    checks.append(("trigger-happy FAIL(h0)", r["verdict"] == "FAIL" and r["g1_h0_safety"] == "FAIL", r.get("why")))

    # 5: determinism — same seed rerun, identical rates
    r3 = run_probe(good, [], None, None, 100, 40, 0.5, -0.6, 0xC0FFEE,
                   0.12, 0.8, "WITNESSED", "verdict", False)
    r4 = run_probe(good, [], None, None, 100, 40, 0.5, -0.6, 0xC0FFEE,
                   0.12, 0.8, "WITNESSED", "verdict", False)
    checks.append(("deterministic", (r3["h0_fire_rate"], r3["h1_fire_rate"]) ==
                   (r4["h0_fire_rate"], r4["h1_fire_rate"]), "seeded arms"))

    # 6: fail-loud — mu1 == 0 books FAIL-INPUT rc=2
    try:
        run_probe(good, [], None, None, 100, 40, 0.5, 0.0, 0xC0FFEE,
                  0.12, 0.8, "WITNESSED", "verdict", False)
        checks.append(("mu1=0 fail-loud", False, "no exception"))
    except SystemExit as e:
        checks.append(("mu1=0 fail-loud", e.code == FAIL_INPUT, f"rc={e.code}"))

    ok = sum(1 for _, s, _ in checks if s)
    print(f"SELFTEST {ok}/{len(checks)}")
    for name, passed, note in checks:
        print(f"  {'OK ' if passed else 'BAD'} {name}: {note}")
    sys.exit(0 if ok == len(checks) else 1)


def main():
    ap = argparse.ArgumentParser(description="Randomized H0/H1 property probe for any verdict gate")
    ap.add_argument("--gate", help="gate command (list-form; reads JSON {'series': [...]} on stdin)")
    ap.add_argument("--gate-args", default="", help="comma-separated args for the gate")
    ap.add_argument("--mutant", help="mutant gate command (must break an arm or suite is VACUOUS)")
    ap.add_argument("--mutant-args", default="")
    ap.add_argument("--n", type=int, default=200, help="series per arm (min 20)")
    ap.add_argument("--t", type=int, default=60, help="series length")
    ap.add_argument("--sigma", type=float, default=0.3, help="per-step noise")
    ap.add_argument("--mu1", type=float, default=-0.05, help="per-step effect (must be nonzero)")
    ap.add_argument("--seed", type=lambda x: int(x, 0), default=0xC0FFEE)
    ap.add_argument("--h0-ceil", type=float, default=0.12, help="H0 fire-rate ceiling")
    ap.add_argument("--h1-floor", type=float, default=0.80, help="H1 fire-rate floor")
    ap.add_argument("--fire-verdict", default="WITNESSED", help="verdict string meaning 'fired'")
    ap.add_argument("--verdict-key", default="verdict", help="dotted path to verdict in gate stdout")
    ap.add_argument("--raw-increments", action="store_true",
                    help="hand the gate raw increments instead of cumulative levels")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
    if not args.gate:
        ap.error("--gate required (or --selftest)")

    receipt = run_probe(
        args.gate, [a for a in args.gate_args.split(",") if a],
        args.mutant, [a for a in args.mutant_args.split(",") if a],
        args.n, args.t, args.sigma, args.mu1, args.seed,
        args.h0_ceil, args.h1_floor, args.fire_verdict, args.verdict_key,
        args.raw_increments,
    )
    blob = json.dumps(receipt, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(blob)
    print(blob)
    sys.exit(0 if receipt["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
