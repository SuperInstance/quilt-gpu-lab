#!/usr/bin/env python3
"""X6 — dial-range extrapolation: did LORO ever test the RANGE, or only rooms?

CLAIM UNDER TEST (concrete, falsifiable)
  Every KEEP in the E12 family (E12 Arm B, E13's Arm-L replicate, E15's
  four-encoder leaderboard) validates the frozen-I-JEPA dial read with
  leave-one-ROOM-out CV. LORO holds out a ROOM, but every held-out room's
  dial values still sit INSIDE the trained dial ranges: on the 27-cell grid
  (m ∈ {-0.8,0,+0.8}, v,p ∈ {0.15,0.50,0.85}) a held-out room is always
  INTERPOLATED in dial space. If the ridge reader memorized the staging
  manifold's LOCAL geometry — the embedding's dial direction valid only
  across the trained range — then LORO could not have caught it, and the
  read should COLLAPSE when asked to extrapolate to dial values beyond
  everything it trained on. X6 re-splits E12's 27-room bank by DIAL VALUE
  instead of by room and compares, on the SAME embeddings:

    interpolation : E12's standard LORO ridge (k=64), all 27 rooms (the
                    E12-comparable headline), AND — for the gated ratio —
                    LORO WITHIN the train rooms only (interpolation in the
                    trained range, same yardstick as the test, see the
                    amendment below).
    extrapolation : per dial d (raw dial units, pre-registered threshold
                    0.7): train on rooms with t_d <= 0.7, test on rooms with
                    t_d > 0.7.
                      mood     : train m ∈ {-0.8, 0}    test m = +0.8
                      volume   : train v ∈ {0.15, 0.50} test v = 0.85
                      presence : train p ∈ {0.15, 0.50} test p = 0.85
                    Room-disjoint by construction (a room has ONE value per
                    dial, so all 12 of its stills fall wholly on one side).
                    Ridge fit on train only; λ chosen by inner leave-one-room
                    CV WITHIN the train set (no test contact); error on test.

  KILL  = the read is range-local (manifold memorization): extrapolation
          < 0.6× interpolation on ≥ 2/3 dials. Every LORO KEEP in the family
          must then be re-read as range-bound.
  KEEP  = the read is a genuine dial direction that extends beyond the
          trained range: extrapolation ≥ 0.8× interpolation on ≥ 2/3 dials.
  INCONCLUSIVE = between the two (or split).

AMENDMENT — the scoring currency (fixed BEFORE any GPU spend, from the
  --cpu-only split audit, 2026-09-28)
  The audit showed the test side of every 1D split is ONE grid level, so the
  SPLIT dial's test-side label variance is (near-)zero — in this bank the
  mood test labels are constant at 1.0, presence at 0.6555, volume spans
  0.6739..0.6897 — and a test-variance R² is undefined (numerically ~-1e12)
  regardless of prediction quality. The gated quantity is therefore a
  FIXED-DENOMINATOR R²: both interpolation and extrapolation mean squared
  error are normalized by the TRAIN-side label variance of that split
  (per-sample population variance, the same yardstick for both), and the
  interpolation side of the ratio is LORO run WITHIN the train rooms — pure
  interpolation in the trained range, evaluated in exactly the same
  currency. ratio_d := R²x_d / R²i_d with
      R²x_d = 1 - MSE_test(d) / Var_train(d)      (held-out high range)
      R²i_d = 1 - MSE_loro_within_train(d) / Var_train(d)
  E12's standard all-27 LORO R² (test-variance currency) is still computed
  and still feeds G1 (baseline replication), so the family comparability is
  intact. Raw test RMSE in label units and the train-mean-predictor floor
  (the same currency) sit beside every number so the yardstick is auditable.
  The degenerate test-variance R² values are reported too, as the evidence
  for this amendment.

ALSO (booked, not gated): a 2D corner split — train on ONE CORNER of the
  mood×presence plane (m ≤ 0.7 AND p ≤ 0.7: 12 rooms), test on the remaining
  15 rooms (m > 0.7 OR p > 0.7). Extrapolation off the corner in two dials
  at once; volume stays interpolated (train covers all v levels). Both
  currencies reported (the corner test side DOES vary in both extrapolated
  dims).

CONTROLS / BOOKED (never gated)
  C0 split audit      : exact train/test room counts + per-side label ranges
                        printed in the JSON (the split is on the STAGED
                        TARGET triple — the ground truth of what was staged;
                        the elephant's noisy reading is what the ridge
                        predicts — and every grid level must land wholly on
                        one side or the split is ill-defined).
  C1 raw-pixel probe  : the same 1D splits on E12's 16×9 grayscale stills.
                        On E12's AFFINE carrier the true dial→pixel map is
                        affine, so pixels should extrapolate ~perfectly;
                        JEPA features are nonlinear in pixels. If pixels
                        extrapolate where the embedding collapses, the
                        memorization lives in the encoder's nonlinearity,
                        not in the probe.
  C2 train-only basis : the primary keeps E12's all-stills label-free PCA
                        basis so interpolation and extrapolation differ ONLY
                        by the split. The variant refits the basis on train
                        stills only — if extrapolation dies only under the
                        all-stills basis, the basis itself was bridging the
                        range gap.
  C3 room-level extrap: E12's room-mean convention (overdetermined width
                        min(64, n_train//2), inner-CV λ) applied to the
                        train/test room split — the strict still-noise-free
                        version of the extrapolation number.
  C4 train-mean floor : predicting the train-label mean on test, in the same
                        fixed-denominator currency (the explicit floor: a
                        reader that cannot move past the trained range
                        scores AT this floor, below it is worse than lazy).
  C5 targets arm      : the identical split/probe run on the STAGED TARGET
                        triple as Y (not the elephant's reading). The staged
                        parameter is the dial by construction; if labels and
                        targets disagree, the difference is the label
                        transform (e.g. mood saturating at 1.0), not the
                        embedding.
  C6 mood low holdout : mood's grid is two-sided; the gated split holds out
                        the WARM end only. The mirror split (train m ∈
                        {0,+0.8}, test m = -0.8) checks the cold end too.

PRE-REGISTERED GATES (fixed before running; this file IS the registration)
  G0a staging fidelity : Spearman(target, elephant_label) ≥ 0.5 for ≥ 2/3
      dials on the bank, else INVALID_STAGING (E12's G0a verbatim — a KILL
      from a dead staging is meaningless).
  G0d harness self-test: E13's CPU-only synthetic probe self-test must pass,
      else INVALID_HARNESS.
  G1 baseline          : the interpolation LORO R²(k=64) measured IN THIS RUN
      must be ≥ 0.30 (E12's R2_FLOOR) on ≥ 2/3 dials, else INVALID_BASELINE —
      E12's KEEP did not replicate in this harness instance, so the ratio
      gate's denominator is dead and the comparison is void. Never a KILL.
  G2 THE RATIO GATE    : per dial on its own 1D split, ratio_d as defined in
      the amendment (fixed train-variance denominator, both sides). Dials
      whose range-interpolation R²i ≤ 0.05 (dead denominator in the ratio
      currency) are excluded from both counts; G1 guarantees ≥ 2 dials have
      a living baseline before this can bind.
        KILL : ratio < 0.6 on ≥ 2 dials.
        KEEP : ratio ≥ 0.8 on ≥ 2 dials.
        INCONCLUSIVE otherwise.
  ABORTED              : guard preflight, model load, no frames, < 8 rooms,
      or the split audit fails (grid changed under us).

HONESTY / CAVEATS BOOKED WITH THE RESULT
  - A 3-level grid makes "extrapolation" = ONE grid step beyond the trained
    edge (0.50 → 0.85 in v/p; 0 → +0.8 in m), and makes the held-out level a
    CONSTANT — hence the fixed-denominator currency (amendment above). The
    honest widening (a densified mid/high grid) is a follow-up experiment,
    not a change to this gate.
  - Labels are room-level (broadcast to stills) exactly as in E12; the
    extrapolation split is room-disjoint, so no within-room leakage is
    possible in either direction.
  - The label transform is nonlinear (mood saturates at ±1, presence
    compresses 0.15..0.85 into 0.52..0.66) — C5 (targets arm) separates
    "the embedding stops extrapolating" from "the label saturates".
  - Volume's carrier (noise + contrast) and presence's (drawn boxes) ride on
    fields that keep changing smoothly across the 0.7 boundary — the carrier
    does not change regime at the split; if the read dies anyway, it died in
    the embedding, not in the render.
  - One encoder (ijepa_vith16_1k, E12's), one carrier (E12's linear staging —
    the arm that KEPT). E13's N2 arm already failed 2/3 dials even under
    LORO, so there is nothing left there for extrapolation to kill.

Dev path: `python -m experiments.x6_extrapolation --cpu-only` runs the bank +
split audit + harness self-test with no model and no GPU (no verdict).

Verdict printed as ONE JSON object on stdout (progress on stderr).
Deterministic (seed 2718). CPU-only probe; GPU only for encoder forwards.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# BLAS thread cap before numpy (same rationale as E12/E13: thousands of tiny
# ridge solves in the inner-CV lambda grid).
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
from e9_ijepa_stills import N_STILLS, load_encoder, preflight_guard  # noqa: E402

# --------------------------------------------------------------------- #
# E12 / E13 reused VERBATIM by import — no fork of the bank, the carrier,
# the loader, or the probe. X6 changes exactly one thing: the SPLIT.      #
# --------------------------------------------------------------------- #
from e12_room_dial_reader import (                            # noqa: E402
    DIAL_NAMES, K_PRIMARY, R2_FLOOR, RATE, SECONDS, W, H,
    _ridge_fit_predict, embed_stills, loro_predict, pca_basis, pick_lambda,
    r2_columns, spearman, stage_source,
)
from e13_nonlinear_dial_reader import build_bank, harness_selftest  # noqa: E402

# --------------------------------------------------------------------- #
# Pre-registered constants                                              #
# --------------------------------------------------------------------- #
TAU = 0.7              # dial-range split threshold, raw dial units
KEEP_RATIO = 0.8       # extrapolation >= 0.8x interpolation
KILL_RATIO = 0.6       # extrapolation <  0.6x interpolation
VALID_DIALS_FLOOR = 2  # G1: >= 2/3 dials must replicate the baseline
RATIO_DEN_FLOOR = 0.05  # range-interp R2i below this = dead ratio denominator
CORNER_M = TAU         # 2D corner: m <= TAU AND p <= TAU is train
CORNER_P = TAU


def log(msg: str) -> None:
    """Progress goes to stderr; stdout is reserved for the JSON verdict."""
    print(f"[x6] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------- #
# Splits (room-index masks; stills inherit their room's side)            #
# --------------------------------------------------------------------- #
def split_1d(targets: np.ndarray, i: int, tau: float = TAU):
    """Dial-range split for dial i: train rooms t_i <= tau, test t_i > tau.

    Split on the STAGED TARGET (what was staged), not the elephant's noisy
    label (what the ridge predicts) — the target triple is the ground truth
    of the staging and every grid level lands wholly on one side.
    """
    t = np.asarray(targets, float)[:, i]
    tr = t <= tau
    te = ~tr
    return tr, te, float(t.min()), float(t.max())


def split_corner(targets: np.ndarray, tau_m: float = CORNER_M,
                 tau_p: float = CORNER_P):
    """2D corner split on the mood×presence plane: train = the low-low
    corner (m <= tau_m AND p <= tau_p), test = everything outside it."""
    t = np.asarray(targets, float)
    tr = (t[:, 0] <= tau_m) & (t[:, 2] <= tau_p)
    return tr, ~tr


# --------------------------------------------------------------------- #
# Fixed-denominator scoring (the amendment currency)                     #
# --------------------------------------------------------------------- #
def _expand(mask: np.ndarray, groups: np.ndarray) -> np.ndarray:
    """Room-level split mask (len = n_rooms) -> still-level mask (len =
    n_stills). Stills inherit their room's side; already-still-level masks
    pass through unchanged."""
    m = np.asarray(mask, bool)
    return m[groups] if len(m) == len(np.unique(groups)) else m


def r2_fixed_den(y: np.ndarray, pred: np.ndarray, den_var: np.ndarray) -> list:
    """1 - MSE/var, with the denominator FIXED to the train-side per-sample
    variance of the same split — defined even when the test side is a single
    constant level (which a 3-level grid range-split always is)."""
    mse = ((np.asarray(y, float) - np.asarray(pred, float)) ** 2).mean(0)
    return [round(float(1.0 - m / max(float(v), 1e-18)), 4)
            for m, v in zip(mse, den_var)]


def rmse_cols(y: np.ndarray, pred: np.ndarray) -> list:
    return [round(float(np.sqrt(((np.asarray(y, float)
                                  - np.asarray(pred, float)) ** 2).mean(0)[j])), 4)
            for j in range(np.asarray(y, float).shape[1])]


def train_mean_floor(y_tr: np.ndarray, y_te: np.ndarray,
                     den_var: np.ndarray) -> list:
    """C4: the train-mean predictor, scored in the same currency."""
    pred = np.repeat(y_tr.mean(0, keepdims=True), len(y_te), axis=0)
    return r2_fixed_den(y_te, pred, den_var)


# --------------------------------------------------------------------- #
# Range evaluation (extrapolation + within-train interpolation, one call) #
# --------------------------------------------------------------------- #
def range_eval(z, Y, groups, tr, te) -> dict:
    """The full per-split evaluation, all in the fixed-denominator currency:

    extrap  : ridge on train rooms -> predict test rooms (lambda by inner
              leave-one-room CV within train; no test contact).
    interp  : E12's LORO run WITHIN the train rooms only — pure
              interpolation in the trained range, same yardstick. THIS is
              the ratio's denominator (R2i).
    Also: raw test RMSE, the train-mean floor, E12's standard test-variance
    R2 on the test subset (kept as the amendment's evidence: undefined for
    the split dial), and the fit's lambda.
    """
    tr_ids = np.where(tr)[0]
    tr_s, te_s = _expand(tr, groups), _expand(te, groups)
    room_tr = np.asarray(groups)[tr_s]                # room id per train still
    var_tr = np.asarray(Y, float)[tr_s].var(0)        # per-sample, per-dial
    lam = pick_lambda(z[tr_s], Y[tr_s], room_tr)
    pred_te = _ridge_fit_predict(z[tr_s], Y[tr_s], z[te_s], lam)
    pred_in, lam_in = loro_predict(z[tr_s], Y[tr_s], room_tr)
    yte, ytr = np.asarray(Y, float)[te_s], np.asarray(Y, float)[tr_s]
    return {
        "lambda": round(float(lam), 6),
        "r2i_range": r2_fixed_den(ytr, pred_in, var_tr),      # denominator
        "r2x_range": r2_fixed_den(yte, pred_te, var_tr),      # numerator
        "rmse_test": rmse_cols(yte, pred_te),
        "train_mean_floor_r2": train_mean_floor(ytr, yte, var_tr),
        "var_train": [round(float(v), 6) for v in var_tr],
        "r2_testvar_evidence": [round(float(v), 4)
                                for v in r2_columns(yte, pred_te)],
    }


def room_level_extrap(z, Y, groups, tr, te) -> dict:
    """C3: E12's room-mean convention on the range split — fit on train ROOM
    means (overdetermined width min(K_PRIMARY, n_train//2)), predict test
    room means, fixed-denominator currency (den = train room-level var)."""
    ids = np.unique(groups)
    Xr = np.stack([z[groups == g].mean(0) for g in ids])
    Yr = np.stack([Y[groups == g].mean(0) for g in ids])
    tr_ids, te_ids = np.where(tr)[0], np.where(te)[0]
    k_room = int(min(K_PRIMARY, Xr.shape[1], max(4, len(tr_ids) // 2)))
    lam = pick_lambda(Xr[tr_ids, :k_room], Yr[tr_ids], tr_ids)
    pred = _ridge_fit_predict(Xr[tr_ids, :k_room], Yr[tr_ids],
                              Xr[te_ids, :k_room], lam)
    return {"r2x_room_level": r2_fixed_den(Yr[te_ids], pred,
                                           Yr[tr_ids].var(0)),
            "room_probe_width": k_room}


def basis_only_train(X, Y, groups, tr, te) -> dict:
    """C2: refit the PCA basis on TRAIN stills only, then the same
    extrapolation fit in the fixed-denominator currency. If this differs
    materially from the primary (all-stills label-free basis), the basis was
    bridging the range gap."""
    tr_s, te_s = _expand(tr, groups), _expand(te, groups)
    room_tr = np.asarray(groups)[tr_s]
    b_tr, _ = pca_basis(X[tr_s], K_PRIMARY)
    z_tr, z_te = X[tr_s] @ b_tr, X[te_s] @ b_tr
    var_tr = np.asarray(Y, float)[tr_s].var(0)
    lam = pick_lambda(z_tr, Y[tr_s], room_tr)
    pred = _ridge_fit_predict(z_tr, Y[tr_s], z_te, lam)
    return {"r2x_train_only_basis": r2_fixed_den(Y[te_s], pred, var_tr)}


# --------------------------------------------------------------------- #
# Embedding collection (E12's carrier + loader, E13's collect pattern)   #
# --------------------------------------------------------------------- #
def collect(bank: list, model, processor, dev, torch):
    X, Y, Yt, groups, lum, pix = [], [], [], [], [], []
    for gi, r in enumerate(bank):
        m, v, p = (float(r["target"][0]), float(r["target"][1]),
                   float(r["target"][2]))
        src = stage_source(m, v, p, r["seed"])     # E12's linear carrier
        frames = ppms_from_lavfi(src, SECONDS, RATE, (W, H))
        if not frames:
            raise RuntimeError(f"no frames from staged source {r['name']!r}")
        vecs, l, px = embed_stills(model, processor, dev, frames, r["seed"])
        groups.append(np.full(len(vecs), gi))
        X.append(vecs)
        Y.append(np.repeat(r["label"][None, :], len(vecs), axis=0))
        Yt.append(np.repeat(r["target"][None, :], len(vecs), axis=0))
        lum.append(l)
        pix.append(px)
        if dev == "cuda":
            torch.cuda.empty_cache()
        if (gi + 1) % 9 == 0 or gi == 0:
            log(f"room {gi + 1}/{len(bank)} {r['name']} embedded")
    return (np.concatenate(X), np.concatenate(Y), np.concatenate(Yt),
            np.concatenate(groups), np.concatenate(lum), np.concatenate(pix))


# --------------------------------------------------------------------- #
# Split audit (C0) — the split must be well-defined on this grid         #
# --------------------------------------------------------------------- #
def audit_split(values: np.ndarray, tr: np.ndarray, te: np.ndarray) -> dict:
    levels = sorted({round(float(t), 6) for t in values})
    return {
        "n_train_rooms": int(tr.sum()), "n_test_rooms": int(te.sum()),
        "levels": levels,
        "train_levels": [lv for lv in levels
                         if any(abs(float(t) - lv) < 1e-9 for t in values[tr])],
        "test_levels": [lv for lv in levels
                        if any(abs(float(t) - lv) < 1e-9 for t in values[te])],
    }


def ratio_entry(r2x: float, r2i: float) -> dict:
    """The gated quantity. A dial whose range-interpolation baseline is dead
    in the ratio currency (R2i <= RATIO_DEN_FLOOR) gets ratio=None and is
    excluded from both counts (G1 guarantees >= 2 living baselines first)."""
    ok = r2i > RATIO_DEN_FLOOR
    return {"r2i_range": round(float(r2i), 4),
            "r2x_range": round(float(r2x), 4),
            "ratio": round(r2x / r2i, 4) if ok else None,
            "denominator_valid": bool(ok)}


# --------------------------------------------------------------------- #
# CPU-only mode (no model, no GPU): bank + splits + harness self-test    #
# --------------------------------------------------------------------- #
def cpu_only() -> dict:
    st = harness_selftest()
    bank = build_bank(1)          # e12's 27-cell grid, elephant-bank labels
    targets = np.stack([r["target"] for r in bank])
    labels = np.stack([r["label"] for r in bank])
    splits = {}
    for i, d in enumerate(DIAL_NAMES):
        tr, te, lo, hi = split_1d(targets, i)
        splits[d] = {
            "target_range": [lo, hi],
            **audit_split(targets[:, i], tr, te),
            "label_range_train": [round(float(labels[tr, i].min()), 4),
                                  round(float(labels[tr, i].max()), 4)],
            "label_range_test": [round(float(labels[te, i].min()), 4),
                                 round(float(labels[te, i].max()), 4)],
            "label_std_test": round(float(labels[te, i].std()), 6),
        }
    tr2, te2 = split_corner(targets)
    splits["corner_mood_x_presence"] = audit_split(targets[:, 0], tr2, te2)
    out = {
        "experiment": "X6 dial-range extrapolation",
        "mode": "cpu-only (no model, no GPU)",
        "seed": SEED, "tau": TAU,
        "rooms": len(bank), "stills_per_room": N_STILLS,
        "harness_selftest": st,
        "staging_fidelity_spearman_target_vs_label": {
            d: round(spearman(targets[:, i], labels[:, i]), 4)
            for i, d in enumerate(DIAL_NAMES)},
        "split_audit": splits,
        "sample_lavfi_source": stage_source(
            *[float(x) for x in bank[0]["target"]], bank[0]["seed"]),
        "note": ("No verdict in CPU-only mode. The audit must show: 18/9 "
                 "rooms per 1D dial split with the high level wholly on the "
                 "test side, 12/15 for the corner split, and a passing "
                 "harness self-test. label_std_test ~ 0 on a split dial is "
                 "WHY the gated currency is fixed-denominator (see the "
                 "module docstring's amendment)."),
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
        out = {"experiment": "X6 dial-range extrapolation",
               "verdict": "ABORTED", "reason": reason,
               "guard_preflight": guard_info}
        print(json.dumps(out, indent=2))
        return out

    # G0d — cheapest gate first (model-free).
    selftest = harness_selftest()
    log(f"harness self-test: {selftest}")

    base = {"experiment": "X6 dial-range extrapolation", "seed": SEED,
            "tau": TAU, "keep_ratio": KEEP_RATIO, "kill_ratio": KILL_RATIO,
            "k_primary": K_PRIMARY, "dial_names": DIAL_NAMES,
            "guard_preflight": guard_info,
            "harness_selftest": selftest,
            "bank_provenance": ("e13.build_bank(1) = e12.build_dial_grid + "
                                "e12.stage_transcript + e12.read_room "
                                "(E12's 27-cell grid, elephant-bank labels)"),
            "carrier": ("e12.stage_source (E12's linear staging, the arm "
                        "that KEPT)"),
            "split_is_on": "staged target triple, tau=0.7 in raw dial units",
            "interpolation_reference": ("e12 standard LORO ridge k=64, all 27 "
                                        "rooms (E12 currency, feeds G1); the "
                                        "gated ratio uses LORO within train "
                                        "in the fixed-denominator currency"),
            "extrapolation_fit": ("ridge on train rooms only, lambda by inner "
                                  "leave-one-room CV within train, error on "
                                  "test"),
            "scoring_currency": ("fixed denominator = train-side label "
                                 "variance of the same split (amendment in "
                                 "the module docstring; test-variance R2 is "
                                 "undefined on a one-level test side)"),
        }

    if not selftest["pass"]:
        out = dict(base)
        out.update({"verdict": "INVALID_HARNESS",
                    "reason": "G0d: the imported probe failed the synthetic "
                              "self-test"})
        print(json.dumps(out, indent=2))
        return out

    bank = build_bank(1)
    if len(bank) < 8:
        out = dict(base)
        out.update({"verdict": "ABORTED",
                    "reason": f"only {len(bank)} rooms — grouped CV "
                              "meaningless"})
        print(json.dumps(out, indent=2))
        return out
    targets = np.stack([r["target"] for r in bank])
    labels = np.stack([r["label"] for r in bank])

    # G0a — staging fidelity (E12's validity gate; the bank is deterministic,
    # but re-verify in this run rather than assume).
    fid = {d: round(spearman(targets[:, i], labels[:, i]), 4)
           for i, d in enumerate(DIAL_NAMES)}
    fid_pass = bool(sum(1 for d in DIAL_NAMES if fid[d] >= 0.50) >= 2)
    if not fid_pass:
        out = dict(base)
        out.update({"verdict": "INVALID_STAGING",
                    "staging_fidelity_spearman_target_vs_label": fid,
                    "reason": "G0a: staged scripts did not move >= 2/3 dials"})
        print(json.dumps(out, indent=2))
        return out

    # C0 — split audit BEFORE any GPU spend: the split must be well-defined.
    audits = {}
    for i, d in enumerate(DIAL_NAMES):
        tr, te, lo, hi = split_1d(targets, i)
        a = audit_split(targets[:, i], tr, te)
        if not (a["n_train_rooms"] >= 8 and a["n_test_rooms"] >= 4):
            out = dict(base)
            out.update({"verdict": "ABORTED",
                        "reason": f"split audit failed for {d}: {a}"})
            print(json.dumps(out, indent=2))
            return out
        audits[d] = a
    tr2, te2 = split_corner(targets)
    audits["corner_mood_x_presence"] = audit_split(targets[:, 0], tr2, te2)

    import torch
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    log(f"loading I-JEPA ({dev})...")
    try:
        model_used, model, processor, load_notes = load_encoder(dev)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED",
                    "reason": f"model load failed: {e}"})
        print(json.dumps(out, indent=2))
        return out
    log(f"using {model_used}")

    try:
        X, Y, Yt, groups, lum, pix = collect(bank, model, processor, dev,
                                             torch)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "reason": f"frame/embed failed: {e}"})
        print(json.dumps(out, indent=2))
        return out

    # E12's label-free PCA basis on ALL stills (so interpolation and
    # extrapolation differ ONLY by the split; C2 books the train-only basis).
    basis, evr = pca_basis(X, K_PRIMARY)
    z = X @ basis[:, :K_PRIMARY]

    # Interpolation reference: E12's standard LORO (E12's own currency; G1).
    pred_interp, lam_med = loro_predict(z, Y, groups)
    r2_interp = r2_columns(Y, pred_interp)

    # 1D dial-range splits per dial + booked controls.
    extrap = {}
    for i, d in enumerate(DIAL_NAMES):
        tr, te, lo, hi = split_1d(targets, i)
        e = range_eval(z, Y, groups, tr, te)
        room_r2 = room_level_extrap(z, Y, groups, tr, te)
        entry = {
            "threshold": TAU, "target_range": [lo, hi],
            "train_rooms": int(tr.sum()), "test_rooms": int(te.sum()),
            "test_levels": audits[d]["test_levels"],
            "label_range_test": [round(float(Y[np.asarray(te)[groups], i].min()), 4),
                                 round(float(Y[np.asarray(te)[groups], i].max()), 4)],
            "split_dial": d,
            **e,
            **room_r2,
            **basis_only_train(X, Y, groups, tr, te),
            **ratio_entry(e["r2x_range"][i], e["r2i_range"][i]),
        }
        extrap[d] = entry
        log(f"{d}: interp_range {e['r2i_range'][i]:+.4f} -> extrap "
            f"{e['r2x_range'][i]:+.4f} "
            f"(ratio {entry['ratio']}, "
            f"{entry['train_rooms']}/{entry['test_rooms']} rooms)")

    # The pre-registered G2 gate on the fixed-denominator ratios.
    valid = [d for d in DIAL_NAMES if extrap[d]["denominator_valid"]]
    n_keep = sum(1 for d in valid
                 if extrap[d]["ratio"] is not None
                 and extrap[d]["ratio"] >= KEEP_RATIO)
    n_kill = sum(1 for d in valid
                 if extrap[d]["ratio"] is not None
                 and extrap[d]["ratio"] < KILL_RATIO)
    n_interp_ok = int(sum(1 for i, d in enumerate(DIAL_NAMES)
                          if float(r2_interp[i]) >= R2_FLOOR))

    if n_interp_ok < VALID_DIALS_FLOOR:
        verdict = "INVALID_BASELINE"
        vreason = (f"G1: interpolation LORO R2(k64) >= {R2_FLOOR} on only "
                   f"{n_interp_ok}/3 dials — E12's KEEP did not replicate in "
                   "this run; the ratio gate's denominator is dead")
    elif n_kill >= 2:
        verdict = "KILL"
        vreason = (f"G2: extrapolation < {KILL_RATIO}x interpolation on "
                   f"{n_kill} dials — the read is range-local (LORO tested "
                   "rooms, not dial range)")
    elif n_keep >= 2:
        verdict = "KEEP"
        vreason = (f"G2: extrapolation >= {KEEP_RATIO}x interpolation on "
                   f"{n_keep} dials — the dial direction extends beyond the "
                   "trained range")
    else:
        verdict = "INCONCLUSIVE"
        vreason = (f"G2: {n_keep} dials >= {KEEP_RATIO}x, {n_kill} dials < "
                   f"{KILL_RATIO}x — mixed")

    # Booked C5: the targets arm (staged triple as Y, identical machinery).
    targets_arm = {}
    for i, d in enumerate(DIAL_NAMES):
        tr, te, _, _ = split_1d(targets, i)
        e_t = range_eval(z, Yt, groups, tr, te)
        targets_arm[d] = ratio_entry(e_t["r2x_range"][i], e_t["r2i_range"][i])

    # Booked: 2D corner split (one fit, all three columns; the corner test
    # side DOES vary in mood/presence, so both currencies are reported).
    e_corner = range_eval(z, Y, groups, tr2, te2)
    corner = {d: {"r2x_fixed_den": e_corner["r2x_range"][i],
                  "r2_testvar": e_corner["r2_testvar_evidence"][i],
                  "rmse_test": e_corner["rmse_test"][i],
                  **ratio_entry(e_corner["r2x_range"][i],
                                e_corner["r2i_range"][i])}
              for i, d in enumerate(DIAL_NAMES)}
    corner_summary = {
        "train_rooms": int(tr2.sum()), "test_rooms": int(te2.sum()),
        "train_levels_m": audits["corner_mood_x_presence"]["train_levels"],
        "test_levels_m": audits["corner_mood_x_presence"]["test_levels"],
        "extrapolated_dims": ["mood", "presence"],
        "per_dial": corner,
        "r2i_range_fixed_den": e_corner["r2i_range"],
        "note": ("booked, not gated: mood and presence are the extrapolated "
                 "corner dims; volume stays interpolated (train covers all "
                 "v levels). ratio uses the fixed-denominator currency."),
    }

    # Booked C6: mood's other end (train {0,+0.8}, test {-0.8}).
    mood_lo_tr = targets[:, 0] >= -1e-9
    e_mlo = range_eval(z, Y, groups, mood_lo_tr, ~mood_lo_tr)
    mood_low = {"train_rooms": int(mood_lo_tr.sum()),
                "test_rooms": int((~mood_lo_tr).sum()),
                **ratio_entry(e_mlo["r2x_range"][0], e_mlo["r2i_range"][0]),
                "rmse_test_mood": e_mlo["rmse_test"][0]}

    # Booked C1: raw-pixel probe through the same splits.
    pred_px_interp, _ = loro_predict(pix, Y, groups)
    r2_px_interp = r2_columns(Y, pred_px_interp)
    pix_ctrl = {}
    for i, d in enumerate(DIAL_NAMES):
        tr, te, _, _ = split_1d(targets, i)
        e_px = range_eval(pix, Y, groups, tr, te)
        pix_ctrl[d] = {
            "r2_interp_all27_testvar": round(float(r2_px_interp[i]), 4),
            **ratio_entry(e_px["r2x_range"][i], e_px["r2i_range"][i]),
        }

    out = dict(base)
    out.update({
        "model": model_used, "device": dev, "load_notes": load_notes,
        "rooms": len(bank), "stills_per_room": N_STILLS,
        "cells": int(X.shape[0]), "emb_dim": int(X.shape[1]),
        "pca_evr_k64": round(float(evr[:K_PRIMARY].sum()), 4),
        "staging_fidelity_spearman_target_vs_label": fid,
        "split_audit": audits,
        "lambda_median_interp_all27": round(float(lam_med), 6),
        "interpolation_loro_r2_k64_e12currency": {
            d: round(float(r2_interp[i]), 4)
            for i, d in enumerate(DIAL_NAMES)},
        "extrapolation_1d": extrap,
        "ratios_extrap_over_interp": {
            d: {"ratio": extrap[d]["ratio"],
                "r2i_range": extrap[d]["r2i_range"],
                "r2x_range": extrap[d]["r2x_range"]}
            for d in DIAL_NAMES},
        "booked_targets_arm_c5": targets_arm,
        "corner_2d": corner_summary,
        "booked_mood_low_holdout_c6": mood_low,
        "controls": {
            "raw_pixel_144d_c1": pix_ctrl,
            "pixel_note": ("E12's carrier is affine dial->pixels, so pixels "
                           "should extrapolate; if the embedding collapses "
                           "where pixels hold, the range-locality lives in "
                           "the encoder nonlinearity, not the probe"),
        },
        "gates": {
            "g0d_harness_selftest": selftest["pass"],
            "g0a_staging_fidelity": {"pass": fid_pass, "measured": fid},
            "g1_baseline": {
                "floor": R2_FLOOR, "n_dials_ok": n_interp_ok,
                "measured": {d: round(float(r2_interp[i]), 4)
                             for i, d in enumerate(DIAL_NAMES)},
                "pass": bool(n_interp_ok >= VALID_DIALS_FLOOR)},
            "g2_ratio_gate": {
                "kill_below": KILL_RATIO, "keep_above": KEEP_RATIO,
                "ratio_den_floor": RATIO_DEN_FLOOR,
                "n_keep": n_keep, "n_kill": n_kill, "valid_dials": valid},
        },
        "verdict": verdict,
        "verdict_reason": vreason,
        "data_needed": [
            "ffmpeg ~/.local/bin/ffmpeg (lavfi chain, E12's)",
            "facebook/ijepa_vith16_1k fp16 on the RTX 4050 (E9 loader, "
            "imported)",
            "elephant package importable (dial bank = labels)",
            f"{len(bank)} rooms x {N_STILLS} stills = {len(bank) * N_STILLS} "
            "forwards — ~3-5 min GPU",
        ],
        "note": (
            "X6 asks whether E12-family LORO KEEPs survive DIAL-RANGE "
            "holdout. Same bank, same carrier, same ridge probe as E12; the "
            "ONLY change is the split: per dial, train t<=0.7, test t>0.7 "
            "(room-disjoint by construction; lambda picked inside train). "
            "Because a 3-level grid makes the held-out side a single "
            "CONSTANT level, the gated currency is fixed-denominator R2 "
            "(both sides over the train-side label variance of the same "
            "split; interpolation side = LORO within train) — the "
            "degenerate test-variance numbers are reported per split as the "
            "amendment's evidence. KILL = ratio < 0.6x on >= 2/3 dials (the "
            "read memorized the staging manifold's local geometry; every "
            "LORO KEEP in the family is range-bound). KEEP = >= 0.8x on "
            ">= 2/3 (the dial direction extends beyond the trained range). "
            "INVALID_BASELINE protects the denominator (E12's KEEP must "
            "replicate here first). C5 (targets arm) separates embedding "
            "failure from label saturation (mood labels pin at 1.0)."),
    })
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
