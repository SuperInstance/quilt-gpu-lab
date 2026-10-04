#!/usr/bin/env python3
"""D12t: pin alpha_eps with 10 draws per cell (variance-hardened D12s).

D12s's joint fit gave alpha_eps ~= 4.0 on 3 draws/cell, outside the [1.2, 1.9]
band, with the caveat that the (W=8, eps=0.2) floor looked like a noisy draw.
This rerun doubles... triples draws to 10 per (W, eps, T) point on the same
14-rung T grid and refits the joint law T_floor ~ C / (W * s_eff^alpha).

Gates (pre-registered):
  G1: max |C_emp / C_hat - 1| <= 1 (within 2x everywhere)
  G2: alpha_eps <= 2.5 (between the corr exponent 1.92 and D12s's 4.0 —
      confirms whether discovery-noise exponent is genuinely super-linear;
      anything > 2.5 keeps D12s's 'twice as hard' headline, < 2.5 overturns it)
  Heldout: W=16 predicted from W in {4,8} fit, coverage >= 5/6 at 1.5x.
"""
import json, math, os
import numpy as np

SEED = 2718
rng = np.random.default_rng(SEED)

N = 32
P = 0.3
EPS_GRID = [0.0, 0.05, 0.1, 0.2]
W_GRID = [4, 8, 16]
T_GRID = [10, 15, 20, 30, 40, 60, 80, 120, 160, 240, 320, 480, 640, 800]
DRAWS = 10


def partner_id_acc(w, t, eps):
    half = N // 2
    accs = []
    for d in range(DRAWS):
        a = rng.choice([-1, 1], size=(half, w, t))
        mask = rng.random((half, w, t)) < P
        b = np.where(mask, a, rng.choice([-1, 1], size=a.shape))
        flip = rng.random(a.shape) < eps
        a = np.where(flip, -a, a)
        flip2 = rng.random(b.shape) < eps
        b = np.where(flip2, -b, b)
        A = np.empty((half, 2, w, t)); A[:, 0] = a; A[:, 1] = b
        s = A.reshape(N, w, t).astype(np.float64)
        s = s - s.mean(axis=2, keepdims=True)
        sd = s.std(axis=2, keepdims=True)
        ok = sd > 1e-9
        sz = np.where(ok, s / np.where(ok, sd, 1), 0.0)
        flat = sz.transpose(0, 2, 1).reshape(N, -1)
        C = (flat @ flat.T) / flat.shape[1]
        np.fill_diagonal(C, -2)
        pred = C.argmax(axis=1)
        cells = [(2 * i, 2 * i + 1) for i in range(half)]
        correct = sum(1 for i, j in cells if pred[i] == j)
        accs.append(correct / half)
    return float(np.mean(accs))


def find_floor(w, eps):
    for t in T_GRID:
        if partner_id_acc(w, t, eps) >= 0.9:
            return t
    return None


def main():
    floors = {}
    acc_curves = {}
    for w in W_GRID:
        for eps in EPS_GRID:
            floors[(w, eps)] = find_floor(w, eps)
            tf = floors[(w, eps)]
            acc_curves[f"w{w}_eps{eps}"] = {t: round(partner_id_acc(w, t, eps), 3)
                                            for t in [T_GRID[max(0, T_GRID.index(tf) - 1)] if tf else T_GRID[0], tf] if tf} if tf else None

    xs, ys, labels = [], [], []
    for (w, eps), tf in floors.items():
        if tf is None:
            continue
        s = P * (1 - 2 * eps)
        xs.append([math.log(w), math.log(s)])
        ys.append(math.log(tf))
        labels.append(f"w{w}_eps{eps}")
    xs = np.array(xs); ys = np.array(ys)
    A = np.column_stack([np.ones(len(ys)), xs])
    coef, *_ = np.linalg.lstsq(A, ys, rcond=None)
    logC, aW, aS = coef
    C_hat = math.exp(logC)
    resid = ys - A @ coef
    devs = {lab: round(float(math.exp(r) - 1), 3) for lab, r in zip(labels, resid)}
    max_abs_dev = float(np.max(np.abs(np.exp(resid) - 1)))

    mask = xs[:, 0] < math.log(16) - 1e-9
    coef2, *_ = np.linalg.lstsq(A[mask], ys[mask], rcond=None)
    heldout = []
    for (w, eps), tf in floors.items():
        if w != 16 or tf is None:
            continue
        s = P * (1 - 2 * eps)
        pred = math.exp(coef2[0] + coef2[1] * math.log(w) + coef2[2] * math.log(s))
        heldout.append({"w": w, "eps": eps, "tf": tf, "pred": round(pred, 1),
                        "covered_1p5x": bool(tf <= pred * 1.5)})

    g1 = max_abs_dev <= 1.0
    alpha_eps = -aS
    g2 = alpha_eps <= 2.5
    cov = sum(h["covered_1p5x"] for h in heldout)

    out = {
        "seed": SEED, "N": N, "p": P, "draws": DRAWS, "t_grid": T_GRID,
        "floors": {f"w{w}_eps{eps}": tf for (w, eps), tf in floors.items()},
        "fit": {"C_hat": round(C_hat, 2), "alpha_W": round(-aW, 3), "alpha_eps": round(alpha_eps, 3),
                "max_C_emp_dev": round(max_abs_dev, 3), "C_emp_devs": devs},
        "gates": {"G1_within_2x": bool(g1), "G2_alpha_eps_le_2.5": bool(g2)},
        "heldout_w16": heldout, "heldout_coverage": f"{cov}/{len(heldout)}",
    }
    os.makedirs("results", exist_ok=True)
    with open("results/d12t_draws10_alpha_eps.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
