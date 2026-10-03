#!/usr/bin/env python3
"""GATE LOOP V2 — 16 candidates x 2 prompt arms; can prompt-side push fight
the measured -6.17 machine bias? Bias sheet per arm. v1 machinery reused."""
import base64, json, time, torch, urllib.request, pathlib
from diffusers import StableDiffusionImg2ImgPipeline
from diffusers.schedulers.scheduling_lcm import LCMScheduler
from transformers import CLIPModel, CLIPProcessor
from PIL import Image

PNG = pathlib.Path("/home/eileen/projects/dicebear-quilt/quilt/play-2026-10-02/png")
HERE = pathlib.Path(__file__).parent / "gate_loop"
OUT = HERE / "v2"; OUT.mkdir(exist_ok=True)
CKPT = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/checkpoints/dreamshaper_8.safetensors"
LCM = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/lora/lcm.safetensors"
OLLAMA = "http://127.0.0.1:11434/api/generate"
T_FACE = "lucineer"
T_DIALS = {"mood": 2, "warmth": 0, "complexity": 5, "machine_vs_organic": 10, "colorfulness": 4}
DIALS = list(T_DIALS)
ARMS = {
    "base": "portrait of a stoic machine-like robot, minimal, cool tones, clean vector shapes",
    "push": "metallic mechanical robot head, industrial machine, artificial, minimal, cool tones, clean vector shapes",
}
def log(*a): print(*a, flush=True)

t0 = time.time()
pipe = StableDiffusionImg2ImgPipeline.from_single_file(CKPT, torch_dtype=torch.float16, safety_checker=None)
pipe.load_lora_weights(LCM)
pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
pipe.to("cuda"); pipe.enable_attention_slicing()
init = Image.open(PNG / f"{T_FACE}.png").convert("RGB").resize((512, 512))
cands = []
for arm, prompt in ARMS.items():
    for seed in (11, 22, 33, 44):
        for strength in (0.5, 0.65):
            g = torch.Generator("cuda").manual_seed(seed)
            img = pipe(prompt=prompt, image=init, strength=strength, guidance_scale=1.3,
                       num_inference_steps=6, generator=g).images[0]
            name = f"{arm}_s{seed}_st{strength}"
            img.save(OUT / f"{name}.png")
            cands.append({"name": name, "arm": arm, "seed": seed, "strength": strength, "path": str(OUT / f"{name}.png")})
gen_s = round(time.time() - t0, 1)
log(f"A: 16 candidates in {gen_s}s")
del pipe; torch.cuda.empty_cache()

clip = CLIPModel.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True).to("cuda").eval()
proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True)
@torch.no_grad()
def embed(p):
    inp = proc(images=Image.open(p).convert("RGB"), return_tensors="pt").to("cuda")
    f = clip.get_image_features(**inp)
    f = f.pooler_output if hasattr(f, "pooler_output") else f
    return torch.nn.functional.normalize(f, dim=-1)[0]
e_init = embed(str(PNG / f"{T_FACE}.png"))
for c in cands:
    c["identity"] = round(torch.nn.functional.cosine_similarity(e_init, embed(c["path"]), dim=0).item(), 4)
del clip; torch.cuda.empty_cache()
log("B: identity mean per arm: " + str({a: round(sum(c['identity'] for c in cands if c['arm']==a)/8,3) for a in ARMS}))

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
log("C: 16 perceived+quantized")

# bias sheet PER ARM + corrected L1
receipt = {"target": T_FACE, "target_dials": T_DIALS, "arms": ARMS, "gen_s": gen_s, "candidates": cands}
for arm in ARMS:
    arm_c = [c for c in cands if c["arm"] == arm and c.get("dials")]
    if not arm_c: continue
    bias = {k: round(sum(c["dials"][k] - T_DIALS[k] for c in arm_c) / len(arm_c), 2) for k in DIALS}
    for c in arm_c:
        c["corrected_L1"] = round(sum(abs((c["dials"][k] - T_DIALS[k]) - bias[k]) for k in DIALS), 2)
        c["corrected_pass"] = c["corrected_L1"] <= 5.0
    receipt[f"bias_{arm}"] = bias
    ids = [c["identity"] for c in arm_c]
    receipt[f"identity_{arm}"] = {"mean": round(sum(ids)/len(ids), 3), "min": min(ids)}
    log(f"bias[{arm}] = {bias} | ident mean {receipt[f'identity_{arm}']['mean']}")
mach_base = receipt.get("bias_base", {}).get("machine_vs_organic")
mach_push = receipt.get("bias_push", {}).get("machine_vs_organic")
if mach_base is not None and mach_push is not None:
    receipt["prompt_steering_effect_machine"] = round(mach_push - mach_base, 2)
    log(f"PROMPT STEERING (machine dial): base {mach_base} -> push {mach_push} (effect {receipt['prompt_steering_effect_machine']})")
survivors = [c for c in cands if c.get("corrected_pass") and c["identity"] >= 0.80]
def typesafe_key():
    for line in open("/mnt/c/Users/casey/key.txt"):
        if line.startswith("TYPESAFE_AI_KEY="):
            return line.strip().split("=", 1)[1]
    raise RuntimeError("no key")
for c in survivors:
    body = {"model": "jev-latest", "state": c["desc"],
            "questions": {"robot": {"type": "noul",
                                    "question": "Does this description clearly indicate a machine-like robot character rather than a human?",
                                    "instructions": "Answer true only if the description unambiguously refers to a robot/machine figure."}}}
    req = urllib.request.Request("https://api.typesafe.ai/v1/systemone", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {typesafe_key()}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r_:
            c["jev"] = json.loads(r_.read()).get("answers", {}).get("robot", {})
        log(f"D {c['name']}: jev {json.dumps(c['jev'])[:100]}")
    except Exception as e:
        c["jev_error"] = str(e)[:120]; log(f"D {c['name']}: JEV ERR {str(e)[:80]}")
accepted = [c["name"] for c in survivors if c.get("jev", {}).get("noul", 0) >= 0.6]
receipt["accepted"] = accepted
receipt["survivors"] = [c["name"] for c in survivors]
(OUT / "gate_v2_receipt.json").write_text(json.dumps(receipt, indent=1))
log(f"ACCEPTED {len(accepted)}: {accepted}")
