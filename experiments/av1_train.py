#!/usr/bin/env python
"""experiments/av1_train.py — AV1: ascii→video learning loop (single file).

Pre-registration: proposals/runs/AV1-ascii-to-video.md (FROZEN 2026-09-30, pushed
before fire). Hypotheses/branches are frozen — no re-rolls; verdicts honest.

Stages (default: all):
  A  — algorithmic glyph-atlas baseline (the honest floor), pure-torch eval path
  B  — tiny learned conv decoder (<5M params), frame-L1 training      [RUN 1 / H1]
  B' — same decoder + temporal Δ loss, matched compute               [RUN 2 / H2]
  D  — DDPM warm-up (google/ddpm-cifar10-32, 8 imgs × 8 DDIM steps)  [not a hypothesis]

GEOMETRY NOTES (receipted honestly):
  - Task text said "cell 4×10 px so 100×50 → 400×200": 100×4=400 (W) but 50×10=500≠200.
    Only 4×4 cells map the grid onto 400×200. Baseline A rasterizes at 4×4 per cell
    (supersampled ×16 then avg-pooled for antialiasing) at 400×200, then avg-pools 2×2
    to the common eval resolution.
  - Task wrote target "3×200×100 (2× the grid)": 2× of (rows 50 × cols 100) is
    H=100 × W=200 → tensor 3×100×200 (the literal 3×200×100 is a transposition; the
    "2× the grid" clause is the operative spec). All models + baseline + truth are
    evaluated at the SAME resolution H100×W200 (truth = 400×200 frame bilinear-resized).
  - Data quirk: pairs-manifest.json lists frame0000.png which does not exist on disk
    (ffmpeg 1-index). Train = pairs 1–39 (39 pairs), held-out = 40–49 (10 pairs).

Usage:
  python experiments/av1_train.py --stage all --out results/av1
"""
import argparse, json, math, time, traceback
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image, ImageDraw, ImageFont

RAMP = " .:-=+*#%@"          # 10 glyph ramp (charset verified == data)
VOCAB = len(RAMP) + 1        # +1 unknown slot (never occurs in data; kept per spec)
UNK = len(RAMP)
GRID_ROWS, GRID_COLS = 50, 100
OUT_H, OUT_W = GRID_ROWS * 2, GRID_COLS * 2        # 100 × 200 (H × W)
CELL_W, CELL_H = 4, 4                              # atlas cell at native 400×200
SS = 16                                            # atlas supersampling factor
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
]

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- data
def load_pairs(pairs_dir: Path):
    """manifest-driven; returns list of dicts sorted by index (skips missing files)."""
    man = json.loads((pairs_dir / "pairs-manifest.json").read_text())
    char_to_idx = {c: i for i, c in enumerate(RAMP)}
    out = []
    for fr in man["frames"]:
        ap, fp = pairs_dir / fr["ascii"], pairs_dir / fr["frame"]
        if not fp.exists():
            print(f"[data] skip pair {fr['i']}: frame missing ({fr['frame']}) — ffmpeg 1-index quirk")
            continue
        lines = ap.read_text().rstrip("\n").split("\n")
        assert len(lines) == GRID_ROWS and all(len(l) == GRID_COLS for l in lines), fr["ascii"]
        g = torch.zeros(GRID_ROWS, GRID_COLS, dtype=torch.long)
        for r, line in enumerate(lines):
            for c, ch in enumerate(line):
                g[r, c] = char_to_idx.get(ch, UNK)
        lum = g.float() / len(RAMP)                 # char index / ramp len (per spec)
        img = Image.open(fp).convert("RGB").resize((OUT_W, OUT_H), Image.BILINEAR)
        import numpy as np
        frame = torch.from_numpy(np.asarray(img, dtype=np.float32) / 255.0).permute(2, 0, 1)
        out.append({"i": fr["i"], "glyph": g, "lum": lum, "frame": frame})
    out.sort(key=lambda d: d["i"])
    return out


# ---------------------------------------------------------------- baseline A (honest floor)
def build_atlas(device):
    """Pre-rasterize the 10 ramp glyphs with PIL (supersampled), return (V, CELL_H*SS, CELL_W*SS)."""
    font_path = next((p for p in FONT_CANDIDATES if Path(p).exists()), None)
    ch, cw = CELL_H * SS, CELL_W * SS               # 64 × 64 supersampled cell
    if font_path:
        font = ImageFont.truetype(font_path, int(ch * 0.94))
    else:
        font = ImageFont.load_default(size=int(ch * 0.94))
    atlas = torch.zeros(VOCAB, ch, cw)
    for i, c in enumerate(RAMP):
        if c == " ":
            continue
        im = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(im).text((cw // 2, ch // 2), c, fill=255, font=font, anchor="mm")
        import numpy as np
        atlas[i] = torch.from_numpy(np.asarray(im, dtype=np.float32) / 255.0)
    atlas = F.avg_pool2d(atlas[None], SS)[0]         # → (V, CELL_H, CELL_W), antialiased
    return atlas.to(device)


def render_atlas(glyph, lum, atlas):
    """Pure-torch compositing: block = atlas[glyph] * cell_luminance. (N,·,50,100) → (N,1,H,W)."""
    blocks = atlas[glyph] * lum[..., None, None]    # (N,R,C,CELL_H,CELL_W)
    n = blocks.shape[0]
    img = blocks.permute(0, 1, 3, 2, 4).reshape(n, 1, GRID_ROWS * CELL_H, GRID_COLS * CELL_W)
    return F.avg_pool2d(img, 2)                     # native 200H×400W → eval res 100H×200W


# ---------------------------------------------------------------- model B
class GlyphDecoder(nn.Module):
    """embed(glyph,32) + luminance → conv stack → PixelShuffle(2) → RGB sigmoid."""

    def __init__(self):
        super().__init__()
        self.embed = nn.Embedding(VOCAB, 32)
        self.pre = nn.Sequential(
            nn.Conv2d(33, 128, 3, padding=1), nn.GELU(),
            nn.Conv2d(128, 128, 3, padding=1), nn.GELU(),
            nn.Conv2d(128, 128, 3, padding=1), nn.GELU(),
            nn.Conv2d(128, 256, 3, padding=1), nn.GELU(),
        )
        self.post = nn.Sequential(                   # operates at 2× (after PixelShuffle)
            nn.Conv2d(64, 64, 3, padding=1), nn.GELU(),
            nn.Conv2d(64, 3, 3, padding=1),
        )
        self.ps = nn.PixelShuffle(2)                 # 256ch @50×100 → 64ch @100×200

    def forward(self, glyph, lum):
        x = torch.cat([self.embed(glyph).permute(0, 3, 1, 2), lum[:, None]], dim=1)
        x = self.pre(x)
        x = self.ps(x)
        return torch.sigmoid(self.post(x))           # (N,3,OUT_H,OUT_W)


# ---------------------------------------------------------------- metrics
def psnr(a, b):
    """PSNR in dB on [0,1] tensors: 10·log10(1/MSE)."""
    mse = F.mse_loss(a, b).item()
    return 99.0 if mse <= 1e-12 else 10.0 * math.log10(1.0 / mse)


def _gauss_kernel(win=7, sigma=1.5, device="cpu"):
    coords = torch.arange(win, dtype=torch.float32, device=device) - win // 2
    g = torch.exp(-(coords ** 2) / (2 * sigma ** 2))
    g = (g / g.sum())
    k = torch.outer(g, g)
    return k[None, None].expand(3, 1, win, win).contiguous()


def ssim(x, y, win=7):
    """SSIM — Wang, Simoncelli, Bovik, 'Image quality assessment: from error
    visibility to structural similarity', IEEE TIP 2004:
        SSIM(x,y) = ((2μxμy + C1)(2σxy + C2)) / ((μx² + μy² + C1)(σx² + σy² + C2))
    7×7 Gaussian window (σ=1.5), C1=0.01², C2=0.03², per-channel then averaged.
    """
    device = x.device
    k = _gauss_kernel(win, 1.5, device)
    pad = win // 2
    x, y = x[None], y[None]
    mx = F.conv2d(x, k, padding=pad, groups=3)
    my = F.conv2d(y, k, padding=pad, groups=3)
    mxx, myy, mxy = mx * mx, my * my, mx * my
    vxx = F.conv2d(x * x, k, padding=pad, groups=3) - mxx
    vyy = F.conv2d(y * y, k, padding=pad, groups=3) - myy
    vxy = F.conv2d(x * y, k, padding=pad, groups=3) - mxy
    C1, C2 = 0.01 ** 2, 0.03 ** 2
    num = (2 * mx * my + C1) * (2 * vxy + C2)
    den = (mxx + myy + C1) * (vxx + vyy + C2)
    return ((num / den).mean()).item()


class Divergence(Exception):
    pass


# ---------------------------------------------------------------- training
def train_model(pairs, device, mode, epochs, lr, batch=8, lambda_t=0.5, tag="run"):
    """mode='frame' → L1(frame); mode='temporal' → L1 + λ_t·L1(Δout, Δframe).
    Plateau rule (frozen): stop after 20 consecutive epochs with <1% improvement
    vs the best of the previous 20 epochs. NaN/explosion → Divergence (caller
    retries once at lr/2, then INCONCLUSIVE — never more)."""
    torch.manual_seed(0)
    model = GlyphDecoder().to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[{tag}] params: {n_params:,} ({n_params/1e6:.3f}M) — limit <5M: {'OK' if n_params < 5e6 else 'VIOLATION'}")
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    frames = torch.stack([p["frame"] for p in pairs]).to(device)
    glyphs = torch.stack([p["glyph"] for p in pairs]).to(device)
    lums = torch.stack([p["lum"] for p in pairs]).to(device)
    n = len(pairs)
    hist, plateau, t0 = [], 0, time.time()
    for ep in range(1, epochs + 1):
        model.train()
        ep_loss, nb = 0.0, 0
        # frame pass (sequential batches — order is temporal; keeps runs symmetric)
        for s in range(0, n, batch):
            idx = torch.arange(s, min(s + batch, n), device=device)
            out = model(glyphs[idx], lums[idx])
            loss = F.l1_loss(out, frames[idx])
            opt.zero_grad(); loss.backward(); opt.step()
            ep_loss += loss.item(); nb += 1
        # temporal pass (run2 only): all consecutive pairs, chunks of 8 pairs
        if mode == "temporal":
            starts = list(range(0, n - 1, 8))
            for s in starts:
                a = torch.arange(s, min(s + 8, n - 1), device=device)
                b = a + 1
                g2 = torch.cat([glyphs[a], glyphs[b]]); l2 = torch.cat([lums[a], lums[b]])
                f2 = torch.cat([frames[a], frames[b]])
                out = model(g2, l2)
                d_out = out[len(a):] - out[: len(a)]
                d_fr = f2[len(a):] - f2[: len(a)]
                loss = lambda_t * F.l1_loss(d_out, d_fr)
                opt.zero_grad(); loss.backward(); opt.step()
                ep_loss += loss.item(); nb += 1
        ml = ep_loss / nb
        if not math.isfinite(ml) or ml > 1e3:
            raise Divergence(f"epoch {ep}: loss={ml}")
        hist.append(ml)
        if ep % 10 == 0 or ep == 1:
            print(f"[{tag}] epoch {ep:4d}  loss {ml:.6f}  ({time.time()-t0:.1f}s)")
        if len(hist) > 20:
            best_prev = min(hist[-21:-1])
            if ml > 0.99 * best_prev:
                plateau += 1
            else:
                plateau = 0
            if plateau >= 20:
                print(f"[{tag}] plateau: <1% improvement over last 20 epochs (ep {ep}, loss {ml:.6f}) — stopping")
                break
    return model, n_params, len(hist), hist[-1], time.time() - t0


@torch.no_grad()
def eval_set(render_fn, heldout, device):
    """PSNR/SSIM per-frame + temporal coherence on consecutive held-out pairs."""
    psnrs, ssims = [], []
    gens = [render_fn(p) for p in heldout]
    for p, g in zip(heldout, gens):
        psnrs.append(psnr(g, p["frame"].to(device)))
        ssims.append(ssim(g, p["frame"].to(device)))
    raw_gen = raw_truth = coh = 0.0
    for j in range(len(heldout) - 1):
        dg = gens[j + 1] - gens[j]
        dt = heldout[j + 1]["frame"].to(device) - heldout[j]["frame"].to(device)
        raw_gen += dg.abs().mean().item()
        raw_truth += dt.abs().mean().item()
        coh += F.l1_loss(dg, dt).item()
    m = max(len(heldout) - 1, 1)
    return {"psnr": sum(psnrs) / len(psnrs), "ssim": sum(ssims) / len(ssims),
            "dl1_gen": raw_gen / m, "dl1_truth": raw_truth / m, "dl1_coh": coh / m}


# ---------------------------------------------------------------- warm-up D
def warmup_ddpm(out_dir):
    rec = {"stage": "D-warmup"}
    try:
        import os
        os.environ.setdefault("HF_HUB_OFFLINE", "0")
        from diffusers import DDIMPipeline, DDIMScheduler
        pipe = DDIMPipeline.from_pretrained("google/ddpm-cifar10-32")
        pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)
        pipe = pipe.to("cuda")
        gen = torch.Generator("cuda").manual_seed(0)
        torch.cuda.synchronize(); t0 = time.time()
        imgs = pipe(batch_size=8, num_inference_steps=8, generator=gen).images
        torch.cuda.synchronize(); dt = time.time() - t0
        rec.update(ok=True, steps=8, images=8, seconds=dt, it_per_s=8 / dt,
                   device=torch.cuda.get_device_name(0))
        W, H = imgs[0].size
        grid = Image.new("RGB", (W * 4, H * 2))
        for k, im in enumerate(imgs):
            grid.paste(im, ((k % 4) * W, (k // 4) * H))
        grid.save(out_dir / "ddpm_warmup.png")
        print(f"[D] warm-up OK: 8 imgs × 8 DDIM steps in {dt:.1f}s → {8/dt:.2f} it/s")
    except Exception as e:
        rec.update(ok=False, blocked=str(e)[:500], traceback=traceback.format_exc()[-800:])
        print(f"[D] warm-up BLOCKED: {e}")
    return rec


# ---------------------------------------------------------------- samples grid
@torch.no_grad()
def save_samples(heldout, atlas, runs, out_path):
    picks = [heldout[0], heldout[len(heldout) // 2], heldout[-1]]
    scale = 2
    cols = []
    for p in picks:
        row = [render_atlas(p["glyph"][None].cuda(), p["lum"][None].cuda(), atlas)[0].repeat(3, 1, 1)]
        for _, fn in runs:
            row.append(fn(p))
        row.append(p["frame"].cuda())
        cols.append(row)
    import numpy as np
    H, W = OUT_H * scale, OUT_W * scale
    canvas = Image.new("RGB", (W * 4, H * len(picks)))
    for r, row in enumerate(cols):
        labels = ["A atlas", "B run1", "B run2", "truth"]
        for c, t in enumerate(row):
            arr = (t.clamp(0, 1).cpu().numpy().transpose(1, 2, 0) * 255).astype(np.uint8)
            im = Image.fromarray(arr).resize((W, H), Image.NEAREST)
            canvas.paste(im, (c * W, r * H))
    canvas.save(out_path)
    print(f"[samples] {out_path} ({len(picks)}×4 grid: A | run1 | run2 | truth)")


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["all", "warmup", "train"])
    ap.add_argument("--pairs", default=str(ROOT / "results/av1/pairs-hero"))
    ap.add_argument("--out", default=str(ROOT / "results/av1"))
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--lambda-t", type=float, default=0.5)
    a = ap.parse_args()
    out_dir = ROOT / a.out
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    assert device.type == "cuda", "pre-reg compute budget requires the 4050"
    print(f"[env] torch {torch.__version__} on {torch.cuda.get_device_name(0)}")

    t_wall = time.time()
    pairs = load_pairs(Path(a.pairs))
    train_pairs = [p for p in pairs if p["i"] <= 39]
    heldout = [p for p in pairs if p["i"] >= 40]
    print(f"[data] usable pairs: {len(pairs)} (train {len(train_pairs)} idx "
          f"{train_pairs[0]['i']}–{train_pairs[-1]['i']}, held-out {len(heldout)} idx "
          f"{heldout[0]['i']}–{heldout[-1]['i']})")

    atlas = build_atlas(device)
    metrics = {}
    receipt = {
        "schema": "av1-receipt/v1", "pre_reg": "proposals/runs/AV1-ascii-to-video.md (frozen)",
        "config": vars(a) | {"device": torch.cuda.get_device_name(0), "torch": torch.__version__,
                             "seed": 0, "fp": "fp32"},
        "data_notes": [
            "pair0 frame missing on disk (manifest lists frame0000.png; ffmpeg 1-index) — train = pairs 1–39",
            "eval resolution H100×W200 for ALL of A/run1/run2/truth (2× grid; truth bilinear-resized from 400×200)",
            "atlas cell 4×4 (task's 4×10 arithmetic gives 400×500 ≠ 400×200; corrected, supersampled ×16)",
            "ΔL1 metrics: dl1_gen=mean|Δgen|, dl1_truth=mean|Δtruth|, dl1_coh=L1(Δgen,Δtruth) — coh is the H2 metric",
        ],
        "timings": {},
    }

    # ---- baseline A
    tA = time.time()
    metrics["A"] = eval_set(lambda p: render_atlas(p["glyph"][None].to(device),
                                                   p["lum"][None].to(device), atlas)[0]
                            .repeat(3, 1, 1), heldout, device)
    receipt["timings"]["baseline_A_s"] = round(time.time() - tA, 2)
    print(f"[A] atlas: PSNR {metrics['A']['psnr']:.2f} dB  SSIM {metrics['A']['ssim']:.4f}  "
          f"coh {metrics['A']['dl1_coh']:.5f}  raw|Δ| gen {metrics['A']['dl1_gen']:.5f} truth {metrics['A']['dl1_truth']:.5f}")

    # ---- warm-up D
    if a.stage in ("all", "warmup"):
        tD = time.time()
        receipt["warmup_D"] = warmup_ddpm(out_dir)
        receipt["timings"]["warmup_D_s"] = round(time.time() - tD, 2)

    if a.stage in ("all", "train"):
        # ---- RUN 1 (H1): frame loss only
        runs = {}
        for run_id, mode, lr in (("run1", "frame", a.lr), ("run2", "temporal", a.lr)):
            cap = a.epochs if (run_id == "run1" or runs.get("run1", {}).get("diverged")) \
                else runs["run1"]["epochs"]  # matched compute: run2 budget = run1's achieved epochs
            try:
                t0 = time.time()
                model, npar, eps, final, secs = train_model(
                    train_pairs, device, mode, cap, lr, a.batch, a.lambda_t, tag=run_id)
                diverged = False
            except Divergence as e:
                print(f"[{run_id}] DIVERGED at lr={lr}: {e} — retry ONCE at 1e-3 (per honesty rule)")
                try:
                    t0 = time.time()
                    model, npar, eps, final, secs = train_model(
                        train_pairs, device, mode, cap, 1e-3, a.batch, a.lambda_t, tag=run_id + "-retry")
                    diverged = False
                except Divergence as e2:
                    print(f"[{run_id}] diverged again at 1e-3 → INCONCLUSIVE branch")
                    model, npar, eps, final, secs, diverged = None, None, 0, float("nan"), 0.0, True
            runs[run_id] = {"model": model, "params": npar, "epochs": eps, "final_loss": final,
                            "seconds": secs, "diverged": diverged, "lr": lr, "mode": mode}
            receipt["timings"][f"{run_id}_s"] = round(time.time() - t0, 2)
            if diverged:
                continue
            fn = lambda p: model(p["glyph"][None].to(device), p["lum"][None].to(device))[0]
            metrics[run_id] = eval_set(fn, heldout, device)
            m = metrics[run_id]
            print(f"[{run_id}] {eps} epochs, final train loss {final:.6f} ({secs:.1f}s) → "
                  f"PSNR {m['psnr']:.2f}  SSIM {m['ssim']:.4f}  coh {m['dl1_coh']:.5f}  "
                  f"raw|Δ| {m['dl1_gen']:.5f}")
            torch.save(model.state_dict(), out_dir / f"av1-{run_id}.pt")

        # ---- verdicts (frozen bars)
        verd = {}
        if runs["run1"]["diverged"]:
            verd["H1"] = "INCONCLUSIVE (diverged twice)"
        else:
            d = metrics["run1"]["psnr"] - metrics["A"]["psnr"]
            verd["H1"] = f"{'KEEP' if d >= 1.5 else 'KILL'} (ΔPSNR vs A = {d:+.2f} dB, bar ≥ +1.5 dB)"
        if runs["run2"]["diverged"]:
            verd["H2"] = "INCONCLUSIVE (diverged twice)"
        elif runs["run1"]["diverged"]:
            verd["H2"] = "INCONCLUSIVE (run1 diverged — no matched reference)"
        else:
            rel = (metrics["run1"]["dl1_coh"] - metrics["run2"]["dl1_coh"]) / metrics["run1"]["dl1_coh"]
            dpsnr = metrics["run1"]["psnr"] - metrics["run2"]["psnr"]
            ok = rel >= 0.10 and dpsnr <= 0.5
            verd["H2"] = (f"{'KEEP' if ok else 'KILL'} (ΔL1 coh ↓ {rel*100:.1f}% (bar ≥10%), "
                          f"PSNR drop {dpsnr:.2f} dB (bar ≤0.5))")
        print("[verdicts]", *verd.items(), sep="\n  ")

        # ---- samples + receipt
        live = [(rid, lambda p, mdl=runs[rid]["model"]: mdl(p["glyph"][None].to(device),
                                                            p["lum"][None].to(device))[0])
                for rid in ("run1", "run2") if not runs[rid]["diverged"]]
        save_samples(heldout, atlas, live, out_dir / "av1-samples.png")

        receipt["params"] = {rid: runs[rid]["params"] for rid in runs}
        def _san(o):
            return None if isinstance(o, float) and not math.isfinite(o) else o
        receipt["runs"] = {rid: {k: _san(runs[rid][k]) for k in ("epochs", "final_loss", "lr", "mode",
                                                               "seconds", "diverged")} for rid in runs}
        receipt["metrics"] = {k: {kk: round(vv, 6) for kk, vv in v.items()} for k, v in metrics.items()}
        receipt["verdicts"] = verd
        receipt["wall_s"] = round(time.time() - t_wall, 1)
        (out_dir / "av1-receipt.json").write_text(json.dumps(receipt, indent=1))
        print(f"[land] receipt → {out_dir/'av1-receipt.json'}  wall {receipt['wall_s']}s")


if __name__ == "__main__":
    main()
