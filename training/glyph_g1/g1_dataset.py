#!/usr/bin/env python3
"""g1_dataset.py — G1 dataset builder: render 6,000 frames to V=32 renderer codes.

Per docs/glyph-predictor-spec-2026-09-28.md (the pre-registration):
- Feeds: 5 lavfi sources (c2_feed conventions) 60s x 10fps @ 320x240 = 3,000
  frames + 3,000 MockScene sinusoidal frames.
- Primary pin: classic ramp, tone 100, edge 60, thr 4, gain 10, relief 70,
  density 48 -> 48x36 = 1,728 cells/frame.
- Code space V=32: tone_idx (0..10, 0 = blank), 11 + edge_code (11..30,
  edge_code = fam*5 + level), SEP = 31.
- Splits: temporal per source, 70/15/15, no shuffle.

Output: training/glyph_g1/data.npz with per-source uint8 code arrays.
"""
import os
import subprocess
import sys

import numpy as np

EMB = os.path.expanduser("~/projects/chiaroscuro-embedding")
sys.path.insert(0, EMB)
from renderer import (  # noqa: E402
    Settings, active_ramp, downsample, tone_field, gradient_fields,
)
from c2_feed import SOURCES, W, H, FPS, SECONDS  # noqa: E402
from scene import MockScene  # noqa: E402

# --- the primary pin (spec §1) ------------------------------------------
S = Settings(density=48, ramp="classic", tone_amt=100.0, edge_amt=60.0,
             edge_thresh=4.0, edge_gain=10.0, relief=70.0)
COLS, ROWS = 48, 36
RL = len(active_ramp(S))          # 11 for classic
SEP = 31

NFF = 600  # spec: 60 s x 10 fps per lavfi source (c2_feed's SECONDS=10 overridden)
SECONDS = 60


def codes_for(frame_rgb: np.ndarray) -> np.ndarray:
    """Exact replication of renderer.render()'s code branching."""
    small = downsample(frame_rgb, COLS, ROWS)
    lum = tone_field(small, S)
    gx, gy, mag = gradient_fields(lum, S.edge_style)
    ramp_arr = np.array(list(active_ramp(S)), dtype="<U1")
    h, w = lum.shape

    edge_mask = (S.edge_amt > 0) & (mag > S.edge_thresh / 100.0)
    ang = np.degrees(np.arctan2(gy, gx)) % 180.0
    fam = np.zeros((h, w), dtype=np.int32)
    fam[(ang >= 22.5) & (ang < 67.5)] = 1
    fam[(ang >= 67.5) & (ang < 112.5)] = 2
    fam[(ang >= 112.5) & (ang < 157.5)] = 3
    relief = S.relief / 100.0
    level = np.clip(
        np.floor(mag * 9.0 * (S.edge_gain / 8.0) * (0.5 + relief)),
        0, 4).astype(np.int32)

    t = np.clip(lum / 255.0, 0.0, 0.999999)
    tone_idx = np.clip(np.floor((1.0 - t) * (RL - 1)).astype(np.int32),
                       0, RL - 1)
    tone_mask = (S.tone_amt > 5.0) & (~edge_mask)
    tone_mask &= (ramp_arr[tone_idx] != " ")

    codes = np.zeros((h, w), dtype=np.uint8)          # blank -> 0
    codes[tone_mask] = tone_idx[tone_mask]
    codes[edge_mask] = (11 + (fam * 5 + level))[edge_mask]
    assert codes.max() <= 30, codes.max()
    return codes


def lavfi_frames(graph: str):
    """Pipe raw rgb24 frames from an ffmpeg lavfi source."""
    cmd = ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", graph,
           "-t", str(SECONDS), "-r", str(FPS),
           "-vf", f"scale={W}:{H}", "-pix_fmt", "rgb24",
           "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=W * H * 3 * 32)
    n = 0
    while n < NFF:
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        n += 1
    p.stdout.close()
    p.wait()


def mock_frames(n: int):
    sc = MockScene()
    for i in range(n):
        frac = i / n
        sx = 0.5 + 0.35 * np.sin(2 * np.pi * frac * 6.0)
        sy = 0.5 + 0.30 * np.cos(2 * np.pi * frac * 4.5)
        ang = 2 * np.pi * frac * 12.0
        frame, _params = sc.frame(sx, sy, ang)
        yield frame


def main() -> None:
    out_dir = os.path.expanduser("~/projects/quilt-gpu-lab/training/glyph_g1")
    os.makedirs(out_dir, exist_ok=True)
    streams = {}
    for name, graph, _cap in SOURCES:
        arr = np.stack([codes_for(f) for f in lavfi_frames(graph)])
        streams[name] = arr
        print(f"[g1] {name}: {arr.shape}", flush=True)

    n_mock = sum(s.shape[0] for s in streams.values())  # 3,000
    arr = np.stack([codes_for(f) for f in mock_frames(n_mock)])
    streams["mockscene"] = arr
    print(f"[g1] mockscene: {arr.shape}", flush=True)

    total = sum(s.shape[0] for s in streams.values())
    splits = {}
    for name, arr in streams.items():
        n = arr.shape[0]
        a, b = int(n * 0.70), int(n * 0.85)
        splits[f"{name}_tr"] = arr[:a]
        splits[f"{name}_va"] = arr[a:b]
        splits[f"{name}_te"] = arr[b:]
    splits["names"] = np.array(list(streams.keys()))
    np.savez_compressed(os.path.join(out_dir, "data.npz"), **splits)
    cells = total * ROWS * COLS
    print(f"[g1] total frames {total}, cells {cells:,}, "
          f"3-pack tokens ~{cells * 3 + total * 9:,}", flush=True)
    print(f"[g1] saved {out_dir}/data.npz", flush=True)


if __name__ == "__main__":
    main()
