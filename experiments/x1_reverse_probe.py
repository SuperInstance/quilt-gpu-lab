#!/usr/bin/env python3
"""X1 — REVERSE probe: how much of the EMBEDDING VARIANCE do the dials explain?

THE KILL-SHOT (SPOOL.md Wave-2, X1 — "HIGHEST VALUE, trivial")
  Every result in this lab so far (E12/E13/E13b/E15/E25/E26) is a FORWARD probe:
  embedding -> dial. All of them report high R² (E12: 0.811/0.962/0.948 at
  k=64) and that number has been carrying the "the frozen JEPA is a
  room-temperature sense" framing. Nobody measured the REVERSE direction.

  Forward R² answers "can a reader, TOLD the dials exist at training time,
  recover them?" — i.e. can an elephant that has already been HANDED the labels
  read them. Reverse R² answers the question that actually decides the framing:
  "how much of the embedding's VARIANCE lies in the 3-dial direction at all?"
  If the dials' linear span accounts for <10% of embedding variance, then the
  dials are a thin, high-SNR needle in a haystack — and an elephant with no
  labels has no reason to ever find that needle. Good forward R² and tiny
  reverse R² are NOT a contradiction; they are the definition of a
  label-requiring signal. That is exactly why this is the kill-shot.

CLAIM UNDER TEST (pre-registered)
  H1 (framing lives): the 3 dials linearly explain > 0.40 of embedding variance
      (mean per-dimension LORO reverse-R²) -> the room-temperature sense is a
      broad property of the representation.
  H0 (framing dies): mean reverse-R² < 0.10 -> the dials are a tiny corner of
      the embedding; the elephant could never bootstrap them without labels,
      whatever the forward R² says.

WHAT IS MEASURED (all reuse E12 verbatim — bank, collector, embed, ridge)
  Primary:
    mean_reverse_r2 = mean over the 1280 embedding dims of the leave-one-room-
    out ridge R² when THAT dim is predicted from the 3 elephant dial labels
    (mood/volume/presence).  Still-level, exactly mirroring E12's still-level
    forward read, so the two numbers are apples-to-apples.  Per-dim lambda,
    chosen by inner grouped CV on the same pooled-SSE statistic the gate
    reports (targets column-standardized first; see reverse_fit for the two
    lambda-selection artifacts caught in the --cpu-only smoke).  The
    one-shared-lambda reading is booked alongside (shared_lambda_read).
  Booked aggregates:
    - median per-dim R²;
    - variance-weighted R² = 1 - sum_j SSE_j / sum_j SS_j — the literal
      "fraction of embedding variance the dials explain" (this is algebraically
      the sum of squared canonical correlations between the dials and the
      embedding, i.e. the dial-aligned variance fraction);
    - room-level reverse read (27 room-mean embeddings from 27 room dials) —
      the version with NO within-room still noise deflating it;
    - the ANOVA between-room CEILING (mean per-dim SS_between/SS_total) — the
      hard upper bound on ANY room-level-feature reverse-R² at still level, so
      the reader can see how much of the primary number is deflation.

  (a) top-K embedding dims most explained by the dials (+ how much of the
      total embedding variance those dims carry);
  (b) CONTROLS — the same reverse read from raw pixels (E12's 144-d grayscale
      still control) and from a luminance-only regressor (1 feature: per-still
      mean luminance).  Question: does the dial->embedding map exceed the
      trivial dial->pixel-statistics map?  Reported raw AND ceiling-normalized
      (R²/ceiling), since the two target spaces have different room-determined
      structure — that is what makes the comparison honest;
  (c) NULL — room-level shuffle of the dial triple -> 200 reverse reads.
  Plus a METRIC-SCALE CALIBRATION (no encoder): synthetic embeddings on the
  real bank's 27-room / 12-still geometry with KNOWN dial-aligned variance
  fractions (weak + strong positive, and a dial-free negative), so the reader
  can see how faithfully the metric recovers a planted fraction.

PRE-REGISTERED GATES (fixed before running; this file IS the registration)
  INVALID_HARNESS : (i) the E12 forward ridge does not replicate on this bank
                    (k=64 still-LORO within ANCHOR_TOL of the recorded
                    0.8106/0.9624/0.9478), OR (ii) the G0b luminance
                    sensitivity control is < 0.90, OR (iii) < 8 rooms.
                    A broken harness must never produce a KILL.
  KILL            : mean_reverse_r2 < 0.10  — the framing dies.
  LICENSE         : mean_reverse_r2 > 0.40  — the framing is licensed.
  INCONCLUSIVE    : 0.10 <= mean_reverse_r2 <= 0.40 (report the number).
  The gate is on the PRIMARY (still-level, dial-label features, mean per-dim
  R²).  The room-level and variance-weighted variants are echoed with the band
  each would imply and an agreement flag; disagreement is itself the finding
  (it localises the remaining variance as within-room still noise vs
  cross-room structure).

HONEST LIMITS (booked with the result, not discovered later)
  - The bank is a STAGED 3x3x3 grid: room identity IS the dial triple. Reverse
    R² here is therefore an UPPER bound over natural rooms — this bank is the
    friendliest possible case for the framing, so a KILL here is decisive and a
    LICENSE is not yet evidence about natural rooms.
  - 27 rooms is small; LORO keeps the estimate honest but it is noisy.
  - Linear reverse only (a ridge). A dial could be nonlinear in the embedding
    and invisible here; the 9-feature augmented variant (squares + pairwise
    products) is booked as a probe for exactly that, and the E13/E13b
    nonlinearity lessons are the reason it is booked rather than gated.
  - Embeddings are L2-normalized per still (E12's convention); mean per-dim R²
    is scale-invariant, the variance-weighted aggregate is not (noted).
  - One encoder (facebook/ijepa_vith16_1k), one seed, one staging family.

This module WRITES NOTHING (no results/, no QUEUE.md/EXP_MOD edits).
Deterministic (seed 2718). Progress on stderr; ONE JSON object on stdout.
Manual fire only:
    ~/venvs/elephant-gpu/bin/python experiments/x1_reverse_probe.py
    ~/venvs/elephant-gpu/bin/python experiments/x1_reverse_probe.py --cpu-only
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# BLAS thread cap before numpy loads (E12's lesson): the null runs hundreds of
# tiny ridge solves; with the default thread count each 3-feature solve spawns
# 24 threads and the sweep thrashes. Also keeps this a good neighbour on a box
# that may be running a sibling experiment.
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

import e12_room_dial_reader as e12  # noqa: E402  (bank, staging, ridge, null)
from e12_room_dial_reader import (  # noqa: E402
    DIAL_NAMES, K_PRIMARY, K_WIDE, LAM_GRID, PERMS, RATE, SECONDS,
    W, H, build_dial_grid, collect_arm_b, loro_predict, pca_basis,
    preflight_guard, r2_columns, read_room, room_from_script, room_means,
    stage_source, stage_transcript,
)
from e9_ijepa_stills import N_STILLS, embed, preprocess  # noqa: E402
from common import ppms_from_lavfi  # noqa: E402

# --------------------------------------------------------------------- #
# Pre-registered constants                                              #
# --------------------------------------------------------------------- #
KILL_BELOW = 0.10               # mean reverse-R² below this KILLs the framing
LICENSE_ABOVE = 0.40            # above this the framing is licensed
ANCHOR_TOL = 0.05               # E12 forward replication tolerance (abs)
SENSITIVITY_FLOOR = 0.90        # G0b, E12's floor verbatim
MIN_ROOMS = 8                   # below this grouped CV is meaningless (E12)
TOP_K = 20                      # how many dial-explained dims to name
AUG_DIAL_FEATS = ("m^2", "v^2", "p^2", "m*v", "m*p", "v*p")  # booked nonlinear
# E12's recorded k=64 still-LORO — the forward anchor. Read from the recorded
# run when the file is present; these literals are the fallback.
E12_ANCHOR_K64 = {"mood": 0.8106, "volume": 0.9624, "presence": 0.9478}
E12_ANCHOR_FILE = LAB / "results" / "e12_room_dial_reader.json"

SMOKE_ROOMS = 6                 # --cpu-only smoke subset of the 27-room bank
SMOKE_PERMS = 20
SMOKE_HIDDEN = 64               # tiny random-init trunk for the smoke path
SMOKE_BLOCKS = 4


def log(msg: str) -> None:
    """Progress to stderr; stdout is reserved for the ONE JSON verdict."""
    print(f"[x1] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------- #
# The reverse probe (the new logic — everything else is E12's)           #
# --------------------------------------------------------------------- #
def reverse_loro(Z, Y, groups, lam):
    """Leave-one-ROOM-out ridge predictions for a MULTI-COLUMN target, with a
    FIXED lambda (the null path).

    E12's `_ridge_path_pred` already supports a multi-column y (it centers per
    column and vectorises the SVD), so a whole 1280-d reverse read costs ONE
    SVD per fold instead of 1280 — that is what makes this experiment cheap.
    """
    pred = np.zeros_like(Y)
    for g in np.unique(groups):
        te = groups == g
        tr = ~te
        if tr.sum() < 3:
            pred[te] = Y[tr].mean(0) if tr.any() else 0.0
            continue
        pred[te] = e12._ridge_fit_predict(Z[tr], Y[tr], Z[te], lam)
    return pred


def inner_cv_stats(Z, Y, groups, grid=LAM_GRID):
    """Inner grouped CV inside each training fold (no leakage: every inner
    held-out room is excluded from its own inner fit).

    Returns (sse (nlam, D), sst_train (D), seen):
      sse[l, j]  = POOLED SSE on the inner held-out rooms for lambda l, dim j.
                   Minimising this per dim IS maximising that dim's pooled R²
                   (its denominator does not depend on lambda), so no baseline
                   convention can bias the choice.
      sst_train[j] = pooled SS of the same held-out rows against the INNER
                   TRAINING rooms' mean — a lambda-independent normaliser used
                   only by the booked one-shared-lambda variant, so low-variance
                   dims count as much as high-variance ones.
    """
    grid = np.asarray(grid, float)
    sse = np.zeros((len(grid), Y.shape[1]))
    sst = np.zeros(Y.shape[1])
    seen = False
    for g in np.unique(groups):
        tr = groups != g
        if tr.sum() < 3:
            continue
        for h in np.unique(groups[tr]):
            ite = groups == h
            itr = tr & ~ite
            if itr.sum() < 3 or ite.sum() == 0:
                continue
            seen = True
            preds = e12._ridge_path_pred(Z[itr], Y[itr], Z[ite], grid)
            for j, p in enumerate(preds):
                sse[j] += ((Y[ite] - p) ** 2).sum(0)
            sst += ((Y[ite] - Y[itr].mean(0)) ** 2).sum(0)
    return sse, sst, seen


def reverse_fit(Z, Y, groups, lams=LAM_GRID):
    """Two-pass leave-one-room-out reverse ridge with a PER-DIM lambda.

    PASS 1: per-dim lambda = argmin of that dim's pooled inner-CV SSE, which is
    exactly the lambda that maximises the dim's pooled inner R² — the same
    statistic the gate reports, so the selection cannot be biased by a baseline
    convention.

    BUILD LESSONS (both caught in the --cpu-only smoke path, both recorded here
    so a future reader does not re-introduce them):
      1. ONE lambda for all 1280 dims, chosen by TOTAL SSE, is dominated by the
         many dims with no dial signal and collapses to full shrinkage; a fully
         shrunk predictor echoes the training rooms' mean, and under
         leave-one-ROOM-out that is far from an unseen room's dims — a random
         trunk scored mean reverse-R² = -0.93, a pure artifact that would have
         faked the KILL.
      2. Choosing lambda on the inner test room's OWN mean as baseline flatters
         heavy shrinkage for the same reason; the pooled-SSE rule above has no
         such convention in it at all.

    Returns (pred, lambda_per_dim).
    """
    D = Y.shape[1]
    grid = np.asarray(lams, float)
    sse, _sst, seen = inner_cv_stats(Z, Y, groups, grid)
    lam_idx = np.argmin(sse, axis=0) if seen else np.zeros(D, int)
    lam_dim = grid[lam_idx]
    uniq = [float(v) for v in sorted(set(lam_dim.tolist()))]
    lut = {v: i for i, v in enumerate(uniq)}
    pick = np.array([lut[float(v)] for v in lam_dim])
    cols = np.arange(D)
    pred = np.zeros_like(Y)
    for g in np.unique(groups):
        te = groups == g
        tr = ~te
        if tr.sum() < 3:
            pred[te] = Y[tr].mean(0) if tr.any() else 0.0
            continue
        preds = e12._ridge_path_pred(Z[tr], Y[tr], Z[te], uniq)   # list of (n_te, D)
        P = np.stack(preds, axis=0)                              # (nlam, n_te, D)
        pred[te] = P[pick, :, cols].T   # per-dim: dim j uses its own lambda's preds
    return pred, lam_dim


def lam_counts(grid: np.ndarray) -> dict:
    """How many dims chose each lambda (a diagnostic on the reverse fit)."""
    vals, cnts = np.unique(np.asarray(grid, float), return_counts=True)
    return {str(float(v)): int(c) for v, c in zip(vals, cnts)}


def shared_lambda_read(Z, Y, groups, lams=LAM_GRID) -> dict:
    """BOOKED variant: ONE lambda for the whole reverse model — the "the dials'
    linear span, as a single model" reading. Chosen by minimising the MEAN
    RELATIVE inner SSE across dims (each dim in its own units), so it is not
    dominated by the high-variance dims the way a total-SSE rule would be.
    Reported next to the primary so the reader can see what the per-dim lambda
    buys; see reverse_fit's build lesson (2)."""
    grid = np.asarray(lams, float)
    sd = Y.std(0) + 1e-8
    sse, sst, seen = inner_cv_stats(Z, (Y - Y.mean(0)) / sd, groups, grid)
    score = (sse / np.maximum(sst, 1e-12)[None, :]).sum(1)
    lam = float(grid[int(np.argmin(score))]) if seen else float(grid[0])
    res = reverse_read(Z, Y, groups, lam=lam)
    res["shared_lambda"] = lam
    return res


def reverse_read(Z, Y, groups, lam=None) -> dict:
    """Predict every column of Y from Z, leave-one-room-out. The reverse probe.

    Targets are column-standardized before fitting (a label-free, purely
    numerical convenience: R² is affine-invariant, and r2_columns() measures
    against the target's own mean, so the per-dim R² is numerically identical
    to the R² in the original units).  Standardizing puts dims of wildly
    different scale on one footing for the lambda search.

    lam=None -> per-dim lambda (PRIMARY). lam=float -> one fixed lambda
    (the null path).
    """
    mu = Y.mean(0)
    sd = Y.std(0) + 1e-8
    Ys = (Y - mu) / sd
    if lam is None:
        pred_s, lam_dim = reverse_fit(Z, Ys, groups)
        lam_med = float(np.median(lam_dim))
    else:
        pred_s = reverse_loro(Z, Ys, groups, lam)
        lam_dim = np.full(Y.shape[1], float(lam))
        lam_med = float(lam)
    r2 = r2_columns(Ys, pred_s)                  # == R² in original units
    pred = pred_s * sd + mu
    sse = ((Y - pred) ** 2).sum(0)
    sst = ((Y - Y.mean(0)) ** 2).sum(0)
    weighted = 1.0 - float(sse.sum()) / max(float(sst.sum()), 1e-12)
    return {
        "r2": r2,
        "lambda_median": lam_med,
        "lambda_per_dim_counts": lam_counts(lam_dim),
        "mean_r2": float(r2.mean()),
        "median_r2": float(np.median(r2)),
        "variance_weighted_r2": float(weighted),
        "n_dims": int(Y.shape[1]),
        "n_dims_r2_ge_0.30": int((r2 >= 0.30).sum()),
        "n_dims_r2_ge_0.10": int((r2 >= 0.10).sum()),
        "n_dims_r2_gt_0": int((r2 > 0.0).sum()),
        "p90_r2": float(np.percentile(r2, 90)),
    }


def room_ceiling(Y, groups) -> dict:
    """ANOVA between-room ceiling: mean per-dim SS_between/SS_total.

    NO room-level feature can beat this at still level — the within-room still
    variance of a dim is invisible to any room-constant regressor. Reporting it
    separates "the dials explain little" from "the stills are noisy".
    """
    gm = Y.mean(0)
    ssb = np.zeros(Y.shape[1])
    sst = np.zeros(Y.shape[1])
    for g in np.unique(groups):
        m = groups == g
        ssb += int(m.sum()) * (Y[m].mean(0) - gm) ** 2
        sst += ((Y[m] - gm) ** 2).sum(0)
    ceil = ssb / np.maximum(sst, 1e-12)
    return {"mean_ceiling": float(ceil.mean()),
            "median_ceiling": float(np.median(ceil)), "per_dim": ceil}


def dial_map_null(Z, Y, groups, lam, perms, seed):
    """(c) NULL — the same reverse read with the room->dial map SHUFFLED.

    Z rows are room-constant (the labels are room-level), so shuffling rooms is
    the whole null: each room gets another room's dial triple.
    Returns (summary, draws_mean_r2, draws_weighted) so the caller can form
    exact p-values from the draws rather than from the summary.
    """
    rng = np.random.default_rng(seed)
    ids = np.unique(groups)
    pos = np.searchsorted(ids, groups)
    Zroom = np.stack([Z[groups == g].mean(0) for g in ids])
    mu = Y.mean(0)
    sd = Y.std(0) + 1e-8
    Ys = (Y - mu) / sd
    mean_r2 = np.zeros(perms)
    weighted = np.zeros(perms)
    for i in range(perms):
        perm = rng.permutation(len(ids))
        Zp = Zroom[perm][pos]
        pred = reverse_loro(Zp, Ys, groups, lam)
        r2 = r2_columns(Ys, pred)
        mean_r2[i] = r2.mean()
        sse = ((Ys - pred) ** 2).sum(0)
        sst = ((Ys - Ys.mean(0)) ** 2).sum(0)
        weighted[i] = 1.0 - float(sse.sum()) / max(float(sst.sum()), 1e-12)
    summary = {
        "perms": int(perms), "lambda_fixed": float(lam),
        "mean_r2_null_mean": float(mean_r2.mean()),
        "mean_r2_null95": float(np.percentile(mean_r2, 95)),
        "mean_r2_null_max": float(mean_r2.max()),
        "mean_r2_null_std": float(mean_r2.std()),
        "variance_weighted_null95": float(np.percentile(weighted, 95)),
        "note": ("room-level shuffle of the dial TRIPLE; because the bank is a "
                 "3x3x3 grid, a shuffled triple is a legal but wrong room's "
                 "dials — the honest 'the dials carry no room information' null"),
    }
    return summary, mean_r2, weighted


def perm_p(obs: float, draws: np.ndarray) -> float:
    """Fraction of null draws >= the observed statistic (E12's convention)."""
    return float((np.asarray(draws) >= obs).mean()) if len(draws) else float("nan")


def synthetic_calibration(dims: int = 64) -> dict:
    """METRIC-SCALE CALIBRATION (no encoder involved).

    Builds a synthetic embedding on the SAME geometry as the real bank (the 27
    staged dial triples, 12 stills per room) with a KNOWN dial-aligned variance
    fraction, and checks that the X1 harness recovers it. Two cases:
      - "dial_aligned": room means are a linear image of the dials plus a room
        residual, plus still noise — the ideal predictor's pooled R² is
        computed exactly and the harness should land near it;
      - "dial_free": the same construction with NO dial term — the harness
        should land at or below the LORO train-mean floor.
    This is what makes the gate number readable: it is a self-test of the
    METRIC, not of the encoder.
    """
    grid = build_dial_grid()
    Zroom = np.array([r["target"] for r in grid], float)
    n = len(grid)
    out: dict = {}
    for tag, w_scale, noise_scale, seed_off in (("dial_aligned", 1.0, 0.75, 7),
                                                ("dial_aligned_strong", 1.0, 0.35, 11),
                                                ("dial_free", 0.0, 0.75, 9)):
        rng = np.random.default_rng(SEED + seed_off)
        W = rng.normal(size=(3, dims)) * w_scale
        resid = rng.normal(size=(n, dims)) * noise_scale
        noise = rng.normal(size=(n, N_STILLS, dims)) * noise_scale
        Yr = Zroom @ W + resid                      # (n, dims) room targets
        Ys = Yr[:, None, :] + noise                 # (n, N_STILLS, dims)
        Yflat = Ys.reshape(-1, dims)
        groups = np.repeat(np.arange(n), N_STILLS)
        Zstill = np.repeat(Zroom, N_STILLS, axis=0)
        P = np.repeat(Zroom @ W, N_STILLS, axis=0)  # ideal (population) predictor
        ideal = r2_columns(Yflat, P)
        sst = ((Yflat - Yflat.mean(0)) ** 2).sum()
        rec = reverse_read(Zstill, Yflat, groups)
        rec_room = reverse_read(Zroom, Yr, np.arange(n))
        out[tag] = {
            "ideal_mean_r2": round(float(ideal.mean()), 4),
            "ideal_variance_weighted_r2": round(
                float(1.0 - ((Yflat - P) ** 2).sum() / max(sst, 1e-12)), 4),
            "recovered_mean_r2": round(float(rec["mean_r2"]), 4),
            "recovered_variance_weighted_r2": round(
                float(rec["variance_weighted_r2"]), 4),
            "recovered_room_level_mean_r2": round(float(rec_room["mean_r2"]), 4),
            "recovery_gap_mean_r2": round(
                float(rec["mean_r2"] - ideal.mean()), 4),
        }
    return {
        "dims": int(dims), "rooms": n, "stills_per_room": N_STILLS,
        "cases": out,
        "note": ("positive + negative controls for the GATE METRIC itself, on "
                 "the real bank's geometry; a large recovery gap would mean "
                 "the metric, not the encoder, is the story"),
    }


def top_k_dims(r2: np.ndarray, Y: np.ndarray) -> dict:
    """(a) the embedding dims the dials explain best, and the share of total
    embedding variance those dims carry."""
    order = np.argsort(-np.asarray(r2))
    sst = ((Y - Y.mean(0)) ** 2).sum(0)
    share = sst / max(float(sst.sum()), 1e-12)
    k = min(TOP_K, len(order))
    dims = [{"dim": int(i), "r2": round(float(r2[i]), 4),
             "var_share": round(float(share[i]), 5)} for i in order[:k]]
    return {"k": int(k), "dims": dims,
            "var_share_top_k": round(float(share[order[:k]].sum()), 4),
            "var_share_top_3": round(float(share[order[:3]].sum()), 4),
            "dims_sorted_by_dial_explainability": True}


def band(v: float) -> str:
    """Which band does a number fall in? (the pre-registered cut points)."""
    if v < KILL_BELOW:
        return "KILL"
    if v > LICENSE_ABOVE:
        return "LICENSE"
    return "INCONCLUSIVE"


def augment_dials(Z: np.ndarray) -> np.ndarray:
    """Booked nonlinear variant: the 3 dials + squares + pairwise products."""
    m, v, p = Z[:, 0], Z[:, 1], Z[:, 2]
    return np.column_stack([Z, m * m, v * v, p * p, m * v, m * p, v * p])


def anchor_reference() -> tuple[dict, str]:
    """E12's recorded forward R², from the recorded run when present."""
    try:
        d = json.loads(E12_ANCHOR_FILE.read_text())
        rec = d.get("r2_still_loro", {}).get("64")
        if rec:
            return ({k: float(rec[k]) for k in DIAL_NAMES},
                    str(E12_ANCHOR_FILE.relative_to(LAB)))
    except Exception:  # noqa: BLE001 — missing/corrupt file: fall back to literals
        pass
    return dict(E12_ANCHOR_K64), "literals in x1_reverse_probe.py"


def forward_replication(X, Ylab, lum, groups) -> dict:
    """INVALID_HARNESS check (i): does E12's forward ridge replicate here?

    E12's own read, verbatim: PCA-64 basis fit unsupervised on ALL embeddings,
    LORO ridge with per-fold inner-CV lambda, still-level R².  Plus G0b (the
    pool of luminance sensitivity) at E12's 0.90 floor.  If this does not
    reproduce the recorded numbers, the bank/harness differs from E12's and no
    reverse number may be reported as evidence.
    """
    basis, _evr = pca_basis(X, K_WIDE)   # (D, k) basis, label-free (E12's)
    zc = X @ basis[:, :K_PRIMARY]
    pred, lam_med = loro_predict(zc, Ylab, groups)
    r2 = r2_columns(Ylab, pred)
    measured = {d: round(float(r2[i]), 4) for i, d in enumerate(DIAL_NAMES)}
    anchors, src = anchor_reference()
    dev = {d: round(abs(measured[d] - anchors[d]), 4) for d in DIAL_NAMES}
    max_dev = max(dev.values())
    lum_target = lum.reshape(-1, 1).astype(np.float64)
    pred_lum, _ = loro_predict(zc, lum_target, groups)
    r2_lum = float(r2_columns(lum_target, pred_lum)[0])
    return {
        "measured_forward_r2_k64": measured,
        "anchors_forward_r2_k64": {d: round(float(anchors[d]), 4) for d in DIAL_NAMES},
        "anchor_source": src, "abs_dev_per_dial": dev,
        "max_abs_dev": round(float(max_dev), 4), "tol": ANCHOR_TOL,
        "forward_replicated": bool(max_dev <= ANCHOR_TOL),
        "lambda_median_k64": lam_med,
        "g0b_sensitivity_r2_luminance_k64": round(r2_lum, 4),
        "g0b_sensitivity_floor": SENSITIVITY_FLOOR,
        "g0b_sensitivity_pass": bool(r2_lum >= SENSITIVITY_FLOOR),
        "forward_note": ("E12's own read, re-run on this bank: anchors "
                         "0.8106/0.9624/0.9478 (mean 0.9069) from the recorded "
                         "run; forward != reverse — a label-told reader can "
                         "recover a thin dial direction with R²~0.95 while the "
                         "dials explain almost none of the embedding's total "
                         "variance. Both numbers are true at once."),
    }


# --------------------------------------------------------------------- #
# The full analysis (given a collected bank)                            #
# --------------------------------------------------------------------- #
def analyse(X, Ylab, Ytgt, groups, lum, pix, names, perms, model_used,
            load_notes, guard_info, device, mode, t0) -> dict:
    """Everything after the bank exists: reverse reads, controls, null, gates."""
    n_rooms = int(len(np.unique(groups)))
    fwd = forward_replication(X, Ylab, lum, groups)

    # ---- PRIMARY: still-level reverse read from the 3 elephant dial labels
    rev_lab = reverse_read(Ylab, X, groups)
    log(f"reverse (label dials, still-level): mean R2={rev_lab['mean_r2']:.4f} "
        f"median={rev_lab['median_r2']:.4f} "
        f"var-weighted={rev_lab['variance_weighted_r2']:.4f} "
        f"lam={rev_lab['lambda_median']}")
    ceil_emb = room_ceiling(X, groups)
    log(f"embedding between-room ceiling: mean={ceil_emb['mean_ceiling']:.4f}")

    # ---- (booked) room-level reverse read: no within-room still noise
    Xr, Yr, ids = room_means(X, Ylab, groups)
    rev_room = reverse_read(Yr, Xr, np.arange(len(ids)))
    log(f"reverse (room-level): mean R2={rev_room['mean_r2']:.4f} "
        f"var-weighted={rev_room['variance_weighted_r2']:.4f}")

    # ---- (booked) one SHARED lambda for the whole reverse model
    rev_shared = shared_lambda_read(Ylab, X, groups)
    log(f"reverse (shared lambda {rev_shared['shared_lambda']}): "
        f"mean R2={rev_shared['mean_r2']:.4f}")

    # ---- (booked) reverse from the staging TARGET triple (not the bank label)
    rev_tgt = reverse_read(Ytgt, X, groups)

    # ---- (booked) nonlinear dial features (squares + products)
    rev_aug = reverse_read(augment_dials(Ylab), X, groups)

    # ---- (b) CONTROLS -----------------------------------------------------
    # raw pixels: E12's 144-d grayscale still control as the TARGET space
    rev_pix = reverse_read(Ylab, pix, groups)
    ceil_pix = room_ceiling(pix, groups)
    # luminance-only regressor: 1 feature -> the whole embedding / the pixels
    lumz = lum.reshape(-1, 1).astype(np.float64)
    rev_lum_emb = reverse_read(lumz, X, groups)
    rev_lum_pix = reverse_read(lumz, pix, groups)
    log(f"controls: pixel mean R2={rev_pix['mean_r2']:.4f} "
        f"(ceiling {ceil_pix['mean_ceiling']:.4f}), "
        f"luminance->emb mean R2={rev_lum_emb['mean_r2']:.4f}")
    controls = {
        "raw_pixel_reverse": {
            "mean_r2": round(rev_pix["mean_r2"], 4),
            "variance_weighted_r2": round(rev_pix["variance_weighted_r2"], 4),
            "mean_ceiling": round(ceil_pix["mean_ceiling"], 4),
            "ceiling_normalized_r2": round(
                rev_pix["mean_r2"] / max(ceil_pix["mean_ceiling"], 1e-9), 4),
            "n_dims": rev_pix["n_dims"]},
        "embedding_ceiling_normalized_r2": round(
            rev_lab["mean_r2"] / max(ceil_emb["mean_ceiling"], 1e-9), 4),
        "embedding_mean_ceiling": round(ceil_emb["mean_ceiling"], 4),
        "luminance_only_to_embedding": {
            "mean_r2": round(rev_lum_emb["mean_r2"], 4),
            "variance_weighted_r2": round(rev_lum_emb["variance_weighted_r2"], 4),
            "ceiling_normalized_r2": round(
                rev_lum_emb["mean_r2"] / max(ceil_emb["mean_ceiling"], 1e-9), 4)},
        "luminance_only_to_pixels": {
            "mean_r2": round(rev_lum_pix["mean_r2"], 4),
            "variance_weighted_r2": round(rev_lum_pix["variance_weighted_r2"], 4),
            "ceiling_normalized_r2": round(
                rev_lum_pix["mean_r2"] / max(ceil_pix["mean_ceiling"], 1e-9), 4)},
        "dial_to_embedding_vs_dial_to_pixels": {
            "mean_r2_ratio_emb_over_pix": round(
                rev_lab["mean_r2"] / max(rev_pix["mean_r2"], 1e-9), 4),
            "ceiling_normalized_ratio": round(
                (rev_lab["mean_r2"] / max(ceil_emb["mean_ceiling"], 1e-9))
                / max(rev_pix["mean_r2"] / max(ceil_pix["mean_ceiling"], 1e-9),
                      1e-9), 4),
            "verdict": ("the dials explain MORE of the embedding than of the "
                        "trivial pixel statistics" if rev_lab["mean_r2"] >
                        rev_pix["mean_r2"] else
                        "the dials explain NO MORE of the embedding than of "
                        "the trivial pixel statistics — the reverse residual "
                        "is not JEPA-specific"),
            "note": ("the two target spaces have different intrinsic room "
                     "structure; the ceiling-normalized ratio is the fairer "
                     "comparison, the raw ratio is scale-dependent")},
    }

    # ---- (c) NULL ---------------------------------------------------------
    null, null_draws_mean, null_draws_w = dial_map_null(
        Ylab, X, groups, rev_lab["lambda_median"], perms, SEED + 13)
    null["p_mean_r2"] = round(perm_p(rev_lab["mean_r2"], null_draws_mean), 4)
    null["p_variance_weighted_r2"] = round(
        perm_p(rev_lab["variance_weighted_r2"], null_draws_w), 4)
    null["primary_beats_null95"] = bool(
        rev_lab["mean_r2"] > null["mean_r2_null95"])
    log(f"null (shuffled dials): mean R2 {null['mean_r2_null_mean']:.4f} "
        f"null95 {null['mean_r2_null95']:.4f} -> p={null['p_mean_r2']}")

    # ---- metric-scale calibration (positive + negative control, no encoder)
    calib = synthetic_calibration()
    log(f"metric calibration: dial-aligned ideal "
        f"{calib['cases']['dial_aligned']['ideal_mean_r2']} -> recovered "
        f"{calib['cases']['dial_aligned']['recovered_mean_r2']}; "
        f"dial-free recovered "
        f"{calib['cases']['dial_free']['recovered_mean_r2']}")

    # ---- gates + verdict --------------------------------------------------
    primary = float(rev_lab["mean_r2"])
    harness_reasons = []
    if n_rooms < MIN_ROOMS:
        harness_reasons.append(f"only {n_rooms} rooms (< {MIN_ROOMS}) — "
                               "grouped CV is meaningless")
    if not fwd["forward_replicated"]:
        harness_reasons.append(
            f"forward ridge does not replicate E12 (max |dev| "
            f"{fwd['max_abs_dev']} > tol {ANCHOR_TOL})")
    if not fwd["g0b_sensitivity_pass"]:
        harness_reasons.append(
            f"G0b luminance sensitivity "
            f"{fwd['g0b_sensitivity_r2_luminance_k64']} < {SENSITIVITY_FLOOR}")

    if harness_reasons:
        verdict = "INVALID_HARNESS"
    else:
        verdict = band(primary)

    echoes = {
        "room_level_mean_r2": {"value": round(float(rev_room["mean_r2"]), 4),
                               "band": band(float(rev_room["mean_r2"]))},
        "variance_weighted_r2": {
            "value": round(float(rev_lab["variance_weighted_r2"]), 4),
            "band": band(float(rev_lab["variance_weighted_r2"]))},
        "target_triple_features_mean_r2": {
            "value": round(float(rev_tgt["mean_r2"]), 4),
            "band": band(float(rev_tgt["mean_r2"]))},
        "shared_lambda_mean_r2": {
            "value": round(float(rev_shared["mean_r2"]), 4),
            "band": band(float(rev_shared["mean_r2"]))},
        "augmented_dial_features_mean_r2": {
            "value": round(float(rev_aug["mean_r2"]), 4),
            "band": band(float(rev_aug["mean_r2"]))},
        "raw_pixel_mean_r2": {"value": round(float(rev_pix["mean_r2"]), 4),
                              "band": band(float(rev_pix["mean_r2"]))},
    }
    bands = {echoes[k]["band"] for k in
             ("room_level_mean_r2", "variance_weighted_r2",
              "target_triple_features_mean_r2", "augmented_dial_features_mean_r2",
              "shared_lambda_mean_r2")}
    agreement = (len(bands) == 1 and bands.pop() == verdict) \
        if verdict in ("KILL", "LICENSE", "INCONCLUSIVE") else None

    out = {
        "experiment": "X1 reverse probe (dial-explained embedding variance)",
        "mode": mode, "device": device, "seed": SEED, "model": model_used,
        "load_notes": load_notes, "guard_preflight": guard_info,
        "dial_names": DIAL_NAMES, "dial_source": (
            "elephant DialBank reading of the room's staged script (E12's "
            "label source — never hand-typed)"),
        "rooms": len(names), "stills_per_room": N_STILLS,
        "cells": int(X.shape[0]), "emb_dim": int(X.shape[1]),
        "lambda_grid": list(LAM_GRID),
        "forward_replication": fwd,
        "reverse_primary_still_level_from_dial_labels": {
            k: round(v, 5) if isinstance(v, float) else v
            for k, v in rev_lab.items() if k != "r2"},
        "reverse_room_level": {
            k: round(v, 5) if isinstance(v, float) else v
            for k, v in rev_room.items() if k != "r2"},
        "reverse_shared_lambda_booked": {
            k: round(v, 5) if isinstance(v, float) else v
            for k, v in rev_shared.items() if k != "r2"},
        "reverse_staging_target_features": {
            k: round(v, 5) if isinstance(v, float) else v
            for k, v in rev_tgt.items() if k != "r2"},
        "reverse_augmented_dial_features": {
            "features": ["m", "v", "p", *AUG_DIAL_FEATS],
            **{k: round(v, 5) if isinstance(v, float) else v
               for k, v in rev_aug.items() if k != "r2"}},
        "embedding_variance_ceiling": {
            "mean_between_room_ceiling": round(ceil_emb["mean_ceiling"], 4),
            "median_between_room_ceiling": round(ceil_emb["median_ceiling"], 4),
            "loro_trainmean_floor_room_constant": round(
                1.0 - (n_rooms / max(n_rooms - 1, 1)) ** 2, 4),
            "note": ("mean per-dim SS_between/SS_total over rooms — the hard "
                     "upper bound on ANY room-constant-feature reverse-R² at "
                     "still level. primary/ceiling isolates 'the dials explain "
                     "little' from 'the stills are noisy'. Calibration: a "
                     "dim that is room-constant but DIAL-UNPREDICTABLE scores "
                     "the LORO train-mean floor 1-(n/(n-1))² (negative at 27 "
                     "rooms, shown above), and a pure within-room noise dim "
                     "scores ~0 — so a dial-free embedding lands near or below "
                     "0 and the 0.10 KILL cut is comfortably above the floor.")},
        "top_dial_explained_dims": top_k_dims(rev_lab["r2"], X),
        "controls": controls,
        "null_shuffled_dials": null,
        "metric_scale_calibration": calib,
        "verdict_echoes": echoes,
        "verdict_echo_agreement": agreement,
        "gates": {
            "metric": ("mean per-dim still-level LORO reverse-R² (dial labels, "
                   "per-dim lambda chosen by inner grouped CV on the same "
                   "pooled-SSE statistic the gate reports)"),
            "kill_below": KILL_BELOW, "license_above": LICENSE_ABOVE,
            "measured_primary_mean_reverse_r2": round(primary, 4),
            "forward_replicated": fwd["forward_replicated"],
            "g0b_sensitivity_pass": fwd["g0b_sensitivity_pass"],
            "n_rooms": n_rooms, "min_rooms": MIN_ROOMS,
            "harness_invalid_reasons": harness_reasons,
        },
        "seconds_total": round(time.time() - t0, 1),
        "verdict": verdict,
        "note": (
            "REVERSE probe: predict each of the 1280 embedding dims from the 3 "
            "elephant dial labels, leave-one-room-out (per-dim ridge lambda "
            "chosen by inner grouped CV on the same pooled-SSE statistic the "
            "gate reports; targets column-standardized). Forward R² asks 'can a "
            "reader HANDED the labels recover the dials?'; reverse R² asks 'is "
            "the dial direction a meaningful share of the embedding's "
            "variance?' — "
            "the question that decides whether a label-free elephant could ever "
            "find it. KILL (<0.10) = the dials are a tiny corner of the "
            "embedding and the room-temperature framing is dead regardless of "
            "forward R². LICENSE (>0.40) = the framing survives. Between = "
            "INCONCLUSIVE, reported as-is. INVALID_HARNESS (E12's forward read "
            "must reproduce, luminance sensitivity must hold, >=8 rooms) "
            "pre-empts any KILL from a broken harness. The bank is a staged "
            "3x3x3 grid "
            "where room identity IS the dial triple, so this is the FRIENDLIEST "
            "possible case: a KILL is decisive, a LICENSE is not yet evidence "
            "about natural rooms. No results/ writes; one JSON on stdout."),
    }
    return out


# --------------------------------------------------------------------- #
# CPU-only smoke path (bank + reverse plumbing, no GPU, no verdict)      #
# --------------------------------------------------------------------- #
def smoke_rooms(n_rooms: int) -> list[dict]:
    """A spread of E12's bank spanning all three dial levels (smoke only)."""
    grid = build_dial_grid()
    if n_rooms >= len(grid):
        return grid
    idx = np.linspace(0, len(grid) - 1, max(2, n_rooms)).round().astype(int)
    return [grid[i] for i in dict.fromkeys(idx.tolist())]


def collect_bank_subset(model, processor, dev, torch, rooms, dtype,
                        max_batch: int = 6) -> dict:
    """E12's Arm-B loop over an ARBITRARY room list, for the CPU smoke path.

    The primary (full) path calls `e12.collect_arm_b` verbatim — this helper
    exists only so `--cpu-only` can exercise the identical staged-bank +
    elephant-label + I-JEPA-embed pipeline on a tiny random trunk without a hub
    download, and so the encoder input dtype can be matched to the smoke model.
    """
    X, Y, Yt, groups, lum, pix, names = [], [], [], [], [], [], []
    for gi, r in enumerate(rooms):
        m, v, p = r["target"]
        script = stage_transcript(m, v, p, r["seed"])
        readings = read_room(room_from_script(r["name"], script))
        label = np.array([readings.get(d, 0.0) for d in DIAL_NAMES], float)
        frames = ppms_from_lavfi(stage_source(m, v, p, r["seed"]),
                                 SECONDS, RATE, (W, H))
        if not frames:
            raise RuntimeError(f"no frames from staged source {r['name']!r}")
        idx = np.linspace(0, len(frames) - 1, N_STILLS).round().astype(int)
        stills = [frames[i] for i in idx]
        chunks = []
        for j0 in range(0, len(stills), max_batch):
            pixel = preprocess(stills[j0:j0 + max_batch], processor, dev).to(dtype)
            chunks.append(embed(model, pixel))
        vecs = np.concatenate(chunks, axis=0).astype(np.float64)
        vecs = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9)
        l = np.array([float(f.astype(np.float32).mean()) for f in stills])
        px = np.stack([f[::10, ::10].astype(np.float32).mean(axis=2).reshape(-1)
                       for f in stills])
        groups.append(np.full(len(vecs), gi))
        X.append(vecs)
        Y.append(np.repeat(label[None, :], len(vecs), axis=0))
        Yt.append(np.repeat(np.array([m, v, p], float)[None, :], len(vecs), axis=0))
        lum.append(l)
        pix.append(px)
        names.append(r["name"])
        log(f"smoke room {r['name']}: {len(vecs)} stills, label "
            f"mood={label[0]:+.3f} volume={label[1]:.3f} presence={label[2]:.3f}")
    return {"X": np.concatenate(X), "Y": np.concatenate(Y),
            "Yt": np.concatenate(Yt), "groups": np.concatenate(groups),
            "lum": np.concatenate(lum), "pix": np.concatenate(pix),
            "names": names}


def cpu_only(perms: int, n_rooms: int) -> dict:
    """Plumbing proof (no GPU, no claim): tiny random-init I-JEPA trunk + a
    smoke subset of E12's bank, then the WHOLE X1 path — reverse read, room
    level, target/augmented variants, pixel + luminance controls, shuffled-dial
    null, top dims, gate logic. verdict = SMOKE (the derived band is recorded
    but no claim is made about facebook/ijepa_vith16_1k)."""
    import torch
    from transformers.models.ijepa.modeling_ijepa import IJepaConfig, IJepaModel

    t0 = time.time()
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    cfg = IJepaConfig(hidden_size=SMOKE_HIDDEN, num_hidden_layers=SMOKE_BLOCKS,
                      num_attention_heads=4, intermediate_size=2 * SMOKE_HIDDEN,
                      image_size=224, patch_size=16, num_channels=3)
    model = IJepaModel(cfg).eval().float()
    rooms = smoke_rooms(n_rooms)
    log(f"cpu-only smoke: {len(rooms)} staged rooms, tiny trunk "
        f"({SMOKE_BLOCKS} blocks, hidden {SMOKE_HIDDEN}), perms={perms}")

    bank = collect_bank_subset(model, None, "cpu", torch, rooms,
                               dtype=next(model.parameters()).dtype)
    out = analyse(bank["X"], bank["Y"], bank["Yt"], bank["groups"], bank["lum"],
                  bank["pix"], bank["names"], perms,
                  model_used="random-init tiny IJepaConfig trunk (no hub download)",
                  load_notes={"smoke": "random weights — no claim"},
                  guard_info={"skipped": "cpu-only path never touches the GPU"},
                  device="cpu", mode="cpu-only smoke (no claim)", t0=t0)
    out["smoke_derived_verdict"] = out["verdict"]
    out["verdict"] = "SMOKE"
    out["smoke_note"] = (
        "SMOKE proves the plumbing only: E12's staged 27-room bank subset + "
        "elephant DialBank labels + an I-JEPA forward + the reverse ridge / "
        "controls / shuffled-dial null / gate logic. A random trunk is EXPECTED "
        "to fail the forward-replication gate (INVALID_HARNESS above), which is "
        "itself the harness check working: no reverse number is admissible "
        "unless E12's forward read reproduces.")
    print(json.dumps(out, indent=2))
    return out


# --------------------------------------------------------------------- #
# Main                                                                  #
# --------------------------------------------------------------------- #
def main() -> dict:
    argv = sys.argv[1:]

    def opt(flag: str, default):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 < len(argv):
                return type(default)(argv[i + 1])
        return default

    perms = int(opt("--perms", PERMS))
    n_rooms = int(opt("--rooms", 27))
    if "--cpu-only" in argv:
        return cpu_only(perms=min(perms, SMOKE_PERMS),
                        n_rooms=min(n_rooms, SMOKE_ROOMS))

    t0 = time.time()
    ok, reason, guard_info = preflight_guard()
    if not ok:
        out = {"experiment": "X1 reverse probe", "verdict": "ABORTED",
               "reason": reason, "guard_preflight": guard_info, "device": "cuda"}
        print(json.dumps(out, indent=2))
        return out
    log(f"guard preflight ok: {guard_info}")

    import torch
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"loading I-JEPA ({dev})...")
    try:
        model_used, model, processor, load_notes = load_encoder_guarded(dev)
    except Exception as e:  # noqa: BLE001
        out = {"experiment": "X1 reverse probe", "verdict": "ABORTED",
               "reason": f"model load failed: {e}", "guard_preflight": guard_info,
               "device": dev}
        print(json.dumps(out, indent=2))
        return out
    log(f"using {model_used}")

    # THE bank: E12's collector VERBATIM (27 staged rooms x 12 stills).
    try:
        X, Y, Yt, groups, lum, pix, names = collect_arm_b(
            model, processor, dev, torch)
    except Exception as e:  # noqa: BLE001
        out = {"experiment": "X1 reverse probe", "verdict": "ABORTED",
               "reason": f"bank/embed failed: {e}", "guard_preflight": guard_info,
               "device": dev, "model": model_used}
        print(json.dumps(out, indent=2))
        return out
    log(f"bank: {len(names)} rooms, {X.shape[0]} stills, dim {X.shape[1]}")

    out = analyse(X, Y, Yt, groups, lum, pix, names, perms, model_used,
                  load_notes, guard_info, dev,
                  mode="full 27-room staged dial bank", t0=t0)
    print(json.dumps(out, indent=2))
    return out


def load_encoder_guarded(dev: str):
    """E9's loader, imported lazily so the CPU smoke path never needs a hub."""
    from e9_ijepa_stills import load_encoder
    return load_encoder(dev)


if __name__ == "__main__":
    main()
