#!/usr/bin/env python3
"""E15 — encoder-swap dial-read leaderboard: is I-JEPA special, or does ANY
frozen vision encoder read the staged mood/volume/presence dials?

QUESTION
  E12 KEEPed: a frozen I-JEPA (facebook/ijepa_vith16_1k) linearly reads the
  elephant's staged mood/volume/presence dials (still-LORO R² 0.81/0.96/0.95
  at k=64). But is that a property of ROOM GEOMETRY (any decent frozen vision
  encoder exposes the staged carriers), or is I-JEPA's inductive bias
  load-bearing? E15 runs E12's dial-read pipeline — SAME 27-room staged bank,
  same staged scripts (elephant DialBank labels), same lavfi carriers, same
  ridge reader + leave-one-room-out CV + 200-permutation null — under
  MULTIPLE frozen encoders and prints ONE leaderboard.

CLAIM UNDER TEST (SPOOL E15)
  A different frozen encoder (DINOv2 ViT-B, CLIP ViT-B/32, V-JEPA 2 ViT-L)
  reads the staged dials as well as or better than ijepa_vith16_1k.

ENCODER REGISTRY (cache-aware; frozen, fp16, no fine-tuning anywhere)
  control : facebook/ijepa_vith16_1k   (image, ViT-H/16, 1280-d)
            loaded by e9.load_encoder VERBATIM — the control must be the
            exact E12 path so its KEEP can replicate (or fail to).
  swap    : facebook/dinov2-base       (image, ViT-B/14,  768-d)
  swap    : openai/clip-vit-base-patch32 (image, ViT-B/32 vision tower, 768-d)
  swap    : facebook/vjepa2-vitl-fpc16-256-ssv2 (video, ViT-L/16)
  Pooling is E9's uniform rule for every encoder: mean-pool
  last_hidden_state over ALL tokens, then L2-normalize per row (I-JEPA has
  no CLS token; DINOv2/CLIP CLS tokens are included by the same rule — one
  pooling rule for everyone, applied label-free).
  V-JEPA 2 stills->clips: each of the 12 E9-sampled stills anchors a
  16-frame window STARTING at the still's index (clamped to fit the 60-frame
  render), processed by VJEPA2VideoProcessor at 256px — E7's loader pattern.
  The row contract stays identical: 12 rows/room for every encoder.

CACHE POLICY (no hangs, honest skips)
  At start each encoder's HF weights are looked up under $HF_HOME (default
  ~/.cache/huggingface). Cached (at write time): ijepa_vith16_1k and
  vjepa2-vitl-fpc16-256-ssv2 (pulled for E9 / E7). NOT cached: dinov2-base
  and clip-vit-base-patch32 — they need a ONE-TIME download (~350/600 MB).
  Default behavior: SKIP them with a clear reason (status "skipped") rather
  than hang on the network. Opt in to the download by exporting
  E15_ALLOW_DOWNLOAD=1 (or pre-pull: huggingface-cli download <id>).

PRE-REGISTERED GATES
  Per-encoder gate = E12's G1 VERBATIM (fid G0a is encoder-independent and
  computed once; G0b sensitivity re-runs per encoder):
    PASS_d := R²_still_loro_k64(d) >= 0.30
              AND R²_room_loro(d) >= 0.15
              AND R²_still_loro_k16(d) >= 0.5 * R²_k64(d)   (top-PC, not diffuse)
              AND R²_k64(d) > null95_k64(d)                 (200-perm shuffle)
    encoder KEEP = >=2/3 dials PASS AND Arm-A room separation >= 0.75
    encoder INVALID_HARNESS if the luminance sensitivity control (G0b,
    R² >= 0.90) fails — never report a KILL from a blind probe.
  Aggregate E15 verdict:
    INVALID_CONTROL : the I-JEPA control does NOT replicate E12's KEEP in
                      this run (the comparison is void — E12's numbers are
                      not reproducible today; fix the harness first).
    KEEP (E15)      : control replicates AND >=1 NON-I-JEPA encoder hits
                      E12's KEEP gate -> the read is a property of room
                      geometry, not I-JEPA's inductive bias.
    KILL            : control replicates AND every non-I-JEPA encoder that
                      ran validly fails E12's gate -> I-JEPA's bias is
                      load-bearing (E12's read is encoder-specific).
    INCONCLUSIVE    : control replicates but NO non-I-JEPA encoder ran
                      (all skipped for cache / failed to load) — no swap
                      evidence either way.
    ABORTED         : preflight guard fail (VRAM/thermal), or <8 Arm-B
                      rooms.
  Only encoders with a valid harness verdict (KEEP/INCONCLUSIVE/KILL) count
  as "ran" for the aggregate; skipped/failed/INVALID_HARNESS never silently
  become a KILL.

CONTROLS / BOOKED (never gated)
  C1 raw-pixel probe + C2 luminance Spearman are encoder-INDEPENDENT (same
  stills for every encoder) — computed once from the first encoder that ran
  and reported in "shared". Per-encoder: G0b luminance sensitivity, room
  identity half-split accuracy (E9 convention, NOT LORO), Arm-A booked dial
  R². E12's published numbers are embedded as "e12_published" reference
  context only — gates are re-measured fresh in THIS run.

HONESTY / CAVEATS BOOKED WITH THE RESULT
  - staged carriers, not naturally-occurring vibes (E12's limit, inherited);
  - the vjepa2 row unit is a 16-frame WINDOW, not a single frame — the only
    encoder whose "still" sees temporal context (its volume carrier includes
    frame-to-frame flicker; windows of neighboring stills overlap because 12
    windows of 16 frames cannot fit disjointly in 60 frames);
  - CLS tokens are inside the mean-pool for dinov2/clip (uniform rule);
  - a skipped encoder is missing evidence, not a failed comparison — the
    verdict says INCONCLUSIVE rather than KILL when nothing swapped.

OUTPUT CONTRACT
  ONE JSON verdict on stdout (progress on stderr, "[e15]" prefix). This
  script writes NOTHING to results/ and is NOT wired into runner.py's
  EXP_MOD or QUEUE.md — it is fired manually once the GPU is free:
      ~/venvs/elephant-gpu/bin/python experiments/e15_encoder_swap_dial_read.py
  Build self-check (no model load, no ffmpeg, no CUDA — bank build + encoder
  registry + probe plumbing on synthetic embeddings):
      ~/venvs/elephant-gpu/bin/python experiments/e15_encoder_swap_dial_read.py --cpu-only

Deterministic (seed 2718). GPU: RTX 4050 6GB, fp16 weights, guard preflight
(E9's), per-encoder VRAM reported (weights + peak). CPU-only probe math.
"""
from __future__ import annotations

import gc
import json
import math
import os
import sys
from pathlib import Path

# BLAS thread cap before numpy (E12's preamble verbatim) — the probe does
# thousands of tiny ridge solves; default threads thrash (see E12 docstring).
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np

try:
    from threadpoolctl import threadpool_limits
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

from common import ppms_from_lavfi                      # noqa: E402
import e9_ijepa_stills as e9                            # noqa: E402
import e12_room_dial_reader as e12                      # noqa: E402

# E12's published reference (RESULTS.md 2026-09-28) — context only, the
# gates below are re-measured fresh inside this run.
E12_PUBLISHED = {
    "verdict": "KEEP", "date": "2026-09-28",
    "model": "facebook/ijepa_vith16_1k",
    "r2_still_loro_k64": {"mood": 0.811, "volume": 0.962, "presence": 0.948},
    "r2_room_loro_k64": {"mood": 0.890, "volume": 0.972, "presence": 0.937},
}

CONTROL_KEY = "ijepa_vith16_1k"
ALLOW_DOWNLOAD_ENV = "E15_ALLOW_DOWNLOAD"
VJ_FPC = 16  # frames per clip expected by V-JEPA 2 (E7)


def log(msg: str) -> None:
    print(f"[e15] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------- #
# Encoder registry + cache detection                                    #
# --------------------------------------------------------------------- #
REGISTRY = [
    {"key": "ijepa_vith16_1k", "hf_id": "facebook/ijepa_vith16_1k",
     "kind": "image", "role": "control (E12 replication)",
     "loader": "e9.load_encoder verbatim",
     "note": "ViT-H/16, 1280-d; E12's exact path"},
    {"key": "dinov2_base", "hf_id": "facebook/dinov2-base",
     "kind": "image", "role": "swap", "loader": "AutoModel + AutoImageProcessor",
     "note": "ViT-B/14, 768-d; CLS+patch mean-pool (uniform E9 rule)"},
    {"key": "clip_vitb32", "hf_id": "openai/clip-vit-base-patch32",
     "kind": "image", "role": "swap",
     "loader": "CLIPVisionModel (vision tower only) + AutoImageProcessor",
     "note": "ViT-B/32, 768-d; CLS+patch mean-pool (uniform E9 rule)"},
    {"key": "vjepa2_vitl", "hf_id": "facebook/vjepa2-vitl-fpc16-256-ssv2",
     "kind": "video", "role": "swap",
     "loader": "VJEPA2Model + VJEPA2VideoProcessor (E7's pattern)",
     "note": "ViT-L/16 video; still -> 16-frame window clip at 256px"},
]


def cache_status(hf_id: str) -> dict:
    """Is this encoder's weights file already in the local HF cache?"""
    hub = Path(os.environ.get("HF_HOME",
                              str(Path.home() / ".cache" / "huggingface")))
    d = hub / "hub" / ("models--" + hf_id.replace("/", "--"))
    if not d.is_dir():
        return {"cached": False,
                "reason": f"{d} absent — one-time download needed"}
    snaps = d / "snapshots"
    for snap in sorted(snaps.glob("*")) if snaps.is_dir() else []:
        for fname in ("model.safetensors", "pytorch_model.bin",
                      "model.safetensors.index.json"):
            p = snap / fname
            if p.exists():  # follows symlinks into blobs
                mib = None
                try:
                    if fname.endswith("index.json"):
                        shard_dir = snap.parent.parent / "blobs"
                        mib = (round(sum(q.stat().st_size for q in
                                         shard_dir.glob("*")) / 2 ** 20, 1)
                               if shard_dir.is_dir() else None)
                    else:
                        mib = round(p.stat().st_size / 2 ** 20, 1)
                except OSError:
                    pass
                return {"cached": True, "snapshot": snap.name,
                        "weights_file": fname, "weights_mib": mib}
    return {"cached": False,
            "reason": "snapshot dir present but no weights file "
                      "(config-only cache) — one-time download needed"}


# --------------------------------------------------------------------- #
# Loaders                                                               #
# --------------------------------------------------------------------- #
def load_control(dev: str):
    """E9's loader VERBATIM — the control must be E12's exact path."""
    return e9.load_encoder(dev)


def _load_kw(allow_download: bool) -> dict:
    import torch
    return {"torch_dtype": torch.float16,
            "local_files_only": not allow_download}


def load_image_encoder(spec: dict, dev: str, allow_download: bool):
    """DINOv2 / CLIP vision: fp16, cached-only unless download opted in."""
    import torch
    from transformers import AutoModel, AutoImageProcessor, CLIPVisionModel
    kw = _load_kw(allow_download)
    notes: dict = {}
    if spec["key"] == "clip_vitb32":
        model = CLIPVisionModel.from_pretrained(spec["hf_id"], **kw)
    else:
        model = AutoModel.from_pretrained(spec["hf_id"], **kw)
    model = model.to(dev).eval()
    proc = None
    try:
        proc = AutoImageProcessor.from_pretrained(
            spec["hf_id"], local_files_only=not allow_download)
    except Exception as e:  # noqa: BLE001
        notes["processor"] = (f"hub processor unavailable "
                              f"({type(e).__name__}) — manual ImageNet "
                              "preprocessing (E9 fallback)")
    return model, proc, notes


def load_vjepa2(spec: dict, dev: str, allow_download: bool):
    """E7's loader pattern (fp16), cached-only unless download opted in."""
    import torch
    from transformers import VJEPA2Model, VJEPA2VideoProcessor
    kw = _load_kw(allow_download)
    proc = VJEPA2VideoProcessor.from_pretrained(
        spec["hf_id"], local_files_only=not allow_download)
    model = VJEPA2Model.from_pretrained(spec["hf_id"], **kw).to(dev).eval()
    return model, proc, {}


# --------------------------------------------------------------------- #
# Embedding: V-JEPA 2 still -> 16-frame window clip                     #
# --------------------------------------------------------------------- #
def embed_vjepa2_stills(model, proc, dev, frames):
    """12 rows/room, same row contract as the image encoders.

    Each E9-sampled still anchors one 16-frame clip: the window STARTS at
    the still's index (clamped to fit the 60-frame render — the last few
    windows share their tail). Mean-pool all tubelet tokens, L2-normalize
    per row. Luminance/pixel controls are computed on the ANCHOR stills so
    they mean the same thing across encoders.
    """
    import torch
    idx = np.linspace(0, len(frames) - 1, e9.N_STILLS).round().astype(int)
    rows = []
    for i in idx:
        s = int(min(int(i), len(frames) - VJ_FPC))
        clip = [frames[j] for j in range(s, s + VJ_FPC)]
        inputs = proc(clip, return_tensors="pt")
        inputs = {k: (v.to(dev, torch.float16) if v.is_floating_point
                      else v.to(dev)) for k, v in inputs.items()}
        with torch.no_grad():
            out = model(**inputs)
        h = getattr(out, "last_hidden_state", None)
        if h is None:
            h = out[0]
        rows.append(h.mean(dim=1)[0].float().cpu().numpy())
    vecs = np.stack(rows)
    stills = [frames[i] for i in idx]
    lum = np.array([float(f.astype(np.float32).mean()) for f in stills])
    pix = np.stack([f[::10, ::10].astype(np.float32).mean(axis=2).reshape(-1)
                    for f in stills])
    norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9
    return vecs / norms, lum, pix


# --------------------------------------------------------------------- #
# Room collection (E12's loops, one injected embed fn)                  #
# --------------------------------------------------------------------- #
def build_arm_items():
    """(name, target_triple, room_seed, lavfi_source) for Arm A + Arm B.

    Arm A: E9's 4 real lavfi rooms with E12's staged targets (room seeds
    700+gi). Arm B: E12's 27-room dial grid (e12.build_dial_grid verbatim).
    """
    arm_a = [(name, e12.ARM_A_TARGETS.get(name, (0.0, 0.5, 0.5)), 700 + gi, src)
             for gi, (name, src) in enumerate(e9.SOURCES)]
    arm_b = [(r["name"], tuple(r["target"]), r["seed"],
              e12.stage_source(*r["target"], r["seed"]))
             for r in e12.build_dial_grid()]
    return arm_a, arm_b


def _collect_arm(items, embed_fn, tag: str):
    """E12's collect loop line-for-line; only the embed fn is injected."""
    X, Y, Yt, G, LUM, PIX, names = [], [], [], [], [], [], []
    for gi, (name, target, seed, src) in enumerate(items):
        m, v, p = target
        script = e12.stage_transcript(m, v, p, seed)
        readings = e12.read_room(e12.room_from_script(name, script))
        label = np.array([readings.get(d, 0.0) for d in e12.DIAL_NAMES], float)
        frames = ppms_from_lavfi(src, e12.SECONDS, e12.RATE, (e12.W, e12.H))
        if not frames:
            raise RuntimeError(f"no frames from {name!r}")
        vecs, lum, pix = embed_fn(frames)
        G.append(np.full(len(vecs), gi))
        X.append(vecs)
        Y.append(np.repeat(label[None, :], len(vecs), axis=0))
        Yt.append(np.repeat(np.array([m, v, p], float)[None, :],
                            len(vecs), axis=0))
        LUM.append(lum)
        PIX.append(pix)
        names.append(name)
        log(f"{tag} {name}: {len(vecs)} rows, label mood={label[0]:+.3f} "
            f"volume={label[1]:.3f} presence={label[2]:.3f}")
    return (np.concatenate(X), np.concatenate(Y), np.concatenate(Yt),
            np.concatenate(G), np.concatenate(LUM), np.concatenate(PIX),
            names)


# --------------------------------------------------------------------- #
# Per-encoder probe + E12 gate verbatim                                 #
# --------------------------------------------------------------------- #
def probe_and_gate(Xb, Yb, gb, lumb, Xa, ga) -> dict:
    rng = np.random.default_rng(SEED)
    basis_b, evr_b = e12.pca_basis(Xb, e12.K_WIDE)
    basis_a, _ = e12.pca_basis(Xa, e12.K_PRIMARY)

    # G0b sensitivity control (per encoder): luminance must be readable.
    lum_t = lumb.reshape(-1, 1).astype(np.float64)
    zc = Xb @ basis_b[:, :e12.K_PRIMARY]
    pred_lum, _ = e12.loro_predict(zc, lum_t, gb)
    r2_lum = float(e12.r2_columns(lum_t, pred_lum)[0])
    sens_pass = bool(r2_lum >= e12.SENSITIVITY_FLOOR)

    sweep, _ = e12.probe_sweep(Xb, Yb, gb, basis_b,
                               (e12.K_STRICT, e12.K_PRIMARY, e12.K_WIDE), rng)
    r2_64 = sweep["r2_still_loro"][str(e12.K_PRIMARY)]
    passes = {}
    for d in e12.DIAL_NAMES:
        r64 = r2_64[d]
        r16 = sweep["r2_still_loro"][str(e12.K_STRICT)][d]
        rroom = sweep["r2_room_loro"][str(e12.K_PRIMARY)][d]
        n95 = sweep["null95"][d]
        passes[d] = bool(r64 >= e12.R2_FLOOR
                         and rroom >= e12.R2_ROOM_FLOOR
                         and r16 >= e12.R2_TOP_PC_FRACTION * r64
                         and r64 > n95)
    n_pass = int(sum(passes.values()))
    mean_r64 = float(np.mean([r2_64[d] for d in e12.DIAL_NAMES]))
    mean_n95 = float(np.mean([sweep["null95"][d] for d in e12.DIAL_NAMES]))

    acc_a = e12.room_halfsplit_acc(Xa @ basis_a, ga)
    arm_a_ok = bool(acc_a >= e12.ARM_A_ACC_FLOOR)
    acc_b = e12.room_halfsplit_acc(zc, gb)

    if not sens_pass:
        verdict = "INVALID_HARNESS"
    elif n_pass >= 2 and arm_a_ok:
        verdict = "KEEP"
    elif n_pass >= 1 or mean_r64 > mean_n95:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "KILL"

    return {
        "verdict": verdict,
        "emb_dim": int(Xb.shape[1]),
        "pca_evr_k64": round(float(evr_b[:e12.K_PRIMARY].sum()), 4),
        "r2_still_loro_k64": r2_64,
        "r2_still_loro_k16": sweep["r2_still_loro"][str(e12.K_STRICT)],
        "r2_still_loro_k256": sweep["r2_still_loro"][str(e12.K_WIDE)],
        "r2_room_loro_k64": sweep["r2_room_loro"][str(e12.K_PRIMARY)],
        "spearman_loro_k64": sweep["spearman_loro"],
        "perm_null95_k64": sweep["null95"],
        "perm_p_k64": sweep["perm_p"],
        "lambda_median_k64": sweep.get("lambda_median"),
        "tertile_acc_k64": sweep["tertile_acc"],
        "g0b_sensitivity_r2_luminance_k64": round(r2_lum, 4),
        "g0b_sensitivity_pass": sens_pass,
        "g1_dial_pass": passes,
        "g1_pass_count": n_pass,
        "armA_room_identity_acc": round(acc_a, 4),
        "armA_room_sep_pass": arm_a_ok,
        "armB_room_identity_acc": round(acc_b, 4),
        "gates": {
            "r2_floor": e12.R2_FLOOR,
            "room_r2_floor": e12.R2_ROOM_FLOOR,
            "top_pc_fraction": e12.R2_TOP_PC_FRACTION,
            "armA_acc_floor": e12.ARM_A_ACC_FLOOR,
            "sensitivity_floor": e12.SENSITIVITY_FLOOR,
        },
    }


# --------------------------------------------------------------------- #
# One encoder: load -> collect both arms -> probe -> VRAM -> free       #
# --------------------------------------------------------------------- #
def run_encoder(spec, dev, torch, allow_download) -> tuple[dict, dict]:
    from guard import sample as guard_sample
    key = spec["key"]
    res = {"key": key, "hf_id": spec["hf_id"], "kind": spec["kind"],
           "role": spec["role"], "loader": spec["loader"],
           "cache": spec.get("cache")}
    if dev == "cuda":
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    free_before, _temp = guard_sample()

    log(f"loading {spec['hf_id']} ({dev})...")
    if spec["loader"].startswith("e9.load_encoder"):
        model_used, model, proc, notes = load_control(dev)
        res["model"] = model_used
    elif spec["kind"] == "video":
        model, proc, notes = load_vjepa2(spec, dev, allow_download)
    else:
        model, proc, notes = load_image_encoder(spec, dev, allow_download)
    res["load_notes"] = notes
    weights_mib = (torch.cuda.memory_allocated() / 2 ** 20
                   if dev == "cuda" else None)

    if spec["kind"] == "video":
        embed_fn = lambda frames: embed_vjepa2_stills(model, proc, dev, frames)
    else:
        # e12.embed_stills verbatim (its seed_room arg is unused there).
        embed_fn = lambda frames: e12.embed_stills(model, proc, dev, frames, 0)

    arm_a, arm_b = build_arm_items()
    try:
        log(f"embedding Arm A ({len(arm_a)} rooms) + Arm B ({len(arm_b)} "
            f"rooms) x {e9.N_STILLS} rows with {key}...")
        (Xa, Ya, Yta, ga, luma, pxa, names_a) = _collect_arm(
            arm_a, embed_fn, "armA")
        (Xb, Yb, Ytb, gb, lumb, pxb, names_b) = _collect_arm(
            arm_b, embed_fn, "armB")
    finally:
        del model, proc
        gc.collect()
        if dev == "cuda":
            torch.cuda.empty_cache()

    peak_mib = (torch.cuda.max_memory_allocated() / 2 ** 20
                if dev == "cuda" else None)
    free_after, _temp = guard_sample()
    res["vram"] = {
        "free_before_mib": free_before, "free_after_mib": free_after,
        "weights_mib": round(weights_mib, 1) if weights_mib else None,
        "peak_allocated_mib": round(peak_mib, 1) if peak_mib else None,
    }

    rep = probe_and_gate(Xb, Yb, gb, lumb, Xa, ga)
    rep.update(res)
    # Arm-A booked dial R² (never gated; 4 groups — regression is weak).
    basis_a, _ = e12.pca_basis(Xa, e12.K_PRIMARY)
    sweep_a, _ = e12.probe_sweep(Xa, Ya, ga, basis_a, (e12.K_PRIMARY,), rng_a())
    rep["controls_armA"] = {
        "dial_r2_k64_booked": sweep_a["r2_still_loro"]["64"],
        "room_identity_acc": rep.pop("armA_room_identity_acc"),
    }
    aux = {"Yb": Yb, "gb": gb, "lumb": lumb, "pxb": pxb, "names_b": names_b}
    return rep, aux


def rng_a():
    return np.random.default_rng(SEED + 7)


# --------------------------------------------------------------------- #
# Aggregate + verdict                                                   #
# --------------------------------------------------------------------- #
def aggregate(results: dict) -> tuple[str, dict]:
    control = results.get(CONTROL_KEY, {})
    control_ran = control.get("status") == "ran"
    control_keep = bool(control_ran and control.get("verdict") == "KEEP")

    swap_keys = [s["key"] for s in REGISTRY if s["key"] != CONTROL_KEY]
    swap_ran, swap_keep, swap_out = [], [], []
    for k in swap_keys:
        r = results.get(k, {})
        st, v = r.get("status"), r.get("verdict")
        if st == "ran" and v in ("KEEP", "INCONCLUSIVE", "KILL"):
            swap_ran.append(k)
            if v == "KEEP":
                swap_keep.append(k)
        else:
            swap_out.append({"key": k, "status": st,
                             "verdict": v,
                             "reason": r.get("reason")})

    gates = {
        "control_key": CONTROL_KEY,
        "control_ran": control_ran,
        "control_keep": control_keep,
        "control_verdict": control.get("verdict") if control_ran else None,
        "swaps_ran": swap_ran,
        "swaps_keep": swap_keep,
        "swaps_not_ran": swap_out,
    }
    if not control_keep:
        verdict = "INVALID_CONTROL"
    elif swap_keep:
        verdict = "KEEP"
    elif swap_ran:
        verdict = "KILL"
    else:
        verdict = "INCONCLUSIVE"
    return verdict, gates


# --------------------------------------------------------------------- #
# --cpu-only: bank build + registry + probe plumbing (no model/GPU)     #
# --------------------------------------------------------------------- #
def probe_plumbing_selfcheck() -> dict:
    """Synthetic embeddings with PLANTED dials: the imported E12 ridge/PCA/
    LORO/perm machinery must recover them. No model, no ffmpeg, no CUDA."""
    rng = np.random.default_rng(SEED)
    G, S, D = 27, 12, 128
    groups = np.repeat(np.arange(G), S)
    w_true = rng.normal(size=(3, D)) / math.sqrt(D)
    targets = rng.uniform(-1, 1, size=(G, 3))
    X = rng.normal(size=(G * S, D)) * 0.25
    room_off = np.repeat(rng.normal(size=(G, 1, D)) * 0.3, S, axis=0)
    sig = np.repeat(targets, S, axis=0) @ w_true
    X = X + room_off.reshape(G * S, D) + 25.0 * sig
    Y = np.repeat(targets, S, axis=0)

    basis, _ = e12.pca_basis(X, 256)
    z = X @ basis[:, :e12.K_PRIMARY]
    pred, _ = e12.loro_predict(z, Y, groups)
    r2 = e12.r2_columns(Y, pred)
    Xr, Yr, ids = e12.room_means(z, Y, groups)
    k_room = min(e12.K_PRIMARY, Xr.shape[1], max(4, len(ids) // 2))
    pred_r, _ = e12.loro_predict(Xr[:, :k_room], Yr, np.arange(len(ids)))
    r2r = e12.r2_columns(Yr, pred_r)
    null = e12.perm_null(Xr[:, :k_room], Yr, np.arange(len(ids)),
                         1.0, 20, SEED + 11)
    n95 = np.percentile(null, 95, axis=0)
    checks = {
        "still_loro_r2_min": round(float(r2.min()), 4),
        "room_loro_r2_min": round(float(r2r.min()), 4),
        "room_probe_width_expected": int(k_room),
        "room_probe_width_is_clamped": bool(k_room == 13),
        "perm_null95_max": round(float(n95.max()), 4),
    }
    ok = (checks["still_loro_r2_min"] > 0.90
          and checks["room_loro_r2_min"] > 0.90
          and checks["room_probe_width_is_clamped"]
          and checks["perm_null95_max"] < 0.5)
    return {"pass": bool(ok), "checks": checks,
            "note": "planted 3-dial linear signal in synthetic 128-d "
                    "embeddings (27 rooms x 12 stills); E12's imported "
                    "probe must recover it above the shuffle null"}


def cpu_only() -> dict:
    out = {"experiment": "E15 encoder-swap dial-read leaderboard",
           "mode": "cpu-only self-check: bank build + encoder registry + "
                   "probe plumbing. NO model load, NO ffmpeg render, NO CUDA.",
           "seed": SEED}
    reg = []
    for spec in REGISTRY:
        cache = cache_status(spec["hf_id"])
        reg.append({"key": spec["key"], "hf_id": spec["hf_id"],
                    "kind": spec["kind"], "role": spec["role"],
                    "loader": spec["loader"], "note": spec["note"],
                    "cache": cache,
                    "would": "run" if cache["cached"] else
                             "SKIP (not cached; one-time download needed: "
                             f"{ALLOW_DOWNLOAD_ENV}=1, or huggingface-cli "
                             f"download {spec['hf_id']})"})
    out["encoder_registry"] = reg

    arm_a, arm_b = build_arm_items()
    labels = []
    for name, target, seed, _src in arm_b:
        script = e12.stage_transcript(*target, seed)
        readings = e12.read_room(e12.room_from_script(name, script))
        labels.append([readings.get(d, 0.0) for d in e12.DIAL_NAMES])
    L = np.asarray(labels)
    t = np.array([tgt for _n, tgt, _s, _src in arm_b], float)
    fid = {d: round(e12.spearman(t[:, i], L[:, i]), 4)
           for i, d in enumerate(e12.DIAL_NAMES)}
    out["dial_bank"] = {
        "rooms_armB": len(arm_b), "rooms_armA": len(arm_a),
        "stills_per_room": e9.N_STILLS, "dial_names": e12.DIAL_NAMES,
        "label_min": {d: round(float(L[:, i].min()), 4)
                      for i, d in enumerate(e12.DIAL_NAMES)},
        "label_max": {d: round(float(L[:, i].max()), 4)
                      for i, d in enumerate(e12.DIAL_NAMES)},
        "label_std": {d: round(float(L[:, i].std()), 4)
                      for i, d in enumerate(e12.DIAL_NAMES)},
        "staging_fidelity_spearman_target_vs_label": fid,
        "g0a_staging_fidelity_pass": bool(
            sum(1 for v in fid.values() if v >= e12.FIDELITY_FLOOR) >= 2),
        "example_carrier_armB": arm_b[0][3][:140] + "...",
    }
    sc = probe_plumbing_selfcheck()
    out["probe_selfcheck"] = sc
    out["e12_published_reference"] = E12_PUBLISHED
    out["verdict"] = ("CPU_ONLY_SELFCHECK_PASS" if sc["pass"]
                      else "CPU_ONLY_SELFCHECK_FAIL")
    out["note"] = ("--cpu-only is a build-validation path, not a scientific "
                   "result. Run the full experiment on a free GPU: "
                   "~/venvs/elephant-gpu/bin/python "
                   "experiments/e15_encoder_swap_dial_read.py")
    print(json.dumps(out, indent=2))
    return out


# --------------------------------------------------------------------- #
# Main                                                                  #
# --------------------------------------------------------------------- #
def main() -> dict:
    if "--cpu-only" in sys.argv:
        return cpu_only()

    ok, reason, guard_info = e9.preflight_guard()
    if not ok:
        out = {"experiment": "E15 encoder-swap dial-read leaderboard",
               "verdict": "ABORTED", "reason": reason,
               "guard_preflight": guard_info}
        print(json.dumps(out, indent=2))
        return out

    import torch
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    allow_download = os.environ.get(ALLOW_DOWNLOAD_ENV) == "1"

    results: dict = {}
    aux0 = None
    for spec in REGISTRY:
        key = spec["key"]
        spec["cache"] = cache_status(spec["hf_id"])
        is_control = key == CONTROL_KEY
        if (not is_control and not spec["cache"]["cached"]
                and not allow_download):
            results[key] = {
                "key": key, "hf_id": spec["hf_id"], "status": "skipped",
                "reason": (
                    "weights not in local HF cache — one-time download "
                    f"needed (~350-600 MB). Re-run with {ALLOW_DOWNLOAD_ENV}=1 "
                    f"or pre-pull: huggingface-cli download {spec['hf_id']}"),
                "cache": spec["cache"],
            }
            log(f"{key}: SKIPPED — {results[key]['reason']}")
            continue
        try:
            rep, aux = run_encoder(spec, dev, torch, allow_download)
            rep["status"] = "ran"
            if aux0 is None:
                aux0 = aux
                rep["labels_are_reference"] = True
            else:
                same = (np.allclose(aux["Yb"], aux0["Yb"])
                        and np.allclose(aux["gb"], aux0["gb"]))
                rep["labels_match_control"] = bool(same)
                if not same:
                    log(f"WARNING: {key} labels differ from the control run "
                        "— the bank should be deterministic; investigate.")
            results[key] = rep
            log(f"{key}: verdict {rep['verdict']} "
                f"(pass {rep['g1_pass_count']}/3 dials)")
        except Exception as e:  # noqa: BLE001
            results[key] = {
                "key": key, "hf_id": spec["hf_id"], "status": "failed",
                "reason": f"{type(e).__name__}: {e}"[:400],
                "cache": spec["cache"],
            }
            log(f"{key}: FAILED — {results[key]['reason']}")
            if dev == "cuda":
                torch.cuda.empty_cache()

    verdict, gates = aggregate(results)

    shared = None
    if aux0 is not None:
        Yb, gb, lumb, pxb = (aux0["Yb"], aux0["gb"], aux0["lumb"],
                             aux0["pxb"])
        pred_px, _ = e12.loro_predict(pxb, Yb, gb)
        r2_px = e12.r2_columns(Yb, pred_px)
        shared = {
            "rooms_armB": int(len(np.unique(gb))),
            "rooms_armA": len(e9.SOURCES),
            "stills_per_room": e9.N_STILLS,
            "raw_pixel_r2_k64_booked": {
                d: round(float(r2_px[i]), 4)
                for i, d in enumerate(e12.DIAL_NAMES)},
            "luminance_spearman_booked": {
                d: round(e12.spearman(lumb, Yb[:, i]), 4)
                for i, d in enumerate(e12.DIAL_NAMES)},
            "note": "C1/C2 are encoder-independent (same stills for every "
                    "encoder) — taken from the first encoder that ran",
        }
        # staging fidelity (encoder-independent): targets vs bank labels,
        # read back off the first still of each Arm-B room (= its label row).
        arm_a, arm_b = build_arm_items()
        t = np.array([tgt for _n, tgt, _s, _src in arm_b], float)
        labs = aux0["Yb"][::e9.N_STILLS]  # first still per room = room label
        shared["staging_fidelity_spearman_target_vs_label"] = {
            d: round(e12.spearman(t[:, i], labs[:, i]), 4)
            for i, d in enumerate(e12.DIAL_NAMES)}

    leaderboard = []
    for spec in REGISTRY:
        r = results.get(spec["key"], {})
        leaderboard.append({
            "encoder": spec["key"], "hf_id": spec["hf_id"],
            "role": spec["role"], "status": r.get("status"),
            "verdict": r.get("verdict"),
            "r2_still_loro_k64": r.get("r2_still_loro_k64"),
            "r2_room_loro_k64": r.get("r2_room_loro_k64"),
            "perm_null95_k64": r.get("perm_null95_k64"),
            "g1_pass_count": r.get("g1_pass_count"),
            "armA_room_identity_acc": r.get("controls_armA", {}).get(
                "room_identity_acc") if r.get("controls_armA") else None,
            "vram": r.get("vram"),
            "reason": r.get("reason"),
        })

    out = {
        "experiment": "E15 encoder-swap dial-read leaderboard",
        "device": dev, "seed": SEED, "guard_preflight": guard_info,
        "download_opt_in": allow_download,
        "dial_names": e12.DIAL_NAMES,
        "k_primary": e12.K_PRIMARY,
        "e12_published_reference": E12_PUBLISHED,
        "shared": shared,
        "encoders": results,
        "leaderboard": leaderboard,
        "gates": gates,
        "verdict": verdict,
        "note": (
            "E12's dial-read pipeline (same 27-room staged bank, same "
            "elephant-bank labels, same ridge/LORO/perm-null) re-run under "
            "each frozen encoder. Per-encoder gate = E12 G1 verbatim. "
            "INVALID_CONTROL: the I-JEPA control failed to replicate E12's "
            "KEEP in THIS run (comparison void). KEEP: >=1 non-I-JEPA "
            "encoder reads >=2/3 dials at E12's thresholds -> room-geometry "
            "property. KILL: every valid non-I-JEPA swap fails where I-JEPA "
            "keeps -> I-JEPA's inductive bias is load-bearing. Skipped/"
            "failed/INVALID_HARNESS swaps never silently become a KILL. "
            "Caveats: staged carriers (E12's limit); vjepa2 rows are "
            "16-frame windows anchored at each still; CLS tokens included "
            "in the uniform mean-pool for dinov2/clip."),
    }
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
