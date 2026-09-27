"""E4 — next-room transformer: can a tiny model predict the room ahead?

The JEV-temporal probe: room cells (normalized vMF mean directions from
real frames, the QUILT-CELL-LOG shape) arranged as a walk across four
clips — still-solid -> moving-testsrc -> smpte -> moving-testsrc2 — so
real room transitions exist in the data. A <2M-param transformer sees
the last 8 cell embeddings and predicts the NEXT room's class (4-way).
Held-out evaluation against a majority-class baseline. If a model this
small reads room-trajectory structure, the "agent carries room-state in
context" thesis has a floor.

Determinism: fixed seed 2718, fixed walk order, fixed split (last 20%
of windows held out, no shuffle leak).
"""
from __future__ import annotations

import json
import sys

import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, "/home/eileen/projects/tessera/seeds/glyph-sense")
sys.path.insert(0, "/home/eileen/projects/tessera/lab")
sys.path.insert(0, "/home/eileen/projects/elephant")
from glyph_sense_real import decode_ppm_frames, to_glyph_frames, fit_room, zmatrix  # noqa: E402
from glyph_rooms import frame_features, windowed_readings  # noqa: E402

SEED = 2718
WALK = [("still-solid", "color=c=gray:duration=6:size=160x90:rate=10"),
        ("moving-testsrc", "testsrc=duration=6:size=160x90:rate=10"),
        ("smpte", "smptebars=duration=6:size=160x90:rate=10"),
        ("moving-testsrc2", "testsrc2=duration=6:size=160x90:rate=10")]
CTX = 8
D_MODEL, N_HEADS, N_LAYERS = 64, 4, 2


class TinyRoomformer(nn.Module):
    def __init__(self, d_in, n_rooms, d=D_MODEL, heads=N_HEADS, layers=N_LAYERS):
        super().__init__()
        self.proj = nn.Linear(d_in, d)
        self.pos = nn.Parameter(torch.randn(CTX, d) * 0.02)
        enc = nn.TransformerEncoderLayer(d, heads, d * 2, dropout=0.0,
                                         batch_first=True, norm_first=True)
        self.enc = nn.TransformerEncoder(enc, layers)
        self.head = nn.Linear(d, n_rooms)

    def forward(self, x):  # x: (B, CTX, d_in)
        h = self.enc(self.proj(x) + self.pos)
        return self.head(h[:, -1])


def main() -> dict:
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    cells, labels, room_names = [], [], []
    for ri, (name, src) in enumerate(WALK):
        ppms = decode_ppm_frames(["-f", "lavfi", "-i", src])
        feat = frame_features(to_glyph_frames(ppms))
        ro, _ = windowed_readings(feat, step=1)
        Z = zmatrix(ro)
        # batch fits over 10-window groups -> cell embeddings (the log shape)
        n = len(Z) // 10 * 10
        for i in range(0, n, 10):
            f, _ = fit_room(ro[i:i + 10])
            if f is None:
                continue
            mu = np.asarray(f["mu_hat"], np.float32)
            cells.append(mu / (np.linalg.norm(mu) + 1e-9))
            labels.append(ri)
        room_names.append(name)
    X = np.asarray(cells, np.float32)
    y = np.asarray(labels)
    print(f"[e4] walk: {len(X)} cells, rooms={room_names}")

    # sliding windows -> next-room label
    W, T = [], []
    for i in range(len(X) - CTX):
        W.append(X[i:i + CTX])
        T.append(y[i + CTX])
    W = np.asarray(W, np.float32)
    T = np.asarray(T)
    split = int(len(W) * 0.8)
    Wtr, Ttr = torch.tensor(W[:split]), torch.tensor(T[:split])
    Whe, The = torch.tensor(W[split:]), torch.tensor(T[split:])
    print(f"[e4] {split} train windows, {len(Whe)} heldout")

    n_rooms = len(room_names)
    model = TinyRoomformer(X.shape[1], n_rooms).to(dev)
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    lossf = nn.CrossEntropyLoss()
    for ep in range(120):
        model.train()
        perm = torch.randperm(len(Wtr))
        for i in range(0, len(perm), 32):
            b = perm[i:i + 32]
            opt.zero_grad()
            loss = lossf(model(Wtr[b].to(dev)), Ttr[b].to(dev))
            loss.backward()
            opt.step()
    if dev == "cuda":
        torch.cuda.empty_cache()

    model.eval()
    with torch.no_grad():
        pred = model(Whe.to(dev)).argmax(-1).cpu()
    acc = float((pred == The).float().mean())
    # majority baseline on heldout
    vals, counts = np.unique(Ttr.numpy(), return_counts=True)
    maj = vals[counts.argmax()]
    base = float((The.numpy() == maj).mean())
    verdict = "KEEP" if acc > base + 0.05 else "INCONCLUSIVE"
    out = {
        "experiment": "E4 next-room transformer", "device": dev, "seed": SEED,
        "params": n_params, "rooms": room_names,
        "heldout_acc": round(acc, 3), "majority_baseline": round(base, 3),
        "verdict": verdict,
    }
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
