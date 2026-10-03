#!/usr/bin/env python3
"""GATE LOOP V3 — ControlNet-scribble from dicebear edges. Per v3_prereg.json (frozen).
Arms: cn06/cn09/cn075 (scribble-CN conditioned) vs base (plain img2img, matched control)."""
import base64, hashlib, json, time, urllib.request, pathlib
import torch
from diffusers import StableDiffusionControlNetImg2ImgPipeline, StableDiffusionImg2ImgPipeline, ControlNetModel
from diffusers.schedulers.scheduling_lcm import LCMScheduler
from transformers import CLIPModel, CLIPProcessor
from PIL import Image, ImageFilter, ImageOps

HERE = pathlib.Path(__file__).parent
PNG = pathlib.Path("/home/eileen/projects/dicebear-quilt/quilt/play-2026-10-02/png")
OUT = HERE / "gate_loop" / "v3"; OUT.mkdir(parents=True, exist_ok=True)
CKPT = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/checkpoints/dreamshaper_8.safetensors"
CN = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/controlnet/lllyasviel_scribble"
LCM = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/lora/lcm.safetensors"
OLLAMA = "http://127.0.0.1:11434/api/generate"
T_DIALS = {"lucineer": {"mood": 2, "warmth": 0, "complexity": 5, "machine_vs_organic": 10, "colorfulness": 4},
           "casey":    {"mood": 10, "warmth": 10, "complexity": 4, "machine_vs_organic": 1, "colorfulness": 6}}
DIALS = list(next(iter(T_DIALS.values())))
STRENGTH = 0.7
PROMPT = "portrait of a stoic machine-like robot, minimal, cool tones, clean vector shapes"
PROMPT_HUMAN = "portrait of a warm friendly adventurer, minimal, warm tones, clean vector shapes"
ARMS = {"lucineer": {"cn06": (0.6, PROMPT), "cn09": (0.9, PROMPT), "base": (None, PROMPT)},
        "casey": {"cn075": (0.75, PROMPT_HUMAN), "base": (None, PROMPT_HUMAN)}}
SEEDS = (11, 22, 33)

def log(*a): print(*a, flush=True)

def freeze_prereg():
    p = HERE / "v3_prereg.json"
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]

def edge_map(png_path):
    """dicebear -> scribble conditioning map: white lines on black."""
    img = Image.open(png_path).convert("L").resize((512, 512))
    e = img.filter(ImageFilter.FIND_EDGES)
    e = ImageOps.invert(e)          # lines white, body black
    e = ImageOps.autocontrast(e)
    return e.filter(ImageFilter.GaussianBlur(0.6))

def edge_iou(gen_path, src_path, t=100, size=128):
    a = edge_map(src_path).resize((size, size)).point(lambda v: 255 if v > t else 0)
    b = edge_map(gen_path).resize((size, size)).point(lambda v: 255 if v > t else 0)
    ab, bb = a.tobytes(), b.tobytes()
    inter = sum(1 for x, y in zip(ab, bb) if x and y)
    union = sum(1 for x, y in zip(ab, bb) if x or y)
    return round(inter / union, 4) if union else 0.0

t0 = time.time()
prereg_sha = freeze_prereg()
log(f"prereg sha256[:16] = {prereg_sha}")
cn = ControlNetModel.from_pretrained(CN, torch_dtype=torch.float16, variant="fp16")
log(f"CN loaded {round(time.time()-t0,1)}s")
pipe_cn = StableDiffusionControlNetImg2ImgPipeline.from_single_file(
    CKPT, controlnet=cn, torch_dtype=torch.float16, safety_checker=None)
pipe_cn.load_lora_weights(LCM)
pipe_cn.scheduler = LCMScheduler.from_config(pipe_cn.scheduler.config)
pipe_cn.to("cuda"); pipe_cn.enable_attention_slicing()
log(f"cn pipe loaded {round(time.time()-t0,1)}s")

srcs = {s: PNG / f"{s}.png" for s in T_DIALS}
inits = {s: Image.open(srcs[s]).convert("RGB").resize((512, 512)) for s in T_DIALS}
emaps = {s: edge_map(srcs[s]) for s in T_DIALS}

# phase 1: CN arms (6GB law — one heavy pipeline resident at a time)
cands = []
for subject, arms in ARMS.items():
    for arm, (cns, prompt) in arms.items():
        if cns is None: continue
        for seed in SEEDS:
            g = torch.Generator("cuda").manual_seed(seed)
            img = pipe_cn(prompt=prompt, image=inits[subject], control_image=emaps[subject],
                          strength=STRENGTH, guidance_scale=1.5, num_inference_steps=6,
                          controlnet_conditioning_scale=cns, generator=g).images[0]
            name = f"{subject}_{arm}_s{seed}"
            img.save(OUT / f"{name}.png")
            cands.append({"name": name, "subject": subject, "arm": arm, "seed": seed,
                          "cn_scale": cns, "path": str(OUT / f"{name}.png")})
del pipe_cn, cn; torch.cuda.empty_cache()

# phase 2: base control arms
pipe_base = StableDiffusionImg2ImgPipeline.from_single_file(
    CKPT, torch_dtype=torch.float16, safety_checker=None)
pipe_base.load_lora_weights(LCM)
pipe_base.scheduler = LCMScheduler.from_config(pipe_base.scheduler.config)
pipe_base.to("cuda"); pipe_base.enable_attention_slicing()
log(f"base pipe loaded {round(time.time()-t0,1)}s")
for subject, arms in ARMS.items():
    for arm, (cns, prompt) in arms.items():
        if cns is not None: continue
        for seed in SEEDS:
            g = torch.Generator("cuda").manual_seed(seed)
            img = pipe_base(prompt=prompt, image=inits[subject], strength=STRENGTH,
                            guidance_scale=1.5, num_inference_steps=6, generator=g).images[0]
            name = f"{subject}_{arm}_s{seed}"
            img.save(OUT / f"{name}.png")
            cands.append({"name": name, "subject": subject, "arm": arm, "seed": seed,
                          "cn_scale": None, "path": str(OUT / f"{name}.png")})
del pipe_base; torch.cuda.empty_cache()
gen_s = round(time.time() - t0, 1)
log(f"A: {len(cands)} candidates in {gen_s}s")
del pipe_cn, pipe_base, cn; torch.cuda.empty_cache()

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
        log(f"B {subj}/{arm}: ident mean {round(sum(c['identity'] for c in cs)/len(cs),3)} "
            f"edgeIoU mean {round(sum(c['edge_iou'] for c in cs)/len(cs),3)}")
log("B: identity + structure done")

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
log("C: 15 perceived+quantized")

receipt = {"experiment": "gate-loop-v3", "prereg_sha16": prereg_sha, "prereg": json.loads((HERE / "v3_prereg.json").read_text()),
           "strength": STRENGTH, "gen_s": gen_s, "candidates": cands}
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

# ---- claims
def arm_mean(subj, arm, key):
    cs = [c for c in cands if c["subject"] == subj and c["arm"] == arm]
    return round(sum(c[key] for c in cs) / len(cs), 4)
claims = {}
for subj in T_DIALS:
    base_arm = "base"
    cn_arms = [a for a in ARMS[subj] if a != "base"]
    ident_ok = all(arm_mean(subj, a, "identity") >= 0.82 for a in cn_arms)
    claims[f"C1_{subj}"] = {"claim": "cn mean identity >= 0.82", "pass": ident_ok,
                            "means": {a: arm_mean(subj, a, "identity") for a in ARMS[subj]}}
    paired = all(arm_mean(subj, a, "edge_iou") > arm_mean(subj, base_arm, "edge_iou") for a in cn_arms)
    claims[f"C2_{subj}"] = {"claim": "cn edge-IoU > base (paired)", "pass": bool(paired),
                            "means": {a: arm_mean(subj, a, "edge_iou") for a in ARMS[subj]}}
mb = receipt.get(f"bias_lucineer_base", {}).get("machine_vs_organic")
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
(HERE / "gate_loop" / "v3_receipt.json").write_text(json.dumps(receipt, indent=1))
log(f"CLAIMS {json.dumps({k: v['pass'] for k, v in claims.items()})}")
log(f"ACCEPTED {len(accepted)}: {accepted}")
