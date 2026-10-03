#!/usr/bin/env python3
"""IDENTITY LOOP V0 — the cascading-NN play, measured.
dicebear face (deterministic identity spec) -> SD img2img (NN expansion,
prompt = its measured face-dials) -> CLIP cosine (identity survival metric).
All local: DreamShaper8 + CLIP-vit-b32 (HF cache). dicebear = last-mile anchor.
"""
import torch, json, time, pathlib
from diffusers import StableDiffusionImg2ImgPipeline
from transformers import CLIPModel, CLIPProcessor
from PIL import Image

PNG = pathlib.Path("/home/eileen/projects/dicebear-quilt/quilt/play-2026-10-02/png")
OUT = pathlib.Path(__file__).parent
CKPT = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/checkpoints/dreamshaper_8.safetensors"
# prompts written FROM the face-dials v3 measurements (dials -> words)
TARGETS = {
    "lucineer": "portrait of a stoic machine-like robot, minimal, cool tones, clean vector shapes",
    "casey": "portrait of a joyful friendly adventurer human, warm vivid colors, expressive",
}
receipt = {"identity_metric": "clip-vit-b32 cosine", "strength": 0.55, "steps": 30, "targets": {}}
clip = CLIPModel.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True)
proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True)
clip = clip.to("cuda").eval()

@torch.no_grad()
def embed(img: Image.Image):
    inp = proc(images=img, return_tensors="pt").to("cuda")
    f = clip.get_image_features(**inp)
    f = f.pooler_output if hasattr(f, "pooler_output") else f
    return torch.nn.functional.normalize(f, dim=-1)[0]

t0 = time.time()
pipe = StableDiffusionImg2ImgPipeline.from_single_file(CKPT, torch_dtype=torch.float16, safety_checker=None)
pipe.to("cuda"); pipe.enable_attention_slicing()
receipt["load_s"] = round(time.time() - t0, 1)

def cos(a, b):
    return round(torch.nn.functional.cosine_similarity(a, b, dim=0).item(), 4)

for face, prompt in TARGETS.items():
    init = Image.open(PNG / f"{face}.png").convert("RGB").resize((512, 512))
    t1 = time.time()
    out = pipe(prompt=prompt, image=init, strength=0.55, guidance_scale=7.5,
               num_inference_steps=30).images[0]
    gen_s = round(time.time() - t1, 1)
    out.save(OUT / f"identity_{face}.png")
    e_init, e_out = embed(init), embed(out)
    decoy = Image.open(PNG / "zeroclaw.png").convert("RGB").resize((512, 512))
    identity = cos(e_init, e_out)
    baseline = cos(e_init, embed(decoy))
    receipt["targets"][face] = {"identity_cosine": identity, "decoy_baseline_cosine": baseline,
                                "delta_over_decoy": round(identity - baseline, 4), "gen_s": gen_s}
    print(f"{face}: identity {identity} vs decoy-baseline {baseline} ({gen_s}s)")
del pipe; torch.cuda.empty_cache()
receipt["vram_after_MiB"] = torch.cuda.memory_allocated() // 2**20
(OUT / "identity_receipt.json").write_text(json.dumps(receipt, indent=1))
print("receipt: identity_receipt.json")
