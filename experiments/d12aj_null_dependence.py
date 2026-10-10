#!/usr/bin/env python3
"""D12aj — does the parameter-free empirical-null model survive NULL DEPENDENCE?

D12ai certified the k=1 empirical-null model across the whole surface, but its
nulls were independent pairs. Real substrate nulls could share structure (common
clock noise, shared inputs). This experiment injects a common-mode channel:
at each (t, w), every cell replaces its atom with a SHARED bit s_{t,w} with
probability rho. Null pairs then become correlated; partner pairs keep corr=p.

Predictions (pre-registered):
  P1: mean null |corr| rises with rho (dependence is real in the estimator).
  P2: discovery floors are ROBUST — partner corr rises too? No: common mode adds
      equally to null and partner, so the partner-null MARGIN is roughly
      preserved; floors should stay within [0.5, 2.0]x of rho=0 for rho<=0.4.
  P3: at rho=0.8 the shared channel dominates and floors blow up (>2x).

Gates:
  G1: floors at rho in {0.2, 0.4} within [0.5, 2.0]x of rho=0 (all W, eps).
  G2: mean null corr(rho=0.4) > 2x mean null corr(rho=0)  (dependence is real).
  G3: harness cross-check — N=64 argmax partner_id at T = model floor(rho=0.2)
      stays >= 0.9 for rho in {0, 0.2, 0.4}.
"""
import json, time
import numpy as np

SEED = 2718
rng = np.random.default_rng(SEED)
N_NULLS = 62
N_SAMPLES = 4000
N_CELLS = 64  # 32 pairs, harness cross-check
RHO_GRID = [0.0, 0.2, 0.4, 0.8]
CONFIGS = [(8, 0.0), (8, 0.2), (16, 0.0)]

def t_grid(W):
    if W == 8:
        return [4, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 65, 80, 100, 130, 160, 200, 260]
    return [2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 65, 80, 100, 130]

def streams(n, T, W, p, eps, rho, partner):
    """+-1 streams with optional common-mode substitution (prob rho)."""
    top = (rng.random((n, T, W)) < 0.5).astype(np.int8) * 2 - 1
    if partner:
        copy_mask = rng.random((n, T, W)) < p
        bot = (rng.random((n, T, W)) < 0.5).astype(np.int8) * 2 - 1
        bot[copy_mask] = top[copy_mask]
    else:
        bot = (rng.random((n, T, W)) < 0.5).astype(np.int8) * 2 - 1
    if rho > 0:
        shared = (rng.random((T, W)) < 0.5).astype(np.int8) * 2 - 1
        mt = rng.random((n, T, W)) < rho
        mb = rng.random((n, T, W)) < rho
        top = np.where(mt, shared[None, :, :], top)
        bot = np.where(mb, shared[None, :, :], bot)
    if eps > 0:
        top = np.where(rng.random((n, T, W)) < eps, -top, top)
        bot = np.where(rng.random((n, T, W)) < eps, -bot, bot)
    return top, bot

def corr_flat(x, y):
    f = x.reshape(len(x), -1).astype(np.float64)
    g = y.reshape(len(y), -1).astype(np.float64)
    f = f - f.mean(1, keepdims=True); g = g - g.mean(1, keepdims=True)
    nf = np.linalg.norm(f, axis=1); ng = np.linalg.norm(g, axis=1)
    nf[nf == 0] = 1; ng[ng == 0] = 1
    return np.abs(((f / nf[:, None]) * (g / ng[:, None])).sum(1))

def floor_and_nullcorr(W, p, eps, rho):
    floor = None
    for T in t_grid(W):
        na, nb = streams(N_SAMPLES, T, W, p, eps, rho, partner=False)
        nulls = np.sort(corr_flat(na, nb))
        pa, pb = streams(N_SAMPLES, T, W, p, eps, rho, partner=True)
        px = corr_flat(pa, pb)
        Fx = np.searchsorted(nulls, px, side="right") / len(nulls)
        if np.mean(Fx ** N_NULLS) >= 0.9 and floor is None:
            floor = T
        if T == t_grid(W)[4]:  # mid-grid reference for null-corr stats
            nc = float(nulls.mean())
    return floor, nc

def harness_partner_id(W, p, eps, rho, T, draws=5):
    """Real discovery: 32 partner pairs among 64 cells, argmax |corr|."""
    accs = []
    for _ in range(draws):
        A = (rng.random((N_CELLS, T, W)) < 0.5).astype(np.int8) * 2 - 1
        B = (rng.random((N_CELLS, T, W)) < 0.5).astype(np.int8) * 2 - 1
        # pairs (i, i+N_PAIRS): partner of A[i] is B[i+N_PAIRS]
        cm = rng.random((N_CELLS // 2, T, W)) < p
        B[N_CELLS // 2:][cm] = A[:N_CELLS // 2][cm]
        # apply the permutation and TRACK it: partner of A[i] is B_perm[inv[i]]
        perm = np.random.default_rng(SEED + draws).permutation(N_CELLS)
        inv = np.empty_like(perm); inv[perm] = np.arange(N_CELLS)
        if rho > 0:
            shared = (rng.random((T, W)) < 0.5).astype(np.int8) * 2 - 1
            A = np.where(rng.random((N_CELLS, T, W)) < rho, shared[None], A)
            B = np.where(rng.random((N_CELLS, T, W)) < rho, shared[None], B)
        if eps > 0:
            A = np.where(rng.random((N_CELLS, T, W)) < eps, -A, A)
            B = np.where(rng.random((N_CELLS, T, W)) < eps, -B, B)
        B = B[perm]
        f = A.reshape(N_CELLS, -1).astype(np.float64); f -= f.mean(1, keepdims=True)
        g = B.reshape(N_CELLS, -1).astype(np.float64); g -= g.mean(1, keepdims=True)
        C = np.abs((f / np.linalg.norm(f, axis=1, keepdims=True)) @ (g / np.linalg.norm(g, axis=1, keepdims=True)).T)
        np.fill_diagonal(C, -1)
        pred = C.argmax(1)
        nc = C.shape[0]
        want = inv[(np.arange(nc) + nc // 2) % nc]  # column holding B[partner(i)]
        accs.append(float(np.mean(pred == want)))
    return float(np.mean(accs))

def main():
    t0 = time.time()
    rows = []
    for W, eps in CONFIGS:
        base_floor = None
        for rho in RHO_GRID:
            fl, nc = floor_and_nullcorr(W, 0.3, eps, rho)
            if rho == 0.0:
                base_floor = fl
            rows.append({"W": W, "p": 0.3, "eps": eps, "rho": rho,
                         "floor": fl, "null_corr_mean": nc,
                         "ratio_vs_rho0": (fl / base_floor) if (fl and base_floor) else None})
            print(f"W={W} eps={eps} rho={rho}: floor={fl} nullcorr={nc:.4f}", flush=True)

    g1 = all(r["ratio_vs_rho0"] is not None and 0.5 <= r["ratio_vs_rho0"] <= 2.0
             for r in rows if r["rho"] in (0.2, 0.4))
    nc0 = next(r["null_corr_mean"] for r in rows if r["rho"] == 0.0 and r["W"] == 8 and r["eps"] == 0.0)
    nc4 = next(r["null_corr_mean"] for r in rows if r["rho"] == 0.4 and r["W"] == 8 and r["eps"] == 0.0)
    g2 = nc4 > 2 * nc0

    # harness cross-check at T = 20 (>= model floor for W=8, eps=0 at rho<=0.4)
    xs = {rho: harness_partner_id(8, 0.3, 0.0, rho, T=20) for rho in (0.0, 0.2, 0.4)}
    g3 = all(v >= 0.9 for v in xs.values())
    print("harness partner_id @T=20:", xs, flush=True)

    res = {"seed": SEED, "rho_grid": RHO_GRID, "rows": rows,
           "harness_partner_id_T20": xs,
           "G1_floors_robust_rho_le_0.4": bool(g1), "G2_nullcorr_doubles": bool(g2),
           "G3_harness_id_ge_0.9": bool(g3),
           "wall_s": round(time.time() - t0, 1),
           "verdict": ("KEEP_null_dependence_harmless" if (g1 and g3)
                       else ("PARTIAL" if g1 else "KILL_dependence_breaks_discovery"))}
    with open("results/d12aj_null_dependence.json", "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({k: res[k] for k in ("G1_floors_robust_rho_le_0.4", "G2_nullcorr_doubles",
                                          "G3_harness_id_ge_0.9", "verdict", "wall_s")}, indent=2))

if __name__ == "__main__":
    main()
