#!/usr/bin/env python3
"""law_ks_gate.py — two-sample KS law-fidelity gate (stdlib-only).

Pattern lifted from the W8b/W9a law-check doctrine and PIDFIRE-1's self-KS
tau bracket: when you own the generator, drift is *exactly* measurable —
resample the reference from the generator and compare with a two-sample
Kolmogorov-Smirnov gate. Observed sample vs generator-resampled reference;
KEEP iff D <= bar AND permutation p >= alpha (seeded, exact when C(na+nb,na)
is small), with a keep-both-clauses rule: either clause failing books FAIL.
Degenerate input (empty/constant-degenerate samples, mismatched dims) fails
loud rc=2. Nulls and FAILs are first-class, never retried until PASS.

Worked example (deterministic):
    python tools/law_ks_gate.py \
        --a 0.12,0.31,0.27,0.44,0.19,0.38,0.22,0.41 \
        --b 0.10,0.33,0.29,0.47,0.16,0.36,0.25,0.43,0.21,0.39 \
        --bar 0.4 --alpha 0.05
    -> KEEP rc=0 (same law, small D)
    python tools/law_ks_gate.py --a 0,0,0,0,1,1,1,1 \
        --b 0.45,0.55,0.40,0.60,0.48,0.52,0.43,0.57 --bar 0.4 --alpha 0.05
    -> FAIL rc=1 (bimodal vs uniform — D at the mid-gap, p small)

CLI:
    --a LIST            comma-separated observed sample (floats)
    --b LIST            comma-separated reference sample (floats)
    --a-file/--b-file   newline-separated floats (one per line)
    --bar F             max KS statistic (default 0.4)
    --alpha F           min permutation p (default 0.05)
    --draws N           MC permutation draws when exact is infeasible (default 4000)
    --seed N            rng seed (default 7)
    --out PATH          write JSON receipt
    --selftest          run the pin battery (controls + fail-loud), rc=0 iff all pass
"""
import argparse
import json
import math
import os
import random
import sys
from itertools import combinations

EXIT_KEEP, EXIT_FAIL, EXIT_LOUD = 0, 1, 2


def ks_stat(a, b):
    """Two-sample KS statistic D = sup |F_a - F_b| (floats)."""
    sa, sb = sorted(a), sorted(b)
    i = j = 0
    d = 0.0
    na, nb = len(sa), len(sb)
    while i < na or j < nb:
        if i < na and j < nb and sa[i] == sb[j]:
            i += 1
            j += 1
        elif j >= nb or (i < na and sa[i] < sb[j]):
            i += 1
        else:
            j += 1
        d = max(d, abs(i / na - j / nb))
    return d


def ks_pvalue(a, b, draws=4000, seed=7):
    """Exact permutation p when C(na+nb,na) small, else seeded MC (add-one)."""
    pool = list(a) + list(b)
    na = len(a)
    obs = ks_stat(a, b)
    n = len(pool)
    nc = math.comb(n, na) if n - na <= na else math.comb(n, n - na)
    if nc <= 20000:
        count = 0
        total = 0
        for idx in combinations(range(n), na):
            sa = [pool[k] for k in idx]
            sb = [pool[k] for k in range(n) if k not in set(idx)]
            total += 1
            if ks_stat(sa, sb) >= obs - 1e-12:
                count += 1
        return count / total
    rng = random.Random(seed)
    count = 0
    for _ in range(draws):
        samp = rng.sample(pool, na)
        sb = [pool[k] for k in rng.sample(range(n), n - na)]
        # complement via remaining multiset
        rest = pool[:]
        for x in samp:
            rest.remove(x)
        if ks_stat(samp, rest) >= obs - 1e-12:
            count += 1
    return (count + 1) / (draws + 1)


def _parse_floats(text, name):
    try:
        vals = [float(t) for t in text.replace(";", ",").split(",") if t.strip()]
    except ValueError as e:
        raise SystemExit(f"FAIL-INPUT: {name} not comma-separated floats: {e}")
    if not vals:
        raise SystemExit(f"FAIL-INPUT: {name} empty")
    for v in vals:
        if not math.isfinite(v):
            raise SystemExit(f"FAIL-INPUT: {name} contains non-finite value")
    return vals


def run_gate(a, b, bar, alpha, draws, seed):
    if not a or not b:
        raise SystemExit("FAIL-INPUT: both samples required")
    for v in list(a) + list(b):
        if not math.isfinite(v):
            raise SystemExit("FAIL-INPUT: non-finite value in samples")
    if not (0.0 < alpha <= 1.0):
        raise SystemExit("FAIL-INPUT: alpha must be in (0,1]")
    if bar <= 0 or bar > 1:
        raise SystemExit("FAIL-INPUT: bar must be in (0,1]")
    d = ks_stat(a, b)
    p = ks_pvalue(a, b, draws=draws, seed=seed)
    g1 = d <= bar
    g2 = p >= alpha
    verdict = "KEEP" if (g1 and g2) else "FAIL"
    return {
        "tool": "law_ks_gate",
        "verdict": verdict,
        "ks_d": round(d, 6),
        "p": round(p, 6),
        "g1_d_le_bar": g1,
        "g2_p_ge_alpha": g2,
        "bar": bar,
        "alpha": alpha,
        "n_a": len(a),
        "n_b": len(b),
        "seed": seed,
    }


def selftest():
    checks = 0
    fails = []
    # control 1: same-law samples -> KEEP both clauses
    rng = random.Random(11)
    a = [rng.gauss(0, 1) for _ in range(20)]
    b = [rng.gauss(0, 1) for _ in range(20)]
    r = run_gate(a, b, 0.4, 0.05, draws=3000, seed=7)
    checks += 1
    if r["verdict"] != "KEEP":
        fails.append(f"same-law control booked {r['verdict']} d={r['ks_d']} p={r['p']}")
    # control 2: shifted law -> D large, verdict FAIL
    c = [x + 2.0 for x in a]
    r2 = run_gate(a, c, 0.4, 0.05, draws=3000, seed=7)
    checks += 1
    if not (r2["ks_d"] >= 0.5 and r2["verdict"] == "FAIL"):
        fails.append(f"shifted control d={r2['ks_d']} verdict={r2['verdict']}")
    # control 3: identical samples -> D == 0, KEEP
    r3 = run_gate(a, a[:], 0.4, 0.05, draws=100, seed=7)
    checks += 1
    if r3["ks_d"] != 0.0:
        fails.append(f"identical control d={r3['ks_d']} (must be exactly 0)")
    # fail-loud: non-finite
    try:
        run_gate([float("nan")], [1.0], 0.4, 0.05, 10, 7)
        fails.append("non-finite input did not fail loud")
    except SystemExit as e:
        checks += 1
        if "FAIL-INPUT" not in str(e):
            fails.append(f"non-finite exit message wrong: {e}")
    # fail-loud: bad alpha
    try:
        run_gate([1.0], [1.0], 0.4, 0.0, 10, 7)
        fails.append("alpha=0 did not fail loud")
    except SystemExit as e:
        checks += 1
        if "FAIL-INPUT" not in str(e):
            fails.append(f"alpha=0 exit message wrong: {e}")
    # determinism: same seed -> identical p
    r4 = run_gate(a, b, 0.4, 0.05, draws=500, seed=7)
    r5 = run_gate(a, b, 0.4, 0.05, draws=500, seed=7)
    checks += 1
    if r4["p"] != r5["p"]:
        fails.append(f"non-deterministic p {r4['p']} vs {r5['p']}")
    print(json.dumps({"selftest": "OK" if not fails else "FAIL", "checks": checks,
                      "failures": fails}, indent=2))
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser(description="two-sample KS law-fidelity gate")
    ap.add_argument("--a")
    ap.add_argument("--b")
    ap.add_argument("--a-file")
    ap.add_argument("--b-file")
    ap.add_argument("--bar", type=float, default=0.4)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--draws", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())

    def load(which):
        text = getattr(args, which) 
        path = getattr(args, which + "_file")
        if text:
            return _parse_floats(text, "--" + which)
        if path:
            with open(path) as fh:
                return _parse_floats(fh.read(), "--" + which + "_file")
        raise SystemExit(f"FAIL-INPUT: --{which} or --{which}_file required")

    a, b = load("a"), load("b")
    receipt = run_gate(a, b, args.bar, args.alpha, args.draws, args.seed)
    js = json.dumps(receipt, indent=2)
    print(js)
    if args.out:
        tmp = args.out + ".tmp"
        with open(tmp, "w") as fh:
            fh.write(js + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, args.out)
    sys.exit(EXIT_KEEP if receipt["verdict"] == "KEEP" else EXIT_FAIL)


if __name__ == "__main__":
    main()
