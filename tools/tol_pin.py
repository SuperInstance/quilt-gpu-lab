#!/usr/bin/env python3
"""tol_pin — tolerance-boundary pinner for numeric gates.

Pattern lifted PROVEN from TIE-1 (booked YELLOW 2026-10-09, canons 8fef113
class): `mae() > 1e-6` never fires on clean input; `X <= Y + 1e-12` passes at
tie. A tolerance that is not PINNED between the noise floor and the signal
scale is either vacuous (fires on noise), blind (misses the signal), or
degenerate (sits exactly on a boundary so the tie/no-op case decides the
verdict). This tool mechanizes the pin claim for a single tolerance:

    gate fires  iff  measured > tol          (strict comparator convention)

Given tol, a noise level (must stay quiet), and a signal level (must fire),
the pin holds iff ALL clauses pass:

  G1 quiet   : noise      <= tol   (noise never trips a strict gate)
  G2 fires   : signal     >  tol   (signal always trips it)
  G3 pinned  : noise      <  tol   (strict — noise == tol is a DEGENERATE tie,
                                   the exact TIE-1 YELLOW class, booked FAIL)
  G4 witness : signal/noise >= band (both sides of the boundary are
                                   witnessable at realistic scales; default 4)

Degenerate signal == tol also books FAIL (G2 strict). Non-finite inputs,
noise <= 0, or signal <= 0 fail loud rc=2. One JSON receipt either way;
exit 0=PINNED / 1=UNPINNED / 2=FAIL-INPUT. Stdlib-only, deterministic.

Worked example (docstring, also --example):
    tol=0.05, noise=1e-6, signal=0.2
      G1 quiet    1e-6  <= 0.05   OK
      G2 fires    0.2    > 0.05   OK
      G3 pinned   1e-6   < 0.05   OK
      G4 witness  0.2/1e-6 = 2e5 >= 4  OK
    -> PINNED rc=0

    tol=1e-12 with noise=1e-12 (the `X <= Y + 1e-12` tie):
      G3 pinned fails at equality -> UNPINNED rc=1 (degenerate-tie booked)

Usage:
    python tools/tol_pin.py --tol 0.05 --noise 1e-6 --signal 0.2 [--band 4 --name mygate --out r.json]
    python tools/tol_pin.py --example | --selftest
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time

DEFAULT_BAND = 4.0


def _finite(x: float) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def run_pin(tol: float, noise: float, signal: float, band: float = DEFAULT_BAND,
            name: str = "") -> dict:
    """Gate a single tolerance pin. Returns the receipt dict (verdict + rc)."""
    for label, v in (("tol", tol), ("noise", noise), ("signal", signal), ("band", band)):
        if not _finite(v):
            raise ValueError(f"{label} must be finite, got {v!r}")
    if noise <= 0:
        raise ValueError(f"noise must be > 0 (a zero/absent noise floor pins nothing), got {noise!r}")
    if signal <= 0:
        raise ValueError(f"signal must be > 0, got {signal!r}")
    if band <= 1:
        raise ValueError(f"band must be > 1 (band <= 1 cannot separate the arms), got {band!r}")

    g1_quiet = noise <= tol
    g2_fires = signal > tol
    g3_pinned = noise < tol  # strict: equality is the DEGENERATE tie class
    ratio = signal / noise
    g4_witness = ratio >= band

    clauses = {
        "G1_quiet": bool(g1_quiet),
        "G2_fires": bool(g2_fires),
        "G3_pinned_strict": bool(g3_pinned),
        "G4_witness": bool(g4_witness),
    }
    degenerate_tie = (noise == tol) or (signal == tol)
    ok = all(clauses.values())

    if degenerate_tie:
        verdict = "UNPINNED"
        tie_clauses = [c for c, hit in (("G2", signal == tol), ("G3", noise == tol)) if hit]
        why = "degenerate tie at boundary: " + ", ".join(tie_clauses)
    elif ok:
        verdict, why = "PINNED", "tol strictly separates noise from signal with witnessable margin"
    else:
        fails = [k for k, v in clauses.items() if not v]
        verdict, why = "UNPINNED", "unpinned: " + ", ".join(fails)

    return {
        "tool": "tol_pin",
        "name": name,
        "verdict": verdict,
        "rc": 0 if verdict == "PINNED" else 1,
        "why": why,
        "inputs": {"tol": tol, "noise": noise, "signal": signal, "band": band},
        "clauses": clauses,
        "signal_noise_ratio": ratio,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def _emit(receipt: dict, out: str | None) -> None:
    if out:
        with open(out, "w") as f:
            json.dump(receipt, f, indent=2)
            f.write("\n")
    print(json.dumps(receipt, indent=2))


def selftest() -> int:
    checks: list[tuple[str, bool]] = []

    def pin(tag, **kw):
        return tag, run_pin(**kw)

    # clean pin -> PINNED
    _, r = pin("clean", tol=0.05, noise=1e-6, signal=0.2)
    checks.append(("clean PINNED", r["verdict"] == "PINNED" and r["rc"] == 0))

    # degenerate noise==tol tie -> UNPINNED (the TIE-1 class)
    _, r = pin("tie-noise", tol=1e-12, noise=1e-12, signal=0.2)
    checks.append(("noise==tol tie UNPINNED",
                   r["verdict"] == "UNPINNED" and "G3" in r["why"]))

    # degenerate signal==tol -> UNPINNED
    _, r = pin("tie-signal", tol=0.2, noise=1e-6, signal=0.2)
    checks.append(("signal==tol UNPINNED", r["verdict"] == "UNPINNED" and "G2" in r["why"]))

    # vacuous tol below noise -> UNPINNED G1
    _, r = pin("vacuous", tol=1e-9, noise=1e-6, signal=0.2)
    checks.append(("tol<noise G1 UNPINNED", r["verdict"] == "UNPINNED" and not r["clauses"]["G1_quiet"]))

    # blind tol above signal -> UNPINNED G2
    _, r = pin("blind", tol=0.5, noise=1e-6, signal=0.2)
    checks.append(("tol>signal G2 UNPINNED", r["verdict"] == "UNPINNED" and not r["clauses"]["G2_fires"]))

    # tight band: real separation but ratio < band -> honest UNPINNED G4
    _, r = pin("tight", tol=0.05, noise=0.05, signal=0.15, band=4)
    checks.append(("tight-ratio G4 UNPINNED", r["verdict"] == "UNPINNED" and not r["clauses"]["G4_witness"]))

    # fail-loud battery
    for tag, kw in (("nan-tol", {"tol": float("nan"), "noise": 1e-6, "signal": 0.2}),
                    ("zero-noise", {"tol": 0.05, "noise": 0.0, "signal": 0.2}),
                    ("neg-signal", {"tol": 0.05, "noise": 1e-6, "signal": -0.2}),
                    ("bad-band", {"tol": 0.05, "noise": 1e-6, "signal": 0.2, "band": 1})):
        try:
            run_pin(**kw)
            checks.append((tag + " rc2", False))
        except ValueError:
            checks.append((tag + " rc2", True))

    failed = [t for t, ok in checks if not ok]
    print(json.dumps({"selftest": "PASS" if not failed else "FAIL",
                      "n": len(checks), "failed": failed}))
    return 0 if not failed else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tol_pin", description=__doc__.splitlines()[0])
    ap.add_argument("--tol", type=float, help="the tolerance constant under test")
    ap.add_argument("--noise", type=float, help="noise floor that must stay quiet")
    ap.add_argument("--signal", type=float, help="signal that must fire the gate")
    ap.add_argument("--band", type=float, default=DEFAULT_BAND, help="min signal/noise ratio (default 4)")
    ap.add_argument("--name", default="", help="label for the gate being pinned")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--example", action="store_true", help="run the docstring worked example")
    ap.add_argument("--selftest", action="store_true", help="run the self-test battery")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()
    try:
        if a.example:
            r = run_pin(tol=0.05, noise=1e-6, signal=0.2, name="docstring-example")
        else:
            missing = [k for k, v in (("tol", a.tol), ("noise", a.noise), ("signal", a.signal)) if v is None]
            if missing:
                ap.error("missing required args: " + ", ".join("--" + m for m in missing))
            r = run_pin(tol=a.tol, noise=a.noise, signal=a.signal,
                        band=a.band, name=a.name)
    except ValueError as e:
        print(json.dumps({"tool": "tol_pin", "verdict": "FAIL-INPUT", "rc": 2,
                          "why": str(e)}))
        return 2
    _emit(r, a.out)
    return r["rc"]


if __name__ == "__main__":
    sys.exit(main())
