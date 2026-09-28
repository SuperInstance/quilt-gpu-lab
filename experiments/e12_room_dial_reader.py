#!/usr/bin/env python3
"""E12 — room-dial reader: does a FROZEN I-JEPA read the elephant's dials?

CLAIM UNDER TEST (concrete, falsifiable)
  The elephant's dials are senses for ONE dimension of a room's vibe
  (`elephant/dial.py`: "Each dial reads a Room and reports a scalar
  reading... The ensemble of dials is the Field — the elephant"). E9 showed
  a frozen I-JEPA separates the lab's 4 lavfi rooms in embedding space. E12
  asks the next question: does that embedding space carry the ELEPHANT'S
  DIALS — mood (warm/cold), volume (quiet/loud), presence (empty/thrumming)
  — as *linearly readable* directions? If it does, the frozen JEPA is already
  a room-dial sense (no fine-tuning, no head training beyond a linear probe);
  if it does not, "JEPA reads the room" is only room-identity, not vibes.

WHY A STAGED GRID (and the honest limit of that)
  The elephant's text dials (mood/volume/presence in `elephant/dials/`) are
  read from ROOMS OF MESSAGES; I-JEPA reads FRAMES. To get paired
  (frame, dial-label) data we build a room bank where each room is staged
  twice from the SAME dial triple (m, v, p):
    - a script (messages) → the REAL elephant dial bank reads it → label;
    - a lavfi scene → 12 stills → frozen I-JEPA → embedding row.
  So the labels are the elephant's own readings (authoritative code, never
  hand-typed), and the scenes are staged *carriers* of those dials:
  mood → colour temperature + luminance, volume → temporal noise energy +
  contrast, presence → count of drawn occupants (boxes).
  LIMIT, stated up front: this tests "can JEPA linearly READ the staged
  visual carriers of the dials", NOT "do arbitrary camera feeds leak vibes".
  A KEEP is a floor (the read exists); a KILL is decisive (even a
  deliberately staged carrier is not linearly readable → the frozen
  embedding is not a dial reader, and E8's leaderboard must say so).

DEFINITIONS
  embedding     : E9's pipeline verbatim — facebook/ijepa_vith16_1k, fp16,
                  mean-pooled patch tokens, L2-normalized per still (1280-d).
  dial label    : `elephant.dials` reading of the room's staged script
                  (mood ∈ [-1,1], volume ∈ [0,1], presence ∈ [0,1]).
                  Target triple (m,v,p) is booked alongside as `target`.
  probe         : ridge regression, leave-one-room-out (LORO) CV, features
                  = top-k PCA components of the still embeddings. PCA basis
                  is fit UNSUPERVISED on all embeddings (label-free, so no
                  label leakage); λ is chosen per-fold by inner grouped CV.
                  The classification arm predicts with the SAME LORO ridge and
                  cuts at train tertiles, so it rolls with the R².
  k=64          : the pre-registered PRIMARY probe space (the "top-PC test":
                  the dial must live in the leading PCs, not at full width).

ROOMS
  Arm A "e9-stills"   : E9's 4 real lavfi rooms (still-solid / moving-testsrc
                        / smpte / moving-testsrc2), 12 stills each. Frames are
                        E9's; labels come from 4 staged scripts. Used as the
                        continuity arm: 4 rooms cannot support regression, so
                        Arm A is gated ONLY on room separability.
  Arm B "dial-grid"   : 3×3×3 = 27 staged rooms over m ∈ {-0.8,0,+0.8},
                        v ∈ {0.15,0.50,0.85}, p ∈ {0.15,0.50,0.85}, 12 stills
                        each (324 stills). This is the regression room.

PRE-REGISTERED GATES (fixed before running; this file IS the registration)
  G0a staging fidelity : Spearman(target, elephant_label) ≥ 0.5 for ≥ 2 of 3
      dials; else INVALID_STAGING (the staging failed to move the dials, so
      the arm tests nothing — never report a KILL from a dead staging).
  G0b sensitivity      : the same LORO probe on the per-still mean-luminance
      target (a signal that certainly exists in the frames) must reach
      R²(k=64) ≥ 0.90; else INVALID_HARNESS (a KILL would be meaningless).
  G1  THE CLAIM (KEEP) : ≥ 2 of the 3 dials PASS, where
        PASS_d := R²_still_loro_k64(d) ≥ 0.30
                  AND R²_room_loro(d) ≥ 0.15   (room-level check: probe width
                      min(64, n_rooms//2) so it is overdetermined; n_rooms<k
                      makes a room-level ridge structurally undefined)
                  AND R²_still_loro_k16(d) ≥ 0.5·R²(d@k64) (top-PC, not diffuse)
                  AND R²_still_loro_k64(d) > null95_k64(d) (beats label shuffle)
        AND Arm A room-separability accuracy ≥ 0.75 (half-split, chance 0.25).
  G2 INCONCLUSIVE      : exactly 1 dial PASSes, or mean R²(d@k64) > null95.
  G3 KILL              : no dial PASSes and no mean R² above the null — the
      frozen I-JEPA does not linearly expose the elephant dials.
  ABORTED              : guard preflight fails, model unloadable, no frames
      from ffmpeg, or < 8 Arm-B groups (grouped CV meaningless).
  (G0a/G0b are harness-validity gates, not evidence for the claim.)

CONTROLS / BOOKED (never gated)
  C1 raw-pixel probe   : same LORO ridge on 16×9 grayscale stills (144-d) —
      if pixels beat the JEPA embedding, the embedding is losing dial signal.
  C2 luminance Spearman : per-dial rank correlation with mean luminance — the
      trivial visual correlate the probe must NOT be merely echoing.
  C3 permutation null   : 200 room-level label shuffles in the k=64 space
      (fixed λ = median fold λ, for cost) → 95th percentile + p-value.
  C4 Arm A dial R²      : booked only (4 groups — regression is meaningless).
  C5 room-identity acc  : half-split nearest-centroid room classification —
      centroids from each room's first 6 stills, classify the held-out last 6
      (E9's convention). 4 rooms (chance 0.25) and 27 rooms (chance 1/27).
      LORO is NOT used for identity: a held-out room has no centroid, so LORO
      identity accuracy is 0 by construction (caught in the CPU-only check).
  C6 extra dials        : earnestness/cynicism/joke_landing/panic are read by
      the bank and booked with target+label stats, never gated (not tasked).

DATA THE GATE NEEDS
  - ffmpeg at ~/.local/bin/ffmpeg + the lavfi filter chain (color, eq, noise,
    drawbox) — verified present (7.0.2-static).
  - facebook/ijepa_vith16_1k weights, fp16, on the RTX 4050 (E9's loader).
  - the elephant package importable (dial bank = ground-truth labels).
  - 27+4 rooms × 12 stills ≈ 372 forwards at 224² → ~3-5 min GPU once the
    GPU is free (D15c has it at write time), or CPU at ~30-60 min.
  - nothing else: numpy-only probe (no sklearn/torch-head dependency).

HONESTY / CAVEATS BOOKED WITH THE RESULT
  - staged carriers, not naturally-occurring vibes (see "WHY A STAGED GRID");
  - labels are room-level (broadcast to stills) — grouped CV prevents
    within-room leakage, and the room-mean R² is reported as the strict check;
  - λ selection is per-fold, but the PCA basis is global (label-free);
  - presence's carrier (drawn boxes) and volume's (temporal noise) are
    correlated with luminance/contrast — C2 names that escape hatch;
  - 27 rooms is small for a 1280-d embedding; k=16/64/256 (top-PC widths)
    are all reported so the reader can see capacity vs signal.

Verdict printed as ONE JSON object on stdout (progress on stderr).
Deterministic (seed 2718). CPU-only probe; GPU only for the encoder forwards.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

# BLAS thread cap: the probe does THOUSANDS of tiny ridge solves (grouped CV ×
# lambda grid); with the default thread count each 144-d solve spawns 24 threads
# and the whole sweep thrashes for minutes instead of seconds (caught in the
# CPU-only plumbing test, where the raw-pixel control burned ~22 cores for 9
# minutes). Must be set before numpy loads. Also keeps this job a good
# neighbour to whatever else is on the box.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np

try:  # belt-and-braces for callers that imported numpy before this module:
    from threadpoolctl import threadpool_limits   # noqa: E402
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

from common import ppms_from_lavfi                      # noqa: E402
from e9_ijepa_stills import (                           # noqa: E402
    N_STILLS, SOURCES as E9_SOURCES, embed, load_encoder, preflight_guard,
    preprocess,
)
from elephant.dial import DialBank                      # noqa: E402
from elephant.dials import DEFAULT_DIALS                # noqa: E402
from elephant.dials.mood import NEGATIVE, POSITIVE      # noqa: E402
from elephant.room import Message, Room                 # noqa: E402

# --------------------------------------------------------------------- #
# Pre-registered constants                                              #
# --------------------------------------------------------------------- #
DIAL_NAMES = ["mood", "volume", "presence"]            # gated
EXTRA_DIALS = ["earnestness", "cynicism", "joke_landing", "panic"]  # booked
GRID_M = (-0.8, 0.0, 0.8)
GRID_V = (0.15, 0.50, 0.85)
GRID_P = (0.15, 0.50, 0.85)
K_PRIMARY = 64          # the "top-PC" probe space
K_STRICT = 16           # top-PC retention check
K_WIDE = 256            # capacity reference
LAM_GRID = (1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0)
LAM_FIXED_WIDE = 1.0    # wide/full-D reference (no inner CV, booked)
PERMS = 200
R2_FLOOR = 0.30
R2_ROOM_FLOOR = 0.15
R2_TOP_PC_FRACTION = 0.5
FIDELITY_FLOOR = 0.50
SENSITIVITY_FLOOR = 0.90
ARM_A_ACC_FLOOR = 0.75

W, H = 160, 90          # lavfi render size (E9's real frames)
RATE, SECONDS = 10, 6


def log(msg: str) -> None:
    """Progress goes to stderr; stdout is reserved for the JSON verdict."""
    print(f"[e12] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------- #
# Staging: dial triple -> (lavfi scene, script)                          #
# --------------------------------------------------------------------- #
def _mood_rgb(m: float) -> tuple[int, int, int]:
    """Warm (m=+1) -> amber; cold (m=-1) -> blue. Deterministic."""
    t = max(0.0, min(1.0, (m + 1.0) / 2.0))
    r = int(60 + t * 195)
    g = int(90 + t * 80)
    b = int(255 - t * 195)
    return r, g, b


def _boxes(room_seed: int, n: int) -> list[tuple[int, int]]:
    """Deterministic occupant positions (a low-discrepancy scatter)."""
    out = []
    for i in range(n):
        x = (i * 53 + room_seed * 17 + 7) % (W - 14)
        y = ((i * 31 + room_seed * 11 + 5) % (H - 14))
        out.append((int(x), int(y)))
    return out


def stage_source(m: float, v: float, p: float, room_seed: int) -> str:
    """The staged visual carrier of a dial triple.

    mood  -> colour temperature + luminance   (eq/brightness, color hex)
    volume-> temporal noise energy + contrast (noise/allf=t, eq/contrast)
    presence -> drawn occupants               (n drawbox, deterministic spots)
    """
    r, g, b = _mood_rgb(m)
    bright = -0.25 + 0.50 * ((m + 1.0) / 2.0)
    contrast = 0.70 + 0.90 * v
    noise = int(round(2 + 60 * v))
    n_occ = 1 + int(round(p * 8))
    parts = [
        f"color=c=0x{r:02x}{g:02x}{b:02x}:s={W}x{H}:r={RATE}:d={SECONDS}",
        f"eq=brightness={bright:+.3f}:contrast={contrast:.2f}",
        f"noise=alls={noise}:allf=t:all_seed={room_seed}",
    ]
    for (x, y) in _boxes(room_seed, n_occ):
        parts.append(f"drawbox=x={x}:y={y}:w=12:h=12:color=white@0.85:t=fill")
    return ",".join(parts)


_FILLER = ("the room evening shift harbor boat line work night deck glass "
           "weather water lamp wood rail hour coast crew").split()
_AUTHORS = ["reed", "cora", "finn", "sage", "barnacle"]


def stage_transcript(m: float, v: float, p: float, room_seed: int
                     ) -> list[tuple[str, str, float]]:
    """Script staged from the same dial triple. Returns (author, text, ts).

    mood     -> POSITIVE/NEGATIVE lexicon mix  (the bank's own words)
    volume   -> message density, CAPS ratio, exclamations
    presence -> distinct authors, longevity, message count
    """
    rng = np.random.default_rng(room_seed)
    n_msg = 4 + int(round(p * 20))            # 4 .. 24
    n_auth = 1 + int(round(p * 4))            # 1 .. 5
    density = 4.0 + 36.0 * v                  # msgs/min target
    span = max(n_msg / max(density, 0.5) * 60.0, 12.0)
    n_words = 4 + int(round(v * 16))          # 4 .. 20 content words
    pos_p = (m + 1.0) / 2.0
    pos = sorted(POSITIVE)
    neg = sorted(NEGATIVE)
    msgs: list[tuple[str, str, float]] = []
    for i in range(n_msg):
        author = _AUTHORS[(i * n_auth) // max(n_msg, 1)]
        words = []
        for _ in range(n_words):
            if rng.random() < pos_p:
                w = pos[int(rng.integers(0, len(pos)))]
            else:
                w = neg[int(rng.integers(0, len(neg)))]
            if rng.random() < 0.5:
                w = _FILLER[int(rng.integers(0, len(_FILLER)))]
            if v > 0.05 and rng.random() < v and len(w) > 1:
                w = w.upper()
            words.append(w)
        text = " ".join(words)
        elif_marks = "!" * int(round(v * 3))
        if elif_marks:
            text = text + " " + elif_marks
        ts = i * span / max(n_msg - 1, 1)
        msgs.append((author, text, ts))
    return msgs


def room_from_script(name: str, script: list[tuple[str, str, float]]) -> Room:
    return Room(name, [Message(author=a, text=t, ts=ts) for (a, t, ts) in script])


_BANK = DialBank(DEFAULT_DIALS)


def read_room(room: Room) -> dict:
    """Every bank dial's reading of a room. The label source, never typed."""
    return dict(_BANK.readings(room))


# --------------------------------------------------------------------- #
# Probe machinery (numpy-only: ridge, PCA, LORO CV, R², Spearman)        #
# --------------------------------------------------------------------- #
def _rank(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, float)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), float)
    ranks[order] = np.arange(len(a), dtype=float)
    # average ties
    vals, inv, counts = np.unique(a, return_inverse=True, return_counts=True)
    sums = np.zeros(len(vals))
    np.add.at(sums, inv, ranks)
    return (sums / counts)[inv]


def spearman(a, b) -> float:
    ra, rb = _rank(np.asarray(a, float)), _rank(np.asarray(b, float))
    ra = ra - ra.mean()
    rb = rb - rb.mean()
    den = math.sqrt(float(ra @ ra) * float(rb @ rb))
    return float(ra @ rb) / den if den > 1e-12 else 0.0


def r2_columns(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    den = ((y - y.mean(0)) ** 2).sum(0)
    num = ((y - p) ** 2).sum(0)
    return 1.0 - num / np.maximum(den, 1e-12)


def pca_basis(X: np.ndarray, k_max: int):
    """Unsupervised (label-free) PCA basis — safe to fit on all embeddings."""
    Xc = X - X.mean(0)
    _, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    evr = (S ** 2) / max(float((S ** 2).sum()), 1e-12)
    k = min(k_max, Vt.shape[0])
    return Vt[:k].T, evr[:k]


def _ridge_path_pred(ztr, ytr, zte, lams):
    """Predictions for MANY lambdas from ONE SVD of the standardized train set.

    Ridge in SVD form: ŷ = ȳ + T·V·diag(s/(s²+λ))·Uᵀ(y−ȳ). One SVD per train
    fold instead of one solve per (fold, λ) — the inner grouped CV is otherwise
    thousands of tiny solves and starves on BLAS thread overhead.
    """
    mu = ztr.mean(0)
    sd = ztr.std(0) + 1e-8
    X = (ztr - mu) / sd
    T = (zte - mu) / sd
    ym = ytr.mean(0)
    U, S, Vt = np.linalg.svd(X - X.mean(0), full_matrices=False)
    UTy = U.T @ (ytr - ym)
    out = []
    for lam in lams:
        coef = S / (S ** 2 + lam)
        W = Vt.T @ (coef[:, None] * UTy)
        out.append(T @ W + ym)
    return out


def _ridge_fit_predict(ztr, ytr, zte, lam):
    return _ridge_path_pred(ztr, ytr, zte, [lam])[0]


def pick_lambda(z, y, groups, grid=LAM_GRID) -> float:
    """Inner grouped CV over the training rooms only (no leakage)."""
    sse = np.zeros(len(grid))
    seen = False
    for g in np.unique(groups):
        te = groups == g
        tr = ~te
        if tr.sum() < 2:
            continue
        seen = True
        preds = _ridge_path_pred(z[tr], y[tr], z[te], grid)
        for j, p in enumerate(preds):
            sse[j] += float(((y[te] - p) ** 2).sum())
    if not seen:
        return grid[0]
    return float(grid[int(np.argmin(sse))])


def loro_predict(z, y, groups, lam=None) -> tuple[np.ndarray, float]:
    """Leave-one-ROOM-out predictions. lam=None -> per-fold inner CV."""
    pred = np.zeros_like(y)
    lams = []
    for g in np.unique(groups):
        te = groups == g
        tr = ~te
        if tr.sum() < 2:
            pred[te] = y[tr].mean(0) if tr.any() else 0.0
            continue
        lam_g = pick_lambda(z[tr], y[tr], groups[tr]) if lam is None else lam
        lams.append(lam_g)
        pred[te] = _ridge_fit_predict(z[tr], y[tr], z[te], lam_g)
    return pred, float(np.median(lams)) if lams else float("nan")


def room_means(X, y, groups):
    ids = np.unique(groups)
    Xr = np.stack([X[groups == g].mean(0) for g in ids])
    yr = np.stack([y[groups == g].mean(0) for g in ids])
    return Xr, yr, ids


def perm_null(z, y, groups, lam, perms, seed) -> np.ndarray:
    """Room-level label shuffle: the same probe on a randomized room->label map."""
    rng = np.random.default_rng(seed)
    ids = np.unique(groups)
    yroom = np.stack([y[groups == g].mean(0) for g in ids])
    pos = np.searchsorted(ids, groups)
    out = np.zeros((perms, y.shape[1]))
    for i in range(perms):
        perm = rng.permutation(len(ids))
        yp = yroom[perm][pos]
        pred, _ = loro_predict(z, yp, groups, lam=lam)
        out[i] = r2_columns(yp, pred)
    return out


def tertile_acc_ridge(z, ycol, groups) -> float:
    """LORO 3-class accuracy, chance 1/3. The classification arm uses the SAME
    probe as the regression arm — predict the dial with the LORO ridge, then
    cut at the TRAIN tertiles (rolling with the R², not a second, weaker
    probe). NOTE: nearest-centroid-on-embeddings was tried first and is a much
    weaker read (per-still embedding noise swamps class-centroid distances);
    it is not used."""
    correct = n = 0
    for g in np.unique(groups):
        te = groups == g
        tr = ~te
        if tr.sum() < 3:
            continue
        lam = pick_lambda(z[tr], ycol[tr, None], groups[tr])
        pred = _ridge_fit_predict(z[tr], ycol[tr, None], z[te], lam)[:, 0]
        q1, q2 = np.quantile(ycol[tr], [1 / 3, 2 / 3])
        pred_lab = np.digitize(pred, [q1, q2])
        true_lab = np.digitize(ycol[te], [q1, q2])
        correct += int((pred_lab == true_lab).sum())
        n += int(te.sum())
    return correct / max(n, 1)


def room_halfsplit_acc(z, groups) -> float:
    """Room-identity sanity (E9's convention): each room's centroid from the
    FIRST half of its stills, classify the held-out SECOND half.

    Leave-one-ROOM-out is deliberately NOT used here: a held-out room has no
    centroid in the candidate set, so LORO identity accuracy is ~0 by
    construction — a meaningless metric (caught by the CPU-only self-check).
    Continuous dial labels DO use LORO (generalizing a dial to an unseen room
    is exactly the claim).
    """
    ids = np.unique(groups)
    cents, parts, labs = [], [], []
    for gi, g in enumerate(ids):
        idx = np.where(groups == g)[0]
        half = max(len(idx) // 2, 1)
        cents.append(z[idx[:half]].mean(0))
        parts.append(z[idx[half:]])
        labs.append(np.full(len(idx) - half, gi))
    if any(len(p) == 0 for p in parts):
        return float("nan")
    C = np.stack(cents)
    Xte = np.concatenate(parts)
    lab = np.concatenate(labs)
    pred = ((Xte[:, None, :] - C[None, :, :]) ** 2).sum(-1).argmin(1)
    return float((pred == lab).mean())


def binom_ge(k: int, n: int, p: float) -> float:
    if n <= 0:
        return float("nan")
    return float(sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i)
                     for i in range(k, n + 1)))


# --------------------------------------------------------------------- #
# Room banks                                                            #
# --------------------------------------------------------------------- #
ARM_A_TARGETS = {
    # E9's four lavfi rooms, staged as scripts (frames stay E9's real frames).
    "still-solid":     (-0.7, 0.10, 0.10),   # flat gray: the cold, empty room
    "moving-testsrc":  (0.7, 0.85, 0.85),    # loud crowded warm room
    "smpte":           (-0.2, 0.40, 0.30),   # the cool, mid, sparse room
    "moving-testsrc2": (0.4, 0.70, 0.70),    # busy, warm-ish, crowded
}


def build_dial_grid():
    rooms = []
    i = 0
    for m in GRID_M:
        for v in GRID_V:
            for p in GRID_P:
                i += 1
                rooms.append({
                    "name": f"dial_grid_{i:02d}",
                    "target": (m, v, p),
                    "seed": 1000 + i,
                })
    return rooms


def embed_stills(model, processor, dev, frames, seed_room: int):
    """E9's still sampling + preprocessing + forward, plus cheap controls."""
    idx = np.linspace(0, len(frames) - 1, N_STILLS).round().astype(int)
    stills = [frames[i] for i in idx]
    pixel = preprocess(stills, processor, dev)
    vecs = embed(model, pixel)                                   # (12, 1280)
    lum = np.array([float(f.astype(np.float32).mean()) for f in stills])
    pix = np.stack([f[::10, ::10].astype(np.float32).mean(axis=2).reshape(-1)
                    for f in stills])                            # (12, 144)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9
    return vecs / norms, lum, pix


def collect_arm_a(model, processor, dev, torch):
    X, Y, Yt, groups, lum, pix, names = [], [], [], [], [], [], []
    for gi, (name, src) in enumerate(E9_SOURCES):
        m, v, p = ARM_A_TARGETS.get(name, (0.0, 0.5, 0.5))
        script = stage_transcript(m, v, p, room_seed=700 + gi)
        readings = read_room(room_from_script(name, script))
        label = np.array([readings.get(d, 0.0) for d in DIAL_NAMES], float)
        frames = ppms_from_lavfi(src, SECONDS, RATE, (W, H))
        if not frames:
            raise RuntimeError(f"no frames from E9 source {name!r}")
        vecs, l, px = embed_stills(model, processor, dev, frames, 700 + gi)
        groups.append(np.full(len(vecs), gi))
        X.append(vecs)
        Y.append(np.repeat(label[None, :], len(vecs), axis=0))
        Yt.append(np.repeat(np.array([m, v, p], float)[None, :], len(vecs), axis=0))
        lum.append(l)
        pix.append(px)
        names.append(name)
        log(f"armA {name}: {len(vecs)} stills, label mood={label[0]:+.3f} "
            f"volume={label[1]:.3f} presence={label[2]:.3f}")
        if dev == "cuda":
            torch.cuda.empty_cache()
    return (np.concatenate(X), np.concatenate(Y), np.concatenate(Yt),
            np.concatenate(groups), np.concatenate(lum), np.concatenate(pix),
            names)


def collect_arm_b(model, processor, dev, torch):
    X, Y, Yt, groups, lum, pix, names = [], [], [], [], [], [], []
    rooms = build_dial_grid()
    for gi, r in enumerate(rooms):
        m, v, p = r["target"]
        script = stage_transcript(m, v, p, r["seed"])
        readings = read_room(room_from_script(r["name"], script))
        label = np.array([readings.get(d, 0.0) for d in DIAL_NAMES], float)
        src = stage_source(m, v, p, r["seed"])
        frames = ppms_from_lavfi(src, SECONDS, RATE, (W, H))
        if not frames:
            raise RuntimeError(f"no frames from staged source {r['name']!r}")
        vecs, l, px = embed_stills(model, processor, dev, frames, r["seed"])
        groups.append(np.full(len(vecs), gi))
        X.append(vecs)
        Y.append(np.repeat(label[None, :], len(vecs), axis=0))
        Yt.append(np.repeat(np.array([m, v, p], float)[None, :], len(vecs), axis=0))
        lum.append(l)
        pix.append(px)
        names.append(r["name"])
        if dev == "cuda":
            torch.cuda.empty_cache()
    return (np.concatenate(X), np.concatenate(Y), np.concatenate(Yt),
            np.concatenate(groups), np.concatenate(lum), np.concatenate(pix),
            names)


# --------------------------------------------------------------------- #
# Probe sweep                                                           #
# --------------------------------------------------------------------- #
def probe_sweep(X, Y, groups, basis_full, ks, rng) -> dict:
    """LORO ridge across probe spaces + controls + null + classification."""
    out: dict = {"r2_still_loro": {}, "r2_room_loro": {}, "spearman_loro": {},
                 "tertile_acc": {}, "tertile_p": {}, "null95": {}, "perm_p": {}}
    preds: dict = {}
    for k in ks:
        z = X @ basis_full[:, :k] if k < basis_full.shape[1] else X
        lam = None if k <= K_PRIMARY else LAM_FIXED_WIDE
        pred, lam_med = loro_predict(z, Y, groups, lam=lam)
        r2 = r2_columns(Y, pred)
        preds[k] = (z, pred, lam_med)
        out["r2_still_loro"][str(k)] = {d: round(float(r2[i]), 4)
                                        for i, d in enumerate(DIAL_NAMES)}
        Xr, Yr, ids = room_means(z, Y, groups)
        n_rooms = len(ids)
        # The room-level check must be OVERDETERMINED: with n_rooms < k a
        # ridge is underdetermined and LORO R2 collapses to ~ -0.6 even when
        # the still-level read is 0.99 (caught in the CPU-only self-check).
        # So the room-space probe uses its own width min(k, n_rooms // 2) and
        # its own per-fold inner-CV lambda.
        k_room = min(K_PRIMARY, Xr.shape[1], max(4, n_rooms // 2))
        zr = Xr[:, :k_room]
        gr = np.arange(n_rooms)
        pred_r, _ = loro_predict(zr, Yr, gr, lam=None)
        out.setdefault("room_space_k", {})[str(k)] = int(k_room)
        r2r = r2_columns(Yr, pred_r)
        out["r2_room_loro"][str(k)] = {d: round(float(r2r[i]), 4)
                                       for i, d in enumerate(DIAL_NAMES)}
        if k == K_PRIMARY:
            out["lambda_median"] = lam_med
            out["spearman_loro"] = {
                d: round(spearman(Y[:, i], pred[:, i]), 4)
                for i, d in enumerate(DIAL_NAMES)}
            null = perm_null(z, Y, groups, lam_med, PERMS, SEED + 11)
            out["null95"] = {d: round(float(np.percentile(null[:, i], 95)), 4)
                             for i, d in enumerate(DIAL_NAMES)}
            out["perm_p"] = {
                d: round(float((null[:, i] >= r2[i]).mean()), 4)
                for i, d in enumerate(DIAL_NAMES)}
            for i, d in enumerate(DIAL_NAMES):
                acc = tertile_acc_ridge(z, Y[:, i], groups)
                n = len(Y)
                out["tertile_acc"][d] = round(acc, 4)
                out["tertile_p"][d] = round(
                    binom_ge(int(round(acc * n)), n, 1 / 3), 6)
    return out, preds


# --------------------------------------------------------------------- #
# Main                                                                  #
# --------------------------------------------------------------------- #
def main() -> dict:
    ok, reason, guard_info = preflight_guard()
    if not ok:
        out = {"experiment": "E12 room-dial reader", "verdict": "ABORTED",
               "reason": reason, "guard_preflight": guard_info}
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
        out = {"experiment": "E12 room-dial reader", "verdict": "ABORTED",
               "reason": f"model load failed: {e}", "guard_preflight": guard_info}
        print(json.dumps(out, indent=2))
        return out
    log(f"using {model_used}")

    base = {"experiment": "E12 room-dial reader", "device": dev, "seed": SEED,
            "model": model_used, "load_notes": load_notes,
            "guard_preflight": guard_info, "dial_names": DIAL_NAMES,
            "extra_dials": EXTRA_DIALS, "k_primary": K_PRIMARY}

    try:
        (Xa, Ya, Yta, ga, luma, pxa, names_a) = collect_arm_a(
            model, processor, dev, torch)
        (Xb, Yb, Ytb, gb, lumb, pxb, names_b) = collect_arm_b(
            model, processor, dev, torch)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "reason": f"frame/embed failed: {e}"})
        print(json.dumps(out, indent=2))
        return out

    if len(np.unique(gb)) < 8:
        out = dict(base)
        out.update({"verdict": "ABORTED",
                    "reason": f"only {len(np.unique(gb))} Arm-B rooms — "
                              "grouped CV would be meaningless"})
        print(json.dumps(out, indent=2))
        return out

    rng = np.random.default_rng(SEED)
    basis_b, evr_b = pca_basis(Xb, K_WIDE)
    basis_a, evr_a = pca_basis(Xa, K_PRIMARY)

    # G0a — staging fidelity: did the staged scripts actually move the dials?
    fid = {d: round(spearman(Ytb[:, i], Yb[:, i]), 4)
           for i, d in enumerate(DIAL_NAMES)}
    fid_pass = sum(1 for d in DIAL_NAMES if fid[d] >= FIDELITY_FLOOR) >= 2

    # G0b — sensitivity control (a signal known to exist: mean luminance).
    zc = Xb @ basis_b[:, :K_PRIMARY]
    lum_target = lumb.reshape(-1, 1).astype(np.float64)
    pred_lum, _ = loro_predict(zc, lum_target, gb)
    r2_lum = float(r2_columns(lum_target, pred_lum)[0])
    sens_pass = bool(r2_lum >= SENSITIVITY_FLOOR)

    # Primary sweep + controls.
    sweep_b, _ = probe_sweep(Xb, Yb, gb, basis_b,
                            (K_STRICT, K_PRIMARY, K_WIDE), rng)
    r2_full_b = sweep_b["r2_still_loro"]["64"]

    # C1 raw-pixel probe (144-d grayscale), C2 luminance Spearman.
    pred_px, _ = loro_predict(pxb, Yb, gb)
    r2_px = r2_columns(Yb, pred_px)
    pix_r2 = {d: round(float(r2_px[i]), 4) for i, d in enumerate(DIAL_NAMES)}
    lum_spear = {d: round(spearman(lumb, Yb[:, i]), 4)
                 for i, d in enumerate(DIAL_NAMES)}

    # C5 room-identity capacity (E9's half-split convention, NOT LORO).
    acc_b_rooms = room_halfsplit_acc(zc, gb)
    acc_a_rooms = room_halfsplit_acc(Xa @ basis_a, ga)

    # Arm A booked dial R² (4 groups — regression is meaningless, booked).
    sweep_a, _ = probe_sweep(Xa, Ya, ga, basis_a, (K_PRIMARY,), rng)
    arm_a_r2 = sweep_a["r2_still_loro"]["64"]
    arm_a_acc = sweep_a["tertile_acc"]

    # G1 — the pre-registered gate.
    passes = {}
    for i, d in enumerate(DIAL_NAMES):
        r64 = r2_full_b[d]
        r16 = sweep_b["r2_still_loro"][str(K_STRICT)][d]
        rroom = sweep_b["r2_room_loro"]["64"][d]
        n95 = sweep_b["null95"][d]
        passes[d] = bool(r64 >= R2_FLOOR
                         and rroom >= R2_ROOM_FLOOR
                         and r16 >= R2_TOP_PC_FRACTION * r64
                         and r64 > n95)
    n_pass = sum(1 for d in DIAL_NAMES if passes[d])
    mean_r64 = float(np.mean([r2_full_b[d] for d in DIAL_NAMES]))
    mean_null95 = float(np.mean([sweep_b["null95"][d] for d in DIAL_NAMES]))
    arm_a_ok = bool(acc_a_rooms >= ARM_A_ACC_FLOOR)

    if not fid_pass:
        verdict = "INVALID_STAGING"
    elif not sens_pass:
        verdict = "INVALID_HARNESS"
    elif n_pass >= 2 and arm_a_ok:
        verdict = "KEEP"
    elif n_pass >= 1 or mean_r64 > mean_null95:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "KILL"

    label_stats = {
        d: {"min": round(float(Yb[:, i].min()), 4),
            "max": round(float(Yb[:, i].max()), 4),
            "std": round(float(Yb[:, i].std()), 4)}
        for i, d in enumerate(DIAL_NAMES)}

    out = dict(base)
    out.update({
        "rooms_armA": len(names_a), "rooms_armB": len(np.unique(gb)),
        "stills_per_room": N_STILLS, "cells_armB": int(Xb.shape[0]),
        "emb_dim": int(Xb.shape[1]),
        "pca_evr_k16": round(float(evr_b[:K_STRICT].sum()), 4),
        "pca_evr_k64": round(float(evr_b[:K_PRIMARY].sum()), 4),
        "pca_evr_k256": round(float(evr_b[:K_WIDE].sum()), 4),
        "label_stats_armB": label_stats,
        "staging_fidelity_spearman_target_vs_label": fid,
        "g0a_staging_fidelity_pass": bool(fid_pass),
        "g0b_sensitivity_r2_luminance_k64": round(r2_lum, 4),
        "g0b_sensitivity_pass": bool(sens_pass),
        "r2_still_loro": sweep_b["r2_still_loro"],
        "r2_room_loro": sweep_b["r2_room_loro"],
        "room_space_k": sweep_b.get("room_space_k", {}),
        "room_probe_note": ("room-level check uses width min(64, k, n_rooms//2) "
                            "= 13 with its own per-fold inner-CV lambda, so "
                            "every k maps to the SAME 13-d room probe (a "
                            "27-room ridge is underdetermined above that)"),
        "spearman_loro_k64": sweep_b["spearman_loro"],
        "perm_null95_k64": sweep_b["null95"],
        "perm_p_k64": sweep_b["perm_p"],
        "lambda_median_k64": sweep_b.get("lambda_median"),
        "tertile_acc_k64": sweep_b["tertile_acc"],
        "tertile_chance": round(1 / 3, 4),
        "tertile_p_k64": sweep_b["tertile_p"],
        "controls": {
            "raw_pixel_r2_k64": pix_r2,
            "luminance_spearman": lum_spear,
            "room_identity_acc_armB": round(acc_b_rooms, 4),
            "room_identity_chance_armB": round(1 / len(np.unique(gb)), 4),
            "room_identity_acc_armA": round(acc_a_rooms, 4),
            "room_identity_chance_armA": round(1 / max(len(names_a), 1), 4),
            "armA_dial_r2_k64": arm_a_r2,
            "armA_dial_tertile_acc_k64": arm_a_acc,
        },
        "gates": {
            "g0a_staging_fidelity": {"floor": FIDELITY_FLOOR, "pass": bool(fid_pass)},
            "g0b_sensitivity": {"floor": SENSITIVITY_FLOOR,
                                "measured": round(r2_lum, 4), "pass": bool(sens_pass)},
            "g1_dial_pass": passes,
            "g1_pass_count": n_pass,
            "g1_r2_floor": R2_FLOOR,
            "g1_room_r2_floor": R2_ROOM_FLOOR,
            "g1_top_pc_fraction": R2_TOP_PC_FRACTION,
            "armA_room_sep": {"floor": ARM_A_ACC_FLOOR,
                              "measured": round(acc_a_rooms, 4),
                              "pass": arm_a_ok},
            "mean_r2_k64": round(mean_r64, 4),
            "mean_null95_k64": round(mean_null95, 4),
        },
        "data_needed": [
            "ffmpeg ~/.local/bin/ffmpeg (lavfi: color, eq, noise, drawbox) — "
            "chain pre-verified at write time",
            "facebook/ijepa_vith16_1k fp16 weights on the RTX 4050 (E9 loader)",
            "elephant package importable (dial bank = ground-truth labels)",
            f"{len(np.unique(gb))}+{len(names_a)} rooms x {N_STILLS} stills "
            "≈ 372 forwards; ~3-5 min GPU, ~30-60 min CPU",
            "GPU free (D15c held it at write time) — no other blockers",
        ],
        "verdict": verdict,
        "note": (
            "Staged-carrier test: scripts are read by the REAL elephant dial "
            "bank (labels), lavfi scenes staged from the same dial triple are "
            "read by a frozen I-JEPA. KEEP = >=2/3 dials linearly readable at "
            "k=64 (R2>=0.30, room-level R2>=0.15, top-16 PCs retain >=50%, "
            "above the 200-perm shuffle null) AND Arm A room separation "
            ">=0.75. INVALID_STAGING/INVALID_HARNESS mean the arm tested "
            "nothing (dead staging / blind probe) — never a KILL. A KILL says "
            "the frozen embedding is not a dial reader even for a deliberately "
            "staged carrier. Caveat: carriers are staged, not naturally-"
            "occurring vibes; C2 (luminance Spearman) names the trivial-"
            "correlate escape hatch."),
    })
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
