#!/usr/bin/env python3
"""GATE LOOP V0 — the full cascade, gated, receipted.
Target: LUCINEER (target dials from facedials-v3).
Phase A: SD+LCM img2img candidates (seed x strength grid)
Phase B: CLIP identity gate (cos >= 0.80 vs init)
Phase C: moondream+qwen dial gate (L1 to target <= 8)
Phase D: JEV (typesafe noul) semantic gate on survivors' descriptions
Accept set -> gate_receipt.json -> parent anchors via tipnotary.
"""
import base64, json, time, torch, urllib.request, urllib.error, pathlib
from diffusers import StableDiffusionImg2ImgPipeline
from diffusers.schedulers.scheduling_lcm import LCMScheduler
from transformers import CLIPModel, CLIPProcessor
from PIL import Image

PNG = pathlib.Path("/home/eileen/projects/dicebear-quilt/quilt/play-2026-10-02/png")
OUT = pathlib.Path(__file__).parent / "gate_loop"; OUT.mkdir(exist_ok=True)
CKPT = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/checkpoints/dreamshaper_8.safetensors"
LCM = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/lora/lcm.safetensors"
OLLAMA = "http://127.0.0.1:11434/api/generate"
TARGET_FACE = "lucineer"
TARGET_DIALS = {"mood": 2, "warmth": 0, "complexity": 5, "machine_vs_organic": 10, "colorfulness": 4}
PROMPT = "portrait of a stoic machine-like robot, minimal, cool tones, clean vector shapes"
DIALS = list(TARGET_DIALS)
IDENTITY_MIN = 0.80
DIAL_L1_MAX = 8

def log(*a): print(*a, flush=True)

# ---- Phase A: SD + LCM candidates -------------------------------------
t0 = time.time()
pipe = StableDiffusionImg2ImgPipeline.from_single_file(CKPT, torch_dtype=torch.float16, safety_checker=None)
pipe.load_lora_weights(LCM)
pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
pipe.to("cuda"); pipe.enable_attention_slicing()
init = Image.open(PNG / f"{TARGET_FACE}.png").convert("RGB").resize((512, 512))
cands = []
for seed in (11, 22, 33):
    for strength in (0.45, 0.60):
        g = torch.Generator("cuda").manual_seed(seed)
        img = pipe(prompt=PROMPT, image=init, strength=strength, guidance_scale=1.3,
                   num_inference_steps=6, generator=g).images[0]
        name = f"cand_s{seed}_st{strength}"
        img.save(OUT / f"{name}.png")
        cands.append({"name": name, "seed": seed, "strength": strength, "path": str(OUT / f"{name}.png")})
receipt = {"target": TARGET_FACE, "target_dials": TARGET_DIALS, "lcm_steps": 6,
           "gen_s": round(time.time() - t0, 1), "n_candidates": len(cands),
           "identity_min": IDENTITY_MIN, "dial_l1_max": DIAL_L1_MAX, "candidates": cands}
log(f"A: {len(cands)} candidates in {receipt['gen_s']}s (LCM 6-step)")
del pipe; torch.cuda.empty_cache()

# ---- Phase B: CLIP identity gate --------------------------------------
clip = CLIPModel.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True).to("cuda").eval()
proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True)
@torch.no_grad()
def embed(p):
    inp = proc(images=Image.open(p).convert("RGB"), return_tensors="pt").to("cuda")
    f = clip.get_image_features(**inp)
    f = f.pooler_output if hasattr(f, "pooler_output") else f
    return torch.nn.functional.normalize(f, dim=-1)[0]
e_init = embed(str(PNG / f"{TARGET_FACE}.png"))
for c in cands:
    c["identity_cosine"] = round(torch.nn.functional.cosine_similarity(e_init, embed(c["path"]), dim=0).item(), 4)
    c["identity_pass"] = c["identity_cosine"] >= IDENTITY_MIN
del clip; torch.cuda.empty_cache()
log("B: identities " + " ".join(f"{c['identity_cosine']}{'✓' if c['identity_pass'] else '✗'}" for c in cands))

# ---- Phase C: face-dials gate (moondream -> qwen) ---------------------
def ollama(model, prompt, images=None, opts=None, keep_alive=None):
    body = {"model": model, "prompt": prompt, "stream": False, "options":
            {"temperature": 0, "num_predict": 140, "repeat_penalty": 1.15, "repeat_last_n": 32}}
    if opts: body["options"].update(opts)
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
    c["dial_l1"] = round(sum(abs(d[k] - TARGET_DIALS[k]) for k in DIALS), 2) if d else None
    c["dial_pass"] = (c["dial_l1"] is not None and c["dial_l1"] <= DIAL_L1_MAX)
    log(f"C {c['name']}: L1 {c['dial_l1']} {'✓' if c['dial_pass'] else '✗'}")
receipt["dial_spread_all"] = {c["name"]: c["dial_l1"] for c in cands}

# ---- Phase D: JEV semantic gate (typesafe noul on descriptions) -------
def typesafe_key():
    for line in open("/mnt/c/Users/casey/key.txt"):
        if line.startswith("TYPESAFE_AI_KEY="):
            return line.strip().split("=", 1)[1]
    raise RuntimeError("TYPESAFE_AI_KEY not found")
def jev_noul(qid, question, instructions, context_text):
    body = {"model": "jev-latest",
            "questions": {qid: {"type": "noul", "question": question, "instructions": instructions}},
            "input": context_text}
    req = urllib.request.Request("https://api.typesafe.ai/v1/systemone",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {typesafe_key()}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())
survivors = [c for c in cands if c["identity_pass"] and c["dial_pass"]]
log(f"D: {len(survivors)} survivors to JEV")
for c in survivors:
    try:
        r = jev_noul("robot_character",
                     "Does this description clearly indicate a machine-like robot character rather than a human?",
                     "Answer true only if the description unambiguously refers to a robot/machine figure.",
                     c["desc"])
        c["jev_raw"] = json.dumps(r)[:200]
        cell = r.get("results", r)
        c["jev_robot"] = cell
        log(f"D {c['name']}: jev {json.dumps(cell)[:120]}")
    except Exception as e:
        c["jev_error"] = str(e)[:150]; log(f"D {c['name']}: JEV ERROR {str(e)[:100]}")

accepted = [c for c in survivors if not c.get("jev_error")]
receipt["survivors_after_identity_dial"] = [c["name"] for c in survivors]
receipt["accepted"] = [c["name"] for c in accepted]
(OUT / "gate_receipt.json").write_text(json.dumps(receipt, indent=1))
log(f"ACCEPTED {len(accepted)}/{len(cands)}: {[c['name'] for c in accepted]}")
log("receipt: gate_loop/gate_receipt.json")
