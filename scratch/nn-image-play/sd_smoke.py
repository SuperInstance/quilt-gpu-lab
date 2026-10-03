#!/usr/bin/env python3
"""SD1.5 smoke: DreamShaper 8 (ASUS AICreator checkpoint) -> 1 txt2img, VRAM-batched."""
import torch, time, json, pathlib
from diffusers import StableDiffusionPipeline

CKPT = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/checkpoints/dreamshaper_8.safetensors"
OUT = pathlib.Path(__file__).parent
ramp = {"vram_before_MiB": torch.cuda.memory_allocated() // 2**20}
t0 = time.time()
pipe = StableDiffusionPipeline.from_single_file(CKPT, torch_dtype=torch.float16, safety_checker=None)
load_s = round(time.time() - t0, 1)
pipe.to("cuda"); pipe.enable_attention_slicing()
ramp["vram_loaded_MiB"] = torch.cuda.memory_allocated() // 2**20
t1 = time.time()
img = pipe("a friendly robot bartender polishing a glass, flat vector style, warm light",
           num_inference_steps=25, guidance_scale=7.0, width=512, height=512).images[0]
gen_s = round(time.time() - t1, 1)
img.save(OUT / "sd_smoke_1.png")
ramp.update({"load_s": load_s, "gen25step_s": gen_s,
             "size": list(img.size), "sha_file": str(OUT / "sd_smoke_1.png")})
del pipe; torch.cuda.empty_cache()
ramp["vram_after_MiB"] = torch.cuda.memory_allocated() // 2**20
print(json.dumps(ramp, indent=1))
