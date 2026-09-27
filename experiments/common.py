"""common.py — shared plumbing: real frames -> ASCII -> features.

ffmpeg (static 7.0.2, list-form subprocess, frames never touch disk)
renders lavfi sources as PPM image2pipe; pure-python P6 parse; integral-
image block-mean raster to 80x24 glyph frames over the lab ramp.
numpy-only.
"""
from __future__ import annotations

import subprocess
from typing import List, Tuple

import numpy as np

RAMP = " .:-=+*#%@"
W, H = 80, 24
FFMPEG = "/home/eileen/.local/bin/ffmpeg"


def ppms_from_lavfi(src: str, seconds: float, fps: int, size: Tuple[int, int]) -> List[np.ndarray]:
    """Render a lavfi source, return list of (h, w, 3) uint8 frames."""
    w, h = size
    cmd = [FFMPEG, "-loglevel", "error", "-f", "lavfi", "-i", src,
           "-f", "image2pipe", "-vcodec", "ppm", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    frames, off = [], 0
    while off < len(raw):
        assert raw[off:off+2] == b"P6", "bad ppm magic"
        parts: List[int] = []
        i = off + 2
        while len(parts) < 3:
            while raw[i:i+1].isspace():
                i += 1
            if raw[i:i+1] == b"#":
                while raw[i:i+1] != b"\n":
                    i += 1
                continue
            j = i
            while not raw[j:j+1].isspace():
                j += 1
            parts.append(int(raw[i:j]))
            i = j
        assert parts[2] == 255
        i += 1  # single whitespace after maxval
        n = parts[0] * parts[1] * 3
        frames.append(np.frombuffer(raw, np.uint8, n, i).reshape(parts[1], parts[0], 3))
        off = i + n
    return frames


def to_glyph(frames: List[np.ndarray]) -> np.ndarray:
    """RGB frames -> (T, H, W) uint8 ramp indices via luminance block-mean."""
    lum = (0.299 * frames[0][..., 0] + 0.587 * frames[0][..., 1]
           + 0.114 * frames[0][..., 2])
    out = np.empty((len(frames), H, W), np.uint8)
    bh, bw = lum.shape[0] // H, lum.shape[1] // W
    for t, f in enumerate(frames):
        lum = (0.299 * f[..., 0].astype(np.float32) + 0.587 * f[..., 1]
               + 0.114 * f[..., 2])
        blocks = lum[:H*bh, :W*bw].reshape(H, bh, W, bw).mean(axis=(1, 3))
        out[t] = np.clip(blocks / 255.0 * (len(RAMP) - 1) + 0.5, 0, len(RAMP) - 1).astype(np.uint8)
    return out


def frame_features(frames: np.ndarray) -> np.ndarray:
    """(T, H, W) ramp indices -> per-frame feature vector (lab's axes).

    Returns (T-1, 6): change, persistence, gradient energy, crest
    coherence, density, mean luminance.
    """
    T, Hh, Ww = frames.shape
    lum = frames.astype(np.float32) / (len(RAMP) - 1)
    feats = []
    for t in range(1, T):
        prev, cur = lum[t-1], lum[t]
        change = float(np.abs(cur - prev).mean())
        persist = float(1.0 - np.abs(cur - prev).mean() * 10)  # clip at 0 below
        gy, gx = np.gradient(cur)
        grad_e = float(np.hypot(gx, gy).mean())
        crest = float((gx * np.roll(gx, 1, 1)).mean())
        density = float((frames[t] > len(RAMP) // 2).mean())
        mean_l = float(cur.mean())
        feats.append([change, max(persist, 0.0), grad_e, crest, density, mean_l])
    return np.asarray(feats, np.float32)


def window_obs(feats: np.ndarray, window: int = 8) -> np.ndarray:
    """Non-overlapping window means -> obs rows for the encoder."""
    n = len(feats) // window * window
    return feats[:n].reshape(-1, window, feats.shape[-1]).mean(axis=1)
