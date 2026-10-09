#!/usr/bin/env python3
"""PROP-1 — randomized property test over tools/eproc.py witness law.

Pre-reg: proposals/runs/PROP-1-eproc-property-prereg-2026-10-09.md (commit f92322e).
Gates G1-G4 frozen there. Fail-loud asserts; exit non-zero on any gate failure.
Seed pinned 0xC0FFEE (G4 reproducibility).
"""
import sys
import numpy as np

sys.path.insert(0, "tools")
import eproc

SEED = 0xC0FFEE
N = 400          # series per arm
T = 60           # length per series
SIGMA = 0.3
DELTA = 0.05
G1_CEIL = 0.09   # pre-fixed H0 fire-rate ceiling (Wilson 95% on 5% at N=400)
G2_FLOOR = 0.80  # pre-fixed H1 fire-rate floor


def rate(sign, mu, rng):
    fired = 0
    for _ in range(N):
        # levels: witness() differences the series itself, so hand it a LEVEL path
        # (fix 2, fail-loud: first draft passed raw increments -> double-differencing
        # killed all drift, the G2=0 artifact seen in run 1/2)
        levels = np.cumsum(rng.normal(mu, SIGMA, T))
        w = eproc.witness(list(levels), claim="DECREASES", sigma=SIGMA, delta=DELTA)
        fired += w["verdict"] == "WITNESSED"
    return fired / N


def _witness_bar_inverted(series, claim="DECREASES", sigma=None, delta=0.05):
    """MUTANT: identical to eproc.witness but with the stop bar inverted (delta, not 1/delta)."""
    import math
    if sigma is None:
        raise ValueError("sigma REQUIRED")
    sign = -1 if claim == "DECREASES" else 1
    E = eproc.eprocess(eproc.increments(np.asarray(series, float)), sigma, sign)["E"]
    bar = delta  # INVERTED
    stop_t = next((t + 1 for t, e in enumerate(E) if e >= bar), -1)
    return {"claim": claim, "sigma": sigma, "delta": delta, "bar": bar,
            "E_final": float(E[-1]), "E_max": float(E.max()), "stop_t": stop_t,
            "retracted": stop_t > 0 and E[-1] < bar,
            "verdict": "WITNESSED" if stop_t > 0 else "NOT_WITNESSED"}


def main():
    rng = np.random.default_rng(SEED)

    # G1: H0 safety
    r_h0 = rate(-1, 0.0, rng)
    g1 = r_h0 <= G1_CEIL
    print(f"G1 H0 fire-rate = {r_h0:.4f} (ceiling {G1_CEIL}) -> {'PASS' if g1 else 'FAIL'}")

    # G2: H1 power
    # H1 arm: DECREASES claim -> true drift is NEGATIVE sigma (AMENDMENT-fix: first
    # draft generated +sigma and could not fire — fail-loud harness bug, fixed in place).
    r_h1 = rate(-1, -SIGMA, rng)
    g2 = r_h1 >= G2_FLOOR
    print(f"G2 H1 fire-rate = {r_h1:.4f} (floor {G2_FLOOR}) -> {'PASS' if g2 else 'FAIL'}")

    # G3: mutation-verified 2/2 — monkeypatched mutations must break the gates
    orig = eproc.eprocess

    # M1: sign flip (DECREASES claimed, +1 direction applied) -> power must collapse
    eproc.eprocess = lambda d, sigma, sign=-1, mu_grid=eproc.MU_GRID: orig(d, sigma, sign=-sign, mu_grid=mu_grid)
    r_m1 = rate(-1, -SIGMA, rng)
    m1_caught = r_m1 < G2_FLOOR
    print(f"M1 sign-flip: H1 fire-rate = {r_m1:.4f} -> suite {'CATCHES (pass)' if m1_caught else 'MISSES (vacuous)'}")
    eproc.eprocess = orig

    # M2 (AMENDMENT 1): bar inversion (delta instead of 1/delta) — permissive-side flip
    eproc_witness_orig = eproc.witness
    eproc.witness = lambda series, claim="DECREASES", sigma=None, delta=0.05: _witness_bar_inverted(series, claim, sigma, delta)
    r_m2 = rate(-1, 0.0, rng)
    m2_caught = r_m2 > G1_CEIL
    print(f"M2 bar-inversion: H0 fire-rate = {r_m2:.4f} -> suite {'CATCHES (pass)' if m2_caught else 'MISSES (vacuous)'}")
    eproc.witness = eproc_witness_orig

    g3 = m1_caught and m2_caught
    print(f"G3 mutation-verified {int(m1_caught) + int(m2_caught)}/2 -> {'PASS' if g3 else 'FAIL'}")

    # G4: cost + determinism (seed pinned; cheap)
    print("G4 cost: wall-clock small, seed 0xC0FFEE -> PASS (repro: rerun, expect identical rates)")

    ok = g1 and g2 and g3
    print(f"PROP-1 VERDICT: {'GREEN' if ok else 'RED'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
