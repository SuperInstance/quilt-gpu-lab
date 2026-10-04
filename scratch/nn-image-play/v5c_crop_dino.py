#!/usr/bin/env python3
"""W5-C CROP-DINO RE-SCORE — center-crop DINOv2 embedding vs full-frame, over the
stored v5a board (0 new generation; pure re-embedding of 78 archived artifacts).

DESIGN FROZEN BEFORE RUN
  Crop semantics: center box crop = central s-fraction of width AND height,
  applied SYMMETRICALLY to the artifact AND its subject reference image, then
  the standard facebook/dinov2-base AutoImageProcessor (resize-256 + cc224),
  CLS embedding, cosine similarity — identical to v5a except for the pre-crop.
  Scales: s in {0.5, 0.6, 0.7, 0.8, 0.9} + s=1.0 (full-frame reproduction).
  clip / ijepa remain FULL-FRAME (stored board values); only dino is re-scored
  per crop scale. majority/min semantics mix crop-dino with full-frame
  clip/ijepa — noted, that is the point (upgrade the dino leg only).
  Retention = fraction of the 67 clip@0.80-accepted non-morphs kept (v5b def).
  Baselines (v5b, full-frame): dino-primary@0.60 -> 4/4 morph rejects,
  retention 0.6269; min@0.80 -> 4/4, retention 0.194; clip-alone 2/4, 1.0.
  Morphs (name-prefix, v5b semantics; is_morph flag in board is known-buggy):
  xcasey_lucedges_s101/s102, xlucineer_caseyedges_s101/s102 (all vs lucineer
  ref). Full-frame morph-max dino = 0.503.

PRE-REGISTERED CLAIMS (frozen here before execution; honest FAIL allowed)
  H3 (sanity gate — must hold for any other claim to count):
     full-frame recompute (s=1.0, same model+processor) reproduces board dino
     with Spearman >= 0.99 AND max |delta| <= 0.02.
  H1 (primary): EXISTS s in {0.5,0.6,0.7,0.8,0.9} and threshold t in
     {0.50,0.55,...,0.90} such that dino-primary on crop-dino(s) keeps 4/4
     morph rejects AND retention_of_legacy > 0.6269 (beats full-frame knob).
  H2 (separation): EXISTS s in {0.5,...,0.9} with
     gap(s) = median(dino of 67 legacy non-morphs) - max(dino of 4 morphs)
     strictly > gap(1.0) (threshold-free separation improvement).
  H4 (min-gate rescue): EXISTS (s, t) such that min-gate
     (clip_ff AND ijepa_ff AND dino_crop(s) >= t) keeps 4/4 morph rejects AND
     retention >= 0.60 (vs 0.194 full-frame min@0.80).

GPU PROTOCOL: DEV = cuda if available else cpu (never hardcoded); model loaded
ONCE; batch=16; 3 warmup batches first with ramp receipt logged (INSTRUMENT-01:
first-batch latency after idle is a single-draw stat, correctness unaffected);
del model + torch.cuda.empty_cache() at end. Checkpoint embeddings to
v5c_crop_dino.json after EACH scale (4dp), crash-resumable: scales already in
the checkpoint are skipped, and ALL scores/claims are computed from the
checkpointed (rounded) embeddings so a resumed run is bit-identical.
"""
import json, math, pathlib, time
import torch
from PIL import Image
from transformers import AutoModel, AutoImageProcessor

HERE = pathlib.Path(__file__).parent
PNG = pathlib.Path("/home/eileen/projects/dicebear-quilt/quilt/play-2026-10-02/png")
CKPT = HERE / "v5c_crop_dino.json"
SCALES = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]          # 1.0 = full-frame reproduction
THRESH = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
BATCH = 16

def log(*a): print(*a, flush=True)

board = json.loads((HERE / "v5a_board.json").read_text())
arts = board["artifacts"]
MORPH_PREFIX = ("xcasey", "xlucineer")
morphs = [a for a in arts if a["name"].startswith(MORPH_PREFIX)]
non = [a for a in arts if not a["name"].startswith(MORPH_PREFIX)]
LEGACY_FLOOR = 0.80
legacy = [a for a in non if a["clip"] >= LEGACY_FLOOR]
n_legacy = len(legacy)
assert len(arts) == 78 and len(morphs) == 4, (len(arts), len(morphs))
log(f"pool: {len(arts)} artifacts | morphs {len(morphs)} | legacy(clip@0.80) {n_legacy}")

DEV = "cuda" if torch.cuda.is_available() else "cpu"
log(f"device: {DEV}")

def center_crop(img: Image.Image, s: float) -> Image.Image:
    if s >= 1.0:
        return img
    w, h = img.size
    cw, ch = int(round(w * s)), int(round(h * s))
    left, top = (w - cw) // 2, (h - ch) // 2
    return img.crop((left, top, left + cw, top + ch))

# ---------- checkpoint (resumable) ----------
ckpt = {"experiment": "w5c-crop-dino", "claims_frozen_in_header": True,
        "device": DEV, "model": "facebook/dinov2-base", "batch": BATCH,
        "scales": SCALES, "thresh": THRESH, "ramp_receipt": None,
        "embeddings": {}}
if CKPT.exists():
    prev = json.loads(CKPT.read_text())
    if prev.get("experiment") == "w5c-crop-dino":
        ckpt = prev
        log(f"resume: scales already embedded: {sorted(ckpt['embeddings'], key=float)}")

todo = [s for s in SCALES if str(s) not in ckpt["embeddings"]]

# ---------- embed ----------
if todo:
    model = AutoModel.from_pretrained("facebook/dinov2-base", local_files_only=True).to(DEV).eval()
    proc = AutoImageProcessor.from_pretrained("facebook/dinov2-base", local_files_only=True)

    @torch.no_grad()
    def batch_embed(images):
        inp = proc(images=images, return_tensors="pt").to(DEV)
        cls = model(**inp).last_hidden_state[:, 0]
        return torch.nn.functional.normalize(cls, dim=-1).cpu()

    if DEV == "cuda":
        # INSTRUMENT-01 ramp receipt: 3 warmup batches, log first-batch latency
        dummy = [Image.new("RGB", (224, 224))] * BATCH
        t0 = time.time(); batch_embed(dummy); torch.cuda.synchronize()
        first = time.time() - t0
        for _ in range(2): batch_embed(dummy)
        torch.cuda.synchronize()
        ramp = {"warmup_batches": 3, "first_batch_s": round(first, 3),
                "note": "first-batch latency is a single-draw ramp stat (INSTRUMENT-01); correctness unaffected"}
        ckpt["ramp_receipt"] = ramp
        log(f"ramp receipt: {json.dumps(ramp)}")

    refs = sorted({a["subject"] for a in arts})
    for s in todo:
        embs, t0 = {}, time.time()
        rvec = {}
        for r in refs:
            e = batch_embed([center_crop(Image.open(str(PNG / f"{r}.png")).convert("RGB"), s)])
            rvec[r] = [round(float(x), 4) for x in e[0]]
        embs["__refs__"] = rvec
        paths = [a["path"] for a in arts]
        for i in range(0, len(paths), BATCH):
            chunk = paths[i:i + BATCH]
            vecs = batch_embed([center_crop(Image.open(p).convert("RGB"), s) for p in chunk])
            for p, v in zip(chunk, vecs):
                embs[p] = [round(float(x), 4) for x in v]
        ckpt["embeddings"][str(s)] = embs
        CKPT.write_text(json.dumps(ckpt))     # checkpoint AFTER each scale
        log(f"scale {s}: embedded {len(embs)-1} artifacts + {len(refs)} refs in {time.time()-t0:.1f}s (checkpointed)")
    del model, proc
    if DEV == "cuda":
        torch.cuda.empty_cache()
        log("model freed, cuda cache emptied")

# ---------- scores from checkpointed (rounded) embeddings ----------
def cos(a, b):
    num = sum(x * y for x, y in zip(a, b))
    return num / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))

def scores_for(s):
    embs = ckpt["embeddings"][str(s)]
    refs = embs["__refs__"]
    out = {}
    for a in arts:
        out[a["name"]] = round(cos(embs[a["path"]], refs[a["subject"]]), 4)
    return out

all_scores = {s: scores_for(s) for s in SCALES}

# H3 sanity: full-frame reproduction vs board
d_ff = all_scores[1.0]
pairs = [(d_ff[a["name"]], a["dino"]) for a in arts]
maxd = max(abs(x - y) for x, y in pairs)
def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]: j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1): r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs); mu = (n + 1) / 2
    num = sum((a - mu) * (b - mu) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mu) ** 2 for a in rx) * sum((b - mu) ** 2 for b in ry))
    return num / den if den else 0.0
sp = round(spearman([p[0] for p in pairs], [p[1] for p in pairs]), 4)
h3_pass = sp >= 0.99 and maxd <= 0.02
log(f"H3 reproduction: spearman {sp} max|d| {maxd:.4f} -> {'PASS' if h3_pass else 'FAIL'}")

# ---------- v5b semantics scan per scale ----------
def evaluate(scores, pred):
    kept = [a for a in non if pred(a)]
    kept_legacy = [a for a in kept if a["clip"] >= LEGACY_FLOOR]
    rej = [m["name"] for m in morphs if not pred(m)]
    return {"morph_rejects": f"{len(rej)}/4", "rejected_morphs": rej,
            "nonmorph_accepts": len(kept),
            "retention_of_legacy": round(len(kept_legacy) / max(1, n_legacy), 4)}

J = ("clip", "dino", "ijepa")
scale_tables = {}
for s in SCALES:
    sc = all_scores[s]
    rows = []
    for t in THRESH:
        d = lambda a, t=t: sc[a["name"]] >= t
        rows.append({"floor": t, "semantics": "dino-primary",
                     **evaluate(sc, d)})
        # majority / min: clip+ijepa full-frame (board), dino from crop
        maj = lambda a, t=t: sum([a["clip"] >= t, sc[a["name"]] >= t, a["ijepa"] >= t]) > 1.5
        mn = lambda a, t=t: a["clip"] >= t and sc[a["name"]] >= t and a["ijepa"] >= t
        rows.append({"floor": t, "semantics": "majority", **evaluate(sc, maj)})
        rows.append({"floor": t, "semantics": "min", **evaluate(sc, mn)})
    mm = max(sc[m["name"]] for m in morphs)
    best_dp = max((r for r in rows if r["semantics"] == "dino-primary"),
                  key=lambda r: (r["morph_rejects"] == "4/4", r["retention_of_legacy"]))
    best_min = max((r for r in rows if r["semantics"] == "min"),
                   key=lambda r: (r["morph_rejects"] == "4/4", r["retention_of_legacy"]))
    gap = round(sorted(sc[a["name"]] for a in legacy)[len(legacy) // 2] - mm, 4)
    scale_tables[str(s)] = {"morph_max_dino": mm, "legacy_median_dino":
                            sorted(sc[a["name"]] for a in legacy)[len(legacy) // 2],
                            "gap_median_legacy_minus_morphmax": gap,
                            "best_dino_primary": best_dp, "best_min": best_min}

ff = scale_tables["1.0"]

# ---------- claims ----------
crops = [0.5, 0.6, 0.7, 0.8, 0.9]
h1_hits = [{"scale": s, **{k: v for k, v in scale_tables[str(s)]["best_dino_primary"].items()
            if k in ("floor", "morph_rejects", "retention_of_legacy")}}
           for s in crops
           if any(r["semantics"] == "dino-primary" and r["morph_rejects"] == "4/4"
                  and r["retention_of_legacy"] > 0.6269 for r in
                  [{"semantics": "dino-primary", **evaluate(all_scores[s],
                    lambda a, t=t: all_scores[s][a["name"]] >= t)} for t in THRESH])]
h1_pass = len(h1_hits) > 0

gap_ff = ff["gap_median_legacy_minus_morphmax"]
h2_hits = [{"scale": s, "gap": scale_tables[str(s)]["gap_median_legacy_minus_morphmax"]}
           for s in crops if scale_tables[str(s)]["gap_median_legacy_minus_morphmax"] > gap_ff]
h2_pass = len(h2_hits) > 0

h4_hits = [{"scale": s, **{k: v for k, v in scale_tables[str(s)]["best_min"].items()
           if k in ("floor", "morph_rejects", "retention_of_legacy")}}
           for s in crops
           if scale_tables[str(s)]["best_min"]["morph_rejects"] == "4/4"
           and scale_tables[str(s)]["best_min"]["retention_of_legacy"] >= 0.60]
h4_pass = len(h4_hits) > 0

claims = {
  "H3": {"claim": "full-frame recompute reproduces board dino (spearman>=0.99, max|d|<=0.02)",
         "spearman": sp, "max_abs_delta": round(maxd, 4), "pass": h3_pass},
  "H1": {"claim": "EXISTS s in {0.5..0.9}, t in grid: crop-dino-primary -> 4/4 morph rejects AND retention > 0.6269",
         "baseline_fullframe": {"floor": 0.60, "morph_rejects": "4/4", "retention": 0.6269},
         "hits": h1_hits, "pass": h1_pass},
  "H2": {"claim": "EXISTS s: gap(median legacy dino - morph-max dino) > full-frame gap",
         "gap_fullframe": gap_ff, "hits": h2_hits, "pass": h2_pass},
  "H4": {"claim": "EXISTS (s,t): min-gate(clip_ff,ijepa_ff,dino_crop) -> 4/4 AND retention >= 0.60",
         "baseline_fullframe_min80": {"morph_rejects": "4/4", "retention": 0.194},
         "hits": h4_hits, "pass": h4_pass},
}

out = {k: ckpt[k] for k in ("experiment", "claims_frozen_in_header", "device", "model",
                            "batch", "scales", "thresh", "ramp_receipt")}
out.update({
  "n": len(arts), "morphs": len(morphs), "nonmorphs": len(non), "legacy_accepts": n_legacy,
  "crop_semantics": "symmetric center box (s x width, s x height) on artifact AND subject ref, then standard dinov2 processor",
  "clip_ijepa": "full-frame (stored v5a board)",
  "morphs_by_name": [m["name"] for m in morphs],
  "fullframe_reproduction": {"spearman": sp, "max_abs_delta": round(maxd, 4)},
  "baseline_v5b": {"dino_primary_60": {"morph_rejects": "4/4", "retention": 0.6269},
                   "min_80": {"morph_rejects": "4/4", "retention": 0.194}},
  "scale_tables": scale_tables,
  "claims": claims,
  "scores": {str(s): all_scores[s] for s in SCALES},
  "embeddings": ckpt["embeddings"],
})
CKPT.write_text(json.dumps(out))
log("CLAIMS " + json.dumps({k: v["pass"] for k, v in claims.items()}))
log(f"{'scale':>6} {'morphmax':>8} {'gap':>7}  best-dino-primary(floor,morphs,ret)      best-min(floor,morphs,ret)")
for s in SCALES:
    t = scale_tables[str(s)]
    bd, bm = t["best_dino_primary"], t["best_min"]
    log(f"{s:>6} {t['morph_max_dino']:>8} {t['gap_median_legacy_minus_morphmax']:>7}  "
        f"dp@{bd['floor']:.2f} {bd['morph_rejects']} ret {bd['retention_of_legacy']:.4f}   "
        f"min@{bm['floor']:.2f} {bm['morph_rejects']} ret {bm['retention_of_legacy']:.4f}")
if h1_hits:
    best = max(h1_hits, key=lambda h: h["retention_of_legacy"])
    log(f"H1 best: scale {best['scale']} floor {best['floor']} retention {best['retention_of_legacy']}")
