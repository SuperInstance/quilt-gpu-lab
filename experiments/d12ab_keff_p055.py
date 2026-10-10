#!/usr/bin/env python3
"""D12ab: direct k_eff(p) at p=0.55 — midpoint of the 0.4->0.7 span.

k_eff(p) direct measurements so far: 0.657@0.3, 0.896@0.4, 1.200@0.7 (D12u1/u5/aa2).
Linear interpolation at p=0.55 predicts k ~ 0.657 + (1.2-0.657)*(0.55-0.3)/(0.7-0.3) = 0.996.
This run: (1) harness discovery floors at p=0.55, (2) bisect k_eff(0.55) directly
against those floors with the calibrated order-statistics model.

Seed 2718. CPU-only. Guard untouched.
"""
import json, math, os
import numpy as np

SEED = 2718
rng = np.random.default_rng(SEED)

N_CELLS = 64
N_PAIRS = N_CELLS // 2
P = 0.55
W_LIST = [4, 8]
EPS_LIST = [0.0, 0.05, 0.1, 0.2]
DRAWS = 5
T_GRID = [2, 3, 4, 6, 8, 10, 15, 20, 30, 40, 60, 80, 120, 160, 240, 320, 400]
ACC_BAR = 0.9

ALPHA = 1.92          # corr-decay exponent (D12m)
THRESH = 0.5          # discovery threshold in MC model
MC_DRAWS = 20000


def gen_streams(T, W, n_pairs, p, rng):
    """Correlated-branch generator: with prob p partner copies the atom, else independent."""
    a = rng.integers(0, 2, size=(n_pairs, T, W)).astype(np.float64) * 2 - 1
    copy_mask = rng.random((n_pairs, T, 1)) < p
    b_indep = rng.integers(0, 2, size=(n_pairs, T, W)).astype(np.float64) * 2 - 1
    b = np.where(copy_mask, a, b_indep)
    return np.concatenate([a, b], axis=0)  # 2*n_pairs cells; partner of i is i+n_pairs, B-streams are the null pool


def corr_matrix(streams):
    """Centered cosine correlation between all pairs of cells, pooled over (T,W)."""
    flat = streams.reshape(streams.shape[0], -1)
    c = flat - flat.mean(axis=1, keepdims=True)
    n = np.linalg.norm(c, axis=1, keepdims=True)
    n[n == 0] = 1e-12
    cn = c / n
    return cn @ cn.T


def partner_id_acc(T, W, eps, rng):
    """Add measurement noise eps (atom flips post-generation), run max-|corr| discovery."""
    hits = 0
    for _ in range(DRAWS):
        s = gen_streams(T, W, N_PAIRS, P, rng)
        if eps > 0:
            flip = rng.random(s.shape) < eps
            s = np.where(flip, -s, s)
        C = np.abs(corr_matrix(s))
        np.fill_diagonal(C, -1)
        pred = np.argmax(C, axis=1)
        hits += sum(1 for i in range(N_PAIRS) if pred[i] == i + N_PAIRS and pred[i + N_PAIRS] == i)
    return hits / (DRAWS * N_PAIRS)


def harness_floors():
    floors = {}
    for W in W_LIST:
        for eps in EPS_LIST:
            floor = None
            accs = []
            for T in T_GRID:
                acc = partner_id_acc(T, W, eps, rng)
                accs.append((T, round(acc, 3)))
                if acc >= ACC_BAR and floor is None:
                    floor = T
            floors[(W, eps)] = {"floor": floor, "acc_curve": accs}
    return floors


def model_floor(W, eps, k):
    """MC order-statistics model floor: partner ~ N(s^ALPHA, (k/sqrt(W*T))^2), nulls ~ N(0, same)."""
    s_eff = P * (1 - 2 * eps)
    c = s_eff ** ALPHA
    def p_disc(T):
        sigma = k / math.sqrt(W * T)
        draws = rng.standard_normal(MC_DRAWS)
        partner = c + sigma * rng.standard_normal(MC_DRAWS)
        nulls = sigma * rng.standard_normal((MC_DRAWS, N_CELLS - 2))
        return float(np.mean(partner > nulls.max(axis=1)))
    lo, hi = 0.5, 2000.0
    if p_disc(hi) < THRESH:
        return None
    for _ in range(40):
        mid = (lo + hi) / 2
        if p_disc(mid) >= THRESH:
            hi = mid
        else:
            lo = mid
    return hi


def bisect_k(W, eps, h_floor):
    """Find k such that model floor == harness floor."""
    if h_floor is None:
        return None
    def f(k):
        mf = model_floor(W, eps, k)
        if mf is None:
            return 1.0  # model floor beyond T_max: above harness, need smaller k
        return mf - h_floor
    # model floor INCREASES with k (larger null sigma -> harder discovery)
    lo, hi = 0.05, 8.0
    if f(lo) > 0:
        return lo  # even tiny k puts floor above harness
    if f(hi) < 0:
        return hi
    for _ in range(30):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def main():
    # linear interpolation from direct anchors (0.3, 0.657) and (0.7, 1.200)
    k_interp = 0.657 + (1.200 - 0.657) * (P - 0.3) / (0.7 - 0.3)
    floors = harness_floors()
    implied = {}
    model_floors = {}
    for (W, eps), d in floors.items():
        implied[(W, eps)] = bisect_k(W, eps, d["floor"])
        model_floors[(W, eps)] = model_floor(W, eps, k_interp)
    rows = []
    g1_pass = True
    for W in W_LIST:
        for eps in EPS_LIST:
            hf = floors[(W, eps)]["floor"]
            mf = model_floors[(W, eps)]
            ke = implied[(W, eps)]
            ratio = (mf / hf) if (hf and mf) else None
            if ratio is not None and not (0.5 <= ratio <= 2.0):
                g1_pass = False
            rows.append({"W": W, "eps": eps, "harness_floor": hf,
                         "model_floor@k_interp": round(mf, 1) if mf else None,
                         "ratio": round(ratio, 3) if ratio else None,
                         "implied_k_eff": round(ke, 4) if ke else None})
    res = {"seed": SEED, "p": P, "N": N_CELLS, "draws": DRAWS,
           "k_interp_linear": round(k_interp, 4),
           "anchors": {"0.3": 0.657, "0.4": 0.896, "0.7": 1.200},
           "floors": rows, "G1_interpolated_coverage": g1_pass,
           "acc_curves": {f"{W}_{eps}": floors[(W, eps)]["acc_curve"] for W in W_LIST for eps in EPS_LIST}}
    os.makedirs("results", exist_ok=True)
    with open("results/d12ab_keff_p055.json", "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({k: v for k, v in res.items() if k != "acc_curves"}, indent=2))
    print("implied k_eff values:", [r["implied_k_eff"] for r in rows])


if __name__ == "__main__":
    main()
