#!/usr/bin/env python3
"""V4 E1 — judge axis: CLIP vs DINOv2 identity agreement over ALL existing artifacts."""
import json, pathlib, torch
DEV = "cuda" if torch.cuda.is_available() else "cpu"
from transformers import CLIPModel, CLIPProcessor, AutoModel, AutoImageProcessor
from PIL import Image

HERE = pathlib.Path(__file__).parent
PNG = pathlib.Path("/home/eileen/projects/dicebear-quilt/quilt/play-2026-10-02/png")
def log(*a): print(*a, flush=True)

def subject_of(p, stem):
    for s in ("lucineer", "casey", "jev", "mmx"):
        if stem.startswith(s): return s
    return "lucineer"  # v1/v2 were all lucineer

artifacts = []
for sub in ("gate_loop", "gate_loop/v2", "gate_loop/v3"):
    for f in (HERE / sub).glob("*.png"):
        stem = f.stem
        if stem.startswith("identity_") or stem == "sd_smoke_1": continue
        artifacts.append({"path": str(f), "subject": subject_of(f, stem), "name": stem})
artifacts = list({a["name"]: a for a in artifacts}.values())
log(f"E1: {len(artifacts)} artifacts")

clip = CLIPModel.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True).to(DEV).eval()
cproc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True)
@torch.no_grad()
def clip_embed(p):
    inp = cproc(images=Image.open(p).convert("RGB"), return_tensors="pt").to(DEV)
    f = clip.get_image_features(**inp)
    f = f.pooler_output if hasattr(f, "pooler_output") else f
    return torch.nn.functional.normalize(f, dim=-1)[0]
for a in artifacts:
    e0 = clip_embed(str(PNG / f"{a['subject']}.png"))
    a["clip_identity"] = round(torch.nn.functional.cosine_similarity(e0, clip_embed(a["path"]), dim=0).item(), 4)
del clip; torch.cuda.empty_cache()

dino_ok = True
try:
    dino = AutoModel.from_pretrained("facebook/dinov2-base", local_files_only=True).to(DEV).eval()
    dproc = AutoImageProcessor.from_pretrained("facebook/dinov2-base", local_files_only=True)
    @torch.no_grad()
    def dino_embed(p):
        inp = dproc(images=Image.open(p).convert("RGB"), return_tensors="pt").to(DEV)
        f = dino(**inp).last_hidden_state[:, 0]
        return torch.nn.functional.normalize(f, dim=-1)[0]
    for a in artifacts:
        e0 = dino_embed(str(PNG / f"{a['subject']}.png"))
        a["dino_identity"] = round(torch.nn.functional.cosine_similarity(e0, dino_embed(a["path"]), dim=0).item(), 4)
    del dino; torch.cuda.empty_cache()
except Exception as e:
    dino_ok = False
    log(f"DINOv2 unavailable: {str(e)[:120]}")

out = {"experiment": "v4_e1_judge_axis", "n": len(artifacts), "artifacts": artifacts, "dino_ok": dino_ok}
if dino_ok:
    xs = sorted(range(len(artifacts)), key=lambda i: artifacts[i]["clip_identity"])
    ranks_x = [0]*len(xs)
    for r, i in enumerate(xs): ranks_x[i] = r
    ys = sorted(range(len(artifacts)), key=lambda i: artifacts[i]["dino_identity"])
    ranks_y = [0]*len(ys)
    for r, i in enumerate(ys): ranks_y[i] = r
    n = len(xs); mx = sum(ranks_x)/n; my = sum(ranks_y)/n
    num = sum((ranks_x[i]-mx)*(ranks_y[i]-my) for i in range(n))
    den = (sum((ranks_x[i]-mx)**2 for i in range(n)) * sum((ranks_y[i]-my)**2 for i in range(n))) ** 0.5
    rho = round(num/den, 4)
    flips = [a["name"] for a in artifacts if (a["clip_identity"] >= 0.80) != (a["dino_identity"] >= 0.75) or
             (a["dino_identity"] >= 0.80) != (a["clip_identity"] >= 0.75)]
    flip_rate = round(len(flips)/len(artifacts), 4)
    out.update({"spearman": rho, "flip_names": flips, "flip_rate": flip_rate,
                "claim_E1a_pass": rho >= 0.85, "claim_E1b_pass": flip_rate <= 0.10})
    log(f"E1 spearman={rho} flip_rate={flip_rate} ({len(flips)} flips)")
(HERE / "v4_e1.json").write_text(json.dumps(out, indent=1))
log("E1 written")
