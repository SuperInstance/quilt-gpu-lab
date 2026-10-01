#!/usr/bin/env python3
"""C5 paired-condition action probe — frozen per proposals/runs/C5-paired-action-plan.md.
Deterministic (no free RNG; shuffle control seed 11). Reuses c3_make_data + c3_probe
(module-safe), model-load discipline copied from c4_action_probe.

Design: 4 frame-aligned windows per REAL source (av_0, av_1) x 2 conditions
(forward = c3 geometry verbatim; reversed = SAME bytes, frame order flipped —
flipping the raw frames in python is exact, no filter-chain gambles).
16 clips, identity balanced across conditions by construction.
H1 action-in-latent: fwd-vs-rev LOOCV AUC >= 0.75 (bands in plan)
H2 beyond endpoints: emb AUC >= pixel-endpoint AUC + 0.05
H3 identity anchor: av0-vs-av1 AUC within fwd >= 0.90 (replicates C4)
Harness control: label-shuffle (seed 11) action AUC in [0.35, 0.65] else HARNESS_INVALID.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import numpy as np

import c3_make_data as mk
import c3_probe as c3

OUT_JSON = os.path.join(LAB, "results", "c5_paired_action.json")
CHECKPOINT = os.path.join(LAB, "results", "c5_embeddings_checkpoint.json")
CLIP_DIR = os.path.join(LAB, "data", "c5")
SOURCES = mk.REAL_SOURCES
N_PER = 4
SHUFFLE_SEED = 11
FS = mk.W * mk.H * 3  # bytes per raw frame


def log(msg):
    print("[c5 %s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def loocv_centroid_auc(X, y):
    """Leave-one-out nearest-centroid AUC (rank-exact) — c4's exact pattern."""
    X = np.asarray(X)
    y = np.asarray(y)
    pos, neg = [], []
    for i in range(len(y)):
        keep = [j for j in range(len(y)) if j != i]
        sc = c3.nearest_centroid_scores(X[keep], y[keep], X[i:i + 1])[0]
        (pos if y[i] == 1 else neg).append(float(sc))
    return c3.auc_exact(pos, neg)


def make_clips(ffmpeg):
    os.makedirs(CLIP_DIR, exist_ok=True)
    clips, meta = [], []  # meta rows: (video_idx, window_idx, cond)
    for vi, src in enumerate(SOURCES):
        p = os.path.join(mk.SNAP, "assets", src)
        if not os.path.isfile(p):
            sys.exit("[c5] FATAL: missing source %s" % p)
        probe = mk.probe_source(ffmpeg, p)
        sha = mk.sha256_file(p)
        for ci, t0 in enumerate(mk.pick_frames(mk.frame_starts(probe["duration_s"]),
                                               N_PER, "c5/av%d" % vi)):
            fwd = os.path.join(CLIP_DIR, "av%d_%02d_fwd.rgb" % (vi, ci))
            rev = os.path.join(CLIP_DIR, "av%d_%02d_rev.rgb" % (vi, ci))
            mk.run_ffmpeg(mk.real_clip(ffmpeg, p, t0, fwd)["argv"])
            if os.path.getsize(fwd) != mk.BYTES_PER_CLIP:
                sys.exit("[c5] FATAL: %s wrong size" % fwd)
            data = open(fwd, "rb").read()
            fr = [data[i * FS:(i + 1) * FS] for i in range(mk.FRAMES)]
            open(rev, "wb").write(b"".join(reversed(fr)))  # exact: same frames, flipped
            if os.path.getsize(rev) != mk.BYTES_PER_CLIP:
                sys.exit("[c5] FATAL: %s wrong size" % rev)
            for cond, path in (("fwd", fwd), ("rev", rev)):
                clips.append({"path": os.path.relpath(path, LAB),
                              "domain": "av%d" % vi, "split": "all",
                              "idx": len(clips), "family": None,
                              "source": src, "sha256": sha})
                meta.append((vi, ci, cond))
    log("clips: %d (%d src x %d windows x 2 conds)" % (len(clips), len(SOURCES), N_PER))
    return clips, meta


def pixel_endpoint_features():
    """H2 baseline: frame0 + frame15 downsampled 16x16 gray, flattened (512-d).
    Built for ALL 16 clips (fwd AND rev — the rev clip's endpoints are the
    swapped pair, which is exactly the directional signal a cheap feature
    should be able to see). Row order matches clips/meta/y_cond exactly."""
    feats = []
    for vi in range(len(SOURCES)):
        for ci in range(N_PER):
            for cond in ("fwd", "rev"):
                data = open(os.path.join(CLIP_DIR, "av%d_%02d_%s.rgb" % (vi, ci, cond)), "rb").read()
                v = []
                for fi in (0, mk.FRAMES - 1):
                    f = np.frombuffer(data[fi * FS:(fi + 1) * FS], dtype=np.uint8)
                    g = f.reshape(mk.H, mk.W, 3).mean(axis=2)
                    small = g.reshape(16, 16, 16, 16).mean(axis=(1, 3)) / 255.0
                    v.append(small.ravel())
                feats.append(np.concatenate(v))
    return np.array(feats)


def main():
    c3.preflight()  # VRAM/temp guard (fail loud)
    ffmpeg = mk.resolve_bin("C3_FFMPEG", "/home/eileen/.local/bin/ffmpeg", "ffmpeg")
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)

    clips, meta = make_clips(ffmpeg)

    # --- resume path: the 22:28 crash happened AFTER extraction (scoring-stage bug),
    # so the checkpoint lets the re-run skip the GPU entirely (metric bugs never lose GPU work)
    resumed = None
    if os.path.isfile(CHECKPOINT):
        try:
            d = json.load(open(CHECKPOINT))
            if len(d["records"]) == len(clips) and \
               [list(m) for m in d["meta"]] == [list(m) for m in meta]:
                resumed = d
                log("RESUME: checkpoint matches (%d records) — scoring only, no GPU" % len(d["records"]))
        except Exception as e:  # noqa: BLE001 — unreadable checkpoint = full run
            log("checkpoint unreadable (%r) — full run" % e)

    if resumed is not None:
        records = resumed["records"]
        batch_final = {"resumed": True}
        peak = 0.0
        visual_dtype = visual_type = "checkpoint-resume"
    else:
        # --- model: skip-tower recipe + fail-loud receipt (c4's block) ---
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
            sys.exit("[c5] FATAL: INVALID_HARNESS (visual %s/%s)" % (visual_dtype, visual_type))
        log("model loaded %.1fs, receipt %s/%s" % (time.time() - t0, visual_dtype, visual_type))

        # --- extract embeddings, checkpoint before scoring ---
        torch.cuda.reset_peak_memory_stats()
        records, batch_final = c3.extract_all(model, proc, clips, ffmpeg)
        json.dump({"records": records, "meta": [list(m) for m in meta]},
                  open(CHECKPOINT, "w"))
        log("checkpoint: embeddings persisted")
        peak = torch.cuda.max_memory_allocated() / 2 ** 30
        torch.cuda.empty_cache()
    X = np.array([[float(v) for v in r["emb_tokens_f16"]] for r in records], dtype=np.float64)

    # --- frozen probes ---
    y_cond = [1 if m[2] == "rev" else 0 for m in meta]
    y_vid = [m[0] for m in meta]
    fwd_idx = [i for i, m in enumerate(meta) if m[2] == "fwd"]
    rev_idx = [i for i, m in enumerate(meta) if m[2] == "rev"]

    auc_cond = loocv_centroid_auc(X, y_cond)
    auc_id_fwd = loocv_centroid_auc(X[fwd_idx], [y_vid[i] for i in fwd_idx])
    auc_id_rev = loocv_centroid_auc(X[rev_idx], [y_vid[i] for i in rev_idx])
    # informational: identity cross-condition (train fwd -> test rev)
    # ytr MUST be ndarray: `list == int` is just False, which made an empty class
    # and NaN centroids (the 22:28 crash)
    sc = c3.nearest_centroid_scores(X[fwd_idx], np.array([y_vid[i] for i in fwd_idx]), X[rev_idx])
    id_xhits = sum(1 for i, s in zip(rev_idx, sc)
                   if (s > 0) == (y_vid[i] == 1))
    id_xacc = round(id_xhits / max(len(rev_idx), 1), 4)

    P = pixel_endpoint_features()
    auc_pixel = loocv_centroid_auc(P, y_cond)

    rng = np.random.default_rng(SHUFFLE_SEED)
    y_shuf = list(rng.permutation(np.array(y_cond)))
    auc_shuf = loocv_centroid_auc(X, y_shuf)
    harness_ok = 0.35 <= auc_shuf <= 0.65

    if not harness_ok:
        verdicts = {"verdict": "HARNESS_INVALID",
                    "reason": "shuffle control out of band: %.4f" % auc_shuf}
    else:
        h1 = ("KEEP" if auc_cond >= 0.75 else
              "KILL/CONTENT_ONLY" if auc_cond <= 0.55 else "WEAK_UNRESOLVED")
        h2 = "KEEP" if auc_cond >= auc_pixel + 0.05 else "KILL"
        h3 = "KEEP" if auc_id_fwd >= 0.90 else "KILL"
        verdicts = {"H1_action_in_latent": h1, "H2_beyond_endpoints": h2,
                    "H3_identity_anchor": h3}

    log("auc_cond=%.4f auc_pixel=%.4f auc_id_fwd=%.4f auc_id_rev=%.4f id_xacc=%.4f "
        "auc_shuf=%.4f -> %s" % (auc_cond, auc_pixel, auc_id_fwd, auc_id_rev,
                                 id_xacc, auc_shuf, json.dumps(verdicts)))

    json.dump({
        "schema": "c5-paired-action/1",
        "plan": "proposals/runs/C5-paired-action-plan.md",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "visual_dtype": visual_dtype, "visual_type": visual_type,
        "batch_final": batch_final, "peak_alloc_gib": round(peak, 2),
        "n_clips": len(clips), "windows_per_source": N_PER,
        "shuffle_seed": SHUFFLE_SEED,
        "gate": {"H1_auc_bar": 0.75, "H1_content_bar": 0.55,
                 "H2_margin": 0.05, "H3_auc_bar": 0.90,
                 "shuffle_band": [0.35, 0.65]},
        "auc_cond": round(auc_cond, 4), "auc_pixel_endpoint": round(auc_pixel, 4),
        "auc_id_fwd": round(auc_id_fwd, 4), "auc_id_rev": round(auc_id_rev, 4),
        "id_crosscond_acc": id_xacc, "auc_shuffle_control": round(auc_shuf, 4),
        "harness_ok": harness_ok, "verdicts": verdicts,
        "checkpoint": os.path.relpath(CHECKPOINT, LAB),
        "clips": [{"path": c["path"], "video": m[0], "window": m[1], "cond": m[2]}
                  for c, m in zip(clips, meta)],
    }, open(OUT_JSON, "w"), indent=1)
    log("DONE")


if __name__ == "__main__":
    main()
