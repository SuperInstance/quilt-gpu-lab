#!/usr/bin/env python3
"""V4 E2/E3/E4 generation — phased per 6GB law (CN pipe first, then base pipe)."""
import json, time, pathlib, torch
from diffusers import StableDiffusionControlNetImg2ImgPipeline, StableDiffusionImg2ImgPipeline, ControlNetModel
from diffusers.schedulers.scheduling_lcm import LCMScheduler
from PIL import Image, ImageFilter, ImageOps

HERE = pathlib.Path(__file__).parent
PNG = pathlib.Path("/home/eileen/projects/dicebear-quilt/quilt/play-2026-10-02/png")
OUT = HERE / "gate_loop" / "v4"; OUT.mkdir(parents=True, exist_ok=True)
CKPT = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/checkpoints/dreamshaper_8.safetensors"
CN = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/controlnet/lllyasviel_scribble"
LCM = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/lora/lcm.safetensors"
STRENGTH = 0.7
SEEDS4 = (101, 102, 103, 104); SEEDS3 = (101, 102, 103); SEEDS2 = (101, 102)
P_ROBOT = "portrait of a stoic machine-like robot, minimal, cool tones, clean vector shapes"
P_HUMAN = "portrait of a warm friendly adventurer, minimal, warm tones, clean vector shapes"
P_JUDGE = "portrait of an abstract computational judge figure, minimal, cool tones, clean vector shapes"
P_FUN = "portrait of a colorful playful character, minimal, vivid tones, clean vector shapes"
P_WATER = "watercolor painting of a small robot portrait, soft washes, paper texture"
P_NEON = "neon vector poster of a robot head, electric glow, dark background"
PROMPTS = {"lucineer": P_ROBOT, "casey": P_HUMAN, "jev": P_JUDGE, "mmx": P_FUN}
SUBJECTS = ("lucineer", "casey", "jev", "mmx")

def log(*a): print(*a, flush=True)

def edge_map(p, size=512):
    img = Image.open(p).convert("L").resize((size, size))
    e = ImageOps.invert(img.filter(ImageFilter.FIND_EDGES))
    return ImageOps.autocontrast(e).filter(ImageFilter.GaussianBlur(0.6))

# (name, subject, arm, cn_scale_or_None, seed, prompt, init_subject, edges_subject)
PLAN = []
for seed in SEEDS4:
    PLAN.append((f"lucineer_cn045_s{seed}", "lucineer", "cn045", 0.45, seed, P_ROBOT, "lucineer", "lucineer"))
    PLAN.append((f"lucineer_cn06_s{seed}", "lucineer", "cn06", 0.6, seed, P_ROBOT, "lucineer", "lucineer"))
    PLAN.append((f"casey_cn06_s{seed}", "casey", "cn06", 0.6, seed, P_HUMAN, "casey", "casey"))
for seed in SEEDS3:
    PLAN.append((f"jev_cn06_s{seed}", "jev", "cn06", 0.6, seed, P_JUDGE, "jev", "jev"))
    PLAN.append((f"mmx_cn06_s{seed}", "mmx", "cn06", 0.6, seed, P_FUN, "mmx", "mmx"))
for seed in SEEDS2:
    PLAN.append((f"xcasey_lucedges_s{seed}", "casey", "xcn06", 0.6, seed, P_HUMAN, "casey", "lucineer"))
    PLAN.append((f"xlucineer_caseyedges_s{seed}", "lucineer", "xcn06", 0.6, seed, P_ROBOT, "lucineer", "casey"))
    PLAN.append((f"lucineer_water_cn06_s{seed}", "lucineer", "water_cn06", 0.6, seed, P_WATER, "lucineer", "lucineer"))
    PLAN.append((f"lucineer_neon_cn06_s{seed}", "lucineer", "neon_cn06", 0.6, seed, P_NEON, "lucineer", "lucineer"))
BASE_PLAN = []
for seed in SEEDS4:
    BASE_PLAN.append((f"lucineer_base_s{seed}", "lucineer", "base", None, seed, P_ROBOT, "lucineer", "lucineer"))
for seed in SEEDS2:
    BASE_PLAN.append((f"casey_base_s{seed}", "casey", "base", None, seed, P_HUMAN, "casey", "casey"))
    BASE_PLAN.append((f"jev_base_s{seed}", "jev", "base", None, seed, P_JUDGE, "jev", "jev"))
    BASE_PLAN.append((f"mmx_base_s{seed}", "mmx", "base", None, seed, P_FUN, "mmx", "mmx"))
    BASE_PLAN.append((f"lucineer_water_base_s{seed}", "lucineer", "water_base", None, seed, P_WATER, "lucineer", "lucineer"))
    BASE_PLAN.append((f"lucineer_neon_base_s{seed}", "lucineer", "neon_base", None, seed, P_NEON, "lucineer", "lucineer"))

emaps = {s: edge_map(PNG / f"{s}.png") for s in SUBJECTS}
inits = {s: Image.open(PNG / f"{s}.png").convert("RGB").resize((512, 512)) for s in SUBJECTS}
cands, t0 = [], time.time()

cn = ControlNetModel.from_pretrained(CN, torch_dtype=torch.float16, variant="fp16")
pipe = StableDiffusionControlNetImg2ImgPipeline.from_single_file(CKPT, controlnet=cn, torch_dtype=torch.float16, safety_checker=None)
pipe.load_lora_weights(LCM); pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
pipe.to("cuda"); pipe.enable_attention_slicing()
log(f"cn pipe {round(time.time()-t0,1)}s")
for (name, subject, arm, cns, seed, prompt, init_sub, edge_sub) in PLAN:
    g = torch.Generator("cuda").manual_seed(seed)
    img = pipe(prompt=prompt, image=inits[init_sub], control_image=emaps[edge_sub],
               strength=STRENGTH, guidance_scale=1.5, num_inference_steps=6,
               controlnet_conditioning_scale=cns, generator=g).images[0]
    img.save(OUT / f"{name}.png")
    cands.append({"name": name, "subject": subject, "arm": arm, "cn_scale": cns, "seed": seed,
                  "prompt": prompt, "init_subject": init_sub, "edges_subject": edge_sub,
                  "path": str(OUT / f"{name}.png")})
log(f"A: {len(cands)} cn candidates {round(time.time()-t0,1)}s")
del pipe, cn; torch.cuda.empty_cache()

pipe = StableDiffusionImg2ImgPipeline.from_single_file(CKPT, torch_dtype=torch.float16, safety_checker=None)
pipe.load_lora_weights(LCM); pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
pipe.to("cuda"); pipe.enable_attention_slicing()
log(f"base pipe {round(time.time()-t0,1)}s")
for (name, subject, arm, cns, seed, prompt, init_sub, edge_sub) in BASE_PLAN:
    g = torch.Generator("cuda").manual_seed(seed)
    img = pipe(prompt=prompt, image=inits[init_sub], strength=STRENGTH,
               guidance_scale=1.5, num_inference_steps=6, generator=g).images[0]
    img.save(OUT / f"{name}.png")
    cands.append({"name": name, "subject": subject, "arm": arm, "cn_scale": None, "seed": seed,
                  "prompt": prompt, "init_subject": init_sub, "edges_subject": edge_sub,
                  "path": str(OUT / f"{name}.png")})
gen_s = round(time.time() - t0, 1)
log(f"A: {len(cands)} total candidates in {gen_s}s")
del pipe; torch.cuda.empty_cache()
(HERE / "v4_cands.json").write_text(json.dumps({"gen_s": gen_s, "strength": STRENGTH, "candidates": cands}, indent=1))
log("v4_cands.json written")
