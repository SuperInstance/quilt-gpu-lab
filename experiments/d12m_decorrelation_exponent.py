#!/usr/bin/env python3
"""D12m — decorrelation-exponent refit of the noise-damage law.

D12l found the naive product bound W*T <= 600/s^2 (s = (2p-1)(1-2eps)) FAILS at
high eps: noise hurts slower than 1/s^2, hypothesized because a flipped atom
preserves |corr| through its sign-squared contribution — i.e. the effective
decorrelation exponent alpha < 2. This experiment fits alpha directly.

Method: at each (W, eps), measure T_floor on a fine T grid, then fit
    W * T_floor = C / s^alpha
in log space across the eps axis (per W), for both the naive s=(2p-1)(1-2eps)
and a corrected signal-under-flipping model s_c = (2p-1)*(1-2eps)^2... — but the
cleaner move is agnostic: fit log(T_floor) = log(C') - alpha*log(s) + beta*log(W)
and report alpha per model of s. ALSO measure the actual |corr| of partner
streams empirically at each eps and fit alpha against the EMPIRICAL correlation
magnitude: if |corr_partner|(eps) decays as (1-2eps)^alpha_emp, that IS the
decorrelation exponent — measurable exactly, no discovery noise.

Pre-registered gate: the empirical decorrelation exponent alpha_emp, measured as
the log-log slope of |corr_partner| vs (1-2eps), must satisfy alpha_emp <= 1.5
(KILL of the 1/s^2 bound is confirmed real, not a floor-grid artifact) and the
naive bound with s^alpha_emp must then cover >= 9/10 of the (W,eps) floor cells.
Seed 2718. CPU-only, < 1 min, no GPU — 6GB/80C guard untouched.
"""
from __future__ import annotations

import json
import math
import random

SEED = 2718
W_VALUES = (4, 8)
N = 16
P = 0.3
EPS_VALUES = (0.0, 0.05, 0.10, 0.20, 0.30)
T_VALUES = (10, 25, 50, 100, 200, 400, 800)
DRAWS = 3
ACC_BAR = 0.9


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
        tot += sum(sa[i] * sb[i] for i in range(len(sa)))
    return tot / n if n else 0.0


def discover(streams, n):
    return {a: max((c for c in range(n) if c != a),
                   key=lambda c: abs(signed_corr(streams, a, c)))
            for a in range(n)}


def main():
    rng = random.Random(SEED)
    # --- Part 1: empirical decorrelation exponent (exact, big T, no discovery) ---
    T_BIG = 20000
    emp = {}
    for eps in EPS_VALUES:
        # partner-stream correlation with clean pairing at p=1 reference and at p=0.3
        for p in (1.0, P):
            vals = []
            for d in range(20):
                r = random.Random(SEED * 7 + int(eps * 100) + d)
                a = [1 if r.random() < 0.5 else -1 for _ in range(T_BIG)]
                b = []
                for x in a:
                    if r.random() < p:
                        b.append(x)
                    else:
                        b.append(1 if r.random() < 0.5 else -1)
                # flip noise
                a = [-x if r.random() < eps else x for x in a]
                b = [-x if r.random() < eps else x for x in b]
                m = sum(x * y for x, y in zip(a, b)) / T_BIG
                vals.append(m)
            emp[f"p={p}"] = sum(vals) / len(vals)

    out = {}

    # Empirical partner correlation, keyed by eps
    emp2 = {}
    for eps in EPS_VALUES:
        vals = []
        for d in range(20):
            r = random.Random(SEED * 7 + int(eps * 100) + d)
            a = [1 if r.random() < 0.5 else -1 for _ in range(T_BIG)]
            b = []
            for x in a:
                if r.random() < P:
                    b.append(x)
                else:
                    b.append(1 if r.random() < 0.5 else -1)
            a = [-x if r.random() < eps else x for x in a]
            b = [-x if r.random() < eps else x for x in b]
            vals.append(sum(x * y for x, y in zip(a, b)) / T_BIG)
        emp2[eps] = sum(vals) / len(vals)

    xs = [math.log(1 - 2 * e) for e in EPS_VALUES[1:]]
    ys = [math.log(abs(emp2[e]) / abs(emp2[0.0])) for e in EPS_VALUES[1:]]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    alpha_emp = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / \
        sum((x - mx) ** 2 for x in xs)

    # --- Part 2: fine-grid T floors, same harness as D12l but T up to 800 ---
    grid = {}
    for w in W_VALUES:
        for eps in EPS_VALUES:
            for t in T_VALUES:
                accs = []
                for d in range(DRAWS):
                    r = random.Random(SEED * 100000 + w * 1000 + int(eps * 100) * 10 + t * 2 + d)
                    partner = make_pairs(N, r)
                    streams = streams_for(r, partner, N, P, eps, t, w)
                    found = discover(streams, N)
                    accs.append(sum(found[c] == partner[c] for c in partner) / N)
                grid[f"{w}|{eps}|{t}"] = sum(accs) / len(accs)

    floors = {}
    for w in W_VALUES:
        for eps in EPS_VALUES:
            floor = None
            for t in T_VALUES:
                if grid[f"{w}|{eps}|{t}"] >= ACC_BAR:
                    floor = t
                    break
            floors[f"W={w},eps={eps}"] = floor

    # Gate: alpha_emp <= 1.5 confirms slow decorrelation; refit bound coverage
    s_base = (2 * P - 1)
    covered = 0
    cells = 0
    for w in W_VALUES:
        for e in EPS_VALUES:
            fl = floors[f"W={w},eps={e}"]
            if fl is None:
                cells += 1
                continue
            cells += 1
            bound = 600 / abs(s_base * (1 - 2 * e)) ** alpha_emp
            if w * fl <= bound:
                covered += 1
    coverage = covered / cells
    g1 = alpha_emp <= 1.5
    g2 = coverage >= 0.9
    verdict = "KEEP" if (g1 and g2) else "KILL"

    out = {
        "experiment": "d12m_decorrelation_exponent",
        "seed": SEED, "N": N, "p_corr": P, "W": W_VALUES, "eps": EPS_VALUES,
        "T_values": T_VALUES, "draws": DRAWS, "acc_bar": ACC_BAR,
        "empirical_partner_corr_by_eps": {str(e): emp2[e] for e in EPS_VALUES},
        "alpha_empirical": alpha_emp,
        "T_floors": floors,
        "acc_grid": grid,
        "gate1_alpha_leq_1p5": g1,
        "gate2_refit_coverage": coverage,
        "verdict": verdict,
    }
    with open("results/d12m_decorrelation_exponent.json", "w") as f:
        json.dump(out, f, indent=1)
    print("empirical |corr| by eps:", {e: round(emp2[e], 4) for e in EPS_VALUES})
    print("alpha_emp:", round(alpha_emp, 4))
    print("T_floors:", floors)
    print("refit coverage:", coverage, f"({covered}/{cells})")
    print("verdict:", verdict)


if __name__ == "__main__":
    main()
