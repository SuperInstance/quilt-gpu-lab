#!/usr/bin/env python3
"""m5_gpu_tick.py — the GPU cell tick (importable + CLI).

A cell's 16 dials are derived from a fixed-iteration torch matmul chain, so the
dial vector depends ONLY on the seed (determinism receipt for the GPU cell).

INSTRUMENT-01: ramps (0.6 s sustained synced load) and emits a ramp receipt.

CLI: m5_gpu_tick.py <seed> <out.json>
"""
from __future__ import annotations

import hashlib
import json
import sys
import time

import torch

N_ITERS = 80000
SIZE = 1024
RAMP_S = 0.6


def tick(seed: int, dev: str = "cuda") -> dict:
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    name = torch.cuda.get_device_name(0)

    a = torch.randn(SIZE, SIZE, device=dev, dtype=torch.bfloat16)
    b = torch.randn(SIZE, SIZE, device=dev, dtype=torch.bfloat16)

    # --- INSTRUMENT-01 ramp: sustained synced load before measurement ---
    t0 = time.perf_counter()
    cold_ms = None
    n_ramp = 0
    while time.perf_counter() - t0 < RAMP_S:
        c = a @ b
        torch.cuda.synchronize()
        if cold_ms is None:
            cold_ms = (time.perf_counter() - t0) * 1000.0
        n_ramp += 1
    ramp_s = time.perf_counter() - t0
    t_r1 = time.perf_counter()
    a @ b
    torch.cuda.synchronize()
    hot_ms = (time.perf_counter() - t_r1) * 1000.0

    # --- measured tick: fixed iteration count => seed-determined dials ---
    t1 = time.perf_counter()
    acc = a
    for _ in range(N_ITERS):
        acc = torch.tanh(acc @ b) * 0.5 + acc * 0.5
    torch.cuda.synchronize()
    wall = time.perf_counter() - t1

    col = acc.float().sum(dim=0).cpu()
    dials = [int(abs(float(col[i * 8])) * 1000.0) % 100 for i in range(16)]

    state = {"dials": dials, "seed": seed, "iters": N_ITERS, "size": SIZE,
             "device": name, "torch": torch.__version__}
    blob = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
    return {
        "seed": seed, "dials": dials, "iters": N_ITERS, "size": SIZE,
        "device": name, "torch": torch.__version__, "wall_s": round(wall, 3),
        "ramp_receipt": {
            "ramp_s": round(ramp_s, 3), "ramp_iters": n_ramp,
            "cold_first_matmul_ms": round(cold_ms, 3) if cold_ms else None,
            "hot_matmul_ms": round(hot_ms, 3),
            "ramped": hot_ms > 0 and (cold_ms or 0) > hot_ms,
        },
        "state_sha256": hashlib.sha256(blob).hexdigest(),
    }


def main() -> int:
    seed = int(sys.argv[1])
    rec = tick(seed)
    with open(sys.argv[2], "w") as f:
        json.dump(rec, f, indent=2, sort_keys=True)
    print(json.dumps({k: rec[k] for k in ("seed", "wall_s", "state_sha256",
                                          "dials", "ramp_receipt")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
