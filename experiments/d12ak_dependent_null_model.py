#!/usr/bin/env python3
"""D12ak — does a mean-shift model explain the common-mode floor blow-up?

D12aj measured that injecting a common-mode channel (prob rho) inflates the
empirical-null discovery floors ~6.4x at rho=0.4 (W=8, p=0.3: 25 -> 50 -> 160).
Open lever: model it analytically.

Claim under test: under the injection, a null pair shares the common bit at
both members w.p. rho^2 per (t,w) cell, so E[null corr] ~ rho^2; the partner
pair gains the same +rho^2. If a Gaussian order-statistics model with these
shifted means explained the blow-up, floors should rise with rho.

KEY STRUCTURAL FACT: the model subtracts to rho-invariance —
  success = P[ N(s^1.92 + rho^2, sig) > max of 62 x N(rho^2, sig) ]
is IDENTICAL in distribution to the rho=0 case (subtract rho^2 everywhere).
So the mean-shift model predicts floor_ratio(rho) = 1.0 EXACTLY at every rho.
We verify this numerically (MC at matched seeds) and gate against the measured
D12aj ratios.

Gates (vs D12aj measured MC floors):
  G1: model floor_ratio(rho=0.2) within [0.5, 2]x of measured (2x).
  G2: model floor_ratio(rho=0.4) within [0.5, 2]x of measured (6.4x / 6.7x).
  (Both compare RATIOS so the Gaussian model's known constant looseness
  cancels — this is the fair test of the mean-shift explanation.)
"""
import json, time
import numpy as np

SEED = 2718
rng = np.random.default_rng(SEED)
N_NULLS = 62
N_SAMPLES = 20000
ALPHA = 1.92
P = 0.3

# D12aj measured MC floors: (W, eps) -> {rho: floor or None}
MEASURED = {
    (8, 0.0):  {0.0: 25, 0.2: 50, 0.4: 160},
    (8, 0.2):  {0.0: 65, 0.2: 130, 0.4: None},
    (16, 0.0): {0.0: 12, 0.2: 25, 0.4: 80},
}

def t_grid(W):
    if W == 8:
        return [4, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 65, 80, 100, 130, 160, 200, 260, 320, 400]
    return [2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 65, 80, 100, 130, 160, 200]

def model_floor(W, eps, rho):
    s = P * (1 - 2 * eps)
    mu_partner = s ** ALPHA + rho ** 2
    mu_null = rho ** 2
    floor = None
    for T in t_grid(W):
        sig = 1.0 / np.sqrt(W * T)
        z = rng.standard_normal(N_SAMPLES) * sig + mu_partner
        nulls = rng.standard_normal((N_SAMPLES, N_NULLS)) * sig + mu_null
        if np.mean(nulls.max(1) < z) >= 0.9 and floor is None:
            floor = T
    return floor

def main():
    t0 = time.time()
    rows, g = [], {"g1": None, "g2": None}
    for (W, eps), mrow in MEASURED.items():
        fl = {rho: model_floor(W, eps, rho) for rho in mrow}
        for rho, meas in mrow.items():
            if meas is None or fl[0.0] is None or fl[rho] is None:
                r_pred = r_meas = None
            else:
                r_pred = fl[rho] / fl[0.0]
                r_meas = meas / mrow[0.0]
            row = {"W": W, "eps": eps, "rho": rho, "pred_floor": fl[rho],
                   "meas_floor": meas, "pred_ratio": r_pred, "meas_ratio": r_meas}
            if rho == 0.2 and r_pred is not None:
                g["g1"] = 0.5 <= r_pred / r_meas <= 2.0
            if rho == 0.4 and r_pred is not None and r_meas is not None:
                g["g2"] = 0.5 <= r_pred / r_meas <= 2.0
            rows.append(row)
    out = {"name": "d12ak_dependent_null_model", "seed": SEED,
           "model": "mean-shift Gaussian order statistics: N(s^1.92+rho^2, 1/sqrt(WT)) partner vs 62 x N(rho^2, 1/sqrt(WT)); floor ratio vs rho",
           "structural_note": "model is EXACTLY rho-invariant (both means shift by rho^2, cancels); predicted ratio = 1.0 at all rho",
           "rows": rows, "gates": g, "wall_s": round(time.time() - t0, 2)}
    with open("results/d12ak_dependent_null_model.json", "w") as f:
        json.dump(out, f, indent=1)
    for r in rows:
        print(r)
    print("G1 (rho=0.2):", g["g1"], " G2 (rho=0.4):", g["g2"], " wall", out["wall_s"], "s")

if __name__ == "__main__":
    main()
