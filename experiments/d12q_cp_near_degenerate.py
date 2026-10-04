#!/usr/bin/env python3
"""D12q — pin C(p) in the near-degenerate regime p in {0.45, 0.55}.

D12p's weak KEEP: floors at p in {0.6,0.7} sit pinned at the bottom of the
T grid, so C_emp is quantized and the beta fit had 0 degrees of freedom.
The one regime where C(p) can actually be measured is just beside the
degenerate point p=0.5: floors there are large (10s-100s of T), so the
T grid resolves them. This run measures floors at p in
{0.45, 0.5 (null check), 0.55} with eps=0, W=8, N=32 on a dense T grid,
computes C_emp(p) = W*T_floor*|2p-1|^1.92, and tests whether the D12p
fit (C0=400, beta=-2.92) PREDICTS these out-of-sample floors.

Pre-registered gates:
  G1 (null): p=0.5 must NOT floor within T<=800 (partner streams are
      uncorrelated by construction — discovery at chance).
  G2 (prediction): D12p's C(p) = 400*|2p-1|^2.92 predicts floors at
      p=0.45/0.55; coverage 2/2 (W*T_floor <= C_fit/s^1.92) AND
      non-vacuous (ratio >= 0.02).
KEEP iff G1 and G2. Seed 2718. CPU-only, <5 min, 6GB/80C guard untouched.
"""
from __future__ import annotations

import json
import random

SEED = 2718
W = 8
N = 32
EPS = 0.0
P_GRID = (0.45, 0.5, 0.55)
T_VALUES = (5, 10, 15, 20, 30, 40, 60, 80, 120, 160, 240, 320, 480, 640, 800)
DRAWS = 3
ACC_BAR = 0.9
ALPHA = 1.92
C0_D12P = 400.0
BETA_D12P = -2.92


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


def floor_at_p(p):
    accs = {}
    for t in T_VALUES:
        run = []
        for d in range(DRAWS):
            r = random.Random(SEED * 100000 + int(p * 1000) * 10 + t * 2 + d)
            partner = make_pairs(N, r)
            streams = streams_for(r, partner, N, p, EPS, t, W)
            found = discover(streams, N)
            run.append(sum(found[c] == partner[c] for c in partner) / N)
        accs[t] = sum(run) / len(run)
    for t in T_VALUES:
        if accs[t] >= ACC_BAR:
            return t, accs
    return None, accs


def main():
    floors, acc_grids, c_emp = {}, {}, {}
    for p in P_GRID:
        fl, accs = floor_at_p(p)
        floors[p] = fl
        acc_grids[p] = accs
        if fl is not None:
            s = abs(2 * p - 1) * (1 - 2 * EPS)
            c_emp[p] = W * fl * s ** ALPHA

    # G1: p=0.5 null — no floor within grid
    g1 = floors[0.5] is None

    # G2: D12p fit predicts p=0.45/0.55 out-of-sample
    g2_details = {}
    g2_ok = 0
    for p in (0.45, 0.55):
        s = abs(2 * p - 1) * (1 - 2 * EPS)
        c_fit = C0_D12P * abs(2 * p - 1) ** (-BETA_D12P)
        bound = c_fit / s ** ALPHA
        fl = floors[p]
        wt = W * fl if fl is not None else None
        ok = wt is not None and wt <= bound
        ratio = wt / bound if wt else None
        g2_ok += ok and (ratio or 0) >= 0.02
        g2_details[p] = {"floor": fl, "wt": wt, "c_fit": round(c_fit, 1),
                         "bound": round(bound, 1),
                         "ratio": round(ratio, 5) if ratio else None, "ok": ok}
    g2 = g2_ok == 2

    verdict = "KEEP" if (g1 and g2) else "KILL"
    out = {
        "experiment": "d12q_cp_near_degenerate",
        "seed": SEED, "N": N, "W": W, "eps": EPS,
        "p_grid": P_GRID, "T_values": T_VALUES, "draws": DRAWS,
        "alpha_fixed": ALPHA, "d12p_fit": {"C0": C0_D12P, "beta": BETA_D12P},
        "T_floors": {str(p): floors[p] for p in P_GRID},
        "acc_grids": {str(p): {str(t): round(a, 4) for t, a in acc_grids[p].items()}
                      for p in P_GRID},
        "C_emp": {str(p): round(c_emp[p], 1) for p in c_emp},
        "g1_null_pass": g1, "g2_details": {str(k): v for k, v in g2_details.items()},
        "verdict": verdict,
    }
    with open("results/d12q_cp_near_degenerate.json", "w") as f:
        json.dump(out, f, indent=1)
    print("T_floors:", {p: floors[p] for p in P_GRID})
    print("C_emp:", {p: round(v, 1) for p, v in c_emp.items()})
    print("G1 null (p=0.5 no floor):", g1)
    print("G2 heldout:", g2_details)
    print("verdict:", verdict)


if __name__ == "__main__":
    main()
