#!/usr/bin/env python3
"""E26 — layer-wise probe: WHERE does the dial information live in I-JEPA?

THE QUESTION (SPOOL.md, entry E26)
  E12 showed a frozen I-JEPA (facebook/ijepa_vith16_1k) linearly READS the
  elephant's three staged dials off its final embedding: still-LORO
  R2(k=64) = 0.81 mood / 0.96 volume / 0.95 presence (recorded run). E26 asks
  the question one dimension deeper, into the network: does the information
  live at DIFFERENT DEPTHS for different dials?
      "volume/presence info lives in LATER layers while mood lives EARLIER
       (colour/temperature is low-level, volume/presence are semantic)"
  i.e. is there an ABSTRACTION GRADIENT inside the frozen trunk — low-level
  colour statistics resolved early, semantic/structural content resolved late?

THE TRUNK, NOT THE HEAD (harness documentation — requested by the task)
  The HF port of I-JEPA (`transformers.models.ijepa.modeling_ijepa.IJepaModel`,
  transformers 5.17) is the frozen ENCODER TRUNK and nothing else. Verified at
  write time by walking the module tree of the loaded checkpoint:
      IJepaModel children = [embeddings, layers(ModuleList[32]), layernorm]
      IJepaModel.forward  = embeddings -> 32 x IJepaLayer -> layernorm,
                            returning BaseModelOutputWithPooling(last_hidden_state ...)
  There is NO predictor module and NO target encoder in this graph (both exist
  only in the original facebookresearch/ijepa PRETRAINING recipe, where the
  predictor is trained against the EMA target encoder; the published
  `ijepa_vith16_1k` checkpoint is the trained trunk, and the HF port does not
  instantiate the pretraining heads). So there is no head to accidentally
  probe. The probe depths are:
      "emb"      = output of model.embeddings (patch + pos embeddings, no
                   attention)                            -> depth index 0
      "b00".."b31" = OUTPUT of model.layers[i] (IJepaLayer): the post-block
                   residual stream, after attention-residual then MLP-residual
                   (see IJepaLayer.forward).             -> depth index i+1
      "ln_final" = model.layernorm(layers[-1] output)    -> depth index 32+1
                   (this is EXACTLY E12's embedding: mean-pooled
                    last_hidden_state -> the anchor that must reproduce E12)
  Extraction = plain `register_forward_hook` on each IJepaLayer (and on
  model.embeddings), pooling each captured activation to a per-still vector
  inside the hook (`mean(dim=1)` over the patch tokens; I-JEPA has no CLS
  token, so mean-pooling is E9/E12's convention verbatim) and moving it to CPU
  as float32. Each depth's per-still vector is then L2-normalized exactly as
  E12 normalizes its final embedding — so the depths are compared on SHAPE,
  not scale, and the final depth reproduces E12's number by construction.
  RESOLUTION (measured, not assumed): E9's `preprocess` uses the checkpoint's
  own hub image processor, which feeds 448x448 = 28x28 = 784 tokens (the
  model's native `image_size` is 448 — NOT the 224² that E9's SIZE constant
  suggests for its processor-less fallback). The hook self-check DERIVES its
  probe resolution from E9's own preprocess on a dummy lab frame and reports
  the captured token count, so this cannot drift silently.
  LIVENESS SELF-CHECK (must pass before any read, on both smoke and real runs):
  two forwards on different random pixels must produce different per-depth
  vectors, and "b00" must differ from "b31" for the same input — a hook that
  silently captured a constant, or one depth for all, fails loudly instead of
  producing a flat curve.
  HONEST NOTE ON DEPTH COUNT: SPOOL's entry guesses "~12 encoder blocks"; the
  checkpoint actually used is ViT-H/16 with 32 blocks (hidden 1280, 16 heads,
  patch 16). All 32 blocks + the two boundary depths (34 depths total) are
  probed, at the checkpoint processor's 448x448 input (784 tokens, matching
  E9/E12's actual forward).

DESIGN (re-embed once, re-read at every depth)
  Bank and staging are E12's, imported not forked:
      rooms   = e12.build_dial_grid()   (27 rooms, m x v x p in 3x3x3)
      frames  = e12.stage_source(m, v, p, seed) -> common.ppms_from_lavfi
      labels  = e12.read_room(e12.room_from_script(name, e12.stage_transcript(...)))
                (the REAL elephant DialBank readings of the staged script —
                 never hand-typed)
      stills  = E12's np.linspace sampling of the 60 rendered frames, 12/room
      forward = one forward per room; the 34 hooked activations are pooled and
                stored; the final depth is E12's mean-pooled last_hidden_state
      probe   = e12.pca_basis + e12.loro_predict + e12.r2_columns (leave-one-
                ROOM-out ridge, per-fold inner-CV lambda, top-k PCA space,
                k = 16 and 64) + e12.perm_null (room-shuffle null) + E12's
                room-level LORO check + e12.tertile_acc_ridge +
                e12.room_halfsplit_acc, called ONCE PER DEPTH.
  So: 27 rooms x 12 stills = 324 forwards (~3-5 min GPU, fp16, RTX 4050), then
  ~34 CPU ridge sweeps (~4 min; the 200-perm null dominates). Nothing is
  forked from E12 except the hook + the depth loop, which is the point.

PRE-REGISTERED GATES (fixed before running; this file IS the registration)
  Depth units: layer index 0..33 as above (0 = patch-emb, 1..32 = blocks,
  33 = final LN); a "block gap" of 1 = 1/33 of trunk depth.
  Curve: per-dial still-LORO R2(k=64) across the 34 depths. PEAK depth is the
  argmax of a 3-point moving average of that curve (edges use the available
  window) — single-depth noise cannot move the peak. The RAW argmax is booked
  alongside. all three dials' PEAK must be VALID:
      PEAK_VALID(d) := R2(d at peak) >= E12's 0.30 floor
                       AND R2(d at peak) > null95(d at the peak depth)
  GRADIENT (two independent depth measures must agree):
      gap(d)   := peak_depth_mood ... vs volume/presence, in blocks
      centroid := sum_i w_i*i / sum_i w_i, w_i = max(0, R2_i - max(0.30,null95_i))
      mood_early := centroid_mood < centroid_volume AND centroid_mood < centroid_presence
                    AND peak_depth_mood < peak_depth_volume
                    AND peak_depth_mood < peak_depth_presence
      separated  := (peak_depth_volume - peak_depth_mood) >= 3 blocks
                    AND (peak_depth_presence - peak_depth_mood) >= 3 blocks
  KEEP : all three PEAK_VALID AND mood_early AND separated
         → the read-maxima sit at DIFFERENT depths, mood earliest: an
         abstraction gradient in the claimed direction.
  KILL : (a) FLAT — every dial's 3-point-smoothed curve spans < 0.10 R2 across
         the trunk (info smeared uniformly, no gradient), OR (b) NO_SEPARATION
         — all three peak depths lie within 3 blocks of each other (includes
         "everything only in the final layer": all peaks at ln_final), OR
         (c) INVERTED — all three peaks valid and volume AND presence both peak
         >= 3 blocks EARLIER than mood (the gradient exists, but the claimed
         direction is falsified).
  INCONCLUSIVE : everything else with valid peaks — partial gradient (< 3
         blocks separation, or only one of volume/presence late, or the two
         depth measures disagree), i.e. suggestive but not the registered
         claim.
  INVALID_HARNESS (any of these → no verdict about the claim):
      hook liveness self-check fails; a depth is missing / non-finite / has the
      wrong width; < 8 rooms (grouped CV meaningless); the G0b sensitivity
      control (mean-luminance LORO read at the final depth) < 0.90; or the
      ANCHOR fails — the final depth must reproduce E12's recorded k=64
      still-LORO numbers (mood 0.8106 / volume 0.9624 / presence 0.9478 for
      this seed, staging and model) within 0.15 absolute. The anchor makes
      "the layer curve ends where E12's number lives" a checkable fact.
  ABORTED : guard preflight fails, model unloadable, or no frames from ffmpeg.

CONTROLS / BOOKED (never gated)
  C1 anchor           : final depth vs E12's recorded k=64 numbers (above).
  C2 hook liveness    : two random forwards differ; b00 != b31.
  C3 luminance read   : mean-luminance LORO R2 at every depth — a signal that
                        trivially exists in the frames; it should be readable
                        everywhere and flat-ish, which is what makes a NON-flat
                        dial curve meaningful.
  C4 room identity    : E12's half-split nearest-centroid room accuracy per
                        depth (booked; shows where room identity exists).
  C5 normalization    : the final depth read WITHOUT the per-still L2
                        normalization (booked) — the L2 convention must not be
                        the thing producing the curve.
  C6 raw-pixel read   : E12's 16x9 grayscale control at the final depth.
  C7 tertile accuracy : E12's LORO classification arm per depth (booked; an
                        independent readout that should peak with its R2).
  C8 per-depth E12 PASS: E12's 4-condition dial PASS evaluated at every depth
                        (r64 >= 0.30, room >= 0.15, k16 >= 0.5*k64, > null95) —
                        booked, and reported as first/last passing depth per
                        dial (where in the trunk the dial becomes readable).
  C9 unnormalized ... : (see C5.)

HONESTY / CAVEATS BOOKED WITH THE RESULT
  - the staged bank is LOW-DIMENSIONAL by construction (E12's own record shows
    k=16 ~ k=64: 0.848 vs 0.811 mood) — the abstraction gradient measured here
    is a gradient over STAGED CARRIERS, not over naturally-occurring vibes;
  - labels are room-level broadcast to stills, and per-still stills within a
    room are near-duplicates, so per-still R2 is inflated vs the room-level
    number; the SAME inflation applies at every depth, which is what makes the
    between-depth comparison fair (booked room-level R2 per depth alongside);
  - LORO on a 3x3x3 factorial leaves one (m,v,p) cell unobserved in every
    training fold — inherited from E12, uniform across depths;
  - one encoder, one seed, one staging family; the linear (ridge) reader of
    E12/E13 (E13b's nonlinear-reader axis is not answered here);
  - "early" and "later" are the trunk's own depth ordering, not a causal claim;
    a KEEP is a location result (info for the dials is spatially separable
    inside the frozen trunk), not a claim about what the encoder "understands".

Deterministic (seed 2718). Progress on stderr; ONE JSON object on stdout.
This module WRITES NOTHING (no results/, no QUEUE.md, no runner.py edits).
Manual fire only:
    ~/venvs/elephant-gpu/bin/python experiments/e26_layerwise_probe.py
    ~/venvs/elephant-gpu/bin/python experiments/e26_layerwise_probe.py --cpu-only
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# BLAS thread cap before numpy loads — the per-depth sweep is thousands of tiny
# ridge solves (34 depths x 27 LORO folds x per-fold inner CV x 200 perms); with
# the default thread count each 64-d solve spawns 24 threads and the sweep
# thrashes (E12's lesson). Also keeps this job a good neighbour on a shared box.
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
    DIAL_NAMES, K_PRIMARY, K_STRICT, K_WIDE, PERMS, R2_FLOOR, R2_ROOM_FLOOR,
    R2_TOP_PC_FRACTION, RATE, SECONDS, W, H, N_STILLS,
    build_dial_grid, loro_predict, pca_basis, perm_null, preflight_guard,
    r2_columns, read_room, room_from_script, room_halfsplit_acc, room_means,
    stage_source, stage_transcript, tertile_acc_ridge,
)
from e9_ijepa_stills import load_encoder, preprocess  # noqa: E402
from common import ppms_from_lavfi  # noqa: E402

# --------------------------------------------------------------------- #
# Pre-registered constants                                              #
# --------------------------------------------------------------------- #
MIN_GAP_BLOCKS = 3          # required peak separation, in blocks (of 32)
FLAT_RANGE_EPS = 0.10       # smoothed curve span below this = "flat"
SMOOTH_W = 3                # peak = argmax of a 3-point moving average
ANCHOR_TOL = 0.15           # |final depth - E12 recorded| tolerance, per dial
SENSITIVITY_FLOOR = 0.90    # G0b, E12's floor verbatim (mean-luminance read)
MIN_ROOMS = 8               # below this, grouped CV is meaningless (E12)
# E12's recorded k=64 still-LORO = the anchor for the final depth. Read from the
# recorded run when the file is present; these literals are the fallback.
E12_ANCHOR_K64 = {"mood": 0.8106, "volume": 0.9624, "presence": 0.9478}
E12_ANCHOR_FILE = LAB / "results" / "e12_room_dial_reader.json"
SMOKE_ROOMS = 6             # --cpu-only smoke subset of the 27-room bank
SMOKE_PERMS = 20
SMOKE_BLOCKS = 4            # tiny random-init trunk for the smoke path
SMOKE_HIDDEN = 64


def log(msg: str) -> None:
    """Progress to stderr; stdout is reserved for the ONE JSON verdict."""
    print(f"[e26] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------- #
# Trunk hooking (the new logic; everything else is imported from E12)    #
# --------------------------------------------------------------------- #
def depth_names(n_blocks: int) -> list[str]:
    """Probe depths, shallow -> deep: patch-emb, every block output, final LN.

    index 0      = model.embeddings output (patch+pos embeddings, no attention)
    index 1..n   = output of model.layers[i-1] (IJepaLayer, post-block residual)
    index n+1    = model.layernorm(last block) = E12's embedding exactly
    """
    return ["emb"] + [f"b{i:02d}" for i in range(n_blocks)] + ["ln_final"]


def install_trunk_hooks(model, token_capture_name: str | None = None):
    """register_forward_hook on model.embeddings + every IJepaLayer.

    Each hook mean-pools the captured activation over the patch axis (I-JEPA
    has no CLS token) and stores a CPU float32 numpy array under its depth
    name. The hook returns None, so the forward pass is untouched. The caller
    clears the dict before each forward. If `token_capture_name` names a depth,
    that block's UNPOOLED (B,N,C) activation is ALSO stored as `<name>__tokens`,
    so the collector can verify (token-level) that the final depth really is
    `pool(layernorm(last block))` and not a stray tensor.
    """
    caps: dict = {}
    handles = []

    def _mk(name):
        def _hook(_module, _inp, out):
            t = out[0] if isinstance(out, (tuple, list)) else out
            if not hasattr(t, "dim") or t.dim() != 3:
                raise RuntimeError(
                    f"hook {name}: expected (B,N,C) activation, got "
                    f"{getattr(t, 'shape', type(t))}")
            caps[name] = t.detach().float().mean(dim=1).cpu().numpy()
            if token_capture_name is not None and name == token_capture_name:
                caps[name + "__tokens"] = t.detach().float().cpu().numpy()
        return _hook

    if not hasattr(model, "embeddings") or not hasattr(model, "layers"):
        raise RuntimeError("model is not an IJepaModel-shaped trunk "
                           "(needs .embeddings and .layers)")
    handles.append(model.embeddings.register_forward_hook(_mk("emb")))
    for i, layer in enumerate(model.layers):
        handles.append(layer.register_forward_hook(_mk(f"b{i:02d}")))
    return caps, handles


def __to_tensor(pooled: np.ndarray, like):
    import torch
    return torch.as_tensor(pooled, dtype=like.dtype, device=like.device)


def hook_self_check(model, dev, torch, n_blocks: int,
                    processor=None) -> dict:
    """Prove the hooks are LIVE and DEPTH-DISCRIMINATING before any read.

    Two forwards on DIFFERENT random pixels: every depth must be captured
    (n_blocks+2 of them), finite, width = hidden size; the two inputs must give
    different vectors at every depth (a constant capture fails); and b00 must
    differ from b31 for the same input (a single-depth capture fails).
    The probe resolution is taken from E9's OWN `preprocess` on a dummy lab
    frame — the checkpoint's processor feeds 448x448 (784 tokens), NOT 224², so
    hard-coding a resolution here would test a different harness than the one
    E12 ran. The captured token count is reported.
    """
    names = depth_names(n_blocks)
    probe = preprocess([np.zeros((90, 160, 3), np.uint8)], processor, dev)
    _, _, hh, ww = probe.shape
    tokens = (hh // int(model.config.patch_size)) * (ww // int(model.config.patch_size))
    caps, handles = install_trunk_hooks(model, token_capture_name=names[1])
    try:
        got = []
        seen_tokens = None
        for s in (0, 1):
            gen = torch.Generator().manual_seed(SEED + s)
            x = torch.randn(1, 3, hh, ww, generator=gen).to(dev)
            x = x.to(next(model.parameters()).dtype)
            caps.clear()
            with torch.no_grad():
                out = model(pixel_values=x)
            h = getattr(out, "last_hidden_state", None)
            if h is None:
                h = out[0]
            caps["ln_final"] = h.detach().float().mean(dim=1).cpu().numpy()
            t = caps.get(names[1] + "__tokens")
            seen_tokens = int(t.shape[1]) if t is not None else None
            missing = [d for d in names if d not in caps]
            if missing:
                raise RuntimeError(f"hook self-check: missing depths {missing}")
            got.append({d: np.asarray(caps[d], np.float32) for d in names})
    finally:
        for hd in handles:
            hd.remove()
    info = {"probe_resolution": [int(hh), int(ww)],
            "tokens_per_image": seen_tokens,
            "expected_tokens": int(tokens),
            "depths_captured": len(names),
            "hidden": int(got[0][names[0]].shape[-1])}
    if seen_tokens is not None and seen_tokens != tokens:
        raise RuntimeError(f"hook self-check: captured {seen_tokens} tokens, "
                           f"expected {tokens} at {hh}x{ww}")
    for d in names:
        a, b = got[0][d], got[1][d]
        if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise RuntimeError(f"hook self-check: bad capture at {d}")
        info[f"input_delta_{d}"] = float(np.abs(a - b).max())
        if float(np.abs(a - b).max()) <= 1e-6:
            raise RuntimeError(f"hook self-check: {d} is constant across inputs "
                               "(dead hook)")
    if n_blocks >= 2:
        d00 = float(np.abs(got[0]["b00"] - got[0]["b31" if n_blocks > 31 else f"b{n_blocks-1:02d}"]).max())
        info["b00_vs_last_block_delta"] = d00
        if d00 <= 1e-6:
            raise RuntimeError("hook self-check: b00 == last block (depth "
                               "aliasing — the same activation captured)")
    info["pass"] = True
    log(f"hook self-check OK: {info['depths_captured']} depths, hidden "
        f"{info['hidden']}, {info['tokens_per_image']} tokens at "
        f"{info['probe_resolution'][0]}x{info['probe_resolution'][1]}")
    return info


# --------------------------------------------------------------------- #
# Bank collection with per-depth capture                                #
# --------------------------------------------------------------------- #
def collect_layer_bank(model, processor, dev, torch, rooms, caps,
                       want_raw_final=False) -> dict:
    """E12's staged bank, one forward per room, every depth captured.

    Frames/labels/still-sampling are E12's (stage_source + read_room +
    np.linspace over the 60 rendered frames). E12's bank *collector* is reused
    in spirit but not callable here: it keeps only the final pooled vector, and
    E26's whole point is the intermediate depths — so the loop is E12's,
    with the hook capture added. The final depth is pooled from the model
    output, so it IS E12's embedding (checked against the last block + LN).
    """
    names = depth_names(len(model.layers))
    X = {d: [] for d in names}
    raw_final: list = []
    pix_rows: list = []
    Y, Yt, groups, lum, names_rooms = [], [], [], [], []
    for gi, r in enumerate(rooms):
        m, v, p = r["target"]
        script = stage_transcript(m, v, p, r["seed"])
        readings = read_room(room_from_script(r["name"], script))
        label = np.array([readings.get(d, 0.0) for d in DIAL_NAMES], float)
        src = stage_source(m, v, p, r["seed"])
        frames = ppms_from_lavfi(src, SECONDS, RATE, (W, H))
        if not frames:
            raise RuntimeError(f"no frames from staged source {r['name']!r}")
        idx = np.linspace(0, len(frames) - 1, N_STILLS).round().astype(int)
        stills = [frames[i] for i in idx]
        pixel = preprocess(stills, processor, dev)
        caps.clear()
        with torch.no_grad():
            out = model(pixel_values=pixel)
        h = getattr(out, "last_hidden_state", None)
        if h is None:
            h = out[0]
        ln_final = h.detach().float().mean(dim=1).cpu().numpy()
        # Token-level self-check: the final depth must be
        # pool(layernorm(last block tokens)) — the trunk's own last op. (Pooling
        # FIRST and then applying LayerNorm is NOT the same function, which is
        # exactly why the check needs the unpooled tokens.)
        last = f"b{len(model.layers)-1:02d}"
        toks = caps.get(last + "__tokens")
        if toks is None:
            raise RuntimeError(f"token capture for {last} missing")
        ref = model.layernorm(__to_tensor(np.asarray(toks, np.float32), h))
        ref = ref.detach().float().mean(dim=1).cpu().numpy()
        rel = float(np.abs(ref - ln_final).max() / (np.abs(ln_final).max() + 1e-9))
        if ref.shape != ln_final.shape or rel > 1e-2:
            raise RuntimeError(
                f"final depth mismatch: pooled last_hidden_state != "
                f"pool(layernorm({last})) (rel dev {rel:.2e}) — trunk layout "
                "changed or the hook captured the wrong tensor")
        cap = {d: np.asarray(caps[d], np.float32) for d in names[:-1]}
        cap["ln_final"] = np.asarray(ln_final, np.float32)
        for d in names:
            arr = cap[d]
            if arr.shape != (len(stills), ln_final.shape[1]):
                raise RuntimeError(f"depth {d}: unexpected shape {arr.shape}")
            nrm = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9
            X[d].append(arr / nrm)          # E12's per-still L2 convention
        if want_raw_final:
            raw_final.append(np.asarray(ln_final, np.float32))  # C5 control
        groups.append(np.full(len(stills), gi))
        Y.append(np.repeat(label[None, :], len(stills), axis=0))
        Yt.append(np.repeat(np.array([m, v, p], float)[None, :], len(stills), axis=0))
        lum.append(np.array([float(f.astype(np.float32).mean()) for f in stills]))
        pix_rows.extend(f[::10, ::10].astype(np.float32).mean(axis=2).reshape(-1)
                        for f in stills)          # E12's C1 raw-pixel control
        names_rooms.append(r["name"])
        log(f"room {gi+1}/{len(rooms)} {r['name']}: {len(stills)} stills, "
            f"label m={label[0]:+.3f} v={label[1]:.3f} p={label[2]:.3f}, "
            f"+{len(names)} depths captured")
        if dev == "cuda":
            torch.cuda.empty_cache()
    return {
        "X": {d: np.concatenate(X[d]) for d in names},
        "raw_final": np.concatenate(raw_final) if raw_final else None,
        "Y": np.concatenate(Y), "Y_target": np.concatenate(Yt),
        "groups": np.concatenate(groups), "lum": np.concatenate(lum),
        "pix": np.stack(pix_rows) if pix_rows else None,
        "room_names": names_rooms, "depths": names,
    }


# --------------------------------------------------------------------- #
# Per-depth probe (E12's ridge, exactly, called once per depth)          #
# --------------------------------------------------------------------- #
def probe_depth(Xd: np.ndarray, Y: np.ndarray, groups: np.ndarray,
                lum: np.ndarray, perms: int, seed: int) -> dict:
    """E12's still-LORO ridge read at ONE depth. Returns the full per-depth row."""
    basis, evr = pca_basis(Xd, K_WIDE)
    row: dict = {"r2_k16": {}, "r2_k64": {}, "lambda_median_k64": None,
                 "pca_evr_k64": round(float(evr[:min(K_PRIMARY, evr.shape[0])].sum()), 4)}
    z64 = None
    for k in (K_STRICT, K_PRIMARY):
        keff = min(k, basis.shape[1])
        z = Xd @ basis[:, :keff]
        pred, lam = loro_predict(z, Y, groups)          # per-fold inner-CV lambda
        r2 = r2_columns(Y, pred)
        row[f"r2_k{k}"] = {d: round(float(r2[i]), 4) for i, d in enumerate(DIAL_NAMES)}
        row[f"spearman_k{k}"] = {d: round(float(e12.spearman(Y[:, i], pred[:, i])), 4)
                                 for i, d in enumerate(DIAL_NAMES)}
        if k == K_PRIMARY:
            z64, pred64, lam64 = z, pred, lam
            row["lambda_median_k64"] = lam64
            r2_64 = r2
    # room-level LORO (E12's overdetermined width rule: min(64, k, n_rooms//2))
    Xr, Yr, ids = room_means(z64, Y, groups)
    k_room = min(K_PRIMARY, Xr.shape[1], max(4, len(ids) // 2))
    pred_r, _ = loro_predict(Xr[:, :k_room], Yr, np.arange(len(ids)))
    r2r = r2_columns(Yr, pred_r)
    row["room_space_k"] = int(k_room)
    row["room_r2_k64"] = {d: round(float(r2r[i]), 4) for i, d in enumerate(DIAL_NAMES)}
    # room-shuffle null (E12's control, same perms; fixed lambda for cost)
    null = perm_null(z64, Y, groups, lam64, perms, seed)
    row["null95_k64"] = {d: round(float(np.percentile(null[:, i], 95)), 4)
                         for i, d in enumerate(DIAL_NAMES)}
    row["perm_p_k64"] = {d: round(float((null[:, i] >= r2_64[i]).mean()), 4)
                         for i, d in enumerate(DIAL_NAMES)}
    row["null_mean_k64"] = {d: round(float(null[:, i].mean()), 4)
                            for i, d in enumerate(DIAL_NAMES)}
    # E12's classification arm (same LORO ridge, train-tertile cuts)
    row["tertile_acc_k64"] = {d: round(float(tertile_acc_ridge(z64, Y[:, i], groups)), 4)
                              for i, d in enumerate(DIAL_NAMES)}
    # C3 luminance sensitivity control (a signal that trivially exists in frames)
    lt = lum.reshape(-1, 1).astype(np.float64)
    lp, _ = loro_predict(z64, lt, groups)
    row["lum_r2_k64"] = round(float(r2_columns(lt, lp)[0]), 4)
    # C4 room identity (E12's half-split convention, booked)
    row["room_identity_acc_k64"] = round(float(room_halfsplit_acc(z64, groups)), 4)
    # C8 E12's 4-condition dial PASS at this depth (booked)
    row["e12_pass_k64"] = {
        d: bool(row["r2_k64"][d] >= R2_FLOOR
                and row["room_r2_k64"][d] >= R2_ROOM_FLOOR
                and row["r2_k16"][d] >= R2_TOP_PC_FRACTION * row["r2_k64"][d]
                and row["r2_k64"][d] > row["null95_k64"][d])
        for d in DIAL_NAMES}
    return row


# --------------------------------------------------------------------- #
# Curve shaping + the pre-registered verdict                            #
# --------------------------------------------------------------------- #
def smooth_curve(c: list[float], w: int = SMOOTH_W) -> list[float]:
    """3-point moving average; edges use the available window."""
    n = len(c)
    half = w // 2
    return [float(np.mean(c[max(0, i - half):min(n, i + half + 1)])) for i in range(n)]


def _first_depth_at(frac: float, r64: list[float],
                    depths: list[str]) -> tuple[int | None, str | None]:
    """Shallowest depth whose read reaches `frac` of the dial's peak read."""
    pk = max(r64)
    if pk <= 0:
        return None, None
    thr = frac * pk
    for i, v in enumerate(r64):
        if v >= thr:
            return i, depths[i]
    return None, None


def _depth_gap(cur: dict, a: str, b: str, depths: list[str]) -> int | None:
    """BOOKED helper: block distance between two dials' 95%-of-peak depths."""
    na = cur[a]["first_depth_at_95pct_of_peak"]
    nb = cur[b]["first_depth_at_95pct_of_peak"]
    if na not in depths or nb not in depths:
        return None
    return int(depths.index(na) - depths.index(nb))


def dial_curve(per_depth: dict, depths: list[str], dial: str) -> dict:
    """One dial's trajectory across the trunk + its depth statistics."""
    r64 = [float(per_depth[d]["r2_k64"][dial]) for d in depths]
    r16 = [float(per_depth[d]["r2_k16"][dial]) for d in depths]
    n95 = [float(per_depth[d]["null95_k64"][dial]) for d in depths]
    room = [float(per_depth[d]["room_r2_k64"][dial]) for d in depths]
    acc = [float(per_depth[d]["tertile_acc_k64"][dial]) for d in depths]
    sm = smooth_curve(r64)
    peak_sm = int(np.argmax(sm))
    peak_raw = int(np.argmax(r64))
    w = [max(0.0, r64[i] - max(R2_FLOOR, n95[i])) for i in range(len(r64))]
    tw = float(sum(w))
    centroid = (float(sum(w[i] * i for i in range(len(w))) / tw) if tw > 1e-9
                else float("nan"))
    passes = [bool(per_depth[d]["e12_pass_k64"][dial]) for d in depths]
    pass_idx = [i for i, p in enumerate(passes) if p]
    n3 = max(1, len(r64) // 3)
    # BOOKED (never gated) plateau/warmup diagnostics: the staged bank is
    # low-dimensional (E12's record: k=16 ~ k=64), so several dials sit near
    # their ceiling across a broad plateau — which makes an ARGMAX comparison
    # uninformative even when it is numerically well defined. These fields say
    # so explicitly instead of hiding it behind a peak index.
    plateau = [depths[i] for i, v in enumerate(r64) if v >= max(r64) - 0.02]
    d90, n90 = _first_depth_at(0.90, r64, depths)
    d95, n95f = _first_depth_at(0.95, r64, depths)
    return {
        "r2_k64": [round(x, 4) for x in r64],
        "r2_k16": [round(x, 4) for x in r16],
        "room_r2_k64": [round(x, 4) for x in room],
        "null95_k64": [round(x, 4) for x in n95],
        "tertile_acc_k64": [round(x, 4) for x in acc],
        "smoothed_r2_k64": [round(x, 4) for x in sm],
        "peak_depth": peak_sm,
        "peak_depth_raw": peak_raw,
        "peak_depth_name": depths[peak_sm],
        "peak_depth_name_raw": depths[peak_raw],
        "peak_r2": round(r64[peak_sm], 4),
        "peak_r2_raw_argmax": round(r64[peak_raw], 4),
        "peak_null95": round(n95[peak_sm], 4),
        "peak_valid": bool(r64[peak_sm] >= R2_FLOOR and r64[peak_sm] > n95[peak_sm]),
        "centroid_depth": (round(centroid, 3) if centroid == centroid else None),
        "range_smoothed": round(float(max(sm) - min(sm)), 4),
        "flat": bool((max(sm) - min(sm)) < FLAT_RANGE_EPS),
        "early_minus_late": round(float(np.mean(sm[:n3]) - np.mean(sm[-n3:])), 4),
        "final_depth_r2": round(r64[-1], 4),
        "n_pass_depths": len(pass_idx),
        "first_pass_depth": (depths[pass_idx[0]] if pass_idx else None),
        "last_pass_depth": (depths[pass_idx[-1]] if pass_idx else None),
        "plateau_width_02": len(plateau),
        "plateau_depths_02": plateau,
        "argmax_informative": bool(max(r64) < 0.95 or len(plateau) < 5),
        "first_depth_at_90pct_of_peak": n90,
        "first_depth_at_95pct_of_peak": n95f,
        "rise_from_input_emb_to_peak": round(r64[0], 4),
    }


def derive_verdict(per_depth: dict, depths: list[str]) -> dict:
    """The pre-registered gate. Pure function (exercised by --cpu-only too)."""
    cur = {d: dial_curve(per_depth, depths, d) for d in DIAL_NAMES}
    peaks = {d: cur[d]["peak_depth"] for d in DIAL_NAMES}
    cents = {d: cur[d]["centroid_depth"] for d in DIAL_NAMES}
    valid = {d: cur[d]["peak_valid"] for d in DIAL_NAMES}
    flat = {d: cur[d]["flat"] for d in DIAL_NAMES}
    gap_v = peaks["volume"] - peaks["mood"]
    gap_p = peaks["presence"] - peaks["mood"]
    peak_early = bool(peaks["mood"] < peaks["volume"] and peaks["mood"] < peaks["presence"])
    cent_early = (cents["mood"] is not None and cents["volume"] is not None
                  and cents["presence"] is not None
                  and cents["mood"] < cents["volume"] and cents["mood"] < cents["presence"])
    separated = bool(gap_v >= MIN_GAP_BLOCKS and gap_p >= MIN_GAP_BLOCKS)
    all_within = bool(max(peaks.values()) - min(peaks.values()) < MIN_GAP_BLOCKS)
    inverted = bool(valid["mood"] and valid["volume"] and valid["presence"]
                    and peaks["volume"] - peaks["mood"] <= -MIN_GAP_BLOCKS
                    and peaks["presence"] - peaks["mood"] <= -MIN_GAP_BLOCKS)
    grad = {
        "depth_units": ("layer index: 0=patch-emb, 1..N=block outputs, "
                        "N+1=final LayerNorm (=E12's embedding)"),
        "min_gap_blocks": MIN_GAP_BLOCKS, "flat_range_eps": FLAT_RANGE_EPS,
        "peak_depths": peaks, "centroid_depths": cents,
        "peak_valid": valid, "flat": flat,
        "gap_volume_minus_mood_blocks": int(gap_v),
        "gap_presence_minus_mood_blocks": int(gap_p),
        "mood_peaks_earlier_than_volume": bool(peaks["mood"] < peaks["volume"]),
        "mood_peaks_earlier_than_presence": bool(peaks["mood"] < peaks["presence"]),
        "mood_early_argmax": peak_early,
        "mood_early_centroid": bool(cent_early),
        "depth_measures_agree": bool(peak_early == cent_early),
        "separated": separated,
        "all_peaks_within_gap": all_within,
        "inverted": inverted,
        "BOOKED_diagnostics_not_gated": {
            "note": ("plateau/warmup fields are BOOKED — they never enter the "
                     "KEEP/KILL rule above, which is the pre-registered peak "
                     "test. They exist so a saturated curve cannot be mistaken "
                     "for a located peak."),
            "argmax_informative": {d: cur[d]["argmax_informative"] for d in DIAL_NAMES},
            "plateau_width_02": {d: cur[d]["plateau_width_02"] for d in DIAL_NAMES},
            "first_depth_at_90pct_of_peak": {d: cur[d]["first_depth_at_90pct_of_peak"]
                                             for d in DIAL_NAMES},
            "first_depth_at_95pct_of_peak": {d: cur[d]["first_depth_at_95pct_of_peak"]
                                             for d in DIAL_NAMES},
            "r2_at_input_emb": {d: cur[d]["r2_k64"][0] for d in DIAL_NAMES},
            "gap_at_95pct_blocks": {
                "volume_minus_mood": _depth_gap(cur, "volume", "mood", depths),
                "presence_minus_mood": _depth_gap(cur, "presence", "mood", depths),
            },
            "reading": ("See the curves: every dial clears E12's 4-condition floor at "
                        "almost every depth, so the trunk does not GATE the dial "
                        "information anywhere — the depth structure is a WARMUP "
                        "(how shallow the representation gets resolvable), not a "
                        "localised peak. mood/volume reach ~95% of their peak at "
                        "the patch embedding / first block (colour-temperature and "
                        "noise/contrast are input statistics), while presence "
                        "starts ANTI-readable at the patch embedding and only "
                        "climbs through the blocks (drawn occupants are structure, "
                        "not colour)."),
        },
    }
    if not all(valid.values()):
        dead = [d for d in DIAL_NAMES if not valid[d]]
        return {"curves": cur, "gradient": grad, "verdict": "INCONCLUSIVE",
                "verdict_reason": (f"peak_not_valid:{','.join(dead)} — the dial's "
                                   "read-maximum sits at/below E12's 0.30 floor or "
                                   "is not above its own layer's shuffle null, so no "
                                   "depth location can be claimed for it")}
    if all(flat[d] for d in DIAL_NAMES):
        return {"curves": cur, "gradient": grad, "verdict": "KILL",
                "verdict_reason": (f"flat:{FLAT_RANGE_EPS} — every dial's smoothed "
                                   "curve spans less than the flat threshold: the "
                                   "dial information is smeared across the trunk, "
                                   "there is no abstraction gradient")}
    if all_within:
        return {"curves": cur, "gradient": grad, "verdict": "KILL",
                "verdict_reason": (f"no_separation:{MIN_GAP_BLOCKS} blocks — all "
                                   "three read-maxima sit within one gap (includes "
                                   "the 'only the final layer' case): the dials are "
                                   "not depth-separable, so there is no gradient")}
    if peak_early and separated and cent_early:
        return {"curves": cur, "gradient": grad, "verdict": "KEEP",
                "verdict_reason": (
                    "abstraction_gradient — all three dial read-maxima are valid "
                    f"and depth-separated (volume {gap_v:+d}, presence {gap_p:+d} "
                    "blocks after mood), mood peaks earliest by BOTH depth measures "
                    "(smoothed argmax and above-null mass centroid): mood is read "
                    "from the early trunk, volume/presence from the late trunk")}
    if inverted:
        return {"curves": cur, "gradient": grad, "verdict": "KILL",
                "verdict_reason": ("gradient_inverted — a depth gradient exists but "
                                   "backwards: volume AND presence both peak >= 3 "
                                   "blocks EARLIER than mood, contradicting the "
                                   "registered claim (mood early / semantic dials "
                                   "late)")}
    return {"curves": cur, "gradient": grad, "verdict": "INCONCLUSIVE",
            "verdict_reason": (
                "partial_gradient — peaks are valid but the registered claim is not "
                f"met (separated={separated}, mood_early_argmax={peak_early}, "
                f"mood_early_centroid={bool(cent_early)}, measures_agree="
                f"{bool(peak_early == cent_early)})")}


# --------------------------------------------------------------------- #
# Anchor + drivers                                                      #
# --------------------------------------------------------------------- #
def anchor_reference() -> tuple[dict, str]:
    """E12's recorded k=64 still-LORO per dial (the final-depth anchor)."""
    try:
        rec = json.loads(E12_ANCHOR_FILE.read_text())
        vals = rec["r2_still_loro"]["64"]
        return ({d: float(vals[d]) for d in DIAL_NAMES},
                f"results/e12_room_dial_reader.json (seed {rec.get('seed')}, "
                f"model {rec.get('model')})")
    except Exception as e:  # noqa: BLE001 — anchor must never crash the run
        return dict(E12_ANCHOR_K64), f"hard-coded E12 record (file unreadable: {e})"


def raw_pixel_control(X_pix: np.ndarray, Y: np.ndarray, groups: np.ndarray) -> dict:
    """C6: E12's 16x9 grayscale raw-pixel read at the collection depth set."""
    pred, _ = loro_predict(X_pix, Y, groups)
    r2 = r2_columns(Y, pred)
    return {d: round(float(r2[i]), 4) for i, d in enumerate(DIAL_NAMES)}


def run(rooms: list[dict], perms: int, dev: str, torch, mode: str,
        dev_override: bool, guard_info: dict | None = None) -> dict:
    """Full E26: load trunk, hook, re-embed the bank once, read at every depth."""
    t0 = time.time()
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    log(f"loading I-JEPA ({dev})...")
    try:
        model_used, model, processor, load_notes = load_encoder(dev)
    except Exception as e:  # noqa: BLE001
        out = {"experiment": "E26 layer-wise probe", "verdict": "ABORTED",
               "reason": f"model load failed: {e}"}
        print(json.dumps(out, indent=2))
        return out

    n_blocks = len(model.layers)
    depths = depth_names(n_blocks)
    child_names = [n for n, _ in model.named_children()]
    log(f"trunk: {type(model).__name__}, {n_blocks} blocks, "
        f"hidden {model.config.hidden_size}; children {child_names}")
    head_like = [n for n in child_names if n not in ("embeddings", "layers", "layernorm")]

    base = {"experiment": "E26 layer-wise probe", "mode": mode, "device": dev,
            "seed": SEED, "model": model_used, "load_notes": load_notes,
            "guard_preflight": guard_info,
            "dial_names": DIAL_NAMES, "k_primary": K_PRIMARY,
            "n_rooms": len(rooms), "stills_per_room": N_STILLS,
            "perms": perms}

    # ---- harness: hooks are live and depth-discriminating ----------------
    try:
        hcheck = hook_self_check(model, dev, torch, n_blocks, processor=processor)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "INVALID_HARNESS",
                    "verdict_reason": f"hook self-check failed: {e}",
                    "trunk": trunk_doc(model, n_blocks, depths, child_names,
                                       head_like)})
        print(json.dumps(out, indent=2))
        return out

    caps, handles = install_trunk_hooks(
        model, token_capture_name=f"b{n_blocks-1:02d}")
    try:
        bank = collect_layer_bank(model, processor, dev, torch, rooms, caps,
                                  want_raw_final=True)
    except Exception as e:  # noqa: BLE001
        out = dict(base)
        out.update({"verdict": "ABORTED", "reason": f"embed failed: {e}",
                    "hook_self_check": hcheck})
        print(json.dumps(out, indent=2))
        return out
    finally:
        for hd in handles:
            hd.remove()

    X, Y, groups, lum = bank["X"], bank["Y"], bank["groups"], bank["lum"]
    n_rooms = len(np.unique(groups))
    emb_dim = int(X["ln_final"].shape[1])
    log(f"bank embedded: {X['ln_final'].shape[0]} stills x {emb_dim}-d x "
        f"{len(depths)} depths, {n_rooms} rooms")

    # ---- harness: shapes, finiteness, room count -------------------------
    harness_ok, harness_reason = True, None
    if n_rooms < MIN_ROOMS:
        harness_ok, harness_reason = False, f"only {n_rooms} rooms (<{MIN_ROOMS})"
    for d in depths:
        if d not in X or X[d].shape != (Y.shape[0], emb_dim):
            harness_ok, harness_reason = False, f"depth {d} shape {X[d].shape}"
            break
        if not np.isfinite(X[d]).all():
            harness_ok, harness_reason = False, f"depth {d} non-finite"
            break

    # ---- per-depth sweep (the new loop) ----------------------------------
    per_depth: dict = {}
    for i, d in enumerate(depths):
        row = probe_depth(X[d], Y, groups, lum, perms, SEED + 3 * i + 1)
        per_depth[d] = row
        log(f"depth {i+1:2d}/{len(depths)} {d:>8s}: "
            + " ".join(f"{dl}={row['r2_k64'][dl]:+.3f}" for dl in DIAL_NAMES)
            + f" (null95 "
            + ",".join(f"{row['null95_k64'][dl]:+.3f}" for dl in DIAL_NAMES) + ")")

    # ---- sensitivity + anchor (harness gates) ----------------------------
    lum_final = per_depth["ln_final"]["lum_r2_k64"]
    sens_pass = bool(lum_final >= SENSITIVITY_FLOOR)
    ref, ref_src = anchor_reference()
    meas = {d: per_depth["ln_final"]["r2_k64"][d] for d in DIAL_NAMES}
    devs = {d: round(float(abs(meas[d] - ref[d])), 4) for d in DIAL_NAMES}
    max_dev = max(devs.values())
    anchor_pass = bool(max_dev <= ANCHOR_TOL)

    derived = derive_verdict(per_depth, depths)
    if not harness_ok:
        verdict, reason = "INVALID_HARNESS", f"bank check: {harness_reason}"
    elif not hcheck["pass"]:
        verdict, reason = "INVALID_HARNESS", "hook liveness self-check failed"
    elif not sens_pass:
        verdict, reason = "INVALID_HARNESS", (f"G0b sensitivity {lum_final} < "
                                              f"{SENSITIVITY_FLOOR} (mean-luminance "
                                              "is not readable — blind probe)")
    elif not anchor_pass:
        verdict, reason = "INVALID_HARNESS", (
            f"anchor: final depth deviates from E12's recorded k=64 read by "
            f"{max_dev} > {ANCHOR_TOL} ({devs}) — the per-depth curve does not end "
            "where E12's number lives, so the depths are not comparable to E12")
    else:
        verdict, reason = derived["verdict"], derived["verdict_reason"]
    if dev_override:
        verdict = "DEV_" + verdict

    # ---- booked controls --------------------------------------------------
    raw_final = bank["raw_final"]
    norm_ctrl = {}
    if raw_final is not None:
        basis_r, _ = pca_basis(raw_final, K_PRIMARY)
        zr = raw_final @ basis_r[:, :min(K_PRIMARY, basis_r.shape[1])]
        pr, _ = loro_predict(zr, Y, groups)
        rr = r2_columns(Y, pr)
        norm_ctrl = {d: round(float(rr[i]), 4) for i, d in enumerate(DIAL_NAMES)}
    # C6 raw-pixel control (E12's 16x9 grayscale features, collected above so
    # the staged scenes are rendered exactly once)
    if bank["pix"] is not None and bank["pix"].shape[0] == Y.shape[0]:
        pix_r2 = raw_pixel_control(bank["pix"], Y, groups)
    else:
        pix_r2 = {"error": "pixel features not collected for every still"}

    out = dict(base)
    out.update({
        "verdict": verdict,
        "verdict_reason": reason,
        "cells": int(Y.shape[0]), "emb_dim": emb_dim,
        "n_depths": len(depths), "depth_names": depths,
        "trunk": trunk_doc(model, n_blocks, depths, child_names, head_like),
        "hook_self_check": hcheck,
        "per_depth": {d: per_depth[d] for d in depths},
        "curves": derived["curves"],
        "gradient": derived["gradient"],
        "anchor": {"reference": ref, "reference_source": ref_src,
                   "measured_final_depth_k64": meas, "abs_dev": devs,
                   "tolerance": ANCHOR_TOL, "pass": anchor_pass},
        "controls": {
            "g0b_sensitivity_lum_r2_final_depth": lum_final,
            "g0b_sensitivity_floor": SENSITIVITY_FLOOR,
            "luminance_r2_k64_by_depth": {d: per_depth[d]["lum_r2_k64"]
                                          for d in depths},
            "room_identity_acc_k64_by_depth": {d: per_depth[d]["room_identity_acc_k64"]
                                               for d in depths},
            "final_depth_unnormalized_r2_k64": norm_ctrl,
            "raw_pixel_r2_k64": pix_r2,
            "dial_label_stats": {
                d: {"min": round(float(Y[:, i].min()), 4),
                    "max": round(float(Y[:, i].max()), 4),
                    "std": round(float(Y[:, i].std()), 4)}
                for i, d in enumerate(DIAL_NAMES)},
            "staging_fidelity_spearman_target_vs_label": {
                d: round(float(e12.spearman(bank["Y_target"][:, i], Y[:, i])), 4)
                for i, d in enumerate(DIAL_NAMES)},
            "cross_dial_level_note": (
                "the three dials' LABEL variances differ by ~15x (mood std 0.83 "
                "vs presence std 0.055 on this bank), so R2 LEVELS are not "
                "comparable ACROSS dials; only each dial's own depth "
                "trajectory is (the same target is used at every depth)"),
            "room_identity_chance": round(1.0 / max(n_rooms, 1), 4),
            "tertile_chance": round(1 / 3, 4),
        },
        "gates": {
            "keep_rule": (f"all peaks valid (r2>={R2_FLOOR}, > own null95) AND "
                          f"mood peaks earliest by argmax AND centroid AND "
                          f"volume/presence peaks >= {MIN_GAP_BLOCKS} blocks later"),
            "kill_rule": (f"flat (all smoothed curves span <{FLAT_RANGE_EPS}) OR all "
                          f"peaks within {MIN_GAP_BLOCKS} blocks OR inverted "
                          "(volume+presence both >=3 blocks earlier than mood)"),
            "invalid_harness_rule": ("hook liveness/anchor/G0b sensitivity/<8 rooms"),
            "sensitivity": {"floor": SENSITIVITY_FLOOR, "measured": lum_final,
                            "pass": sens_pass},
            "anchor": {"tolerance": ANCHOR_TOL, "max_abs_dev": max_dev,
                       "pass": anchor_pass},
            "hook_self_check_pass": bool(hcheck["pass"]),
            "bank_check_pass": bool(harness_ok),
        },
        "seconds_total": round(time.time() - t0, 1),
        "data_needed": [
            "~/.local/bin/ffmpeg (lavfi: color, eq, noise, drawbox) — E12's chain",
            "facebook/ijepa_vith16_1k fp16 on the RTX 4050 (E9's loader)",
            "elephant package importable (DialBank = the labels)",
            f"{len(rooms)} rooms x {N_STILLS} stills = {Y.shape[0]} forwards "
            "(~3-5 min GPU) + "
            f"{len(depths)} depth reads x {perms}-perm null (~4 min CPU)",
            "NOT in QUEUE.md / runner.py EXP_MOD by design — manual fire only",
        ],
        "caveats": [
            "the staged bank is low-dimensional by construction (E12's record: "
            "k=16 ~ k=64) AND its dial reads saturate near the ceiling at most "
            "depths, so a peak index is a weak locator here: the booked "
            "plateau/warmup fields report where each dial becomes resolvable, "
            "which is the quantity this bank can actually support",
            "the three dials' target variances differ ~15x (mood std 0.83 vs "
            "presence std 0.055), so R2 levels are not comparable across dials "
            "— only each dial's own depth trajectory is",
            "room-level labels broadcast to near-duplicate stills inflate "
            "per-still R2 — uniformly across depths, which is what makes the "
            "between-depth comparison fair; room-level R2 is booked per depth",
            "LORO on a 3x3x3 factorial leaves one (m,v,p) cell unobserved per "
            "training fold — inherited from E12, uniform across depths",
            "one encoder, one seed, one staging family, linear (ridge) reader "
            "(E13b's nonlinear-reader axis not answered)",
            "depth ordering is the trunk's own; a KEEP is a LOCATION result "
            "(dial info is depth-separable in the frozen trunk), not a claim "
            "about internal semantics",
        ],
        "note": (
            "E26 hooks the frozen I-JEPA TRUNK (model.embeddings + all 32 "
            "IJepaLayer outputs + the final LayerNorm; no predictor/target head "
            "exists in this HF port) and runs E12's leave-one-room-out ridge dial "
            "read at every depth. KEEP = the three dial read-maxima sit at "
            "different depths with mood earliest (an abstraction gradient). "
            "KILL = flat across the trunk, all maxima within one gap (including "
            "'only the final layer'), or an inverted gradient. INVALID_HARNESS "
            "when the hook liveness check, the mean-luminance sensitivity floor, "
            "or the E12 anchor at the final depth fails — the harness, not the "
            "claim, is then the finding. ONE JSON on stdout; this module writes "
            "nothing."),
    })
    print(json.dumps(out, indent=2))
    return out


def trunk_doc(model, n_blocks: int, depths: list[str], child_names: list[str],
              head_like: list[str]) -> dict:
    return {
        "class": type(model).__name__,
        "children": child_names,
        "blocks": int(n_blocks),
        "hidden": int(model.config.hidden_size),
        "patch": int(model.config.patch_size),
        "probe_depths": depths,
        "n_depths": len(depths),
        "hook_targets": ("model.embeddings output (patch+pos emb), each "
                         "model.layers[i] (IJepaLayer) OUTPUT = post-block "
                         "residual stream, and model.layernorm(last block) = "
                         "the trunk's final feature (= E12's embedding)"),
        "pooling": "mean over the patch axis (784 tokens at 448x448 via the "
                   "checkpoint's own image processor — the resolution E9/E12 "
                   "actually fed; I-JEPA has no CLS token) — E9/E12's convention",
        "normalization": "per-still L2 at every depth (E12's convention), so "
                         "depths are compared on shape, not scale",
        "head_modules_found_outside_trunk": head_like,
        "predictor_or_target_encoder": (
            "absent — the HF I-JEPA port ships the trained encoder trunk only; "
            "the predictor/EMA-target heads belong to the pretraining recipe "
            "and are not instantiated here"),
        "spool_note": ("SPOOL guessed ~12 blocks; this checkpoint is ViT-H/16 "
                       "with 32, so 34 depths are probed"),
    }


# --------------------------------------------------------------------- #
# CPU-only smoke path (bank build + hook self-check, no GPU, no verdict) #
# --------------------------------------------------------------------- #
def smoke_rooms(n_rooms: int) -> list[dict]:
    """A spread of E12's bank for the smoke path (spans all three dial levels)."""
    grid = build_dial_grid()
    if n_rooms >= len(grid):
        return grid
    idx = np.linspace(0, len(grid) - 1, max(2, n_rooms)).round().astype(int)
    return [grid[i] for i in dict.fromkeys(idx.tolist())]


def cpu_only(perms: int, n_rooms: int) -> dict:
    """Plumbing proof: tiny random-init trunk + a smoke subset of E12's bank.

    Exercises the whole E26 path — staged lavfi frames, elephant DialBank
    labels, the 34-depth hook capture, the per-depth E12 ridge/nulls, the curve
    and verdict logic — with NO GPU, NO hub download (a random IJepaConfig
    trunk), and NO claim about the real checkpoint. verdict = SMOKE.
    """
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

    hcheck = hook_self_check(model, "cpu", torch, SMOKE_BLOCKS, processor=None)
    caps, handles = install_trunk_hooks(
        model, token_capture_name=f"b{SMOKE_BLOCKS-1:02d}")
    bank_ok, bank_err = True, None
    try:
        bank = collect_layer_bank(model, processor=None, dev="cpu", torch=torch,
                                  rooms=rooms, caps=caps, want_raw_final=True)
    except Exception as e:  # noqa: BLE001
        bank_ok, bank_err = False, f"{type(e).__name__}: {e}"
        bank = None
    finally:
        for hd in handles:
            hd.remove()

    out: dict = {
        "experiment": "E26 layer-wise probe", "mode": "cpu-only smoke",
        "verdict": "SMOKE", "device": "cpu", "seed": SEED,
        "model": "random-init tiny IJepaConfig trunk (no hub download)",
        "n_rooms": len(rooms), "perms": perms,
        "trunk": {"class": type(model).__name__, "blocks": SMOKE_BLOCKS,
                  "hidden": SMOKE_HIDDEN,
                  "probe_depths": depth_names(SMOKE_BLOCKS)},
        "hook_self_check": hcheck,
        "bank_build": {"ok": bank_ok, "error": bank_err},
        "note": ("SMOKE proves the plumbing only: staged bank + elephant labels "
                 "+ 34-depth hook capture + E12's ridge/null per depth + the "
                 "curve/verdict logic, on a random tiny trunk. No claim about "
                 "facebook/ijepa_vith16_1k."),
    }
    if not bank_ok:
        out["verdict"] = "INVALID_HARNESS"
        out["verdict_reason"] = f"bank build failed: {bank_err}"
        print(json.dumps(out, indent=2))
        return out

    depths = bank["depths"]
    per_depth = {d: probe_depth(bank["X"][d], bank["Y"], bank["groups"],
                                bank["lum"], perms, SEED + i)
                 for i, d in enumerate(depths)}
    derived = derive_verdict(per_depth, depths)
    ref, ref_src = anchor_reference()
    out.update({
        "cells": int(bank["Y"].shape[0]),
        "emb_dim": int(bank["X"]["ln_final"].shape[1]),
        "depth_names": depths,
        "smoke_per_depth_r2_k64": {d: per_depth[d]["r2_k64"] for d in depths},
        "smoke_curves": derived["curves"],
        "smoke_gradient": derived["gradient"],
        "smoke_derived_verdict": derived["verdict"],
        "smoke_derived_reason": derived["verdict_reason"],
        "smoke_hook_depths_ok": bool(set(depths) == set(bank["X"].keys())),
        "reference_e12_anchor": ref, "reference_source": ref_src,
        "seconds_total": round(time.time() - t0, 1),
    })
    print(json.dumps(out, indent=2))
    return out


# --------------------------------------------------------------------- #
# CLI                                                                   #
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
        return cpu_only(perms=min(perms, SMOKE_PERMS), n_rooms=min(n_rooms, SMOKE_ROOMS))

    import torch
    ok, reason, guard_info = preflight_guard()
    if not ok:
        out = {"experiment": "E26 layer-wise probe", "verdict": "ABORTED",
               "reason": reason, "guard_preflight": guard_info, "device": "cuda"}
        print(json.dumps(out, indent=2))
        return out
    log(f"guard preflight ok: {guard_info}")
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    rooms = build_dial_grid()[:n_rooms]
    dev_override = n_rooms != 27 or perms != PERMS
    return run(rooms, perms, dev, torch,
               mode=("full" if not dev_override else f"dev-subset({n_rooms} rooms,"
                     f" {perms} perms)"), dev_override=dev_override,
               guard_info=guard_info)


if __name__ == "__main__":
    main()
