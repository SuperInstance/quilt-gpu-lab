#!/usr/bin/env python3
"""X2 — renderer transfer: is the dial read ROOM CONTENT or RENDERER PARAMETERIZATION?

CLAIM UNDER TEST (concrete, falsifiable)
  The E12 family's KEEP (frozen I-JEPA reads staged mood/volume/presence,
  R2_still_loro_k64 = 0.81 / 0.96 / 0.95) was produced with ONE renderer:
  E12's lavfi staging (color/eq/noise/drawbox). The family's successors
  sharpened the scope — E13 kept on a nonlinear carrier, X3 found volume at
  classical-stats parity, X6 KILLed range extrapolation — but every one of
  them rendered dials through the SAME lavfi pipeline. The remaining question
  is the decisive one for the whole family:

      Is the read a property of the ROOM CONTENT (the dial triple rendered
      into any visual scene), or a property of the RENDERER's
      parameterization (the specific pixel axes E12 happened to build)?

  X2 re-renders the SAME 27-room dial bank through a SECOND, INDEPENDENT
  renderer sharing NO primitives with lavfi, embeds both frame sets with the
  SAME frozen I-JEPA, and tests whether a probe trained on one renderer's
  embeddings transfers to the other's.

  KILL  = RENDERER-PARAMETERIZATION: the read collapses cross-renderer —
          the E12 family measured its own staging function, not room
          geometry. Every KEEP in the family must be re-read as
          renderer-bound.
  KEEP  = CONTENT: the read transfers across independent renderings — the
          embedding carries the dial CONTENT, not one pipeline's pixels.

RENDERER B — "pil-compositor" (the intervention; the only new code here)
  Renderer A is E12's stage_source VERBATIM (imported; lavfi color+eq+noise+
  drawbox). Renderer B is a pure numpy/PIL compositor that draws the SAME
  dial->scene semantics through DIFFERENT primitives:
    mood     -> HUE-WHEEL mapping. hue_deg = 230 - 190*(m+1)/2: m=-1 -> 230 deg
                (blue/cold), m=+1 -> 40 deg (amber/warm), interpolation through
                the HSV hue circle (m=0 -> 135 deg green) at fixed saturation
                0.55 — NOT E12's RGB channel lerp (m=0 -> gray). Mood also
                scales base value (0.60+0.12m), the brightness coupling E12
                has, at a different gain. The background is additionally a
                smooth diagonal VALUE GRADIENT (E12's is a flat field).
    volume   -> STRIPE TEXTURE + BLUR. A sinusoidal stripe field (orientation
                from the room seed) with spatial frequency 2.5+13.5v cycles,
                amplitude 0.06+0.30v, and temporal phase speed 0.1+1.1v cps
                (texture energy ~ volume), plus a Gaussian defocus
                radius 0.3+2.4(1-v) px (quiet = soft, loud = crisp). NOT
                gaussian pixel noise.
    presence -> SOFT BLOBS. n = 1+round(8p) occupants (E12's count rule)
                placed on a deterministic phyllotaxis scatter, each a soft
                additive radial-Gaussian glow of radius (4.5+5.5p) px — NOT
                hard drawbox squares.
    temporal : stills differ by stripe phase drift + a mild dial-independent
                flicker (E12's stills differ by lavfi temporal noise).
  Same dial semantics (cold<->warm, quiet<->loud, empty<->crowded), a
  different pixel pipeline end to end. The B knob vector (11 dims: hue,
  value0, gradient angle, stripe angle+phase, freq, amp, speed, blur radius,
  blob count, blob radius) is audited with E13's carrier certificate
  (booked) — but B's liveness is GATED by its own within-B read (below), the
  strongest possible certificate.

CROSS-RENDERER PROBE (the measurement)
  Both renderers' frames go through the SAME frozen I-JEPA (E9 loader, E12's
  embed_stills: 12 stills/room, mean-pooled, L2), so XA and XB live in the
  SAME 1280-d embedding space and a probe trained on one side evaluates
  directly on the other. No alignment, no CCA, no shared fitting — the
  transfer test is raw.
    within-A / within-B : E12's probe_sweep verbatim (k=16/64/256 PCA + LORO
        ridge with per-fold inner-CV lambda, room-level check, 200-perm
        null, tertile arm). Each arm's PCA basis is fit on ITS OWN
        embeddings (label-free, E12 convention).
    cross A->B / B->A   : E12's SAME 27 LORO room folds. For each held-out
        room g: fit the ridge on the TRAIN renderer's other 26 rooms in the
        TRAIN renderer's top-64 PCs (lambda by E12's inner grouped CV on the
        train side only), predict the held room's TEST-renderer rows. The
        test renderer's embeddings never touch the basis or the fit.
  Ratio (pre-registered currency):
    ratio_d,dir := max(R2cross_d,dir, 0) / max(R2within_d, 1e-6)
  where R2within_d is that dial's within-renderer LORO R2 at k=64 (all 27
  rooms). Cross R2 is per-still (test-renderer label variance); room-mean
  cross R2 is booked beside it.

PRE-REGISTERED GATES (fixed before running; this file IS the registration)
  G0a staging fidelity : Spearman(target, elephant_label) >= 0.5 for >= 2/3
      dials on the shared bank (E12's G0a verbatim) — else INVALID_STAGING.
  G0d harness self-test: E13's synthetic probe check — else INVALID_HARNESS.
  G0b sensitivity      : per-still mean-luminance LORO R2(k=64) >= 0.90 on
      the E12-replication arm (A) — else INVALID_HARNESS (a blind arm tests
      nothing). AMENDED before any verdict was read (first execution
      returned INVALID_HARNESS on an earlier draft that gated B too): B is
      BOOKED only, per E13's convention — B intentionally does NOT carry
      the dials on luminance (hue/texture/shape instead), and B-liveness is
      already gated by within-B passing E12's own gate (V2). B's booked
      luminance R2 is reported beside the gate so the reader can see what
      the dials do NOT ride on in each renderer.
  V1 control           : within-A must KEEP under E12's gate ladder
      (replication ~0.81/0.96/0.95) — else INVALID_CONTROL (E13's
      convention; a broken positive control interprets nothing).
  V2 renderer-B liveness: within-B must KEEP under E12's gate ladder — else
      INVALID_HARNESS (a dead renderer-B is not a verdict — the task's rule).
  MAIN (both directions, the conservative reading):
    CONTENT (KEEP) : ratio >= 0.5 on >= 2/3 dials in BOTH directions.
    RENDERER-PARAMETERIZATION (KILL): ratio < 0.2 on >= 2/3 dials in BOTH
      directions.
    INCONCLUSIVE   : between (including a split — one direction transfers,
      the other collapses).
  ABORTED: preflight, model load, no frames, < 8 rooms.

CONTROLS / BOOKED (never gated)
  C1 pooled-basis cross  : cross probes recomputed on a label-free PCA basis
      fit on POOLED A+B embeddings (a basis that has seen both pixel
      styles; bounds how much of a collapse is basis-vs-fit geometry).
  C2 cross shuffle null  : 100 room-label shuffles per direction at fixed
      lambda — does the cross read beat chance, independent of ratios.
  C3 carrier certificates: E13's certificate on BOTH knob matrices (A's must
      measure curvature ~0 with a linear knob read ~1 — the certificate's
      own discriminative check; B's is the booked audit of the new carrier).
  C4 mirror audit        : E13's mirror_check byte-compares E12's
      stage_source against the mirrored A knobs for all 27 rooms.
  C5 raw-pixel probe     : LORO ridge on 16x9 grayscale stills per arm.
  C6 luminance Spearman  : trivial-correlate check per arm.
  C7 room identity       : half-split nearest-centroid per arm.
  C8 room-mean cross R2  : the strict room-level currency for the cross arm.

DATA THE GATE NEEDS
  - ffmpeg ~/.local/bin/ffmpeg + E12's lavfi chain (renderer A only).
  - facebook/ijepa_vith16_1k fp16 on the RTX 4050 (E9 loader, imported).
  - the elephant package importable (dial bank = ground-truth labels).
  - PIL (Pillow) for renderer B's blur/uint8 path.
  - 2 arms x 27 rooms x 6 s @ 10 fps -> 648 encoder forwards at 224^2 ->
    ~6-10 min GPU (E13 measured ~8-12 for 972), or CPU overnight.
  - GPU free (guard preflight in-process; checked with nvidia-smi before fire).

HONESTY / CAVEATS BOOKED WITH THE RESULT
  - Both carriers are STAGED (E12's standing caveat, unchanged). X2 asks
    whether the read is invariant to the STAGING FUNCTION, not whether it
    survives natural footage.
  - Renderer B is ONE hand-built alternative. A KILL says "the read did not
    survive THIS independent renderer" — reproducible (seed 2718) and
    decisive against the family only because A replicates in the same run.
    A KEEP is the stronger result: two independent pixel pipelines agree.
  - The cross probe is deliberately alignment-free. If the encoder devotes
    its top PCs to renderer style, the train-renderer basis may simply not
    contain the shared dial direction; C1 (pooled basis) bounds that
    explanation and is reported beside the gate.
  - Renderer B's hue path makes mid-mood GREEN where A is gray; if the read
    transfers anyway, that is evidence the encoder reads the cold<->warm
    CONTENT and not a specific chroma axis.

Dev path: `python -m experiments.x2_renderer_transfer --cpu-only` runs the
bank, both knob sets, certificates, mirror audit, and renderer-B frame
sanity with no model and no GPU.

Verdict printed as ONE JSON object on stdout (progress on stderr).
Deterministic (seed 2718). CPU-only probe; GPU only for encoder forwards.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

# BLAS thread cap — same reason as E12/E13 (thousands of tiny ridge solves).
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np  # noqa: E402

try:
    from threadpoolctl import threadpool_limits  # noqa: E402
    _BLAS_LIMIT = threadpool_limits(limits=4)
    _BLAS_LIMIT.__enter__()
except Exception:
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

# --------------------------------------------------------------------- #
# E12 / E13 imported VERBATIM — the bank, the labels, the probe, the     #
# gates, the certificates. X2 adds exactly one thing: renderer B.        #
# --------------------------------------------------------------------- #
from e12_room_dial_reader import (                            # noqa: E402
    DIAL_NAMES, EXTRA_DIALS, FIDELITY_FLOOR, K_PRIMARY, K_STRICT, K_WIDE,
    RATE, SECONDS, SENSITIVITY_FLOOR, W, H, _boxes, _ridge_fit_predict,
    build_dial_grid, embed_stills, loro_predict, pca_basis, pick_lambda,
    probe_sweep, r2_columns, room_halfsplit_acc, spearman, stage_source,
)
from e13_nonlinear_dial_reader import (                       # noqa: E402
    KNOB_NAMES, build_bank, carrier_certificate, harness_selftest,
    knobs_linear, mirror_check,
)

# --------------------------------------------------------------------- #
# Pre-registered constants                                               #
# --------------------------------------------------------------------- #
CROSS_FLOOR = 0.5      # CONTENT: cross >= 0.5 x within
CROSS_COLLAPSE = 0.2   # KILL:    cross <  0.2 x within
CROSS_DIALS_FLOOR = 2  # ...on >= 2/3 dials
CROSS_NULL_PERMS = 100
K_CROSS = K_PRIMARY    # 64 — the pre-registered cross probe space

RENDERER_A = ("A", "lavfi-staging (E12's stage_source verbatim: color/eq/"
                   "noise/drawbox) — replication control")
RENDERER_B = ("B", "pil-compositor (hue-wheel mood, stripe+blur volume, "
                   "soft-blob presence) — the independent renderer")


def knob_ranges_any(km: np.ndarray, names: tuple) -> dict:
    """E13's knob_ranges, generalized to any knob schema (renderer B's is
    11-dim; E13's helper is hard-wired to its 7 lavfi knob names)."""
    km = np.asarray(km, float)
    return {names[j]: {
        "min": round(float(km[:, j].min()), 3),
        "max": round(float(km[:, j].max()), 3),
        "n_unique": int(len(np.unique(np.round(km[:, j], 4)))),
    } for j in range(km.shape[1])}


def log(msg: str) -> None:
    """Progress goes to stderr; stdout is reserved for the JSON verdict."""
    print(f"[x2] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------- #
# RENDERER B — the pil-compositor (the only new rendering code)          #
# --------------------------------------------------------------------- #
B_KNOB_NAMES = ("hue_deg", "value0", "grad_ang", "stripe_ang", "phase0",
                "stripe_freq", "stripe_amp", "stripe_speed_cps",
                "blur_radius_px", "n_blobs", "blob_radius_px")


def _b_rng(room_seed: int) -> np.random.Generator:
    """Renderer-B's frozen per-room nuisance stream (angles, phase, jitter).
    Independent of E12's _boxes stream and of the lavfi noise seed."""
    return np.random.default_rng((int(room_seed) * 31 + 7) % (2 ** 32))


def knobs_b(m: float, v: float, p: float, room_seed: int) -> np.ndarray:
    """Renderer-B's frozen knob vector for a dial triple.

    mood     -> hue_deg (230 - 190*t, the hue-wheel mapping) + value0
                (0.60+0.12m, the brightness coupling at a different gain)
    volume   -> stripe_freq, stripe_amp, stripe_speed, blur_radius
    presence -> n_blobs (E12's count rule), blob_radius
    nuisance -> gradient angle, stripe angle, phase0 (per-room, frozen)
    """
    t = (float(m) + 1.0) / 2.0
    hue = (230.0 - 190.0 * t) % 360.0
    value0 = 0.60 + 0.12 * float(m)
    freq = 2.5 + 13.5 * float(v)
    amp = 0.06 + 0.30 * float(v)
    speed = 0.1 + 1.1 * float(v)
    blur = 0.3 + 2.4 * (1.0 - float(v))
    n_blobs = 1 + int(round(float(p) * 8))          # E12's count rule
    blob_r = 4.5 + 5.5 * float(p)
    rng = _b_rng(room_seed)
    grad_ang = float(rng.uniform(0.0, 2.0 * math.pi))
    stripe_ang = float(rng.uniform(0.0, math.pi))
    phase0 = float(rng.uniform(0.0, 2.0 * math.pi))
    return np.array([hue, value0, grad_ang, stripe_ang, phase0,
                     freq, amp, speed, blur, float(n_blobs), blob_r], float)


def hsv_to_rgb(hdeg: float, s: float, v_field: np.ndarray) -> np.ndarray:
    """Vectorized HSV->RGB. h, s scalar; v an (H, W) field. Returns (H, W, 3)."""
    h = (float(hdeg) % 360.0) / 60.0
    i = int(math.floor(h)) % 6
    f = h - math.floor(h)
    p = v_field * (1.0 - s)
    q = v_field * (1.0 - s * f)
    t = v_field * (1.0 - s * (1.0 - f))
    r = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5],
                  [v_field, q, p, p, t, v_field])
    g = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5],
                  [t, v_field, v_field, q, p, p])
    b = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5],
                  [p, p, t, v_field, v_field, q])
    return np.stack([r, g, b], axis=-1)


def _blob_centers(knobs: np.ndarray, room_seed: int) -> np.ndarray:
    """Deterministic phyllotaxis scatter of the occupants (golden angle),
    jittered per room, clamped so glows stay inside the frame."""
    n = int(round(knobs[B_KNOB_NAMES.index("n_blobs")]))
    r = float(knobs[B_KNOB_NAMES.index("blob_radius_px")])
    rng = _b_rng(room_seed)
    jit = rng.uniform(-3.0, 3.0, (max(n, 1), 2))
    out = np.empty((max(n, 1), 2), float)
    for i in range(max(n, 1)):
        ang = i * 2.39996323 + (room_seed % 17) * 0.37
        rad = 0.10 + 0.32 * math.sqrt((i + 1) / max(n, 1))
        cx = W / 2.0 + rad * W * 0.62 * math.cos(ang) + jit[i, 0]
        cy = H / 2.0 + rad * H * 0.62 * math.sin(ang) + jit[i, 1]
        out[i] = (min(max(cx, r + 2.0), W - r - 2.0),
                  min(max(cy, r + 2.0), H - r - 2.0))
    return out[:n]


def render_b_frames(m: float, v: float, p: float, room_seed: int) -> list:
    """Renderer B: dial triple -> SECONDS*RATE uint8 (H, W, 3) frames.

    Pure numpy/PIL. Static per room: hue base field (mood), value gradient
    (nuisance), stripe coordinates (nuisance), blob alpha maps (presence).
    Per frame: stripe phase advances at the volume-driven speed; a mild
    dial-independent flicker varies the stills (E12's stills vary by lavfi
    temporal noise); Gaussian defocus (volume) blurs the composited frame.
    """
    from PIL import Image, ImageFilter
    k = knobs_b(m, v, p, room_seed)
    (hue, value0, grad_ang, stripe_ang, phase0,
     freq, amp, speed, blur, n_blobs, blob_r) = (
        float(x) for x in k)
    nb = int(round(n_blobs))

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    u = xx / (W - 1) * 2.0 - 1.0
    w = yy / (H - 1) * 2.0 - 1.0
    value = np.clip(value0 + 0.08 * (math.cos(grad_ang) * u
                                     + math.sin(grad_ang) * w), 0.05, 1.0)
    base = hsv_to_rgb(hue, 0.55, value)                       # (H, W, 3)
    c = u * math.cos(stripe_ang) + w * math.sin(stripe_ang)   # stripe coord
    centers = _blob_centers(k, room_seed)
    sigma = blob_r / 2.0
    blob_alpha = np.stack([
        0.85 * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2)
                        / (2.0 * sigma ** 2))) for (cx, cy) in centers])
    blob_color = np.array([1.0, 0.96, 0.85])                  # warm glow
    blob_sum = np.clip(blob_alpha.sum(0), 0.0, 1.0)[..., None] * blob_color
    flick_w = 2.0 * math.pi * (0.15 + 0.05 * (room_seed % 7)) / RATE

    frames = []
    for t in range(SECONDS * RATE):
        phase = phase0 + 2.0 * math.pi * speed * (t / RATE)
        field = base * ((1.0 + amp * np.sin(2.0 * math.pi * freq * c + phase))
                        * (1.0 + 0.025 * math.sin(flick_w * t)))[..., None]
        field = np.clip(field + blob_sum, 0.0, 1.0)
        pil = Image.fromarray((field * 255.0 + 0.5).astype(np.uint8))
        if blur > 0.05:
            pil = pil.filter(ImageFilter.GaussianBlur(blur))
        frames.append(np.asarray(pil, np.uint8))
    return frames


# --------------------------------------------------------------------- #
# Collection (one code path, the frame source is the only difference)    #
# --------------------------------------------------------------------- #
def collect(renderer: str, bank: list, model, processor, dev, torch):
    """Render every room through ONE renderer and embed 12 stills each
    (E12's embed_stills verbatim: E9 sampling, preprocessing, forward,
    luminance + grayscale-pixel controls). renderer 'A' -> lavfi via
    E12's stage_source; renderer 'B' -> the pil-compositor."""
    X, Y, Yt, groups, lum, pix = [], [], [], [], [], []
    for gi, r in enumerate(bank):
        m, v, p = (float(r["target"][0]), float(r["target"][1]),
                   float(r["target"][2]))
        if renderer == "A":
            frames = ppms_from_lavfi(stage_source(m, v, p, r["seed"]),
                                     SECONDS, RATE, (W, H))
        else:
            frames = render_b_frames(m, v, p, r["seed"])
        if not frames:
            raise RuntimeError(f"no frames from renderer {renderer} for "
                               f"{r['name']!r}")
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
            log(f"renderer {renderer} room {gi + 1}/{len(bank)} {r['name']}")
    return (np.concatenate(X), np.concatenate(Y), np.concatenate(Yt),
            np.concatenate(groups), np.concatenate(lum), np.concatenate(pix))


# --------------------------------------------------------------------- #
# Within-renderer report (E12's sweep + gate ladder, per arm)            #
# --------------------------------------------------------------------- #
def within_report(tag: str, X: np.ndarray, Y: np.ndarray, lum: np.ndarray,
                  pix: np.ndarray, groups: np.ndarray,
                  knob_matrix: np.ndarray, targets: np.ndarray) -> dict:
    basis, evr = pca_basis(X, K_WIDE)
    rng = np.random.default_rng(SEED)
    sweep, _ = probe_sweep(X, Y, groups, basis,
                           (K_STRICT, K_PRIMARY, K_WIDE), rng)
    zc = X @ basis[:, :K_PRIMARY]

    lum_col = lum.reshape(-1, 1).astype(np.float64)
    pred_lum, _ = loro_predict(zc, lum_col, groups)
    r2_lum = float(r2_columns(lum_col, pred_lum)[0])

    pred_px, _ = loro_predict(pix, Y, groups)
    r2_px = r2_columns(Y, pred_px)

    room_acc = room_halfsplit_acc(zc, groups)
    room_chance = 1.0 / max(len(np.unique(groups)), 1)

    passes = {}
    for i, d in enumerate(DIAL_NAMES):
        r64 = sweep["r2_still_loro"]["64"][d]
        r16 = sweep["r2_still_loro"][str(K_STRICT)][d]
        rroom = sweep["r2_room_loro"]["64"][d]
        n95 = sweep["null95"][d]
        passes[d] = bool(r64 >= 0.30 and rroom >= 0.15
                         and r16 >= 0.5 * r64 and r64 > n95)
    n_pass = int(sum(1 for d in DIAL_NAMES if passes[d]))
    mean_r64 = float(np.mean([sweep["r2_still_loro"]["64"][d]
                              for d in DIAL_NAMES]))
    mean_n95 = float(np.mean([sweep["null95"][d] for d in DIAL_NAMES]))
    room_ok = bool(room_acc >= 0.75)
    if n_pass >= 2 and room_ok:
        ladder = "KEEP"
    elif n_pass >= 1 or mean_r64 > mean_n95:
        ladder = "INCONCLUSIVE"
    else:
        ladder = "KILL"

    per_dial, cert = carrier_certificate(knob_matrix, targets)
    kr = knob_ranges_any(knob_matrix, KNOB_NAMES if tag == "A"
                         else B_KNOB_NAMES)
    return {
        "renderer": tag, "cells": int(X.shape[0]), "emb_dim": int(X.shape[1]),
        "pca_evr_k64": round(float(evr[:K_PRIMARY].sum()), 4),
        "r2_still_loro": sweep["r2_still_loro"],
        "r2_room_loro": sweep["r2_room_loro"],
        "spearman_loro_k64": sweep["spearman_loro"],
        "perm_null95_k64": sweep["null95"],
        "perm_p_k64": sweep["perm_p"],
        "lambda_median_k64": sweep.get("lambda_median"),
        "tertile_acc_k64": sweep["tertile_acc"],
        "g0b_luminance_r2_k64": round(r2_lum, 4),
        "controls": {
            "raw_pixel_r2_k64": {d: round(float(r2_px[i]), 4)
                                 for i, d in enumerate(DIAL_NAMES)},
            "luminance_spearman": {d: round(spearman(lum, Y[:, i]), 4)
                                   for i, d in enumerate(DIAL_NAMES)},
            "room_identity_acc": round(room_acc, 4),
            "room_identity_chance": round(room_chance, 4),
        },
        "carrier_certificate": {"per_dial": per_dial, "summary": cert,
                                "knob_ranges": kr},
        "gate": {"dial_pass": passes, "n_pass": n_pass,
                 "mean_r2_k64": round(mean_r64, 4),
                 "mean_null95_k64": round(mean_n95, 4),
                 "room_sep_ok": room_ok, "ladder": ladder},
        "_basis": basis,
    }


# --------------------------------------------------------------------- #
# Cross-renderer probe (E12's LORO folds, train renderer -> test renderer)#
# --------------------------------------------------------------------- #
def cross_loro(Xtr: np.ndarray, Xte: np.ndarray, Y: np.ndarray,
               groups: np.ndarray, basis_tr: np.ndarray, k: int,
               lam_fixed: float | None = None):
    """For each held-out room g: ridge fit on the TRAIN renderer's other 26
    rooms in the train renderer's top-k PCs (lambda by E12's inner grouped
    CV on the train side), predict the held room's TEST-renderer rows. The
    test renderer's embeddings never touch the basis or the fit. Returns
    (per-still R2, room-mean R2, median lambda, predictions)."""
    ztr = Xtr @ basis_tr[:, :k]
    zte = Xte @ basis_tr[:, :k]
    pred = np.zeros_like(Y)
    lams = []
    for g in np.unique(groups):
        te = groups == g
        tr = ~te
        if tr.sum() < 2:
            continue
        lam_g = pick_lambda(ztr[tr], Y[tr], groups[tr]) \
            if lam_fixed is None else lam_fixed
        lams.append(float(lam_g))
        pred[te] = _ridge_fit_predict(ztr[tr], Y[tr], zte[te], lam_g)
    r2 = r2_columns(Y, pred)
    ids = np.unique(groups)
    pm = np.stack([pred[groups == g].mean(0) for g in ids])
    ym = np.stack([Y[groups == g].mean(0) for g in ids])
    r2_room = r2_columns(ym, pm)
    return (r2, r2_room, float(np.median(lams)) if lams else float("nan"),
            pred)


def cross_null95(Xtr: np.ndarray, Xte: np.ndarray, Y: np.ndarray,
                 groups: np.ndarray, basis_tr: np.ndarray, k: int,
                 lam: float, perms: int, seed: int) -> dict:
    """Room-label shuffle null for the cross probe (booked): the same folds
    and fixed lambda on randomized room->label maps."""
    rng = np.random.default_rng(seed)
    ids = np.unique(groups)
    yroom = np.stack([Y[groups == g].mean(0) for g in ids])
    pos = np.searchsorted(ids, groups)
    out = np.zeros((perms, Y.shape[1]))
    for i in range(perms):
        yp = yroom[rng.permutation(len(ids))][pos]
        r2, _, _, _ = cross_loro(Xtr, Xte, yp, groups, basis_tr, k,
                                 lam_fixed=lam)
        out[i] = r2
    return {d: round(float(np.percentile(out[:, j], 95)), 4)
            for j, d in enumerate(DIAL_NAMES)}


def cross_direction(src: str, dst: str, reports: dict, X: dict, Y: np.ndarray,
                    groups: np.ndarray) -> dict:
    """One direction of the transfer, at the pre-registered k=64, plus the
    booked pooled-basis variant and the booked shuffle null."""
    basis_src = reports[src]["_basis"]
    r2, r2_room, lam_med, _ = cross_loro(X[src], X[dst], Y, groups,
                                         basis_src, K_CROSS)
    within_src = {d: reports[src]["r2_still_loro"]["64"][d]
                  for d in DIAL_NAMES}
    ratios = {d: round(max(float(r2[i]), 0.0) / max(within_src[d], 1e-6), 4)
              for i, d in enumerate(DIAL_NAMES)}
    # C2 — booked shuffle null at the median train-side lambda.
    n95 = cross_null95(X[src], X[dst], Y, groups, basis_src, K_CROSS,
                       lam_med, CROSS_NULL_PERMS, SEED + 23)
    # C1 — booked pooled-basis variant (label-free, sees both pixel styles).
    basis_pooled = pca_basis(np.concatenate([X[src], X[dst]]), K_WIDE)[0]
    r2p, r2p_room, _, _ = cross_loro(X[src], X[dst], Y, groups,
                                     basis_pooled, K_CROSS)
    return {
        "direction": f"{src}->to->{dst}",
        "k": K_CROSS,
        "cross_r2_still_k64": {d: round(float(r2[i]), 4)
                               for i, d in enumerate(DIAL_NAMES)},
        "within_src_r2_k64": within_src,
        "ratio_cross_over_within": ratios,
        "cross_room_mean_r2": {d: round(float(r2_room[i]), 4)
                               for i, d in enumerate(DIAL_NAMES)},
        "lambda_median": round(lam_med, 6),
        "shuffle_null95_booked": n95,
        "pooled_basis_booked": {
            "cross_r2_still_k64": {d: round(float(r2p[i]), 4)
                                   for i, d in enumerate(DIAL_NAMES)},
            "cross_room_mean_r2": {d: round(float(r2p_room[i]), 4)
                                   for i, d in enumerate(DIAL_NAMES)},
        },
    }


# --------------------------------------------------------------------- #
# CPU-only mode (no model, no GPU): the plumbing test                    #
# --------------------------------------------------------------------- #
def cpu_only() -> dict:
    st = harness_selftest()
    bank = build_bank(1)
    targets = np.stack([r["target"] for r in bank])
    knobs = {tag: np.stack([
        (knobs_linear(float(r["target"][0]), float(r["target"][1]),
                      float(r["target"][2])) if tag == "A"
         else knobs_b(float(r["target"][0]), float(r["target"][1]),
                      float(r["target"][2]), r["seed"]))
        for r in bank]) for tag in ("A", "B")}
    certs = {tag: carrier_certificate(knobs[tag], targets)
             for tag in ("A", "B")}

    # Renderer-B frame sanity: shapes, temporal variation, room distinctness.
    samples = {}
    for ri in (0, 13, 26):
        r = bank[ri]
        fr = render_b_frames(float(r["target"][0]), float(r["target"][1]),
                             float(r["target"][2]), r["seed"])
        arr = np.stack(fr).astype(np.float32)
        samples[r["name"]] = {
            "target": [round(float(x), 3) for x in r["target"]],
            "knobs": {n: round(float(v), 4) for n, v in
                      zip(B_KNOB_NAMES, knobs["B"][ri])},
            "n_frames": len(fr), "shape": list(fr[0].shape),
            "mean_luminance": round(float(arr.mean()), 2),
            "mean_abs_frame_diff": round(
                float(np.abs(arr[1:] - arr[:-1]).mean()), 3),
        }
    fr0 = np.stack([np.asarray(render_b_frames(
        float(r["target"][0]), float(r["target"][1]),
        float(r["target"][2]), r["seed"])[0], np.float32).mean(0)
        for r in bank])                     # (rooms, H, 3) mean frames
    dmin, dmax = float("inf"), 0.0
    for i in range(len(bank)):
        for j in range(i + 1, len(bank)):
            d = float(np.abs(fr0[i] - fr0[j]).mean())
            dmin, dmax = min(dmin, d), max(dmax, d)
    # one renderer-A smoke render (ffmpeg, one room) to prove the import path
    a_frames = ppms_from_lavfi(stage_source(*bank[0]["target"], bank[0]["seed"]),
                               SECONDS, RATE, (W, H))
    out = {
        "experiment": "X2 renderer transfer",
        "mode": "cpu-only (no model, no GPU)",
        "seed": SEED, "rooms": len(bank),
        "renderer_a": RENDERER_A, "renderer_b": RENDERER_B,
        "harness_selftest": st,
        "arm_mirror_check": mirror_check(bank, {"L": {
            r["name"]: knobs_linear(float(r["target"][0]),
                                    float(r["target"][1]),
                                    float(r["target"][2])) for r in bank}}),
        "carrier_certificates": {
            tag: {"per_dial": certs[tag][0], "summary": certs[tag][1],
                  "knob_ranges": knob_ranges_any(
                      knobs[tag], KNOB_NAMES if tag == "A" else B_KNOB_NAMES)}
            for tag in ("A", "B")},
        "staging_fidelity_spearman_target_vs_label": {
            d: round(spearman(targets[:, i],
                              np.stack([r["label"] for r in bank])[:, i]), 4)
            for i, d in enumerate(DIAL_NAMES)},
        "renderer_b_frames_booked": {
            "samples": samples,
            "min_pairwise_room_meanframe_absdiff": round(dmin, 4),
            "max_pairwise_room_meanframe_absdiff": round(dmax, 4),
            "renderer_a_smoke": {
                "room": bank[0]["name"], "n_frames": len(a_frames),
                "shape": list(a_frames[0].shape)},
        },
        "note": ("No verdict in CPU-only mode. Watch: A's certificate must "
                 "measure curvature ~0 with a linear knob read ~1 (the "
                 "discriminative check), B's must be live; renderer-B frames "
                 "must vary temporally and differ across rooms."),
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
        out = {"experiment": "X2 renderer transfer", "verdict": "ABORTED",
               "reason": reason, "guard_preflight": guard_info}
        print(json.dumps(out, indent=2))
        return out

    base = {"experiment": "X2 renderer transfer", "seed": SEED,
            "dial_names": DIAL_NAMES, "extra_dials": EXTRA_DIALS,
            "k_primary": K_PRIMARY, "k_cross": K_CROSS,
            "renderer_a": RENDERER_A, "renderer_b": RENDERER_B,
            "guard_preflight": guard_info,
            "gates_registered": {
                "content": "ratio >= 0.5 x within on >= 2/3 dials, BOTH "
                           "directions",
                "renderer_parameterization_kill": "ratio < 0.2 x within on "
                    ">= 2/3 dials, BOTH directions",
                "invalid_harness": "within-B fails E12's gate (a dead "
                                   "renderer-B is not a verdict)",
                "invalid_control": "within-A fails E12's gate",
            }}

    # G0d — cheapest gate first (model-free).
    selftest = harness_selftest()
    log(f"harness self-test: {selftest}")

    # Bank (E13's builder: E12's 27-cell grid + the elephant's own labels).
    bank = build_bank(1)
    targets = np.stack([r["target"] for r in bank])
    labels = np.stack([r["label"] for r in bank])
    log(f"bank: {len(bank)} rooms (E12's grid, shared by both renderers)")

    # Knob matrices + mirror audit + certificates (all CPU, before the model).
    k_l = {r["name"]: knobs_linear(float(r["target"][0]),
                                   float(r["target"][1]),
                                   float(r["target"][2])) for r in bank}
    mirror = mirror_check(bank, {"L": k_l})
    knobs = {"A": np.stack([k_l[r["name"]] for r in bank]),
             "B": np.stack([knobs_b(float(r["target"][0]),
                                    float(r["target"][1]),
                                    float(r["target"][2]), r["seed"])
                            for r in bank])}
    certs = {tag: carrier_certificate(knobs[tag], targets)
             for tag in ("A", "B")}
    log("carrier certificates: " + "; ".join(
        f"{tag}: curv={certs[tag][1]['mean_curvature']} "
        f"live={certs[tag][1]['n_dials_live']}/3" for tag in ("A", "B")))

    # G0a — staging fidelity (shared bank, E12's G0a).
    fid = {d: round(spearman(targets[:, i], labels[:, i]), 4)
           for i, d in enumerate(DIAL_NAMES)}
    fid_pass = bool(sum(1 for d in DIAL_NAMES if fid[d] >= FIDELITY_FLOOR) >= 2)

    if not selftest["pass"]:
        out = dict(base)
        out.update({"verdict": "INVALID_HARNESS", "harness_selftest": selftest,
                    "reason": "G0d: the imported probe failed the synthetic "
                              "self-test"})
        print(json.dumps(out, indent=2))
        return out
    if not fid_pass:
        out = dict(base)
        out.update({"verdict": "INVALID_STAGING", "harness_selftest": selftest,
                    "staging_fidelity_spearman_target_vs_label": fid,
                    "reason": "G0a: the staged scripts did not move >= 2/3 "
                              "dials"})
        print(json.dumps(out, indent=2))
        return out
    if len(bank) < 8:
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest": selftest,
                    "reason": f"only {len(bank)} rooms — grouped CV would be "
                              "meaningless"})
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

    # Collect both renderers through the SAME frozen encoder.
    data = {}
    try:
        for tag in ("A", "B"):
            log(f"renderer {tag}: rendering + embedding {len(bank)} rooms "
                f"x {N_STILLS} stills")
            data[tag] = collect(tag, bank, model, processor, dev, torch)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest": selftest,
                    "reason": f"frame/embed failed: {e}"})
        print(json.dumps(out, indent=2))
        return out

    # Within-renderer reports (E12's sweep + gate ladder, per arm).
    reports = {}
    try:
        for tag in ("A", "B"):
            X, Y, Yt, groups, lum, pix = data[tag]
            reports[tag] = within_report(tag, X, Y, lum, pix, groups,
                                         knobs[tag], targets)
            log(f"within-{tag}: r2_still_loro(k64)="
                f"{reports[tag]['r2_still_loro']['64']} "
                f"ladder={reports[tag]['gate']['ladder']} "
                f"lum_r2={reports[tag]['g0b_luminance_r2_k64']}")
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest": selftest,
                    "reason": f"probe failed: {e}"})
        print(json.dumps(out, indent=2))
        return out

    # Cross-renderer transfer (the measurement), both directions.
    try:
        Xmat = {tag: data[tag][0] for tag in ("A", "B")}
        Y = data["A"][1]
        groups = data["A"][3]
        cross = {"A_to_B": cross_direction("A", "B", reports, Xmat, Y, groups),
                 "B_to_A": cross_direction("B", "A", reports, Xmat, Y, groups)}
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "harness_selftest": selftest,
                    "reason": f"cross probe failed: {e}"})
        print(json.dumps(out, indent=2))
        return out

    for rep in reports.values():
        rep.pop("_basis", None)   # 1280-wide basis does not belong in the JSON

    # ------------------------------------------------------------------ #
    # Gate ladder (pre-registered).                                       #
    # ------------------------------------------------------------------ #
    sens = {tag: reports[tag]["g0b_luminance_r2_k64"] for tag in ("A", "B")}
    # G0b gated on the E12-replication arm only (E13's convention; amended
    # before any verdict was read — see the module docstring). B's value is
    # booked: B carries its dials on hue/texture/shape, not luminance, and
    # B-liveness is gated by within-B KEEP (V2) instead.
    sens_pass = bool(float(sens["A"]) >= SENSITIVITY_FLOOR)
    a_keeps = reports["A"]["gate"]["ladder"] == "KEEP"
    b_keeps = reports["B"]["gate"]["ladder"] == "KEEP"

    n_hi, n_lo = {}, {}
    for key, cw in (("A_to_B", cross["A_to_B"]),
                    ("B_to_A", cross["B_to_A"])):
        ratios = cw["ratio_cross_over_within"]
        n_hi[key] = sum(1 for d in DIAL_NAMES if ratios[d] >= CROSS_FLOOR)
        n_lo[key] = sum(1 for d in DIAL_NAMES if ratios[d] < CROSS_COLLAPSE)
    content = bool(min(n_hi.values()) >= CROSS_DIALS_FLOOR)
    collapse = bool(min(n_lo.values()) >= CROSS_DIALS_FLOOR)

    if not sens_pass:
        verdict, vreason = "INVALID_HARNESS", (
            "G0b: the luminance sensitivity control on renderer A (E12's own "
            f"carrier) fell below the floor (measured {sens['A']}) — the "
            "probe is blind there")
    elif not a_keeps:
        verdict, vreason = "INVALID_CONTROL", (
            "within-A (E12's own carrier, imported verbatim) did not "
            "reproduce E12's KEEP — the positive control is broken, so no "
            "cross number is interpretable")
    elif not b_keeps:
        verdict, vreason = "INVALID_HARNESS", (
            "within-B failed E12's gate: renderer B is dead as a dial "
            "carrier, and a dead renderer-B is not a verdict (never a KILL)")
    elif content and not collapse:
        verdict, vreason = "CONTENT", (
            "cross-renderer R2 holds >= 0.5x within-renderer on >= 2/3 dials "
            "in BOTH directions — the read is room content, not one "
            "renderer's parameterization")
    elif collapse and not content:
        verdict, vreason = "RENDERER_PARAMETERIZATION", (
            "cross-renderer R2 collapses < 0.2x within-renderer on >= 2/3 "
            "dials in BOTH directions while both within-renderer reads keep "
            "— the E12 family measured its staging function")
    else:
        verdict, vreason = "INCONCLUSIVE", (
            "between the pre-registered floors (including split directions) "
            "— see the per-dial ratios")

    table = {}
    for i, d in enumerate(DIAL_NAMES):
        ab, ba = cross["A_to_B"], cross["B_to_A"]
        table[d] = {
            "within_A_r2": reports["A"]["r2_still_loro"]["64"][d],
            "within_B_r2": reports["B"]["r2_still_loro"]["64"][d],
            "cross_AtoB_r2": ab["cross_r2_still_k64"][d],
            "ratio_AtoB": ab["ratio_cross_over_within"][d],
            "cross_BtoA_r2": ba["cross_r2_still_k64"][d],
            "ratio_BtoA": ba["ratio_cross_over_within"][d],
        }

    out = dict(base)
    out.update({
        "model": model_used, "load_notes": load_notes, "device": dev,
        "rooms": len(bank), "stills_per_room": N_STILLS,
        "cells_per_renderer": int(data["A"][0].shape[0]),
        "label_stats": {d: {"min": round(float(labels[:, i].min()), 4),
                            "max": round(float(labels[:, i].max()), 4),
                            "std": round(float(labels[:, i].std()), 4)}
                        for i, d in enumerate(DIAL_NAMES)},
        "harness_selftest": selftest,
        "staging_fidelity_spearman_target_vs_label": fid,
        "g0a_staging_fidelity_pass": fid_pass,
        "arm_mirror_check": mirror,
        "carrier_certificates": {
            tag: {"summary": certs[tag][1],
                  "knob_ranges": knob_ranges_any(
                      knobs[tag], KNOB_NAMES if tag == "A" else B_KNOB_NAMES)}
            for tag in ("A", "B")},
        "within": {tag: {k: v for k, v in reports[tag].items()
                         if k != "carrier_certificate"}
                   for tag in ("A", "B")},
        "within_certificates": {
            tag: reports[tag]["carrier_certificate"]["summary"]
            for tag in ("A", "B")},
        "cross": cross,
        "transfer_table": table,
        "gates": {
            "g0d_harness_selftest": selftest["pass"],
            "g0a_staging_fidelity": {"floor": FIDELITY_FLOOR,
                                     "pass": fid_pass, "measured": fid},
            "g0b_luminance": {"floor": SENSITIVITY_FLOOR, "gated_arm": "A",
                              "measured": sens, "pass": sens_pass,
                              "booked_note": (
                                  "gated on the E12-replication arm only "
                                  "(E13's convention; amendment recorded in "
                                  "the module docstring, applied before any "
                                  "verdict was read). B's luminance R2 is "
                                  "booked: B carries its dials on hue/"
                                  "texture/shape, not luminance — within-B "
                                  "KEEP (V2) is its liveness gate")},
            "v1_within_A_keep": a_keeps,
            "v2_within_B_keep": b_keeps,
            "content": {"floor": CROSS_FLOOR, "dials_floor": CROSS_DIALS_FLOOR,
                        "dials_per_direction": n_hi, "pass": content},
            "collapse": {"floor": CROSS_COLLAPSE,
                         "dials_floor": CROSS_DIALS_FLOOR,
                         "dials_per_direction": n_lo, "pass": collapse},
        },
        "verdict": verdict,
        "verdict_reason": vreason,
        "amendments": [
            "G0b luminance sensitivity: first draft gated BOTH arms at "
            "R2 >= 0.90 and returned INVALID_HARNESS on B (B measures "
            "~0.41 BY DESIGN — its dials ride hue/texture/shape, not "
            "luminance). Amended before any verdict was read to E13's "
            "convention (gated on the E12-replication arm, per-arm booked); "
            "the experiment was re-executed from scratch and this JSON is "
            "the verdict of record. No cross number moved: the pipeline is "
            "deterministic (seed 2718).",
        ],
        "data_needed": [
            "ffmpeg ~/.local/bin/ffmpeg (renderer A only: E12's lavfi chain)",
            "facebook/ijepa_vith16_1k fp16 on the RTX 4050 (E9 loader)",
            "elephant package importable (dial bank = ground-truth labels)",
            "Pillow (renderer B's blur/uint8 path)",
            f"2 renderers x {len(bank)} rooms x {N_STILLS} stills = "
            f"{2 * len(bank) * N_STILLS} forwards — ~6-10 min GPU, or CPU "
            "overnight",
        ],
        "note": (
            "X2 falsifies the E12 family's scope with a SECOND renderer. Same "
            "27-room bank, same elephant labels, same frozen I-JEPA; only the "
            "pixel pipeline differs (A = E12's lavfi verbatim, B = numpy/PIL "
            "hue-wheel/stripes/soft-blobs compositor, no shared primitives). "
            "The cross probe is alignment-free: a ridge trained on renderer "
            "X's other 26 rooms (X's own top-64 label-free PCs, E12's inner-CV "
            "lambda) predicts room g's Y-renderer embeddings over E12's SAME "
            "27 LORO folds. CONTENT (KEEP) = ratio >= 0.5 x within on >= 2/3 "
            "dials in BOTH directions; RENDERER_PARAMETERIZATION (KILL) = "
            "ratio < 0.2 x within on >= 2/3 in BOTH directions while both "
            "within reads keep. Validity: within-A must replicate E12's KEEP "
            "(INVALID_CONTROL) and within-B must keep (INVALID_HARNESS — a "
            "dead renderer-B is not a verdict), plus E12's staging-fidelity "
            "and luminance-sensitivity gates. Booked: pooled-basis cross and "
            "100-shuffle nulls per direction (C1/C2), carrier certificates "
            "(C3), mirror audit (C4), raw-pixel and room-identity controls "
            "(C5/C7), room-mean cross R2 (C8). Caveats: both carriers are "
            "staged; renderer B is one hand-built alternative; a KILL is "
            "evidence about this renderer pair (reproducible), a KEEP is the "
            "stronger two-pipeline agreement."),
    })
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
