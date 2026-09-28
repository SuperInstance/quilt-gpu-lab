#!/usr/bin/env python3
"""X9 — presence-depth: can a NONLINEAR reader buy the stats battery the
presence generalization it lacked? (Wave-2 escalation, booked by X3.)

CLAIM UNDER TEST (the day's one surviving deep claim, concrete + falsifiable)
  X3 (2026-09-28) parity-tested E12's I-JEPA dial-read against a 24-dim
  classical image-statistics battery on the same 27-room bank, same LORO
  ridge, same labels. Result: volume is parity (gap 0.008 — decoration),
  mood flips to the battery, but PRESENCE survived as a GENERALIZATION win:
      room-level LORO   battery 0.028  vs  I-JEPA 0.937
  X3's own caveat: the battery was shot with a LINEAR reader only. Before
  "classical statistics cannot buy presence across unseen rooms" hardens
  into a wall, the battery gets its escalation: the SAME 24-d battery read
  by E13b's fixed NONLINEAR reader (sklearn MLPRegressor, hidden 16, ReLU,
  LBFGS, alpha 0.1) under the SAME room-level LORO. If a nonlinear reader
  still cannot generalize presence off battery features while the embedding
  holds, the depth claim hardens; if it can, presence too falls to
  statistics.

ARMS — one bank, two feature sets, two readers, ONE protocol (fair by import)
  features (X3's, verbatim by import):
    battery : the 24-d classic-statistics battery (x3_stats_battery.
              stats_battery) on the native 160x90 stills — colour moments,
              gray percentiles, Michelson contrast, Fourier band powers,
              Sobel edge density/magnitude, spatial autocorrelations.
    jepa    : frozen I-JEPA (facebook/ijepa_vith16_1k, fp16, mean-pooled,
              L2-norm) -> E12's label-free PCA basis on ALL stills, k=64
              (K_PRIMARY). X3's jepa space exactly.
  readers:
    ridge   : E12's LORO ridge (per-fold inner-CV lambda) — X3's numbers,
              re-run here as the CONTROL + drift check vs X3's published.
    mlp     : E13b's fixed reader, by import: mlp_loro = per-fold sklearn
              MLPRegressor(hidden=16, relu, lbfgs, alpha=0.1, max_iter=2000),
              per-fold input/target standardization on train rooms only.

ROOM-LEVEL CONVENTIONS (both honest, both reported; the gate takes the MAX)
  avg-pred : E13b's pre-registered room-level check — MLP trains at still
             level under LORO, held-out still predictions are ROOM-AVERAGED,
             R2 on the 27 room points. (An MLP gradient-trained on 26
             room-mean rows was ruled dishonest by E13b's registration.)
  refit    : the battery's charity arm — LORO AT room granularity: ridge-
             style room-mean features (27x24), train on 26 rooms, predict
             the held-out room, hidden-16/alpha-0.1 MLP. Small-n training is
             exactly the battery's best shot at the room-level gap, so it
             gets the attempt (LORO keeps it honest, just variance-heavy).
  GATE INPUT: arm room-level MLP presence := max(avg-pred, refit). The null
  gets EVERY chance: WALL requires BOTH conventions to fail.

PRE-REGISTERED GATES (fixed before running; this file IS the registration)
  G0d  ridge harness self-test : e13.harness_selftest pass, else
      INVALID_HARNESS.
  G0d' MLP reader self-test    : e13b.mlp_selftest pass (linear LORO >= 0.90,
      shuffled < 0.10, nonlinear capability >= 0.5 on >= 2/3 while ridge
      stays < 0.30 on >= 2/3, null smoke < 0.20), else INVALID_READER.
  G0a  staging fidelity        : Spearman(target, elephant_label) >= 0.5 for
      >= 2/3 dials (E12/X3 verbatim), else INVALID_STAGING.
  G0b  battery sensitivity     : battery reads per-still mean luminance at
      LORO R2 >= 0.90 (X3 verbatim), else INVALID_HARNESS.
  Gc   reader non-affinity     : mean normalized second-difference curvature
      of the trained MLPs >= e13b.MLP_CURV_FLOOR (0.02) on >= 2/3 dials for
      BOTH arms (E13b's Gc) — an affine reader cannot arbitrate; else
      INCONCLUSIVE (reason READER_AFFINE).
  G1   THE GATE (presence is the headline; volume/mood reported, not gated):
      let B := room-level battery-MLP presence (max convention),
          E := room-level jepa-MLP presence (max convention).
      FALLS (depth dies)      : B >= 0.7 * E   — a nonlinear reader lifts
          the battery to within 30% relative of the embedding; presence
          falls to statistics, X3's surviving claim is dead.
      WALL  (depth hardens)   : B < 0.30 AND E >= 0.80 — the battery fails
          at room-level presence EVEN nonlinearly while the embedding reads
          it comfortably; the gap is in the features, not the reader.
      INCONCLUSIVE            : otherwise.
      Non-overlap: when E >= 0.80, FALLS implies B >= 0.56 > 0.30, so the
      two verdicts are mutually exclusive; FALLS is evaluated first (the
      claim-killer outranks the claim-hardener). If E < 0.80, WALL is
      unavailable by construction and the ladder degrades gracefully to
      FALLS-or-INCONCLUSIVE.

CONTROLS / BOOKED (never gated)
  C1 ridge drift check : battery-ridge and jepa-ridge rows (still + room)
      must reproduce X3's published room-level presence (0.028 / 0.937);
      X3_PUBLISHED booked verbatim in the JSON.
  C2 MLP permutation nulls : PERMS_MLP (default 100) room-level label
      shuffles per feature set (E12's convention, MLP edition via
      e13b.mlp_null verbatim: shuffled labels expanded to stills, still-
      level LORO MLP, pooled R2 — E13b's booked null convention), compared
      against the still-level MLP reads; null95 + permutation p.
  C3 still-level rows : the four-way table at still level too (the wall is
      specifically a room-level claim; the still-level table shows what the
      nonlinear reader changes where fitting is easy).
  C4 curvature certificates : per-arm MLP curvature (non-affinity) with the
      floor, feeding Gc.
  C5 jepa k16 line : booked ridge line (E12's K_STRICT), still-level only.

DATA THE GATE NEEDS
  - ffmpeg ~/.local/bin/ffmpeg (E12's lavfi chain), elephant package
    importable (labels), facebook/ijepa_vith16_1k fp16 on the RTX 4050
    (E9 loader; preflight_guard re-checked in-process).
  - 27 rooms x 12 stills = 324 encoder forwards (~5 min GPU) + CPU probes
    (ridge LORO minutes; MLP nulls ~6-8 min per feature set at 100 perms).

HONESTY / CAVEATS BOOKED WITH THE RESULT
  - Staged carriers (the standing E12-family caveat); X9 tests whether
    X3's surviving presence claim survives the battery's best nonlinear
    reader, not natural feeds.
  - 27 rooms: room-level R2 lives on 27 points; the refit convention trains
    on 26 rows per fold (variance-heavy — hence the max-convention charity
    and the reported per-convention numbers).
  - 0.30 / 0.80 / 0.7x are this file's own pre-registration, fixed before
    the run; they are strict enough that WALL requires a clean failure.
  - The MLP null budget (100) is below E13b's 200; nulls are controls here,
    never gated (X9_PERMS_MLP env override exists for a rerun at 200).

Verdict printed as ONE JSON object on stdout (progress on stderr).
Deterministic (seed 2718; E13b reader seeds from SEED_B=2731).
CPU-only probe; GPU only for encoder forwards.

Dev path: `python -m experiments.x9_presence_depth --cpu-only` runs the
self-tests, bank, staging fidelity and battery smoke with no model, no GPU,
and no verdict.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# BLAS thread cap — X3/E12/E13's reason verbatim: the probe path does
# thousands of tiny solves; uncapped BLAS turns each into a thread storm.
# Must be set BEFORE numpy loads (this module imports X3, which imports E12).
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

from sklearn.neural_network import MLPRegressor  # noqa: E402  (refit arm)

# X3 is imported VERBATIM — battery, bank, collection, ridge probe path.
from x3_stats_battery import (  # noqa: E402
    PERM_SEEDS, STATS_NAMES, build_bank, collect, feature_probe,
    stats_battery,
)
# E12's probe machinery + spaces (X3 re-exports the same objects).
from e12_room_dial_reader import (  # noqa: E402
    DIAL_NAMES, FIDELITY_FLOOR, K_PRIMARY, K_STRICT, RATE, SECONDS, W, H,
    loro_predict, pca_basis, r2_columns, spearman, stage_source,
)
from common import ppms_from_lavfi  # noqa: E402
# E13b's fixed nonlinear reader, by import (constants are the registration).
from e13b_nonlinear_reader import (  # noqa: E402
    MLP_ALPHA, MLP_CURV_FLOOR, MLP_HIDDEN, MLP_MAX_ITER, MLP_SOLVER,
    SEED_B, mlp_curvature, mlp_loro, mlp_null, mlp_selftest,
)
from e13_nonlinear_dial_reader import harness_selftest  # noqa: E402
from e9_ijepa_stills import N_STILLS, preflight_guard  # noqa: E402

# --------------------------------------------------------------------- #
# Pre-registered constants                                              #
# --------------------------------------------------------------------- #
HEADLINE_DIAL = "presence"
WALL_BATT_MLP = 0.30        # WALL: battery-MLP room-level presence BELOW this
WALL_EMB_FLOOR = 0.80       # WALL: embedding-MLP room-level presence AT/ABOVE
FALLS_RATIO = 0.7           # FALLS: battery-MLP >= 0.7 x embedding-MLP
PERMS_RIDGE = 200           # X3's ridge null budget (drift-check parity)
PERMS_MLP = max(20, int(os.environ.get("X9_PERMS_MLP", "100")))
BATT_LUM_FLOOR = 0.90       # G0b (X3 verbatim)

# Reader seeds (E13b's namespace; distinct offsets per arm/convention).
MLP_SEED = {"battery": SEED_B + 901, "jepa": SEED_B + 964}
REFIT_SEED = {"battery": SEED_B + 921, "jepa": SEED_B + 922}
NULL_SEED = {"battery": SEED_B + 931, "jepa": SEED_B + 932}
# X3's ridge perm seeds by arm (x3.PERM_SEEDS keys: lum1/stats/pixels/jepa).
RIDGE_PERM_SEED = {"battery": PERM_SEEDS["stats"], "jepa": PERM_SEEDS["jepa"]}

# X3's published numbers (RESULTS.md 2026-09-28 11:10) — C1 drift reference.
X3_PUBLISHED = {
    "verdict": "INCONCLUSIVE (volume parity, presence jepa-wins)",
    "r2_room_loro_presence": {"battery": 0.028, "jepa": 0.937},
    "r2_still_loro": {"volume": {"battery": 0.954, "jepa": 0.962},
                      "mood": {"battery": 0.937, "jepa": 0.811},
                      "presence": {"battery": 0.66, "jepa": 0.948}},
}


def log(msg: str) -> None:
    """Progress goes to stderr; stdout is reserved for the JSON verdict."""
    print(f"[x9] {msg}", file=sys.stderr, flush=True)


def _strip(pr: dict) -> dict:
    return {k: v for k, v in pr.items() if not k.startswith("_")}


# --------------------------------------------------------------------- #
# Readers                                                                #
# --------------------------------------------------------------------- #
def room_average_r2(Y: np.ndarray, pred: np.ndarray,
                    groups: np.ndarray) -> dict:
    """E13b's avg-pred room-level convention: average held-out still
    predictions per room, R2 against the room labels (27 points)."""
    ids = np.unique(groups)
    Yr = np.stack([Y[groups == g].mean(0) for g in ids])
    Pr = np.stack([pred[groups == g].mean(0) for g in ids])
    return {d: round(float(v), 4)
            for d, v in zip(DIAL_NAMES, r2_columns(Yr, Pr))}


def mlp_arm(z: np.ndarray, Y: np.ndarray, groups: np.ndarray,
            arm: str) -> dict:
    """The E13b reader on one feature set: LORO MLP fits (still-level),
    avg-pred room-level R2, curvature certificate, permutation null."""
    t0 = time.time()
    fit = mlp_loro(z, Y, groups, dev="cpu", seed=MLP_SEED[arm],
                   want_curv=True)
    r2_still = {d: round(float(v), 4)
                for d, v in zip(DIAL_NAMES, r2_columns(Y, fit["pred"]))}
    r2_room = room_average_r2(Y, fit["pred"], groups)
    curv = mlp_curvature(fit["weights"], fit["curv_rows"])
    n_curv_ok = int(sum(1 for d in DIAL_NAMES
                        if curv.get(d, 0.0) >= MLP_CURV_FLOOR))
    log(f"mlp[{arm}] fits done in {time.time() - t0:.1f}s — still={r2_still} "
        f"room_avg={r2_room} curv_mean={curv.get('mean')}")
    return {"fit": fit, "r2_still": r2_still, "r2_room_avg": r2_room,
            "curvature": curv, "curv_dials_ok": n_curv_ok}


def mlp_room_refit(Xf: np.ndarray, Y: np.ndarray,
                   groups: np.ndarray, arm: str) -> dict:
    """Charity arm: LORO AT room granularity — MLP trained on room-mean
    features (26 rows/fold, hidden 16, lbfgs, alpha 0.1), predicts the
    held-out room mean. Per-fold standardization on train rooms only."""
    ids = np.unique(groups)
    Xr = np.stack([Xf[groups == g].mean(0) for g in ids])
    Yr = np.stack([Y[groups == g].mean(0) for g in ids])
    F = len(ids)
    pred = np.zeros_like(Yr)
    for f in range(F):
        te = np.zeros(F, bool)
        te[f] = True
        tr = ~te
        mu, sd = Xr[tr].mean(0), Xr[tr].std(0) + 1e-8
        my, sy = Yr[tr].mean(0), Yr[tr].std(0) + 1e-8
        m = MLPRegressor(hidden_layer_sizes=(MLP_HIDDEN,),
                         activation="relu", solver=MLP_SOLVER,
                         alpha=MLP_ALPHA, max_iter=MLP_MAX_ITER,
                         random_state=int(REFIT_SEED[arm] + f))
        m.fit(((Xr[tr] - mu) / sd).astype(np.float32),
              ((Yr[tr] - my) / sy).astype(np.float32))
        pred[f] = m.predict(((Xr[f:f + 1] - mu) / sd).astype(np.float32))[0] \
            * sy + my
    r2 = {d: round(float(v), 4)
          for d, v in zip(DIAL_NAMES, r2_columns(Yr, pred))}
    log(f"mlp-refit[{arm}] room_refit={r2}")
    return r2


def mlp_null95(z: np.ndarray, Y: np.ndarray, groups: np.ndarray,
               r2_still: dict, arm: str) -> tuple[dict, dict]:
    """E12's permutation null, MLP edition (e13b.mlp_null verbatim): room-
    level label shuffles, fixed budget = MLP_MAX_ITER. Booked control,
    never gated. Compared against the STILL-level reads (E13b's booked null
    convention — the matrix is pooled R2 on shuffled labels)."""
    t0 = time.time()
    null = mlp_null(z, Y, groups, "cpu", PERMS_MLP, MLP_MAX_ITER,
                    seed=NULL_SEED[arm])
    null95 = {d: round(float(np.percentile(null[:, j], 95)), 4)
              for j, d in enumerate(DIAL_NAMES)}
    perm_p = {d: round(float((null[:, j] >= r2_still[d]).mean()), 4)
              for j, d in enumerate(DIAL_NAMES)}
    log(f"mlp-null[{arm}] {PERMS_MLP} perms in {time.time() - t0:.1f}s "
        f"null95={null95}")
    return null95, perm_p


# --------------------------------------------------------------------- #
# CPU-only mode (no model, no GPU): the plumbing test                    #
# --------------------------------------------------------------------- #
def cpu_only() -> dict:
    st = harness_selftest()
    mst = mlp_selftest("cpu")
    bank = build_bank()
    targets = np.stack([r["target"] for r in bank])
    labels = np.stack([r["label"] for r in bank])
    fid = {d: round(spearman(targets[:, i], labels[:, i]), 4)
           for i, d in enumerate(DIAL_NAMES)}
    # battery smoke on REAL ffmpeg renders of 3 grid rooms (X3's corners)
    smoke = []
    for r in (bank[0], bank[13], bank[26]):
        src = stage_source(*[float(t) for t in r["target"]], r["seed"])
        frames = ppms_from_lavfi(src, SECONDS, RATE, (W, H))
        idx = np.linspace(0, len(frames) - 1, N_STILLS).round().astype(int)
        smoke.append(np.stack([stats_battery(frames[i]) for i in idx]))
    bat = np.concatenate(smoke)
    dead = [STATS_NAMES[j] for j in range(bat.shape[1])
            if bat[:, j].std() < 1e-9]
    out = {
        "experiment": "X9 presence-depth (battery + nonlinear reader)",
        "mode": "cpu-only (no model, no GPU)",
        "seed": SEED, "reader_seed_base": SEED_B,
        "reader": (f"MLP {MLP_HIDDEN} hidden ReLU, {MLP_SOLVER}, "
                   f"alpha={MLP_ALPHA}, max_iter={MLP_MAX_ITER} (e13b verbatim)"),
        "ridge_harness_selftest_e13": st,
        "mlp_reader_selftest_e13b": mst,
        "rooms": len(bank),
        "staging_fidelity_spearman_target_vs_label": fid,
        "battery_dim": int(bat.shape[1]),
        "battery_smoke": {"rooms": 3, "stills": int(bat.shape[0]),
                          "dead_dims": dead},
        "perms": {"ridge": PERMS_RIDGE, "mlp": PERMS_MLP},
        "gates_pre_registered": {
            "G0d_ridge_selftest_pass": st["pass"],
            "G0dp_mlp_selftest_pass": mst["pass"],
            "G0a_staging_fidelity_floor": FIDELITY_FLOOR,
            "G0b_battery_luminance_floor": BATT_LUM_FLOOR,
            "Gc_curvature_floor": MLP_CURV_FLOOR,
            "G1": {"FALLS": f"batt_mlp_room >= {FALLS_RATIO} x emb_mlp_room",
                   "WALL": f"batt_mlp_room < {WALL_BATT_MLP} AND "
                           f"emb_mlp_room >= {WALL_EMB_FLOOR}",
                   "gate_input": "max(avg-pred, room-refit) per arm"}},
        "note": ("No verdict in CPU-only mode. Watch: both self-tests pass, "
                 "fidelity >= 0.5 on >= 2/3 dials, no dead battery dims."),
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
        out = {"experiment": "X9 presence-depth (battery + nonlinear reader)",
               "verdict": "ABORTED", "reason": reason,
               "guard_preflight": guard_info}
        print(json.dumps(out, indent=2))
        return out

    # G0d + G0d' — cheapest validity gates first (model-free, CPU-only).
    st = harness_selftest()
    mst = mlp_selftest("cpu")
    log(f"ridge self-test: {st} | mlp self-test: "
        f"pass={mst['pass']} ({mst.get('seconds', '?')}s)")
    base = {"experiment": "X9 presence-depth (battery + nonlinear reader)",
            "seed": SEED, "reader_seed_base": SEED_B,
            "reader": (f"MLP {MLP_HIDDEN} hidden ReLU, {MLP_SOLVER}, "
                       f"alpha={MLP_ALPHA}, max_iter={MLP_MAX_ITER} "
                       f"(e13b verbatim)"),
            "headline_dial": HEADLINE_DIAL,
            "gate_thresholds": {"wall_batt_mlp": WALL_BATT_MLP,
                                "wall_emb_floor": WALL_EMB_FLOOR,
                                "falls_ratio": FALLS_RATIO},
            "perms": {"ridge": PERMS_RIDGE, "mlp": PERMS_MLP},
            "guard_preflight": guard_info,
            "x3_published_reference": X3_PUBLISHED}
    if not st["pass"]:
        out = dict(base)
        out.update({"verdict": "INVALID_HARNESS",
                    "reason": "G0d: E13's ridge probe-path self-test failed"})
        print(json.dumps(out, indent=2))
        return out
    if not mst["pass"]:
        out = dict(base)
        out.update({"verdict": "INVALID_READER",
                    "mlp_reader_selftest": mst,
                    "reason": "G0d': E13b's MLP reader self-test failed"})
        print(json.dumps(out, indent=2))
        return out

    # Bank + staging fidelity (G0a) — E12's Arm B, elephant's own labels.
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

    # GPU pass — X3's collect verbatim (renders, embeds, battery, controls).
    import torch
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"loading I-JEPA ({dev})...")
    try:
        from e9_ijepa_stills import load_encoder
        model_used, model, processor, load_notes = load_encoder(dev)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest": st,
                    "mlp_reader_selftest": mst,
                    "reason": f"model load failed: {e}"})
        print(json.dumps(out, indent=2))
        return out
    log(f"using {model_used}")
    try:
        (X, Y, Yt, G, LUM, PIX, S, names) = collect(model, processor, dev,
                                                    torch)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest": st,
                    "mlp_reader_selftest": mst,
                    "staging_fidelity_spearman_target_vs_label": fid,
                    "reason": f"frame/embed failed: {e}"})
        print(json.dumps(out, indent=2))
        return out
    finally:
        if dev == "cuda":
            torch.cuda.empty_cache()
    if len(np.unique(G)) < 8:
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest": st,
                    "mlp_reader_selftest": mst,
                    "reason": f"only {len(np.unique(G))} rooms — "
                              "grouped CV meaningless"})
        print(json.dumps(out, indent=2))
        return out

    # Feature sets: battery verbatim (24-d) + jepa PCA-k64 (E12's basis).
    basis, evr = pca_basis(X, K_PRIMARY)
    z64 = X @ basis[:, :K_PRIMARY]
    FEATS = {"battery": S.astype(np.float64), "jepa": z64.astype(np.float64)}

    # ---- ridge rows: X3's probe verbatim (control + drift check) ----
    log(f"ridge probes ({PERMS_RIDGE} perms each)...")
    ridge = {}
    for arm in ("battery", "jepa"):
        ridge[arm] = feature_probe(FEATS[arm], Y, G, PERMS_RIDGE,
                                   RIDGE_PERM_SEED[arm])
        log(f"ridge[{arm}] still={ridge[arm]['r2_still_loro']} "
            f"room={ridge[arm]['r2_room_loro']}")
    # C5 — jepa k16 ridge line, still-level only (booked).
    pred16, _ = loro_predict(X @ basis[:, :K_STRICT], Y, G)
    jepa_k16 = {d: round(float(v), 4)
                for d, v in zip(DIAL_NAMES, r2_columns(Y, pred16))}

    # G0b — battery sensitivity: must read the luminance it contains (X3).
    Ss = (S - S.mean(0)) / (S.std(0) + 1e-8)
    pred_lum, _ = loro_predict(Ss, LUM.reshape(-1, 1).astype(np.float64), G)
    r2_stats_lum = float(r2_columns(LUM.reshape(-1, 1).astype(np.float64),
                                    pred_lum)[0])
    if r2_stats_lum < BATT_LUM_FLOOR:
        out = dict(base)
        out.update({"verdict": "INVALID_HARNESS",
                    "ridge_rows": {a: _strip(ridge[a]) for a in ridge},
                    "g0b_battery_luminance_r2": round(r2_stats_lum, 4),
                    "reason": "G0b: battery cannot read mean luminance — "
                              "broken battery"})
        print(json.dumps(out, indent=2))
        return out
    log(f"G0b battery->luminance LORO R2 = {r2_stats_lum:.4f} (floor "
        f"{BATT_LUM_FLOOR})")

    # ---- MLP rows: E13b's reader, both conventions + nulls ----
    log(f"MLP arms (reader={MLP_HIDDEN}h/{MLP_SOLVER}/alpha={MLP_ALPHA})...")
    arms: dict = {}
    for arm in ("battery", "jepa"):
        res = mlp_arm(FEATS[arm], Y, G, arm)
        res["r2_room_refit"] = mlp_room_refit(FEATS[arm], Y, G, arm)
        # gate input per arm: the BEST honest room-level convention
        res["r2_room_gate_input"] = {
            d: max(res["r2_room_avg"][d], res["r2_room_refit"][d])
            for d in DIAL_NAMES}
        res["null95"], res["perm_p"] = mlp_null95(
            FEATS[arm], Y, G, res["r2_still"], arm)
        arms[arm] = res

    # ---- Gc: reader non-affinity (both arms must be genuinely nonlinear) --
    curv_ok = {arm: arms[arm]["curv_dials_ok"] >= 2 for arm in arms}
    if not all(curv_ok.values()):
        out = dict(base)
        out.update({
            "verdict": "INCONCLUSIVE",
            "reason": "Gc: reader went affine on "
                      f"{[a for a, v in curv_ok.items() if not v]} — the "
                      "nonlinear escalation cannot arbitrate (E13b's clause)",
            "curvature": {a: arms[a]["curvature"] for a in arms},
            "harness_selftest_e13": st, "mlp_reader_selftest_e13b": mst})
        print(json.dumps(out, indent=2))
        return out

    # ---- G1: the pre-registered gate (max convention per arm) ----
    B = float(arms["battery"]["r2_room_gate_input"][HEADLINE_DIAL])
    E = float(arms["jepa"]["r2_room_gate_input"][HEADLINE_DIAL])
    falls = bool(B >= FALLS_RATIO * E)
    wall = bool(B < WALL_BATT_MLP and E >= WALL_EMB_FLOOR)
    if falls:
        verdict = "FALLS"
        verdict_reason = (
            f"nonlinear reader lifts battery presence to room-level {B} = "
            f"{B / max(E, 1e-9):.2f}x the embedding's {E} (>= "
            f"{FALLS_RATIO}x) — presence falls to statistics; X3's surviving "
            "deep claim is dead")
    elif wall:
        verdict = "WALL"
        verdict_reason = (
            f"battery presence stays at room-level {B} < {WALL_BATT_MLP} "
            f"EVEN under the nonlinear reader while the embedding holds "
            f"{E} >= {WALL_EMB_FLOOR} — the gap is in the features, not the "
            "reader; presence depth hardens into a wall")
    else:
        verdict = "INCONCLUSIVE"
        verdict_reason = (
            f"between the gates: batt_mlp_room={B}, emb_mlp_room={E} "
            f"(falls needs B >= {FALLS_RATIO * E:.3f}; wall needs "
            f"B < {WALL_BATT_MLP} with E >= {WALL_EMB_FLOOR})")

    # ---- assemble the ONE JSON verdict ----
    table = {}
    for arm, nice in (("battery", "battery"), ("jepa", "embedding")):
        table[f"{nice}_ridge"] = {
            "r2_room_loro": ridge[arm]["r2_room_loro"],
            "r2_still_loro": ridge[arm]["r2_still_loro"],
            "perm_null95_still": ridge[arm]["perm_null95"],
            "perm_p_still": ridge[arm]["perm_p"],
            "lambda_median": ridge[arm]["lambda_median"],
        }
        table[f"{nice}_mlp"] = {
            "r2_room_loro_avg_pred": arms[arm]["r2_room_avg"],
            "r2_room_loro_refit": arms[arm]["r2_room_refit"],
            "r2_room_loro_gate_input": arms[arm]["r2_room_gate_input"],
            "r2_still_loro": arms[arm]["r2_still"],
            "perm_null95_still": arms[arm]["null95"],
            "perm_p_still": arms[arm]["perm_p"],
            "curvature": arms[arm]["curvature"],
            "curv_dials_ok": arms[arm]["curv_dials_ok"],
        }

    four_way = {
        d: {f"{nice}_{reader}":
            (table[f"{nice}_ridge"]["r2_room_loro"][d] if reader == "ridge"
             else table[f"{nice}_mlp"]["r2_room_loro_gate_input"][d])
            for reader in ("ridge", "mlp") for nice in ("battery", "embedding")}
        for d in DIAL_NAMES}

    out = dict(base)
    out.update({
        "model": model_used, "device": dev, "load_notes": load_notes,
        "rooms": len(names), "stills_per_room": N_STILLS,
        "cells": int(X.shape[0]),
        "harness_selftest_e13": st, "mlp_reader_selftest_e13b": mst,
        "staging_fidelity_spearman_target_vs_label": fid,
        "g0a_pass": fid_pass,
        "g0b_battery_luminance_r2": round(r2_stats_lum, 4),
        "pca_evr_k16": round(float(evr[:K_STRICT].sum()), 4),
        "pca_evr_k64": round(float(evr[:K_PRIMARY].sum()), 4),
        "jepa_k16_ridge_still": jepa_k16,
        "four_way_table_room_loro": four_way,
        "full_table": table,
        "gate": {
            "rule": ("FALLS iff batt_mlp_room >= 0.7 x emb_mlp_room (checked "
                     "first); WALL iff batt_mlp_room < 0.30 AND emb_mlp_room "
                     ">= 0.80; batt/emb_mlp_room = max(avg-pred, refit) — "
                     "the null gets every chance"),
            "batt_mlp_room_gate_input": B, "emb_mlp_room_gate_input": E,
            "falls": falls, "wall": wall,
            "reader_affine_guard_fired": False,
        },
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "note": (
            "X9 gives X3's 24-d stats battery the E13b nonlinear reader at "
            "room-level LORO, against the frozen I-JEPA embedding on the "
            "same bank/labels/protocol. Ridge rows are X3's control, "
            "re-run for drift. The gate input per arm is the BEST of the "
            "two honest room-level MLP conventions (E13b avg-pred; room-"
            "mean refit). A WALL hardens 'classical stats cannot buy "
            "presence generalization even nonlinearly'; a FALLS kills the "
            "last deep claim; volume/mood are reported, not gated (X3 "
            "already gave them to statistics)."),
    })
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
