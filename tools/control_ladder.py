#!/usr/bin/env python3
"""control-ladder — generic POS + expect-red negative-control harness (stdlib only).

Lifted from tonight's PROVEN CAN-1 pattern (tools/canary.py control_ladder,
BOOKED PASS G1-G4, crab-traps template via SCOUT-30): a checker isn't trusted
until it has passed a positive control (real defect -> red) AND been shown
not to be trivially-always-red (clean input -> green). The ladder makes
"the detector can fire AND doesn't false-positive" a mechanical, fail-closed
verdict instead of a vibe.

Core API:

    from control_ladder import Ladder

    lad = Ladder()
    lad.green("POS-clean", lambda: my_check(good_input))       # must NOT fire
    lad.red("T1-tamper",   lambda: my_check(bad_input))        # MUST fire
    verdict = lad.run()            # {"verdict": "PASS"|"FAIL", "rungs": {...}}
    sys.exit(0 if verdict["verdict"] == "PASS" else 1)

Semantics (fail-closed, never escalates):
  - green rung: check returns falsy  -> ok; truthy -> FALSE-POSITIVE -> FAIL
  - red rung:   check returns truthy -> ok; falsy  -> BLIND SPOT -> FAIL
  - check raises -> rung counts as FIRED (an exception is a detection signal),
    EXCEPT for green rungs, where raising -> FAIL (a clean input must not blow up)
  - any non-PASS exits 1 with a JSON receipt on stdout

CLI — worked example (self-test, mirrors canary.py's digest ladder):

    $ python tools/control_ladder.py --selftest
    {"verdict": "PASS", "rungs": {"POS": ..., "T1": ...}, ...}

Ad hoc ladder from a python expression file (each line "name|expect|expr",
expr evaluated with a shared `env` dict built line-by-line):

    $ python tools/control_ladder.py --rungs rungs.txt
"""
from __future__ import annotations

import json
import sys
from typing import Callable, Dict, List, Tuple


class Rung:
    __slots__ = ("name", "expect_red", "fn")

    def __init__(self, name: str, expect_red: bool, fn: Callable[[], object]):
        self.name, self.expect_red, self.fn = name, expect_red, fn


class Ladder:
    """Ordered collection of green (POS) and red (negative-control) rungs."""

    def __init__(self) -> None:
        self._rungs: List[Rung] = []

    def green(self, name: str, fn: Callable[[], object]) -> "Ladder":
        self._rungs.append(Rung(name, False, fn))
        return self

    def red(self, name: str, fn: Callable[[], object]) -> "Ladder":
        self._rungs.append(Rung(name, True, fn))
        return self

    def run(self) -> dict:
        """Execute every rung. Returns fail-closed verdict dict.

        verdict PASS iff: every red rung fired, every green rung did not,
        and at least one red rung exists (a ladder with no negative controls
        is a tautology — VOID, never PASS)."""
        rungs: Dict[str, dict] = {}
        fired = 0
        for r in self._rungs:
            try:
                out = bool(r.fn())
                err = None
            except Exception as e:  # exception == detection signal
                out, err = True, f"{type(e).__name__}: {e}"
            if out:
                fired += 1
            observed = "red" if out else "green"
            want = "red" if r.expect_red else "green"
            entry = {"expect": want, "observed": observed, "ok": observed == want}
            if err:
                entry["exception"] = err
            rungs[r.name] = entry
        n_red = sum(1 for r in self._rungs if r.expect_red)
        ok = all(v["ok"] for v in rungs.values())
        if n_red == 0:
            # a ladder with no negative controls is a tautology — VOID, never PASS
            ok = False
        verdict = "PASS" if ok else "FAIL"
        return {"verdict": verdict, "rungs": rungs, "red_fired": fired, "n_red": n_red}


def _selftest() -> dict:
    """Digest ladder mirroring canary.py: a checker that catches a tampered
    input but passes a clean one."""
    M = (1 << 64) - 1

    def fnv1a64(s: str) -> int:
        h = 14695981039346656037
        for b in s.encode("utf-8"):
            h = ((h ^ b) * 1099511628211) & M
        return h

    fixture = "café Δ 日本語"
    pin = fnv1a64(fixture)

    def check(s: str, expected: int) -> bool:
        return fnv1a64(s) != expected  # True == defect detected (fired)

    lad = Ladder()
    lad.green("POS-clean-fixture", lambda: check(fixture, pin))
    lad.red("T1-tamper-expectation", lambda: check(fixture, pin ^ 0x1))
    lad.red("T2-tamper-input-bytes", lambda: check(fixture.replace("café", "cafe"), pin))
    return lad.run()


def _run_rungs_file(path: str) -> dict:
    """Lines 'name|red|python-expr'. env dict accumulates prior line values."""
    lad = Ladder()
    env: dict = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, expect, expr = (p.strip() for p in line.split("|", 2))
            expect_red = expect.lower() == "red"
            def fn(expr=expr, env=env):  # noqa: E731 — closure per line
                env["out"] = bool(eval(expr, {"__builtins__": __builtins__}, env))  # type: ignore[name-defined]
                return env["out"]
            (lad.red if expect_red else lad.green)(name, fn)
    return lad.run()


def main(argv: List[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Generic POS + expect-red control-ladder harness (fail-closed).")
    ap.add_argument("--selftest", action="store_true",
                    help="run the built-in digest-ladder example")
    ap.add_argument("--rungs", metavar="FILE",
                    help="ladder definition: lines 'name|red|expr' or 'name|green|expr'")
    args = ap.parse_args(argv)

    if args.selftest:
        receipt = _selftest()
    elif args.rungs:
        receipt = _run_rungs_file(args.rungs)
    else:
        ap.print_help()
        return 1
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
