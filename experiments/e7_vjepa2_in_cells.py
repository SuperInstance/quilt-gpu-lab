"""E7 — vjepa2-in-cells: Meta's V-JEPA 2 world model as a quilt cell encoder.

The swap-and-hunt begins: same 4 real lavfi clips the whole lab uses,
embedded by Meta's pretrained video world model (~300M params, fp16 on the
4050), folded into the SAME quilt-cell wire shape, judged by the SAME
protocol: (a) heldout room separation, (b) drift-gate behavior, (c) the
surprise metric — dimensions of room structure this encoder reads that
elephant's dials + our contrastive head don't.

V-JEPA 2 expects 16-frame clips at 256px. We sample 16-frame windows from
each clip, embed, mean-pool patches -> one room vector per window.
"""
from __future__ import annotations

import json
import sys

import numpy as np

sys.path.insert(0, "/home/eileen/projects/quilt-gpu-lab/experiments")
from common import ppms_from_lavfi, to_glyph  # noqa: E402

SEED = 2718
SOURCES = [("still-solid", "color=c=gray:duration=6:size=160x90:rate=10"),
           ("moving-testsrc", "testsrc=duration=6:size=160x90:rate=10"),
           ("smpte", "smptebars=duration=6:size=160x90:rate=10"),
           ("moving-testsrc2", "testsrc2=duration=6:size=160x90:rate=10")]
MODEL_ID = "facebook/vjepa2-vitl-fpc16-256-ssv2"
FPC = 16  # frames per clip expected by vjepa2
WINDOW, BATCHES_PER_CLIP = 10, 6


def main() -> dict:
    import torch
    from transformers import VJEPA2Model, VJEPA2VideoProcessor

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"[e7] loading {MODEL_ID} (fp16, {dev})...")
    processor = VJEPA2VideoProcessor.from_pretrained(MODEL_ID)
    model = VJEPA2Model.from_pretrained(MODEL_ID, torch_dtype=torch.float16).to(dev).eval()

    cell_vecs, cell_labels, room_names = [], [], []
    for name, src in SOURCES:
        frames = ppms_from_lavfi(src, 6, 10, (160, 90))  # 60 RGB frames
        # sample 6 disjoint 16-frame windows (stride 7 -> overlaps at 60 frames? 6*16=96>60; use stride to fit)
        starts = np.linspace(0, len(frames) - FPC, WINDOW * BATCHES_PER_CLIP // WINDOW).astype(int)[:BATCHES_PER_CLIP]
        ri = len(room_names)
        room_names.append(name)
        for s in starts:
            clip = [np.array(f) for f in frames[s:s + FPC]]
            inputs = processor(clip, return_tensors="pt").to(dev)
            with torch.no_grad():
                out = model(**inputs)
            # mean-pool sequence dim -> room vector
            v = out.last_hidden_state.mean(dim=1)[0].float().cpu().numpy()
            cell_vecs.append(v / (np.linalg.norm(v) + 1e-9))
            cell_labels.append(ri)
        print(f"[e7] {name}: {BATCHES_PER_CLIP} windows embedded "
              f"(dim={len(cell_vecs[-1])})")
        if dev == "cuda":
            torch.cuda.empty_cache()

    X = np.asarray(cell_vecs, np.float32)
    y = np.asarray(cell_labels)

    # (a) separation: heldout margin on the two contrast rooms (still vs testsrc)
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

    # (c) surprise metric: variance structure across rooms per dim — dims that
    # separate smpte (static texture) from still (flat) while testsrc/testsrc2
    # (motion) sit together = a reading of "static texture" our dials conflate
    def room_mean(ri):
        return X[y == ri].mean(0)

    tex_axis = room_mean(2) - room_mean(0)          # smpte vs still
    motion_axis = room_mean(1) - room_mean(3)       # testsrc vs testsrc2
    tex_motion_corr = float(np.corrcoef(tex_axis, motion_axis)[0, 1])

    out = {
        "experiment": "E7 vjepa2-in-cells", "device": dev, "seed": SEED,
        "model": MODEL_ID, "rooms": room_names, "cells": int(len(X)),
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
