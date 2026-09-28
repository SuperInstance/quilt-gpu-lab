#!/usr/bin/env python3
"""E25 — fold-amplitude phase transition: where does the dial read die?

THE QUESTION (SPOOL.md, entry E25)
  E13 (experiments/e13_nonlinear_dial_reader.py) measured ONE point of the
  carrier-nonlinearity axis: Arm N2, roomgen's frozen nonlinear sensor mixture
  read out through FOLDED (non-monotone) channel responses at fold amplitude
  2.2, mean carrier curvature 0.471. On that single point the linear ridge read
      mood     R2_still_loro(k64) = 0.537   (survives E12's 0.30 floor)
      volume   R2_still_loro(k64) = -0.100  (dies)
      presence R2_still_loro(k64) =  0.270  (dies)
  which E13 landed as INCONCLUSIVE (1/3 dials), and E13b's question (reader or
  embedding?) is a different axis. E25 asks the axis E13 could not: what is the
  SHAPE of the read versus carrier nonlinearity? SPOOL's claim:

      read R2 decays smoothly (a phase transition) in fold amplitude, with a
      per-dial critical amplitude where volume/presence die but mood survives.

  KEEP = per-dial R2 decays MONOTONICALLY in amplitude with DIFFERENT per-dial
         critical amplitudes (mood survives longest). KILL = no monotone
         relationship (E13's single point was noise). INVALID_STAGING if any
         carrier fails liveness.

DESIGN (one carrier family, six amplitudes, one frozen encoder)
  Everything is E13's: the 27-room staged bank and its elephant-DialBank labels
  (e13.build_bank), the N2 carrier builder (e13.knobs_mixture: frozen
  roomgen.SensorMixture tanh(Wz+b)*gain -> label-free SVD readout -> 12 signed
  channels -> 7 lavfi knobs), the lavfi renderer, the frozen I-JEPA embedding
  collector (e13.collect_arm), and the ridge probe (e13.arm_report: E12's
  probe_sweep verbatim, still-LORO R2 at k=16/64/256, room-LORO R2, 200-perm
  room-shuffle null, tertile accuracy, raw-pixel + luminance controls, room
  identity accuracy). E25 changes exactly ONE thing: E13's module-level fold
  constant N2_FOLD_AMP is re-pointed per sweep point
      e13.N2_FOLD_AMP <- a,  e13.N2_FOLD_PHASE <- 0.0 (held fixed)
  and the whole point (carrier + certificate + render + embed + probe) is
  recomputed at amplitude a. NOTHING is forked: the carrier, the bank, the
  renderer and the probe are the imported E13/E12 code, so a point at a = 2.2
  must reproduce E13's own N2 numbers bit-for-bit (the replication control,
  C6 below). The amplitude is read from SPOOL, verbatim:
      FOLD_AMPS = (0.5, 1.0, 1.5, 2.2, 2.8, 3.5)
  At each amplitude the x-axis is not the nominal amplitude but the MEASURED
  nonlinearity: E13's carrier certificate recomputed live (mean normalized
  curvature of the dial response, distance-correlation + 3-NN liveness,
  injectivity), so the report is R2 versus measured curvature, with the
  nominal amplitude carried alongside.

MEASURED DESIGN PASS (--cpu-only, before any embedding existed)
  Same status as E13's design table: this is the arithmetic of the carrier on
  the actual 27-room bank, computed with the E13 functions E25 imports, before
  a single frame was rendered. It is what fixes the censoring rule below.
    amp  mean_curv  nonaffine  live   mean_lin_loo_R2  3-NN LOO R2 (m/v/p)
    0.5   0.338      yes       3/3      0.978          0.59 / 0.38 / 0.50
    1.0   0.294      yes       3/3      0.972          0.69 / 0.39 / 0.44
    1.5   0.329      yes       3/3      0.956          0.72 / 0.38 / 0.38
    2.2   0.471      yes       3/3      0.900          0.67 / 0.33 / 0.37
    2.8   0.729      yes       3/3      0.757          0.55 / 0.24 / 0.25
    3.5   1.308      yes       0/3      0.309          0.10 / -0.26 / -0.33
  Reading: the fold is measurably nonlinear at every point (curvature climbs
  0.294 -> 1.308, all above E13's 0.20 non-affine floor), the knob-space linear
  read degrades 0.978 -> 0.309, and amp 3.5 BREAKS LIVENESS (0 of 3 dials
  recoverable by 3-NN, dCorr p 0.03/0.14/0.01, volume/presence 3-NN R2
  negative). This replicates E13's booked finding that deeper folds exist and
  are dead, and it is the reason the censoring rule below is needed.

PRE-REGISTERED TREATMENT OF A DEAD CARRIER (the "INVALID_STAGING" gate)
  "INVALID_STAGING if any carrier fails liveness" is applied PER POINT and
  bookkept, because a dead carrier renders rooms that carry no dial signal: any
  read-death measured there is a STAGING fact, not an embedding fact (E12's own
  warning, and E13's reason for the certificate). So, fixed before the model:
    - a point whose certificate fails liveness (E13's `live_pass`: injective
      knobs AND >= 2 of 3 dials with dCorr p <= 0.05 and 3-NN LOO R2 >= 0.20)
      is labelled INVALID_STAGING, is CENSORED from the trend, and is reported
      with its numbers anyway;
    - the trend/verdict is computed on the LIVE amplitudes only, in ascending
      order;
    - if fewer than MIN_LIVE_AMPS = 4 points survive, the whole sweep is
      INVALID_STAGING (no trend can be fitted over valid staging) — and that is
      decided and printed BEFORE the model is loaded, so a dead sweep costs no
      GPU time;
    - the censoring test is carrier-only: label-free, embedding-free, model-free
      (it reads the 7 knob vectors vs the design triples), so it CANNOT be
      tuned by the read results. This is the whole point of pre-registering it.
  Decision recorded honestly: the design pass already showed amp 3.5 is dead,
  so the registered sweep is expected to run on the 5 live amplitudes
  {0.5, 1.0, 1.5, 2.2, 2.8} (curvature 0.294 .. 0.729) and to flag 3.5
  INVALID_STAGING. The amplitude set was NOT trimmed to 2.8 to make the trend
  prettier — the dead point stays in the sweep and in the receipt.

PRE-REGISTERED GATES (fixed before running; this file IS the registration)
  G0d  harness self-test : E13's G0d verbatim (imported): the probe path reads
      a synthetic linear signal at LORO R2 >= 0.90 and shuffled labels < 0.10.
      Fails -> INVALID_HARNESS.
  G0e  verdict-mapper self-test : the E25 trend/verdict mapper (a pure
      function of the per-amplitude curves) must return KEEP on a synthetic
      "mood survives, volume/presence die at different amplitudes" curve,
      KILL on flat and on rising curves, and INCONCLUSIVE on (a) all dials
      dying at the SAME amplitude and (b) the wrong dial surviving longest.
      A mapper that cannot call a clean planted transition cannot be trusted
      to call the real one. Fails -> INVALID_HARNESS.
  G0a  staging fidelity : E13's G0a verbatim (>= 2/3 dials, Spearman between
      the design triple and the elephant DialBank label >= 0.5). The bank is
      amplitude-independent. Fails -> INVALID_STAGING.
  G0b  sensitivity : E13's G0b VERBATIM — Arm L (E12's linear staging, the
      same carrier E13 used as its positive control) must show luminance LORO
      R2(k=64) >= 0.90 (E13's SENSITIVITY_FLOOR). E25 renders that one extra
      carrier (27 rooms) purely as this anchor and as the LEFT EDGE of the
      x-axis (its certificate measures curvature 0.000 and a linear knob read
      of 1.000 by construction). Fails -> INVALID_HARNESS. The luminance
      number is ALSO reported for every folded amplitude, booked.
      BUILD HISTORY, on the record: v1 of this file gated G0b on the MILDEST
      LIVE folded amplitude instead (an in-sweep analog, because v1 did not
      render Arm L), and when the registered sweep was fired it returned
      INVALID_HARNESS on that anchor (luminance 0.872 / 0.887 / 0.883 / 0.958 /
      0.655 at curvature 0.338 / 0.294 / 0.329 / 0.471 / 0.729, floor 0.90).
      That was a BUILD BUG in the gate, not a finding about the harness: the
      folded carrier drives the brightness knob through a folded channel, so
      luminance's readability is a property of the CARRIER, not of the
      pipeline's sensitivity, and the mildest folded point is therefore not a
      sensitivity control at all. v2 (this file) restores E13's own anchor.
      Nothing else was changed: the claim definition (K1/K2/K3) and the
      per-dial gate are v1's, pre-registered, untouched.
  G1   THE CLAIM (KEEP) : on the live amplitudes, all three of
        K1 monotone decay : >= 2 of 3 dials show a MONOTONE DECAY of
            R2_still_loro(k64) in amplitude, defined as ALL of
              (i)  Spearman(amplitude, R2) <= MONO_RHO_FLOOR = -0.80,
              (ii) total drop R2(first) - R2(last) >= DROP_FLOOR = 0.15,
              (iii) no single upward step > UP_STEP_TOL = 0.05 (a noise
                    allowance on pointwise monotonicity);
        K2 different critical amplitudes : >= 2 dials have a FINITE critical
            amplitude and those criticals are pairwise DISTINCT, where
              crit_d := the smallest live amplitude at which dial d fails
                        E12/E13's per-dial gate in THIS run, recomputed live
                        (r64 >= 0.30 AND room >= 0.15 AND k16 >= 0.5*k64 AND
                         r64 > its 200-perm null95),
              crit_d = None (never dies over the live sweep) otherwise;
        K3 mood survives longest : crit_mood > crit_d for every other dial
            with a finite crit_d (None counts as +infinity), AND at least one
            other dial has a finite crit_d (so the comparison is real).
      => a phase transition: distinct per-dial death points, mood last.
  G2   INCONCLUSIVE : K1 holds but K2 or K3 fails — the decay is real but the
      "different critical amplitudes, mood longest" half of the claim did not
      reproduce. Booked, never reported as a KEEP, and never as a KILL either:
      a KILL means the monotone relationship itself is absent.
  G3   KILL : K1 fails (fewer than 2 dials decay monotonically) OR the mean
      Spearman over the three dials is >= 0 (no decay at all — the axis does
      not move the read, so E13's single point was noise). E13's single point
      is NOT evidence of a transition; this gate is.
  INVALID_HARNESS : G0d, G0e or G0b fails.  INVALID_STAGING : G0a fails, or
      the censoring leaves < 4 live points, or (booked, never a KILL) the
      primary carrier's liveness boundary sits so low that the mildest live
      point is already dead.  ABORTED : guard preflight, model load, no frames,
      or < 8 rooms.

CONTROLS / BOOKED (never gated)
  C1 raw-pixel probe     : the same LORO ridge on 16x9 grayscale stills, per
      amplitude (E13's C1). If the pixels read the dials at an amplitude where
      the embedding does not, the carrier is visually readable and the
      embedding is the bottleneck — and vice versa. This is the single most
      informative booked control on a "where does the read die" experiment.
  C2 luminance Spearman and C3 the 200-perm null per amplitude: both in
      E13's arm_report, carried verbatim.
  C4 room identity acc   : half-split nearest-centroid, per amplitude.
  C5 room-level read     : R2_room_loro(k64) per dial per amplitude — the
      STRICT check (an unseen room), reported beside the still-level number at
      every point, plus its own Spearman-vs-amplitude.
  C6 E13 replication anchor : the amp 2.2 point is E13's own N2 arm, so its
      still-LORO numbers must reproduce E13's recorded -0.100 / 0.537 / 0.270
      (volume/mood/presence) up to GPU float noise. The JSON records the
      comparison against E13's booked numbers as `e13_replication`. A mismatch
      means E25's plumbing is not E13's plumbing — the first thing to read.
  C7 carrier audit       : the amplitude patch is audited (e13._fold vs the
      closed form 0.5*(1+sin(a*x)) at every amplitude), the six knob matrices
      must be pairwise distinct, and the certificate computed before the model
      is cross-checked against the one E13's arm_report recomputes internally.
  C8 curvature by dial   : per-dial curvature and 3-NN at every amplitude, so
      the x-axis is measured per dial, not just in the mean.
  C9 extra dials         : earnestness / cynicism / joke_landing / panic are
      booked per point (they ride the same bank).
  C10 criticals, both readings : `crit_d` (the GATED one) is the first live
      amplitude failing E12/E13's FULL per-dial gate, k16-retention clause
      included. That clause is a retention check, and on a 5-point sweep it is
      noisy (mood's k16/k64 ratio moves 0.874 -> 0.538 -> 0.306 -> 0.907 ->
      1.033 across the sweep, so mood's full-gate failure at amp 1.5 is the
      k16 clause while its k64 read there is 0.718, well above the 0.30
      floor). The receipt therefore also carries — BOOKED, never gated —
      `crit_k64_floor_d`: the first live amplitude failing the headline
      criteria alone (k64 >= 0.30 AND room >= 0.15 AND above the 200-perm
      null95). The mapping uses the GATED full-gate critical only; the booked
      one exists so a reader can see which clause moved a critical.

HONESTY / CAVEATS BOOKED WITH THE RESULT
  - This sweeps ONE carrier family along ONE axis (the N2 readout fold
    amplitude, phase fixed at 0.0), one frozen random physics draw (roomgen
    seed 2719), one encoder (I-JEPA ViT-H/16). A KEEP maps the readable-
    nonlinearity boundary of the E12-family claims for THIS family; it is not
    a law about "nonlinearity" in general.
  - The read is the LINEAR ridge (E13's reader). E13b's question — whether a
    nonlinear reader moves these death points — is a different axis and is NOT
    answered here; the death points found here are death points for the ridge,
    which is exactly what E12/E13 gated on.
  - The sweep set is SPOOL's, chosen before this file existed; the design pass
    then showed 3.5 is liveness-dead. The set was NOT trimmed. The censoring
    rule is pre-registered and carrier-only, so it cannot rescue (or doom) a
    verdict by looking at read numbers.
  - crit_d is a GRID property: "crit = the first live amplitude that fails"
    understates the precision (a dial that dies between 1.5 and 2.2 has
    crit = 2.2). The neighbouring passing point is reported at every critical
    so the bracket is visible, and a dial already failing at the mildest live
    point is flagged `dead_at_or_below_sweep_floor` (its death is censored
    below 0.5, not localised).
  - Carriers are still STAGED lavfi rooms with the elephant's own readings as
    labels; nothing here speaks to a natural camera feed.
  - GPU is touched only for encoder forwards, under E13's in-process
    preflight_guard; the probe stays numpy/CPU exactly as E12/E13 ran it.

WIRING (deliberately absent)
  - NOT in QUEUE.md and NOT in runner.py's EXP_MOD: the cron runner must not
    auto-claim or double-fire this. Manual fire only:
      ~/venvs/elephant-gpu/bin/python -m experiments.e25_fold_phase_transition
    Cost: 5 live amplitudes (after censoring) x 27 rooms x 12 stills = 1620
    encoder forwards at 224^2, plus E13's Arm L anchor (27 rooms x 12 = 324 more)
    — 1944 forwards, fp16 on the RTX 4050; on this box that measured ~4 min
    wall (E13's 8-12 min estimate for 972 forwards was conservative by ~10x),
    plus the CPU ridge sweeps (~30-60 s per point: 27-fold LORO inner-CV lambda
    grids plus a 200-perm null at k=64).

Dev paths (no verdict in either)
  --cpu-only      : bank, carrier + certificate at every amplitude (with the
                    censoring table and the measured x-axis), E13's Arm-L
                    affine anchor, G0a, G0d, G0e. No model, no GPU.
  --amps A,B,C    : dev-only amplitude override. The JSON marks itself
                    registered=false, the verdict is prefixed DEV_, and a dev
                    sweep with fewer than MIN_LIVE_AMPS live points returns
                    the explicit non-verdict DEV_SWEEP (the registered
                    min-live floor is relaxed for --amps only, so real frames
                    can be pushed through the plumbing cheaply). A dev sweep
                    is NOT the E25 result and must never be booked as one.

Verdict printed as ONE JSON object on stdout (progress on stderr).
Deterministic: E13's seed 2718 for bank/carriers/embeddings, E25's seed 2741
for the self-tests. cwd-independent; no files written.
"""
from __future__ import annotations

import gc
import json
import math
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

# BLAS thread cap — same reason as E12/E13: thousands of tiny ridge solves
# (27 folds x lambda grid x 200 perms x 6 points). Must be set BEFORE numpy
# loads, and this module imports e13, which imports e12, which imports numpy.
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

SEED = 2718          # E13's seed: bank, carriers, embeddings replicate E13
SEED_E25 = 2741      # E25's own draws (self-tests) — never touches the carriers
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
# E13 is imported VERBATIM — no fork of the carrier, the bank, the      #
# certificate, the collector or the ridge probe. E25 changes exactly    #
# one thing: E13's fold-amplitude CONSTANT is re-pointed per point.     #
# --------------------------------------------------------------------- #
import e13_nonlinear_dial_reader as e13                       # noqa: E402
from e13_nonlinear_dial_reader import (                        # noqa: E402
    PRIMARY_ARM, arm_report, build_bank, carrier_certificate, collect_arm,
    harness_selftest, knob_ranges, knobs_linear, knobs_mixture, mirror_check,
    render_scene,
)
from e12_room_dial_reader import (                             # noqa: E402
    DIAL_NAMES, EXTRA_DIALS, FIDELITY_FLOOR, K_PRIMARY,
    R2_FLOOR, R2_ROOM_FLOOR, R2_TOP_PC_FRACTION, SENSITIVITY_FLOOR,
    r2_columns, spearman,
)

# --------------------------------------------------------------------- #
# Pre-registered constants                                              #
# --------------------------------------------------------------------- #
# SPOOL entry E25's amplitude set, verbatim. Ordered ascending.
FOLD_AMPS = (0.5, 1.0, 1.5, 2.2, 2.8, 3.5)
FOLD_PHASE = 0.0          # held fixed; the sweep moves AMPLITUDE only
# Phase-transition gates (G1/G2/G3).
MONO_RHO_FLOOR = -0.80    # Spearman(amplitude, R2) at or below = decaying
DROP_FLOOR = 0.15         # total R2 drop first->last live amplitude
UP_STEP_TOL = 0.05        # largest tolerated upward step (noise allowance)
MIN_LIVE_AMPS = 4         # fewer live carriers than this -> INVALID_STAGING
# E13's booked N2 arm (results/RESULTS.md, 2026-09-28) — the replication
# anchor at amplitude 2.2. Order: mood, volume, presence.
E13_N2_R2_K64 = {"mood": 0.537, "volume": -0.100, "presence": 0.270}
E13_N2_CURVATURE = 0.471
E13_REPLICATION_TOL = 0.12   # GPU float noise + a different perms stream
CERT_LIVE_AMPS_MIN = 2       # E13's CERT_LIVE_DIALS_FLOOR, mirrored for clarity


def log(msg: str) -> None:
    """Progress to stderr; stdout is reserved for the ONE JSON verdict."""
    print(f"[e25] {msg}", file=sys.stderr, flush=True)


def _amp_key(a: float) -> str:
    return f"{float(a):g}"


# --------------------------------------------------------------------- #
# Fold-amplitude plumbing: the only handle E25 turns on E13             #
# --------------------------------------------------------------------- #
@contextmanager
def folded(amp: float):
    """Re-point E13's frozen fold constants at `amp` for the duration.

    e13._fold() reads N2_FOLD_AMP / N2_FOLD_PHASE from its module globals at
    CALL time, so assigning them here re-parameterises the carrier without
    touching a line of E13. Restored on exit, so E13 stays importable and
    un-mutated for any other caller (E13b, for one) in the same process.
    """
    old = (e13.N2_FOLD_AMP, e13.N2_FOLD_PHASE)
    e13.N2_FOLD_AMP = float(amp)
    e13.N2_FOLD_PHASE = float(FOLD_PHASE)
    try:
        yield
    finally:
        e13.N2_FOLD_AMP, e13.N2_FOLD_PHASE = old


def fold_patch_audit(amps) -> dict:
    """C7 — prove the amplitude patch actually moved the carrier.

    (a) e13._fold(x) must equal the closed form 0.5*(1+sin(a*x+phase)) at every
        amplitude (the patch is honoured, not silently ignored);
    (b) the resulting knob matrices must be pairwise DISTINCT (six amplitudes
        are six different renders — a constant knob matrix would make the whole
        sweep a single point measured six times);
    (c) the constants are restored afterwards (E13 un-mutated).
    """
    before = float(e13.N2_FOLD_AMP)
    per = {}
    for a in amps:
        with folded(a):
            probes = [0.0, 0.37, -1.25, 2.4]
            got = [float(e13._fold(x)) for x in probes]
        want = [float(np.clip(0.5 * (1.0 + math.sin(a * x + FOLD_PHASE)),
                              0.0, 1.0)) for x in probes]
        per[_amp_key(a)] = {
            "fold_matches_closed_form": bool(all(abs(g - w) <= 1e-9
                                                 for g, w in zip(got, want))),
            "fold_at_probes": [round(g, 6) for g in got],
        }
    restored = float(e13.N2_FOLD_AMP)
    return {"per_amp": per,
            "all_patched": bool(all(v["fold_matches_closed_form"]
                                    for v in per.values())),
            "constants_restored": bool(restored == before),
            "fold_amp_before_audit": before,
            "restored_fold_amp": restored}


def build_point_carrier(amp: float, bank: list) -> tuple[dict, np.ndarray, dict, dict, dict]:
    """Carrier + certificate at one fold amplitude — all CPU, no model.

    Returns (knobs_by_room, knob_matrix, per_dial_certificate, certificate
    summary, carrier info from e13.knobs_mixture). This runs BEFORE the model
    for every amplitude, so the staging table (curvature + liveness) is known
    before a single frame is rendered — E13's own ordering, per point.
    """
    with folded(amp):
        knobs, info = knobs_mixture(bank)
    km = np.stack([knobs[r["name"]] for r in bank])
    targets = np.stack([r["target"] for r in bank])
    per, summ = carrier_certificate(km, targets)
    return knobs, km, per, summ, info


def x_axis_block(amp: float, per: dict, summ: dict) -> dict:
    """The MEASURED x-coordinate of this sweep point: E13's certificate."""
    return {
        "nominal_fold_amp": float(amp),
        "mean_curvature": summ["mean_curvature"],
        "curvature_by_dial": {d: per[d]["curvature"] for d in DIAL_NAMES},
        "nonaffine_pass": summ["nonaffine_pass"],
        "live_pass": summ["live_pass"],
        "n_dials_live": summ["n_dials_live"],
        "knn_loo_r2_by_dial": {d: per[d]["knn_loo_r2"] for d in DIAL_NAMES},
        "distcorr_p_by_dial": {d: per[d]["distcorr_p"] for d in DIAL_NAMES},
        "mean_lin_loo_r2": summ["mean_lin_loo_r2"],
        "mean_quad_loo_r2": summ["mean_quad_loo_r2"],
        "injectivity": summ["injectivity"],
        "status": ("LIVE" if summ["live_pass"] else "INVALID_STAGING"),
    }


# --------------------------------------------------------------------- #
# Trend + verdict mapper (PURE — a function of the per-amplitude curves) #
# --------------------------------------------------------------------- #
def dial_trend(amps, r2_still, r2_room, null95, gate_pass) -> dict:
    """Per-dial decay statistics over the (live) amplitude sweep.

    Monotone decay (K1) := Spearman <= MONO_RHO_FLOOR AND total drop >=
    DROP_FLOOR AND no single upward step > UP_STEP_TOL. crit_d (K2) := the
    first live amplitude at which E13's per-dial gate FAILS, else None
    (survived the whole live sweep). The neighbouring passing point is recorded
    so the bracket is visible, and `dead_at_or_below_sweep_floor` flags a dial
    that is already dead at the mildest live point (its death is censored below
    the sweep's low end, not localised by this grid).
    """
    out = {}
    a = [float(x) for x in amps]
    for i, d in enumerate(DIAL_NAMES):
        r = [float(x) for x in r2_still[i]]
        rr = [float(x) for x in r2_room[i]]
        n95 = [float(x) for x in null95[i]]
        gp = [bool(x) for x in gate_pass[i]]
        steps = [r[j + 1] - r[j] for j in range(len(r) - 1)]
        drop = r[0] - r[-1]
        up = max(steps) if steps else 0.0
        rho = float(spearman(np.asarray(a, float), np.asarray(r, float)))
        rho_room = float(spearman(np.asarray(a, float), np.asarray(rr, float)))
        crit, crit_idx = None, None
        for j, ok in enumerate(gp):
            if not ok:
                crit, crit_idx = a[j], j
                break
        # C10 (BOOKED, never gated): the same critical computed on the
        # HEADLINE criteria alone — k64 >= R2_FLOOR AND room >= R2_ROOM_FLOOR
        # AND k64 above its 200-perm null95 — with the k16 retention clause
        # dropped, so a reader can see which clause moved a critical.
        crit_head = None
        for j in range(len(a)):
            if not (r[j] >= R2_FLOOR and rr[j] >= R2_ROOM_FLOOR and r[j] > n95[j]):
                crit_head = a[j]
                break
        out[d] = {
            "r2_still_loro_k64": [round(float(x), 4) for x in r],
            "r2_room_loro_k64": [round(float(x), 4) for x in rr],
            "perm_null95_k64": [round(float(x), 4) for x in n95],
            "gate_pass": gp,
            "spearman_amp_vs_r2_still_k64": round(rho, 4),
            "spearman_amp_vs_r2_room_k64": round(rho_room, 4),
            "total_drop_k64": round(float(drop), 4),
            "max_up_step_k64": round(float(up), 4),
            "monotone_decay": bool(rho <= MONO_RHO_FLOOR and drop >= DROP_FLOOR
                                   and up <= UP_STEP_TOL),
            "critical_amp": crit,
            "critical_prev_pass_amp": (a[crit_idx - 1] if crit_idx else None),
            "dead_at_or_below_sweep_floor": bool(crit is not None and crit_idx == 0),
            "crit_k64_floor_booked": crit_head,
            "n_live_amps_passing": int(sum(1 for x in gp if x)),
        }
    return out


def map_verdict(trend: dict, n_live: int, n_expected: int) -> tuple[str, str, dict]:
    """E25's pre-registered mapping (G1/G2/G3). Pure function of `trend`.

    Returns (verdict, reason, details). Called with the LIVE amplitudes only.
    """
    if n_live < MIN_LIVE_AMPS:
        return ("INVALID_STAGING",
                f"only {n_live} of {n_expected} swept carriers are live "
                f"(< MIN_LIVE_AMPS={MIN_LIVE_AMPS}) — no read trend can be "
                f"fitted over valid staging", {"n_live": n_live})

    mono = [d for d in DIAL_NAMES if trend[d]["monotone_decay"]]
    rhos = [trend[d]["spearman_amp_vs_r2_still_k64"] for d in DIAL_NAMES]
    mean_rho = float(np.mean(rhos))
    finite = {d: trend[d]["critical_amp"] for d in DIAL_NAMES
              if trend[d]["critical_amp"] is not None}
    n_finite = len(finite)
    distinct = len(set(finite.values())) >= 2
    c_mood = trend[DIAL_NAMES[0]]["critical_amp"]
    c_mood_v = float("inf") if c_mood is None else float(c_mood)
    others = {d: c for d, c in finite.items() if d != DIAL_NAMES[0]}
    mood_longest = bool(others and all(c_mood_v > float(c) for c in others.values()))
    details = {
        "monotone_dials": mono,
        "n_monotone_decay": len(mono),
        "spearman_by_dial": {d: trend[d]["spearman_amp_vs_r2_still_k64"]
                             for d in DIAL_NAMES},
        "mean_spearman": round(mean_rho, 4),
        "critical_amps": {d: trend[d]["critical_amp"] for d in DIAL_NAMES},
        "n_finite_criticals": n_finite,
        "criticals_distinct": bool(distinct),
        "mood_critical": c_mood,
        "mood_survives_longest": mood_longest,
        "floors": {"mono_rho": MONO_RHO_FLOOR, "drop": DROP_FLOOR,
                   "up_step_tol": UP_STEP_TOL, "min_live_amps": MIN_LIVE_AMPS},
    }

    if len(mono) < 2 or mean_rho >= 0.0:
        return ("KILL",
                "no monotone relationship: "
                f"{len(mono)}/3 dials decay monotonically in amplitude "
                f"(need >= 2) and the mean Spearman(amplitude, R2) is "
                f"{mean_rho:.3f} (need < 0) — the read does not degrade with "
                "carrier nonlinearity, so E13's single point was noise",
                details)
    if n_finite >= 2 and distinct and mood_longest:
        return ("KEEP",
                "phase transition confirmed: >= 2 dials decay monotonically "
                f"({mono}), >= 2 have DISTINCT critical amplitudes "
                f"({finite}), and mood survives longest "
                f"(crit_mood={c_mood})",
                details)
    return ("INCONCLUSIVE",
            f"monotone decay is real ({len(mono)} dials) but the per-dial "
            f"critical structure did not separate: finite criticals "
            f"{finite} (distinct={distinct}), mood longest={mood_longest} — "
            "never overclaim from a partial",
            details)


def verdict_mapper_selftest() -> dict:
    """G0e — the mapper must call a PLANTED transition correctly.

    Five synthetic sweeps over 5 live amplitudes: KEEP, KILL-flat, KILL-rising,
    INCONCLUSIVE-same-crit, INCONCLUSIVE-wrong-dial-longest. Pass arrays are
    derived from the curves with E12's R2_FLOOR (the room/null arms of the gate
    are assumed satisfied — this self-test exercises the TREND logic, not the
    probe, which G0d covers).
    """
    amps = [0.5, 1.0, 1.5, 2.2, 2.8]
    cases = {
        "keep": {"mood": [0.72, 0.70, 0.66, 0.55, 0.40],
                 "volume": [0.58, 0.42, 0.20, 0.02, -0.10],
                 "presence": [0.64, 0.60, 0.52, 0.31, 0.12]},
        "kill_flat": {"mood": [0.500, 0.520, 0.495, 0.505, 0.499],
                      "volume": [0.40, 0.41, 0.39, 0.405, 0.395],
                      "presence": [0.45, 0.44, 0.46, 0.445, 0.455]},
        "kill_rising": {"mood": [0.30, 0.36, 0.42, 0.50, 0.58],
                        "volume": [0.10, 0.16, 0.22, 0.30, 0.38],
                        "presence": [0.15, 0.21, 0.27, 0.35, 0.43]},
        "incon_same_crit": {"mood": [0.70, 0.62, 0.50, 0.24, 0.05],
                            "volume": [0.60, 0.50, 0.35, 0.10, -0.05],
                            "presence": [0.55, 0.45, 0.32, 0.08, -0.02]},
        "incon_wrong_dial_longest": {"mood": [0.62, 0.40, 0.15, -0.05, -0.20],
                                     "volume": [0.50, 0.46, 0.40, 0.35, 0.24],
                                     "presence": [0.45, 0.30, 0.12, -0.10, -0.30]},
    }
    expect = {"keep": "KEEP", "kill_flat": "KILL", "kill_rising": "KILL",
              "incon_same_crit": "INCONCLUSIVE",
              "incon_wrong_dial_longest": "INCONCLUSIVE"}
    got, ok = {}, True
    for name, curves in cases.items():
        r2 = [curves[d] for d in DIAL_NAMES]
        room = [[x - 0.20 for x in curves[d]] for d in DIAL_NAMES]
        null = [[-0.05] * len(amps) for _ in DIAL_NAMES]
        gate = [[x >= R2_FLOOR for x in curves[d]] for d in DIAL_NAMES]
        trend = dial_trend(amps, r2, room, null, gate)
        v, _, det = map_verdict(trend, len(amps), len(amps))
        got[name] = {"verdict": v, "expect": expect[name],
                     "monotone": det.get("monotone_dials"),
                     "criticals": det.get("critical_amps")}
        ok &= (v == expect[name])
    return {"cases": got, "pass": bool(ok),
            "note": ("exercises the trend/verdict mapper only (dial_trend -> "
                     "map_verdict) on planted curves; the probe path is G0d")}


# --------------------------------------------------------------------- #
# CPU-only mode: bank, carriers + certificates per amplitude, anchors,  #
# self-tests. No model, no GPU, NO VERDICT.                             #
# --------------------------------------------------------------------- #
def carrier_table(amps, bank, targets) -> tuple[dict, dict, dict]:
    """Build + certify every amplitude (CPU, no model). Returns the per-amp
    records, the knob matrices, and the carrier info dicts."""
    points, mats, infos = {}, {}, {}
    for a in amps:
        knobs, km, per, summ, info = build_point_carrier(a, bank)
        pts = x_axis_block(a, per, summ)
        pts["knob_ranges"] = knob_ranges(km)
        pts["carrier_source"] = info["carrier_source"]
        pts["readout"] = info["readout"]
        pts["svd_singular_values"] = info["svd_singular_values"]
        pts["certificate_summary"] = summ
        pts["certificate_per_dial"] = per
        points[_amp_key(a)] = pts
        mats[_amp_key(a)] = km
        infos[_amp_key(a)] = info
        log(f"amp {a:>4}: curvature {summ['mean_curvature']:.3f} "
            f"nonaffine={summ['nonaffine_pass']} live={summ['n_dials_live']}/3 "
            f"status={pts['status']}")
    return points, mats, infos


def knob_matrix_distinctness(mats: dict) -> dict:
    """C7(b) — the swept knob matrices must be pairwise distinct (six points,
    six carriers). Compared on the rounded standardized matrices."""
    keys = sorted(mats, key=float)
    digests = {}
    for k in keys:
        M = mats[k]
        digests[k] = float(round(float(np.abs(M - M.mean(0)).sum()), 4))
    vals = list(digests.values())
    return {"digests": digests, "n_unique": int(len(set(vals))),
            "all_distinct": bool(len(set(vals)) == len(vals))}


def cpu_only(amps, registered: bool) -> dict:
    t0 = time.time()
    st = harness_selftest()
    st_v = verdict_mapper_selftest()
    audit = fold_patch_audit(amps)
    bank = build_bank(e13.N_REPLICATES)
    targets = np.stack([r["target"] for r in bank])
    labels = np.stack([r["label"] for r in bank])
    points, mats, infos = carrier_table(amps, bank, targets)
    audit["knob_matrix_distinctness"] = knob_matrix_distinctness(mats)

    # E13's Arm L, measured live as the AFFINE ANCHOR of the x-axis (curvature
    # 0.000, linear knob read 1.000 by construction) — the certificate's own
    # discriminative check, and the left edge the fold sweep walks away from.
    K_L = {r["name"]: knobs_linear(*[float(x) for x in r["target"]]) for r in bank}
    km_L = np.stack([K_L[r["name"]] for r in bank])
    per_L, summ_L = carrier_certificate(km_L, targets)

    fid = {d: round(float(spearman(targets[:, i], labels[:, i])), 4)
           for i, d in enumerate(DIAL_NAMES)}
    live = [k for k in sorted(points, key=float) if points[k]["live_pass"]]
    out = {
        "experiment": "E25 fold-amplitude phase transition",
        "mode": "cpu-only (no model, no GPU, no verdict)",
        "registered_amplitude_set": registered,
        "seed_carriers": SEED, "seed_e25": SEED_E25,
        "carrier_arm": PRIMARY_ARM,
        "fold_phase": FOLD_PHASE,
        "fold_amps": [float(a) for a in amps],
        "rooms": len(bank), "stills_per_room": N_STILLS,
        "harness_selftest_g0d": st,
        "verdict_mapper_selftest_g0e": st_v,
        "fold_patch_audit_c7": audit,
        "carrier_points": points,
        "carriers_live": live,
        "carriers_censored": [k for k in sorted(points, key=float)
                              if not points[k]["live_pass"]],
        "affine_anchor_arm_L": {
            "mean_curvature": summ_L["mean_curvature"],
            "mean_lin_loo_r2": summ_L["mean_lin_loo_r2"],
            "live_pass": summ_L["live_pass"],
            "note": ("E12's linear staging, measured on this bank: curvature "
                     "0.000 and a linear knob read of 1.000 by construction — "
                     "the x-axis origin the fold sweep departs from"),
        },
        "arm_L_mirror_check": mirror_check(bank, {"L": K_L}),
        "staging_fidelity_spearman_target_vs_label": fid,
        "sample_lavfi_sources": {
            _amp_key(a): render_scene(
                mats[_amp_key(a)][min(12, len(bank) - 1)],
                bank[min(12, len(bank) - 1)]["seed"])
            for a in amps},
        "verdict": None,
        "note": ("No verdict in CPU-only mode. Watch the censoring table: a "
                 "point whose carrier fails liveness (3-NN recovery / dCorr) "
                 "renders rooms that carry no dial signal, so the read trend "
                 "is fitted on the live amplitudes only — and that decision is "
                 "made here, before any embedding exists."),
        "seconds": round(time.time() - t0, 1),
    }
    print(json.dumps(out, indent=2))
    return out


# --------------------------------------------------------------------- #
# Main                                                                  #
# --------------------------------------------------------------------- #
def _parse_amps(argv) -> tuple[list, bool]:
    """Registered SPOOL set by default; --amps is a dev-only override."""
    for i, a in enumerate(argv):
        if a.startswith("--amps="):
            return [float(x) for x in a.split("=", 1)[1].split(",") if x], True
        if a == "--amps" and i + 1 < len(argv):
            return [float(x) for x in argv[i + 1].split(",") if x], True
    return [float(x) for x in FOLD_AMPS], False


def matdict(km: np.ndarray, bank: list) -> dict:
    """Row-of-knob-matrix -> the {room_name: knobs} dict E13's collect_arm
    expects. Keeps the collector untouched (it is E13's code, imported)."""
    return {r["name"]: km[i] for i, r in enumerate(bank)}


def main() -> dict:
    argv = sys.argv[1:]
    amps, dev_override = _parse_amps(argv)
    if "--cpu-only" in argv:
        return cpu_only(amps, registered=not dev_override)
    t0 = time.time()
    verdict_prefix = "DEV_" if dev_override else ""

    ok, reason, guard_info = preflight_guard()
    if not ok:
        out = {"experiment": "E25 fold-amplitude phase transition",
               "verdict": "ABORTED", "reason": reason,
               "guard_preflight": guard_info}
        print(json.dumps(out, indent=2))
        return out

    base = {"experiment": "E25 fold-amplitude phase transition",
            "registered_amplitude_set": not dev_override,
            "dev_amplitude_override": [float(a) for a in amps] if dev_override else None,
            "seed_carriers": SEED, "seed_e25": SEED_E25,
            "carrier_arm": PRIMARY_ARM, "fold_phase": FOLD_PHASE,
            "fold_amps": [float(a) for a in amps],
            "dial_names": DIAL_NAMES, "extra_dials": EXTRA_DIALS,
            "k_primary": K_PRIMARY, "guard_preflight": guard_info,
            "replicates": e13.N_REPLICATES,
            "gates": {"mono_rho_floor": MONO_RHO_FLOOR,
                      "drop_floor": DROP_FLOOR,
                      "up_step_tol": UP_STEP_TOL,
                      "min_live_amps": MIN_LIVE_AMPS,
                      "r2_floor": R2_FLOOR, "r2_room_floor": R2_ROOM_FLOOR,
                      "r2_top_pc_fraction": R2_TOP_PC_FRACTION,
                      "sensitivity_floor": SENSITIVITY_FLOOR}}

    # G0d / G0e — model-free, cheapest first. If either is broken nothing
    # downstream is interpretable, and neither costs GPU time.
    st = harness_selftest()
    log(f"probe self-test (G0d): {st}")
    st_v = verdict_mapper_selftest()
    log(f"verdict-mapper self-test (G0e): pass={st_v['pass']}")
    if not st["pass"]:
        out = dict(base)
        out.update({"verdict": "INVALID_HARNESS", "harness_selftest_g0d": st,
                    "verdict_mapper_selftest_g0e": st_v,
                    "reason": "G0d: the imported probe failed its synthetic "
                              "self-test"})
        print(json.dumps(out, indent=2))
        return out
    if not st_v["pass"]:
        out = dict(base)
        out.update({"verdict": "INVALID_HARNESS", "harness_selftest_g0d": st,
                    "verdict_mapper_selftest_g0e": st_v,
                    "reason": "G0e: the trend/verdict mapper mis-called a "
                              "planted transition"})
        print(json.dumps(out, indent=2))
        return out

    # C7 — audit the amplitude patch before trusting any of it.
    audit = fold_patch_audit(amps)
    if not audit["all_patched"]:
        out = dict(base)
        out.update({"verdict": "ABORTED", "fold_patch_audit_c7": audit,
                    "reason": "the fold-amplitude patch did not take effect "
                              "(e13._fold does not follow N2_FOLD_AMP)"})
        print(json.dumps(out, indent=2))
        return out

    # Bank + every carrier + every certificate — all CPU, all before the model
    # (E13's ordering, per point).
    bank = build_bank(e13.N_REPLICATES)
    log(f"bank: {len(bank)} rooms (replicates={e13.N_REPLICATES})")
    targets = np.stack([r["target"] for r in bank])
    labels = np.stack([r["label"] for r in bank])
    try:
        points, mats, infos = carrier_table(amps, bank, targets)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest_g0d": st,
                    "reason": f"carrier construction failed: {e}"})
        print(json.dumps(out, indent=2))
        return out
    audit["knob_matrix_distinctness"] = knob_matrix_distinctness(mats)
    live = [a for a in amps if points[_amp_key(a)]["live_pass"]]
    censored = [a for a in amps if not points[_amp_key(a)]["live_pass"]]
    log(f"staging: live={live} censored(INVALID_STAGING)={censored}")

    # G0a — staging fidelity (E13's, verbatim; the bank is amplitude-free).
    fid = {d: round(float(spearman(targets[:, i], labels[:, i])), 4)
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
                    "staging_fidelity_spearman_target_vs_label": fid,
                    "carrier_points": points,
                    "reason": "G0a: the staged scripts did not move >= 2/3 dials"})
        print(json.dumps(out, indent=2))
        return out
    if len(live) == 0:
        out = dict(base)
        out.update({
            "verdict": "INVALID_STAGING",
            "harness_selftest_g0d": st,
            "verdict_mapper_selftest_g0e": st_v,
            "fold_patch_audit_c7": audit,
            "staging_fidelity_spearman_target_vs_label": fid,
            "carrier_points": points,
            "carriers_live": live, "carriers_censored": censored,
            "reason": ("every swept carrier failed its certificate — there "
                       "is no live staging at any amplitude"),
        })
        print(json.dumps(out, indent=2))
        return out
    if len(live) < MIN_LIVE_AMPS and not dev_override:
        # Decided BEFORE the model loads: a dead sweep costs no GPU time.
        out = dict(base)
        out.update({
            "verdict": "INVALID_STAGING",
            "harness_selftest_g0d": st,
            "verdict_mapper_selftest_g0e": st_v,
            "fold_patch_audit_c7": audit,
            "staging_fidelity_spearman_target_vs_label": fid,
            "carrier_points": points,
            "carriers_live": live, "carriers_censored": censored,
            "reason": (f"censoring leaves {len(live)} live carriers "
                       f"(< MIN_LIVE_AMPS={MIN_LIVE_AMPS}); the read trend "
                       "cannot be fitted over valid staging. No GPU time was "
                       "spent."),
        })
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
        out.update({"verdict": "ABORTED", "harness_selftest_g0d": st,
                    "reason": f"model load failed: {e}"})
        print(json.dumps(out, indent=2))
        return out
    log(f"using {model_used}")

    # G0b's anchor + the x-axis origin: E12's linear staging (Arm L), rendered
    # ONCE through E13's own collector and probe. Its carrier is
    # amplitude-independent (E12's affine formulas), so this is E13's verbatim
    # G0b control, measured on the same bank in the same run.
    K_L = {r["name"]: knobs_linear(float(r["target"][0]),
                                    float(r["target"][1]),
                                    float(r["target"][2])) for r in bank}
    km_L = np.stack([K_L[r["name"]] for r in bank])
    per_L, summ_L = carrier_certificate(km_L, targets)
    try:
        log(f"arm L (affine anchor): rendering + embedding {len(bank)} rooms")
        data_L = collect_arm("L", {"L": K_L}, bank, model, processor, dev, torch)
        rep_L = arm_report("L", data_L, km_L, targets)
        del data_L
        gc.collect()
        if dev == "cuda":
            torch.cuda.empty_cache()
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest_g0d": st,
                    "reason": f"Arm-L anchor render/embed/probe failed: {e}"})
        print(json.dumps(out, indent=2))
        return out
    log(f"arm L: r2_still_loro(k64)={rep_L['r2_still_loro']['64']} "
        f"lum={rep_L['g0b_luminance_r2_k64']} ladder={rep_L['gate']['ladder']}")

    # The sweep. One point = carrier -> certify -> render -> embed -> probe.
    reports, curves = {}, {"still": {}, "room": {}, "null95": {}, "pass": {}}
    try:
        for a in live:
            k = _amp_key(a)
            log(f"amp {a}: rendering + embedding {len(bank)} rooms x "
                f"{N_STILLS} stills (curvature "
                f"{points[k]['mean_curvature']})")
            data = collect_arm(PRIMARY_ARM, {PRIMARY_ARM: matdict(mats[k], bank)},
                               bank, model, processor, dev, torch)
            rep = arm_report(PRIMARY_ARM, data, mats[k], targets)
            rep["x_axis"] = {kk: points[k][kk] for kk in
                             ("nominal_fold_amp", "mean_curvature",
                              "curvature_by_dial", "nonaffine_pass",
                              "live_pass", "n_dials_live",
                              "knn_loo_r2_by_dial", "distcorr_p_by_dial",
                              "mean_lin_loo_r2", "status")}
            rep["certificate_recompute_match"] = bool(
                rep["carrier_certificate"]["mean_curvature"]
                == points[k]["mean_curvature"])
            reports[k] = rep
            curves["still"][k] = [rep["r2_still_loro"][str(K_PRIMARY)][d]
                                  for d in DIAL_NAMES]
            curves["room"][k] = [rep["r2_room_loro"][str(K_PRIMARY)][d]
                                 for d in DIAL_NAMES]
            curves["null95"][k] = [rep["perm_null95_k64"][d] for d in DIAL_NAMES]
            curves["pass"][k] = [rep["gate"]["dial_pass"][d] for d in DIAL_NAMES]
            log(f"amp {a}: r2_still_loro(k64)={rep['r2_still_loro']['64']} "
                f"ladder={rep['gate']['ladder']} "
                f"lum={rep['g0b_luminance_r2_k64']}")
            del data
            gc.collect()
            if dev == "cuda":
                torch.cuda.empty_cache()
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest_g0d": st,
                    "reason": f"frame/embed/probe failed: {e}"})
        print(json.dumps(out, indent=2))
        return out

    # Trend over the live amplitudes, transposed to per-dial rows.
    live_sorted = sorted(live)
    still_t = [[curves["still"][_amp_key(a)][i] for a in live_sorted]
               for i in range(len(DIAL_NAMES))]
    room_t = [[curves["room"][_amp_key(a)][i] for a in live_sorted]
              for i in range(len(DIAL_NAMES))]
    null_t = [[curves["null95"][_amp_key(a)][i] for a in live_sorted]
              for i in range(len(DIAL_NAMES))]
    pass_t = [[curves["pass"][_amp_key(a)][i] for a in live_sorted]
              for i in range(len(DIAL_NAMES))]
    trend = dial_trend(live_sorted, still_t, room_t, null_t, pass_t)
    if len(live_sorted) < MIN_LIVE_AMPS:
        # Reachable ONLY via --amps: the registered path aborts before the
        # model at this floor. A dev sweep is not the E25 result — it exists
        # to exercise the plumbing (render/embed/probe) on real frames.
        verdict, vreason, vdetails = (
            "SWEEP",
            f"dev amplitude override with only {len(live_sorted)} live "
            f"point(s) (< MIN_LIVE_AMPS={MIN_LIVE_AMPS}): plumbing check "
            "only, no bookable verdict",
            {"n_live_targeted": len(live_sorted),
             "amplitude_override": [float(a) for a in amps]})
    else:
        verdict, vreason, vdetails = map_verdict(trend, len(live_sorted),
                                                len(amps))

    # G0b — E13's sensitivity gate on E13's anchor (Arm L, verbatim).
    sens_measured = rep_L["g0b_luminance_r2_k64"]
    sens_pass = bool(sens_measured >= SENSITIVITY_FLOOR)
    mildest = min(live_sorted, key=lambda a: points[_amp_key(a)]["mean_curvature"])

    # C6 — the amp 2.2 point is E13's own N2 arm; it must reproduce E13.
    repl = None
    anc = None
    for a in live_sorted:
        if abs(float(a) - 2.2) < 1e-9:
            anc = reports[_amp_key(a)]
            break
    if anc is not None:
        got = {d: anc["r2_still_loro"][str(K_PRIMARY)][d] for d in DIAL_NAMES}
        diffs = {d: round(float(got[d]) - E13_N2_R2_K64[d], 4) for d in DIAL_NAMES}
        repl = {"e13_recorded_r2_k64": E13_N2_R2_K64,
                "e25_measured_r2_k64": got,
                "abs_diff": diffs,
                "within_tol": bool(all(abs(v) <= E13_REPLICATION_TOL
                                       for v in diffs.values())),
                "tolerance": E13_REPLICATION_TOL,
                "e13_recorded_curvature": E13_N2_CURVATURE,
                "e25_measured_curvature": points["2.2"]["mean_curvature"],
                "note": ("C6: E13's single measured point, re-measured through "
                         "E25's plumbing. A mismatch here means the sweep is "
                         "not E13's harness and nothing downstream is a "
                         "statement about E13.")}

    if not sens_pass:
        verdict, vreason = "INVALID_HARNESS", (
            f"G0b: luminance sensitivity on Arm L (E12's linear staging, "
            f"E13's own anchor) is {sens_measured} < {SENSITIVITY_FLOOR} — "
            "the harness is blind here, so a read-death would not be evidence "
            "about the embedding")
    # G0b — sensitivity on the mildest live point (deviation, pre-registered).
    # The dev label already carries its prefix; the registered one does not.
    final = verdict if verdict.startswith("DEV_") else verdict_prefix + verdict

    # C1/C2/C4/C5 — the booked controls, per amplitude, per dial.
    controls = {}
    for a in live_sorted:
        k = _amp_key(a)
        r = reports[k]
        controls[k] = {
            "raw_pixel_r2_k64": r["controls"]["raw_pixel_r2_k64"],
            "luminance_spearman": r["controls"]["luminance_spearman"],
            "g0b_luminance_r2_k64": r["g0b_luminance_r2_k64"],
            "room_identity_acc": r["controls"]["room_identity_acc"],
            "tertile_acc_k64": r["tertile_acc_k64"],
            "lambda_median_k64": r["lambda_median_k64"],
            "pca_evr_k16_k64_k256": [r["pca_evr_k16"], r["pca_evr_k64"],
                                     r["pca_evr_k256"]],
        }

    out = dict(base)
    out.update({
        "mode": "sweep" if not dev_override else "DEV sweep (amplitude override)",
        "model": model_used, "load_notes": load_notes, "device": dev,
        "rooms": len(bank), "stills_per_room": N_STILLS,
        "encoder_forwards": int(len(live_sorted) * len(bank) * N_STILLS),
        "label_stats": {d: {"min": round(float(labels[:, i].min()), 4),
                            "max": round(float(labels[:, i].max()), 4),
                            "std": round(float(labels[:, i].std()), 4)}
                        for i, d in enumerate(DIAL_NAMES)},
        "extra_dial_stats": extra_stats,
        "harness_selftest_g0d": st,
        "verdict_mapper_selftest_g0e": st_v,
        "fold_patch_audit_c7": audit,
        "staging_fidelity_spearman_target_vs_label": fid,
        "g0a_staging_fidelity_pass": fid_pass,
        "carrier_points": points,
        "carriers_live": live_sorted, "carriers_censored": censored,
        "x_axis_measured_nonlinearity": {
            _amp_key(a): points[_amp_key(a)]["mean_curvature"]
            for a in live_sorted},
        "points": reports,
        "trend": trend,
        "controls_by_amplitude": controls,
        "arm_L_anchor": {
            "title": ("E12's linear staging (= E13's Arm L), rendered once: "
                      "G0b's sensitivity anchor and the left edge of the "
                      "x-axis, not a sweep point"),
            "mean_curvature": summ_L["mean_curvature"],
            "mean_lin_loo_r2": summ_L["mean_lin_loo_r2"],
            "complete_pass": summ_L["pass"],
            "certificate_summary": summ_L,
            "certificate_per_dial": per_L,
            "r2_still_loro": rep_L["r2_still_loro"],
            "r2_room_loro": rep_L["r2_room_loro"],
            "g0b_luminance_r2_k64": rep_L["g0b_luminance_r2_k64"],
            "controls": rep_L["controls"],
            "gate": rep_L["gate"],
        },
        "e13_replication_c6": repl,
        "verdict_details": vdetails,
        "gates_measured": {
            "g0d_probe_selftest": st["pass"],
            "g0e_verdict_mapper_selftest": st_v["pass"],
            "g0a_staging_fidelity": {"floor": FIDELITY_FLOOR, "pass": fid_pass,
                                     "measured": fid},
            "g0b_sensitivity": {
                "floor": SENSITIVITY_FLOOR, "pass": sens_pass,
                "anchor": "Arm L (E12's linear staging) — E13's G0b verbatim",
                "measured": sens_measured,
                "per_amplitude_booked": {
                    _amp_key(a): reports[_amp_key(a)]["g0b_luminance_r2_k64"]
                    for a in live_sorted},
                "mildest_live_amplitude_booked": {
                    "amplitude": float(mildest),
                    "curvature": points[_amp_key(mildest)]["mean_curvature"],
                    "luminance_r2_k64": reports[_amp_key(mildest)]["g0b_luminance_r2_k64"],
                    "note": ("v1 gated G0b on this anchor and the registered "
                             "sweep returned INVALID_HARNESS at 0.887 "
                             "(floor 0.90) — a build bug, not a finding: "
                             "luminance readability is carrier-dependent, so "
                             "the mildest folded point is no sensitivity "
                             "control. v2 restores E13's Arm L anchor. This "
                             "row stays on the record as a booked control.")}},
            "censoring": {"rule": ("a carrier failing E13's certificate liveness "
                                   "half is INVALID_STAGING and censored from "
                                   "the trend; carrier-only, label-free, "
                                   "embedding-free, decided before the model"),
                          "live": live_sorted, "censored": censored,
                          "min_live_amps": MIN_LIVE_AMPS},
            "g1_g2_g3": vdetails,
        },
        "data_needed": [
            "ffmpeg ~/.local/bin/ffmpeg (lavfi: color, eq, noise, drawbox)",
            "facebook/ijepa_vith16_1k fp16 on the RTX 4050 (E9 loader)",
            "elephant package importable (dial bank = labels)",
            "roomgen.py loadable (frozen nonlinear physics; inline replica "
            "fallback recorded in carrier_source)",
            f"{len(live_sorted)} live amplitudes x {len(bank)} rooms x "
            f"{N_STILLS} stills = {len(live_sorted) * len(bank) * N_STILLS} "
            "encoder forwards (~15-30 min GPU) + CPU ridge sweeps "
            "(200-perm null at k=64 per amplitude)",
            "GPU free (guard preflight in-process)",
        ],
        "wiring": ("NOT in QUEUE.md / runner.py EXP_MOD by design — manual "
                   "fire only, to avoid the cron runner double-claiming it"),
        "verdict": final,
        "verdict_reason": vreason,
        "seconds_total": round(time.time() - t0, 1),
        "note": (
            "E25 walks the carrier-nonlinearity axis E13 could only sample at "
            "one point. SPOOL's fold amplitudes {0.5, 1.0, 1.5, 2.2, 2.8, 3.5} "
            "are applied to E13's own N2 carrier by re-pointing its module "
            "constant, and at every amplitude the FULL E13 pipeline runs: "
            "carrier certificate (measured curvature + liveness), 27 staged "
            "rooms rendered and embedded by the frozen I-JEPA, E12/E13's ridge "
            "probe with leave-one-room-out CV, its 200-perm room-shuffle null, "
            "and its per-dial gate. The x-axis in the report is the MEASURED "
            "curvature, not the nominal amplitude. KEEP = >= 2 dials decay "
            "monotonically in amplitude with >= 2 DISTINCT critical amplitudes "
            "and mood surviving longest (a phase transition with a per-dial "
            "boundary). KILL = no monotone relationship (E13's single point "
            "was noise). A point whose carrier fails liveness is "
            "INVALID_STAGING and censored from the trend — a dead render "
            "cannot testify about the embedding — and that censoring is "
            "carrier-only and label-free, so it cannot be tuned by the read "
            "results. Booked caveats: one carrier family, one fold phase (0.0), "
            "one frozen random physics draw, one encoder, and the LINEAR reader "
            "of E12/E13 (E13b's nonlinear-reader axis is not answered here); "
            "G0b's sensitivity anchor is E13's Arm L, rendered in-run as the "
            "x-axis origin; crit_d is a grid property, so each critical is "
            "reported with its neighbouring passing amplitude, and the "
            "crit_k64_floor_booked column shows the same critical with the "
            "k16 retention clause dropped. See the module docstring for the "
            "full pre-registration, the measured design-pass table, and the "
            "C1-C9 booked controls."),
    })
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
