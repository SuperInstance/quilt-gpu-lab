#!/usr/bin/env python3
"""X3 — stats-battery parity: is the JEPA dial-read more than classic image
statistics?  (Wave-2 contrarian falsifier X3, pre-registered in SPOOL.md)

CLAIM UNDER TEST (concrete, falsifiable)
  E12's KEEP ("a frozen I-JEPA linearly reads staged mood/volume/presence",
  R²_k64 = 0.811/0.962/0.948, leave-one-room-out) controlled for exactly ONE
  trivial visual correlate: per-still MEAN luminance. That control is too
  weak to license "the encoder found something deep". X3 builds the real
  null: a ~24-dim battery of classic image statistics (colour moments,
  grayscale histogram percentiles, Fourier band energies, Michelson contrast,
  Sobel edge density/energy, spatial autocorrelations) and reads the SAME
  dials from it with the SAME LORO ridge, on the SAME 27-room staged bank,
  next to (b) the frozen I-JEPA embedding (E12's pipeline, reproduced live)
  and (c) E12's raw-pixel control. If a trivial battery matches I-JEPA on
  volume/presence, "JEPA reads the room" is decoration — the statistics were
  carrying the signal all along.

ARMS — one bank, four feature sets, ONE probe (fairness by construction)
  All four feature sets are read by the identical probe path: standardize →
  ridge with per-fold inner-CV λ (E12's loro_predict) → leave-one-ROOM-out →
  room-level LORO check → 200 room-level label shuffles (fixed λ = median
  fold λ) → Spearman. Nothing about the probe favours the embedding.
    lum1   : per-still mean luminance, 1-d — E12's original (weak) control,
             kept so X3 shows exactly what it replaces.
    stats  : THE BATTERY, 24-d, computed on the native 160x90 still:
             mean/std/skew per RGB channel (9), gray percentiles
             p5/p25/p50/p75/p95 (5), Michelson contrast (1), log Fourier
             power in low/mid/high radial bands (3), Sobel edge density
             (fraction |grad| > 0.15) (1), mean Sobel magnitude (1),
             spatial autocorrelation lag-1/lag-2 along x and y (4).
             numpy-only, no cv2/sklearn; deterministic per still.
    pixels : E12's C1 control verbatim — 16x9 grayscale downsample (144-d),
             from embed_stills.
    jepa   : frozen I-JEPA (facebook/ijepa_vith16_1k, fp16, mean-pooled,
             L2-normalized), PCA k=64 (E12's PRIMARY space, label-free basis
             on all embeddings). k=16 booked as a line.

BANK
  E12's Arm B verbatim, by import: build_dial_grid() 27 rooms over
  m ∈ {-0.8,0,+0.8}, v,p ∈ {0.15,0.50,0.85}; labels are the ELEPHANT's own
  DialBank readings of staged scripts (never hand-typed); frames are
  stage_source renders (ffmpeg lavfi), 12 evenly spaced stills each (E12's
  embed_stills sampling, re-derived identically for the battery).
  Deterministic (seed 2718) — E25's C6 showed this bank reproduces E12's
  numbers bit-for-bit, so the jepa row should land on 0.811/0.962/0.948.

PRE-REGISTERED GATES (fixed before running; this file IS the registration)
  G0d harness self-test : E13's harness_selftest (model-free, CPU-only) must
      pass — else INVALID_HARNESS (a KILL from a broken probe is noise).
  G0a staging fidelity  : Spearman(target, elephant_label) ≥ 0.5 for ≥ 2/3
      dials — E12's G0a verbatim; else INVALID_STAGING.
  G0b battery sensitivity: the battery must read per-still mean luminance at
      LORO R² ≥ 0.90 (luminance is a linear function of the battery's channel
      means — a battery that misses it is broken); else INVALID_HARNESS.
  G1  THE GATE (on labels, per dial d ∈ {volume, presence}):
        gap_d := R²_jepa_k64(d) − R²_stats(d)
        KILL         : gap_d ≤ 0.10 for BOTH dials — the battery is within
                       0.10 R² of I-JEPA on the semantic pair; the JEPA story
                       is decoration for volume/presence.
        KEEP         : gap_d > 0.10 for BOTH dials — I-JEPA beats the battery
                       by more than 0.10 R² on the semantic pair.
        INCONCLUSIVE : mixed, OR the dead-dead guard fires (below).
      mood is REPORTED in the full table but not gated (mood is known to ride
      colour temperature — the battery will match it there; the claim at risk
      is volume/presence, per the SPOOL entry).
  DEAD-DEAD GUARD (validity, not a gate change): if stats AND jepa BOTH sit
      at/below their own 200-perm 95th percentiles on BOTH gated dials, the
      comparison is two dead reads and the verdict is INCONCLUSIVE (never a
      KILL or KEEP off null-level noise). This can only move cases toward
      INCONCLUSIVE, which the pre-registered ladder already allows.

CONTROLS / BOOKED (never gated)
  C1 raw-pixel R²       : E12's C1, same LORO ridge, full table row.
  C2 luminance row      : the 1-d control, full table row — the thing X3
                          replaces, shown degraded for contrast.
  C3 permutation nulls  : 200 room-level shuffles per feature set (fixed
                          λ = median fold λ, E12's convention), reported as
                          null95 + permutation p per dial per set.
  C4 jepa k16           : top-16-PC retention line for the embedding.
  C5 battery ranges     : per-dim min/max/std/n-unique + dead-dim count
                          (a constant battery dim would be a broken battery).
  C6 E12 reference      : E12's published k64 numbers booked next to the
                          re-run jepa row (same seeds — a drift check).

DATA THE GATE NEEDS
  - ffmpeg ~/.local/bin/ffmpeg (lavfi: color, eq, noise, drawbox) — E12's chain.
  - facebook/ijepa_vith16_1k fp16 weights on the RTX 4050 (E9 loader).
  - the elephant package importable (dial bank = labels).
  - 27 rooms × 12 stills = 324 encoder forwards at 224² → ~3-5 min GPU
    (whole run ~5-8 min including ffmpeg renders and the CPU probe sweep).
  - GPU free (checked via nvidia-smi before firing; guard preflights again
    in-process).

HONESTY / CAVEATS BOOKED WITH THE RESULT
  - Carriers are still STAGED (E12's standing caveat); X3 tests whether the
    E12/E13/E15 result survives a REAL null model, not natural feeds.
  - The battery is linear-shot only (ridge): a battery + nonlinear reader is
    a further escalation not run here (mirror of E13b's reader question).
  - "Within 0.10 R²" is the SPOOL pre-registration's own threshold; it is
    coarse, but it was fixed before this file existed.
  - 27 rooms: every LORO fold trains on 26 rooms / 312 stills — room-level
    probes are width-13 (overdetermined), the strict check.
  - The PCA basis (jepa) and the standardization (all sets) are label-free,
    fit on all stills — E12's convention, no label leakage.

Verdict printed as ONE JSON object on stdout (progress on stderr).
Deterministic (seed 2718). CPU-only probe; GPU only for encoder forwards.

Dev path: `python -m experiments.x3_stats_battery --cpu-only` runs everything
except the encoder (self-test, bank, fidelity, battery smoke on real ffmpeg
renders, probe-path synthetic check) with no model and no GPU.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

# BLAS thread cap — E12/E13's reason verbatim: the probe does thousands of
# tiny ridge solves; uncapped BLAS turns each into a thread storm. Must be
# set BEFORE numpy loads (this module imports E12, which imports numpy).
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np  # noqa: E402

try:  # belt-and-braces for callers that imported numpy before this module
    from threadpoolctl import threadpool_limits  # noqa: E402
    _BLAS_LIMIT = threadpool_limits(limits=4)
    _BLAS_LIMIT.__enter__()
except Exception:  # threadpoolctl absent — the env vars above still apply
    _BLAS_LIMIT = None

SEED = 2718
LAB = Path(__file__).resolve().parents[1]
ELEPHANT = Path.home() / "projects" / "elephant"
for _p in (str(LAB), str(LAB / "experiments"), str(ELEPHANT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common import ppms_from_lavfi                            # noqa: E402
from e9_ijepa_stills import (                                 # noqa: E402
    N_STILLS, load_encoder, preflight_guard,
)

# E12 is imported VERBATIM — bank, staging, probe machinery. X3 changes
# exactly one thing: the FEATURE SET read by the probe.
from e12_room_dial_reader import (                            # noqa: E402
    DIAL_NAMES, EXTRA_DIALS, FIDELITY_FLOOR, GRID_M, GRID_P, GRID_V,
    K_PRIMARY, K_STRICT, RATE, SECONDS, W, H, _boxes, build_dial_grid,
    embed_stills, loro_predict, pca_basis, perm_null, r2_columns, read_room,
    room_from_script, room_means, spearman, stage_source, stage_transcript,
)
from e13_nonlinear_dial_reader import harness_selftest        # noqa: E402

# --------------------------------------------------------------------- #
# Pre-registered constants                                              #
# --------------------------------------------------------------------- #
PARITY_EPS = 0.10          # the SPOOL X3 threshold: "within 0.10 R² of I-JEPA"
GATED_DIALS = ("volume", "presence")
PERMS = 200                # room-level label shuffles per feature set
BATT_LUM_FLOOR = 0.90      # G0b: battery must read mean luminance
PERM_SEEDS = {"lum1": SEED + 34, "stats": SEED + 31, "pixels": SEED + 33,
              "jepa": SEED + 32}

# E12's published numbers (RESULTS.md / E15's booked reference), for C6.
E12_PUBLISHED = {
    "verdict": "KEEP", "date": "2026-09-28",
    "r2_still_loro_k64": {"mood": 0.811, "volume": 0.962, "presence": 0.948},
    "r2_room_loro_k64": {"mood": 0.890, "volume": 0.972, "presence": 0.937},
}

STATS_NAMES = [
    "r_mean", "r_std", "r_skew",
    "g_mean", "g_std", "g_skew",
    "b_mean", "b_std", "b_skew",
    "gray_p5", "gray_p25", "gray_p50", "gray_p75", "gray_p95",
    "michelson_contrast",
    "fft_low_log", "fft_mid_log", "fft_high_log",
    "edge_density", "sobel_mean",
    "autocorr_x1", "autocorr_x2", "autocorr_y1", "autocorr_y2",
]
FOURIER_BANDS = ((0.0, 0.10), (0.10, 0.30), (0.30, 10.0))  # cycles/pixel radii
EDGE_THRESH = 0.15         # on [0,1] grayscale Sobel magnitude


def log(msg: str) -> None:
    """Progress goes to stderr; stdout is reserved for the JSON verdict."""
    print(f"[x3] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------- #
# The stats battery (numpy-only, deterministic, per still)               #
# --------------------------------------------------------------------- #
def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, float).ravel()
    b = np.asarray(b, float).ravel()
    sa, sb = a.std(), b.std()
    if sa < 1e-12 or sb < 1e-12:
        return 0.0
    c = float(np.corrcoef(a, b)[0, 1])
    return c if math.isfinite(c) else 0.0


def _sobel(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sobel gradient via explicit shifts (reflect pad) — no cv2/scipy."""
    p = np.pad(gray, 1, mode="reflect")
    gx = ((p[0:-2, 2:] + 2.0 * p[1:-1, 2:] + p[2:, 2:])
          - (p[0:-2, 0:-2] + 2.0 * p[1:-1, 0:-2] + p[2:, 0:-2]))
    gy = ((p[2:, 0:-2] + 2.0 * p[2:, 1:-1] + p[2:, 2:])
          - (p[0:-2, 0:-2] + 2.0 * p[0:-2, 1:-1] + p[0:-2, 2:]))
    return gx, gy


def stats_battery(img: np.ndarray) -> np.ndarray:
    """(H, W, 3) uint8 still -> 24-d classic-statistics vector (see docstring)."""
    x = np.asarray(img, np.float64) / 255.0
    gray = x.mean(axis=2)
    feats: list[float] = []
    # 1-9: colour moments per channel
    for c in range(3):
        ch = x[:, :, c]
        mu = float(ch.mean())
        sd = float(ch.std())
        feats += [mu, sd,
                  (float(((ch - mu) ** 3).mean()) / max(sd, 1e-12) ** 3)
                  if sd > 1e-12 else 0.0]
    # 10-14: grayscale histogram percentiles
    q = np.percentile(gray, [5, 25, 50, 75, 95])
    feats += [float(v) for v in q]
    # 15: Michelson contrast from the same percentiles
    p5, p95 = float(q[0]), float(q[4])
    feats.append((p95 - p5) / max(p95 + p5, 1e-6))
    # 16-18: radial Fourier band power (log10), cycles/pixel bands
    F = np.fft.rfft2(gray)
    P = np.abs(F) ** 2
    fy = np.fft.fftfreq(gray.shape[0])[:, None]
    fx = np.fft.rfftfreq(gray.shape[1])[None, :]
    r = np.sqrt(fy * fy + fx * fx)
    for lo, hi in FOURIER_BANDS:
        m = (r >= lo) & (r < hi)
        feats.append(math.log10(float(P[m].mean()) + 1e-12) if m.any()
                     else -12.0)
    # 19-20: Sobel edge density + mean gradient magnitude
    gx, gy = _sobel(gray)
    mag = np.sqrt(gx * gx + gy * gy)
    feats.append(float((mag > EDGE_THRESH).mean()))
    feats.append(float(mag.mean()))
    # 21-24: spatial autocorrelation, lags 1-2 along x and y
    feats.append(_pearson(gray[:, :-1], gray[:, 1:]))
    feats.append(_pearson(gray[:, :-2], gray[:, 2:]))
    feats.append(_pearson(gray[:-1, :], gray[1:, :]))
    feats.append(_pearson(gray[:-2, :], gray[2:, :]))
    out = np.asarray(feats, float)
    assert out.shape == (len(STATS_NAMES),), out.shape
    return out


# --------------------------------------------------------------------- #
# Bank (labels only — E12's Arm B) and still collection                  #
# --------------------------------------------------------------------- #
def build_bank() -> list:
    """E12's 27-cell grid with the elephant's own labels (never hand-typed)."""
    bank = []
    for r in build_dial_grid():
        m, v, p = r["target"]
        script = stage_transcript(m, v, p, r["seed"])
        readings = read_room(room_from_script(r["name"], script))
        bank.append({
            "name": r["name"], "seed": int(r["seed"]),
            "target": np.array([m, v, p], float),
            "label": np.array([readings.get(d, 0.0) for d in DIAL_NAMES], float),
            "extra": {d: round(float(readings.get(d, 0.0)), 6) for d in EXTRA_DIALS},
        })
    return bank


def collect(model, processor, dev, torch):
    """Render + embed all 27 rooms. embed_stills re-derives E12's linspace
    still sampling internally; the battery uses the identical stills by
    re-deriving the same indices here (same frames list, same rule)."""
    X, Y, Yt, G, LUM, PIX, S, names = [], [], [], [], [], [], [], []
    rooms = build_bank()
    for gi, r in enumerate(rooms):
        src = stage_source(*[float(t) for t in r["target"]], r["seed"])
        frames = ppms_from_lavfi(src, SECONDS, RATE, (W, H))
        if not frames:
            raise RuntimeError(f"no frames from staged source {r['name']!r}")
        idx = np.linspace(0, len(frames) - 1, N_STILLS).round().astype(int)
        stills = [frames[i] for i in idx]
        vecs, lum, pix = embed_stills(model, processor, dev, frames, r["seed"])
        bat = np.stack([stats_battery(s) for s in stills])
        groups = np.full(len(vecs), gi)
        X.append(vecs)
        Y.append(np.repeat(r["label"][None, :], len(vecs), axis=0))
        Yt.append(np.repeat(r["target"][None, :], len(vecs), axis=0))
        G.append(groups)
        LUM.append(lum)
        PIX.append(pix)
        S.append(bat)
        names.append(r["name"])
        if dev == "cuda":
            torch.cuda.empty_cache()
        if (gi + 1) % 9 == 0 or gi == 0:
            log(f"room {gi + 1}/{len(rooms)} {r['name']} "
                f"label={np.round(r['label'], 3).tolist()}")
    return (np.concatenate(X), np.concatenate(Y), np.concatenate(Yt),
            np.concatenate(G), np.concatenate(LUM), np.concatenate(PIX),
            np.concatenate(S), names)


# --------------------------------------------------------------------- #
# ONE probe for every feature set (fairness by construction)             #
# --------------------------------------------------------------------- #
def feature_probe(Z: np.ndarray, Y: np.ndarray, groups: np.ndarray,
                  perms: int, seed: int) -> dict:
    """Standardize -> LORO ridge (per-fold inner-CV lambda) -> room-level
    LORO (width min(dim, max(4, n_rooms//2)), overdetermined) -> 200-shuffle
    null at fixed lambda -> Spearman. E12's machinery throughout."""
    z = (np.asarray(Z, float) - np.asarray(Z, float).mean(0)) \
        / (np.asarray(Z, float).std(0) + 1e-8)
    pred, lam_med = loro_predict(z, Y, groups, lam=None)
    r2 = r2_columns(Y, pred)
    Xr, Yr, ids = room_means(z, Y, groups)
    k_room = int(min(z.shape[1], max(4, len(ids) // 2)))
    pred_r, _ = loro_predict(Xr[:, :k_room], Yr, np.arange(len(ids)), lam=None)
    r2r = r2_columns(Yr, pred_r)
    null = perm_null(z, Y, groups, lam_med, perms, seed)
    null95 = np.percentile(null, 95, axis=0)
    return {
        "dim": int(z.shape[1]), "room_probe_width": k_room,
        "lambda_median": round(float(lam_med), 6),
        "r2_still_loro": {d: round(float(r2[i]), 4)
                          for i, d in enumerate(DIAL_NAMES)},
        "r2_room_loro": {d: round(float(r2r[i]), 4)
                         for i, d in enumerate(DIAL_NAMES)},
        "spearman_loro": {d: round(float(spearman(Y[:, i], pred[:, i])), 4)
                          for i, d in enumerate(DIAL_NAMES)},
        "perm_null95": {d: round(float(null95[i]), 4)
                        for i, d in enumerate(DIAL_NAMES)},
        "perm_p": {d: round(float((null[:, i] >= r2[i]).mean()), 4)
                   for i, d in enumerate(DIAL_NAMES)},
        "_r2_vec": r2, "_null95_vec": null95,
    }


def _strip(pr: dict) -> dict:
    return {k: v for k, v in pr.items() if not k.startswith("_")}


# --------------------------------------------------------------------- #
# CPU-only mode (no model, no GPU): the plumbing test                    #
# --------------------------------------------------------------------- #
def _probe_synthetic_check() -> dict:
    """feature_probe itself (standardize + room-level + null) on a synthetic
    bank with a known linear signal: must read >= 0.9 still and room, and
    collapse under label shuffle."""
    rng = np.random.default_rng(SEED + 5)
    n_rooms, n_still, d = 12, 6, 40
    T = rng.uniform(-1.0, 1.0, (n_rooms, 3))
    A = rng.standard_normal((3, d))
    Z = np.repeat(T @ A, n_still, 0) + 0.02 * rng.standard_normal((n_rooms * n_still, d))
    groups = np.repeat(np.arange(n_rooms), n_still)
    Y = np.repeat(T, n_still, 0)
    pr = feature_probe(Z, Y, groups, perms=20, seed=SEED + 6)
    perm = rng.permutation(n_rooms)
    pr_null = feature_probe(Z, np.repeat(T[perm], n_still, 0), groups,
                            perms=5, seed=SEED + 7)
    return {
        "r2_min_still": round(float(pr["_r2_vec"].min()), 4),
        "r2_min_room": round(float(min(pr["r2_room_loro"].values())), 4),
        "r2_max_shuffled_still": round(float(pr_null["_r2_vec"].max()), 4),
        "pass": bool(pr["_r2_vec"].min() >= 0.90
                     and min(pr["r2_room_loro"].values()) >= 0.90
                     and pr_null["_r2_vec"].max() < 0.10),
    }


def cpu_only() -> dict:
    st = harness_selftest()
    pchk = _probe_synthetic_check()
    bank = build_bank()
    targets = np.stack([r["target"] for r in bank])
    labels = np.stack([r["label"] for r in bank])
    fid = {d: round(spearman(targets[:, i], labels[:, i]), 4)
           for i, d in enumerate(DIAL_NAMES)}
    # battery smoke on REAL ffmpeg renders of 3 grid rooms (spanning corners)
    smoke = []
    for r in (bank[0], bank[13], bank[26]):
        src = stage_source(*[float(t) for t in r["target"]], r["seed"])
        frames = ppms_from_lavfi(src, SECONDS, RATE, (W, H))
        idx = np.linspace(0, len(frames) - 1, N_STILLS).round().astype(int)
        smoke.append(np.stack([stats_battery(frames[i]) for i in idx]))
    bat = np.concatenate(smoke)
    ranges = {n: {"min": round(float(bat[:, j].min()), 4),
                  "max": round(float(bat[:, j].max()), 4),
                  "std": round(float(bat[:, j].std()), 4)}
              for j, n in enumerate(STATS_NAMES)}
    dead = [STATS_NAMES[j] for j in range(bat.shape[1])
            if bat[:, j].std() < 1e-9]
    out = {
        "experiment": "X3 stats-battery parity",
        "mode": "cpu-only (no model, no GPU)",
        "seed": SEED,
        "harness_selftest_e13": st,
        "probe_synthetic_check": pchk,
        "rooms": len(bank),
        "staging_fidelity_spearman_target_vs_label": fid,
        "battery_dim": int(bat.shape[1]),
        "battery_names": STATS_NAMES,
        "battery_smoke": {"rooms": 3, "stills": int(bat.shape[0]),
                          "ranges": ranges, "dead_dims": dead},
        "note": ("No verdict in CPU-only mode. Watch: harness_selftest and "
                 "probe_synthetic_check must pass, fidelity >= 0.5 on >= 2/3 "
                 "dials, and the battery must show no dead dims across real "
                 "renders."),
    }
    print(json.dumps(out, indent=2))
    return out


# --------------------------------------------------------------------- #
# Main                                                                  #
# --------------------------------------------------------------------- #
def main() -> dict:
    if "--cpu-only" in sys.argv:
        return cpu_only()

    ok, reason, guard_info = preflight_guard()
    if not ok:
        out = {"experiment": "X3 stats-battery parity", "verdict": "ABORTED",
               "reason": reason, "guard_preflight": guard_info}
        print(json.dumps(out, indent=2))
        return out

    # G0d — cheapest validity gate first (model-free probe-path check).
    selftest = harness_selftest()
    log(f"harness self-test: {selftest}")

    base = {"experiment": "X3 stats-battery parity", "seed": SEED,
            "dial_names": DIAL_NAMES, "gated_dials": list(GATED_DIALS),
            "parity_eps": PARITY_EPS, "k_primary": K_PRIMARY,
            "guard_preflight": guard_info, "e12_published_reference": E12_PUBLISHED}
    if not selftest["pass"]:
        out = dict(base)
        out.update({"verdict": "INVALID_HARNESS",
                    "reason": "G0d: E13's probe-path self-test failed"})
        print(json.dumps(out, indent=2))
        return out

    bank = build_bank()
    targets = np.stack([r["target"] for r in bank])
    labels = np.stack([r["label"] for r in bank])
    fid = {d: round(spearman(targets[:, i], labels[:, i]), 4)
           for i, d in enumerate(DIAL_NAMES)}
    fid_pass = bool(sum(1 for d in DIAL_NAMES if fid[d] >= FIDELITY_FLOOR) >= 2)
    if len(bank) < 8 or not fid_pass:
        out = dict(base)
        out.update({"verdict": "INVALID_STAGING",
                    "staging_fidelity_spearman_target_vs_label": fid,
                    "reason": "G0a: staging fidelity failed (dead staging)"})
        print(json.dumps(out, indent=2))
        return out

    import torch
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    log(f"loading I-JEPA ({dev})...")
    try:
        model_used, model, processor, load_notes = load_encoder(dev)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest": selftest,
                    "reason": f"model load failed: {e}"})
        print(json.dumps(out, indent=2))
        return out
    log(f"using {model_used}")

    try:
        (X, Y, Yt, G, LUM, PIX, S, names) = collect(model, processor, dev, torch)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest": selftest,
                    "staging_fidelity_spearman_target_vs_label": fid,
                    "reason": f"frame/embed failed: {e}"})
        print(json.dumps(out, indent=2))
        return out

    if len(np.unique(G)) < 8:
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest": selftest,
                    "reason": f"only {len(np.unique(G))} rooms — grouped CV meaningless"})
        print(json.dumps(out, indent=2))
        return out

    # ---- the four feature sets, ONE probe path ----
    log("probing lum1 / stats / pixels / jepa (LORO ridge + 200-perm nulls)...")
    probes: dict = {}
    probes["lum1"] = feature_probe(LUM.reshape(-1, 1).astype(np.float64),
                                   Y, G, PERMS, PERM_SEEDS["lum1"])
    probes["stats"] = feature_probe(S, Y, G, PERMS, PERM_SEEDS["stats"])
    probes["pixels"] = feature_probe(PIX.astype(np.float64), Y, G,
                                     PERMS, PERM_SEEDS["pixels"])
    basis, evr = pca_basis(X, K_PRIMARY)
    z64 = X @ basis[:, :K_PRIMARY]
    probes["jepa"] = feature_probe(z64, Y, G, PERMS, PERM_SEEDS["jepa"])
    # C4 — k16 line (still-level only, booked)
    pred16, _ = loro_predict(X @ basis[:, :K_STRICT], Y, G)
    r2_16 = r2_columns(Y, pred16)
    jepa_k16 = {d: round(float(r2_16[i]), 4) for i, d in enumerate(DIAL_NAMES)}

    # C5 — battery ranges / dead dims
    ranges = {n: {"min": round(float(S[:, j].min()), 4),
                  "max": round(float(S[:, j].max()), 4),
                  "std": round(float(S[:, j].std()), 4),
                  "n_unique": int(len(np.unique(np.round(S[:, j], 6))))}
              for j, n in enumerate(STATS_NAMES)}
    dead_dims = [STATS_NAMES[j] for j in range(S.shape[1]) if S[:, j].std() < 1e-9]

    # G0b — battery sensitivity (must read the luminance it contains)
    sens = probes["stats"]["r2_still_loro"]  # not the right target; do a direct read
    pred_lum_stats, _ = loro_predict((S - S.mean(0)) / (S.std(0) + 1e-8),
                                     LUM.reshape(-1, 1).astype(np.float64), G)
    r2_stats_lum = float(r2_columns(LUM.reshape(-1, 1).astype(np.float64),
                                    pred_lum_stats)[0])
    sens_pass = bool(r2_stats_lum >= BATT_LUM_FLOOR)
    if not sens_pass:
        out = dict(base)
        out.update({"verdict": "INVALID_HARNESS",
                    "harness_selftest": selftest,
                    "g0b_battery_luminance_r2": round(r2_stats_lum, 4),
                    "reason": "G0b: the battery cannot read mean luminance — broken battery"})
        print(json.dumps(out, indent=2))
        return out

    # ---- G1: the pre-registered parity gate ----
    jepa_r2 = probes["jepa"]["_r2_vec"]
    stats_r2 = probes["stats"]["_r2_vec"]
    di = {d: i for i, d in enumerate(DIAL_NAMES)}
    gaps_all = {d: round(float(jepa_r2[di[d]] - stats_r2[di[d]]), 4)
                for d in DIAL_NAMES}
    gaps = {d: gaps_all[d] for d in GATED_DIALS}
    parity = all(g <= PARITY_EPS for g in gaps.values())
    jepa_wins = all(g > PARITY_EPS for g in gaps.values())
    stats_dead = all(probes["stats"]["perm_null95"][d]
                     >= probes["stats"]["r2_still_loro"][d] for d in GATED_DIALS)
    jepa_dead = all(probes["jepa"]["perm_null95"][d]
                    >= probes["jepa"]["r2_still_loro"][d] for d in GATED_DIALS)
    dead_dead = bool(stats_dead and jepa_dead)

    if dead_dead:
        verdict = "INCONCLUSIVE"
        verdict_reason = ("dead-dead guard: stats AND jepa are both at/below "
                          "their permutation nulls on volume+presence — two "
                          "dead reads, not a parity result")
    elif parity:
        verdict = "KILL"
        verdict_reason = (f"stats battery within {PARITY_EPS} R² of I-JEPA on "
                          f"both gated dials (gaps {gaps}) — the JEPA story is "
                          "decoration for volume/presence")
    elif jepa_wins:
        verdict = "KEEP"
        verdict_reason = (f"I-JEPA beats the battery by > {PARITY_EPS} R² on "
                          f"both gated dials (gaps {gaps})")
    else:
        verdict = "INCONCLUSIVE"
        verdict_reason = f"mixed gaps across the gated pair: {gaps}"

    out = dict(base)
    out.update({
        "model": model_used, "device": dev, "load_notes": load_notes,
        "rooms": len(names), "stills_per_room": N_STILLS,
        "cells": int(X.shape[0]),
        "harness_selftest_e13": selftest,
        "staging_fidelity_spearman_target_vs_label": fid,
        "g0a_staging_fidelity_pass": fid_pass,
        "battery": {
            "dim": int(S.shape[1]), "names": STATS_NAMES,
            "fourier_bands_cyc_per_px": FOURIER_BANDS,
            "edge_threshold": EDGE_THRESH,
            "ranges": ranges, "dead_dims": dead_dims,
        },
        "comparison": {
            "lum1_1d": _strip(probes["lum1"]),
            "stats_battery_24d": _strip(probes["stats"]),
            "raw_pixels_144d": _strip(probes["pixels"]),
            "ijepa_k64": _strip(probes["jepa"]),
            "ijepa_k16_still_only": jepa_k16,
            "pca_evr_k16": round(float(evr[:K_STRICT].sum()), 4),
            "pca_evr_k64": round(float(evr[:K_PRIMARY].sum()), 4),
        },
        "gaps_jepa_minus_stats": gaps_all,
        "gates": {
            "g0d_harness_selftest": selftest["pass"],
            "g0a_staging_fidelity": {"floor": FIDELITY_FLOOR, "pass": fid_pass},
            "g0b_battery_luminance": {"floor": BATT_LUM_FLOOR,
                                      "measured": round(r2_stats_lum, 4),
                                      "pass": sens_pass},
            "g1_parity": {"rule": f"KILL iff max gap over {list(GATED_DIALS)} "
                                  f"<= {PARITY_EPS}; KEEP iff min gap > {PARITY_EPS}",
                          "gaps": gaps, "parity": bool(parity),
                          "jepa_wins": bool(jepa_wins)},
            "dead_dead_guard": {"stats_at_null": bool(stats_dead),
                                "jepa_at_null": bool(jepa_dead),
                                "fired": dead_dead},
        },
        "conclusion_rule": (
            "KILL = stats within 0.10 R² of I-JEPA on volume AND presence "
            "(JEPA story decoration). KEEP = I-JEPA beats stats by > 0.10 R² "
            "on both. INCONCLUSIVE otherwise, including the dead-dead guard "
            "(both reads at/below their own 200-perm nulls on the gated pair)."),
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "data_needed": [
            "ffmpeg ~/.local/bin/ffmpeg (E12's lavfi chain)",
            "facebook/ijepa_vith16_1k fp16 on the RTX 4050 (E9 loader)",
            "elephant package importable (dial bank = labels)",
            f"27 rooms x {N_STILLS} stills = 324 forwards — ~3-5 min GPU; "
            "whole run ~5-8 min",
        ],
        "note": (
            "X3 replaces E12's mean-luminance control with a 24-d classic "
            "statistics battery read by the SAME LORO ridge on the SAME bank "
            "and labels as I-JEPA. The gate is the SPOOL X3 pre-registration "
            "verbatim, restricted to volume/presence (mood is known to ride "
            "colour temperature and is reported, not gated). The dead-dead "
            "guard can only move a case to INCONCLUSIVE (two null-level reads "
            "are not a parity result). Scope: staged carriers, linear probe "
            "on the battery, 27 rooms — a KILL here demotes E12/E15's "
            "volume/presence read to 'classic statistics do it too'; a KEEP "
            "survives the strongest cheap null in the room."),
    })
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
