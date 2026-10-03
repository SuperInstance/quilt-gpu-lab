#!/usr/bin/env python3
"""W5-A Judge Board of Three — CLIP + DINOv2 + IJEPA over all archived artifacts.
Claims (frozen in header before run):
  B1: >= 2 of 3 judge pairs Spearman >= 0.80
  B2: 3-judge majority flips <= 40% of CLIP-alone floor decisions on non-morph artifacts
  B3: board rejects >= 3 of 4 E3 cross-identity morphs that CLIP alone accepted
Honest FAIL allowed; v4_E1 known: CLIPxDINOv2 Spearman 0.5633, flips 78.4%.
"""
import json, pathlib, torch
from transformers import CLIPModel, CLIPProcessor, AutoModel, AutoImageProcessor
from PIL import Image

HERE = pathlib.Path(__file__).parent
PNG = pathlib.Path("/home/eileen/projects/dicebear-quilt/quilt/play-2026-10-02/png")
DEV = "cuda" if torch.cuda.is_available() else "cpu"
def log(*a): print(*a, flush=True)

def subject_of(stem):
    for s in ("lucineer", "casey", "jev", "mmx"):
        if stem.startswith(s): return s
    return "lucineer"

artifacts = []
for sub in ("gate_loop", "gate_loop/v2", "gate_loop/v3", "gate_loop/v4"):
    for f in (HERE / sub).glob("*.png"):
        stem = f.stem
        if stem.startswith("identity_") or stem == "sd_smoke_1": continue
        artifacts.append({"path": str(f), "name": stem, "subject": subject_of(stem),
                          "is_morph": "_cn06_s1" in stem and stem.startswith(("xcasey", "xlucineer"))})
artifacts = list({a["name"]: a for a in artifacts}.values())
log(f"board: {len(artifacts)} artifacts ({sum(a['is_morph'] for a in artifacts)} morphs)")

def run_judge(label, model_name, feat_fn):
    model = AutoModel.from_pretrained(model_name, local_files_only=True).to(DEV).eval()
    proc = AutoImageProcessor.from_pretrained(model_name, local_files_only=True)
    @torch.no_grad()
    def embed(p):
        inp = proc(images=Image.open(p).convert("RGB"), return_tensors="pt").to(DEV)
        return torch.nn.functional.normalize(feat_fn(model(**inp)), dim=-1)[0]
    for a in artifacts:
        e0 = embed(str(PNG / f"{a['subject']}.png"))
        a[label] = round(torch.nn.functional.cosine_similarity(e0, embed(a["path"]), dim=0).item(), 4)
    del model; torch.cuda.empty_cache()
    log(f"{label} done")

run_judge("dino", "facebook/dinov2-base",
          lambda out: out.last_hidden_state[:, 0])

def ijeap_feat(out):
    h = out.last_hidden_state
    return h[:, 1:].mean(dim=1) if h.shape[1] > 1 else h[:, 0]
try:
    run_judge("ijepa", "facebook/ijepa_vith16_1k", ijeap_feat)
except Exception as e:
    log(f"ijepa unavailable: {str(e)[:150]}")

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
    a["clip"] = round(torch.nn.functional.cosine_similarity(e0, clip_embed(a["path"]), dim=0).item(), 4)
del clip; torch.cuda.empty_cache()
log("clip done")

JUDGES = [j for j in ("clip", "dino", "ijepa") if all(j in a for a in artifacts)]
def spearman(key):
    xs = sorted(artifacts, key=lambda a: a[key])
    ranks = {a["name"]: r for r, a in enumerate(xs)}
    n = len(xs); mx = n * (n - 1) / 2 / n
    num = sum((ranks[artifacts[i]["name"]] - mx) * (ranks[artifacts[i]["name"]] - mx) for i in range(n))
    den = sum((ranks[a["name"]] - mx) ** 2 for a in artifacts)
    return round(num / (den ** 0.5), 4) if den else 0.0
def spearman2(k1, k2):
    order1 = sorted(artifacts, key=lambda a: a[k1])
    r1 = {a["name"]: r for r, a in enumerate(order1)}
    order2 = sorted(artifacts, key=lambda a: a[k2])
    r2 = {a["name"]: r for r, a in enumerate(order2)}
    n = len(artifacts); mu = (n - 1) / 2
    num = sum((r1[a["name"]] - mu) * (r2[a["name"]] - mu) for a in artifacts)
    den = (sum((r1[a["name"]] - mu) ** 2 for a in artifacts) * sum((r2[a["name"]] - mu) ** 2 for a in artifacts)) ** 0.5
    return round(num / den, 4) if den else 0.0

pairs = {f"{a}x{b}": spearman2(a, b) for i, a in enumerate(JUDGES) for b in JUDGES[i+1:]}
FLOOR = 0.80
morphs = [a for a in artifacts if a["is_morph"]]
nonmorphs = [a for a in artifacts if not a["is_morph"]]
def board(a): return sum(a[j] >= FLOOR for j in JUDGES) > len(JUDGES) / 2
flips = [a["name"] for a in nonmorphs if (a["clip"] >= FLOOR) != board(a)]
flip_rate = round(len(flips) / max(1, len(nonmorphs)), 4)
morph_rejects = [a["name"] for a in morphs if not board(a)]

claims = {
    "B1": {"claim": ">=2/3 pairs Spearman >= 0.80", "pairs": pairs,
           "pass": sum(v >= 0.80 for v in pairs.values()) >= 2},
    "B2": {"claim": "board-vs-CLIP flip <= 40% on non-morphs", "flip_rate": flip_rate,
           "flips": flips, "pass": flip_rate <= 0.40},
    "B3": {"claim": "board rejects >= 3/4 morphs CLIP accepted",
           "morph_identities": {a["name"]: {j: a[j] for j in JUDGES} for a in morphs},
           "rejected": morph_rejects, "pass": len(morph_rejects) >= 3},
}
out = {"experiment": "w5a-judge-board", "claims_frozen_in_header": True, "judges": JUDGES,
       "floor": FLOOR, "n": len(artifacts), "pairs_spearman": pairs,
       "flip_rate_nonmorph": flip_rate, "morph_verdicts": morph_rejects, "claims": claims,
       "artifacts": artifacts}
(HERE / "v5a_board.json").write_text(json.dumps(out, indent=1))
log("CLAIMS " + json.dumps({k: v["pass"] for k, v in claims.items()}))
log(f"pairs {pairs} | nonmorph flip {flip_rate} | morph rejects {len(morph_rejects)}/4")
