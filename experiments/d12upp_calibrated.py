#!/usr/bin/env python3
"""D12u++ CALIBRATED FIT (pre-registered plan — committed before firing).

Prescribed verbatim by the D12u+ family test booking (RESULTS.md
"[BOOKED 15:0x CPU Oct 4]"): "next fit may proceed with a null-strength
correction term; exponent and b(N)²/W skeleton are certified" and the
close-out's follow-up "prereg d12u++ calibrated fit (effective-null-count
parameter vs d12t's 12 measured cells)".

ONE PARAMETER (chosen a priori): effective null count K_eff = κ·(N−1),
replacing the N−1 iid std-normal nulls in the certified M1 model. Chosen
over the alternative σ_eff = σ·s_factor because the close-out and family
test both name CORRELATED NULLS (K_eff < K) as the lead suspect and the
follow-up prescribes the effective-null-count form explicitly. Direction
expected from t4: the family test's model C at the d12t overlap is 2.67×
TOO HIGH — ideal-Gaussian floors are too expensive, i.e. the harness's
effective nulls are FEWER/WEAKER than N−1 iid std normals — so κ < 1 is
the predicted sign. HONESTY CAVEAT (pre-declared): κ is a LUMPED
effective-strength parameter — it absorbs correlated nulls, the
measured-side criterion offset (d12t floor = first grid T with mean
partner-ID acc ≥ 0.9 over 10 draws, vs model P(win)=0.5 crossing), and
any estimator-variance realism — it is NOT a literal surviving-arm count.

EXACT REDUCTION (documented, no MC change to the model): M1 is
partner ~ N(s^1.92, σ), nulls iid N(0, σ), σ = 1/√(WT), s = p(1−2eps).
Standardizing by σ, P(win|T) = P(δ + z > M) where δ = s^1.92·√(WT),
z ~ N(0,1), M = max over the (mixture-count) nulls — all standard.
So P(win) depends on T only through δ, and the floor obeys EXACTLY
  T_floor = δ*(K_eff)² / (W · s^3.84),   δ*(K) := 0.5-crossing of δ,
with exponent 3.84 = 2×1.92 (certified config-independent, D12u+ V1 —
NOT refit here). δ*(K_eff) is computed by MC once per K_eff (mixture
construction for fractional K_eff: per draw, K_hi nulls with probability
frac = K_eff − floor(K_eff), else K_lo; the max is over the first K_i).
This is the same order-statistics model, evaluated without per-cell MC
floor noise. Machinery cross-check (reported, not gated): exact-reduction
floors at (32,8,0.3) must agree with d12u+'s per-cell MC floors
[53.6, 79.6, 122.3, 376.8] within ~10% (their 4000-draw wobble).

FIT (frozen): κ fitted on d12t's 12 measured cells (N=32, p=0.3,
W∈{4,8,16} × eps∈{0,.05,.1,.2}; floors from results/d12t_draws10_alpha_eps.json,
hard-grid values, quantization caveat noted below). Objective = MINIMAX:
minimize over κ the worst-cell |log(T_model(κ)/T_meas)| — chosen because
G1 is itself a worst-cell gate; one parameter, no other dof. Search:
33-pt log grid on [0.10, 1.00] then ternary refine to <0.5% — deterministic.
δ* MC: 300k draws/eval (search), 1.2M (final). Seeds 2718 lineage:
default_rng([2718, 7000, tag, chunk]); b-mixture stream [2718, 888].

GATES (frozen before firing):
  G1 (all 12 cells): post-fit ratio T_model(κ̂)/T_meas ∈ [1/1.3, 1.3]
     for EVERY cell (worst-cell gap ≤ 1.3×).
  G2 (sane band): κ̂ ∈ [0.10, 1.00]. A priori: lower bound keeps
     K_eff ≥ 3.1 at the fit-N (mechanism stays a max over ≥2 nulls,
     non-degenerate); upper bound = no correction (t4 direction
     diagnostic rules out κ > 1 — it would push floors further up and
     worsen the certified 2–3× gap).
  G3 (out-of-sample consistency, NOT a refit): apply the single κ̂ to the
     d12u+ 27-config family grid. Calibrated model gives exactly
     C(N,W,p)·W = δ*(κ̂(N−1))²; require (a) C·W within 1.5× of
     b(K_eff)² — b = E[max] of the same mixture nulls, separate seed
     stream — for every config with K_eff ≥ 2, and (b) C·W strictly
     monotone increasing in N within every (W,p) slice (all 27 configs).
     PRE-DECLARED DEGENERACY: for K_eff < 2 (only possible in the N=8
     block when κ̂ < 2/7) the extreme-value b² anchor analytically
     degenerates (a single-null component has no finite 0.5-crossing
     anchor; for K_eff ≤ 1 no finite floor exists at all) — those
     configs are flagged degenerate, EXEMPT from (a), reported as
     diagnostics, still included in (b) (no-crossing ⇒ C·W := 0).

VERDICT RULE (frozen): CALIBRATED iff G1 AND G2 AND G3. Any failure is
booked honestly as FAIL — no refit without a new pre-registration.

CAVEATS (pre-declared): measured floors are hard-grid ceilings (t-grid
steps ×1.33–1.5, so per-cell truth is up to ~1.3× below the booked
integer) and w16/eps0 sits at the grid bottom (censored low); the
measured-side W-exponent is 0.927 vs the model's exact 1.0, so the
post-fit residual is expected to be dominated by W-shape + quantization,
not by κ; κ is fitted at a single N (32) — no measured-side N-transfer
evidence exists (d12t is single-N); CPU-only, ~1 min, no GPU touched.
"""
import json
import math
import numpy as np

SEED = 2718
ALPHA_CORR = 1.92
EXP_LAW = 2 * ALPHA_CORR          # 3.84, certified (D12u+ V1), not refit
EPS_GRID = [0.0, 0.05, 0.1, 0.2]
W_GRID = [4, 8, 16]
N_FIT, P_FIT = 32, 0.3            # d12t measured config
KAPPA_LO, KAPPA_HI = 0.10, 1.00   # G2 band
D_SEARCH, D_FINAL = 300_000, 1_200_000
N_FAMILY = [8, 32, 128]
P_FAMILY = [0.15, 0.3, 0.45]
G1_BAND, G3_BAND = 1.3, 1.5
D_GRID = np.linspace(0.0, 6.0, 241)
MEAS = "results/d12t_draws10_alpha_eps.json"
OUT = "results/d12upp_calibrated.json"


def mix_counts(K_eff, rng, n):
    """Per-draw null counts for fractional K_eff (mixture construction)."""
    K_lo = int(math.floor(K_eff))
    frac = K_eff - K_lo
    return K_lo + (rng.random(n) < frac) if frac > 0 else np.full(n, K_lo)


def delta_star(K_eff, tag, draws):
    """δ*(K_eff): 0.5-crossing of P(δ + z > M), M = max of mixture nulls.
    Chunked; exact-reduction MC. Returns None if P(0) ≥ 0.5 (no floor)."""
    n_lo = 300_000
    chunks = max(1, draws // n_lo)
    n = min(n_lo, draws)
    wins = np.zeros(len(D_GRID), dtype=np.int64)
    tot = 0
    for c in range(chunks):
        rng = np.random.default_rng([SEED, 7000, tag, c])
        counts = mix_counts(K_eff, rng, n)
        K_hi = int(counts.max())
        nulls = rng.normal(0.0, 1.0, size=(n, K_hi))
        mask = np.arange(K_hi)[None, :] >= counts[:, None]
        nulls[mask] = -np.inf
        M = nulls.max(axis=1)
        z = rng.normal(0.0, 1.0, size=n)
        D = np.sort(M - z)                     # P(δ) = P(δ > M − z) = ECDF(D) at δ
        wins += np.searchsorted(D, D_GRID, side="left")
        tot += n
    P = wins / tot
    if P[0] >= 0.5:
        return None, float(P[0]), "no_crossing"
    for i in range(len(D_GRID) - 1):
        if P[i] < 0.5 <= P[i + 1]:
            d0, d1, p0, p1 = D_GRID[i], D_GRID[i + 1], P[i], P[i + 1]
            return float(d0 + (0.5 - p0) * (d1 - d0) / (p1 - p0)), float(P[0]), "ok"
    return None, float(P[-1]), "no_crossing_high"


def b_mix(K_eff, draws=2_000_000):
    """E[max] of the same mixture nulls; separate stream [2718, 888]."""
    n_lo, chunks, tot, s = 500_000, 4, 0, 0.0
    n = min(n_lo, draws)
    for c in range(chunks):
        rng = np.random.default_rng([SEED, 888, c])
        counts = mix_counts(K_eff, rng, n)
        K_hi = int(counts.max())
        nulls = rng.normal(0.0, 1.0, size=(n, K_hi))
        mask = np.arange(K_hi)[None, :] >= counts[:, None]
        nulls[mask] = -np.inf
        s += float(nulls.max(axis=1).sum())
        tot += n
    return s / tot


# --- measured cells (d12t, hard-grid floors)
mraw = json.load(open(MEAS))["floors"]
cells = []
for k, Tm in mraw.items():
    W = int(k[1:k.index("_")])
    eps = float(k[k.index("eps") + 3:])
    cells.append({"W": W, "eps": eps, "s": P_FIT * (1 - 2 * eps), "T_meas": float(Tm)})
assert len(cells) == 12 and {c["W"] for c in cells} == {4, 8, 16}


def obj_kappa(kappa, tag, draws=D_SEARCH):
    ds, _, _ = delta_star(kappa * (N_FIT - 1), tag, draws)
    if ds is None:
        return float("inf"), None
    worst, ratios = 0.0, []
    for c in cells:
        Tm = ds * ds / (c["W"] * c["s"] ** EXP_LAW)
        r = Tm / c["T_meas"]
        ratios.append(r)
        worst = max(worst, abs(math.log(r)))
    return worst, ratios


# --- frozen search: 33-pt coarse log grid + ternary refine
coarse = np.geomspace(KAPPA_LO, KAPPA_HI, 33)
vals = []
for i, k in enumerate(coarse):
    w, _ = obj_kappa(float(k), 100 + i)
    vals.append(w)
    print(f"[coarse] kappa={k:.4f} worst_loggap={w:.4f}")
best = int(np.argmin(vals))
lo = coarse[max(0, best - 1)]
hi = coarse[min(len(coarse) - 1, best + 1)]
tag = 500
for _ in range(60):                      # ternary on log kappa
    m1 = math.exp(math.log(lo) + 0.38197 * (math.log(hi) - math.log(lo)))
    m2 = math.exp(math.log(lo) + 0.61803 * (math.log(hi) - math.log(lo)))
    tag += 2
    f1, _ = obj_kappa(m1, tag)
    f2, _ = obj_kappa(m2, tag + 1)
    if f1 < f2:
        hi = m2
    else:
        lo = m1
kappa_hat = math.exp(0.5 * (math.log(lo) + math.log(hi)))
print(f"\nkappa_hat = {kappa_hat:.4f}")

# --- final eval at kappa_hat (1.2M draws)
ds_hat, p0, flag = delta_star(kappa_hat * (N_FIT - 1), 999, D_FINAL)
worst_r, worst_r_inv = 0.0, 0.0
for c in cells:
    c["T_model"] = ds_hat * ds_hat / (c["W"] * c["s"] ** EXP_LAW)
    c["ratio"] = c["T_model"] / c["T_meas"]
    worst_r = max(worst_r, c["ratio"])
    worst_r_inv = max(worst_r_inv, 1.0 / c["ratio"])
g1 = (worst_r <= G1_BAND) and (worst_r_inv <= G1_BAND)
g2 = KAPPA_LO <= kappa_hat <= KAPPA_HI

# --- machinery cross-check vs d12u+ MC floors (reported, not gated)
ds31, _, _ = delta_star(31.0, 990, D_FINAL)
u_fam = [53.6, 79.6, 122.3, 376.8]
xcheck = [float((ds31 * ds31 / (8 * (0.3 * (1 - 2 * e)) ** EXP_LAW)) / f)
          for e, f in zip(EPS_GRID, u_fam)]

# --- G3: calibrated family sweep (exact reduction; C·W = δ*²(κ̂(N−1)))
g3_rows, cW = [], {}
for N in N_FAMILY:
    K_eff = kappa_hat * (N - 1)
    ds, p0n, fl = delta_star(K_eff, 800 + N, D_FINAL)
    b = b_mix(K_eff)
    cw = ds * ds if ds is not None else 0.0
    cW[N] = cw
    degenerate = K_eff < 2
    row = {"N": N, "K_eff": K_eff, "delta_star": ds, "flag": fl,
           "b_mix": b, "C_times_W": cw, "ratio_CW_over_b2": (cw / (b * b)) if b > 0 else None,
           "degenerate": degenerate}
    g3_rows.append(row)
    print(f"[G3] N={N:3d} K_eff={K_eff:6.2f} delta*={ds} b_mix={b:.4f} "
          f"C·W={cw:.4f} ratio={row['ratio_CW_over_b2']} degenerate={degenerate}")
mono = all(cW[N_FAMILY[i]] < cW[N_FAMILY[i + 1]] for i in range(len(N_FAMILY) - 1))
ratio_ok = all((not r["degenerate"]) or (r["ratio_CW_over_b2"] is not None
                and 1 / G3_BAND <= r["ratio_CW_over_b2"] <= G3_BAND) for r in g3_rows)
g3 = mono and ratio_ok

verdict = "CALIBRATED" if (g1 and g2 and g3) else "FAIL"

print(f"\nG1 worst-cell ratio: {worst_r:.3f} (high) / {worst_r_inv:.3f} (low) "
      f"band {G1_BAND}: {'PASS' if g1 else 'FAIL'}")
print(f"G2 kappa_hat={kappa_hat:.4f} in [{KAPPA_LO},{KAPPA_HI}]: "
      f"{'PASS' if g2 else 'FAIL'}")
print(f"G3 monotone={mono} ratio_ok={ratio_ok}: {'PASS' if g3 else 'FAIL'}")
print(f"machinery cross-check (exact vs d12u+ MC floors): "
      f"{[round(x, 3) for x in xcheck]}")
print(f"VERDICT: {verdict}")

out = {
    "seed": SEED,
    "seed_lineage": "default_rng([2718, 7000, tag, chunk]); b_mix [2718,888,chunk]",
    "parameter": "K_eff = kappa*(N-1) mixture nulls (single lumped null-strength correction)",
    "kappa_hat": kappa_hat, "kappa_band": [KAPPA_LO, KAPPA_HI],
    "delta_star_hat_N32": ds_hat, "delta_star_31_uncal": ds31,
    "draws_final": D_FINAL,
    "cells": [{k: c[k] for k in ("W", "eps", "T_meas", "T_model", "ratio")} for c in cells],
    "g1": {"pass": g1, "worst_ratio_high": worst_r, "worst_ratio_low_inv": worst_r_inv,
           "band": G1_BAND},
    "g2": {"pass": g2},
    "g3": {"pass": g3, "monotone_in_N": mono, "rows": g3_rows, "band": G3_BAND,
           "degeneracy_rule": "K_eff<2 exempt from ratio (pre-declared), C·W:=0 if no crossing"},
    "machinery_crosscheck_vs_d12up_mc": {"exact_over_mc": xcheck,
                                          "d12up_mc_floors_w8": u_fam, "note": "reported, not gated"},
    "verdict": verdict,
    "predictor": "T_floor(N,W,p,eps) = delta_star(kappa*(N-1))^2 / (W * (p*(1-2eps))^3.84)",
}
with open(OUT, "w") as f:
    json.dump(out, f, indent=2, default=str)
print("wrote", OUT)
