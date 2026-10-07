#!/usr/bin/env python3
"""gen-audit — generator-fidelity audit (pattern lifted PROVEN from D12x,
booked 2026-10-06/07: D12u3's partner corr read 0.605 at nominal p=0.7 and the
question "is the generator lying or is it sampling noise" needed its own
answer — the generator is a measurement target too).

Given a copy-prob ±1 partner-stream generator (partner pairs share atoms with
prob p, the D12x/D12u4 family), audit that the measured centered-cosine |corr|
actually lands on the nominal p:

  G1 (fidelity): mean |corr| over D independent partner draws within
      p +- k/sqrt(T*W)  (the D12x gate form; k=3 default)
  G2 (null control): null-pair mean |corr| strictly positive (finite-sample
      positive bias of |corr| must be visible) AND null_mean < p/4 (bias is
      small, not masking a broken signal)

Stdlib-only, seeded, fail-loud rc=2, JSON receipt. Exit 0=PASS, 1=FAIL,
2=fail-loud input. A corrupted generator is the RED control — the audit is
trusted only if it fires on one.

Worked example (faithful generator at p=0.7, T=800, W=8):
    python tools/gen_audit.py --p 0.7 --t 800 --w 8 --draws 300 --out r.json
Corrupted control (generator silently copies at p-0.1):
    python tools/gen_audit.py --p 0.7 --t 800 --w 8 --draws 300 --actual 0.6
"""
import argparse
import json
import math
import random
import sys
import time

def _fail(msg):
    print(json.dumps({"tool": "gen-audit", "status": "FAIL-INPUT", "error": msg}), file=sys.stderr)
    sys.exit(2)

def draw_pair_corr(T, W, p, rng):
    """One independent partner pair -> centered-cosine |corr| (D12x estimator)."""
    a = [1.0 if rng.random() < 0.5 else -1.0 for _ in range(T * W)]
    b = list(a)
    # independent atoms where copy did NOT happen
    b = [x if rng.random() < p else (1.0 if rng.random() < 0.5 else -1.0)
         for x in a]
    ma = sum(a) / len(a); mb = sum(b) / len(b)
    fa = [x - ma for x in a]; fb = [x - mb for x in b]
    na = math.sqrt(sum(x * x for x in fa)); nb = math.sqrt(sum(x * x for x in fb))
    if na == 0 or nb == 0:
        return 0.0
    return abs(sum(x * y for x, y in zip(fa, fb)) / (na * nb))

def run_audit(p, T, W, draws, k, actual=None, seed=2718):
    for name, v in (("p", p), ("t", T), ("w", W), ("draws", draws), ("k", k)):
        if not isinstance(v, (int, float)) or v != v or v in (float("inf"), float("-inf")):
            _fail(f"{name} must be finite")
    if not (0 < p < 1):
        _fail("p must be in (0,1) exclusive")
    if actual is not None and not (0 < actual < 1):
        _fail("actual must be in (0,1) exclusive")
    if T < 4 or W < 1 or draws < 30 or k <= 0:
        _fail("need t>=4, w>=1, draws>=30, k>0")
    p_gen = actual if actual is not None else p
    rng = random.Random(seed)
    cs = [draw_pair_corr(T, W, p_gen, rng) for _ in range(draws)]
    ns = [draw_pair_corr(T, W, 0.0, rng) for _ in range(min(200, draws))]
    mean = sum(cs) / len(cs)
    sd = math.sqrt(sum((x - mean) ** 2 for x in cs) / len(cs))
    nmean = sum(ns) / len(ns)
    sigma = 1.0 / math.sqrt(T * W)
    g1 = abs(mean - p) <= k * sigma
    g2 = nmean > 0 and nmean < p / 4
    verdict = "PASS" if (g1 and g2) else "FAIL"
    return {
        "tool": "gen-audit",
        "p": p, "T": T, "W": W, "draws": draws, "k": k,
        "actual_gen_p": p_gen, "seed": seed,
        "corr_mean": mean, "corr_sd": sd,
        "null_mean": nmean, "sigma": sigma,
        "window": [p - k * sigma, p + k * sigma],
        "G1_fidelity": g1, "G2_null_control": g2,
        "verdict": verdict, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

def selftest():
    checks = []
    # 1. faithful generator PASSES
    r = run_audit(0.7, 800, 8, 300, 3)
    checks.append(("faithful-PASS", r["verdict"] == "PASS"))
    # 2. corrupted generator FAILS G1 (RED control — the audit must fire)
    r2 = run_audit(0.7, 800, 8, 300, 3, actual=0.6)
    checks.append(("corrupt-RED", r2["verdict"] == "FAIL" and not r2["G1_fidelity"]))
    # 3. determinism: same seed -> bit-identical stats
    r3 = run_audit(0.4, 200, 8, 100, 3)
    r4 = run_audit(0.4, 200, 8, 100, 3)
    checks.append(("determinism", r3["corr_mean"] == r4["corr_mean"]))
    # 4. fail-loud: bad p (0.5 is VALID — corr 0; use 0.0)
    try:
        run_audit(0.0, 800, 8, 100, 3)
        checks.append(("p0.5-fail-loud", False))
    except SystemExit as e:
        checks.append(("p0-fail-loud", e.code == 2))
    # 5. fail-loud: draws too few
    try:
        run_audit(0.7, 800, 8, 10, 3)
        checks.append(("draws-fail-loud", False))
    except SystemExit as e:
        checks.append(("draws-fail-loud", e.code == 2))
    ok = all(v for _, v in checks)
    print(json.dumps({"selftest": "OK" if ok else "FAIL",
                      "checks": {n: v for n, v in checks}}))
    sys.exit(0 if ok else 1)

def main():
    ap = argparse.ArgumentParser(description="Generator-fidelity audit (D12x pattern)")
    ap.add_argument("--p", type=float, help="nominal copy-prob")
    ap.add_argument("--t", type=int, default=800, help="stream length (default 800)")
    ap.add_argument("--w", type=int, default=8, help="streams per snapshot (default 8)")
    ap.add_argument("--draws", type=int, default=300, help="independent partner draws (default 300)")
    ap.add_argument("--k", type=float, default=3.0, help="gate half-width in sigmas (default 3)")
    ap.add_argument("--actual", type=float, default=None, help="RED control: generator's true p")
    ap.add_argument("--seed", type=int, default=2718)
    ap.add_argument("--out", help="receipt JSON path")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    if a.p is None:
        _fail("--p required (or --selftest)")
    r = run_audit(a.p, a.t, a.w, a.draws, a.k, actual=a.actual, seed=a.seed)
    if a.out:
        with open(a.out, "w") as f:
            json.dump(r, f, indent=2)
    print(json.dumps(r))
    sys.exit(0 if r["verdict"] == "PASS" else 1)

if __name__ == "__main__":
    main()
