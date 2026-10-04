#!/usr/bin/env python3
"""D12u+ FAMILY TEST (pre-registered plan — committed before firing).

The D12 close-out (RESULTS.md, BOOKED 12:2x Oct 4) prescribes this family
test before ANY next constant-surface fit. D12u (single config N=32, W=8,
p=0.3) showed the order-statistics model nails the exponent (model alpha_eps
4.18 vs measured 3.91 vs naive 2*1.92 = 3.84) but the constant was loose
(booked as "~400x"; the artifacts themselves show ~2x in C at the W=8
overlap — this run re-audits that number too), with ideal-Gaussian nulls and
no estimator-tail realism. The open question: is the looseness a NULL-SHAPE
artifact (effective-null-count / W-scaling the model already predicts) or a
TAIL-REALISM gap (real estimator noise isn't Gaussian)?

PLAN (frozen before run):
  Grid: N in {8, 32, 128} x W in {4, 8, 16} x p in {0.15, 0.3, 0.45} — 27
  configs, 3x3x3. For each: model exactly as D12u variant M1 — partner
  estimate ~ N(s^1.92, sigma), nulls ~ N(0, sigma), sigma = 1/sqrt(W*T);
  s = p*(1-2*eps) on eps grid {0, .05, .1, .2}; floor = T where
  P(partner > max of N-1 nulls) crosses 0.5, LINEARLY INTERPOLATED in log T
  (D12u used hard grid values; interpolation removes the grid-quantization
  wobble in the fit — documented change, MC identical otherwise).
  4000 draws/point. Seeds: 2718 lineage via default_rng([2718, cfg_idx]).
  Fit log T = logC - alpha*log s per config -> (alpha_eps, C).

  Realism variant (ONE, per close-out mandate): t-distributed estimate
  noise, df=4, variance-standardized (x sqrt((df-2)/df)) for BOTH partner
  and nulls — same seeds, same grid, same fit. Heavy tails inflate the
  null max; if that moves C TOWARD the harness, looseness was tail
  realism; if it moves C AWAY, tails are exculpated and the residual gap
  is a null-shape/effective-count artifact.

  Theory anchor: floor implies sigma ~ s^1.92 / b(N), b(N) = E[max of N-1
  std normals] -> T ~ b(N)^2 / (W * s^3.84). So alpha should sit at 3.84
  independent of config, and C * W should equal b(N)^2 (monotone in N,
  flat in W and p). b(N) measured by MC on a separate seed-stream.

VERDICT RULE (pre-registered):
  CONFIRMED iff:
    V1 exponent stable: all 27 Gaussian-config alphas in [3.34, 4.34]
       (within +/-0.5 of 3.84) AND |Spearman(alpha, axis)| <= 0.5 for each
       of N, W, p (no monotone drift);
    V2 C monotone-predictable from N: C*W monotone increasing in N within
       every (W, p) slice AND C within 1.5x of b(N-1)^2/W for >= 24/27
       configs;
    V3 t4 variant keeps alpha in [3.34, 4.34] (constant may move; the
       direction is the diagnostic, not the gate).
  Any failure -> CONFIG_DEPENDENT: the 2x law is a coincidence of the
  (32, 8, 0.3) config and any next fit must be per-config — say so loudly.

CPU-only. ~minutes. Seed 2718 (D-series lineage). No GPU touched.
"""
import json
import math
import numpy as np

SEED = 2718
N_GRID = [8, 32, 128]
W_GRID = [4, 8, 16]
P_GRID = [0.15, 0.3, 0.45]
EPS_GRID = [0.0, 0.05, 0.1, 0.2]
DRAWS = 4000
ALPHA_CORR = 1.92  # D12m certified decorrelation exponent
T_GRID = np.geomspace(1.0, 40000.0, 95)  # x1.12 steps, sub-grid interp
T_DF = 4  # realism variant degrees of freedom
VERDICT_BAND = (3.34, 4.34)  # 3.84 +/- 0.5


def success_probs(Ts, s_eff, K, rng, noise="gauss"):
    """P(partner > max null) for each T in Ts; single vectorized draw set."""
    sig = 1.0 / np.sqrt(W_cur * Ts)  # W_cur from caller (module global swap)
    out = []
    for i, T in enumerate(Ts):
        sg = sig[i]
        if noise == "gauss":
            nulls = rng.normal(0.0, sg, size=(DRAWS, K))
            partner = rng.normal(s_eff, sg, size=DRAWS)
        else:  # t4, variance-standardized
            sc = math.sqrt((T_DF - 2) / T_DF)
            nulls = sc * rng.standard_t(T_DF, size=(DRAWS, K)) * sg
            partner = sc * rng.standard_t(T_DF, size=DRAWS) * sg + s_eff
        out.append(float((partner > nulls.max(axis=1)).mean()))
    return np.array(out)


def floor_interp(Ts, probs):
    """First log-T crossing of 0.5, linearly interpolated; flags if outside."""
    if probs[0] >= 0.5:
        return float(Ts[0]), "at_grid_bottom"
    for i in range(len(Ts) - 1):
        if probs[i] < 0.5 <= probs[i + 1]:
            x0, x1 = math.log(Ts[i]), math.log(Ts[i + 1])
            p0, p1 = probs[i], probs[i + 1]
            xc = x0 + (0.5 - p0) * (x1 - x0) / (p1 - p0)
            return math.exp(xc), "ok"
    return float("inf"), "no_crossing"


def fit(floors, s_list):
    m = [i for i, f in enumerate(floors) if math.isfinite(f)]
    x = np.log(np.array([s_list[i] for i in m]))
    y = np.log(np.array([floors[i] for i in m]))
    a, b = np.polyfit(x, y, 1)
    return float(-a), float(math.exp(b)), len(m)


def spearman(x, y):
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    return float(np.corrcoef(rx, ry)[0, 1])


# --- theory anchor: b(N) = E[max of N-1 std normals], MC on separate stream
brng = np.random.default_rng([SEED, 999])
bN = {}
for N in N_GRID:
    K = N - 1
    bN[N] = float(brng.normal(0.0, 1.0, size=(400_000, K)).max(axis=1).mean())

configs = []
cfg_idx = 0
for N in N_GRID:
    for W in W_GRID:
        for P in P_GRID:
            for noise in ("gauss", "t4"):
                globals()["W_cur"] = W
                rng = np.random.default_rng([SEED, cfg_idx])
                floors, flags, s_list = [], [], []
                for eps in EPS_GRID:
                    s = P * (1 - 2 * eps)
                    s_eff = s ** ALPHA_CORR
                    Ts = T_GRID if s_eff > 0.05 else T_GRID  # wide grid covers all
                    probs = success_probs(Ts, s_eff, N - 1, rng, noise)
                    fl, flag = floor_interp(Ts, probs)
                    floors.append(fl)
                    flags.append(flag)
                    s_list.append(s)
                a, C, npts = fit(floors, s_list)
                rec = {"N": N, "W": W, "p": P, "noise": noise, "floors": floors,
                       "flags": flags, "alpha": a, "C": C, "fit_points": npts}
                configs.append(rec)
                print(f"N={N:3d} W={W:2d} p={P:.2f} {noise:5s}: "
                      f"alpha={a:5.2f} C={C:9.3f} flags={flags}")
                cfg_idx += 1

gauss_cfgs = [c for c in configs if c["noise"] == "gauss"]
t4_cfgs = [c for c in configs if c["noise"] == "t4"]

# --- V1: exponent stability
alphas = np.array([c["alpha"] for c in gauss_cfgs])
vN = np.array([c["N"] for c in gauss_cfgs], float)
vW = np.array([c["W"] for c in gauss_cfgs], float)
vP = np.array([c["p"] for c in gauss_cfgs], float)
in_band = [VERDICT_BAND[0] <= a <= VERDICT_BAND[1] for a in alphas]
rho_N, rho_W, rho_P = spearman(vN, alphas), spearman(vW, alphas), spearman(vP, alphas)
v1 = all(in_band) and max(abs(rho_N), abs(rho_W), abs(rho_P)) <= 0.5

# --- V2: C predictable from N (C*W ~ b(N)^2, monotone in N, flat in W, p)
mono_ok, ratio_ok, n_ratio_ok = True, [], 0
for c in gauss_cfgs:
    pred = bN[c["N"]] ** 2 / c["W"]
    ratio = c["C"] / pred
    ratio_ok.append(ratio)
    if 1 / 1.5 <= ratio <= 1.5:
        n_ratio_ok += 1
for W in W_GRID:
    for P in P_GRID:
        series = [next(c["C"] * c["W"] for c in gauss_cfgs
                       if c["N"] == N and c["W"] == W and c["p"] == P)
                  for N in N_GRID]
        if not all(series[i] < series[i + 1] for i in range(len(series) - 1)):
            mono_ok = False
v2 = mono_ok and n_ratio_ok >= 24

# --- V3: t4 exponent band (direction of C move = diagnostic)
t4_alphas = np.array([c["alpha"] for c in t4_cfgs])
v3 = bool(np.all((t4_alphas >= VERDICT_BAND[0]) & (t4_alphas <= VERDICT_BAND[1])))

# --- W-scaling exponent per N (compare measured alpha_W 0.927, D12t)
aw_model = {}
for N in N_GRID:
    cs = [next(c["C"] for c in gauss_cfgs if c["N"] == N and c["W"] == W and c["p"] == P_GRID[1])
          for W in W_GRID]
    sl = np.polyfit(np.log(np.array(W_GRID, float)), np.log(np.array(cs)), 1)[0]
    aw_model[N] = float(-sl)

# --- audit: model vs measured at the D12t overlap (N=32, W=8, p=0.3)
ov = next(c for c in gauss_cfgs if (c["N"], c["W"], c["p"]) == (32, 8, 0.3))
C_hat_d12t, alpha_W_d12t = 1.38, 0.927
meas_C_at_w8 = C_hat_d12t * 8 ** (-alpha_W_d12t)

verdict = "CONFIRMED" if (v1 and v2 and v3) else "CONFIG_DEPENDENT"
print(f"\nV1 exponent stable: {v1} (alphas {alphas.min():.2f}-{alphas.max():.2f}, "
      f"rhoN={rho_N:.2f} rhoW={rho_W:.2f} rhoP={rho_P:.2f})")
print(f"V2 C predictable:   {v2} (mono={mono_ok}, within1.5x {n_ratio_ok}/27)")
print(f"V3 t4 in band:      {v3} (t4 alphas {t4_alphas.min():.2f}-{t4_alphas.max():.2f})")
print(f"alpha_W model: {aw_model} (measured 0.927)")
print(f"overlap (32,8,0.3): model C={ov['C']:.3f} vs measured C@W8~{meas_C_at_w8:.3f} "
      f"ratio={ov['C']/meas_C_at_w8:.2f}x")
print("VERDICT:", verdict)

out = {
    "seed": SEED, "seed_lineage": "default_rng([2718, cfg_idx]), b(N): [2718, 999]",
    "grid": {"N": N_GRID, "W": W_GRID, "p": P_GRID, "eps": EPS_GRID},
    "draws": DRAWS, "t_grid": "geomspace(1,40000,95) x1.12, floor=interp log-T crossing",
    "bN_Emax": bN, "configs": configs,
    "v1": {"pass": v1, "alpha_min": float(alphas.min()), "alpha_max": float(alphas.max()),
           "rho_N": rho_N, "rho_W": rho_W, "rho_P": rho_P, "band": VERDICT_BAND},
    "v2": {"pass": v2, "monotone_in_N": mono_ok, "within_1p5x_of_pred": n_ratio_ok,
           "C_over_pred_range": [float(min(ratio_ok)), float(max(ratio_ok))]},
    "v3": {"pass": v3, "t4_alpha_min": float(t4_alphas.min()), "t4_alpha_max": float(t4_alphas.max())},
    "alpha_W_model_per_N": aw_model, "measured_alpha_W_d12t": alpha_W_d12t,
    "overlap_audit": {"model_C": ov["C"], "measured_C_at_w8": meas_C_at_w8,
                      "ratio": ov["C"] / meas_C_at_w8, "model_alpha": ov["alpha"],
                      "measured_alpha_d12t": 3.91,
                      "note": "booked '~400x loose' does not reproduce from d12u/d12t artifacts; actual C gap at overlap is ~2x, floors ~3x"},
    "verdict": verdict,
}
with open("results/d12u_family.json", "w") as f:
    json.dump(out, f, indent=2, default=str)
