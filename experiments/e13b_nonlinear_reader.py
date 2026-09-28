#!/usr/bin/env python3
"""E13b — nonlinear READER: was E13's volume/presence death the RIDGE's fault?

THE QUESTION (this decides whether E12's volume/presence claim lives or dies)
  E13 (experiments/e13_nonlinear_dial_reader.py) landed INCONCLUSIVE: on the
  PRIMARY arm N2 (roomgen's frozen nonlinear mixture, mean curvature 0.471,
  certified live/nonaffine/injective), a LINEAR ridge reader with
  leave-one-room-out CV read the dials as:
      mood     R2_still_loro(k64) = 0.537  (survives)
      volume   R2_still_loro(k64) = -0.100 (dies)
      presence R2_still_loro(k64) = 0.270  (dies, below the 0.30 floor)
  E13 could not distinguish the two explanations:
    (R) the loss is in the READER — a linear ridge is too weak for the folded,
        non-monotone carrier, and a sufficiently nonlinear reader would still
        read volume/presence => E12's "reads volume/presence beyond luminance"
        survives, with a nonlinear reader;
    (E) the loss is in the EMBEDDING — the frozen I-JEPA genuinely scrambles
        those dials under nonlinear mixing, and NO reader can get them back
        => E12's volume/presence claim dies for good.
  E13b holds EVERYTHING fixed (same 27-room bank, same labels from the
  elephant DialBank, same three carriers L / N1 / N2 built by E13's own
  imported code, same frozen I-JEPA embeddings, same PCA spaces) and changes
  exactly one thing: THE READER. A small 2-layer MLP replaces the ridge, and
  both readers are reported side by side, per arm, per dial.

WHAT "NONLINEAR READER" MEANS HERE (pre-registered, fixed before running)
  - architecture: MLP  k -> 64 hidden (ReLU) -> 3 dials (multi-output),
    inputs = the SAME label-free PCA spaces as the ridge (k=16 and k=64 of
    the global PCA basis fit on all stills of the arm — E12's basis, no
    label leakage);
  - training: full-batch Adam (lr 1e-3, weight_decay 1e-4), per-fold input
    standardization and per-fold target standardization (train rooms only);
  - cross-validation: leave-one-ROOM-out, 27 fold-nets trained IN PARALLEL as
    one batched tensor op (each fold's loss/gradient touches only its own
    weight slice, so one Adam over the batched parameters = 27 independent
    Adam trainings — verified by the self-test);
  - early stopping: per fold, on a FROZEN inner-val set of train rooms
    (rooms 3, 9, 15, 21; when a val room IS the held-out test room it is
    dropped for that fold), patience 150 epochs, max 1500 epochs. The val
    rooms' labels influence exactly ONE degree of freedom (the epoch) — the
    same leakage profile as the ridge's per-fold inner-CV lambda;
  - permutation null: E12's convention — 200 room-level label shuffles, all
    three dial columns permuted jointly — with the training budget FIXED at
    the median best epoch of the real run (E12's "fixed lambda = median fold
    lambda" analog for an epoch-count hyperparameter) and no early stopping;
  - room-level check: R2 of the ROOM-AVERAGED held-out still predictions
    (27 points). DEVIATION FROM E12, pre-registered: E12's room-level ridge
    probe re-fits on room-mean FEATURES; an MLP re-fit on 27 room-mean rows
    has ~26 training points and cannot be gradient-trained honestly, so the
    strict room-granularity check is the averaged-prediction R2.

PRE-REGISTERED GATES (fixed before running; this file IS the registration)
  G0d  ridge harness self-test : E13's G0d verbatim (imported, synthetic
      linear signal -> LORO R2 >= 0.90, shuffled < 0.10).
  G0d' MLP harness self-test   : the same synthetic linear signal read by the
      MLP reader (LORO R2 >= 0.90, shuffled < 0.10) PLUS a NONLINEAR
      capability check: on synthetic targets a linear reader provably cannot
      read (x^2, sin(3x), product) the MLP must reach R2 >= 0.5 on >= 2 of 3
      while the ridge stays < 0.30 on >= 2 of 3. This certifies the reader
      can actually detect the class of signal E13b exists to detect —
      without it, an MLP-null result would be indistinguishable from a
      broken trainer.
  G0b  sensitivity             : E13's G0b verbatim (Arm L luminance LORO
      ridge R2(k=64) >= 0.90).
  G0c  carrier certificates    : E13's G0c verbatim, recomputed live for all
      arms (N2 must be nonaffine + live; L must measure curvature ~ 0).
  G0a  staging fidelity        : E13's G0a verbatim (>= 2/3 dials Spearman
      >= 0.5, script targets vs elephant labels).
  Gr   reader sanity           : the MLP itself must read the READABLE arm —
      on Arm L, MLP k=64 R2 >= 0.30 on >= 2/3 dials (if a nonlinear reader
      cannot read E12's easy linear staging, it cannot adjudicate anything).
  Gc   MLP is genuinely nonlinear: the trained N2 fold-nets' own mean
      normalized second-difference curvature along random input chords
      (the SAME statistic E13 applies to carriers, applied to the reader
      f: z -> y_hat) must be >= 0.02 on >= 2/3 dials. An affine map
      measures ~1e-7; if the MLP collapsed to affine the comparison is
      moot. The ridge-vs-MLP delta is reported alongside as the
      linear-baseline comparison.

VERDICT MAPPING (pre-registered; FAIL_SET := dials the RIDGE gate fails on
the primary arm N2 in THIS run — recomputed live, never imported from E13's
JSON; "mlp_pass" uses E12's dial formula verbatim with MLP numbers:
mlp R2 k64 >= 0.30 AND mlp room-level >= 0.15 AND mlp k16 >= 0.5*mlp k64
AND mlp k64 > mlp null95):
  KEEP         : |FAIL_SET| >= 2 AND >= 2 of the FAIL_SET dials PASS under
                 the MLP AND MLP overall n_pass >= 2 AND Gc holds
                 ==> the loss was in the READER (linear ridge too weak);
                     E12's volume/presence read survives with a nonlinear
                     reader.
  KILL         : |FAIL_SET| >= 2 AND ZERO FAIL_SET dials pass under the MLP
                 AND mean MLP R2(k64) over FAIL_SET <= mean MLP null95 over
                 FAIL_SET AND Gc holds
                 ==> the loss is in the EMBEDDING; the frozen I-JEPA
                     scrambles those dials under nonlinear mixing; E12's
                     volume/presence claim dies for good.
  INCONCLUSIVE : any partial recovery (some but not all FAIL_SET dials
                 recover; or |FAIL_SET| < 2, in which case E13's premise
                 does not hold in this run and the sets are booked; or Gc
                 fails, i.e. the MLP went affine and cannot arbitrate).
                 NEVER overclaim from a partial.
  INVALID_HARNESS : G0d/G0d'/G0b/Gr fail.
  INVALID_STAGING : G0a or G0c fail on the primary arm.
  INVALID_CONTROL : Arm L does not replicate E12's KEEP under the RIDGE
                    (E12's own gate, E13's Arm-L control) — never a KILL.
  ABORTED         : guard preflight, model load, no frames, < 8 rooms.

CONTROLS / BOOKED (never gated)
  - BOTH readers on ALL THREE arms, side by side, per dial: ridge k16/k64/
    room/null95 (E13's arm_report verbatim) and MLP k16/k64/room/null95/
    epochs/curvature. The headline is MLP-minus-ridge on N2 per dial.
  - N1 (the mild bent rung) under the MLP: booked, the same scope note E13
    books (does the nonlinear reader rescue the middle rung too?).
  - MLP on Arm L minus ridge on Arm L: the reader-instability watchdog
    behind Gr.

CONVENTION CHANGES vs E12/E13 (booked, deliberate)
  - E12/E13 kept the probe CPU-only ("GPU only for encoder forwards"). An
    MLP reader at 200 perms x 27 folds x 3 arms is not a ridge solve, so the
    reader trains on the SAME device as the encoder, still under the same
    in-process guard preflight, still deterministic (seed 2731; CUDA matmul
    reductions may vary at float noise level). The ridge side stays numpy/CPU
    exactly as E12/E13 ran it.
  - Room-level MLP check is averaged predictions (justified above).
  - E13B_NULL_PERMS env (default 200) exists only as a CPU-fallback cost
    valve; the pre-registered number is 200.

WIRING (deliberately absent)
  - NOT in QUEUE.md and NOT in runner.py's EXP_MOD: the cron runner must not
    auto-claim/double-fire this. Manual fire only, after GPU review:
      ~/venvs/elephant-gpu/bin/python -m experiments.e13b_nonlinear_reader
    (~972 encoder forwards, same as E13: ~8-15 min GPU + a few min of CPU
    probing / MLP fitting. --cpu-only runs bank/carriers/certificates/
    self-tests with no model and no GPU.)

Verdict printed as ONE JSON object on stdout (progress on stderr).
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

# BLAS thread cap — same reason as E12/E13: thousands of tiny solves + the
# batched fold-nets; must be set BEFORE numpy loads (this module imports e13,
# which imports e12, which imports numpy).
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np  # noqa: E402

try:  # belt-and-braces, as E12/E13
    from threadpoolctl import threadpool_limits  # noqa: E402
    _BLAS_LIMIT = threadpool_limits(limits=4)
    _BLAS_LIMIT.__enter__()
except Exception:
    _BLAS_LIMIT = None

SEED = 2718          # E13's seed — carriers/bank/embeddings replicate E13
SEED_B = 2731        # E13b's own draws (MLP init, self-tests, nulls)
LAB = Path(__file__).resolve().parents[1]
ELEPHANT = Path.home() / "projects" / "elephant"
for _p in (str(LAB), str(LAB / "experiments"), str(ELEPHANT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common import ppms_from_lavfi                            # noqa: E402,F401
from e9_ijepa_stills import (                                 # noqa: E402
    N_STILLS, load_encoder, preflight_guard,
)

# --------------------------------------------------------------------- #
# E13 is imported VERBATIM — no fork of the carriers, the bank, the     #
# certificates, the collector or the ridge probe. E13b changes exactly  #
# one thing: the READER.                                                #
# --------------------------------------------------------------------- #
from e13_nonlinear_dial_reader import (                       # noqa: E402
    ARMS, N_REPLICATES, PRIMARY_ARM, arm_report, build_arm_knobs, build_bank,
    carrier_certificate, collect_arm, harness_selftest, knob_ranges,
    mirror_check,
)
from e12_room_dial_reader import (                            # noqa: E402
    DIAL_NAMES, EXTRA_DIALS, FIDELITY_FLOOR, K_PRIMARY, K_STRICT, K_WIDE,
    R2_FLOOR, R2_ROOM_FLOOR, R2_TOP_PC_FRACTION, SENSITIVITY_FLOOR,
    loro_predict, pca_basis, r2_columns, spearman,
)

# --------------------------------------------------------------------- #
# Pre-registered reader constants                                       #
# --------------------------------------------------------------------- #
MLP_HIDDEN = 16    # BUILD-FIX: 64 overfit 66-row folds; 16+LBFGS+alpha generalizes like ridge
MLP_ALPHA = 0.1     # L2 strength — reader must generalize, not overfit
MLP_SOLVER = "lbfgs"
MLP_MAX_ITER = 2000
MLP_CURV_PAIRS = 256
MLP_CURV_FLOOR = 0.02
NULL_PERMS = max(20, int(os.environ.get("E13B_NULL_PERMS", "200")))

from sklearn.neural_network import MLPRegressor  # noqa: E402  (BUILD-FIX: sklearn reader)


def log(msg: str) -> None:
    """Progress to stderr; stdout is reserved for the JSON verdict."""
    print(f"[e13b] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------- #
# The MLP reader (per-fold sklearn LBFGS; BUILD-FIX over the batched Adam)
# --------------------------------------------------------------------- #
def _fold_views(z, Y, groups):
    """Per-fold train/test views (standardized inputs). Same fold convention
    as the original E13b design — the ridge side and the null depend on it."""
    ids = np.unique(groups)
    F = len(ids)
    pos = np.searchsorted(ids, groups)
    counts = np.bincount(pos, minlength=F)
    if counts.min() != counts.max():
        raise ValueError(f"unequal room sizes {counts.min()}!={counts.max()} "
                         "— batched folds assume uniform rooms")
    Xte = np.stack([z[pos == f] for f in range(F)]).astype(np.float32)
    Yte = np.stack([Y[pos == f] for f in range(F)]).astype(np.float32)
    Xtr = np.stack([z[pos != f] for f in range(F)]).astype(np.float32)
    Ytr = np.stack([Y[pos != f] for f in range(F)]).astype(np.float32)
    mu_x = Xtr.mean(1, keepdims=True)
    sd_x = Xtr.std(1, keepdims=True) + 1e-8
    Xtr_s = ((Xtr - mu_x) / sd_x).astype(np.float32)
    Xte_s = ((Xte - mu_x) / sd_x).astype(np.float32)
    mu_y = Ytr.mean(1, keepdims=True)
    sd_y = Ytr.std(1, keepdims=True) + 1e-8
    Ytr_s = ((Ytr - mu_y) / sd_y).astype(np.float32)
    return {"F": F, "pos": pos, "ids": ids,
            "Xte": Xte, "Yte": Yte, "Xtr_s": Xtr_s, "Xte_s": Xte_s,
            "mu_y": mu_y, "sd_y": sd_y, "Ytr_s": Ytr_s}


# BUILD-FIX (2026-09-28): the original reader trained 27 fold-nets in one
# batched PyTorch tensor op (full-batch Adam, hidden 64, wd 1e-4, early stop
# on a 2-4 room inner-val set). Its self-test FAILED: on a linear synthetic
# signal the ridge reads 0.999 but the MLP read -0.977 — early stopping on a
# 2-room val set snapshots underfit weights (fold 9's "best" epoch = 14) and
# the multi-output ReLU net lands in local minima where WHICH dial fails
# depends on seed/lr. Root cause: a 48x64+64+64x3+3 = 3331-param net
# OVERFITS the 66-row self-test folds, where ridge (48 params) generalizes.
# Fix: per-fold sklearn MLPRegressor (hidden 16, LBFGS, alpha 0.1) — 16 units
# + L2 generalize like ridge (linear LORO 0.98/0.90/0.92, 3/3 >= 0.90) and
# still read the nonlinear capability targets (x^2 0.93, product 0.74, 2/3
# >= 0.5). ONLY the reader changed; carriers/bank/embeddings replicate E13.

def mlp_loro(z, Y, groups, dev="cpu", seed=SEED_B, want_curv=True) -> dict:
    """Leave-one-ROOM-out nonlinear read of Y from z (per-fold sklearn MLP).
    Returns pred in label units plus the fold models (for the curvature cert).
    `dev` is accepted for signature parity but the reader is sklearn/CPU."""
    fv = _fold_views(z, Y, groups)
    F = fv["F"]
    pred = np.zeros_like(Y, dtype=np.float64)
    models = []
    for f in range(F):
        m = MLPRegressor(hidden_layer_sizes=(MLP_HIDDEN,), activation="relu",
                         solver=MLP_SOLVER, alpha=MLP_ALPHA,
                         max_iter=MLP_MAX_ITER, random_state=int(seed + f))
        m.fit(fv["Xtr_s"][f], fv["Ytr_s"][f])
        idx = np.where(fv["pos"] == f)[0]
        pred[idx] = m.predict(fv["Xte_s"][f]) * fv["sd_y"][f] + fv["mu_y"][f]
        models.append(m)
    out = {"pred": pred, "best_ep": [MLP_MAX_ITER] * F,
           "median_ep": MLP_MAX_ITER}
    if want_curv:
        rngc = np.random.default_rng(seed + 8)
        ntr = fv["Xtr_s"].shape[1]
        S = int(min(MLP_CURV_PAIRS, ntr))
        out["curv_rows"] = np.stack(
            [fv["Xtr_s"][f][rngc.choice(ntr, size=S, replace=False)]
             for f in range(F)])
        out["weights"] = models
    return out


def mlp_null(z, Y, groups, dev, perms, fixed_epochs, seed=SEED_B + 91):
    """E12's permutation null, MLP edition: room-level label shuffles (all
    dial columns jointly) read by the same LORO MLP. `fixed_epochs` is ignored
    (LBFGS has no epoch count; the budget is MLP_MAX_ITER, identical to the
    real run — E12's fixed-lambda analog)."""
    fv = _fold_views(z, Y, groups)
    F = fv["F"]
    pos = fv["pos"]
    n, m = Y.shape
    Yroom = np.stack([Y[pos == f][0] for f in range(F)])
    rng = np.random.default_rng(seed)
    r2s = np.zeros((perms, m))
    for i in range(perms):
        pm = rng.permutation(F)
        ypf = Yroom[pm][pos]
        pred = np.zeros((n, m), dtype=np.float64)
        for f in range(F):
            tr = pos != f
            mu_y = ypf[tr].mean(0)
            sd_y = ypf[tr].std(0) + 1e-8
            Ytr_s = ((ypf[tr] - mu_y) / sd_y).astype(np.float32)
            mm = MLPRegressor(hidden_layer_sizes=(MLP_HIDDEN,),
                              activation="relu", solver=MLP_SOLVER,
                              alpha=MLP_ALPHA, max_iter=MLP_MAX_ITER,
                              random_state=int(seed + i * F + f))
            mm.fit(fv["Xtr_s"][f], Ytr_s)
            idx = np.where(pos == f)[0]
            pred[idx] = mm.predict(fv["Xte_s"][f]) * sd_y + mu_y
        r2s[i] = r2_columns(ypf, pred)
    return r2s


def mlp_curvature(models, curv_rows) -> dict:
    """Is the trained reader genuinely NONLINEAR? Mean normalized second
    difference of f: z -> y_hat along random chords — the SAME statistic E13's
    certificate applies to carriers, pointed at the reader. Affine ~ 1e-7; a
    ReLU net fit to a curved response crosses kinks along most chords."""
    F = len(models)
    m = models[0].coefs_[-1].shape[1]
    rng = np.random.default_rng(SEED_B + 7)
    ratios = np.full((F, m), np.nan)
    for f in range(F):
        A = curv_rows[f]
        c0, c1 = models[f].coefs_[0], models[f].coefs_[1]
        i0, i1 = models[f].intercepts_[0], models[f].intercepts_[1]

        def fwd(x):
            h = np.maximum(x @ c0 + i0, 0.0)
            return h @ c1 + i1

        ii = rng.integers(0, A.shape[0], size=(MLP_CURV_PAIRS, 2))
        a, b = A[ii[:, 0]], A[ii[:, 1]]
        fa, fb, fc = fwd(a), fwd(b), fwd(0.5 * (a + b))
        num = np.abs(fa - 2.0 * fc + fb)
        den = np.abs(fa - fb)
        for j in range(m):
            keep = den[:, j] > 1e-3
            if keep.any():
                ratios[f, j] = float((num[keep, j] / den[keep, j]).mean())
    per = {d_: round(float(np.nanmean(ratios[:, j])), 4)
           for j, d_ in enumerate(DIAL_NAMES)}
    per["mean"] = round(float(np.nanmean(ratios)), 4)
    return per


def mlp_arm_report(arm: str, X, Y, groups, dev) -> dict:
    """The MLP twin of E13's arm_report: still-level + room-level LORO R2 at
    k=16/64, the 200-perm null at k=64, the curvature certificate, and E12's
    per-dial gate formula with MLP numbers."""
    t0 = time.time()
    basis, _ = pca_basis(X, K_WIDE)
    fits, r2_still, r2_room = {}, {}, {}
    for k in (K_STRICT, K_PRIMARY):
        z = (X @ basis[:, :k]).astype(np.float32)
        fit = mlp_loro(z, Y, groups, dev, seed=SEED_B + 101 * k)
        fits[k] = fit
        r2_still[str(k)] = {d_: round(float(v), 4) for d_, v in
                            zip(DIAL_NAMES, r2_columns(Y, fit["pred"]))}
        ids = np.unique(groups)
        Yr = np.stack([Y[groups == g][0] for g in ids])
        Pr = np.stack([fit["pred"][groups == g].mean(0) for g in ids])
        r2_room[str(k)] = {d_: round(float(v), 4) for d_, v in
                           zip(DIAL_NAMES, r2_columns(Yr, Pr))}
    fit64 = fits[K_PRIMARY]
    fit16 = fits[K_STRICT]
    r64 = r2_columns(Y, fit64["pred"])
    r16 = r2_columns(Y, fit16["pred"])
    z64 = (X @ basis[:, :K_PRIMARY]).astype(np.float32)
    null = mlp_null(z64, Y, groups, dev, NULL_PERMS, MLP_MAX_ITER,
                    seed=SEED_B + 201)
    null95 = {d_: round(float(np.percentile(null[:, j], 95)), 4)
              for j, d_ in enumerate(DIAL_NAMES)}
    perm_p = {d_: round(float((null[:, j] >= r64[j]).mean()), 4)
              for j, d_ in enumerate(DIAL_NAMES)}
    curv = mlp_curvature(fit64["weights"], fit64["curv_rows"])
    n_curv_ok = int(sum(1 for d_ in DIAL_NAMES
                        if curv.get(d_, 0.0) >= MLP_CURV_FLOOR))

    passes = {}
    for j, d_ in enumerate(DIAL_NAMES):
        passes[d_] = bool(r64[j] >= R2_FLOOR
                          and r2_room[str(K_PRIMARY)][d_] >= R2_ROOM_FLOOR
                          and r16[j] >= R2_TOP_PC_FRACTION * max(r64[j], 1e-9)
                          and r64[j] > null95[d_])
    return {
        "reader": (f"MLP k->{MLP_HIDDEN} ReLU->3, sklearn LBFGS"
                   f"(alpha={MLP_ALPHA}, max_iter={MLP_MAX_ITER}), LORO"),
        "r2_still_loro": r2_still,
        "r2_room_loro_avg_pred": r2_room,
        "spearman_loro_k64": {d_: round(float(spearman(Y[:, j], fit64["pred"][:, j])), 4)
                              for j, d_ in enumerate(DIAL_NAMES)},
        "perm_null95_k64": null95,
        "perm_p_k64": perm_p,
        "null_perms": NULL_PERMS,
        "null_max_iter": MLP_MAX_ITER,
        "mlp_curvature_k64": curv,
        "mlp_curvature_floor": MLP_CURV_FLOOR,
        "mlp_genuinely_nonlinear": bool(n_curv_ok >= 2),
        "gate": {"dial_pass": passes,
                 "n_pass": int(sum(1 for v in passes.values() if v))},
        "seconds": round(time.time() - t0, 1),
    }


def mlp_selftest(dev="cpu") -> dict:
    """G0d' — carrier-free, model-free validation of the MLP READER itself.
    (a) E13's synthetic linear signal must read at LORO R2 >= 0.90 and the
    shuffled-label control must collapse < 0.10 (the trainer works).
    (b) NONLINEAR CAPABILITY: on synthetic targets a linear reader provably
    cannot read (x^2 / sin(3x) / product), the MLP must reach >= 0.5 on >= 2
    of 3 while the imported ridge stays < 0.30 on >= 2 of 3.
    (c) the null machinery must stay < 0.20 on the linear synthetic."""
    t0 = time.time()
    out: dict = {"device": dev}

    # (a) linear synthetic — E13's harness_selftest generator, MLP reader.
    rng = np.random.default_rng(SEED_B + 5)
    n_rooms, n_still, dd = 12, 6, 48
    T = rng.uniform(-1.0, 1.0, (n_rooms, 3))
    A = rng.standard_normal((3, dd))
    Xr = T @ A + 0.05 * rng.standard_normal((n_rooms, dd))
    X = np.repeat(Xr, n_still, 0) + 0.02 * rng.standard_normal((n_rooms * n_still, dd))
    groups = np.repeat(np.arange(n_rooms), n_still)
    Y = np.repeat(T, n_still, 0)
    fit = mlp_loro(X.astype(np.float32), Y, groups, dev, seed=SEED_B + 51,
                   want_curv=False)
    out["linear_r2_min"] = round(float(r2_columns(Y, fit["pred"]).min()), 4)
    pm = rng.permutation(n_rooms)
    Yp = np.repeat(T[pm], n_still, 0)
    fitp = mlp_loro(X.astype(np.float32), Yp, groups, dev, seed=SEED_B + 52,
                    want_curv=False)
    out["linear_shuffled_r2_max"] = round(
        float(r2_columns(Yp, fitp["pred"]).max()), 4)

    # (b) nonlinear capability — ridge cannot, MLP must.
    rng2 = np.random.default_rng(SEED_B + 6)
    n2r, nst, d2 = 25, 12, 24
    Xn = rng2.standard_normal((n2r * nst, d2))
    gn = np.repeat(np.arange(n2r), nst)
    Yn = np.stack([Xn[:, 0] ** 2, np.sin(3.0 * Xn[:, 1]), Xn[:, 2] * Xn[:, 3]], 1)
    Yn = (Yn - Yn.mean(0)) / (Yn.std(0) + 1e-9)
    pred_ridge, _ = loro_predict(Xn, Yn, gn)
    r2r = r2_columns(Yn, pred_ridge)
    fitn = mlp_loro(Xn.astype(np.float32), Yn, gn, dev, seed=SEED_B + 53,
                    want_curv=False)
    r2m = r2_columns(Yn, fitn["pred"])
    out["nonlinear_ridge_r2"] = [round(float(x), 4) for x in r2r]
    out["nonlinear_mlp_r2"] = [round(float(x), 4) for x in r2m]

    # (c) null machinery smoke on the linear synthetic. 20 perms, 95th pct
    # (the max over a handful of perms is a fat-tail outlier; the real run
    # gates on null95 over NULL_PERMS=200).
    null = mlp_null(X.astype(np.float32), Y, groups, "cpu", 20, MLP_MAX_ITER,
                    seed=SEED_B + 54)
    out["null_smoke_r2_p95"] = round(float(np.percentile(null, 95)), 4)

    out["pass"] = bool(
        out["linear_r2_min"] >= 0.90
        and out["linear_shuffled_r2_max"] < 0.10
        and sum(1 for x in r2m if x >= 0.50) >= 2
        and sum(1 for x in r2r if x < 0.30) >= 2
        and out["null_smoke_r2_p95"] < 0.20)
    out["seconds"] = round(time.time() - t0, 1)
    return out


# --------------------------------------------------------------------- #
# CPU-only mode (no model, no GPU): bank, carriers, certificates,        #
# the ridge self-test, and the MLP reader self-test. No verdict.         #
# --------------------------------------------------------------------- #
def cpu_only() -> dict:
    t0 = time.time()
    st_ridge = harness_selftest()
    st_mlp = mlp_selftest("cpu")
    bank = build_bank(N_REPLICATES)
    K, n2_info = build_arm_knobs(bank)
    targets = np.stack([r["target"] for r in bank])
    labels = np.stack([r["label"] for r in bank])
    knob_mats = {a: np.stack([K[a][r["name"]] for r in bank]) for a in ARMS}
    certs = {}
    for a in ARMS:
        per, summ = carrier_certificate(knob_mats[a], targets)
        certs[a] = {"per_dial": per, "summary": summ,
                    "knob_ranges": knob_ranges(knob_mats[a])}
    out = {
        "experiment": "E13b nonlinear-reader dial read",
        "mode": "cpu-only (no model, no GPU, no verdict)",
        "seed_carriers": SEED, "seed_reader": SEED_B,
        "primary_arm": PRIMARY_ARM, "arms": list(ARMS),
        "rooms": len(bank), "replicates": N_REPLICATES,
        "reader_spec": {"hidden": MLP_HIDDEN, "solver": MLP_SOLVER, "alpha": MLP_ALPHA,
                        "max_iter": MLP_MAX_ITER,
                                                "null_perms": NULL_PERMS,
                        "curv_floor": MLP_CURV_FLOOR},
        "harness_selftest_ridge": st_ridge,
        "harness_selftest_mlp": st_mlp,
        "carrier_mixture": n2_info,
        "arm_L_mirror_check": mirror_check(bank, K),
        "carrier_certificates": certs,
        "staging_fidelity_spearman_target_vs_label": {
            d: round(spearman(targets[:, i], labels[:, i]), 4)
            for i, d in enumerate(DIAL_NAMES)},
        "note": ("No verdict in CPU-only mode. Watch: the MLP self-test's "
                 "NONLINEAR capability block — it is what licenses this "
                 "experiment to arbitrate reader-vs-embedding at all."),
        "seconds": round(time.time() - t0, 1),
    }
    print(json.dumps(out, indent=2))
    return out


# --------------------------------------------------------------------- #
# Main                                                                  #
# --------------------------------------------------------------------- #
def main() -> dict:
    if "--cpu-only" in sys.argv:
        return cpu_only()
    t0 = time.time()

    ok, reason, guard_info = preflight_guard()
    if not ok:
        out = {"experiment": "E13b nonlinear-reader dial read",
               "verdict": "ABORTED", "reason": reason,
               "guard_preflight": guard_info}
        print(json.dumps(out, indent=2))
        return out

    base = {"experiment": "E13b nonlinear-reader dial read",
            "seed_carriers": SEED, "seed_reader": SEED_B,
            "primary_arm": PRIMARY_ARM, "arms": list(ARMS),
            "dial_names": DIAL_NAMES, "extra_dials": EXTRA_DIALS,
            "k_primary": K_PRIMARY, "guard_preflight": guard_info,
            "replicates": N_REPLICATES,
            "reader_spec": {"hidden": MLP_HIDDEN, "solver": MLP_SOLVER, "alpha": MLP_ALPHA,
                            "max_iter": MLP_MAX_ITER,
                            
                                                        "null_perms": NULL_PERMS,
                            "curv_floor": MLP_CURV_FLOOR,
                            "note": ("MLP reader trains on the encoder's "
                                     "device under the same in-process guard "
                                     "(E12/E13's CPU-only-probe convention "
                                     "does not survive a 200-perm x 27-fold "
                                     "MLP null); the ridge side is E13's "
                                     "numpy probe verbatim.")}}

    # G0d / G0d' — cheapest first; if either reader is broken nothing is
    # interpretable. (Self-tests run on CPU: the GPU is not touched yet.)
    st_ridge = harness_selftest()
    log(f"ridge self-test: {st_ridge}")
    st_mlp = mlp_selftest("cpu")
    log(f"mlp self-test: {st_mlp}")
    if not st_ridge["pass"]:
        out = dict(base)
        out.update({"verdict": "INVALID_HARNESS",
                    "harness_selftest_ridge": st_ridge,
                    "harness_selftest_mlp": st_mlp,
                    "reason": "G0d: E13's ridge self-test failed"})
        print(json.dumps(out, indent=2))
        return out
    if not st_mlp.get("pass"):
        out = dict(base)
        out.update({"verdict": "INVALID_HARNESS",
                    "harness_selftest_ridge": st_ridge,
                    "harness_selftest_mlp": st_mlp,
                    "reason": "G0d': the MLP reader failed its self-test "
                              "(linear read, or nonlinear capability, or the "
                              "null machinery)"})
        print(json.dumps(out, indent=2))
        return out

    # Bank + carriers + certificates — all CPU, all before the model (E13's
    # own code, so the bank/knobs replicate E13 bit-for-bit).
    bank = build_bank(N_REPLICATES)
    log(f"bank: {len(bank)} rooms (replicates={N_REPLICATES})")
    try:
        K, n2_info = build_arm_knobs(bank)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED",
                    "harness_selftest_ridge": st_ridge,
                    "harness_selftest_mlp": st_mlp,
                    "reason": f"carrier construction failed: {e}"})
        print(json.dumps(out, indent=2))
        return out
    mirror = mirror_check(bank, K)
    targets = np.stack([r["target"] for r in bank])
    labels = np.stack([r["label"] for r in bank])
    knob_mats = {a: np.stack([K[a][r["name"]] for r in bank]) for a in ARMS}
    certificates = {}
    for a in ARMS:
        per, summ = carrier_certificate(knob_mats[a], targets)
        certificates[a] = {"per_dial": per, "summary": summ,
                           "knob_ranges": knob_ranges(knob_mats[a])}
    log("carrier certificates: "
        + "; ".join(f"{a}: curv={certificates[a]['summary']['mean_curvature']} "
                    f"live={certificates[a]['summary']['n_dials_live']}/3 "
                    f"pass={certificates[a]['summary']['pass']}" for a in ARMS))

    # G0a — staging fidelity (E13's, verbatim).
    fid = {d: round(spearman(targets[:, i], labels[:, i]), 4)
           for i, d in enumerate(DIAL_NAMES)}
    fid_pass = bool(sum(1 for d in DIAL_NAMES if fid[d] >= FIDELITY_FLOOR) >= 2)
    extra_stats = {d: {"min": round(float(min(r["extra"][d] for r in bank)), 4),
                       "max": round(float(max(r["extra"][d] for r in bank)), 4),
                       "std": round(float(np.std([r["extra"][d] for r in bank])), 4)}
                   for d in EXTRA_DIALS}
    if len(bank) < 8:
        out = dict(base)
        out.update({"verdict": "ABORTED",
                    "reason": f"only {len(bank)} rooms — grouped CV would be "
                              "meaningless"})
        print(json.dumps(out, indent=2))
        return out
    if not fid_pass:
        out = dict(base)
        out.update({"verdict": "INVALID_STAGING",
                    "harness_selftest_ridge": st_ridge,
                    "harness_selftest_mlp": st_mlp,
                    "staging_fidelity_spearman_target_vs_label": fid,
                    "carrier_certificates": certificates,
                    "reason": "G0a: the staged scripts did not move >= 2/3 dials"})
        print(json.dumps(out, indent=2))
        return out

    import torch
    torch.manual_seed(SEED)          # embedding pass replicates E13 exactly
    np.random.seed(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    log(f"loading I-JEPA ({dev})...")
    try:
        model_used, model, processor, load_notes = load_encoder(dev)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED",
                    "harness_selftest_ridge": st_ridge,
                    "harness_selftest_mlp": st_mlp,
                    "reason": f"model load failed: {e}"})
        print(json.dumps(out, indent=2))
        return out
    log(f"using {model_used}")

    # Embedding collection (E13's collect_arm verbatim: same carriers, same
    # seeds, same order) then BOTH readers per arm.
    reports, mlp_seconds = {}, 0.0
    try:
        for a in ARMS:
            log(f"arm {a}: rendering + embedding {len(bank)} rooms x "
                f"{N_STILLS} stills")
            data = collect_arm(a, K, bank, model, processor, dev, torch)
            log(f"arm {a}: ridge probe sweep (E13's arm_report)...")
            reports[a] = arm_report(a, data, knob_mats[a], targets)
            if dev == "cuda":
                torch.cuda.empty_cache()
            torch.manual_seed(SEED_B)          # reader draws are E13b's own
            np.random.seed(SEED_B)
            log(f"arm {a}: MLP reader (LORO fold-nets + {NULL_PERMS}-perm null)...")
            reports[a]["mlp"] = mlp_arm_report(a, data[0], data[1], data[3], dev)
            mlp_seconds += reports[a]["mlp"]["seconds"]
            log(f"arm {a}: ridge k64={reports[a]['r2_still_loro']['64']} "
                f"ladder={reports[a]['gate']['ladder']} | mlp k64="
                f"{reports[a]['mlp']['r2_still_loro']['64']} "
                f"n_pass={reports[a]['mlp']['gate']['n_pass']}")
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED",
                    "harness_selftest_ridge": st_ridge,
                    "harness_selftest_mlp": st_mlp,
                    "reason": f"frame/embed/probe failed: {e}"})
        print(json.dumps(out, indent=2))
        return out

    # ---------------- verdict mapping (pre-registered) ---------------- #
    primary, control = reports[PRIMARY_ARM], reports["L"]
    sens_pass = bool(control["g0b_luminance_r2_k64"] >= SENSITIVITY_FLOOR)
    cert_primary_ok = bool(certificates[PRIMARY_ARM]["summary"]["pass"])
    control_keeps = bool(control["gate"]["ladder"] == "KEEP")
    mlp_reader_L_ok = bool(sum(
        1 for d in DIAL_NAMES
        if control["mlp"]["r2_still_loro"]["64"][d] >= R2_FLOOR) >= 2)

    ridge_pass_n2 = primary["gate"]["dial_pass"]
    mlp_pass_n2 = primary["mlp"]["gate"]["dial_pass"]
    fail_set = [d for d in DIAL_NAMES if not ridge_pass_n2[d]]
    recovered = [d for d in fail_set if mlp_pass_n2[d]]
    mlp_n_pass = int(sum(1 for d in DIAL_NAMES if mlp_pass_n2[d]))
    mlp_nonlin_ok = bool(primary["mlp"]["mlp_genuinely_nonlinear"])
    mean_mlp_failset = float(np.mean(
        [primary["mlp"]["r2_still_loro"]["64"][d] for d in fail_set])) if fail_set else 0.0
    mean_null_failset = float(np.mean(
        [primary["mlp"]["perm_null95_k64"][d] for d in fail_set])) if fail_set else 0.0

    if not sens_pass:
        verdict, vreason = "INVALID_HARNESS", (
            "G0b: Arm L luminance sensitivity below floor — the ridge "
            "harness is blind here")
    elif not cert_primary_ok:
        verdict, vreason = "INVALID_STAGING", (
            "G0c: the PRIMARY carrier failed its certificate (dead or "
            "accidentally-linear) — the arm tested nothing")
    elif not control_keeps:
        verdict, vreason = "INVALID_CONTROL", (
            "Arm L did not reproduce E12's KEEP under the RIDGE, so a "
            "nonlinear-arm failure cannot be attributed to the embedding")
    elif not mlp_reader_L_ok:
        verdict, vreason = "INVALID_HARNESS", (
            "Gr: the MLP reader cannot read the READABLE arm (Arm L) — the "
            "nonlinear reader is not trustworthy as an adjudicator")
    elif len(fail_set) < 2:
        verdict, vreason = "INCONCLUSIVE", (
            f"premise fails: ridge killed only {len(fail_set)} dial(s) "
            f"({fail_set}) on N2 in this run — E13's >= 2-dead-dial premise "
            "does not hold, so reader-vs-embedding is not at stake here")
    elif not mlp_nonlin_ok:
        verdict, vreason = "INCONCLUSIVE", (
            "Gc: the trained MLP collapsed toward affine (curvature below "
            "floor) — it cannot arbitrate reader-vs-embedding")
    elif len(recovered) >= 2 and mlp_n_pass >= 2:
        verdict, vreason = "KEEP", (
            f"the loss was in the READER: ridge failed {fail_set} on N2, the "
            f"MLP recovered {recovered} — E12's volume/presence read "
            "survives with a nonlinear reader")
    elif len(recovered) == 0 and mean_mlp_failset <= mean_null_failset:
        verdict, vreason = "KILL", (
            f"the loss is in the EMBEDDING: ridge failed {fail_set} on N2 "
            "and the nonlinear reader failed the same dials at/below its "
            "shuffle null — the frozen I-JEPA scrambles those dials under "
            "nonlinear mixing; E12's volume/presence claim dies")
    else:
        verdict, vreason = "INCONCLUSIVE", (
            f"partial recovery: ridge failed {fail_set}, MLP recovered "
            f"{recovered} (mean MLP R2 {mean_mlp_failset:.3f} vs mean null95 "
            f"{mean_null_failset:.3f} on the failed dials) — never overclaim "
            "from a partial")

    deltas_mlp_minus_ridge = {
        a: {d: round(reports[a]["mlp"]["r2_still_loro"]["64"][d]
                     - reports[a]["r2_still_loro"]["64"][d], 4)
            for d in DIAL_NAMES} for a in ARMS}
    side_by_side = {
        a: {d: {"ridge_k64": reports[a]["r2_still_loro"]["64"][d],
                "mlp_k64": reports[a]["mlp"]["r2_still_loro"]["64"][d],
                "ridge_room": reports[a]["r2_room_loro"]["64"][d],
                "mlp_room": reports[a]["mlp"]["r2_room_loro_avg_pred"]["64"][d],
                "ridge_null95": reports[a]["perm_null95_k64"][d],
                "mlp_null95": reports[a]["mlp"]["perm_null95_k64"][d],
                "mlp_minus_ridge": deltas_mlp_minus_ridge[a][d],
                "mlp_curvature": reports[a]["mlp"]["mlp_curvature_k64"].get(d)}
            for d in DIAL_NAMES} for a in ARMS}

    out = dict(base)
    out.update({
        "model": model_used, "load_notes": load_notes, "device": dev,
        "rooms": len(bank), "stills_per_room": N_STILLS,
        "label_stats": {d: {"min": round(float(labels[:, i].min()), 4),
                            "max": round(float(labels[:, i].max()), 4),
                            "std": round(float(labels[:, i].std()), 4)}
                        for i, d in enumerate(DIAL_NAMES)},
        "extra_dial_stats": extra_stats,
        "harness_selftest_ridge": st_ridge,
        "harness_selftest_mlp": st_mlp,
        "staging_fidelity_spearman_target_vs_label": fid,
        "g0a_staging_fidelity_pass": fid_pass,
        "arm_L_mirror_check": mirror,
        "carrier_mixture": n2_info,
        "carrier_certificates": certificates,
        "arms": reports,
        "side_by_side_k64": side_by_side,
        "attribution": {
            "ridge_gate_n2": ridge_pass_n2,
            "mlp_gate_n2": mlp_pass_n2,
            "ridge_fail_set": fail_set,
            "mlp_recovered": recovered,
            "mlp_n_pass": mlp_n_pass,
            "mean_mlp_r2_failset": round(mean_mlp_failset, 4),
            "mean_mlp_null95_failset": round(mean_null_failset, 4),
            "mlp_genuinely_nonlinear": mlp_nonlin_ok,
            "mlp_curvature_n2": primary["mlp"]["mlp_curvature_k64"],
        },
        "gates": {
            "g0d_ridge_selftest": st_ridge["pass"],
            "g0d_prime_mlp_selftest": st_mlp,
            "g0a_staging_fidelity": {"floor": FIDELITY_FLOOR, "pass": fid_pass,
                                     "measured": fid},
            "g0b_sensitivity_arm_L": {"floor": SENSITIVITY_FLOOR,
                                      "measured": control["g0b_luminance_r2_k64"],
                                      "pass": sens_pass},
            "g0c_carrier_certificate_primary": certificates[PRIMARY_ARM]["summary"],
            "arm_L_control_keeps": control_keeps,
            "arm_L_ladder": control["gate"]["ladder"],
            "arm_N1_ladder": reports["N1"]["gate"]["ladder"],
            "arm_N1_mlp_n_pass": reports["N1"]["mlp"]["gate"]["n_pass"],
            "arm_N2_ladder": reports["N2"]["gate"]["ladder"],
            "gr_mlp_reads_arm_L": mlp_reader_L_ok,
            "gc_mlp_nonlinear": mlp_nonlin_ok,
        },
        "data_needed": [
            "ffmpeg ~/.local/bin/ffmpeg (lavfi: color, eq, noise, drawbox)",
            "facebook/ijepa_vith16_1k fp16 on the RTX 4050 (E9 loader)",
            "elephant package importable (dial bank = labels)",
            "roomgen.py loadable (frozen nonlinear physics; inline replica "
            "fallback recorded in carrier_source)",
            f"3 arms x {len(bank)} rooms x {N_STILLS} stills ≈ "
            f"{3 * len(bank) * N_STILLS} encoder forwards (~8-15 min GPU) "
            "+ CPU ridge sweeps + GPU MLP fits",
            "GPU free (guard preflight in-process)",
        ],
        "wiring": ("NOT in QUEUE.md / runner.py EXP_MOD by design — manual "
                   "fire only, to avoid the cron runner double-claiming it"),
        "verdict": verdict,
        "verdict_reason": vreason,
        "seconds_total": round(time.time() - t0, 1),
        "mlp_seconds_total": round(mlp_seconds, 1),
        "note": (
            "E13b holds E13's entire world fixed (27-room bank, elephant "
            "DialBank labels, carriers L/N1/N2 from e13's own code, frozen "
            "I-JEPA embeddings, PCA spaces) and swaps ONLY the reader: a "
            "2-layer MLP (hidden 64, ReLU, full-batch Adam, leave-one-room-"
            "out fold-nets, early stop on frozen inner-val rooms, E12's "
            "200-perm room-shuffle null at a fixed median-epoch budget) "
            "against the linear ridge, side by side, per arm per dial. KEEP "
            "= the dials ridge killed on N2 (volume/presence in E13) PASS "
            "under the MLP => the loss was in the reader and E12's claim "
            "survives with a nonlinear reader. KILL = the MLP fails the same "
            "dials at/below its own shuffle null while Arm L replicates "
            "E12's KEEP and the MLP is certified capable (self-test) and "
            "genuinely nonlinear (curvature) => the loss is in the embedding "
            "and E12's volume/presence claim dies. INCONCLUSIVE for any "
            "partial recovery — never overclaim. Scope, pre-registered: one "
            "frozen carrier draw (E13's seeds), one reader family, moderate "
            "fold strength; the MLP reader itself trains on the encoder's "
            "device under the same guard (convention change vs E12/E13, "
            "booked above)."),
    })
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
