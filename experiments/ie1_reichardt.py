#!/usr/bin/env python3
"""ie1 — Reichardt correlators -> 4 motion family codes (the lobula-plate rung).

Science (docs/insect-vision-science-2026-09-28.md, primary-sourced 2026-09-28):
  HRC analytic response to a drifting sinusoid:
      R = c^2 * sin(2*pi*dphi/lambda) * (w*tau) / (1 + (w*tau)^2)
  delay-and-multiply on ADJACENT cell pairs, mirror-subtract for direction;
  first-order low-pass delay arm (modern form of the Hassenstein-Reichardt EMD);
  tau = 2 frames baseline (fly analogue 25-50 ms, Clark 2011);
  pool signed correlator outputs per cardinal direction -> 4 fam codes
  (T4a-d/T5a-d arity, Lappalainen 2024); a linear reader on the pooled code
  stream plays the LPTC+motor decode (pooling earns hyperacuity, science S4).

Gate (frozen in proposals/runs/ie1-plan.md BEFORE this code existed):
  KEEP iff multi-output test R^2 of ridge decoding the true DIRECTION unit
  vector from the 4 fam codes >= 0.5 at >= 2 of 3 cell densities (8/16/32),
  tau = 2 frames. Diagnostics: aliasing sign flip near lambda = 2*dphi,
  c^2 contrast fingerprint, temporal-tuning peak at w*tau = 1, tau sweep.

CPU ONLY: numpy on system python3. No cuda, no torch, no .gpu.lock.
Receipt: results/ie1_reichardt.json + stdout block.
"""
import json
import os
import time

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(HERE, "results")

# ---------------- frozen config (proposals/runs/ie1-plan.md S2) ----------------
SEED_BASE = 20260928
TAU_BASELINE = 2.0            # frames (delay-arm time constant, dt = 1 frame)
DENSITIES = (8, 16, 32)       # cell lattice pitches; dphi = 1 cell
WARMUP = 12                   # frames discarded for LP settling
T_FRAMES = 48                 # kept frames per sequence
N_TRAIN_SEQ = 4
N_TEST_SEQ = 4
RIDGE_ALPHA = 1e-2
GATE_THRESHOLD = 0.5
GATE_MIN_DENSITIES = 2

# stimuli
CONTRAST = 1.0
GRAT_LAMBDAS = (8.0, 16.0)    # spatial period, cells (dphi = 1)
GRAT_SPEEDS = (0.25, 0.5, 1.0)
BLOB_SIGMAS = (2.0, 3.0)
BLOB_SPEEDS = (0.25, 0.5)
# cardinal motion directions as (vx, vy) unit vectors in ARRAY coords
# (row index grows downward, so "D" = +row — documented convention)
DIRS = {"R": (1.0, 0.0), "L": (-1.0, 0.0), "D": (0.0, 1.0), "U": (0.0, -1.0)}
DIR_ORDER = ("R", "L", "D", "U")  # fixed code vector layout: [R, L, D, U]

TAU_SWEEP = (1.0, 2.0, 4.0)   # diagnostic only; gate stays at TAU_BASELINE
ALIAS_LAMBDAS = (1.5, 1.75, 2.0, 2.25, 2.5, 3.0, 4.0, 6.0, 8.0)
FP_CONTRASTS = (0.25, 0.5, 1.0)
TUNE_SPEEDS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.8, 1.2, 1.6, 2.0)


# ---------------- stimulus synthesis (deterministic, seeded) ----------------
def grating_scene(n, lam, v, dvec, n_frames, rng, contrast=CONTRAST):
    """Drifting sinusoid I = c*sin(2pi(x*vx + y*vy)/lam - w t), w = 2pi v/lam."""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    vx, vy = dvec
    phase0 = 2.0 * np.pi * float(rng.random())
    omega = 2.0 * np.pi * v / lam
    proj = vx * xx + vy * yy
    frames = np.empty((n_frames, n, n))
    for t in range(n_frames):
        frames[t] = contrast * np.sin(2.0 * np.pi * proj / lam - omega * t + phase0)
    return frames


def blob_scene(n, sigma, v, dvec, n_frames, rng):
    """Gaussian bump translating along dvec, path centered on the lattice."""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    vx, vy = dvec
    travel = v * (n_frames - 1)
    jx = (float(rng.random()) - 0.5) * 2.0   # deterministic per-seed jitter, <=1 cell
    jy = (float(rng.random()) - 0.5) * 2.0
    x0 = n / 2.0 - vx * travel / 2.0 + jx
    y0 = n / 2.0 - vy * travel / 2.0 + jy
    frames = np.empty((n_frames, n, n))
    for t in range(n_frames):
        cx = x0 + vx * v * t
        cy = y0 + vy * v * t
        frames[t] = CONTRAST * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2.0 * sigma ** 2)))
    return frames


# ---------------- the correlator bank (science S1.5 pseudocode) ----------------
def fam_codes(seq, tau):
    """seq (T,n,n) raw frames -> (T,4) pooled fam codes [R, L, D, U].

    Per frame: signed contrast prefilter, first-order LP delay arm (ZOH),
    four cardinal subtypes on adjacent-cell pairs, mirror-subtracted,
    pooled by mean over interior cells (LP wide-field pooling, S2.3).
    """
    a = 1.0 - np.exp(-1.0 / tau)
    lp = np.zeros_like(seq[0])
    codes = np.empty((len(seq), 4))
    for t in range(len(seq)):
        img = seq[t]
        c = img - img.mean()                       # signed contrast (keep the SIGN)
        lp += a * (c - lp)                         # delay arm: lp ~ c delayed by tau
        # RIGHT: pairs (x, x+1) — lp[x]*c[x+d] - c[x]*lp[x+d]
        d_r = lp[:, :-1] * c[:, 1:] - c[:, :-1] * lp[:, 1:]
        # LEFT: pairs (x, x-1) — lp[x]*c[x-d] - c[x]*lp[x-d]
        d_l = lp[:, 1:] * c[:, :-1] - c[:, 1:] * lp[:, :-1]
        # DOWN: pairs (y, y+1) (+row) — lp[y]*c[y+d] - c[y]*lp[y+d]
        d_dn = lp[:-1, :] * c[1:, :] - c[:-1, :] * lp[1:, :]
        # UP: pairs (y, y-1) (-row)
        d_up = lp[1:, :] * c[:-1, :] - c[1:, :] * lp[:-1, :]
        codes[t] = (d_r.mean(), d_l.mean(), d_dn.mean(), d_up.mean())
    return codes


# ---------------- dataset + ridge reader ----------------
def build_dataset(n, tau):
    """All sequences at density n. Returns train/test feature + target arrays."""
    cfgs = []
    for lam in GRAT_LAMBDAS:
        for v in GRAT_SPEEDS:
            for name in DIR_ORDER:
                cfgs.append(("grating", dict(lam=lam, v=v, dvec=DIRS[name])))
    for sigma in BLOB_SIGMAS:
        for v in BLOB_SPEEDS:
            for name in DIR_ORDER:
                cfgs.append(("blob", dict(sigma=sigma, v=v, dvec=DIRS[name])))

    def collect(split_offset):
        feats, y_dir, y_vel, fam_ids = [], [], [], []
        for ci, (fam, kw) in enumerate(cfgs):
            for si in range(N_TRAIN_SEQ if split_offset == 0 else N_TEST_SEQ):
                seed = SEED_BASE + 1000 * ci + 10 * si + split_offset
                rng = np.random.default_rng(seed)
                seq = (grating_scene(n, kw["lam"], kw["v"], kw["dvec"], WARMUP + T_FRAMES, rng)
                       if fam == "grating" else
                       blob_scene(n, kw["sigma"], kw["v"], kw["dvec"], WARMUP + T_FRAMES, rng))
                codes = fam_codes(seq, tau)[WARMUP:]
                feats.append(codes)
                vx, vy = kw["dvec"]
                y_dir.append(np.tile(np.array([vx, vy]), (T_FRAMES, 1)))
                y_vel.append(np.tile(kw["v"] * np.array([vx, vy]), (T_FRAMES, 1)))
                fam_ids.append(np.full(T_FRAMES, 0 if fam == "grating" else 1))
        return (np.concatenate(feats), np.concatenate(y_dir),
                np.concatenate(y_vel), np.concatenate(fam_ids))

    return collect(0), collect(100)


def r2_multi(y_true, y_pred):
    ss_res = float(((y_true - y_pred) ** 2).sum())
    ss_tot = float(((y_true - y_true.mean(axis=0)) ** 2).sum())
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def fit_ridge(x_tr, y_tr, alpha=RIDGE_ALPHA):
    mu, sd = x_tr.mean(0), x_tr.std(0)
    sd = np.where(sd < 1e-12, 1.0, sd)
    z = (x_tr - mu) / sd
    d = z.shape[1]
    w = np.linalg.solve(z.T @ z + alpha * np.eye(d), z.T @ y_tr)
    return mu, sd, w


def apply_ridge(model, x):
    mu, sd, w = model
    return (x - mu) / sd @ w


def cardinal_accuracy(y_true_dir, y_pred_dir):
    """Snap both true and predicted vectors to nearest cardinal; compare labels."""
    cards = np.array([[1, 0], [-1, 0], [0, 1], [0, -1]], dtype=float)  # R, L, D, U
    true_lab = np.argmax(y_true_dir @ cards.T, axis=1)
    pred_lab = np.argmax(y_pred_dir @ cards.T, axis=1)
    return float((pred_lab == true_lab).mean())


def evaluate_density(n, tau=TAU_BASELINE):
    (x_tr, ydir_tr, yvel_tr, fam_tr), (x_te, ydir_te, yvel_te, fam_te) = build_dataset(n, tau)
    out = {"lattice": [n, n], "dphi_cells": 1.0, "tau_frames": tau,
           "train_frames": int(len(x_tr)), "test_frames": int(len(x_te))}
    m_dir = fit_ridge(x_tr, ydir_tr)
    pred = apply_ridge(m_dir, x_te)
    out["r2_direction"] = round(r2_multi(ydir_te, pred), 6)
    out["direction_accuracy_cardinal"] = round(cardinal_accuracy(ydir_te, pred), 6)
    m_vel = fit_ridge(x_tr, yvel_tr)
    pv = apply_ridge(m_vel, x_te)
    out["r2_velocity"] = round(r2_multi(yvel_te, pv), 6)
    out["r2_direction_gratings_only"] = round(
        r2_multi(ydir_te[fam_te == 0], pred[fam_te == 0]), 6)
    out["r2_direction_blobs_only"] = round(
        r2_multi(ydir_te[fam_te == 1], pred[fam_te == 1]), 6)
    return out


# ---------------- diagnostics ----------------
def aliasing_check(n=32, tau=TAU_BASELINE, v=0.5):
    """Sweep lambda across the alias; predicted sign flip at lambda = 2*dphi = 2."""
    rng = np.random.default_rng(SEED_BASE + 777)
    meas = []
    for lam in ALIAS_LAMBDAS:
        seq = grating_scene(n, lam, v, DIRS["R"], WARMUP + T_FRAMES, rng)
        r = float(fam_codes(seq, tau)[WARMUP:, 0].mean())  # pooled D_R
        w = 2.0 * np.pi * v / lam
        pred = (np.sin(2.0 * np.pi / lam) * (w * tau) / (1.0 + (w * tau) ** 2))
        meas.append((lam, r, pred))
    # analytic-curve scale fit + shape correlation
    m = np.array([x[1] for x in meas]); p = np.array([x[2] for x in meas])
    scale = float((m @ p) / (p @ p))
    corr = float(np.corrcoef(m, p)[0, 1])
    # measured zero crossing near lambda=2 (first sign change from below 2 upward)
    cross = None
    for i in range(len(meas) - 1):
        (l0, r0, _), (l1, r1, _) = meas[i], meas[i + 1]
        if r0 == 0.0:
            cross = l0; break
        if r0 * r1 < 0:
            cross = l0 + (l1 - l0) * abs(r0) / (abs(r0) + abs(r1)); break
    return {"lambda_cells": [x[0] for x in meas],
            "pooled_D_R": [round(x[1], 8) for x in meas],
            "predicted_shape": [round(x[2], 8) for x in meas],
            "predicted_zero_crossing_lambda": 2.0,
            "measured_zero_crossing_lambda": None if cross is None else round(cross, 4),
            "shape_pearson_r": round(corr, 6),
            "fitted_scale": round(scale, 6)}


def contrast_fingerprint(n=32, tau=TAU_BASELINE, lam=8.0, v=0.5):
    """R ~ c^2: amplitude ratios vs predicted 1:4:16 (normalized to c=0.25)."""
    rng = np.random.default_rng(SEED_BASE + 888)
    meas, pred = [], []
    for c in FP_CONTRASTS:
        seq = grating_scene(n, lam, v, DIRS["R"], WARMUP + T_FRAMES, rng, contrast=c)
        r = abs(float(fam_codes(seq, tau)[WARMUP:, 0].mean()))
        meas.append(r); pred.append(c ** 2)
    meas = np.array(meas); pred = np.array(pred)
    return {"contrasts": list(FP_CONTRASTS),
            "measured_amplitude": [round(float(x), 8) for x in meas],
            "measured_ratio_vs_c025": [round(float(x / meas[0]), 4) for x in meas],
            "predicted_ratio_vs_c025": [round(float(x / pred[0]), 4) for x in pred]}


def temporal_tuning(n=32, tau=TAU_BASELINE, lam=8.0):
    """Peak of |pooled D_R| vs v; predicted v* = lam/(2*pi*tau)."""
    rng = np.random.default_rng(SEED_BASE + 999)
    meas = []
    for v in TUNE_SPEEDS:
        seq = grating_scene(n, lam, v, DIRS["R"], WARMUP + T_FRAMES, rng)
        meas.append(abs(float(fam_codes(seq, tau)[WARMUP:, 0].mean())))
    k = int(np.argmax(meas))
    return {"speeds": list(TUNE_SPEEDS),
            "amplitude": [round(float(x), 8) for x in meas],
            "measured_peak_speed": TUNE_SPEEDS[k],
            "predicted_peak_speed": round(lam / (2.0 * np.pi * tau), 4)}


# ---------------- main ----------------
def main():
    t0 = time.time()
    out = {
        "experiment": "ie1 Reichardt correlators -> 4 motion fam codes (lobula-plate rung)",
        "date": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "science": "docs/insect-vision-science-2026-09-28.md S1.2/S1.5/S2.2-2.3/S4",
        "hrc": "R = c^2 sin(2 pi dphi/lambda) w tau / (1+(w tau)^2); "
               "delay-LP + multiply + mirror-subtract on adjacent pairs; signed inputs",
        "cpu_only": True, "numpy_version": np.__version__,
        "config": {
            "tau_baseline_frames": TAU_BASELINE,
            "densities": list(DENSITIES), "dphi_cells": 1.0,
            "warmup_frames": WARMUP, "kept_frames": T_FRAMES,
            "train_seqs_per_cfg": N_TRAIN_SEQ, "test_seqs_per_cfg": N_TEST_SEQ,
            "grating_lambdas": list(GRAT_LAMBDAS), "grating_speeds": list(GRAT_SPEEDS),
            "blob_sigmas": list(BLOB_SIGMAS), "blob_speeds": list(BLOB_SPEEDS),
            "directions": DIR_ORDER, "contrast": CONTRAST,
            "ridge_alpha": RIDGE_ALPHA, "seed_base": SEED_BASE,
            "gate": f"R^2(direction) >= {GATE_THRESHOLD} at >= {GATE_MIN_DENSITIES} "
                    f"of {len(DENSITIES)} densities, tau={TAU_BASELINE} frames",
        },
        "gate_by_density": {},
        "tau_sweep_density16": {},
        "aliasing_check": {},
        "contrast_fingerprint": {},
        "temporal_tuning": {},
    }
    print("[ie1] gate: ridge direction decode from 4 fam codes, tau=2", flush=True)
    for n in DENSITIES:
        res = evaluate_density(n)
        out["gate_by_density"][str(n)] = res
        print(f"[ie1] density {n}x{n}: R2_dir={res['r2_direction']} "
              f"acc={res['direction_accuracy_cardinal']} R2_vel={res['r2_velocity']}", flush=True)
    passing = [n for n in DENSITIES
               if out["gate_by_density"][str(n)]["r2_direction"] >= GATE_THRESHOLD]
    out["gate_densities_passing"] = len(passing)
    out["verdict"] = ("KEEP" if len(passing) >= GATE_MIN_DENSITIES else "KILL")
    print(f"[ie1] GATE: {len(passing)}/{len(DENSITIES)} densities >= {GATE_THRESHOLD} "
          f"-> {out['verdict']}", flush=True)

    print("[ie1] tau sweep (density 16, descriptive)", flush=True)
    for tau in TAU_SWEEP:
        res = evaluate_density(16, tau)
        out["tau_sweep_density16"][str(tau)] = {
            "r2_direction": res["r2_direction"], "r2_velocity": res["r2_velocity"]}
        print(f"[ie1]   tau={tau}: R2_dir={res['r2_direction']}", flush=True)

    out["aliasing_check"] = aliasing_check()
    print(f"[ie1] aliasing: zero-crossing at lambda="
          f"{out['aliasing_check']['measured_zero_crossing_lambda']} "
          f"(predicted 2.0), shape r={out['aliasing_check']['shape_pearson_r']}", flush=True)
    out["contrast_fingerprint"] = contrast_fingerprint()
    print(f"[ie1] c^2 fingerprint ratios: {out['contrast_fingerprint']['measured_ratio_vs_c025']} "
          f"(predicted {out['contrast_fingerprint']['predicted_ratio_vs_c025']})", flush=True)
    out["temporal_tuning"] = temporal_tuning()
    print(f"[ie1] temporal peak v={out['temporal_tuning']['measured_peak_speed']} "
          f"(predicted {out['temporal_tuning']['predicted_peak_speed']})", flush=True)

    out["seconds"] = round(time.time() - t0, 1)
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "ie1_reichardt.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({k: out[k] for k in
                      ("verdict", "gate_densities_passing", "gate_by_density",
                       "aliasing_check", "contrast_fingerprint", "temporal_tuning",
                       "tau_sweep_density16", "seconds")}, indent=2))


if __name__ == "__main__":
    main()
