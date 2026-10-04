#!/usr/bin/env python3
"""D12u: analytic order-statistics model of the discovery floor.

Question (D12t's open lever): does a max-over-noisy-correlation-estimates
order-statistics model predict alpha_disc ~ 2 * alpha_corr ~ 3.84, matching
the measured 3.91?

Model: partner true corr = s. Each of the N-1 candidate cells yields a
corr estimate \hat r ~ N(s_hat, sigma) where for the true partner
s_hat = s * (1-2eps)... no — signal in the ESTIMATOR decays as s^alpha_corr/...
Keep it simple and honest: null candidates have true corr 0, estimator
noise sd sigma_r(T) ~ 1/sqrt(T) (sample corr of T atoms). True partner has
true corr c(T, s) = s^1.92 (D12m's measured decay, applied to the stream
generator directly: corr ~ (1-2eps)^1.92 * ... at eps=0, corr = p = s).
Discovery succeeds iff max null estimate < partner estimate with prob >= 0.5
(floor = smallest T with success prob >= 0.5, matching the harness).

Two model variants:
  M1: partner estimate ~ N(c, sigma), nulls ~ N(0, sigma), sigma = 1/sqrt(W*T).
  M2: same but partner true corr = s (linear, no 1.92 decay) as a control.
Fit T_floor(s) on an eps grid at p=0.3, W=8, N=32 and fit alpha_eps of the
model; compare to measured 3.91 and to 2*1.92 = 3.84.
Seed 2718. CPU-only, seconds.
"""
import json
import math
import numpy as np

SEED = 2718
rng = np.random.default_rng(SEED)

N = 32          # cells (N-1 nulls)
W = 8           # channel width -> estimator pools W*T atoms
P = 0.3
ALPHA_CORR = 1.92
T_GRID = np.array([10, 15, 20, 30, 40, 60, 80, 120, 160, 240, 320, 480, 640, 800], float)
EPS_GRID = [0.0, 0.05, 0.1, 0.2]
DRAWS = 4000    # monte carlo draws per (T, eps)


def success_prob(T, s, draws=DRAWS):
    """P(discover) via MC: partner est vs max of N-1 null ests."""
    sigma = 1.0 / math.sqrt(W * T)
    nulls = rng.normal(0.0, sigma, size=(draws, N - 1)).max(axis=1)
    partner = rng.normal(s, sigma, size=draws)
    return float((partner > nulls).mean())


def floor_for(s, variant_decay):
    eff = (s ** ALPHA_CORR) if variant_decay else s
    for T in T_GRID:
        if success_prob(T, eff) >= 0.5:
            return T
    return float("inf")


def fit_alpha(floors, eff_s_list):
    """log T = logC - a*log s -> a."""
    x = np.log(np.array(eff_s_list))
    y = np.log(np.array(floors))
    a = -(np.polyfit(x, y, 1)[0])
    return float(a), float(np.polyfit(x, y, 1)[1])


results = {}
for variant, decay in [("M1_s^1.92", True), ("M2_linear", False)]:
    floors = []
    effs = []
    for eps in EPS_GRID:
        s = P * (1 - 2 * eps)  # generator corr (D12q correction)
        fl = floor_for(s, decay)
        floors.append(fl)
        effs.append(s)
        print(f"{variant} eps={eps}: s={s:.3f} floor={fl}")
    a, logC = fit_alpha(floors, effs)
    results[variant] = {"floors": floors, "alpha": a, "C": math.exp(logC)}
    print(f"{variant}: alpha_eps = {a:.2f}, C = {math.exp(logC):.2f}")

m1 = results["M1_s^1.92"]
measured = 3.91
pred = 2 * ALPHA_CORR
out = {
    "seed": SEED, "N": N, "W": W, "p": P, "draws": DRAWS,
    "results": results,
    "measured_alpha_eps_d12t": measured,
    "predicted_2x": pred,
    "verdict": "KEEP_orderstats" if abs(m1["alpha"] - measured) < 1.0 else "KILL_orderstats",
}
with open("results/d12u_orderstats_model.json", "w") as f:
    json.dump(out, f, indent=2, default=str)
print("VERDICT:", out["verdict"])
