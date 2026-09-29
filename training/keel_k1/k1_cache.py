#!/usr/bin/env python3
"""K1 stage 0 — freeze V-JEPA 2 latents + motion labels to cache.pt.

Defensive + fail-loud (see K1-plan.md). Encoder priority: (a) transformers
(E7's exact pattern; HF cache already on disk), (b) E7 module introspect,
(c) torch.hub. Patch outputs are mean-pooled. HARD preflight before the burn.
"""
import hashlib, json, os, sys, time
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, "cache.pt")
DEV = "cuda" if torch.cuda.is_available() else "cpu"
N_TRAIN, N_VAL, CLIP_LEN, H, W = 96, 32, 16, 256, 256
MODEL_ID = "facebook/vjepa2-vitl-fpc16-256-ssv2"

def log(m): print(f"[k1_cache {time.strftime('%H:%M:%S')}] {m}", flush=True)

def synth_clip(idx: int, split_seed: int):
    """Drifting coarse-field clip. Returns (T,C,H,W float in [0,1], (vx,vy))."""
    g = torch.Generator().manual_seed(split_seed * 100_003 + idx)
    base = torch.rand(1, 3, H // 8, W // 8, generator=g)
    base = torch.nn.functional.interpolate(base, size=(H, W), mode="bilinear")[0]
    vx = int(torch.randint(-40, 40, (1,), generator=g))
    vy = int(torch.randint(-30, 30, (1,), generator=g))
    frames = []
    for i in range(CLIP_LEN):
        sh = base.roll(shifts=(int(vy * i / CLIP_LEN * 8), int(vx * i / CLIP_LEN * 8)), dims=(1, 2))
        flick = 0.04 * torch.randn(1, H, W, generator=g)
        frames.append((sh + flick).clamp(0, 1))
    return torch.stack(frames), (vx, vy)

def load_encoder():
    # (a) transformers — mirrors E7; HF cache verified on disk
    try:
        from transformers import VJEPA2Model, VJEPA2VideoProcessor
        proc = VJEPA2VideoProcessor.from_pretrained(MODEL_ID)
        mdl = VJEPA2Model.from_pretrained(MODEL_ID, torch_dtype=torch.float16).to(DEV).eval()
        @torch.no_grad()
        def fn(clip):
            inputs = proc(videos=[clip.numpy()], return_tensors="pt")
            inputs = {k: (v.half().to(DEV) if v.dtype.is_floating_point else v.to(DEV))
                      for k, v in inputs.items()}
            out = mdl(**inputs)
            h = getattr(out, "last_hidden_state", None)
            if h is None:
                h = out[0]
            if h.dim() == 3:          # (B, N_patches, D) -> mean-pool
                h = h.mean(dim=1)
            return h.reshape(-1).float().cpu()
        return fn, f"transformers:{MODEL_ID}"
    except Exception as e:
        log(f"transformers path failed ({type(e).__name__}: {e}); trying E7 module")
    # (b) E7's module — introspect only, never guess internals
    try:
        sys.path.insert(0, os.path.join(LAB, "experiments"))
        import importlib
        e7 = importlib.import_module("e7_vjepa2_in_cells")
        cands = [n for n in dir(e7) if "encode" in n.lower()]
        if cands:
            fn = getattr(e7, cands[0])
            log(f"E7 encoder: e7_vjepa2_in_cells.{cands[0]}")
            return fn, f"e7:{cands[0]}"
    except Exception as e:
        log(f"E7 path failed ({type(e).__name__}: {e}); torch.hub fallback")
    # (c) torch.hub
    model = torch.hub.load("facebookresearch/vjepa2", "vjepa2_vitl_fpc16_256", pretrained=True)
    model = model.to(DEV).eval()
    @torch.no_grad()
    def fn(clip):
        x = clip.to(DEV).unsqueeze(0)
        z = model(x)
        z = z if torch.is_tensor(z) else z[0]
        if z.dim() == 3:
            z = z.mean(dim=1)
        return z.reshape(-1).float().cpu()
    return fn, "torchhub:vjepa2_vitl_fpc16_256"

def quadrant(vx, vy):  # the 4-code motion arity (T4/T5 cardinals)
    return (0 if vx >= 0 else 1) | (0 if vy >= 0 else 2)

def main():
    t0 = time.time()
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    enc, name = load_encoder()
    clip, _ = synth_clip(0, 42)
    z = enc(clip)  # HARD PREFLIGHT
    assert z.numel() > 0 and torch.isfinite(z).all(), f"bad preflight latent {tuple(z.shape)}"
    D = z.numel(); log(f"preflight OK dim={D} via {name}")
    if D > 4096:
        log(f"WARNING: latent dim {D} large; predictor proj will be heavy")

    data = {}
    for split, n, sd in (("train", N_TRAIN, 42), ("val", N_VAL, 1337)):
        zs, labels = [], []
        for i in range(n):
            c, (vx, vy) = synth_clip(i, sd)
            zs.append(enc(c)); labels.append(quadrant(vx, vy))
            if (i + 1) % 8 == 0: log(f"{split} {i+1}/{n} ({time.time()-t0:.0f}s)")
        data[split] = {"latents": torch.stack(zs), "labels": torch.tensor(labels)}
    meta = {"encoder": name, "latent_dim": D, "n_train": N_TRAIN, "n_val": N_VAL,
            "clip_len": CLIP_LEN, "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    torch.save({"data": data, "meta": meta}, OUT)
    print(json.dumps({"stage": "cache", "out": OUT, "dim": D,
                      "label_hist": torch.bincount(data["train"]["labels"]).tolist(),
                      "sha_head": hashlib.sha256(open(OUT, "rb").read(65536)).hexdigest()[:16],
                      "seconds": round(time.time() - t0, 1), "meta": meta}, indent=2))

if __name__ == "__main__":
    main()
