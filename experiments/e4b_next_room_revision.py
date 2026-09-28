"""E4b — next-room revision: fix E4's DATASET, keep the 68k-param harness.

E4 (RESULTS.md) was downgraded INCONCLUSIVE: 24 cells / 4 heldout windows
cannot separate signal from 'predict the last room always' — the tail split
put a single room in heldout, so the constant-predictor scored 0.75 without
reading trajectory at all. The harness worked; the dataset didn't. This
revision changes the dataset four ways and keeps the model identical to E4
for comparability:

  1. longer clips: 60 s @ 10 fps -> ~59 cells/room, ~236 cells (4 rooms)
     (E4 had 6 s clips, 24 cells total)
  2. interleaved walk: cells are traversed in seeded random runs (3..9
     cells per room visit), so room transitions are spread through the
     whole trajectory instead of one-room-at-a-time
  3. blocked split: 10 contiguous cell-blocks of the walk, 2 of 10 held
     out by TARGET cell-block (all rooms asserted present on both sides),
     not the temporal tail
  4. baselines reported alongside: constant-predictor AND markov-1
     (train transition counts, argmax per current room, majority fallback)

Verdict (full pass, pre-registered): with best = max(constant, markov1),
  KEEP          iff heldout_acc > best + 0.05
  KILL          iff heldout_acc <= best   (model fails to beat trivial
                predictors on a walk with learnable structure)
  INCONCLUSIVE  otherwise (in the margin band)
SMOKE (default): 2 rooms, 12 s clips, ~38 cells, 1 epoch — pipeline proof
only; verdict forced INCONCLUSIVE regardless of numbers (a 1-epoch run can
neither KEEP nor KILL the hypothesis, only prove the loop runs).
FULL (E4B_FULL=1): 4 rooms, 60 s clips, ~236 cells, 120 epochs — minutes
on the RTX 4050.

Guard policy (same floor/ceil as guard.py): preflight refuses if free VRAM
< 1024 MiB or temp > 80 C. Any crash: ONE JSON with verdict ABORTED, exit 0
(failures are data). Determinism: seed 2718 everywhere, no shuffle leak
(split fixed before training; only the train loader shuffles).
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "experiments"))
from guard import FREE_FLOOR_MIB, TEMP_CEIL_C, sample  # noqa: E402
from common import ppms_from_lavfi, to_glyph, frame_features, window_obs  # noqa: E402

SEED = 2718
CTX = 8                          # context cells -> predict room of cell CTX+1
D_MODEL, N_HEADS, N_LAYERS = 64, 4, 2
LR, BATCH = 1e-3, 32
PREREG_MARGIN = 0.05
MIN_RUN, MAX_RUN = 3, 9          # walk run-lengths: cells per room visit
N_BLOCKS = 10                    # blocked-split granularity (2 of 10 held out)
SOURCES = [("still-solid", "color=c=gray:duration={sec}:size=160x90:rate=10"),
           ("moving-testsrc", "testsrc=duration={sec}:size=160x90:rate=10"),
           ("smpte", "smptebars=duration={sec}:size=160x90:rate=10"),
           ("moving-testsrc2", "testsrc2=duration={sec}:size=160x90:rate=10")]
MODES = {"smoke": {"rooms": 2, "seconds": 12, "fps": 10, "cell_window": 6, "epochs": 1},
         "full": {"rooms": 4, "seconds": 60, "fps": 10, "cell_window": 10, "epochs": 120}}


class TinyRoomformer(nn.Module):
    """Identical to E4's harness model (68k params) for comparability."""

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


def preflight() -> tuple[bool, str | None, tuple[int, int] | None]:
    free, temp = sample()
    if free is None:
        return False, "preflight: nvidia-smi unavailable", None
    if free < FREE_FLOOR_MIB:
        return False, f"preflight: free VRAM {free} MiB < {FREE_FLOOR_MIB}", (free, temp)
    if temp is not None and temp > TEMP_CEIL_C:
        return False, f"preflight: temp {temp} C > {TEMP_CEIL_C}", (free, temp)
    return True, None, (free, temp)


def build_cells(cfg: dict) -> tuple[list[np.ndarray], list[str]]:
    """60s-style lavfi clips -> per-room cell embeddings (window_obs rows)."""
    cells_per_room, room_names = [], []
    for name, tmpl in SOURCES[:cfg["rooms"]]:
        frames = to_glyph(ppms_from_lavfi(tmpl.format(sec=cfg["seconds"]),
                                          cfg["seconds"], cfg["fps"], (160, 90)))
        cells = window_obs(frame_features(frames), cfg["cell_window"]).astype(np.float32)
        assert len(cells) >= 2, f"{name}: {len(cells)} cells is too few for a walk"
        cells_per_room.append(cells)
        room_names.append(name)
        print(f"[e4b] {name}: {frames.shape[0]} frames -> {len(cells)} cells "
              f"(window={cfg['cell_window']})")
    return cells_per_room, room_names


def build_walk(cells_per_room: list[np.ndarray], rng: np.random.Generator
               ) -> tuple[np.ndarray, np.ndarray]:
    """Interleaved walk: seeded random runs (MIN_RUN..MAX_RUN cells) per visit,
    visiting rooms in per-round random order. Every cell used exactly once."""
    walk_cells, walk_labels = [], []
    cursor = [0] * len(cells_per_room)
    remaining = sum(len(c) for c in cells_per_room)
    while remaining > 0:
        for ri in rng.permutation(len(cells_per_room)):
            avail = len(cells_per_room[ri]) - cursor[ri]
            if avail <= 0:
                continue
            take = int(min(int(rng.integers(MIN_RUN, MAX_RUN + 1)), avail))
            walk_cells.append(cells_per_room[ri][cursor[ri]:cursor[ri] + take])
            walk_labels.append(np.full(take, ri, np.int64))
            cursor[ri] += take
            remaining -= take
    X = np.concatenate(walk_cells)      # (n_walk, d_feat)
    y = np.concatenate(walk_labels)     # (n_walk,)
    transitions = int((y[1:] != y[:-1]).sum())
    print(f"[e4b] walk: {len(y)} cells, {transitions} room transitions "
          f"(interleaved runs of {MIN_RUN}..{MAX_RUN})")
    return X, y


def blocked_split(y: np.ndarray, n_rooms: int, rng: np.random.Generator
                  ) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """Sliding windows over the walk; split by TARGET cell-block, 2 of 10
    contiguous blocks held out. Retry (seeded) until both sides see every
    room and the heldout side has enough windows to mean anything."""
    n_walk = len(y)
    n_windows = n_walk - CTX
    block_of = np.minimum(np.arange(n_walk) * N_BLOCKS // n_walk, N_BLOCKS - 1)
    for _ in range(50):
        heldout_blocks = sorted(rng.choice(N_BLOCKS, size=2, replace=False).tolist())
        he = np.array([block_of[i + CTX] in heldout_blocks for i in range(n_windows)])
        tr = ~he
        if (he.sum() >= 4 and tr.sum() >= n_windows // 2
                and len(np.unique(y[CTX:][he])) == n_rooms
                and len(np.unique(y[CTX:][tr])) == n_rooms):
            return tr, he, heldout_blocks
    raise RuntimeError(f"no valid blocked split in 50 tries (n_windows={n_windows})")


def constant_baseline(t_tr: np.ndarray, t_he: np.ndarray) -> float:
    vals, counts = np.unique(t_tr, return_counts=True)
    return float((t_he == vals[counts.argmax()]).mean())


def markov1_baseline(cur_tr: np.ndarray, nxt_tr: np.ndarray,
                     cur_he: np.ndarray, t_he: np.ndarray, n_rooms: int) -> float:
    """Train transition counts cur->next, argmax per current room; unseen
    current rooms fall back to the train-global majority next-room."""
    counts = np.zeros((n_rooms, n_rooms), np.int64)
    for c, n in zip(cur_tr, nxt_tr):
        counts[c, n] += 1
    vals, cts = np.unique(nxt_tr, return_counts=True)
    global_maj = int(vals[cts.argmax()])
    table = np.full(n_rooms, global_maj, np.int64)
    for r in range(n_rooms):
        if counts[r].sum() > 0:
            table[r] = int(counts[r].argmax())
    return float((table[cur_he] == t_he).mean())


def main() -> dict:
    t_start = time.time()
    mode = "full" if os.environ.get("E4B_FULL") == "1" else "smoke"
    cfg = MODES[mode]
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    rng = np.random.default_rng(SEED)

    ok, breach, gv = preflight()
    if not ok:
        return finish({"experiment": "E4b next-room-revision", "mode": mode,
                       "device": dev, "seed": SEED, "verdict": "ABORTED",
                       "reason": breach,
                       "guard": {"free_mib": gv[0], "temp_c": gv[1]}})

    cells_per_room, room_names = build_cells(cfg)
    X, y = build_walk(cells_per_room, rng)
    n_rooms = len(room_names)
    if len(y) < CTX + 8:
        return finish({"experiment": "E4b next-room-revision", "mode": mode,
                       "device": dev, "seed": SEED, "verdict": "ABORTED",
                       "reason": f"walk too short: {len(y)} cells < CTX+8"})

    # label-free standardization (per-feature z-score over all cells)
    mu, sd = X.mean(0), X.std(0) + 1e-6
    Xz = (X - mu) / sd

    # windows: context Xz[i:i+CTX] -> target room y[i+CTX]
    n_windows = len(y) - CTX
    W = np.stack([Xz[i:i + CTX] for i in range(n_windows)]).astype(np.float32)
    T = y[CTX:]
    tr, he, heldout_blocks = blocked_split(y, n_rooms, rng)
    Wtr, Ttr = torch.tensor(W[tr]), torch.tensor(T[tr])
    Whe, The = torch.tensor(W[he]), torch.tensor(T[he])
    tr_idx, he_idx = np.where(tr)[0], np.where(he)[0]
    cur_tr = y[tr_idx + CTX - 1]   # current room = last context cell's room
    cur_he = y[he_idx + CTX - 1]
    print(f"[e4b] split: {int(tr.sum())} train / {int(he.sum())} heldout windows "
          f"(heldout cell-blocks {heldout_blocks} of {N_BLOCKS})")

    base_const = constant_baseline(T[tr], T[he])
    base_mk1 = markov1_baseline(cur_tr, T[tr], cur_he, T[he], n_rooms)
    print(f"[e4b] baselines: constant {base_const:.3f}  markov-1 {base_mk1:.3f}")

    model = TinyRoomformer(Xz.shape[1], n_rooms).to(dev)
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    lossf = nn.CrossEntropyLoss()
    for _ in range(cfg["epochs"]):
        model.train()
        perm = torch.randperm(len(Wtr))
        for i in range(0, len(perm), BATCH):
            b = perm[i:i + BATCH]
            opt.zero_grad()
            loss = lossf(model(Wtr[b].to(dev)), Ttr[b].to(dev))
            loss.backward()
            opt.step()
    if dev == "cuda":
        torch.cuda.empty_cache()

    model.eval()
    with torch.no_grad():
        pred_he = model(Whe.to(dev)).argmax(-1).cpu().numpy()
        pred_tr = model(Wtr.to(dev)).argmax(-1).cpu().numpy()
    acc_he = float((pred_he == T[he]).mean())
    acc_tr = float((pred_tr == T[tr]).mean())
    print(f"[e4b] model: train {acc_tr:.3f}  heldout {acc_he:.3f}")

    best = max(base_const, base_mk1)
    if mode == "smoke":
        verdict = "INCONCLUSIVE"
    elif acc_he > best + PREREG_MARGIN:
        verdict = "KEEP"
    elif acc_he <= best:
        verdict = "KILL"
    else:
        verdict = "INCONCLUSIVE"

    out = {
        "experiment": "E4b next-room-revision", "mode": mode, "device": dev,
        "seed": SEED, "params": n_params, "rooms": room_names,
        "cells": int(len(y)), "cells_per_room": [int(len(c)) for c in cells_per_room],
        "walk": {"length": int(len(y)),
                 "room_transitions": int((y[1:] != y[:-1]).sum()),
                 "run_lengths": f"{MIN_RUN}..{MAX_RUN} (seeded random)"},
        "split": {"train_windows": int(tr.sum()), "heldout_windows": int(he.sum()),
                  "rule": f"blocked: {N_BLOCKS} contiguous cell-blocks, "
                          f"{heldout_blocks} held out by target cell"},
        "train_acc": round(acc_tr, 3),
        "heldout_acc": round(acc_he, 3),
        "constant_baseline": round(base_const, 3),
        "markov1_baseline": round(base_mk1, 3),
        "best_baseline": round(best, 3),
        "preregistered_margin": PREREG_MARGIN,
        "wall_seconds": round(time.time() - t_start, 1),
        "verdict": verdict,
        "note": (
            "SMOKE numbers are pipeline proof only (verdict forced INCONCLUSIVE). "
            "FULL-SCALE RECIPE (E4B_FULL=1): " + ", ".join(
                f"{k}={v}" for k, v in MODES["full"].items()) +
            f"; 4 rooms x ~59 cells = ~236 cells, interleaved walk "
            f"(runs of {MIN_RUN}..{MAX_RUN}), blocked split (2 of 10 cell-blocks "
            "held out by target), constant+markov-1 baselines, KEEP iff "
            "heldout > max(baselines) + 0.05; ~minutes on the RTX 4050; "
            "run via runner.py guard. Other lanes contend: preflight floor "
            f"{FREE_FLOOR_MIB} MiB free / {TEMP_CEIL_C} C."),
    }
    return finish(out)


def finish(out: dict) -> dict:
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    try:
        main()
    except Exception:
        finish({"experiment": "E4b next-room-revision", "seed": SEED,
                "verdict": "ABORTED", "reason": traceback.format_exc(limit=4)})
