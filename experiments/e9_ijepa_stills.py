"""E9 — ijepa-stills: I-JEPA (still-image world model) on STILL frames
through the same cell contract.

E7 asked whether a VIDEO world model reads the lab's 4 rooms. E9 asks the
twin question: does a STILL-image world model read rooms differently?
Same real lavfi sources, same room vectors, same heldout-separation and
tex-vs-motion axis readings — but one embedding per STILL (evenly spaced
frames), not per 16-frame clip. Same JSON verdict shape as E7 so the E8
leaderboard parses it with the same field names.

Model: tasked id is facebook/ijepa_vitb (HF-native IJepaModel, transformers
5.17). Honest note at write time (2026-09-27): that id is not published on
the HF hub (401), and facebookresearch/ijepa ships no hubconf (its own
scout note in MODELS.md anticipated this) — so the loader falls back to the
closest OFFICIAL facebook still-image JEPA that IS on the hub
(facebook/ijepa_vith16_1k, fp16 — fits the 4050). model_requested vs model
are both recorded; the leaderboard row carries the model actually used.
If neither id resolves, E9 aborts with a parseable JSON — failures are data.

Guard: same VRAM/thermal policy as runner.py's wrapper (guard.py), applied
in-process as a preflight before any model load.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB / "experiments"))
from common import ppms_from_lavfi  # noqa: E402

SEED = 2718
SOURCES = [("still-solid", "color=c=gray:duration=6:size=160x90:rate=10"),
           ("moving-testsrc", "testsrc=duration=6:size=160x90:rate=10"),
           ("smpte", "smptebars=duration=6:size=160x90:rate=10"),
           ("moving-testsrc2", "testsrc2=duration=6:size=160x90:rate=10")]
MODEL_REQUESTED = "facebook/ijepa_vitb"
MODEL_FALLBACKS = ("facebook/ijepa_vith16_1k",)
N_STILLS = 12
SIZE = (224, 224)  # ViT-B/16 native input
MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)


def preflight_guard() -> tuple[bool, str | None, dict]:
    """Same policy as guard.py (FREE_FLOOR_MIB / TEMP_CEIL_C), in-process."""
    from guard import FREE_FLOOR_MIB, TEMP_CEIL_C, sample
    free, temp = sample()
    info = {"free_vram_mib": free, "temp_c": temp}
    if free is None:
        return False, "preflight: nvidia-smi unavailable", info
    if free < FREE_FLOOR_MIB:
        return False, f"preflight: free VRAM {free} MiB < {FREE_FLOOR_MIB}", info
    if temp > TEMP_CEIL_C:
        return False, f"preflight: temp {temp}C > {TEMP_CEIL_C}C", info
    return True, None, info


def load_encoder(dev: str):
    """Try tasked id, then documented official fallbacks. Returns
    (model_used, model, processor|None, load_notes)."""
    import torch
    from transformers import AutoModel
    notes: dict = {}
    for mid in (MODEL_REQUESTED, *MODEL_FALLBACKS):
        try:
            model = AutoModel.from_pretrained(mid, torch_dtype=torch.float16)
            model = model.to(dev).eval()
        except Exception as e:
            notes[mid] = f"load failed: {type(e).__name__}: {e}"[:300]
            continue
        proc = None
        try:
            from transformers import AutoImageProcessor
            proc = AutoImageProcessor.from_pretrained(mid)
        except Exception as e:
            notes[mid] = "loaded; no hub processor — manual ImageNet preprocessing"
            notes[mid + "/processor_err"] = str(e)[:200]
        return mid, model, proc, notes
    raise RuntimeError(f"no I-JEPA checkpoint loadable: {notes}")


def preprocess(frames: list, processor, dev: str) -> "object":
    from PIL import Image
    import torch
    pil = [Image.fromarray(np.asarray(f, np.uint8)) for f in frames]
    if processor is not None:
        inputs = processor(pil, return_tensors="pt")
        return inputs["pixel_values"].to(dev, torch.float16)
    x = np.stack([np.asarray(im.resize(SIZE, Image.BILINEAR), np.float32)
                  for im in pil]) / 255.0
    x = (x - MEAN) / STD
    return torch.from_numpy(x).permute(0, 3, 1, 2).to(dev, torch.float16)


def embed(model, pixel) -> np.ndarray:
    """(B,3,Hi,Wi) -> (B,C) mean-pooled patch embeddings, L2-ready."""
    import torch
    with torch.no_grad():
        out = model(pixel_values=pixel)
    h = getattr(out, "last_hidden_state", None)
    if h is None:
        h = out[0]
    pooled = h.mean(dim=1) if h.dim() == 3 else h
    return pooled.float().cpu().numpy()


def main() -> dict:
    import torch

    ok, reason, guard_info = preflight_guard()
    if not ok:
        out = {"experiment": "E9 ijepa-stills", "verdict": "ABORTED",
               "reason": reason, "guard_preflight": guard_info}
        print(json.dumps(out, indent=2))
        return out

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"[e9] loading I-JEPA (requested {MODEL_REQUESTED}, {dev})...")
    try:
        model_used, model, processor, load_notes = load_encoder(dev)
    except Exception as e:
        out = {"experiment": "E9 ijepa-stills", "verdict": "ABORTED",
               "reason": f"model load failed: {e}", "guard_preflight": guard_info}
        print(json.dumps(out, indent=2))
        return out
    print(f"[e9] using {model_used}")

    cell_vecs, cell_labels, room_names = [], [], []
    for name, src in SOURCES:
        frames = ppms_from_lavfi(src, 6, 10, (160, 90))  # 60 RGB frames
        idx = np.linspace(0, len(frames) - 1, N_STILLS).round().astype(int)
        stills = [frames[i] for i in idx]  # stills, not clips — that's the point
        pixel = preprocess(stills, processor, dev)
        vecs = embed(model, pixel)
        ri = len(room_names)
        room_names.append(name)
        for v in vecs:
            n = np.linalg.norm(v) + 1e-9
            cell_vecs.append(v / n)
            cell_labels.append(ri)
        print(f"[e9] {name}: {len(stills)} stills embedded (dim={vecs.shape[1]})")
        if dev == "cuda":
            torch.cuda.empty_cache()

    X = np.asarray(cell_vecs, np.float32)
    y = np.asarray(cell_labels)

    # same separation reading as E7: centroids from the first half of each
    # room's stills, within-room cosine on the held-out second half
    def sep(ri_a, ri_b):
        a, b = X[y == ri_a], X[y == ri_b]
        half = min(len(a), len(b)) // 2
        ca, cb = a[:half].mean(0), b[:half].mean(0)
        ca, cb = ca / np.linalg.norm(ca), cb / np.linalg.norm(cb)
        within_a = float((a[half:] @ ca).mean()) if len(a) > half else float("nan")
        within_b = float((b[half:] @ cb).mean()) if len(b) > half else float("nan")
        return float(ca @ cb), within_a, within_b

    cross, wa, wb = sep(0, 1)
    gap = min(wa, wb) - cross

    # same axis reading as E7: does the smpte-vs-still (static texture) axis
    # correlate with the testsrc-vs-testsrc2 (motion) axis?
    def room_mean(ri):
        return X[y == ri].mean(0)

    tex_axis = room_mean(2) - room_mean(0)
    motion_axis = room_mean(1) - room_mean(3)
    tex_motion_corr = float(np.corrcoef(tex_axis, motion_axis)[0, 1])

    out = {
        "experiment": "E9 ijepa-stills", "device": dev, "seed": SEED,
        "model_requested": MODEL_REQUESTED, "model": model_used,
        "load_notes": load_notes,
        "rooms": room_names, "stills_per_room": N_STILLS, "cells": int(len(X)),
        "emb_dim": int(X.shape[1]),
        "still_vs_testsrc_cross_cos": round(cross, 4),
        "within_still": round(wa, 4), "within_testsrc": round(wb, 4),
        "heldout_gap": round(gap, 4),
        "tex_vs_motion_axis_corr": round(tex_motion_corr, 4),
    }
    out["verdict"] = "KEEP" if gap > 0.05 else "INCONCLUSIVE"
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
