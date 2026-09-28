#!/usr/bin/env python3
"""E28 — per-dial HYBRID reader: is the reader-vs-embedding answer PER-DIAL?

THE QUESTION (opened by E13b's INCONCLUSIVE)
  E13 (experiments/e13_nonlinear_dial_reader.py) put E12's KEEP on a nonlinear
  carrier: one frozen I-JEPA, one label bank (the elephant's own DialBank), the
  same 27-room grid, three carriers — L = E12's affine staging (positive
  control), N1 = a frozen monotone-but-bent sigmoid warp (mild rung), N2 =
  roomgen's frozen nonlinear mixture (PRIMARY). On N2 a LINEAR ridge read
  mood 0.537, volume -0.100, presence 0.270 (k=64 still-LORO R2) => the read
  survived for mood and died for volume/presence.
  E13b held everything fixed and swapped ONE thing — the reader — replacing the
  ridge with a small sklearn-LBFGS MLP (hidden 16, alpha 0.1) over the SAME
  PCA spaces. Its result (results/e13b_nonlinear_reader.json, 2026-09-28) is the
  premise of this experiment:

      dial      ridge k64   MLP k64    MLP-room  verdict
      mood        0.5372     0.3671      0.3837  ridge OPTIMAL (linear read)
      volume     -0.0998     0.2064      0.2295  dies in the ridge, lives in the MLP
      presence    0.2700     0.3382      0.3555  above the floor only under the MLP

  So on the same carrier, the same embeddings, the same folds: MOOD is a
  linear/luminance dial (the nonlinear reader HURTS it by 0.17) while
  VOLUME and PRESENCE are higher-order dials (the nonlinear reader buys
  +0.31 / +0.07 on still-LORO R2). No single reader architecture is right for
  all three dials — a per-dial reader is the hypothesis E13b left standing.

WHAT THIS EXPERIMENT BUILDS
  The HYBRID reader: a FIXED, pre-registered, per-dial choice of reader —
      mood     -> ridge   (linear; E13's/E12's numpy probe, imported verbatim)
      volume   -> MLP     (sklearn LBFGS, hidden 16, alpha 0.1; E13b's,
                           imported verbatim)
      presence -> MLP
  run on the SAME three carriers (L / N1 / N2) and the SAME 27-room bank as
  E13b, through E13's carriers/bank/collector and E13b's readers BY IMPORT.
  Nothing about the carriers, the bank, the encoder, the folds, the PCA spaces,
  the nulls or the two readers is forked: E28 adds (i) the per-dial SELECTOR,
  (ii) the hybrid report that stitches the two imported readers' per-dial
  numbers into one still-LORO R2(k=64) / room R2 / E12-gate read, and (iii) a
  test-blind NESTED selector as a control (below).

  The hybrid is therefore NOT "pick the best reader per dial by measured
  score" — that would be selection-on-test and would make the dominance claim
  vacuous. The assignment is FIXED before running (the table above), and mood
  is read by the ridge and volume/presence by the MLP in every fold.

PRE-REGISTERED GATES (fixed before running; this file IS the registration)
  Validity gates (never a KEEP, never a KILL):
    G0d  ridge harness self-test : E13's, imported (synthetic linear signal ->
         LORO R2 >= 0.90, shuffled < 0.10). Else INVALID_HARNESS.
    G0d' MLP harness self-test   : E13b's, imported (linear read >= 0.90,
         shuffled < 0.10, nonlinear capability >= 0.5 on >= 2/3 targets the
         ridge cannot read, null smoke < 0.20). Else INVALID_HARNESS.
    G0d'' selector self-test     : E28's own, CPU, carrier-free, model-free, in
         three parts. (a) CAPABILITY: on a synthetic 3-dial embedding where two
         dials are LINEAR and one is NONLINEAR, the NESTED selector must reach
         >= ridge+0.05 on the nonlinear dial while staying within 0.05 of the
         ridge on the two linear dials. (b) LOGIC: the selection rule itself
         (higher inner-LORO R2 wins, ties to the ridge) must hold on all three
         hand-made cases AND on every fold of every dial as recorded. (c) NON-
         DEGENERACY: both reader branches must actually be exercised, so a
         selector that always returns one reader cannot pass vacuously.
         Else INVALID_HARNESS.
    G0b  sensitivity             : E13's (Arm L luminance LORO ridge
         R2(k=64) >= 0.90). Else INVALID_HARNESS.
    Gr   MLP reads the readable arm: E13b's (MLP k=64 >= 0.30 on >= 2/3 dials
         on Arm L). Else INVALID_HARNESS.
    Gc   MLP genuinely nonlinear : E13b's reader-curvature certificate on the
         N2 MLP branch (>= 0.02 on >= 2/3 dials). Else INVALID_HARNESS.
         DEVIATION, pre-registered: E13b labelled a Gc failure INCONCLUSIVE
         ("the MLP cannot arbitrate"); for E28 the MLP branch is a FIXED part
         of the architecture being tested, so a collapsed (affine) MLP branch
         means the hybrid is not the hybrid and the run is invalid — booked
         here so the difference is deliberate, not drift.
    G0a  staging fidelity        : E13's (>= 2/3 dials Spearman(target,label)
         >= 0.5). Else INVALID_STAGING.
    G0c  carrier certificate     : E13's, recomputed live (N2 must be
         nonaffine + live; L must measure curvature 0). Else INVALID_STAGING.
    INVALID_CONTROL              : Arm L's RIDGE ladder != KEEP (E12's KEEP did
         not replicate) — never reported as a KILL.
    ABORTED                      : guard preflight, model load, no frames,
         < 8 rooms.

  THE CLAIM (all three clauses on the PRIMARY arm N2; S = hybrid, R = pure
  ridge, M = pure MLP, all still-LORO R2(k=64) recomputed live in this run):
    KEEP        : the hybrid BEATS pure ridge on both higher-order dials AND
                  matches-or-beats pure ridge on mood
                    vol_pres_beaten := S_volume > R_volume + tol
                                       AND S_presence > R_presence + tol
                    mood_matched    := S_mood >= R_mood - tol
                  AND the hybrid strictly dominates BOTH pure readers on
                  >= 2/3 dials (n_dom >= 2, where dom_d := S_d >=
                  max(R_d, M_d) - tol)
                  AND mean_d S_d > mean_d hybrid_null95_d (the hybrid clears
                  its own permutation null)
                  ==> a per-dial reader is the right architecture: the mood
                      read stays linear, the higher-order dials want the
                      nonlinear reader, and the hybrid is never worse than the
                      reader it did not pick, on >= 2 of 3 dials.
    KILL        : the hybrid MATCHES pure ridge — it never strictly exceeds
                  the ridge on ANY dial (S_d <= R_d + tol for all d), i.e. the
                  nonlinear reader adds nothing even for the higher-order
                  dials, AND the hybrid's E12-gate pass set equals the ridge's
                  ==> the per-dial split was a mirage; E13b's per-dial reading
                      was fold/noise-level, not architectural.
    INCONCLUSIVE: any partial (exactly one of volume/presence beaten; or both
                  beaten but n_dom < 2; or mood_matched fails; or the hybrid
                  does not clear its null) — never overclaim from a partial.
                  ALSO: if the premise fails (no dial where the ridge beats the
                  MLP, or no dial where the MLP beats the ridge, on N2 — i.e.
                  one pure reader dominates all three dials in this run), the
                  per-dial split is not at stake and the run is booked
                  INCONCLUSIVE with that reason, E13b's convention.

CONTROLS / BOOKED (never gated)
  C1 the two pure readers, per arm, per dial: E13's ridge arm_report verbatim
     (still/room R2 k16/k64/k256, Spearman, 200-perm null95 + p, tertile acc,
     raw-pixel and luminance controls, carrier certificate) and E13b's MLP
     report verbatim (still/room R2 k16/k64, null95 + p, reader curvature).
  C2 dominance table, per arm: S vs R vs M per dial, hybrid-minus-ridge,
     hybrid-minus-MLP, n_dom, and which reader the fixed assignment picked. On
     Arm L (E12's affine carrier) the pure ridge is expected to WIN — the MLP
     was measured WORSE there — so the booked question "is the per-dial split
     carrier-conditional?" is answered by n_dom per arm.
  C3 NESTED HYBRID (the test-blind control; DOES NOT GATE). For each held-out
     room, the reader is chosen PER DIAL using ONLY the training rooms: inner
     LORO R2 of the ridge vs inner LORO R2 of the MLP over the 26 training
     rooms, higher wins, then the held-out room is read by that reader's
     outer-fold prediction. This is the honest version of "per-dial reader" —
     no peeking at the test room, no fixed assignment, no post-hoc selection —
     and its R2(k=64) per dial on N2 is the strongest available evidence about
     whether a per-dial split is real. It is BOOKED, not gated, because the
     pre-registered claim is the fixed-assignment hybrid; the nested run is
     reported so a reader can see whether the fixed assignment was the right
     one. Cost: ~26 inner MLP fits per outer fold per arm, so it runs on the
     primary arm by default (`E28_NESTED=0|primary|all`).
  C4 room-level, TWO conventions. E12's gate uses a room-mean-FEATURE ridge
     re-fit; E13b pre-registered averaged held-out still PREDICTIONS for the
     MLP (26 training rows cannot be cheaply re-fit by an MLP). The hybrid
     therefore gates on the PUBLISHED convention of the branch it picked
     (ridge: room-mean-feature; MLP: averaged predictions) and BOOKS the
     common convention (averaged predictions for both readers, computed here
     for the ridge from the imported LORO probe) so the heterogeneity is
     visible instead of hidden.
  C5 the ridge recompute check: E28's own imported-ridge predictions must
     reproduce E13's arm_report r2_still_loro(k=64) to 1e-6 (same basis, same
     folds, same lambda path) — if not, the hybrid is stitching numbers from
     two different probes and the run is not comparable.
  C6 extra dials (earnestness/cynicism/joke_landing/panic) booked as in E12.

HONESTY / CAVEATS BOOKED WITH THE RESULT
  - IN-SAMPLE ASSIGNMENT. The per-dial assignment (mood->ridge,
    volume/presence->MLP) was derived from E13b's measured result on the SAME
    27-room bank, the SAME carriers and the SAME encoder. The fixed-assignment
    hybrid is therefore a CONSOLIDATION of E13b's finding, not a fresh
    falsification of it: a KEEP here says "the per-dial architecture E13b's
    numbers pointed at does what it was built to do, and it is never worse
    than the reader it skipped on >= 2/3 dials", NOT "a per-dial reader was
    discovered on fresh data". The nested selector (C3) is the test-blind
    part of this file and is booked non-gating for exactly that reason.
  - The comparison metric is still-LORO R2(k=64) — the single metric both
    readers are pre-registered on. A dial could in principle be beaten by the
    MLP on room-level R2 while losing at k=64; the dominance table books all
    of them so no dial's story depends on the choice of column.
  - Carriers are staged and frozen (E13's seeds 2718/2719); one random
    nonlinear draw, one reader family, one encoder. E28 is a reader-architecture
    experiment on a fixed world, not a claim about camera feeds.
  - The MLP trains on the encoder's device (E13b's booked convention change);
    the ridge side stays E13's numpy/CPU probe verbatim.
  - JOINT-LAMBDA COUPLING (measured at write time, booked because it shapes
    every ridge number in this file): E12's pick_lambda minimises the SSE over
    ALL THREE dial columns jointly, so a dial the ridge cannot read at all
    (volume on N2) pushes the per-fold lambda up and costs the ridge on the
    dials it CAN read. On the selector self-test's synthetic the effect is
    stark: fixed lambda 1e-3 reads the two linear dials at 1.00/1.00, the
    probe's own per-fold choice lands at lambda ~1.0 and reads them at
    0.67/0.48. The mood branch of the hybrid is measured under that same rule —
    which makes "the ridge is optimal for mood" a CONSERVATIVE claim, and means
    the hybrid's mood number is not the best a linear read of mood could do.

WIRING (deliberately absent)
  NOT in QUEUE.md and NOT in runner.py's EXP_MOD: manual fire only, after GPU
  review —
      ~/venvs/elephant-gpu/bin/python -m experiments.e28_hybrid_reader
  COST, measured not guessed: E13b (the same workload minus the nested
  control) took 1700 s wall (mlp_seconds 1577, ~972 encoder forwards + the
  ridge sweeps). E28 = E13b + the C3 nested selector on N2 (~90 s) ~= 30 min.
  guard.py's Guard default wall is 1800 s, so fire this manually with a raised
  outer timeout (or E28_NESTED=0) — it is not a runner job by design.
  --cpu-only runs bank/carriers/certificates/self-tests (including the selector
  self-test) with no model and no GPU, and prints no verdict.

Verdict printed as ONE JSON object on stdout (progress on stderr).
Deterministic (seeds 2718 carriers / 2731 readers / 2741 selector).
CPU-only probing; GPU only for the encoder forwards.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# BLAS thread cap — same reason as E12/E13/E13b: thousands of tiny ridge solves
# and the batched fold-nets; must be set BEFORE numpy loads (this module imports
# e13b, which imports e13, which imports e12, which imports numpy).
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np  # noqa: E402

try:  # belt-and-braces, as E12/E13/E13b
    from threadpoolctl import threadpool_limits  # noqa: E402
    _BLAS_LIMIT = threadpool_limits(limits=4)
    _BLAS_LIMIT.__enter__()
except Exception:
    _BLAS_LIMIT = None

SEED = 2718        # E13's carrier/bank/embedding seed (replicate E13/E13b)
SEED_B = 2731      # E13b's reader seed
SEED_H = 2741      # E28's own draws (nested selector, its self-test)

LAB = Path(__file__).resolve().parents[1]
ELEPHANT = Path.home() / "projects" / "elephant"
for _p in (str(LAB), str(LAB / "experiments"), str(ELEPHANT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from e9_ijepa_stills import (                                 # noqa: E402
    N_STILLS, load_encoder, preflight_guard,
)

# --------------------------------------------------------------------- #
# E13 is imported VERBATIM — carriers, bank, certificates, collector,   #
# ridge arm_report. E13b is imported VERBATIM — the LBFGS MLP reader.   #
# E28 adds exactly one thing: the per-dial SELECTOR + hybrid report.    #
# --------------------------------------------------------------------- #
from e13_nonlinear_dial_reader import (                       # noqa: E402
    ARMS, N_REPLICATES, PRIMARY_ARM, arm_report, build_arm_knobs, build_bank,
    carrier_certificate, collect_arm, harness_selftest, knob_ranges,
    mirror_check,
)
from e13b_nonlinear_reader import (                           # noqa: E402
    MLP_ALPHA, MLP_CURV_FLOOR, MLP_HIDDEN, MLP_MAX_ITER, MLP_SOLVER,
    NULL_PERMS, mlp_arm_report, mlp_loro, mlp_selftest,
)
from e12_room_dial_reader import (                            # noqa: E402
    ARM_A_ACC_FLOOR, DIAL_NAMES, EXTRA_DIALS, FIDELITY_FLOOR, K_PRIMARY,
    K_STRICT, K_WIDE, R2_FLOOR, R2_ROOM_FLOOR, R2_TOP_PC_FRACTION,
    SENSITIVITY_FLOOR, loro_predict, pca_basis, r2_columns, spearman,
)

# --------------------------------------------------------------------- #
# Pre-registered constants                                              #
# --------------------------------------------------------------------- #
RIDGE, MLP = "ridge", "mlp"
# THE ASSIGNMENT. Fixed before running, from E13b's measured per-dial result
# (in-sample — see the docstring's honesty booking). mood is a linear/luminance
# dial on every carrier measured so far; volume and presence are the dials the
# nonlinear reader buys.
ASSIGNMENT = {"mood": RIDGE, "volume": MLP, "presence": MLP}
TOL = 1e-9          # "matches" tolerance on a metric computed in float64
NESTED_MODE = os.environ.get("E28_NESTED", "primary").strip().lower()
NESTED_ARMS = {"0": (), "off": (), "none": (),
               "primary": (PRIMARY_ARM,), "n2": (PRIMARY_ARM,),
               "1": tuple(ARMS), "all": tuple(ARMS)}.get(NESTED_MODE, (PRIMARY_ARM,))
SELFTEST_ROOMS, SELFTEST_STILLS, SELFTEST_DIM = 12, 12, 24


def log(msg: str) -> None:
    """Progress to stderr; stdout is reserved for the JSON verdict."""
    print(f"[e28] {msg}", file=sys.stderr, flush=True)


def _r(x) -> float:
    return round(float(x), 4)


def _mean(xs) -> float:
    xs = [float(x) for x in xs]
    return float(np.mean(xs)) if xs else float("nan")


# --------------------------------------------------------------------- #
# The selector: per-dial choice of reader                               #
# --------------------------------------------------------------------- #
def select_reader(dial: str) -> str:
    """The pre-registered per-dial reader. The whole experiment is this line."""
    return ASSIGNMENT[dial]


def _pick(inner_ridge: float, inner_mlp: float) -> str:
    """The nested selector's rule, isolated so it can be unit-checked: the
    reader with the higher inner (train-rooms-only) LORO R2 for that dial wins;
    ties go to the ridge (the linear default)."""
    return RIDGE if float(inner_ridge) >= float(inner_mlp) else MLP


def _avpred_room_r2(pred_still: np.ndarray, Y: np.ndarray,
                    groups: np.ndarray) -> np.ndarray:
    """Room-level R2 under E13b's MLP convention (averaged held-out still
    PREDICTIONS per room) — applied to the RIDGE side here so the hybrid's two
    branches can be compared under one convention (C4), and reused for the
    nested control's room-level read."""
    ids = np.unique(groups)
    Yr = np.stack([Y[groups == g][0] for g in ids])
    Pr = np.stack([pred_still[groups == g].mean(0) for g in ids])
    return r2_columns(Yr, Pr)


def hybrid_report(arm: str, ridge: dict, mlp: dict, ridge_room_avg: dict,
                  room_sep_acc: float) -> dict:
    """The hybrid read: per dial, the pre-registered reader's numbers from the
    two imported reports, stitched into ONE still-LORO R2(k=64) / room R2 /
    E12-gate read, plus the dominance table that the claim is stated in.

    Nothing is recomputed here (both readers' numbers are their own published
    ones, from this same run, same embeddings, same folds) and no reader is
    chosen by looking at a score: the assignment is the import-time constant.
    """
    per, passes = {}, {}
    for i, d in enumerate(DIAL_NAMES):
        src = select_reader(d)
        rr = float(ridge["r2_still_loro"]["64"][d])
        mm = float(mlp["r2_still_loro"]["64"][d])
        if src == RIDGE:
            s64 = rr
            s16 = float(ridge["r2_still_loro"]["16"][d])
            room_pub = float(ridge["r2_room_loro"]["64"][d])
            room_avg = float(ridge_room_avg[d])
            null95 = float(ridge["perm_null95_k64"][d])
            perm_p = float(ridge["perm_p_k64"][d])
            sp = float(ridge["spearman_loro_k64"][d])
            tert = float(ridge["tertile_acc_k64"][d])
            curv = None
        else:
            s64 = mm
            s16 = float(mlp["r2_still_loro"]["16"][d])
            room_pub = float(mlp["r2_room_loro_avg_pred"]["64"][d])
            room_avg = room_pub
            null95 = float(mlp["perm_null95_k64"][d])
            perm_p = float(mlp["perm_p_k64"][d])
            sp = float(mlp["spearman_loro_k64"][d])
            tert = None      # E13b's MLP report has no tertile read (booked gap)
            curv = mlp["mlp_curvature_k64"].get(d)
        passes[d] = bool(s64 >= R2_FLOOR
                         and room_pub >= R2_ROOM_FLOOR
                         and s16 >= R2_TOP_PC_FRACTION * max(s64, 1e-9)
                         and s64 > null95)
        per[d] = {
            "reader": src,
            "r2_still_loro_k64": _r(s64),
            "r2_still_loro_k16": _r(s16),
            "k16_retains_frac_of_k64": _r(s16 / max(s64, 1e-9)),
            "r2_room_loro_published": _r(room_pub),
            "r2_room_loro_avg_pred": _r(room_avg),
            "perm_null95_k64": _r(null95),
            "perm_p_k64": _r(perm_p),
            "spearman_loro_k64": _r(sp),
            "tertile_acc_k64": None if tert is None else _r(tert),
            "mlp_curvature": None if curv is None else _r(curv),
            "pass": passes[d],
            "pure_ridge_k64": _r(rr),
            "pure_mlp_k64": _r(mm),
            "hybrid_minus_ridge": _r(s64 - rr),
            "hybrid_minus_mlp": _r(s64 - mm),
            "hybrid_gt_ridge": bool(s64 > rr + TOL),
            "hybrid_ge_ridge": bool(s64 >= rr - TOL),
            "hybrid_gt_mlp": bool(s64 > mm + TOL),
            "dominates_both": bool(s64 >= max(rr, mm) - TOL),
            "assigned_is_better": bool((rr >= mm - TOL) if src == RIDGE
                                       else (mm >= rr - TOL)),
        }

    n_pass = int(sum(1 for d in DIAL_NAMES if passes[d]))
    mean_s = _mean([per[d]["r2_still_loro_k64"] for d in DIAL_NAMES])
    mean_null = _mean([per[d]["perm_null95_k64"] for d in DIAL_NAMES])
    room_ok = bool(room_sep_acc >= ARM_A_ACC_FLOOR)
    room_ok_avg = bool(min(per[d]["r2_room_loro_avg_pred"]
                           for d in DIAL_NAMES) >= R2_ROOM_FLOOR)
    if n_pass >= 2 and room_ok:
        ladder = "KEEP"
    elif n_pass >= 1 or mean_s > mean_null:
        ladder = "INCONCLUSIVE"
    else:
        ladder = "KILL"

    n_dom = int(sum(1 for d in DIAL_NAMES if per[d]["dominates_both"]))
    never_exceeds_ridge = bool(all(not per[d]["hybrid_gt_ridge"] for d in DIAL_NAMES))
    ridge_pass = ridge["gate"]["dial_pass"]
    return {
        "title": (f"per-dial hybrid (mood->{select_reader('mood')}, "
                  f"volume->{select_reader('volume')}, "
                  f"presence->{select_reader('presence')})"),
        "per_dial": per,
        "gate": {
            "dial_pass": passes,
            "n_pass": n_pass,
            "mean_r2_k64": _r(mean_s),
            "mean_null95_k64": _r(mean_null),
            "clears_null": bool(mean_s > mean_null),
            "room_sep_ok": room_ok,
            "room_sep_ok_avg_pred_convention": room_ok_avg,
            "room_sep_floor": ARM_A_ACC_FLOOR,
            "ladder": ladder,
        },
        "dominance": {
            "n_dominates_both": n_dom,
            "n_assigned_is_better": int(sum(
                1 for d in DIAL_NAMES if per[d]["assigned_is_better"])),
            "vol_pres_beaten": bool(per["volume"]["hybrid_gt_ridge"]
                                    and per["presence"]["hybrid_gt_ridge"]),
            "mood_matched": bool(per["mood"]["hybrid_ge_ridge"]),
            "never_exceeds_pure_ridge": never_exceeds_ridge,
            "hybrid_minus_ridge": {d: per[d]["hybrid_minus_ridge"] for d in DIAL_NAMES},
            "hybrid_minus_mlp": {d: per[d]["hybrid_minus_mlp"] for d in DIAL_NAMES},
        },
        "pure_ridge_gate": {
            "dial_pass": ridge_pass,
            "n_pass": int(ridge["gate"]["n_pass"]),
            "ladder": ridge["gate"]["ladder"],
        },
        "pure_mlp_gate": {
            "dial_pass": mlp["gate"]["dial_pass"],
            "n_pass": int(mlp["gate"]["n_pass"]),
        },
        "hybrid_vs_pure_ridge_pass_set_equal": bool(
            passes == {d: bool(ridge_pass[d]) for d in DIAL_NAMES}),
        "note": ("the hybrid's still/room/null columns come from the reader "
                 "named in `reader`, quoted from the two imported reports of "
                 "THIS run; the room column gates on the published convention "
                 "of that branch and book-equotes the common convention."),
    }


# --------------------------------------------------------------------- #
# C3 — the TEST-BLIND nested selector (control, never gated)            #
# --------------------------------------------------------------------- #
def nested_hybrid_loro(z: np.ndarray, Y: np.ndarray, groups: np.ndarray,
                       dev: str = "cpu", seed: int = SEED_H) -> dict:
    """Per-dial reader choice made WITHOUT the held-out room.

    For each outer fold (held-out room f) the two readers are scored by inner
    LORO R2 over the 26 TRAINING rooms only — the ridge via E12's imported
    loro_predict, the MLP via E13b's imported mlp_loro — and the higher inner
    score wins that dial for that fold. The held-out room is then read by the
    winning reader's outer-fold prediction. Nothing about room f enters its own
    reader choice, so the resulting per-dial R2 is an honest out-of-sample
    number for "a per-dial reader", and it is the strongest available check on
    whether the FIXED assignment was the right one (it is booked, not gated:
    the pre-registered claim is the fixed-assignment hybrid).

    Cost: one inner MLP LORO (n_train folds) per outer fold, i.e. ~F*(F-1) MLP
    fits per arm (F=27 -> 702), which is why it defaults to the primary arm.
    """
    ids = np.unique(groups)
    F = int(len(ids))
    pos = np.searchsorted(ids, groups)
    z32 = np.asarray(z, np.float32)
    outer_ridge, lam_med = loro_predict(z, Y, groups)
    outer_mlp = mlp_loro(z32, Y, groups, dev, seed=seed + 7,
                         want_curv=False)["pred"]
    pred = np.zeros_like(Y, dtype=np.float64)
    choices = {d: [] for d in DIAL_NAMES}
    inner = []
    for f in range(F):
        tr = pos != f
        ztr, Ytr, gtr = z[tr], Y[tr], groups[tr]
        pr_r, _ = loro_predict(ztr, Ytr, gtr)
        pr_m = mlp_loro(np.asarray(ztr, np.float32), Ytr, gtr, dev,
                        seed=seed + 101 * (f + 1), want_curv=False)["pred"]
        r2r, r2m = r2_columns(Ytr, pr_r), r2_columns(Ytr, pr_m)
        row = {}
        for j, d in enumerate(DIAL_NAMES):
            pick = _pick(r2r[j], r2m[j])
            choices[d].append(pick)
            pred[pos == f, j] = (outer_ridge if pick == RIDGE
                                 else outer_mlp)[pos == f, j]
            row[d] = {"inner_ridge": _r(r2r[j]), "inner_mlp": _r(r2m[j]),
                      "pick": pick}
        inner.append({"held_out_room": int(ids[f]), "dials": row})
    r2_still = {d: _r(v) for d, v in zip(DIAL_NAMES, r2_columns(Y, pred))}
    r2_room = {d: _r(v) for d, v in
               zip(DIAL_NAMES, _avpred_room_r2(pred, Y, groups))}
    ridge_only = {d: _r(v) for d, v in zip(DIAL_NAMES,
                                           r2_columns(Y, outer_ridge))}
    mlp_only = {d: _r(v) for d, v in zip(DIAL_NAMES, r2_columns(Y, outer_mlp))}
    return {
        "reader": ("nested per-dial selector: inner-LORO (train rooms only) "
                   "ridge vs MLP at k=64, higher wins that dial for that fold"),
        "r2_still_loro_k64": r2_still,
        "r2_room_loro_avg_pred_k64": r2_room,
        "ridge_only_k64": ridge_only,
        "mlp_only_k64": mlp_only,
        "mlp_minus_ridge_k64": {d: _r(r2_still[d] - ridge_only[d])
                                for d in DIAL_NAMES},
        "nested_minus_fixed_k64": None,      # filled by main (needs the fixed read)
        "picks": {d: {"mlp_folds": int(sum(1 for x in choices[d] if x == MLP)),
                      "ridge_folds": int(sum(1 for x in choices[d]
                                               if x == RIDGE)),
                      "n_folds": F,
                      "majority": (MLP if sum(1 for x in choices[d] if x == MLP)
                                   > F // 2 else RIDGE)}
                  for d in DIAL_NAMES},
        "per_fold_choices": inner,
        "lambda_median_k64": None if lam_med != lam_med else _r(lam_med),
        "note": ("test-blind control (C3): the reader for each dial is chosen "
                 "on the training rooms of that fold, so it cannot peek at the "
                 "held-out room. Booked, never gated."),
    }


def selector_selftest(dev: str = "cpu") -> dict:
    """G0d'' — carrier-free, model-free validation of E28's OWN logic.

    A synthetic embedding with a KNOWN structure: dial 0 and dial 2 are linear
    in the embedding, dial 1 is nonlinear (sin + square) and unreadable by a
    ridge. The nested selector must (a) pick the MLP for the nonlinear dial and
    reach at least ridge+0.05 there, while (b) staying within 0.05 of the pure
    ridge on the two linear dials. Without this the experiment's selector could
    be broken in a way that looks like an architectural answer.
    """
    t0 = time.time()
    rng = np.random.default_rng(SEED_H + 3)
    R = rng.standard_normal((SELFTEST_ROOMS, SELFTEST_DIM))
    X = np.repeat(R, SELFTEST_STILLS, 0) + \
        0.05 * rng.standard_normal((SELFTEST_ROOMS * SELFTEST_STILLS, SELFTEST_DIM))
    groups = np.repeat(np.arange(SELFTEST_ROOMS), SELFTEST_STILLS)
    w = rng.standard_normal((SELFTEST_DIM, 5))
    lin0, nl1, sq1, lin2 = (X @ w[:, 0], X @ w[:, 1], X @ w[:, 2], X @ w[:, 3])
    Y = np.stack([lin0, 2.0 * np.sin(2.5 * nl1) + 1.5 * sq1 ** 2, lin2], 1)
    Y = (Y - Y.mean(0)) / (Y.std(0) + 1e-9)
    z = np.asarray(X, np.float32)

    ridge_pred, _ = loro_predict(z, Y, groups)
    r2r = r2_columns(Y, ridge_pred)
    mlp_pred = mlp_loro(z, Y, groups, dev, seed=SEED_H + 11,
                        want_curv=False)["pred"]
    r2m = r2_columns(Y, mlp_pred)
    nest = nested_hybrid_loro(z, Y, groups, dev, seed=SEED_H + 21)
    r2n = np.array([nest["r2_still_loro_k64"][d] for d in DIAL_NAMES], float)

    # (b) logic: the rule itself, three hand-made cases (ties -> ridge), and
    # every fold of every dial must obey it (read back off the fold record).
    rule_cases = {"ridge_wins": _pick(0.5, 0.2) == RIDGE,
                  "mlp_wins": _pick(0.1, 0.4) == MLP,
                  "tie_goes_to_ridge": _pick(0.3, 0.3) == RIDGE}
    rule_holds = all(
        (row["dials"][d]["pick"] == RIDGE)
        == (row["dials"][d]["inner_ridge"] >= row["dials"][d]["inner_mlp"])
        for row in nest["per_fold_choices"] for d in DIAL_NAMES)
    # (c) both reader branches were exercised — a selector that always returns
    # one reader would pass (a) and (b) vacuously.
    both_branches = bool(all(nest["picks"][d]["ridge_folds"] > 0
                             or nest["picks"][d]["mlp_folds"] == SELFTEST_ROOMS
                             for d in DIAL_NAMES)
                         and any(nest["picks"][d]["ridge_folds"] > 0
                                 for d in DIAL_NAMES)
                         and any(nest["picks"][d]["mlp_folds"] > 0
                                 for d in DIAL_NAMES))
    out = {
        "device": dev,
        "ridge_r2": [_r(x) for x in r2r],
        "mlp_r2": [_r(x) for x in r2m],
        "nested_hybrid_r2": [_r(x) for x in r2n],
        "nested_minus_ridge": [_r(r2n[j] - r2r[j]) for j in range(3)],
        "nested_picks": {d: nest["picks"][d]["majority"] for d in DIAL_NAMES},
        "nested_pick_counts": {d: {"mlp_folds": nest["picks"][d]["mlp_folds"],
                                   "ridge_folds": nest["picks"][d]["ridge_folds"],
                                   "n_folds": nest["picks"][d]["n_folds"]}
                               for d in DIAL_NAMES},
        "rule_cases": rule_cases,
        "rule_holds_on_every_fold": bool(rule_holds),
        "both_reader_branches_exercised": both_branches,
        "design": ("dial 0 / dial 2 linear in the embedding, dial 1 = "
                   "2*sin(2.5x) + 1.5*x^2 (a ridge cannot read it)"),
        "joint_lambda_note": (
            "the imported ridge picks lambda on the JOINT 3-dial loss "
            "(E12's pick_lambda), so one unreadable nonlinear dial pushes "
            "lambda up and costs the ridge on the LINEAR dials too: fixed "
            "lambda 1e-3 reads this synthetic's linear dials at 1.00/1.00, "
            "the probe's own per-fold choice lands at lambda ~1.0 and reads "
            "them at 0.67/0.48 (measured at write time, /tmp/sel_diag.py). "
            "This is why the MLP can win the linear dials in the synthetic "
            "AND why the fixed assignment's ridge branch is conservative in "
            "the real run: mood's ridge number is measured under the same "
            "joint-lambda rule."),
    }
    out["pass"] = bool(
        r2n[1] >= r2r[1] + 0.05          # the selector must win the nonlinear dial
        and r2n[0] >= r2r[0] - 0.05      # ...and not damage the linear dials
        and r2n[2] >= r2r[2] - 0.05
        and all(rule_cases.values())
        and rule_holds
        and both_branches
        and all(nest["picks"][d]["n_folds"] == SELFTEST_ROOMS
                for d in DIAL_NAMES))    # F folds, one per room
    out["seconds"] = _r(time.time() - t0)
    return out


# --------------------------------------------------------------------- #
# CPU-only mode (no model, no GPU): bank, carriers, certificates, all    #
# three self-tests. No verdict.                                         #
# --------------------------------------------------------------------- #
def cpu_only() -> dict:
    t0 = time.time()
    st_ridge = harness_selftest()
    st_mlp = mlp_selftest("cpu")
    st_sel = selector_selftest("cpu")
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
        "experiment": "E28 per-dial hybrid reader",
        "mode": "cpu-only (no model, no GPU, no verdict)",
        "seed_carriers": SEED, "seed_reader": SEED_B, "seed_selector": SEED_H,
        "primary_arm": PRIMARY_ARM, "arms": list(ARMS),
        "assignment": ASSIGNMENT,
        "rooms": len(bank), "replicates": N_REPLICATES,
        "readers": {"ridge": ("E13's numpy LORO ridge over the arm's PCA "
                              "space, k=64 primary (imported verbatim)"),
                    "mlp": (f"sklearn MLPRegressor k->{MLP_HIDDEN} ReLU->3, "
                            f"{MLP_SOLVER}, alpha={MLP_ALPHA}, "
                            f"max_iter={MLP_MAX_ITER}, per-fold LORO "
                            f"(imported verbatim from E13b)")},
        "harness_selftest_ridge": st_ridge,
        "harness_selftest_mlp": st_mlp,
        "selector_selftest": st_sel,
        "carrier_mixture": n2_info,
        "arm_L_mirror_check": mirror_check(bank, K),
        "carrier_certificates": certs,
        "staging_fidelity_spearman_target_vs_label": {
            d: _r(spearman(targets[:, i], labels[:, i]))
            for i, d in enumerate(DIAL_NAMES)},
        "note": ("No verdict in CPU-only mode. Watch: the selector self-test "
                 "(E28's own new logic) and the N2 certificate (the world the "
                 "hybrid is tested in). The hybrid needs NO new reader code — "
                 "it is the pairing of the two imported readers."),
        "seconds": _r(time.time() - t0),
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
        out = {"experiment": "E28 per-dial hybrid reader", "verdict": "ABORTED",
               "reason": reason, "guard_preflight": guard_info}
        print(json.dumps(out, indent=2))
        return out

    base = {
        "experiment": "E28 per-dial hybrid reader",
        "seed_carriers": SEED, "seed_reader": SEED_B, "seed_selector": SEED_H,
        "primary_arm": PRIMARY_ARM, "arms": list(ARMS),
        "dial_names": DIAL_NAMES, "extra_dials": EXTRA_DIALS,
        "k_primary": K_PRIMARY, "replicates": N_REPLICATES,
        "assignment": ASSIGNMENT,
        "nested_mode": NESTED_MODE, "nested_arms": list(NESTED_ARMS),
        "guard_preflight": guard_info,
        "readers": {
            "ridge": ("E13/E12's numpy LORO ridge over the arm's label-free "
                      "PCA space, k=16/64/256, per-fold inner-CV lambda "
                      "(imported verbatim from e13.arm_report)"),
            "mlp": (f"sklearn MLPRegressor hidden({MLP_HIDDEN}), ReLU, "
                    f"solver={MLP_SOLVER}, alpha={MLP_ALPHA}, "
                    f"max_iter={MLP_MAX_ITER}; per-fold LORO with train-only "
                    f"standardization; {NULL_PERMS}-perm room-shuffle null "
                    f"(imported verbatim from e13b.mlp_arm_report)"),
            "hybrid": ("per-dial: mood -> ridge, volume/presence -> MLP "
                       "(fixed before running; the selector is E28's only new "
                       "logic)"),
        },
    }

    # G0d / G0d' / G0d'' — cheapest first; if any reader or the selector is
    # broken, nothing downstream is interpretable. All three are CPU/model-free.
    st_ridge = harness_selftest()
    log(f"ridge self-test: {st_ridge}")
    st_mlp = mlp_selftest("cpu")
    log(f"mlp self-test: {st_mlp}")
    st_sel = selector_selftest("cpu")
    log(f"selector self-test: {st_sel}")
    if not st_ridge.get("pass"):
        out = dict(base)
        out.update({"verdict": "INVALID_HARNESS",
                    "harness_selftest_ridge": st_ridge,
                    "harness_selftest_mlp": st_mlp,
                    "selector_selftest": st_sel,
                    "reason": "G0d: E13's ridge self-test failed"})
        print(json.dumps(out, indent=2))
        return out
    if not st_mlp.get("pass"):
        out = dict(base)
        out.update({"verdict": "INVALID_HARNESS",
                    "harness_selftest_ridge": st_ridge,
                    "harness_selftest_mlp": st_mlp,
                    "selector_selftest": st_sel,
                    "reason": "G0d': the MLP reader failed its self-test"})
        print(json.dumps(out, indent=2))
        return out
    if not st_sel.get("pass"):
        out = dict(base)
        out.update({"verdict": "INVALID_HARNESS",
                    "harness_selftest_ridge": st_ridge,
                    "harness_selftest_mlp": st_mlp,
                    "selector_selftest": st_sel,
                    "reason": ("G0d'': E28's per-dial selector failed its "
                               "synthetic test (it must win the nonlinear dial "
                               "without damaging the linear ones)")})
        print(json.dumps(out, indent=2))
        return out

    # Bank + carriers + certificates — E13's own code, CPU, before the model.
    bank = build_bank(N_REPLICATES)
    log(f"bank: {len(bank)} rooms (replicates={N_REPLICATES})")
    try:
        K, n2_info = build_arm_knobs(bank)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED",
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

    fid = {d: _r(spearman(targets[:, i], labels[:, i]))
           for i, d in enumerate(DIAL_NAMES)}
    fid_pass = bool(sum(1 for d in DIAL_NAMES if fid[d] >= FIDELITY_FLOOR) >= 2)
    extra_stats = {d: {"min": _r(min(r["extra"][d] for r in bank)),
                       "max": _r(max(r["extra"][d] for r in bank)),
                       "std": _r(np.std([r["extra"][d] for r in bank]))}
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
                    "staging_fidelity_spearman_target_vs_label": fid,
                    "carrier_certificates": certificates,
                    "reason": "G0a: the staged scripts did not move >= 2/3 dials"})
        print(json.dumps(out, indent=2))
        return out

    import torch
    torch.manual_seed(SEED)          # embedding pass replicates E13/E13b
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

    reports = {}
    try:
        for a in ARMS:
            log(f"arm {a}: rendering + embedding {len(bank)} rooms x "
                f"{N_STILLS} stills")
            data = collect_arm(a, K, bank, model, processor, dev, torch)
            X, Y, Yt, groups = data[0], data[1], data[2], data[3]
            log(f"arm {a}: ridge probe sweep (E13's arm_report)...")
            rep = {"ridge": arm_report(a, data, knob_mats[a], targets)}
            # C5 — E28's own imported-ridge read must reproduce the report's.
            basis, _ = pca_basis(X, K_WIDE)
            z64 = X @ basis[:, :K_PRIMARY].astype(np.float64)
            ridge_pred64, lam_med = loro_predict(z64, Y, groups)
            r2_rc = {d: _r(v) for d, v in zip(DIAL_NAMES, r2_columns(Y, ridge_pred64))}
            rep["ridge_recompute_k64"] = {
                "r2_still_loro_k64": r2_rc,
                "lambda_median_k64": None if lam_med != lam_med else _r(lam_med),
                "matches_arm_report": bool(all(
                    abs(rep["ridge"]["r2_still_loro"]["64"][d] - r2_rc[d]) <= 1e-6
                    for d in DIAL_NAMES)),
            }
            if dev == "cuda":
                torch.cuda.empty_cache()
            torch.manual_seed(SEED_B)      # reader draws are E13b's own
            np.random.seed(SEED_B)
            log(f"arm {a}: MLP reader (LORO fold-nets + {NULL_PERMS}-perm null)...")
            rep["mlp"] = mlp_arm_report(a, X, Y, groups, dev)
            # C4 — the ridge's room-level read under the MLP's convention.
            ridge_room_avg = _avpred_room_r2(ridge_pred64, Y, groups)
            rep["ridge_room_avg_pred_k64"] = {
                d: _r(v) for d, v in zip(DIAL_NAMES, ridge_room_avg)}
            rep["hybrid"] = hybrid_report(
                a, rep["ridge"], rep["mlp"], rep["ridge_room_avg_pred_k64"],
                rep["ridge"]["controls"]["room_identity_acc"])
            if a in NESTED_ARMS:
                torch.manual_seed(SEED_H)
                np.random.seed(SEED_H)
                log(f"arm {a}: NESTED selector control (train-only reader "
                    f"choice per dial)...")
                nest = nested_hybrid_loro(z64, Y, groups, dev, seed=SEED_H)
                nest["nested_minus_fixed_k64"] = {
                    d: _r(nest["r2_still_loro_k64"][d]
                          - rep["hybrid"]["per_dial"][d]["r2_still_loro_k64"])
                    for d in DIAL_NAMES}
                nest["agrees_with_fixed_on_higher_order"] = bool(
                    sum(1 for d in ("volume", "presence")
                        if nest["r2_still_loro_k64"][d]
                        > rep["ridge"]["r2_still_loro"]["64"][d] + TOL) >= 1)
                rep["nested"] = nest
                log(f"arm {a}: nested picks "
                    + ", ".join(f"{d}:{nest['picks'][d]['majority']}"
                                f"({nest['picks'][d]['mlp_folds']}/{nest['picks'][d]['n_folds']}MLP)"
                                for d in DIAL_NAMES))
            reports[a] = rep
            log(f"arm {a}: hybrid k64={rep['hybrid']['gate']['mean_r2_k64']} "
                f"n_pass={rep['hybrid']['gate']['n_pass']} "
                f"ladder={rep['hybrid']['gate']['ladder']} | "
                f"ridge n_pass={rep['ridge']['gate']['n_pass']} | "
                f"mlp n_pass={rep['mlp']['gate']['n_pass']}")
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED",
                    "reason": f"frame/embed/probe failed: {e}"})
        print(json.dumps(out, indent=2))
        return out

    # ---------------- pre-registered verdict mapping ---------------- #
    primary, control = reports[PRIMARY_ARM], reports["L"]
    hyb_n2, hyb_L = primary["hybrid"], control["hybrid"]
    dom = hyb_n2["dominance"]
    sens_pass = bool(control["ridge"]["g0b_luminance_r2_k64"] >= SENSITIVITY_FLOOR)
    cert_primary_ok = bool(certificates[PRIMARY_ARM]["summary"]["pass"])
    control_keeps = bool(control["ridge"]["gate"]["ladder"] == "KEEP")
    mlp_reader_L_ok = bool(sum(
        1 for d in DIAL_NAMES
        if control["mlp"]["r2_still_loro"]["64"][d] >= R2_FLOOR) >= 2)
    gc_ok = bool(primary["mlp"]["mlp_genuinely_nonlinear"])
    recompute_ok = bool(primary["ridge_recompute_k64"]["matches_arm_report"])

    per_dial = hyb_n2["per_dial"]
    vol_pres_beaten = bool(dom["vol_pres_beaten"])
    mood_matched = bool(dom["mood_matched"])
    n_dom = int(dom["n_dominates_both"])
    mean_s = float(hyb_n2["gate"]["mean_r2_k64"])
    mean_null = float(hyb_n2["gate"]["mean_null95_k64"])
    clears_null = bool(mean_s > mean_null)
    never_exceeds = bool(dom["never_exceeds_pure_ridge"])
    pass_set_equal = bool(hyb_n2["hybrid_vs_pure_ridge_pass_set_equal"])

    beats = {d: bool(per_dial[d]["hybrid_gt_ridge"]) for d in DIAL_NAMES}
    ridge_beats_mlp = {d: bool(per_dial[d]["pure_ridge_k64"]
                               > per_dial[d]["pure_mlp_k64"] + TOL)
                       for d in DIAL_NAMES}
    mlp_beats_ridge = {d: bool(per_dial[d]["pure_mlp_k64"]
                               > per_dial[d]["pure_ridge_k64"] + TOL)
                       for d in DIAL_NAMES}
    premise_ok = bool(any(ridge_beats_mlp.values()) and any(mlp_beats_ridge.values()))

    if not sens_pass:
        verdict, vreason = "INVALID_HARNESS", (
            "G0b: Arm L luminance sensitivity below floor — the ridge harness "
            "is blind here")
    elif not recompute_ok:
        verdict, vreason = "INVALID_HARNESS", (
            "C5: E28's imported-ridge recompute does not reproduce E13's "
            "arm_report at k=64 — the hybrid would be stitching numbers from "
            "two different probes")
    elif not gc_ok:
        verdict, vreason = "INVALID_HARNESS", (
            "Gc: the MLP branch collapsed toward affine on N2 (curvature below "
            "floor), so the hybrid's volume/presence branch is not the "
            "nonlinear reader it claims to be (deviation from E13b's "
            "INCONCLUSIVE label, booked in the docstring)")
    elif not mlp_reader_L_ok:
        verdict, vreason = "INVALID_HARNESS", (
            "Gr: the MLP reader cannot read the READABLE arm (Arm L)")
    elif not cert_primary_ok:
        verdict, vreason = "INVALID_STAGING", (
            "G0c: the PRIMARY carrier failed its certificate (dead or "
            "accidentally-linear) — the arm tested nothing")
    elif not control_keeps:
        verdict, vreason = "INVALID_CONTROL", (
            "Arm L did not reproduce E12's KEEP under the RIDGE, so the N2 "
            "hybrid result cannot be attributed to the carrier/embedding")
    elif not premise_ok:
        verdict, vreason = "INCONCLUSIVE", (
            "premise fails: no per-dial split is at stake on N2 in this run "
            f"(parity check: ridge>MLP on {[d for d in DIAL_NAMES if ridge_beats_mlp[d]]}, "
            f"MLP>ridge on {[d for d in DIAL_NAMES if mlp_beats_ridge[d]]}) — "
            "one pure reader dominates, so the hybrid cannot be distinguished")
    elif vol_pres_beaten and mood_matched and n_dom >= 2 and clears_null:
        verdict, vreason = "KEEP", (
            "a per-dial reader is the right architecture: the hybrid beats "
            f"pure ridge on volume ({per_dial['volume']['hybrid_minus_ridge']:+.3f}) "
            f"and presence ({per_dial['presence']['hybrid_minus_ridge']:+.3f}), "
            "matches it on mood (the ridge branch, equal by construction), and "
            f"dominates BOTH pure readers on {n_dom}/3 dials "
            f"(mean hybrid k64 {mean_s:.3f} vs mean null95 {mean_null:.3f})")
    elif never_exceeds and pass_set_equal:
        verdict, vreason = "KILL", (
            "the per-dial split was a mirage: the hybrid never strictly "
            "exceeds pure ridge on any dial "
            f"(hybrid-minus-ridge {dom['hybrid_minus_ridge']}) and its E12 gate "
            "pass set equals the ridge's — the nonlinear reader adds nothing "
            "even for the higher-order dials")
    else:
        verdict, vreason = "INCONCLUSIVE", (
            "partial: "
            f"volume beaten={beats['volume']} presence beaten={beats['presence']} "
            f"mood matched={mood_matched} n_dom={n_dom} clears_null={clears_null} "
            f"(hybrid-minus-ridge {dom['hybrid_minus_ridge']}) — never "
            "overclaim from a partial")

    side_by_side = {
        a: {"per_dial": reports[a]["hybrid"]["per_dial"],
            "ridge_k64": reports[a]["ridge"]["r2_still_loro"]["64"],
            "mlp_k64": reports[a]["mlp"]["r2_still_loro"]["64"],
            "hybrid_k64": {d: reports[a]["hybrid"]["per_dial"][d]["r2_still_loro_k64"]
                           for d in DIAL_NAMES},
            "ridge_room_k64": reports[a]["ridge"]["r2_room_loro"]["64"],
            "mlp_room_k64": reports[a]["mlp"]["r2_room_loro_avg_pred"]["64"],
            "ridge_room_avg_pred_k64": reports[a]["ridge_room_avg_pred_k64"],
            "n_dominates_both": reports[a]["hybrid"]["dominance"]["n_dominates_both"],
            "hybrid_ladder": reports[a]["hybrid"]["gate"]["ladder"],
            "ridge_ladder": reports[a]["ridge"]["gate"]["ladder"],
            "mlp_n_pass": reports[a]["mlp"]["gate"]["n_pass"],
            "hybrid_n_pass": reports[a]["hybrid"]["gate"]["n_pass"]}
        for a in ARMS}

    nested_summary = {
        a: {"picks": reports[a]["nested"]["picks"],
            "r2_still_loro_k64": reports[a]["nested"]["r2_still_loro_k64"],
            "ridge_only_k64": reports[a]["nested"]["ridge_only_k64"],
            "mlp_minus_ridge_k64": reports[a]["nested"]["mlp_minus_ridge_k64"],
            "nested_minus_fixed_k64": reports[a]["nested"]["nested_minus_fixed_k64"],
            "agrees_with_fixed_on_higher_order":
                reports[a]["nested"]["agrees_with_fixed_on_higher_order"]}
        for a in NESTED_ARMS if "nested" in reports[a]}

    out = dict(base)
    out.update({
        "model": model_used, "load_notes": load_notes, "device": dev,
        "rooms": len(bank), "stills_per_room": N_STILLS,
        "label_stats": {d: {"min": _r(labels[:, i].min()),
                            "max": _r(labels[:, i].max()),
                            "std": _r(labels[:, i].std())}
                        for i, d in enumerate(DIAL_NAMES)},
        "extra_dial_stats": extra_stats,
        "harness_selftest_ridge": st_ridge,
        "harness_selftest_mlp": st_mlp,
        "selector_selftest": st_sel,
        "staging_fidelity_spearman_target_vs_label": fid,
        "g0a_staging_fidelity_pass": fid_pass,
        "arm_L_mirror_check": mirror,
        "carrier_mixture": n2_info,
        "carrier_certificates": certificates,
        "arms": {a: reports[a] for a in ARMS},
        "side_by_side_k64": side_by_side,
        "nested_control": nested_summary,
        "attribution": {
            "assignment": ASSIGNMENT,
            "hybrid_gate_n2": hyb_n2["gate"]["dial_pass"],
            "ridge_gate_n2": primary["ridge"]["gate"]["dial_pass"],
            "mlp_gate_n2": primary["mlp"]["gate"]["dial_pass"],
            "n_dominates_both_n2": n_dom,
            "n_dominates_both_per_arm": {
                a: reports[a]["hybrid"]["dominance"]["n_dominates_both"]
                for a in ARMS},
            "vol_pres_beaten": vol_pres_beaten,
            "mood_matched": mood_matched,
            "never_exceeds_pure_ridge": never_exceeds,
            "pass_set_equals_pure_ridge": pass_set_equal,
            "clears_null": clears_null,
            "premise_ok": premise_ok,
            "ridge_beats_mlp": ridge_beats_mlp,
            "mlp_beats_ridge": mlp_beats_ridge,
            "carrier_conditional_split": (
                "n_dominates_both per arm answers whether the per-dial split "
                "is a property of the CARRIER: on E12's linear arm (L) the "
                "pure ridge was measured better on volume/presence, so a "
                "hybrid that is right on N2 and wrong on L is a "
                "carrier-conditional architecture, not a universal one."),
        },
        "gates": {
            "g0d_ridge_selftest": st_ridge.get("pass"),
            "g0d_prime_mlp_selftest": st_mlp.get("pass"),
            "g0d_double_prime_selector_selftest": st_sel.get("pass"),
            "g0a_staging_fidelity": {"floor": FIDELITY_FLOOR, "pass": fid_pass,
                                     "measured": fid},
            "g0b_sensitivity_arm_L": {"floor": SENSITIVITY_FLOOR,
                                      "measured": control["ridge"]["g0b_luminance_r2_k64"],
                                      "pass": sens_pass},
            "g0c_carrier_certificate_primary": certificates[PRIMARY_ARM]["summary"],
            "arm_L_control_keeps_ridge": control_keeps,
            "arm_L_ladder_ridge": control["ridge"]["gate"]["ladder"],
            "arm_L_ladder_hybrid": hyb_L["gate"]["ladder"],
            "arm_N1_ladders": {"ridge": reports["N1"]["ridge"]["gate"]["ladder"],
                               "hybrid": reports["N1"]["hybrid"]["gate"]["ladder"],
                               "mlp_n_pass": reports["N1"]["mlp"]["gate"]["n_pass"]},
            "arm_N2_ladders": {"ridge": reports["N2"]["ridge"]["gate"]["ladder"],
                               "hybrid": reports["N2"]["hybrid"]["gate"]["ladder"],
                               "mlp_n_pass": reports["N2"]["mlp"]["gate"]["n_pass"]},
            "gr_mlp_reads_arm_L": mlp_reader_L_ok,
            "gc_mlp_nonlinear": gc_ok,
            "c5_ridge_recompute_matches": recompute_ok,
        },
        "cost": {
            "measured_reference": (
                "E13b (same workload, no nested control) = 1700 s wall; "
                "MLP nulls 1577 s of it"),
            "this_run_seconds": _r(time.time() - t0),
            "guard_wall_note": (
                "guard.py's Guard default wall-clock is 1800 s; fire E28 "
                "manually with a raised outer timeout, or E28_NESTED=0, to "
                "avoid a wall-clock truncated run"),
        },
        "data_needed": [
            "ffmpeg ~/.local/bin/ffmpeg (lavfi: color, eq, noise, drawbox)",
            "facebook/ijepa_vith16_1k fp16 on the RTX 4050 (E9 loader)",
            "elephant package importable (dial bank = labels)",
            "roomgen.py loadable (frozen nonlinear physics; inline replica "
            "fallback recorded in carrier_source)",
            f"3 arms x {len(bank)} rooms x {N_STILLS} stills ~= "
            f"{3 * len(bank) * N_STILLS} encoder forwards (~3 min GPU) + the "
            "ridge sweeps + the 3 MLP nulls (~26 min) + the nested control "
            "(~1.5 min on N2)",
            "GPU free (guard preflight in-process)",
        ],
        "wiring": ("NOT in QUEUE.md / runner.py EXP_MOD by design — manual "
                   "fire only, as E13b"),
        "verdict": verdict,
        "verdict_reason": vreason,
        "seconds_total": _r(time.time() - t0),
        "note": (
            "E28 asks whether E13b's PER-DIAL answer is an architecture. E13b "
            "put one reader (ridge vs sklearn-LBFGS MLP) on E13's fixed world "
            "(27-room bank, elephant DialBank labels, carriers L/N1/N2, frozen "
            "I-JEPA embeddings, PCA spaces) and found mood ridge-optimal "
            "(0.54 vs 0.37) while volume/presence want the MLP (-0.10 -> 0.21, "
            "0.27 -> 0.34): no single reader wins all three dials. E28 takes "
            "that as the assignment (mood->ridge, volume/presence->MLP, fixed "
            "BEFORE the run, never chosen by score), stitches the two imported "
            "readers' per-dial numbers into one hybrid read on the same three "
            "arms, and states its claim as a DOMINANCE: the hybrid must beat "
            "pure ridge on volume/presence, match it on mood, and dominate both "
            "pure readers on >= 2/3 dials (KEEP); if it never strictly exceeds "
            "the ridge anywhere, the per-dial split was a mirage (KILL); "
            "anything partial is INCONCLUSIVE. Validity first (E13/E13b's "
            "self-tests, G0a/G0b/G0c, plus E28's own selector self-test and the "
            "ridge-recompute check), INVALID_CONTROL if Arm L does not "
            "replicate E12's KEEP, and a booked test-blind NESTED selector "
            "(reader chosen per dial from the training rooms of each fold) that "
            "shows whether the fixed assignment is the one a blind procedure "
            "would have found. Caveats, pre-registered: the assignment is "
            "in-sample (derived from E13b on this very bank/carrier/encoder), so "
            "a KEEP is a consolidation with a book-kept blind control, not a "
            "fresh discovery; the metric is still-LORO R2(k=64) as pre-"
            "registered for both readers; and the split may be "
            "carrier-conditional (n_dominates_both per arm is booked for "
            "exactly that)."),
    })
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
