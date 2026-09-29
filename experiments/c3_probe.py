#!/usr/bin/env python3
"""C3 latent probe — does K3c's domain-anchoring replicate in Cosmos3-Edge?

Pre-registered: proposals/runs/C3-latent-probe-plan.md (frozen; read it first).
Question: K3c found V-JEPA state z-codes are domain-anchored (synth val
4.26-4.71 vs lavfi 1.50-1.80 on floor 2.85). Does the domain split survive
into Cosmos3-Edge vision latents (second encoder family)?

Protocol (frozen in plan):
  - loader: PROVEN C2 a5b skip-tower recipe — NF4 LM, bf16 tower/projector,
    llm_int8_skip_modules short+qualified; fail-loud dtype receipt: first
    visual param must be bf16 AND type Parameter, else INVALID_HARNESS.
  - decode: every .rgb clip -> 16 PNG frames via ffmpeg list-form subprocess.
  - extract: model.model.visual + model.model.projector (inner path,
    modeling_cosmos3_edge.py:965-967 mirrored), mean-pooled per clip.
    Layer B (post-projector tokens) = primary; Layer A (tower features)
    = secondary informational.
  - probe: nearest-centroid cosine classifier (primary) + linear logistic
    (secondary) fit on 192 train clips; FROZEN GATE on 64 val clips:
    val AUC >= 0.90 (chance 0.50) on layer B nearest-centroid.
    ANCHORING_REPLICATED >= 0.90 / PARTIAL [0.70,0.90) / NO_ANCHORING < 0.70.
  - guard preflight (wrapper AND inner): free VRAM >= 1024 MiB, temp <= 80C.
  - batches of 4 clips, OOM auto-halving 4->2->1, fail loud at 1.
  - subprocess list-form ONLY (house law). No git, no generation, no LM run.

Fire: /home/eileen/venvs/elephant-gpu/bin/python experiments/c3_probe.py
Writes: results/c3_probe.json (+ c3_probe.log via shell redirect if wanted).
"""
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(LAB, "data", "c3")
MANIFEST = os.path.join(DATA, "manifest.json")
RESULTS = os.path.join(LAB, "results")
OUT_JSON = os.path.join(RESULTS, "c3_probe.json")
PLAN = "proposals/runs/C3-latent-probe-plan.md"

MODEL_ID = "nvidia/Cosmos3-Edge"
SKIP_MODULES = ["visual", "projector", "model.visual", "model.projector"]
BATCH0 = 4                     # initial clip batch; halve on CUDA OOM
FRAMES, W, H = 16, 256, 256    # frozen data geometry
GATE_AUC = 0.90                # FROZEN primary gate (layer B, centroid, val)
SEED = 20260929                # data-plan pin; linear-probe init
NVIDIA_SMI = "/usr/lib/wsl/lib/nvidia-smi"


def log(msg):
    print("[c3_probe %s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


# ----------------------------------------------------------------- guard ---
def preflight():
    if not os.path.isfile(NVIDIA_SMI):
        sys.exit("[c3_probe] FATAL: no nvidia-smi at %s" % NVIDIA_SMI)
    r = subprocess.run([NVIDIA_SMI, "--query-gpu=memory.free,temperature.gpu",
                        "--format=csv,noheader,nounits"],
                       capture_output=True, text=True)
    free, temp = [int(x.strip()) for x in r.stdout.strip().split(",")]
    assert free >= 1024, "guard: free VRAM %dMiB < 1024" % free
    assert temp <= 80, "guard: temp %dC > 80" % temp
    return {"free_mib": free, "temp_c": temp}


# ------------------------------------------------------------------ data ---
def verify_clips(manifest):
    """Byte-count + sha256 every clip against the manifest. Fail loud."""
    t0 = time.time()
    for rec in manifest["clips"]:
        p = os.path.join(LAB, rec["path"])
        expect_bytes = rec["bytes"]
        if os.path.getsize(p) != expect_bytes:
            sys.exit("[c3_probe] FATAL: %s size != %d" % (rec["path"],
                                                          expect_bytes))
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest() != rec["sha256"]:
            sys.exit("[c3_probe] FATAL: %s sha256 mismatch vs manifest"
                     % rec["path"])
    log("verified %d clips vs manifest (%.1fs)"
        % (len(manifest["clips"]), time.time() - t0))


def decode_clip_ffmpeg(clip_path, ffmpeg_bin, tmpdir):
    """rawvideo .rgb -> exactly FRAMES RGB PIL frames, ffmpeg list-form."""
    out_pat = os.path.join(tmpdir, "frame_%06d.png")
    r = subprocess.run(
        [ffmpeg_bin, "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
         "-i", clip_path,
         "-f", "image2pipe", "-vcodec", "png", out_pat],
        capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("[c3_probe] FATAL: ffmpeg decode %s rc=%d stderr=%s"
                 % (clip_path, r.returncode, r.stderr[-300:]))
    files = sorted(f for f in os.listdir(tmpdir) if f.endswith(".png"))
    if len(files) != FRAMES:
        sys.exit("[c3_probe] FATAL: %s -> %d frames (want %d)"
                 % (clip_path, len(files), FRAMES))
    from PIL import Image
    frames = []
    for f in files:
        frames.append(Image.open(os.path.join(tmpdir, f)).convert("RGB"))
        os.remove(os.path.join(tmpdir, f))   # scratch only, keep tmpdir small
    return frames


# ------------------------------------------------------------ statistics ---
def auc_exact(pos, neg):
    """Mann-Whitney AUC (tie = 0.5 credit). Exact, deterministic."""
    n_win = 0.0
    for p in pos:
        for q in neg:
            n_win += 1.0 if p > q else (0.5 if p == q else 0.0)
    return n_win / (len(pos) * len(neg))


def binom_tail_ge(k, n):
    """P(X >= k) for X ~ Bin(n, 0.5). Exact."""
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2.0 ** n


def l2nrows(mat):
    import numpy as np
    mat = np.asarray(mat, dtype=np.float64)
    return mat / np.maximum(
        np.linalg.norm(mat, axis=1, keepdims=True), 1e-12)


def nearest_centroid_scores(Xtr, ytr, Xev):
    """cos(x, synth_centroid) - cos(x, real_centroid); >0 => synth."""
    import numpy as np
    Xtr, Xev = l2nrows(Xtr), l2nrows(Xev)
    cents = {}
    for dom in (0, 1):                       # 0=synth, 1=real
        c = Xtr[ytr == dom].mean(axis=0)
        cents[dom] = c / max(np.linalg.norm(c), 1e-12)
    return (Xev @ cents[0] - Xev @ cents[1]).tolist()


def linear_probe_scores(Xtr, ytr, Xev):
    """Full-batch logistic regression, Adam lr 0.01, wd 1e-3, 1000 steps,
    CPU float32, seed SEED. Secondary confirmation classifier."""
    import numpy as np
    import torch
    torch.manual_seed(SEED)
    Xt = torch.tensor(l2nrows(Xtr), dtype=torch.float32)
    yt = torch.tensor(ytr, dtype=torch.float32)
    Xv = torch.tensor(l2nrows(Xev), dtype=torch.float32)
    d = Xt.shape[1]
    w = torch.zeros(d, requires_grad=True)
    b = torch.zeros(1, requires_grad=True)
    opt = torch.optim.Adam([w, b], lr=0.01, weight_decay=1e-3)
    for _ in range(1000):
        logits = Xt @ w + b
        loss = torch.nn.functional.binary_cross_entropy_with_logits(
            logits, yt) + 1e-4 * w.pow(2).sum()
        opt.zero_grad()
        loss.backward()
        opt.step()
    with torch.no_grad():
        return (Xv @ w + b).tolist(), float(loss)


# --------------------------------------------------------------- verdict ---
def verdict_of(primary_val_auc):
    if primary_val_auc >= GATE_AUC:
        return "ANCHORING_REPLICATED"
    if primary_val_auc >= 0.70:
        return "PARTIAL"
    return "NO_ANCHORING"


# ------------------------------------------------------------- inner run ---
def extract_all(model, proc, clips, ffmpeg_bin):
    """Batched vision-feature extraction. Returns per-clip dict list."""
    import torch
    visual = model.model.visual           # inner path (C2 a5a lesson)
    projector = model.model.projector
    merge = int(getattr(projector, "spatial_merge_size", 2) or 2)
    dtype = next(visual.parameters()).dtype
    device = next(visual.parameters()).device

    def forward_batch(recs):
        from PIL import Image
        batches_frames = []
        with tempfile.TemporaryDirectory(prefix="c3_frames_") as td:
            for rec in recs:
                batches_frames.append(
                    decode_clip_ffmpeg(os.path.join(LAB, rec["path"]),
                                       ffmpeg_bin, td))
        try:
            inputs = proc(videos=batches_frames, return_tensors="pt")
        except Exception as e:
            log("processor videos-only failed (%s); text-placeholder "
                "fallback (mechanical, logged)" % type(e).__name__)
            inputs = proc(text=[""] * len(batches_frames),
                          videos=batches_frames, return_tensors="pt")
        key_px = next((k for k in ("pixel_values_videos", "pixel_values")
                       if k in inputs), None)
        key_grid = next((k for k in ("video_grid_thw", "image_grid_thw")
                         if k in inputs), None)
        if key_px is None or key_grid is None:
            raise RuntimeError("processor keys missing (px=%s grid=%s); "
                               "available: %s"
                               % (key_px, key_grid, list(inputs.keys())))
        px = inputs[key_px].to(device).type(dtype)
        grid = inputs[key_grid].to(device)
        with torch.no_grad():
            vo = visual(px, grid_thw=grid, return_dict=True)
            tok = projector(vo.last_hidden_state)
        sizes_tower = [int(v) for v in grid.prod(-1).tolist()]
        sizes_tok = [s // merge ** 2 for s in sizes_tower]
        if sum(sizes_tower) != vo.last_hidden_state.shape[0] or \
           sum(sizes_tok) != tok.shape[0]:
            raise RuntimeError("token split mismatch: tower %s vs %d, "
                               "tok %s vs %d" % (
                                   sizes_tower,
                                   int(vo.last_hidden_state.shape[0]),
                                   sizes_tok, int(tok.shape[0])))
        out = []
        for i, (a, t) in enumerate(zip(
                torch.split(vo.last_hidden_state, sizes_tower, dim=0),
                torch.split(tok, sizes_tok, dim=0))):
            rec = recs[i]
            out.append({
                "path": rec["path"], "domain": rec["domain"],
                "split": rec["split"], "idx": rec["idx"],
                "family": rec.get("family"),
                "source": rec.get("source"),
                "sha256": rec["sha256"],
                "n_tokens_tower": sizes_tower[i],
                "n_tokens_merged": sizes_tok[i],
                "emb_tower_f16": _f16_list(a.mean(dim=0)),
                "emb_tokens_f16": _f16_list(t.mean(dim=0)),
            })
        return out

    records, batch, i = [], BATCH0, 0
    while i < len(clips):
        chunk = clips[i:i + batch]
        try:
            records.extend(forward_batch(chunk))
            i += len(chunk)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            if batch == 1:
                raise RuntimeError("CUDA OOM at batch=1 — fail loud")
            batch //= 2
            log("OOM -> batch halved to %d" % batch)
        finally:
            torch.cuda.empty_cache()
    return records, batch


def _f16_list(vec):
    import numpy as np
    return np.asarray(vec.float().cpu().numpy(),
                      dtype=np.float16).tolist()


def score_layer(records, layer_key):
    """layer_key: 'emb_tokens_f16' (B, primary) or 'emb_tower_f16' (A)."""
    import numpy as np
    tr = [r for r in records if r["split"] == "train"]
    va = [r for r in records if r["split"] == "val"]
    Xtr = np.array([r[layer_key] for r in tr], dtype=np.float64)
    ytr = np.array([0 if r["domain"] == "synth" else 1 for r in tr])
    Xva = np.array([r[layer_key] for r in va], dtype=np.float64)
    yva = np.array([0 if r["domain"] == "synth" else 1 for r in va])

    res = {}
    for name, fn in (("nearest_centroid", None),
                     ("linear_logistic", None)):
        if name == "nearest_centroid":
            s_tr = nearest_centroid_scores(Xtr, ytr, Xtr)
            s_va = nearest_centroid_scores(Xtr, ytr, Xva)
            extra = {}
        else:
            s_tr, final_loss = linear_probe_scores(Xtr, ytr, Xtr)
            s_va, _ = linear_probe_scores(Xtr, ytr, Xva)
            extra = {"final_train_loss": round(final_loss, 6)}
        auc_tr = auc_exact([s for s, y in zip(s_tr, ytr) if y == 0],
                           [s for s, y in zip(s_tr, ytr) if y == 1])
        auc_va = auc_exact([s for s, y in zip(s_va, yva) if y == 0],
                           [s for s, y in zip(s_va, yva) if y == 1])
        pred = [0 if s > 0 else 1 for s in s_va]
        acc = sum(int(p == y) for p, y in zip(pred, yva)) / len(yva)
        k = sum(int(p == y) for p, y in zip(pred, yva))
        strat = {}
        for r, p, y in zip(va, pred, yva):
            g = r["source"] or r["family"]
            strat.setdefault(g, [0, 0])
            strat[g][0] += int(p == y)
            strat[g][1] += 1
        res[name] = {
            "train_auc": round(auc_tr, 4), "val_auc": round(auc_va, 4),
            "val_acc": round(acc, 4), "val_correct": k, "val_n": len(yva),
            "val_acc_binom_p_ge": ("%.3e" % binom_tail_ge(k, len(yva))
                                   if k >= len(yva) / 2 else ">0.5"),
            "val_acc_by_source_family": {
                g: "%d/%d" % (c, n) for g, (c, n) in sorted(strat.items())},
            **extra,
        }
    return res, res["nearest_centroid"]["val_auc"]


def inner():
    import torch
    import transformers
    from transformers import AutoProcessor, BitsAndBytesConfig
    try:
        from transformers import Cosmos3EdgeForConditionalGeneration as M
    except ImportError:
        from transformers.models.cosmos3_edge.modeling_cosmos3_edge import \
            Cosmos3EdgeForConditionalGeneration as M

    with open(MANIFEST) as f:
        manifest = json.load(f)
    ffmpeg_bin = manifest.get("ffmpeg", {}).get("path") or \
        shutil.which("ffmpeg")
    if not ffmpeg_bin:
        sys.exit("[c3_probe] FATAL: no ffmpeg in manifest or PATH")
    verify_clips(manifest)

    quant = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        llm_int8_skip_modules=SKIP_MODULES)
    t0 = time.time()
    model = M.from_pretrained(MODEL_ID, quantization_config=quant,
                              device_map="auto",
                              torch_dtype=torch.bfloat16)
    model.eval()
    t_load = time.time() - t0
    proc = AutoProcessor.from_pretrained(MODEL_ID)

    # fail-loud dtype receipt — skip must have taken (C2 a5b gate)
    p0 = next(model.model.visual.parameters())
    visual_dtype, visual_type = str(p0.dtype), type(p0).__name__
    if not (visual_dtype == "torch.bfloat16" and visual_type == "Parameter"):
        return {"verdict": "INVALID_HARNESS",
                "verdict_stage": "dtype_receipt",
                "visual_dtype": visual_dtype, "visual_type": visual_type,
                "reason": "skip-tower failed: visual not bf16 Parameter"}

    torch.cuda.reset_peak_memory_stats()
    records, batch_final = extract_all(model, proc, manifest["clips"],
                                       ffmpeg_bin)
    peak_gib = torch.cuda.max_memory_allocated() / 2 ** 30
    torch.cuda.empty_cache()

    metrics_b, primary_auc = score_layer(records, "emb_tokens_f16")
    metrics_a, _ = score_layer(records, "emb_tower_f16")

    toks = [r["n_tokens_merged"] for r in records]
    return {
        "t_load_s": round(t_load, 2), "batch_final": batch_final,
        "batch0": BATCH0, "skip_modules": SKIP_MODULES,
        "visual_dtype": visual_dtype, "visual_type": visual_type,
        "versions": {"torch": torch.__version__,
                     "transformers": transformers.__version__,
                     "cuda": torch.version.cuda},
        "n_clips": len(records),
        "tokens_per_clip": {"min": min(toks), "max": max(toks)},
        "peak_alloc_gib": round(peak_gib, 2),
        "gate": {"metric": "nearest_centroid val AUC, layer B "
                           "(post-projector, mean-pooled)",
                 "threshold": GATE_AUC, "chance": 0.5},
        "metrics_layer_B_primary": metrics_b,
        "metrics_layer_A_secondary": metrics_a,
        "verdict_stage": "gated",
        "verdict": verdict_of(primary_auc),
        "clips": records,
    }


def main():
    os.makedirs(RESULTS, exist_ok=True)
    if "--inner" in sys.argv:
        try:
            res = {"schema": "c3-latent-probe/1", "plan": PLAN,
                   "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "preflight": preflight(), **inner(), "done": True}
        except Exception:
            res = {"schema": "c3-latent-probe/1", "plan": PLAN,
                   "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "verdict": "INVALID_HARNESS",
                   "verdict_stage": "exception",
                   "traceback_tail": traceback.format_exc()[-1500:],
                   "done": True}
        with open(OUT_JSON, "w") as f:
            json.dump(res, f, indent=1)
        log("INNER_DONE verdict=%s" % res.get("verdict"))
        return
    pf = preflight()
    log("preflight %s" % pf)
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--inner"],
                       capture_output=True, text=True)
    log("guard rc=%d" % r.returncode)
    if r.stderr:
        log("stderr tail: %s" % r.stderr[-400:])
    try:
        with open(OUT_JSON) as f:
            d = json.load(f)
    except Exception as e:
        log("no results json: %s" % e)
        return
    log("visual=%s/%s verdict=%s (stage %s)"
        % (d.get("visual_dtype"), d.get("visual_type"), d.get("verdict"),
           d.get("verdict_stage")))
    mb = d.get("metrics_layer_B_primary", {})
    for clf, m in mb.items():
        log("  B/%s: train_auc=%s val_auc=%s val_acc=%s (p=%s)"
            % (clf, m.get("train_auc"), m.get("val_auc"),
               m.get("val_acc"), m.get("val_acc_binom_p_ge")))
    log("gate: %s" % d.get("gate"))
    log("DONE")


if __name__ == "__main__":
    main()
