#!/usr/bin/env python3
"""C4 action-separability probe — frozen per proposals/runs/C4-action-probe-plan.md.
Deterministic (no RNG). Reuses c3_make_data (clip pipeline) + c3_probe (loader,
extraction, AUC) — both module-safe (guarded mains)."""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import c3_make_data as mk
import c3_probe as c3

OUT_JSON = os.path.join(LAB, "results", "c4_action_probe.json")
CLIP_DIR = os.path.join(LAB, "data", "c4")
SOURCES = ["example_action_id_av_0_input.mp4", "example_action_id_av_1_input.mp4"]
N_PER = 8


def log(msg):
    print("[c4 %s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def loocv_centroid_auc(X, y):
    """Leave-one-out nearest-centroid AUC (rank-exact)."""
    pos, neg = [], []
    for i in range(len(y)):
        keep = [j for j in range(len(y)) if j != i]
        Xtr = X[keep]
        ytr = y[keep]
        sc = c3.nearest_centroid_scores(Xtr, ytr, X[i:i + 1])[0]
        (pos if y[i] == 1 else neg).append(float(sc))
    return c3.auc_exact(pos, neg)


def main():
    c3.preflight()  # VRAM/temp guard (fail loud)
    ffmpeg = mk.resolve_bin("C3_FFMPEG", "/home/eileen/.local/bin/ffmpeg", "ffmpeg")
    os.makedirs(CLIP_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)

    # 1) deterministic clip set: 8 even-t0 windows per source
    clips = []  # dicts for extract_all
    meta = []   # (video, half) for labeling
    for vi, src in enumerate(SOURCES):
        p = os.path.join(mk.SNAP, "assets", src)
        if not os.path.isfile(p):
            sys.exit("[c4] FATAL: missing source %s" % p)
        probe = mk.probe_source(ffmpeg, p)
        sha = mk.sha256_file(p)
        log("source %s: %s" % (src, probe))
        for ci, t0 in enumerate(mk.real_t0s(probe["duration_s"], N_PER)):
            out_path = os.path.join(CLIP_DIR, "av%d_%02d.rgb" % (vi, ci))
            mk.run_ffmpeg(mk.real_clip(ffmpeg, p, t0, out_path)["argv"])
            size = os.path.getsize(out_path)
            if size != mk.BYTES_PER_CLIP:
                sys.exit("[c4] FATAL: %s %d bytes != %d" % (out_path, size, mk.BYTES_PER_CLIP))
            clips.append({
                "path": os.path.relpath(out_path, LAB), "domain": "av%d" % vi,
                "split": "all", "idx": vi * N_PER + ci, "family": None,
                "source": src, "sha256": sha,
            })
            meta.append((vi, ci // (N_PER // 2)))
    log("clips: %d (%d/video)" % (len(clips), N_PER))

    # 2) load model — skip-tower recipe + fail-loud receipt (copied from c3_probe.inner)
    import torch
    from transformers import AutoProcessor, BitsAndBytesConfig
    try:
        from transformers import Cosmos3EdgeForConditionalGeneration as M
    except ImportError:
        from transformers.models.cosmos3_edge.modeling_cosmos3_edge import \
            Cosmos3EdgeForConditionalGeneration as M
    quant = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        llm_int8_skip_modules=c3.SKIP_MODULES)
    t0 = time.time()
    model = M.from_pretrained(c3.MODEL_ID, quantization_config=quant,
                              device_map="auto", torch_dtype=torch.bfloat16)
    model.eval()
    proc = AutoProcessor.from_pretrained(c3.MODEL_ID)
    p0 = next(model.model.visual.parameters())
    visual_dtype, visual_type = str(p0.dtype), type(p0).__name__
    if not (visual_dtype == "torch.bfloat16" and visual_type == "Parameter"):
        json.dump({"verdict": "INVALID_HARNESS", "visual_dtype": visual_dtype,
                   "visual_type": visual_type,
                   "reason": "skip-tower failed"}, open(OUT_JSON, "w"), indent=1)
        sys.exit("[c4] FATAL: INVALID_HARNESS (visual %s/%s)" % (visual_dtype, visual_type))
    log("model loaded %.1fs, receipt %s/%s" % (time.time() - t0, visual_dtype, visual_type))

    # 3) extract layer-B embeddings
    torch.cuda.reset_peak_memory_stats()
    records, batch_final = c3.extract_all(model, proc, clips, ffmpeg)
    peak = torch.cuda.max_memory_allocated() / 2 ** 30
    torch.cuda.empty_cache()
    X = [[float(v) for v in r["emb_tokens_f16"]] for r in records]
    import numpy as np
    X = np.array(X, dtype=np.float64)

    # 4) sets + LOOCV AUCs
    y_cross = [m[0] for m in meta]                       # video id
    y_time = [m[1] for m in meta]                        # early/late half
    auc_cross = loocv_centroid_auc(X, y_cross)
    auc_time = loocv_centroid_auc(X, y_time)
    diff = auc_cross - auc_time
    verdict = ("ACTION_SEPARABLE" if diff >= 0.10 else
               "CONTENT_DOMINANT" if diff <= 0.0 else "WEAK_UNRESOLVED")
    log("AUC cross=%.4f time=%.4f diff=%+.4f -> %s" % (auc_cross, auc_time, diff, verdict))

    json.dump({
        "schema": "c4-action-probe/1",
        "plan": "proposals/runs/C4-action-probe-plan.md",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "visual_dtype": visual_dtype, "visual_type": visual_type,
        "batch_final": batch_final, "peak_alloc_gib": round(peak, 2),
        "n_clips": len(clips), "n_per_video": N_PER,
        "gate": {"diff_threshold": 0.10,
                 "bands": ["ACTION_SEPARABLE >=0.10", "CONTENT_DOMINANT <=0.00",
                           "WEAK_UNRESOLVED between"]},
        "auc_cross": round(auc_cross, 4), "auc_time": round(auc_time, 4),
        "diff": round(diff, 4), "verdict": verdict,
        "clips": [{"path": c["path"], "video": m[0], "half": m[1]}
                  for c, m in zip(clips, meta)],
    }, open(OUT_JSON, "w"), indent=1)
    log("DONE")


if __name__ == "__main__":
    main()
