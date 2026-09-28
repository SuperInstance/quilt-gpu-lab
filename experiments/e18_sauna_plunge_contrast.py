#!/usr/bin/env python3
"""E18 — sauna/plunge contrast read: is the GAP between two rooms more readable
than the rooms themselves?

CLAIM UNDER TEST (concrete, falsifiable)
  E12 (experiments/e12_room_dial_reader.py) returned KEEP: a frozen I-JEPA
  linearly READS the elephant's dials (mood/volume/presence) off staged lavfi
  rooms — R2_still_loro(k=64) = 0.81 / 0.96 / 0.95, room-level R2 =
  0.89 / 0.97 / 0.94, all above a 200-shuffle null. E13 then showed mood
  survives a nonlinear carrier while volume/presence were partly staging
  artifacts. Both asked about ONE room at a time. The lab's doctrine says the
  opposite of that — "the walk between rooms is the lesson" (SPOOL.E16), "the
  contrast is the elephant's identity" (SPOOL.E18). E18 asks it directly:

      Is the CONTRAST between two rooms — the signed sauna/plunge gap
      (target_j − target_i, per dial) — MORE readable from the embedding PAIR
      than either room's absolute dials are readable on their own?

  KEEP (super-additivity) = the direct gap read beats BOTH
      (a) the single-room absolute-dial read, and
      (b) the two-absolutes baseline (the gap predicted by differencing the two
          rooms' own out-of-fold absolute predictions)
  on >= 2 of 3 dials, and the gap read is above its own shuffle null. That
  would say the pair representation carries contrast information the two
  single-room reads do not already contain.
  KILL = at most 1 of 3 dials beats the two-absolutes baseline: contrast is
  just the two absolutes differenced — the walk adds nothing. (INCONCLUSIVE =
  >= 2 dials beat the baseline but fewer than 2 clear BOTH comparators and the
  null.)
  INVALID_STAGING = the carrier certificate fails (dead or non-injective
  staged carrier, or the scripts stopped moving the dials).
  A KILL is a win (a claim died honestly); INVALID_* always means the arm
  tested nothing and is never reported as a KILL.

DEFINITIONS
  bank          : E13's `build_bank(1)` verbatim — E12's 27-cell dial grid
                  (m ∈ {-0.8,0,+0.8}, v,p ∈ {0.15,0.50,0.85}), one staged
                  script per room, target triple booked alongside, and the
                  dial LABELS read by the REAL elephant DialBank (never typed).
  carrier       : E12's linear staging (E13's Arm L) — `knobs_linear` +
                  E13's shared `render_scene`/`collect_arm`. The "sauna/plunge"
                  framing is Casey's; the intervention here is NOT the carrier
                  (that was E13's job). E18 changes only the TARGET and the CV
                  unit: absolute dials, one room at a time -> signed gaps, one
                  pair at a time.
  room feature  : E12's room-level convention — PCA basis fit (label-free) on
                  the 324 still embeddings (top K_WIDE=256), each room's 12
                  stills averaged IN that space. Width k (primary 13 =
                  min(K_PRIMARY=64, 27//2), E12's overdetermination rule).
  pairs         : C(27,2) = 351 unordered pairs in canonical index order
                  i < j, with the SIGNED target gap = target[j] − target[i]
                  (the sauna/plunge orientation is the canonical index order —
                  frozen, not chosen per dial; gap-sign balance is booked).
  pair features : arms, all ridge, all multi-output (3 dials at once)
                    concat  = [z_i, z_j]                     (2k)  — the two rooms
                    diff    = z_j − z_i                      (k)  — the signed walk
                    pair    = [z_i, z_j, z_j − z_i]          (3k)  — PRIMARY (as tasked)
                    pair_inter = pair + top-4 outer products (3k+16) — BOOKED exploratory
                  (the concat block alone can already represent any linear
                  functional, including the difference; the arms separate
                  "read the walk" from "read both rooms".)
  targets       : gap  = target_j − target_i   (PRIMARY, the claim)
                  sum  = target_j + target_i   (booked control: if the pair
                        reader reads the SUM of the two rooms as well or
                        better, the contrast is not special)
                  absolute single-room dials (the (a) comparator, same probe)

CRITICAL CV DESIGN (pre-registered BEFORE the run; this is the whole reason
the experiment is buildable at all)
  27 rooms -> 351 pairs. Leave-one-PAIR-out is FORBIDDEN: a held-out pair
  (i,j) shares both its rooms with training pairs, so a pair-level split
  measures "predict the gap of a room I have already seen in other pairs",
  not "predict the gap involving an unseen room" — which is the claim, and
  the only split under which the two-absolutes baseline is even definable.
  So the outer CV is LEAVE-ONE-ROOM-OUT ON ROOMS:
      for each held-out room h (27 folds):
          test  = EVERY pair touching h          -> 26 pairs
          train = the C(26,2) = 325 pairs among the other 26 rooms
      i.e. the model never sees room h in ANY training pair, so no room is
      shared between train and test. Test predictions concatenate to 351
      out-of-fold gap predictions (one per pair).
  This is E12's grouped-CV convention, lifted from stills to pairs.
  Asserted structurally at run time (`fold_structure_check`): per fold,
  |test| = n-1, |train| = C(n-1,2), every test pair contains h, no train pair
  contains h. A booked leak probe also runs the primary arm under a random
  80/20 PAIR split for comparison (never gated) — the size of the inflation is
  the evidence for this design choice.
  Inner lambda selection is ALSO grouped on rooms: inside each outer fold, for
  each training room g the inner-test is every training pair touching g and
  the inner-train is the rest (26 inner folds x 6 lambdas, one SVD per inner
  fold via e12's `_ridge_path_pred` many-lambda trick).
  PCA basis: label-free, fit once on all still embeddings (E12's convention),
  then frozen for every fold and every arm — no label ever enters the basis.
  Null: 200 ROOM-LEVEL target shuffles — permute the 27 target triples across
  rooms, rebuild the pairwise gaps from the permuted triples, rerun the SAME
  LORO pair probe at the fold-median lambda. The embedding pairing is left
  intact (the shuffle destroys only the room -> dial correspondence), which is
  exactly E12's room-level null.

PRE-REGISTERED GATES (fixed before running; this file IS the registration)
  G0d harness self-test : CPU-only, synthetic (30 rooms, dial exactly linear
      in a 40-d embedding, 2% still noise): the imported pair+LORO machinery
      must read the synthetic gap at R2 >= 0.90 per dial, a room-shuffled
      control must collapse below 0.10, and `fold_structure_check` must pass.
      Carrier-free and model-free.
  G0a staging fidelity  : Spearman(target, elephant_label) >= 0.5 for >= 2/3
      dials on the shared bank — E12's G0a verbatim.
  G0c carrier certificate : E13's `carrier_certificate` on this bank's knob
      matrix, gated on its LIVENESS half only: the 27 knob vectors are
      pairwise distinct/injective AND >= 2 of 3 dials show distance-correlation
      p <= 0.05 against a 200-shuffle null AND 3-NN LOO-R2 >= 0.20, AND the
      Arm-L mirror check reproduces e12.stage_source's lavfi string. Both
      halves are reported, but NON-AFFINITY IS DELIBERATELY NOT GATED: E18
      uses E12's LINEAR carrier (E13 measured its curvature at 0.000 by
      construction), so gating non-affinity would invalidate by construction.
      Deviation from E13 pre-registered here.
  G0b sensitivity       : G0b.1 — E12's control verbatim: the still-level
      k=64 LORO read of per-still mean luminance R2 >= 0.90 (E12 measured
      0.993). A probe blind to a signal certainly present is blind, and a KILL
      from it is meaningless. G0b.2 — the pair machinery's own control: the
      SAME LORO pair probe reading the mean-luminance GAP (lum_j − lum_i) at
      the primary width must reach PAIR_SENSITIVITY_FLOOR = 0.50 and beat its
      own null. The floor is lower than 0.90 by pre-registration, because a
      DIFFERENCE target of the same signal has strictly less shared variance
      than the absolute target (the gap's variance is reported).
  G0e E12 replication   : in-run replication of E12's own gate at the
      still level — >= 2/3 dials with R2_still_loro(k=64) >= R2_FLOOR = 0.30.
      If E12's read does not reproduce here, the (a)/(b) comparators are
      meaningless in this run (E13's INVALID_CONTROL lesson, applied).
  G1 THE CLAIM (KEEP)   : on the PRIMARY arm ("pair") at k = 13, primary
      targeting the signed gap:
        exceed_d := gap_R2(d) > single_room_abs_R2(d)      (comparator a)
                    AND gap_R2(d) > two_abs_loo_R2(d)      (comparator b)
                    AND gap_R2(d) > null95_gap(d)
      KEEP  = exceed_d for >= 2 of 3 dials.
      (Also booked per dial: whether it beats the CONSERVATIVE baseline
      variant two_abs_fold, which predicts the non-held room in-sample.)
  G2 INCONCLUSIVE       : exactly 1 dial exceeds both comparators (and the
      null), or mean gap_R2 > mean null95.
  G3 KILL               : at most 1 dial beats the two-absolutes baseline
      (i.e. >= 2/3 dials: gap_R2 <= two_abs_loo_R2) — the contrast read is not
      super-additive; the walk is just the two absolutes differenced.
      (mean_gap_r2 vs mean_null95 is BOOKED in the gate block and does not
      rescue a KILL: the pre-registered lane is the baseline comparison.)
  INVALID_STAGING       : G0a or G0c fails.
  INVALID_HARNESS       : G0d, G0b or G0e fails.
  ABORTED               : guard preflight, model load, no frames, or < 8 rooms.

CONTROLS / BOOKED (never gated)
  C1 raw-pixel pair probe : the same LORO pair read on the ROOM-MEAN 16x9
      grayscale stills (144-d), PCA-reduced label-free to the SAME width as
      the embedding reader (k = 13) so the pair design stays overdetermined by
      the 325 training pairs and the control is apples-to-apples. If pixels
      beat the embedding, the embedding is losing contrast signal (E12's C1,
      lifted to pairs).
  C2 luminance-gap Spearman per dial.
  C3 permutation null (200 room shuffles) + p-values for the gap read.
  C4 E12 headline replication: still-level absolute dial R2 at k=16/64 (the
      booked reference numbers 0.81-0.97) alongside the room-level comparators.
  C5 knob ranges + E12's room-identity half-split accuracy (harness sanity,
      chance 1/27).
  C6 gap composition: per-dial gap histogram, sign balance, label-gap
      Spearman (target-gap vs bank-label-gap), gap variance vs absolute
      variance (the honest statement of why R2 across the two target types is
      not variance-matched).
  C7 arm ladder: concat / diff / pair / pair_inter across k ∈ {6, 13, 20} —
      which part of the pair actually carries the contrast.
  C8 sum-target control (above) + the random-pair-split leak probe + a
      pair-ORDER invariance check (a reordering of the 351 pair rows must
      reproduce the gap R2 exactly — it is a relabelling, and a mismatch
      would mean the fold bookkeeping is order-dependent).
  C9 extra dials booked by the bank (never gated, not tasked).

HONESTY / CAVEATS BOOKED WITH THE RESULT
  - Carriers are STAGED (E12/E13's caveat, unchanged): this tests staged visual
    carriers of the dials, not arbitrary camera feeds. A KEEP is a floor.
  - Gap R2 and absolute R2 are computed on DIFFERENT sample sets (351 pairs vs
    27 rooms) with DIFFERENT target variance, and each R2 is computed against
    its OWN target's mean, so the two numbers are comparable but not identical
    in difficulty. The direction is NOT assumed: the measured std ratio (gap
    std / absolute std) is booked per dial in gap_composition (C6). At the CPU
    design pass it is 0.89 / 1.39 / 1.44 for mood / volume / presence — the
    volume and presence GAPS have MORE spread than their absolutes (a 3-level
    grid's differences span +-0.7 while its values span 0.15..0.85), so for
    those two dials the gate is not automatically conservative in either
    direction; it is an honest open comparison, and the null95 column (same
    target type, shuffled rooms) is what anchors each dial.
  - Comparator (b) two_abs_loo differences two OUT-OF-FOLD predictions, so it
    is symmetric between the two rooms and shares nothing with the pair
    reader's fitting; the in-sample variant two_abs_fold is reported too and is
    the harder baseline.
  - The absolute comparators use the SAME room-level representation (room-mean
    of still embeddings in the label-free PCA basis, same width k) as the pair
    reader — apples to apples. E12's still-level headline is booked separately.
  - 27 rooms is small: 351 pairs are NOT 351 independent samples (26 pairs per
    fold share a room by construction, and each room enters 26 pairs), which is
    exactly why the outer unit is the room. The effective sample size is ~27
    room-level draws; ridge lambda is selected per fold to respect that.
  - The canonical index order fixes the gap sign; a different orientation would
    negate every gap and leave R2 identical (R2 is invariant to a global sign
    flip of a multi-output target only if the sign is per-target consistent —
    it is here, per dial, across all pairs), so the orientation carries no
    information. Booked as gap_sign_balance.
  - Presence's carrier (drawn boxes) and volume's (noise amount) both move the
    absolute dials' luminance/contrast correlates; the gap reads inherit that
    (C2 names it).

Dev path: `python -m experiments.e18_sauna_plunge_contrast --cpu-only` runs
everything except the encoder — bank, carrier certificate, mirror check, the
351-pair construction with its fold-structure check, the harness self-test,
and a labelled plumbing run of every pair arm on the LABEL-FREE KNOB matrix as
a stand-in feature space (no model, no GPU, no claim).
Never writes to results/ and is not wired into runner.EXP_MOD / QUEUE.md.

Verdict printed as ONE JSON object on stdout (progress on stderr).
Deterministic (seed 2718). CPU-only probe; GPU only for the encoder forwards.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

# BLAS thread cap — E12's reason, verbatim: the probe does thousands of tiny
# ridge solves (27 outer folds x 26 inner folds x 6 lambdas x arms x widths, plus
# 200 null permutations), and the default thread count turns each 39-d solve
# into a thread storm. Must be set BEFORE numpy loads (and this module imports
# E12/E13, which import numpy).
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

# --------------------------------------------------------------------- #
# E12 is imported VERBATIM (the probe) and E13 for the carrier/collector. #
# E18 forks NEITHER the loader, nor the staging, nor the ridge. What it   #
# adds is a new CV unit (rooms, not cells) and a new target (gaps).        #
#   probe    : r2_columns, pca_basis, loro_predict, pick_lambda,          #
#              _ridge_path_pred, _ridge_fit_predict, spearman,            #
#              room_halfsplit_acc                                        #
#   carrier  : knobs_linear, build_bank, carrier_certificate,             #
#              mirror_check, collect_arm, knob_ranges                     #
#   loader   : e9's load_encoder / preflight_guard / N_STILLS             #
# --------------------------------------------------------------------- #
from e12_room_dial_reader import (                            # noqa: E402
    DIAL_NAMES, EXTRA_DIALS, K_PRIMARY, K_STRICT, K_WIDE, LAM_GRID, PERMS,
    R2_FLOOR, SENSITIVITY_FLOOR, _ridge_fit_predict, _ridge_path_pred,
    loro_predict, pca_basis, pick_lambda, r2_columns, room_halfsplit_acc,
    spearman,
)
from e13_nonlinear_dial_reader import (                       # noqa: E402
    build_bank, carrier_certificate, collect_arm, knob_ranges, knobs_linear,
    mirror_check, render_scene,
)
from e9_ijepa_stills import N_STILLS, load_encoder, preflight_guard  # noqa: E402

# --------------------------------------------------------------------- #
# Pre-registered constants (see the module docstring — this IS the       #
# registration; nothing here is chosen after seeing a result)            #
# --------------------------------------------------------------------- #
K_PAIR_PRIMARY = 13      # = min(K_PRIMARY, 27 // 2): E12's room-level rule
K_PAIR_SWEEP = (6, 13, 20)
ARMS = ("concat", "diff", "pair", "pair_inter")
PRIMARY_ARM = "pair"
ARM_TITLES = {
    "concat": "both rooms' embeddings concatenated [z_i, z_j]",
    "diff": "the signed walk only, z_j - z_i",
    "pair": "concat + signed difference [z_i, z_j, z_j - z_i] — PRIMARY",
    "pair_inter": "pair + top-4 inter-room outer products — BOOKED exploratory",
}
N_INTER = 4              # inter-room interaction width (top-4 PCs each -> 16 cols)
PAIR_SENSITIVITY_FLOOR = 0.50   # luminance-GAP read floor (G0b.2)
E12_REPL_FLOOR = R2_FLOOR       # 0.30, E12's per-dial floor (G0e)
LEAK_SPLIT_FRACTION = 0.80      # booked random pair split (never gated)
GATE_HIT_DIALS = 2              # ">= 2 of 3 dials" everywhere
NULL_BEATS = "strict"           # gap_R2 > null95 (not >=)


def log(msg: str) -> None:
    """Progress goes to stderr; stdout is reserved for the JSON verdict."""
    print(f"[e18] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------- #
# Pair construction (the new CV unit)                                    #
# --------------------------------------------------------------------- #
def pairs_from_rooms(n_rooms: int) -> np.ndarray:
    """C(n,2) unordered room pairs in canonical index order (i < j).

    27 rooms -> 351 pairs. The pair IS the sample and the signed gap is
    always target[j] − target[i]; the canonical order freezes the orientation
    (R2 is invariant to a global sign flip, so the choice carries no
    information — booked as gap_sign_balance)."""
    iu = np.triu_indices(int(n_rooms), k=1)
    return np.stack([iu[0], iu[1]], axis=1).astype(int)


def gap_targets(T: np.ndarray, pair_idx: np.ndarray) -> np.ndarray:
    """(n_rooms, D) absolute targets -> (n_pairs, D) signed sauna/plunge gaps."""
    T = np.asarray(T, float)
    return T[pair_idx[:, 1]] - T[pair_idx[:, 0]]


def sum_targets(T: np.ndarray, pair_idx: np.ndarray) -> np.ndarray:
    """Booked control target: the two rooms' SUM (is the pair reader reading
    'both rooms' rather than 'the walk between them'?)."""
    T = np.asarray(T, float)
    return T[pair_idx[:, 1]] + T[pair_idx[:, 0]]


def gap_from_abs(P: np.ndarray, pair_idx: np.ndarray) -> np.ndarray:
    """(n_rooms, D) absolute PREDICTIONS -> gap predictions by differencing."""
    P = np.asarray(P, float)
    return P[pair_idx[:, 1]] - P[pair_idx[:, 0]]


def pair_features(zr: np.ndarray, pair_idx: np.ndarray, arm: str,
                  n_inter: int = N_INTER) -> np.ndarray:
    """Room features -> pair features for one arm (all ridge, multi-output).

    zr : (n_rooms, k) room features (room means in the label-free PCA basis).
    Returns (n_pairs, d_arm) with d_arm = 2k (concat), k (diff),
    3k (pair) or 3k + n_inter^2 (pair_inter).
    """
    a, b = zr[pair_idx[:, 0]], zr[pair_idx[:, 1]]
    if arm == "diff":
        return b - a
    if arm == "concat":
        return np.concatenate([a, b], axis=1)
    base = np.concatenate([a, b, b - a], axis=1)
    if arm == "pair":
        return base
    if arm == "pair_inter":
        m = int(min(n_inter, zr.shape[1]))
        outer = np.einsum("ni,nj->nij", a[:, :m], b[:, :m]).reshape(len(a), m * m)
        return np.concatenate([base, outer], axis=1)
    raise ValueError(f"unknown arm {arm!r}")


def _pairs_touching(pair_idx: np.ndarray, held) -> np.ndarray:
    """True for every pair with at least one room in `held`."""
    h = np.asarray(list(held), int)
    return np.isin(pair_idx, h).any(axis=1)


def pair_loro_folds(pair_idx: np.ndarray, n_rooms: int):
    """Leave-one-ROOM-out folds over pairs (the pre-registered CV unit).

    Yields (held_room, train_mask, test_mask) where test = every pair touching
    the held-out room and train = every pair among the remaining rooms. No
    room ever appears on both sides.
    """
    for h in range(int(n_rooms)):
        te = _pairs_touching(pair_idx, (h,))
        yield h, ~te, te


def fold_structure_check(pair_idx: np.ndarray, n_rooms: int) -> dict:
    """Structural assertion of the CV design (run in both modes).

    Per fold: |test| must be n-1 (one pair per other room), |train| must be
    C(n-1,2), every test pair must contain the held-out room, and no train pair
    may contain it. A failure here means the CV is not room-disjoint and any
    R2 below is meaningless.
    """
    n = int(n_rooms)
    exp_test, exp_train = n - 1, (n - 1) * (n - 2) // 2
    bad_count = bad_test = bad_train = 0
    sizes_te, sizes_tr = [], []
    for h, tr, te in pair_loro_folds(pair_idx, n):
        sizes_te.append(int(te.sum()))
        sizes_tr.append(int(tr.sum()))
        if int(te.sum()) != exp_test or int(tr.sum()) != exp_train:
            bad_count += 1
        if not _pairs_touching(pair_idx[te], (h,)).all():
            bad_test += 1
        if _pairs_touching(pair_idx[tr], (h,)).any():
            bad_train += 1
    return {
        "n_rooms": n, "n_pairs": int(len(pair_idx)), "folds": n,
        "test_pairs_per_fold": exp_test, "train_pairs_per_fold": exp_train,
        "min_test_pairs": min(sizes_te), "min_train_pairs": min(sizes_tr),
        "bad_fold_sizes": bad_count,
        "test_pair_without_held_room": bad_test,
        "train_pair_with_held_room": bad_train,
        "ok": bool(bad_count == 0 and bad_test == 0 and bad_train == 0),
        "note": ("leave-one-ROOM-out on pairs: the held-out room appears in "
                 "every test pair and in no train pair. Leave-one-PAIR-out is "
                 "forbidden (it leaks the rooms of the test pair into "
                 "training and would make the two-absolutes baseline "
                 "undefined)."),
    }


# --------------------------------------------------------------------- #
# The pair probe (ridge + LORO-on-rooms + grouped inner-CV lambda)        #
# --------------------------------------------------------------------- #
def pair_pick_lambda(F: np.ndarray, Yg: np.ndarray, pair_idx: np.ndarray,
                     n_rooms: int, outer_h: int, grid=LAM_GRID) -> float:
    """Lambda by GROUPED inner CV inside one outer fold.

    For each training room g (all rooms except the outer held-out room h), the
    inner-test is every training pair touching g and the inner-train is the
    rest. So the inner CV is grouped on rooms too — the same discipline as the
    outer CV (a pair-level inner CV would select lambda for the wrong task).
    """
    sse = np.zeros(len(grid))
    seen = False
    for g in range(int(n_rooms)):
        if g == outer_h:
            continue
        ite = _pairs_touching(pair_idx, (g,))
        itr = ~ite
        if itr.sum() < 4 or ite.sum() == 0:
            continue
        seen = True
        for j, p in enumerate(_ridge_path_pred(F[itr], Yg[itr], F[ite], grid)):
            sse[j] += float(((Yg[ite] - p) ** 2).sum())
    if not seen:
        return float(grid[0])
    return float(grid[int(np.argmin(sse))])


def pair_loro_predict(F: np.ndarray, Yg: np.ndarray, pair_idx: np.ndarray,
                      n_rooms: int, lam=None, fixed_lam=None,
                      grid=LAM_GRID) -> tuple[np.ndarray, float]:
    """Out-of-fold gap predictions under leave-one-ROOM-out.

    lam=None -> per-fold grouped inner CV; fixed_lam -> a single lambda for
    every fold (used by the permutation null, for cost — E12's convention).
    """
    pred = np.zeros_like(Yg, float)
    lams: list[float] = []
    for h, tr, te in pair_loro_folds(pair_idx, n_rooms):
        if int(tr.sum()) < 4:
            pred[te] = Yg[tr].mean(0) if tr.any() else 0.0
            continue
        if fixed_lam is not None:
            lam_g = float(fixed_lam)
        elif lam is None:
            lam_g = pair_pick_lambda(F[tr], Yg[tr], pair_idx[tr], n_rooms, h, grid)
        else:
            lam_g = float(lam)
        lams.append(lam_g)
        pred[te] = _ridge_fit_predict(F[tr], Yg[tr], F[te], lam_g)
    return pred, (float(np.median(lams)) if lams else float("nan"))


def pair_perm_null(F: np.ndarray, T: np.ndarray, pair_idx: np.ndarray,
                   n_rooms: int, fixed_lam: float, perms: int,
                   seed: int) -> np.ndarray:
    """Room-level shuffle null for the gap read.

    The 27 target triples are permuted ACROSS ROOMS and the gaps are rebuilt
    from the permuted triples; the features (and therefore the embedding
    pairing) are untouched. The probe is rerun at the fold-median lambda for
    cost, exactly E12's room-level null.
    """
    rng = np.random.default_rng(int(seed))
    T = np.asarray(T, float)
    out = np.zeros((int(perms), T.shape[1]))
    for p in range(int(perms)):
        perm = rng.permutation(int(n_rooms))
        Yp = gap_targets(T[perm], pair_idx)
        pred, _ = pair_loro_predict(F, Yp, pair_idx, n_rooms,
                                    fixed_lam=fixed_lam)
        out[p] = r2_columns(Yp, pred)
    return out


# --------------------------------------------------------------------- #
# The two comparators (a) single-room absolute, (b) two-absolutes gap     #
# --------------------------------------------------------------------- #
def abs_room_oof(zr: np.ndarray, T: np.ndarray, n_rooms: int):
    """(a) E12's room-level LORO absolute read: out-of-fold single-room dial
    predictions. Its R2 IS the "single-room absolute-dial R2" comparator, and
    differencing these SAME predictions IS the primary two-absolutes baseline
    — so (a) and (b) share one probe, by design (no third estimator sneaks in).
    """
    pred, lam = loro_predict(zr, np.asarray(T, float), np.arange(int(n_rooms)))
    return pred, lam


def abs_fold_all_rooms(zr: np.ndarray, T: np.ndarray, held: int,
                       n_rooms: int) -> tuple[np.ndarray, float]:
    """One absolute model trained WITHOUT the held-out room, predicting every
    room (including it). Feeds the conservative baseline variant, which is
    in-sample for the non-held room of each test pair."""
    tr = np.arange(int(n_rooms)) != int(held)
    lam = pick_lambda(zr[tr], T[tr], np.arange(int(tr.sum())))
    pred = _ridge_fit_predict(zr[tr], T[tr], zr, lam)
    return pred, float(lam)


def two_abs_fold_gaps(zr: np.ndarray, T: np.ndarray, pair_idx: np.ndarray,
                      n_rooms: int) -> np.ndarray:
    """Conservative two-absolutes baseline: per fold, ONE absolute model
    (trained without the held-out room) predicts both rooms of every test pair,
    and the gap is their difference."""
    out = np.zeros((len(pair_idx), np.asarray(T, float).shape[1]), float)
    for h, _tr, te in pair_loro_folds(pair_idx, n_rooms):
        P, _ = abs_fold_all_rooms(zr, T, h, n_rooms)
        out[te] = gap_from_abs(P, pair_idx[te])
    return out


def pair_split_leak_probe(F: np.ndarray, Yg: np.ndarray, pair_idx: np.ndarray,
                          n_rooms: int, fraction: float = LEAK_SPLIT_FRACTION,
                          seed: int = SEED + 3) -> dict:
    """BOOKED (never gated): the primary arm under a random PAIR split.

    Documented as the wrong split; its inflation (if any) is the run-time
    evidence for the pre-registered room-level CV. Lambda by grouped inner CV
    over rooms on the training pairs, so the split's only flaw is the pair
    sharing, not the lambda choice.
    """
    rng = np.random.default_rng(int(seed))
    n = len(F)
    n_tr = int(round(n * float(fraction)))
    idx = rng.permutation(n)
    tr, te = idx[:n_tr], idx[n_tr:]
    sse = np.zeros(len(LAM_GRID))
    for g in range(int(n_rooms)):
        ite = _pairs_touching(pair_idx[tr], (g,))
        itr = ~ite
        if itr.sum() < 4 or ite.sum() == 0:
            continue
        for j, p in enumerate(_ridge_path_pred(F[tr][itr], Yg[tr][itr],
                                               F[tr][ite], LAM_GRID)):
            sse[j] += float(((Yg[tr][ite] - p) ** 2).sum())
    lam = float(LAM_GRID[int(np.argmin(sse))])
    pred = _ridge_fit_predict(F[tr], Yg[tr], F[te], lam)
    return {"r2": {d: round(float(v), 4)
                   for d, v in zip(DIAL_NAMES, r2_columns(Yg[te], pred))},
            "lambda": lam, "n_train_pairs": int(len(tr)),
            "n_test_pairs": int(len(te)),
            "rooms_shared_between_splits": int(
                len(set(pair_idx[tr].ravel().tolist())
                    & set(pair_idx[te].ravel().tolist()))),
            "note": ("random pair split — rooms appear on BOTH sides (the "
                     "column above), which is why it is booked, not gated.")}


# --------------------------------------------------------------------- #
# Harness self-test (CPU-only, carrier-free, model-free)                  #
# --------------------------------------------------------------------- #
def pair_harness_selftest() -> dict:
    """G0d — the imported pair+LORO path on a synthetic embedding.

    30 synthetic rooms, dials exactly linear in a 40-d embedding with small
    still noise; the gap must read at R2 >= 0.90 per dial, a room-shuffled
    target must collapse below 0.10, and the fold structure must assert clean.
    """
    rng = np.random.default_rng(SEED + 5)
    n_rooms, n_still, d = 30, 6, 40
    T = rng.uniform(-1.0, 1.0, (n_rooms, 3))
    A = rng.standard_normal((3, d))
    Xr = T @ A + 0.05 * rng.standard_normal((n_rooms, d))
    X = np.repeat(Xr, n_still, 0) + 0.02 * rng.standard_normal(
        (n_rooms * n_still, d))
    groups = np.repeat(np.arange(n_rooms), n_still)
    basis, _ = pca_basis(X, 20)
    zr = np.stack([X[groups == g].mean(0) for g in range(n_rooms)]) @ basis

    pair_idx = pairs_from_rooms(n_rooms)
    Yg = gap_targets(T, pair_idx)
    F = pair_features(zr, pair_idx, "pair")
    pred, lam = pair_loro_predict(F, Yg, pair_idx, n_rooms)
    r2_signal = r2_columns(Yg, pred)
    perm = rng.permutation(n_rooms)
    Yp = gap_targets(T[perm], pair_idx)
    pred_p, _ = pair_loro_predict(F, Yp, pair_idx, n_rooms, fixed_lam=lam)
    r2_null = r2_columns(Yp, pred_p)
    struct = fold_structure_check(pair_idx, n_rooms)
    return {
        "r2_gap_signal": [round(float(v), 4) for v in r2_signal],
        "r2_gap_shuffled": [round(float(v), 4) for v in r2_null],
        "r2_gap_signal_min": round(float(r2_signal.min()), 4),
        "r2_gap_shuffled_max": round(float(r2_null.max()), 4),
        "lambda_median": round(float(lam), 6),
        "fold_structure": struct,
        "pass": bool(r2_signal.min() >= 0.90 and r2_null.max() < 0.10
                     and struct["ok"]),
        "note": ("carrier-free, model-free check of pca_basis -> "
                 "pair_features -> pair_loro_predict -> pair_pick_lambda -> "
                 "r2_columns on a synthetic linear dial signal."),
    }


# --------------------------------------------------------------------- #
# Report helpers                                                         #
# --------------------------------------------------------------------- #
def r2_dict(v) -> dict:
    return {d: round(float(x), 4) for d, x in zip(DIAL_NAMES, np.asarray(v))}


def gap_composition(T: np.ndarray, pair_idx: np.ndarray,
                    labels: np.ndarray) -> dict:
    """C6 — the gap targets' own shape: histogram, sign balance, variance vs
    the absolutes', and the label-gap Spearman (does the staged gap move the
    elephant's own readings of the two rooms?)."""
    T = np.asarray(T, float)
    Yg = gap_targets(T, pair_idx)
    Lg = gap_targets(np.asarray(labels, float), pair_idx)
    out = {}
    for i, d in enumerate(DIAL_NAMES):
        vals, counts = np.unique(np.round(Yg[:, i], 6), return_counts=True)
        out[d] = {
            "unique_values": [round(float(v), 4) for v in vals],
            "counts": [int(c) for c in counts],
            "std_gap": round(float(Yg[:, i].std()), 4),
            "std_absolute": round(float(T[:, i].std()), 4),
            "frac_zero": round(float((np.abs(Yg[:, i]) < 1e-9).mean()), 4),
            "frac_positive": round(float((Yg[:, i] > 1e-9).mean()), 4),
            "frac_negative": round(float((Yg[:, i] < -1e-9).mean()), 4),
            "spearman_target_gap_vs_label_gap": round(
                spearman(Yg[:, i], Lg[:, i]), 4),
        }
    return out


# --------------------------------------------------------------------- #
# CPU-only mode (no model, no GPU): the plumbing test                    #
# --------------------------------------------------------------------- #
def cpu_only() -> dict:
    """Bank + pairwise construction + carrier certificate + self-test, no
    model. Also runs EVERY pair arm on the label-free KNOB matrix as a stand-in
    feature space — plumbing only, explicitly NOT evidence for the claim."""
    st = pair_harness_selftest()
    bank = build_bank(1)
    n_rooms = len(bank)
    targets = np.stack([r["target"] for r in bank])
    labels = np.stack([r["label"] for r in bank])

    K_L = {r["name"]: knobs_linear(float(r["target"][0]), float(r["target"][1]),
                                   float(r["target"][2])) for r in bank}
    mirror = mirror_check(bank, {"L": K_L})
    knob_mat = np.stack([K_L[r["name"]] for r in bank])
    cert_dials, cert = carrier_certificate(knob_mat, targets)

    pair_idx = pairs_from_rooms(n_rooms)
    Yg = gap_targets(targets, pair_idx)
    struct = fold_structure_check(pair_idx, n_rooms)

    plumbing = {}
    for arm in ARMS:
        plumbing[arm] = {}
        for k in K_PAIR_SWEEP:
            F = pair_features(knob_mat[:, :k], pair_idx, arm)
            pred, lam = pair_loro_predict(F, Yg, pair_idx, n_rooms)
            plumbing[arm][str(k)] = {
                "n_features": int(F.shape[1]),
                "r2_gap_knobspace": r2_dict(r2_columns(Yg, pred)),
                "lambda_median": round(float(lam), 6),
            }

    out = {
        "experiment": "E18 sauna/plunge contrast read",
        "mode": "cpu-only (no model, no GPU)",
        "seed": SEED,
        "dial_names": DIAL_NAMES,
        "extra_dials_available": EXTRA_DIALS,
        "rooms": n_rooms,
        "pairs": int(len(pair_idx)),
        "pairs_per_fold": {"test": n_rooms - 1, "train": (n_rooms - 1) * (n_rooms - 2) // 2},
        "k_pair_primary": K_PAIR_PRIMARY,
        "k_pair_sweep": list(K_PAIR_SWEEP),
        "arms": list(ARMS),
        "fold_structure": struct,
        "harness_selftest": st,
        "arm_L_mirror_check": mirror,
        "carrier_certificate": {
            "summary": cert, "per_dial": cert_dials,
            "knob_ranges": knob_ranges(knob_mat),
            "gate_used": ("liveness half only (injective + >=2/3 dials live) "
                          "plus the mirror check; non-affinity deliberately "
                          "NOT gated (curvature 0.000 is E12's linear carrier "
                          "by construction)"),
        },
        "staging_fidelity_spearman_target_vs_label": {
            d: round(spearman(targets[:, i], labels[:, i]), 4)
            for i, d in enumerate(DIAL_NAMES)},
        "gap_composition": gap_composition(targets, pair_idx, labels),
        "sample_lavfi_source_room01": render_scene(
            K_L[bank[0]["name"]], bank[0]["seed"]),
        "plumbing_only_not_evidence": {
            "feature_space": ("the 7-d label-free KNOB matrix (room -> scene "
                              "parameters), not I-JEPA embeddings — the "
                              "embedding space needs the GPU run. Widths k > 7 "
                              "therefore clamp to the matrix's 7 columns "
                              "(n_features saturates at 3*7 = 21), so this "
                              "block exercises the code path and the fold "
                              "bookkeeping ONLY; the R2 values are a "
                              "near-affine sanity read, not a claim."),
            "arms": plumbing,
        },
        "note": ("No verdict in CPU-only mode. Watch: fold_structure must be "
                 "clean (27 folds, 26 test pairs, 325 train pairs each), the "
                 "harness self-test must read the synthetic gap at >= 0.90 and "
                 "collapse on the room shuffle, the mirror check must match "
                 "e12.stage_source byte-for-byte, and the liveness half of the "
                 "carrier certificate must pass (non-affinity is NOT gated "
                 "here — E18 uses E12's linear carrier)."),
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
        out = {"experiment": "E18 sauna/plunge contrast read",
               "verdict": "ABORTED", "reason": reason,
               "guard_preflight": guard_info}
        print(json.dumps(out, indent=2))
        return out

    base = {
        "experiment": "E18 sauna/plunge contrast read", "seed": SEED,
        "dial_names": DIAL_NAMES, "extra_dials": EXTRA_DIALS,
        "primary_arm": PRIMARY_ARM, "arm_titles": ARM_TITLES,
        "k_pair_primary": K_PAIR_PRIMARY, "k_pair_sweep": list(K_PAIR_SWEEP),
        "guard_preflight": guard_info,
        "claim": ("the signed sauna/plunge gap (target_j - target_i) is read "
                  "better from embedding-pair features than from either room's "
                  "absolute dials or from differencing the two absolutes"),
    }

    # G0d — cheapest gate first: if the imported probe path is broken, nothing
    # else is interpretable (and it is model-free).
    selftest = pair_harness_selftest()
    log(f"harness self-test: signal_min={selftest['r2_gap_signal_min']} "
        f"shuffled_max={selftest['r2_gap_shuffled_max']} pass={selftest['pass']}")

    # Bank + carrier + certificate — all CPU, all before the model.
    bank = build_bank(1)
    n_rooms = len(bank)
    targets = np.stack([r["target"] for r in bank])
    labels = np.stack([r["label"] for r in bank])
    K_L = {r["name"]: knobs_linear(float(r["target"][0]), float(r["target"][1]),
                                   float(r["target"][2])) for r in bank}
    mirror = mirror_check(bank, {"L": K_L})
    knob_mat = np.stack([K_L[r["name"]] for r in bank])
    cert_dials, cert = carrier_certificate(knob_mat, targets)
    log(f"bank: {n_rooms} rooms; certificate live={cert['n_dials_live']}/3 "
        f"injective={cert['injectivity']['injective']} "
        f"curvature={cert['mean_curvature']} mirror={mirror['match']}")

    fid = {d: round(spearman(targets[:, i], labels[:, i]), 4)
           for i, d in enumerate(DIAL_NAMES)}
    fid_pass = bool(sum(1 for d in DIAL_NAMES if fid[d] >= 0.5)
                    >= GATE_HIT_DIALS)
    cert_ok = bool(cert["live_pass"] and cert["injectivity"]["injective"]
                   and mirror["match"])

    pair_idx = pairs_from_rooms(n_rooms)
    struct = fold_structure_check(pair_idx, n_rooms)
    Ygap = gap_targets(targets, pair_idx)

    def bail(verdict: str, why: str, extra: dict | None = None) -> dict:
        out = dict(base)
        out.update({
            "verdict": verdict, "verdict_reason": why,
            "harness_selftest": selftest,
            "fold_structure": struct,
            "carrier_certificate": {"summary": cert, "per_dial": cert_dials,
                                    "knob_ranges": knob_ranges(knob_mat)},
            "arm_L_mirror_check": mirror,
            "staging_fidelity_spearman_target_vs_label": fid,
        })
        if extra:
            out.update(extra)
        print(json.dumps(out, indent=2))
        return out

    if not selftest["pass"]:
        return bail("INVALID_HARNESS",
                    "G0d: the imported pair+LORO probe failed the synthetic "
                    "self-test (or the fold structure is not room-disjoint)")
    if not struct["ok"]:
        return bail("INVALID_HARNESS",
                    "G0d: the leave-one-ROOM-out pair folds are not "
                    "room-disjoint / have the wrong sizes")
    if not fid_pass:
        return bail("INVALID_STAGING",
                    "G0a: the staged scripts did not move >= 2/3 dials")
    if not cert_ok:
        return bail("INVALID_STAGING",
                    "G0c: the staged carrier failed its liveness certificate "
                    "(dead or non-injective carrier, or the Arm-L mirror "
                    "check failed) — the arm tested nothing")
    if n_rooms < 8:
        return bail("ABORTED",
                    f"only {n_rooms} rooms — grouped CV would be meaningless")

    import torch
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    log(f"loading I-JEPA ({dev})...")
    try:
        model_used, model, processor, load_notes = load_encoder(dev)
    except Exception as e:  # noqa: BLE001
        return bail("ABORTED", f"model load failed: {e}")
    log(f"using {model_used}")

    # E13's collector verbatim, on the Arm-L carrier (E12's staging).
    try:
        X, Ylab, _Yt, groups, lum, pix = collect_arm(
            "L", {"L": K_L}, bank, model, processor, dev, torch)
    except Exception as e:  # noqa: BLE001
        return bail("ABORTED", f"frame/embed failed: {e}")

    # Room features: E12's convention — label-free PCA on the stills, then the
    # room mean taken IN that space.
    basis, evr = pca_basis(X, K_WIDE)
    Xrm = np.stack([X[groups == g].mean(0) for g in range(n_rooms)])
    Xr = Xrm @ basis
    zc = X @ basis[:, :K_PRIMARY]                 # still-level k=64 (E12 space)
    room_lum = np.stack([lum[groups == g].mean() for g in range(n_rooms)])
    room_pix = np.stack([pix[groups == g].mean(0) for g in range(n_rooms)])
    log(f"features: stills={X.shape} room_features={Xr.shape}")

    # G0b.1 — E12's sensitivity control verbatim (still-level luminance).
    lum_col = lum.reshape(-1, 1).astype(np.float64)
    pred_lum, _ = loro_predict(zc, lum_col, groups)
    r2_lum_still = float(r2_columns(lum_col, pred_lum)[0])
    # G0e — in-run replication of E12's own still-level gate (k=64 primary,
    # k=16 booked) on E12's exact cell-level LORO path.
    pred_abs_still, _ = loro_predict(zc, Ylab, groups)
    r2_abs_still = r2_columns(Ylab, pred_abs_still)
    zc16 = X @ basis[:, :K_STRICT]
    pred_abs_still16, _ = loro_predict(zc16, Ylab, groups)
    r2_abs_still16 = r2_columns(Ylab, pred_abs_still16)
    e12_repl = {d: round(float(r2_abs_still[i]), 4)
                for i, d in enumerate(DIAL_NAMES)}
    e12_repl16 = {d: round(float(r2_abs_still16[i]), 4)
                  for i, d in enumerate(DIAL_NAMES)}
    e12_repl_pass = bool(sum(1 for d in DIAL_NAMES
                             if e12_repl[d] >= E12_REPL_FLOOR)
                         >= GATE_HIT_DIALS)
    log(f"G0b.1 luminance(still,k64)={r2_lum_still:.4f}  "
        f"G0e E12 repl(k64)={e12_repl}")

    # ---------------------------------------------------------------- #
    # Comparators (a) single-room absolute and (b) two-absolutes gap    #
    # (same room-level representation and width as the pair reader)     #
    # ---------------------------------------------------------------- #
    def comparators(k: int) -> dict:
        zr = Xr[:, :k]
        abs_pred, lam_abs = abs_room_oof(zr, targets, n_rooms)
        r2_abs = r2_columns(targets, abs_pred)
        base_loo = gap_from_abs(abs_pred, pair_idx)
        r2_base_loo = r2_columns(Ygap, base_loo)
        base_fold = two_abs_fold_gaps(zr, targets, pair_idx, n_rooms)
        r2_base_fold = r2_columns(Ygap, base_fold)
        return {
            "single_room_abs_r2": r2_dict(r2_abs),
            "two_abs_loo_r2": r2_dict(r2_base_loo),
            "two_abs_fold_r2": r2_dict(r2_base_fold),
            "lambda_median_abs": round(float(lam_abs), 6)
            if lam_abs == lam_abs else None,
        }

    comp = {str(k): comparators(k) for k in K_PAIR_SWEEP}
    comp_primary = comp[str(K_PAIR_PRIMARY)]
    log(f"(a) single_room_abs_r2@{K_PAIR_PRIMARY}={comp_primary['single_room_abs_r2']}")
    log(f"(b) two_abs_loo_r2@{K_PAIR_PRIMARY}={comp_primary['two_abs_loo_r2']}")

    # ---------------------------------------------------------------- #
    # G0b.2 — the pair machinery's own sensitivity control: luminance GAP #
    # ---------------------------------------------------------------- #
    Ylum_gap = gap_targets(room_lum.reshape(-1, 1), pair_idx)
    F_prim = pair_features(Xr[:, :K_PAIR_PRIMARY], pair_idx, PRIMARY_ARM)
    pred_lum_gap, lam_lum_gap = pair_loro_predict(
        F_prim, Ylum_gap, pair_idx, n_rooms)
    r2_lum_gap = float(r2_columns(Ylum_gap, pred_lum_gap)[0])
    null_lum_gap = pair_perm_null(F_prim, room_lum.reshape(-1, 1), pair_idx,
                                  n_rooms, lam_lum_gap, PERMS, SEED + 31)
    null95_lum_gap = float(np.percentile(null_lum_gap[:, 0], 95))
    pair_sens_pass = bool(r2_lum_gap >= PAIR_SENSITIVITY_FLOOR
                          and r2_lum_gap > null95_lum_gap)
    log(f"G0b.2 luminance-GAP(pair,k={K_PAIR_PRIMARY})={r2_lum_gap:.4f} "
        f"null95={null95_lum_gap:.4f} pass={pair_sens_pass}")

    if not (r2_lum_still >= SENSITIVITY_FLOOR and pair_sens_pass):
        return bail("INVALID_HARNESS",
                    f"G0b: sensitivity failed (still-level luminance R2 "
                    f"{r2_lum_still:.4f} < {SENSITIVITY_FLOOR}, or pair-level "
                    f"luminance-gap R2 {r2_lum_gap:.4f} < "
                    f"{PAIR_SENSITIVITY_FLOOR}) — the probe cannot read a "
                    "signal certainly present in the frames",
                    {"g0b_sensitivity": {
                        "r2_luminance_still_k64": round(r2_lum_still, 4),
                        "floor_still": SENSITIVITY_FLOOR,
                        "r2_luminance_gap_pair": round(r2_lum_gap, 4),
                        "floor_pair_gap": PAIR_SENSITIVITY_FLOOR,
                        "null95_pair_gap": round(null95_lum_gap, 4)}})
    if not e12_repl_pass:
        return bail("INVALID_HARNESS",
                    "G0e: E12's own still-level dial read did not replicate in "
                    "this run — the (a)/(b) comparators would be meaningless",
                    {"g0e_e12_replication": e12_repl,
                     "floor": E12_REPL_FLOOR})

    # ---------------------------------------------------------------- #
    # The arm sweep: gap targets (primary), sum target (booked control)  #
    # ---------------------------------------------------------------- #
    Ysum = sum_targets(targets, pair_idx)
    sweep: dict = {}
    for arm in ARMS:
        sweep[arm] = {}
        for k in K_PAIR_SWEEP:
            F = pair_features(Xr[:, :k], pair_idx, arm)
            pred, lam = pair_loro_predict(F, Ygap, pair_idx, n_rooms)
            r2_gap = r2_columns(Ygap, pred)
            pred_s, lam_s = pair_loro_predict(F, Ysum, pair_idx, n_rooms)
            r2_sum = r2_columns(Ysum, pred_s)
            rid = np.random.default_rng(SEED + 7 + k)
            idx = rid.permutation(len(pair_idx))
            pred_o, _ = pair_loro_predict(F[idx], Ygap[idx], pair_idx[idx],
                                          n_rooms)
            r2_o = r2_columns(Ygap[idx], pred_o)
            # C8 — pair-ORDER invariance: reordering the 351 pair rows is a
            # relabelling, so the gap R2 must be reproduced exactly. A mismatch
            # means the fold bookkeeping (not the signal) is order-dependent.
            order_gap = float(np.max(np.abs(r2_o - r2_gap)))
            sweep[arm][str(k)] = {
                "n_features": int(F.shape[1]),
                "r2_gap": r2_dict(r2_gap),
                "r2_sum_control": r2_dict(r2_sum),
                "r2_gap_pair_order_invariance": r2_dict(r2_o),
                "pair_order_invariance_max_abs_diff": round(order_gap, 12),
                "lambda_median_gap": round(float(lam), 6),
                "lambda_median_sum": round(float(lam_s), 6),
                "mean_r2_gap": round(float(np.mean(r2_gap)), 4),
            }
            log(f"arm {arm} k={k}: mean_gap_r2={sweep[arm][str(k)]['mean_r2_gap']} "
                f"gap={sweep[arm][str(k)]['r2_gap']} sum={sweep[arm][str(k)]['r2_sum_control']}")

    primary = sweep[PRIMARY_ARM][str(K_PAIR_PRIMARY)]
    prim_gap = primary["r2_gap"]

    # Permutation null for the PRIMARY arm at the primary width.
    null = pair_perm_null(F_prim, targets, pair_idx, n_rooms,
                          primary["lambda_median_gap"], PERMS, SEED + 11)
    null95 = {d: round(float(np.percentile(null[:, i], 95)), 4)
              for i, d in enumerate(DIAL_NAMES)}
    perm_p = {d: round(float((null[:, i] >= prim_gap[d]).mean()), 4)
              for i, d in enumerate(DIAL_NAMES)}

    # C1 — raw-pixel control through the SAME pair probe. The 144-d room-mean
    # pixel vector is PCA-reduced (label-free) to the SAME width as the
    # embedding reader (k = 13) so the control is apples-to-apples and the pair
    # design (3k = 39 features) stays overdetermined by the 325 training pairs.
    pix_basis, pix_evr = pca_basis(room_pix, K_PAIR_PRIMARY)
    F_pix = pair_features(room_pix @ pix_basis[:, :K_PAIR_PRIMARY], pair_idx,
                          PRIMARY_ARM)
    pred_pix, _ = pair_loro_predict(F_pix, Ygap, pair_idx, n_rooms)
    pix_gap = r2_dict(r2_columns(Ygap, pred_pix))

    # C3/C8 — booked leak probe (random pair split).
    leak = pair_split_leak_probe(F_prim, Ygap, pair_idx, n_rooms)

    # C5 — E12's room-identity sanity check (half-split, chance 1/27).
    id_acc = room_halfsplit_acc(zc, groups)

    # C2 — luminance-gap Spearman.
    lum_spear = {d: round(spearman(room_lum, targets[:, i]), 4)
                 for i, d in enumerate(DIAL_NAMES)}

    # ---------------------------------------------------------------- #
    # G1/G2/G3 — the pre-registered contrast gate                        #
    # ---------------------------------------------------------------- #
    exceed, beat_base, beats_conservative = {}, {}, {}
    for d in DIAL_NAMES:
        exceed[d] = bool(prim_gap[d] > comp_primary["single_room_abs_r2"][d]
                         and prim_gap[d] > comp_primary["two_abs_loo_r2"][d]
                         and prim_gap[d] > null95[d])
        beat_base[d] = bool(prim_gap[d] > comp_primary["two_abs_loo_r2"][d])
        beats_conservative[d] = bool(
            prim_gap[d] > comp_primary["two_abs_fold_r2"][d])
    n_exceed = int(sum(1 for d in DIAL_NAMES if exceed[d]))
    n_beat_base = int(sum(1 for d in DIAL_NAMES if beat_base[d]))
    mean_gap = float(np.mean([prim_gap[d] for d in DIAL_NAMES]))
    mean_null = float(np.mean([null95[d] for d in DIAL_NAMES]))

    if n_exceed >= GATE_HIT_DIALS:
        verdict, why = "KEEP", (
            f"contrast read beats BOTH the single-room absolute R2 and the "
            f"two-absolutes baseline on {n_exceed}/3 dials — super-additive")
    elif n_beat_base <= 1:
        verdict, why = "KILL", (
            f"the gap read beats the two-absolutes baseline on only "
            f"{n_beat_base}/3 dials — the contrast is just the two absolutes "
            "differenced (no super-additivity)")
    else:
        verdict, why = "INCONCLUSIVE", (
            f"{n_beat_base}/3 dials beat the two-absolutes baseline but only "
            f"{n_exceed}/3 clear BOTH comparators and the null")

    deltas_abs = {d: round(prim_gap[d] - comp_primary["single_room_abs_r2"][d], 4)
                  for d in DIAL_NAMES}
    deltas_base = {d: round(prim_gap[d] - comp_primary["two_abs_loo_r2"][d], 4)
                   for d in DIAL_NAMES}

    out = dict(base)
    out.update({
        "device": dev, "model": model_used, "load_notes": load_notes,
        "rooms": n_rooms, "pairs": int(len(pair_idx)),
        "stills_per_room": N_STILLS, "cells": int(X.shape[0]),
        "emb_dim": int(X.shape[1]),
        "pca_evr_k16": round(float(evr[:K_STRICT].sum()), 4),
        "pca_evr_k64": round(float(evr[:K_PRIMARY].sum()), 4),
        "pca_evr_k256": round(float(evr[:K_WIDE].sum()), 4),
        "label_stats": {d: {"min": round(float(labels[:, i].min()), 4),
                            "max": round(float(labels[:, i].max()), 4),
                            "std": round(float(labels[:, i].std()), 4)}
                        for i, d in enumerate(DIAL_NAMES)},
        "harness_selftest": selftest,
        "fold_structure": struct,
        "cv_design": {
            "outer_unit": "room (leave-one-ROOM-out on pairs)",
            "folds": n_rooms,
            "test_pairs_per_fold": n_rooms - 1,
            "train_pairs_per_fold": (n_rooms - 1) * (n_rooms - 2) // 2,
            "inner_lambda": "grouped inner CV on the training rooms "
                            "(e12._ridge_path_pred, 6 lambdas)",
            "pca_basis": "label-free, fit once on all still embeddings, frozen "
                         "for every fold and arm (E12's convention)",
            "null": f"{PERMS} room-level target shuffles, gaps rebuilt from "
                    "the permuted triples, fixed fold-median lambda",
            "pair_level_split": "forbidden (booked leak probe below)",
        },
        "comparators": comp,
        "primary": {
            "arm": PRIMARY_ARM, "k": K_PAIR_PRIMARY,
            "r2_gap": prim_gap, "n_features": primary["n_features"],
        },
        "arms": sweep,
        "perm_null95_gap_primary": null95,
        "perm_p_gap_primary": perm_p,
        "deltas_vs_single_abs": deltas_abs,
        "deltas_vs_two_abs": deltas_base,
        "gap_composition": gap_composition(targets, pair_idx, labels),
        "controls": {
            "raw_pixel_pair_gap_r2": pix_gap,
            "raw_pixel_k_used": K_PAIR_PRIMARY,
            "raw_pixel_pca_evr": round(float(pix_evr.sum()), 4),
            "luminance_gap_spearman_target": lum_spear,
            "r2_luminance_still_k64": round(r2_lum_still, 4),
            "r2_luminance_gap_pair_primary": round(r2_lum_gap, 4),
            "null95_luminance_gap_pair": round(null95_lum_gap, 4),
            "e12_still_k64_abs_r2": e12_repl,
            "e12_still_k16_abs_r2": e12_repl16,
            "e12_replication_floor": E12_REPL_FLOOR,
            "room_identity_acc": round(float(id_acc), 4),
            "room_identity_chance": round(1.0 / n_rooms, 4),
            "pair_split_leak_probe": leak,
            "extra_dials_booked": {
                d: {"min": round(float(min(r["extra"][d] for r in bank)), 4),
                    "max": round(float(max(r["extra"][d] for r in bank)), 4)}
                for d in EXTRA_DIALS},
        },
        "carrier_certificate": {"summary": cert, "per_dial": cert_dials,
                                "knob_ranges": knob_ranges(knob_mat),
                                "gate_used": ("liveness half only "
                                              "(injective + >=2/3 dials live) "
                                              "+ mirror check; non-affinity "
                                              "NOT gated — E12's linear "
                                              "carrier by construction")},
        "arm_L_mirror_check": mirror,
        "staging_fidelity_spearman_target_vs_label": fid,
        "gates": {
            "g0d_harness_selftest": {"pass": selftest["pass"],
                                     "signal_min": selftest["r2_gap_signal_min"],
                                     "shuffled_max": selftest["r2_gap_shuffled_max"]},
            "g0a_staging_fidelity": {"floor": 0.5, "measured": fid,
                                     "pass": fid_pass},
            "g0c_carrier_certificate": {"live_pass": cert["live_pass"],
                                        "injective": cert["injectivity"]["injective"],
                                        "mirror_match": mirror["match"],
                                        "mean_curvature": cert["mean_curvature"],
                                        "pass": cert_ok},
            "g0b_sensitivity": {"r2_luminance_still_k64": round(r2_lum_still, 4),
                                "floor_still": SENSITIVITY_FLOOR,
                                "r2_luminance_gap_pair": round(r2_lum_gap, 4),
                                "floor_pair_gap": PAIR_SENSITIVITY_FLOOR,
                                "pass": bool(r2_lum_still >= SENSITIVITY_FLOOR
                                             and pair_sens_pass)},
            "g0e_e12_replication": {"measured": e12_repl,
                                    "floor": E12_REPL_FLOOR,
                                    "pass": e12_repl_pass},
            "g1_contrast": {
                "exceed_both_and_null": exceed,
                "n_exceed": n_exceed,
                "beats_two_abs_baseline": beat_base,
                "n_beat_baseline": n_beat_base,
                "beats_conservative_baseline_booked": beats_conservative,
                "gate_dials_required": GATE_HIT_DIALS,
                "null_beats": NULL_BEATS,
                "mean_gap_r2": round(mean_gap, 4),
                "mean_null95": round(mean_null, 4),
            },
        },
        "verdict": verdict,
        "verdict_reason": why,
        "data_needed": [
            "ffmpeg ~/.local/bin/ffmpeg (lavfi chain, same as E12/E13)",
            "facebook/ijepa_vith16_1k fp16 on the RTX 4050 (E9 loader, "
            "imported via E12/E13)",
            "elephant package importable (DialBank = labels)",
            f"{n_rooms} rooms x {N_STILLS} stills = {n_rooms * N_STILLS} "
            "forwards ≈ 3-5 min GPU (one arm; E18 adds no second carrier)",
            "GPU free (guard preflight in-process)",
        ],
        "note": (
            "E18 changes the TARGET and the CV unit, nothing else: E12's bank "
            "and probe, E13's carrier/collector, one frozen I-JEPA. The target "
            "is the signed sauna/plunge gap target_j - target_i for each of the "
            "351 room pairs; the CV is leave-one-ROOM-out on pairs (a held-out "
            "room appears in every test pair and in no train pair), which is "
            "the only split under which 'read the gap involving an UNSEEN "
            "room' is the question asked. KEEP = the gap read beats both the "
            "single-room absolute R2 and the two-absolutes baseline (and its "
            "null) on >= 2/3 dials — super-additivity: the walk carries signal "
            "the rooms do not. KILL = it beats the baseline on <= 1 dial — the "
            "contrast is just the two absolutes differenced. INVALID_STAGING "
            "(dead/non-injective carrier, or the scripts stopped moving the "
            "dials) and INVALID_HARNESS (blind probe, broken fold structure, or "
            "E12's own read failing to replicate) are never KILLs. SCOPE: "
            "staged carriers (E12/E13's caveat unchanged) — a KEEP is a floor. "
            "Target difficulty is NOT assumed to favour the baseline: the "
            "measured gap-vs-absolute std ratio is booked per dial in "
            "gap_composition (volume/presence gaps are WIDER than their "
            "absolutes), and the room-shuffle null95 anchors every dial."),
    })
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
