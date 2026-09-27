"""E1 — real-glyph-contrast: does the room encoder separate REAL frames?

Real ffmpeg lavfi frames (contrasting sources), 80x24 glyph rasters,
lab feature axes -> elephant's gpu.RoomEncoder (contrastive, tau=0.15,
spread guard) trained on 2 rooms with a held-out split. Metric:
centroid-margin separation (within-room cosine vs cross-room cosine)
on held-out obs, untrained baseline for the honest delta.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import torch

sys.path.insert(0, "/home/eileen/projects/quilt-gpu-lab/experiments")
from common import ppms_from_lavfi, to_glyph, frame_features, window_obs
from elephant_model import RoomEncoder, contrastive_loss, make_batches

SEED = 2718
SOURCES = [("still-solid", "color=c=gray:duration=12:size=160x90:rate=10"),
           ("moving-testsrc", "testsrc=duration=12:size=160x90:rate=10")]
SECONDS, FPS = 12, 10


def main() -> dict:
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.cuda.empty_cache() if dev == "cuda" else None

    rooms, obs = [], []
    for name, src in SOURCES:
        frames = to_glyph(ppms_from_lavfi(src, SECONDS, FPS, (160, 90)))
        rooms.append(name)
        obs.append(window_obs(frame_features(frames)))
        print(f"[e1] {name}: {frames.shape[0]} frames -> {obs[-1].shape[0]} window obs")

    # split: first 10 windows train, last 5 held out per room
    X, y = [], []
    for ri, o in enumerate(obs):
        for i, row in enumerate(o):
            X.append(row)
            y.append(ri)
    X = np.asarray(X, np.float32)
    y = np.asarray(y)
    train_mask = np.concatenate([np.tile([1]*10 + [0]*5, 1)])
    train_mask = np.array([1 if (i % 15) < 10 else 0 for i in range(len(X))])

    Xt = torch.tensor(X[train_mask == 1]); yt = torch.tensor(y[train_mask == 1])
    Xh = torch.tensor(X[train_mask == 0]); yh = torch.tensor(y[train_mask == 0])
    yt_np, yh_np = yt.numpy(), yh.numpy()

    def separations(model):
        model.eval()
        with torch.no_grad():
            zh = model(Xh.to(dev)).cpu().numpy()
            zt = model(Xt.to(dev)).cpu().numpy()
        def margin(z, yy):
            c = [z[yy == r].mean(0) for r in range(len(rooms))]
            c = [x / np.linalg.norm(x) for x in c]
            within = np.mean([np.dot(z[i], c[yy[i]]) for i in range(len(z))])
            cross = float(np.dot(c[0], c[1]))
            return within - cross, within, cross
        return margin(zh, yh_np), margin(zt, yt_np)

    # untrained baseline
    model = RoomEncoder(obs_dim=X.shape[1]).to(dev)
    (mh, _, _), (mt, _, _) = separations(model)
    base_held, base_train = mh, mt

    # train (small batches, few epochs — 6GB discipline)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    for ep in range(60):
        model.train()
        batches = make_batches(yt, rooms_per_batch=2, clips_per_room=8)
        if not batches:
            batches = [torch.randperm(len(yt))[:16]]
        for b in batches:
            opt.zero_grad()
            loss, _ = contrastive_loss(model(Xt[b].to(dev)), yt[b].to(dev))
            loss.backward()
            opt.step()
        if dev == "cuda":
            torch.cuda.empty_cache()
    (mh_t, wh_t, ch_t), (mt_t, _, _) = separations(model)
    gap = mh_t - base_held
    verdict = "KEEP" if gap > 0.05 else ("INCONCLUSIVE" if gap > 0 else "KILL")
    out = {
        "experiment": "E1 real-glyph-contrast", "device": dev, "seed": SEED,
        "rooms": rooms, "n_train": int(train_mask.sum()), "n_heldout": int((train_mask == 0).sum()),
        "heldout_margin_untrained": float(base_held),
        "heldout_margin_trained": float(mh_t),
        "heldout_gap": float(gap),
        "within_trained": float(wh_t), "cross_trained": float(ch_t),
        "verdict": verdict,
    }
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
