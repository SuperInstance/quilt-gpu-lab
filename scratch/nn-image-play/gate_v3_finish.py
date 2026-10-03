#!/usr/bin/env python3
"""GATE V3 finish — resume receipt pipeline from the 15 already-generated PNGs
(generation completed 125.3s; crash was a stale del line AFTER saving)."""
import base64, json, time, urllib.request, pathlib
import torch
from transformers import CLIPModel, CLIPProcessor
from PIL import Image, ImageFilter, ImageOps

HERE = pathlib.Path(__file__).parent
OUT = HERE / "gate_loop" / "v3"
PNG = pathlib.Path("/home/eileen/projects/dicebear-quilt/quilt/play-2026-10-02/png")
OLLAMA = "http://127.0.0.1:11434/api/generate"
T_DIALS = {"lucineer": {"mood": 2, "warmth": 0, "complexity": 5, "machine_vs_organic": 10, "colorfulness": 4},
           "casey":    {"mood": 10, "warmth": 10, "complexity": 4, "machine_vs_organic": 1, "colorfulness": 6}}
DIALS = list(next(iter(T_DIALS.values())))
ARMS = {"lucineer": ["cn06", "cn09", "base"], "casey": ["cn075", "base"]}
SEEDS = (11, 22, 33)
GEN_S = 125.3  # from the crashed run's own log line

def log(*a): print(*a, flush=True)

def edge_map(p, size=512):
    img = Image.open(p).convert("L").resize((size, size))
    e = ImageOps.invert(img.filter(ImageFilter.FIND_EDGES))
    return ImageOps.autocontrast(e).filter(ImageFilter.GaussianBlur(0.6))

def edge_iou(gen, src, t=100, size=128):
    a = edge_map(src, size).point(lambda v: 255 if v > t else 0)
    b = edge_map(gen, size).point(lambda v: 255 if v > t else 0)
    ab, bb = a.tobytes(), b.tobytes()
    inter = sum(1 for x, y in zip(ab, bb) if x and y)
    union = sum(1 for x, y in zip(ab, bb) if x or y)
    return round(inter / union, 4) if union else 0.0

cands = []
for subj, arms in ARMS.items():
    for arm in arms:
        cns = {"cn06": 0.6, "cn09": 0.9, "cn075": 0.75}.get(arm)
        for seed in SEEDS:
            name = f"{subj}_{arm}_s{seed}"
            p = OUT / f"{name}.png"
            assert p.exists(), name
            cands.append({"name": name, "subject": subj, "arm": arm, "seed": seed,
                          "cn_scale": cns, "path": str(p)})

clip = CLIPModel.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True).to("cuda").eval()
proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True)
@torch.no_grad()
def embed(p):
    inp = proc(images=Image.open(p).convert("RGB"), return_tensors="pt").to("cuda")
    f = clip.get_image_features(**inp)
    f = f.pooler_output if hasattr(f, "pooler_output") else f
    return torch.nn.functional.normalize(f, dim=-1)[0]
for c in cands:
    src = PNG / f"{c['subject']}.png"
    e0 = embed(str(src))
    c["identity"] = round(torch.nn.functional.cosine_similarity(e0, embed(c["path"]), dim=0).item(), 4)
    c["edge_iou"] = edge_iou(c["path"], str(src))
del clip; torch.cuda.empty_cache()
for subj in T_DIALS:
    for arm in ARMS[subj]:
        cs = [c for c in cands if c["subject"] == subj and c["arm"] == arm]
        log(f"B {subj}/{arm}: ident {round(sum(c['identity'] for c in cs)/3,3)} edgeIoU {round(sum(c['edge_iou'] for c in cs)/3,3)}")

def ollama(model, prompt, images=None, keep_alive=None):
    body = {"model": model, "prompt": prompt, "stream": False, "options":
            {"temperature": 0, "num_predict": 140, "repeat_penalty": 1.15, "repeat_last_n": 32}}
    if images: body["images"] = images
    if keep_alive is not None: body["keep_alive"] = keep_alive
    req = urllib.request.Request(OLLAMA, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    for temp in (0, 0.4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())["response"]
        except urllib.error.HTTPError as e:
            if "repeat limit" in e.read().decode()[:200]:
                body["options"]["temperature"] = temp + 0.3; continue
            raise
    return None
def extract_dials(txt):
    i, j = txt.find("{"), txt.rfind("}")
    if i < 0 or j <= i: return None
    try:
        d = json.loads(txt[i:j+1]); return d if all(k in d for k in DIALS) else None
    except json.JSONDecodeError: return None
QT = ('You rate avatar faces from a description. Reply with ONLY strict JSON, integers 0-10: '
      '{"mood":<0 gloomy..10 joyful>,"warmth":<0 cold..10 friendly>,"complexity":<0 minimal..10 busy>,'
      '"machine_vs_organic":<0 machine..10 organic>,"colorfulness":<0 monochrome..10 vivid>} '
      'Description: {desc}')
for c in cands:
    b64 = base64.b64encode(open(c["path"], "rb").read()).decode()
    desc = ollama("moondream", "Describe this avatar face.", images=[b64])
    c["desc"] = (desc or "")[:200]
    d = extract_dials(ollama("qwen2.5:3b-instruct-q4_K_M", QT.replace("{desc}", c["desc"]), keep_alive=0)) if desc else None
    c["dials"] = d
log("C: perceived+quantized")

prereg = json.loads((HERE / "v3_prereg.json").read_text())
receipt = {"experiment": "gate-loop-v3",
           "prereg_sha16": "c56c13c7a2dd6a0e", "prereg": prereg,
           "strength": 0.7, "gen_s": GEN_S, "note": "receipt pipeline resumed from saved PNGs after post-gen crash (stale del line); candidates unchanged",
           "candidates": cands}
for subj in T_DIALS:
    td = T_DIALS[subj]
    for arm in ARMS[subj]:
        arm_c = [c for c in cands if c["subject"] == subj and c["arm"] == arm and c.get("dials")]
        if not arm_c: continue
        bias = {k: round(sum(c["dials"][k] - td[k] for c in arm_c) / len(arm_c), 2) for k in DIALS}
        for c in arm_c:
            c["corrected_L1"] = round(sum(abs((c["dials"][k] - td[k]) - bias[k]) for k in DIALS), 2)
            c["corrected_pass"] = c["corrected_L1"] <= 5.0
        receipt[f"bias_{subj}_{arm}"] = bias
        ids = [c["identity"] for c in arm_c]
        receipt[f"identity_{subj}_{arm}"] = {"mean": round(sum(ids)/len(ids), 3), "min": min(ids)}
        log(f"bias[{subj}/{arm}] = {bias} | ident {receipt[f'identity_{subj}_{arm}']['mean']}")

def arm_mean(subj, arm, key):
    cs = [c for c in cands if c["subject"] == subj and c["arm"] == arm]
    return round(sum(c[key] for c in cs) / len(cs), 4)
claims = {}
for subj in T_DIALS:
    cn_arms = [a for a in ARMS[subj] if a != "base"]
    ident_ok = all(arm_mean(subj, a, "identity") >= 0.82 for a in cn_arms)
    claims[f"C1_{subj}"] = {"claim": "cn mean identity >= 0.82", "pass": bool(ident_ok),
                            "means": {a: arm_mean(subj, a, "identity") for a in ARMS[subj]}}
    paired = all(arm_mean(subj, a, "edge_iou") > arm_mean(subj, "base", "edge_iou") for a in cn_arms)
    claims[f"C2_{subj}"] = {"claim": "cn edge-IoU > base (paired)", "pass": bool(paired),
                            "means": {a: arm_mean(subj, a, "edge_iou") for a in ARMS[subj]}}
mb = receipt.get("bias_lucineer_base", {}).get("machine_vs_organic")
cn_ms = [abs(receipt[f"bias_lucineer_{a}"]["machine_vs_organic"]) for a in ("cn06", "cn09") if f"bias_lucineer_{a}" in receipt]
claims["C3_machine_bias"] = {"claim": "|cn machine bias| < base AND >=1 cn survivor",
                             "base_machine_bias": mb, "cn_machine_bias_abs": cn_ms,
                             "pass": bool(cn_ms and mb is not None and all(v < abs(mb) for v in cn_ms))}
receipt["claims"] = claims
survivors = [c for c in cands if c.get("corrected_pass") and c["identity"] >= 0.80]
def typesafe_key():
    for line in open("/mnt/c/Users/casey/key.txt"):
        if line.startswith("TYPESAFE_AI_KEY="):
            return line.strip().split("=", 1)[1]
    raise RuntimeError("no key")
JEV_Q = {
    "lucineer": {"question": "Does this description clearly indicate a machine-like robot character rather than a human?",
                 "instructions": "Answer true only if the description unambiguously refers to a robot/machine figure."},
    "casey": {"question": "Does this description clearly indicate a human adventurer character rather than a robot?",
              "instructions": "Answer true only if the description unambiguously refers to a human figure."},
}
for c in survivors:
    q = JEV_Q[c["subject"]]
    body = {"model": "jev-latest", "state": c["desc"],
            "questions": {"match": {"type": "noul", **q}}}
    req = urllib.request.Request("https://api.typesafe.ai/v1/systemone", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {typesafe_key()}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r_:
            c["jev"] = json.loads(r_.read()).get("answers", {}).get("match", {})
        log(f"D {c['name']}: jev {json.dumps(c['jev'])[:100]}")
    except Exception as e:
        c["jev_error"] = str(e)[:120]; log(f"D {c['name']}: JEV ERR {str(e)[:80]}")
accepted = [c["name"] for c in survivors if c.get("jev", {}).get("noul", 0) >= 0.6]
receipt["accepted"] = accepted
receipt["survivors"] = [c["name"] for c in survivors]
(OUT.parent / "v3_receipt.json").write_text(json.dumps(receipt, indent=1))
log("CLAIMS " + json.dumps({k: v["pass"] for k, v in claims.items()}))
log(f"ACCEPTED {len(accepted)}: {accepted}")
for n in accepted:
    c = next(c for c in cands if c["name"] == n)
    log(f"  {n}: ident {c['identity']} iou {c['edge_iou']} L1 {c['corrected_L1']} noul {c.get('jev',{}).get('noul')}")
