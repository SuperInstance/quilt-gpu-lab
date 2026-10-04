#!/usr/bin/env python3
"""C3b real-footage anchoring — frozen per proposals/runs/C3b-real-anchoring-plan.md.

Question: C3's ANCHORING_REPLICATED rode a 2-source real set. Does domain
structure survive when "real" = 21 diverse licensed clips (H1 delivery)?

Frozen probes (explicit-sign cosines throughout; layer B primary):
  G1 (supporting): synth centroid = C3 train synth; real centroid = 21 NEW
     diverse clips; AUC on C3's frozen 64-clip val set. Bar 0.90.
  G2 (verdict): temporal-half identity matching, halfA (frames 0-7) vs
     halfB (frames 8-15), top-1 cosine among 21, chance 1/21.
     >=12 SURVIVES / <=6 COLLAPSE / 7-11 WEAK. Pixel baseline informational.
  G3 (verdict): project 21 clips on C3's frozen train axis
     (real_c3 - synth_c3); >=16/21 real-side. Sanity clause: C3 val real
     32/32 + val synth 0/32 real-side, else INVALID_HARNESS.

Laws honored: skip-tower loader + dtype receipt (C2-a5b); checkpoint
embeddings BEFORE scoring (C4/C5); ramp receipt >=0.6s sustained synced
load before measurement (INSTRUMENT-01); list-form subprocess only;
fail-loud everywhere; prereg stamp embedded at run start.

Fire: /home/eileen/venvs/elephant-gpu/bin/python experiments/c3b_real_anchoring.py
Writes: results/c3b_real_anchoring.json (+ c3b_embeddings_checkpoint.json).
"""
import hashlib
import json
import math
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, LAB)

import numpy as np

import c3_probe as c3
from tools import prereg_stamp

PLAN = "proposals/runs/C3b-real-anchoring-plan.md"
MANIFEST = os.path.join(LAB, "results", "c3b_clips", "MANIFEST.json")
C3_JSON = os.path.join(LAB, "results", "c3_probe.json")
OUT_JSON = os.path.join(LAB, "results", "c3b_real_anchoring.json")
CHECKPOINT = os.path.join(LAB, "results", "c3b_embeddings_checkpoint.json")
HALF_DIR = os.path.join(LAB, "data", "c3b_halves")

FS = c3.W * c3.H * 3          # 196608 bytes per raw frame
FULL_BYTES = c3.FRAMES * FS   # 3145728
HALF_BYTES = (c3.FRAMES // 2) * FS

G1_GATE = 0.90
G2_SURVIVE, G2_COLLAPSE = 12, 6
G2_CHANCE = 1.0 / 21.0
G3_GATE = 16


def log(msg):
    print("[c3b %s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


# ------------------------------------------------------------------ data ---
def verify_clips(manifest):
    """Byte-count + sha256 every one of the 21 clips. Fail loud."""
    for rec in manifest["clips"]:
        p = os.path.join(LAB, rec["path"])
        if os.path.getsize(p) != rec["bytes"]:
            sys.exit("[c3b] FATAL: %s size mismatch" % rec["path"])
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest() != rec["sha256"]:
            sys.exit("[c3b] FATAL: %s sha256 mismatch vs manifest" % rec["path"])
    log("verified %d c3b clips vs MANIFEST.json" % len(manifest["clips"]))


def build_units(manifest, ffmpeg_bin):
    """63 extraction units: 21 fulls + per clip halfA/halfB byte slices.
    Halves are deterministic byte surgery into data/c3b_halves/ (gitignored)."""
    os.makedirs(HALF_DIR, exist_ok=True)
    units = []
    for rec in manifest["clips"]:
        slug = rec["slug"]
        src = os.path.join(LAB, rec["path"])
        data = open(src, "rb").read()
        if len(data) != FULL_BYTES:
            sys.exit("[c3b] FATAL: %s %d bytes != %d" % (slug, len(data), FULL_BYTES))
        half_a = os.path.join(HALF_DIR, "%s__a.rgb" % slug)
        half_b = os.path.join(HALF_DIR, "%s__b.rgb" % slug)
        open(half_a, "wb").write(data[:HALF_BYTES])
        open(half_b, "wb").write(data[HALF_BYTES:])
        for unit, path, nf in (("full", src, c3.FRAMES),
                               ("halfA", half_a, c3.FRAMES // 2),
                               ("halfB", half_b, c3.FRAMES // 2)):
            units.append({"unit": unit, "slug": slug,
                          "path": os.path.relpath(path, LAB),
                          "n_frames": nf, "sha256": rec["sha256"],
                          # extract_all-shaped fields:
                          "domain": slug, "split": "all", "idx": len(units),
                          "family": None, "source": slug})
    log("units: %d (21 full + 42 half)" % len(units))
    return units


def decode_clip(clip_path, n_frames, ffmpeg_bin, tmpdir):
    """c3.decode_clip_ffmpeg, frame-count-parameterized (halves need 8)."""
    out_pat = os.path.join(tmpdir, "frame_%06d.png")
    r = subprocess.run(
        [ffmpeg_bin, "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (c3.W, c3.H),
         "-i", clip_path, "-vsync", "0", "-vcodec", "png", out_pat],
        capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("[c3b] FATAL: ffmpeg decode %s rc=%d stderr=%s"
                 % (clip_path, r.returncode, r.stderr[-300:]))
    files = sorted(f for f in os.listdir(tmpdir) if f.endswith(".png"))
    if len(files) != n_frames:
        sys.exit("[c3b] FATAL: %s -> %d frames (want %d)"
                 % (clip_path, len(files), n_frames))
    from PIL import Image
    frames = []
    for f in files:
        frames.append(Image.open(os.path.join(tmpdir, f)).convert("RGB"))
        os.remove(os.path.join(tmpdir, f))
    return frames


# ------------------------------------------------------------- GPU laws ---
def ramp_receipt(torch, min_s=0.6, n=32_000_000):
    """INSTRUMENT-01: >=0.6s sustained SYNCED elementwise load, per-iter
    timings booked. No measurement without this receipt."""
    a = torch.randn(n, device="cuda")
    b = torch.randn(n, device="cuda")
    torch.cuda.synchronize()
    t0, per = time.perf_counter(), []
    while time.perf_counter() - t0 < min_s:
        s = time.perf_counter()
        _ = a * b
        torch.cuda.synchronize()
        per.append(time.perf_counter() - s)
    return {"warm_s": round(time.perf_counter() - t0, 3), "iters": len(per),
            "per_iter_ms": {"min": round(min(per) * 1e3, 2),
                            "mean": round(float(np.mean(per)) * 1e3, 2),
                            "max": round(max(per) * 1e3, 2)},
            "law": "INSTRUMENT-01 calibrated 2026-10-01: >=0.6s sustained "
                   "synced load restores >=97% of hot throughput"}


def extract_units(model, proc, units, ffmpeg_bin):
    """c3.extract_all adapted: per-unit frame counts; fulls and halves in
    separate pass groups (never mixed frame-counts in one processor call);
    batches of 4 with OOM auto-halving; fail loud at batch 1."""
    import torch
    visual = model.model.visual
    projector = model.model.projector
    merge = int(getattr(projector, "spatial_merge_size", 2) or 2)
    dtype = next(visual.parameters()).dtype
    device = next(visual.parameters()).device

    def forward_batch(recs):
        from PIL import Image  # noqa: F401  (decode loads PIL itself)
        groups = []
        with tempfile.TemporaryDirectory(prefix="c3b_frames_") as td:
            for rec in recs:
                groups.append(decode_clip(os.path.join(LAB, rec["path"]),
                                          rec["n_frames"], ffmpeg_bin, td))
        try:
            inputs = proc(videos=groups, return_tensors="pt")
        except Exception as e:
            log("processor videos-only failed (%s); text-placeholder "
                "fallback (mechanical, logged)" % type(e).__name__)
            inputs = proc(text=[""] * len(groups), videos=groups,
                          return_tensors="pt")
        key_px = next((k for k in ("pixel_values_videos", "pixel_values")
                       if k in inputs), None)
        key_grid = next((k for k in ("video_grid_thw", "image_grid_thw")
                         if k in inputs), None)
        if key_px is None or key_grid is None:
            raise RuntimeError("processor keys missing: %s" % list(inputs))
        px = inputs[key_px].to(device).type(dtype)
        grid = inputs[key_grid].to(device)
        with torch.no_grad():
            vo = visual(px, grid_thw=grid, return_dict=True)
            tok = projector(vo.last_hidden_state)
        sizes_tower = [int(v) for v in grid.prod(-1).tolist()]
        sizes_tok = [s // merge ** 2 for s in sizes_tower]
        if sum(sizes_tok) != tok.shape[0]:
            raise RuntimeError("token split mismatch: %s vs %d"
                               % (sizes_tok, int(tok.shape[0])))
        out = []
        for i, (a, t) in enumerate(zip(
                torch.split(vo.last_hidden_state, sizes_tower, dim=0),
                torch.split(tok, sizes_tok, dim=0))):
            rec = recs[i]
            out.append({"unit": rec["unit"], "slug": rec["slug"],
                        "n_frames": rec["n_frames"], "sha256": rec["sha256"],
                        "n_tokens_merged": sizes_tok[i],
                        "emb_tower_f16": c3._f16_list(a.mean(dim=0)),
                        "emb_tokens_f16": c3._f16_list(t.mean(dim=0))})
        return out

    records, batch, i, batch_times = [], c3.BATCH0, 0, []
    for group_key in ("full", "halfA", "halfB"):     # never mix frame counts
        grp = [u for u in units if u["unit"] == group_key]
        i = 0
        while i < len(grp):
            chunk = grp[i:i + batch]
            try:
                t0 = time.perf_counter()
                records.extend(forward_batch(chunk))
                batch_times.append({"group": group_key, "batch": batch,
                                    "n": len(chunk),
                                    "s": round(time.perf_counter() - t0, 2)})
                i += len(chunk)
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                if batch == 1:
                    raise RuntimeError("CUDA OOM at batch=1 — fail loud")
                batch //= 2
                log("OOM -> batch halved to %d" % batch)
            finally:
                torch.cuda.empty_cache()
    return records, batch, batch_times


# ------------------------------------------------------------- statistics ---
def binom_tail_ge(k, n, p):
    """P(X >= k), X ~ Bin(n, p). Exact floats."""
    return sum(math.comb(n, i) * p ** i * (1.0 - p) ** (n - i)
               for i in range(k, n + 1))


def centroid(X):
    c = X.mean(axis=0)
    return c / max(np.linalg.norm(c), 1e-12)


def explicit_scores(real_c, synth_c, Xev):
    """score = cos(x, real_c) - cos(x, synth_c); >0 => real-side."""
    Xev = c3.l2nrows(Xev)
    return Xev @ real_c - Xev @ synth_c


def participation_ratio(X):
    """PR = (sum s^2)^2 / sum s^4 over singular values of centered X."""
    Xc = X - X.mean(axis=0)
    s = np.linalg.svd(Xc, compute_uv=False)
    lam = s ** 2
    return float(lam.sum() ** 2 / np.maximum((lam ** 2).sum(), 1e-12))


def pixel_half_features(units_meta):
    """Informational baseline: per half, temporal mean + std of grayscale
    16x16 frames, concat 512-d. Row order: halfA then halfB, per slug."""
    def feats(paths):
        out = []
        for p in paths:
            data = open(os.path.join(LAB, p), "rb").read()
            n = len(data) // FS
            frames = []
            for i in range(n):
                f = np.frombuffer(data[i * FS:(i + 1) * FS], dtype=np.uint8)
                g = f.reshape(c3.H, c3.W, 3).mean(axis=2)
                frames.append(g.reshape(16, 16, 16, 16).mean(axis=(1, 3)))
            st = np.stack(frames)
            out.append(np.concatenate([st.mean(axis=0).ravel(),
                                       st.std(axis=0).ravel()]) / 255.0)
        return np.array(out)

    slugs = [m["slug"] for m in units_meta if m["unit"] == "full"]
    A = feats(["%s__a.rgb" % os.path.join("data", "c3b_halves", s) for s in slugs])
    B = feats(["%s__b.rgb" % os.path.join("data", "c3b_halves", s) for s in slugs])
    return slugs, A, B


# ----------------------------------------------------------------- probes ---
def score_all(records, slugs):
    R = {(r["unit"], r["slug"]): r for r in records}
    X_full = np.array([[float(v) for v in R[("full", s)]["emb_tokens_f16"]]
                       for s in slugs], dtype=np.float64)
    X_A = np.array([[float(v) for v in R[("halfA", s)]["emb_tokens_f16"]]
                    for s in slugs], dtype=np.float64)
    X_B = np.array([[float(v) for v in R[("halfB", s)]["emb_tokens_f16"]]
                    for s in slugs], dtype=np.float64)

    c3d = json.load(open(C3_JSON))
    cc = c3d["clips"]
    tr_synth = [r for r in cc if r["split"] == "train" and r["domain"] == "synth"]
    tr_real = [r for r in cc if r["split"] == "train" and r["domain"] == "real"]
    va_synth = [r for r in cc if r["split"] == "val" and r["domain"] == "synth"]
    va_real = [r for r in cc if r["split"] == "val" and r["domain"] == "real"]
    L = "emb_tokens_f16"
    Xtr_s = c3.l2nrows(np.array([r[L] for r in tr_synth], dtype=np.float64))
    Xtr_r = c3.l2nrows(np.array([r[L] for r in tr_real], dtype=np.float64))
    Xva_s = c3.l2nrows(np.array([r[L] for r in va_synth], dtype=np.float64))
    Xva_r = c3.l2nrows(np.array([r[L] for r in va_real], dtype=np.float64))

    # --- G1: diverse-real anchor swap, scored on C3's frozen val set ---
    synth_c = centroid(Xtr_s)
    div_real_c = centroid(c3.l2nrows(X_full))
    sc_va_r = explicit_scores(div_real_c, synth_c, Xva_r)
    sc_va_s = explicit_scores(div_real_c, synth_c, Xva_s)
    g1_auc = c3.auc_exact(sc_va_r.tolist(), sc_va_s.tolist())
    g1_acc = float(np.mean(np.concatenate(
        [sc_va_r > 0, sc_va_s <= 0]).astype(float)))
    strat = {}
    for r, s in zip(va_real + va_synth, list(sc_va_r) + list(sc_va_s)):
        g = r.get("source") or r.get("family")
        strat.setdefault(g, [0, 0])
        strat[g][0] += int((s > 0) == (r["domain"] == "real"))
        strat[g][1] += 1

    # --- G2: temporal-half identity matching (chance 1/21) ---
    An, Bn = c3.l2nrows(X_A), c3.l2nrows(X_B)
    S = An @ Bn.T
    top1 = [slugs[int(np.argmax(S[i]))] for i in range(len(slugs))]
    g2_correct = [i for i in range(len(slugs)) if top1[i] == slugs[i]]
    g2_count = len(g2_correct)
    pslugs, PA, PB = pixel_half_features(records)
    SP = c3.l2nrows(PA) @ c3.l2nrows(PB).T
    pixel_top1 = [int(np.argmax(SP[i])) for i in range(len(pslugs))]
    pixel_correct = sum(pixel_top1[i] == i for i in range(len(pslugs)))
    # largest train family ('still', n=20) = single-family anchor (checked
    # pre-fire: no family reaches 21; plan amended BEFORE stamp/commit)
    still = sorted([r for r in tr_synth if r.get("family") == "still"],
                   key=lambda r: r["idx"])
    mixed = sorted(tr_synth, key=lambda r: r["idx"])[:21]
    pr_real = participation_ratio(X_full)
    pr_single = participation_ratio(
        np.array([r[L] for r in still], dtype=np.float64))
    pr_mixed = participation_ratio(
        np.array([r[L] for r in mixed], dtype=np.float64))

    # --- G3: project the 21 on C3's frozen train axis ---
    real_c3, synth_c3 = centroid(Xtr_r), centroid(Xtr_s)
    s_new = explicit_scores(real_c3, synth_c3, X_full)
    g3_count = int((s_new > 0).sum())
    # fail-loud sanity clause: must reproduce C3's booked val 1.0
    s_val_r = explicit_scores(real_c3, synth_c3, Xva_r)
    s_val_s = explicit_scores(real_c3, synth_c3, Xva_s)
    sanity = {"val_real_real_side": int((s_val_r > 0).sum()),
              "val_real_n": len(s_val_r),
              "val_synth_real_side": int((s_val_s > 0).sum()),
              "val_synth_n": len(s_val_s)}
    sanity_ok = (sanity["val_real_real_side"] == len(s_val_r)
                 and sanity["val_synth_real_side"] == 0)
    if not sanity_ok:
        return {"verdict": "INVALID_HARNESS",
                "verdict_stage": "g3_sanity_clause", "sanity": sanity,
                "reason": "C3-axis projection does not reproduce C3's "
                          "booked val 1.0 — embedding/protocol mismatch"}

    # --- frozen verdict mapping ---
    if g2_count >= G2_SURVIVE and g3_count >= G3_GATE:
        verdict = "ANCHORING_SURVIVES"
    elif g2_count <= G2_COLLAPSE:
        verdict = "ANCHORING_DEGENERATES"
    elif g2_count >= G2_SURVIVE and g3_count <= G3_GATE - 1:
        verdict = "MIXED_TRANSFER_FAIL"
    elif g3_count >= G3_GATE:
        verdict = "MIXED_WEAK_STRUCTURE"
    else:
        verdict = "MIXED_BOTH_WEAK"

    return {
        "verdict_stage": "gated", "verdict": verdict,
        "G1_diverse_anchor_swap": {
            "auc": round(g1_auc, 4), "acc": round(g1_acc, 4),
            "gate": G1_GATE, "met": bool(g1_auc >= G1_GATE),
            "val_acc_by_source_family": {
                g: "%d/%d" % (c, n) for g, (c, n) in sorted(strat.items())},
            "role": "supporting, not verdict-carrying"},
        "G2_within_real_structure": {
            "correct": g2_count, "n": len(slugs),
            "chance": round(G2_CHANCE, 4),
            "gate_survive": G2_SURVIVE, "gate_collapse": G2_COLLAPSE,
            "binom_p_ge": "%.3e" % binom_tail_ge(g2_count, len(slugs),
                                                 G2_CHANCE),
            "binom_p_ge_collapse_band":
                "%.3e" % binom_tail_ge(G2_COLLAPSE + 1, len(slugs), G2_CHANCE),
            "mismatches": [{"clip": slugs[i], "matched": top1[i],
                            "cos": round(float(S[i, i]), 4),
                            "cos_top1": round(float(S[i].max()), 4)}
                           for i in range(len(slugs)) if top1[i] != slugs[i]],
            "pixel_baseline_correct": pixel_correct,
            "pr_real": round(pr_real, 2),
            "pr_synth_single_family_still20": round(pr_single, 2),
            "pr_synth_mixed21": round(pr_mixed, 2)},
        "G3_c3_axis_transfer": {
            "real_side": g3_count, "n": len(slugs), "gate": G3_GATE,
            "binom_p_ge": "%.3e" % binom_tail_ge(g3_count, len(slugs), 0.5),
            "scores": {s: round(float(v), 4)
                       for s, v in zip(slugs, s_new)},
            "score_stats": {"min": round(float(s_new.min()), 4),
                            "median": round(float(np.median(s_new)), 4),
                            "max": round(float(s_new.max()), 4)},
            "sanity": sanity},
        "half_tokens": {"min": int(min(r["n_tokens_merged"] for r in records
                                        if r["unit"] != "full")),
                        "max": int(max(r["n_tokens_merged"] for r in records
                                       if r["unit"] != "full"))},
    }


# ------------------------------------------------------------------- main ---
def main():
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    prereg = prereg_stamp.prereg_block(pathlib.Path(os.path.join(LAB, PLAN)))
    receipt = {"schema": "c3b-real-anchoring/1", "plan": PLAN,
               "created": time.strftime("%Y-%m-%d %H:%M:%S"),
               "prereg": prereg, "preflight": c3.preflight()}
    try:
        manifest = json.load(open(MANIFEST))
        verify_clips(manifest)
        ffmpeg_bin = manifest.get("ffmpeg", {}).get("path") or shutil.which("ffmpeg")
        if not ffmpeg_bin or not os.path.isfile(ffmpeg_bin):
            sys.exit("[c3b] FATAL: no usable ffmpeg")
        units = build_units(manifest, ffmpeg_bin)
        slugs = [u["slug"] for u in units if u["unit"] == "full"]

        # resume path: checkpoint match -> scoring only, no GPU (C4/C5 law)
        resumed = None
        if os.path.isfile(CHECKPOINT):
            try:
                d = json.load(open(CHECKPOINT))
                if len(d["records"]) == len(units) and \
                   [(r["unit"], r["slug"]) for r in d["records"]] == \
                   [(u["unit"], u["slug"]) for u in units]:
                    resumed = d
                    log("RESUME: checkpoint matches (%d records) — "
                        "scoring only, no GPU" % len(d["records"]))
            except Exception as e:  # noqa: BLE001 — unreadable = full run
                log("checkpoint unreadable (%r) — full run" % e)

        if resumed is not None:
            records = resumed["records"]
            receipt.update({"batch_final": "resumed", "peak_alloc_gib": None,
                            "visual_dtype": "checkpoint-resume",
                            "visual_type": "checkpoint-resume",
                            "ramp_receipt": "checkpoint-resume (no GPU this "
                                            "run; original receipt in "
                                            "checkpoint)"})
            if "loader_receipt" in resumed:
                receipt["loader_receipt_original"] = resumed["loader_receipt"]
        else:
            import torch
            from transformers import AutoProcessor, BitsAndBytesConfig
            try:
                from transformers import \
                    Cosmos3EdgeForConditionalGeneration as M
            except ImportError:
                from transformers.models.cosmos3_edge.\
                    modeling_cosmos3_edge import \
                    Cosmos3EdgeForConditionalGeneration as M
            import transformers
            quant = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                llm_int8_skip_modules=c3.SKIP_MODULES)
            t0 = time.time()
            model = M.from_pretrained(c3.MODEL_ID, quantization_config=quant,
                                      device_map="auto",
                                      torch_dtype=torch.bfloat16)
            model.eval()
            proc = AutoProcessor.from_pretrained(c3.MODEL_ID)
            p0 = next(model.model.visual.parameters())
            visual_dtype, visual_type = str(p0.dtype), type(p0).__name__
            if not (visual_dtype == "torch.bfloat16"
                    and visual_type == "Parameter"):
                receipt.update({"verdict": "INVALID_HARNESS",
                                "verdict_stage": "dtype_receipt",
                                "visual_dtype": visual_dtype,
                                "visual_type": visual_type,
                                "reason": "skip-tower failed"})
                json.dump(receipt, open(OUT_JSON, "w"), indent=1)
                sys.exit("[c3b] FATAL: INVALID_HARNESS (visual %s/%s)"
                         % (visual_dtype, visual_type))
            log("model loaded %.1fs, receipt %s/%s"
                % (time.time() - t0, visual_dtype, visual_type))

            rr = ramp_receipt(torch)          # INSTRUMENT-01, before measuring
            log("ramp receipt: %s" % rr)
            torch.cuda.reset_peak_memory_stats()
            records, batch_final, batch_times = extract_units(
                model, proc, units, ffmpeg_bin)
            peak = torch.cuda.max_memory_allocated() / 2 ** 30
            torch.cuda.empty_cache()
            loader_receipt = {
                "t_load_s": round(time.time() - t0, 2),
                "batch_final": batch_final, "batch0": c3.BATCH0,
                "skip_modules": c3.SKIP_MODULES,
                "visual_dtype": visual_dtype, "visual_type": visual_type,
                "versions": {"torch": torch.__version__,
                             "transformers": transformers.__version__,
                             "cuda": torch.version.cuda},
                "peak_alloc_gib": round(peak, 2),
                "ramp_receipt": rr, "batch_times": batch_times}
            # CHECKPOINT LAW: embeddings persisted BEFORE any scoring
            json.dump({"records": records, "loader_receipt": loader_receipt},
                      open(CHECKPOINT, "w"))
            log("checkpoint: embeddings persisted (metric bugs never lose "
                "GPU work)")
            receipt["loader_receipt"] = loader_receipt

        scored = score_all(records, slugs)
        receipt.update(scored)
        if "clips" not in receipt:
            receipt["records"] = records
    except SystemExit:
        raise
    except Exception:
        receipt.update({"verdict": "INVALID_HARNESS",
                        "verdict_stage": "exception",
                        "traceback_tail": traceback.format_exc()[-1500:]})
    receipt["done"] = True
    json.dump(receipt, open(OUT_JSON, "w"), indent=1)
    log("DONE verdict=%s" % receipt.get("verdict"))


if __name__ == "__main__":
    main()
