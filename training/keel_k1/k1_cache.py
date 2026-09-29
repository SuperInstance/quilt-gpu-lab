#!/usr/bin/env python3
"""K1/K2 stage 0 — freeze V-JEPA 2 latents + labels to cache.pt.

Two sources (env K1_SOURCE):
  synth  (default) — deterministic glyph-lattice drifting fields, K1.
  lavfi  (K2)      — real lavfi video via ffmpeg rawvideo pipe, source-family
                     labels, per-clip deterministic crop/jitter. Self-contained:
                     no unknown APIs, just ffmpeg (used all day in this lab).
Defensive encoder priority: transformers (E7's pattern, HF cache on disk) ->
E7 module introspect -> torch.hub. Patch outputs mean-pooled. HARD preflight.
"""
import hashlib, json, os, subprocess, sys, time
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(os.path.dirname(HERE))
SOURCE = os.environ.get("K1_SOURCE", "synth")
OUT = os.path.join(HERE, "cache.pt" if SOURCE == "synth" else "cache_lavfi.pt")
DEV = "cuda" if torch.cuda.is_available() else "cpu"
N_TRAIN, N_VAL, CLIP_LEN, H, W = 96, 32, 16, 256, 256
MODEL_ID = "facebook/vjepa2-vitl-fpc16-256-ssv2"
LAVFI = [("still", "color=c=gray:duration=6:size=256x256:rate=10"),
         ("testsrc", "testsrc=duration=6:size=256x256:rate=10"),
         ("smpte", "smptebars=duration=6:size=256x256:rate=10"),
         ("testsrc2", "testsrc2=duration=6:size=256x256:rate=10")]

def log(m): print(f"[k1_cache({SOURCE}) {time.strftime('%H:%M:%S')}] {m}", flush=True)

def synth_clip(idx: int, split_seed: int):
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
    return torch.stack(frames), (0 if vx >= 0 else 1) | (0 if vy >= 0 else 2)

def lavfi_clip(idx: int, split_seed: int):
    """Real lavfi frames + deterministic per-clip crop/jitter. Label = source id."""
    import numpy as np
    g = torch.Generator().manual_seed(split_seed * 100_003 + idx)
    name, spec = LAVFI[idx % len(LAVFI)]
    t0 = float(torch.randint(0, 40, (1,), generator=g)) / 10.0  # seek offset
    cmd = ["ffmpeg", "-loglevel", "error", "-ss", f"{t0:.2f}", "-f", "lavfi", "-i", spec,
           "-frames:v", str(CLIP_LEN), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    arr = np.frombuffer(raw, np.uint8)
    n = len(arr) // (H * W * 3)
    if n < CLIP_LEN:
        arr = np.concatenate([arr] * (CLIP_LEN // max(n, 1) + 1))
        n = CLIP_LEN
    clip = torch.tensor(arr[:n * H * W * 3].reshape(n, H, W, 3), dtype=torch.float32).permute(0, 3, 1, 2) / 255.0
    # deterministic spatial variation: random 224 crop -> resize 256, channel gain
    ox, oy = int(torch.randint(0, 32, (1,), generator=g)), int(torch.randint(0, 32, (1,), generator=g))
    gain = 1.0 + 0.2 * (torch.rand(3, generator=g) - 0.5)
    clip = torch.nn.functional.interpolate(clip[:, :, oy:oy + 224, ox:ox + 224], size=(H, W), mode="bilinear")
    clip = (clip * gain.view(1, 3, 1, 1)).clamp(0, 1)
    return clip, idx % len(LAVFI)

def load_encoder():
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
            h = getattr(out, "last_hidden_state", None) or out[0]
            if h.dim() == 3:
                h = h.mean(dim=1)
            return h.reshape(-1).float().cpu()
        return fn, f"transformers:{MODEL_ID}"
    except Exception as e:
        log(f"transformers path failed ({type(e).__name__}: {e}); trying E7 module")
    try:
        sys.path.insert(0, os.path.join(LAB, "experiments"))
        import importlib
        e7 = importlib.import_module("e7_vjepa2_in_cells")
        cands = [n for n in dir(e7) if "encode" in n.lower()]
        if cands:
            fn = getattr(e7, cands[0])
            return fn, f"e7:{cands[0]}"
    except Exception as e:
        log(f"E7 path failed ({type(e).__name__}: {e}); torch.hub fallback")
    model = torch.hub.load("facebookresearch/vjepa2", "vjepa2_vitl_fpc16_256", pretrained=True)
    model = model.to(DEV).eval()
    @torch.no_grad()
    def fn(clip):
        z = model(clip.to(DEV).unsqueeze(0))
        z = z if torch.is_tensor(z) else z[0]
        if z.dim() == 3:
            z = z.mean(dim=1)
        return z.reshape(-1).float().cpu()
    return fn, "torchhub:vjepa2_vitl_fpc16_256"

def main():
    t0 = time.time()
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    enc, name = load_encoder()
    provider = synth_clip if SOURCE == "synth" else lavfi_clip
    clip, _ = provider(0, 42)
    z = enc(clip)  # HARD PREFLIGHT
    assert z.numel() > 0 and torch.isfinite(z).all(), f"bad preflight latent {tuple(z.shape)}"
    D = z.numel(); log(f"preflight OK dim={D} via {name}")
    data = {}
    for split, n, sd in (("train", N_TRAIN, 42), ("val", N_VAL, 1337)):
        zs, labels = [], []
        for i in range(n):
            c, lab = provider(i, sd)
            zs.append(enc(c)); labels.append(lab)
            if (i + 1) % 8 == 0: log(f"{split} {i+1}/{n} ({time.time()-t0:.0f}s)")
        data[split] = {"latents": torch.stack(zs), "labels": torch.tensor(labels)}
    meta = {"encoder": name, "latent_dim": D, "n_train": N_TRAIN, "n_val": N_VAL,
            "clip_len": CLIP_LEN, "source": SOURCE, "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    torch.save({"data": data, "meta": meta}, OUT)
    print(json.dumps({"stage": "cache", "out": OUT, "dim": D, "source": SOURCE,
                      "label_hist": torch.bincount(data["train"]["labels"]).tolist(),
                      "sha_head": hashlib.sha256(open(OUT, "rb").read(65536)).hexdigest()[:16],
                      "seconds": round(time.time() - t0, 1), "meta": meta}, indent=2))

if __name__ == "__main__":
    main()
