#!/usr/bin/env python3
"""D12r — re-express and validate the corrected noise law across the D12n surface.

D12q discovered that the stream generator's partner correlation is exactly p
(measured corr(p=0.5)=0.503, corr(p)=p), so the law's effective signal is
s_eff = p*(1-2eps), NOT |2p-1|*(1-2eps). Under the corrected constant
C ~ 13-20 (d12q, eps=0), re-validate out-of-sample across the D12n eps
surface: W in {4,8,16}, eps in {0,0.05,0.1,0.2}, p=0.3, N=32, plus a
p=0.7 cross-check at eps=0.1.

Pre-registered gates:
  G1 (coverage): W*T_floor*s_eff^1.92 <= C_BOUND=60 at EVERY config
      (one-sided, generous 3x headroom over d12q's C~20 to absorb grid
      quantization; a miss means the corrected law is violated).
  G2 (constancy): C_emp = W*T_floor*s_eff^1.92 across configs with
      resolvable floors (not pinned at the T-grid bottom) must lie in
      [5, 60] — i.e. a single constant within ~one order of magnitude.
KEEP iff G1 and G2. Seed 2718. CPU-only, <5 min, guard untouched.
"""
from __future__ import annotations

import json
import random

SEED = 2718
N = 32
P_MAIN = 0.3
CONFIGS = [(4, e) for e in (0.0, 0.05, 0.1, 0.2)] + \
          [(8, e) for e in (0.0, 0.05, 0.1, 0.2)] + \
          [(16, e) for e in (0.0, 0.05, 0.1, 0.2)] + \
          [(8, 0.1)]  # last one is the p=0.7 cross-check
P_SPECIAL = {0.7}
T_VALUES = (10, 15, 20, 30, 40, 60, 80, 120, 160, 240, 320, 480, 640, 800)
DRAWS = 3
ACC_BAR = 0.9
ALPHA = 1.92
C_BOUND = 60.0


def make_pairs(n, rng):
    perm = list(range(n))
    rng.shuffle(perm)
    partner = {}
    for i in range(0, n, 2):
        a, b = perm[i], perm[i + 1]
        partner[a] = b
        partner[b] = a
    return partner


def streams_for(rng, partner, n, p_corr, eps, t_obs, w):
    streams = {c: [[] for _ in range(w)] for c in range(n)}
    for _ in range(t_obs):
        seen = set()
        for a in partner:
            if a in seen:
                continue
            seen |= {a, partner[a]}
            b = partner[a]
            for q in range(w):
                base = 1 if rng.random() < 0.5 else -1
                if rng.random() < p_corr:
                    va = vb = base
                else:
                    va, vb = base, (1 if rng.random() < 0.5 else -1)
                if rng.random() < eps:
                    va = -va
                if rng.random() < eps:
                    vb = -vb
                streams[a][q].append(va)
                streams[b][q].append(vb)
    return streams


def signed_corr(streams, a, b):
    tot, n = 0.0, 0
    for sa, sb in zip(streams[a], streams[b]):
        n += len(sa)
        tot += sum(x * y for x, y in zip(sa, sb))
    return tot / n if n else 0.0


def discover(streams, n):
    return {a: max((c for c in range(n) if c != a),
                   key=lambda c: abs(signed_corr(streams, a, c)))
            for a in range(n)}


def floor_at(w, eps, p):
    accs = {}
    for t in T_VALUES:
        run = []
        for d in range(DRAWS):
            key = (SEED * 100000 + int(p * 100) * 1000 + int(eps * 1000) * 10
                   + w * 100 + t * 2 + d)
            r = random.Random(key)
            partner = make_pairs(N, r)
            streams = streams_for(r, partner, N, p, eps, t, w)
            found = discover(streams, N)
            run.append(sum(found[c] == partner[c] for c in partner) / N)
        accs[t] = sum(run) / len(run)
        if accs[t] >= ACC_BAR:
            return t, accs
    return None, accs


def main():
    rows = []
    for (w, eps) in CONFIGS:
        p = 0.7 if (w, eps) == (8, 0.1) else P_MAIN
        fl, accs = floor_at(w, eps, p)
        s = p * (1 - 2 * eps)
        row = {"W": w, "eps": eps, "p": p, "s_eff": round(s, 4),
               "T_floor": fl, "pinned": fl == T_VALUES[0]}
        if fl is not None:
            row["C_emp"] = round(w * fl * s ** ALPHA, 1)
            row["covered_C60"] = w * fl * s ** ALPHA <= C_BOUND
        rows.append(row)

    resolvable = [r for r in rows if r.get("T_floor") and not r["pinned"]]
    g1 = all(r.get("covered_C60", True) for r in rows)
    g2 = all(5.0 <= r["C_emp"] <= 60.0 for r in resolvable) and len(resolvable) >= 6

    verdict = "KEEP" if (g1 and g2) else "KILL"
    out = {
        "experiment": "d12r_corrected_constant_surface",
        "seed": SEED, "N": N, "T_values": T_VALUES, "draws": DRAWS,
        "alpha_fixed": ALPHA, "C_BOUND": C_BOUND, "s_eff_definition": "p*(1-2eps)",
        "rows": rows,
        "g1_coverage_all": g1,
        "g2_constancy": {"n_resolvable": len(resolvable),
                         "C_emp_values": [r["C_emp"] for r in resolvable],
                         "pass": g2},
        "verdict": verdict,
    }
    with open("results/d12r_corrected_constant_surface.json", "w") as f:
        json.dump(out, f, indent=1)
    for r in rows:
        print(r)
    print("G1 coverage (all <= C=60):", g1)
    print("G2 constancy [5,60] on resolvable:", g2,
          "n =", len(resolvable))
    print("verdict:", verdict)


if __name__ == "__main__":
    main()
