#!/usr/bin/env python
"""A5 conformance receipt: reproduce quilt-mojo-lab wave-73 runtime #9 (CuPy)
bit-parity receipt on this box's RTX 4050 Laptop (WSL2).

Protocol is their wave-73 bench.py methodology, unchanged where it matters:
same frozen kernels (python/cupy_quilt.py, imported READ-ONLY), same
injection set [(1,1,4.8)], threshold 0.6, 10 flow steps, best-of-3 timing
with flow_sync inside the timed window, checksum accumulated host-side in
the oracle's sequential float64 order, reference = python/flat_quilt.py
(their documented Python canon).

Documented deltas vs their harness (see README.md):
  D1. deliberate ~12s idle gap once at start + pre/post-ramp probes, to
      receipt the INSTRUMENT-01 ramp law on this box;
  D2. per-size pre-ramp probes + JSON receipt emission.
No kernel, gate, or tolerance changes.
"""
import datetime
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, "/home/eileen/projects/quilt-mojo-lab/python")  # READ-ONLY import

import numpy as np  # noqa: E402
import cupy as cp  # noqa: E402

import cupy_quilt  # noqa: E402  (quilt-mojo-lab/python, read-only)
import flat_quilt  # noqa: E402

OUT = "/home/eileen/projects/quilt-gpu-lab/results/a5_parity"
SIZES = [16, 512, 1024]
STEPS = 10
REPEAT = 3
THRESHOLD = 0.6
INJECT = [(1, 1, 4.8)]
RAMP_S = 0.6
IDLE_GAP_S = 12.0


def probe_cells_per_s(size):
    """Short timed burst on a throwaway instance (ramp-law probe only)."""
    w = cupy_quilt.CupySoaQuilt(size, THRESHOLD)
    for r, c, p in INJECT:
        w.inject_force(r, c, p)
    t0 = time.perf_counter_ns()
    for _ in range(STEPS):
        w.step_flow()
    w.flow_sync()
    t1 = time.perf_counter_ns()
    del w
    return round(size * size * STEPS / ((t1 - t0) / 1e9), 1)


def ramp(size):
    """INSTRUMENT-01 / wave-73 law: ~0.6s sustained synced CUDA load on a
    throwaway instance, immediately before any timed GPU work."""
    w = cupy_quilt.CupySoaQuilt(size, THRESHOLD)
    for r, c, p in INJECT:
        w.inject_force(r, c, p)
    t0 = time.perf_counter()
    passes = 0
    while time.perf_counter() - t0 < RAMP_S:
        for _ in range(20):
            w.step_flow()
        w.flow_sync()
        passes += 20
    dur = time.perf_counter() - t0
    del w
    return {"ramp_duration_s": round(dur, 3), "ramp_flow_passes": passes}


def reference(size):
    """Their Python canon: FlatQuilt, same injection, run(10)."""
    ref = flat_quilt.FlatQuilt(size, THRESHOLD)
    for r, c, p in INJECT:
        ref.inject_force(r, c, p)
    ref.run(STEPS)
    pot = np.frombuffer(ref.mem.tobytes(), dtype=np.float32)[0::4].copy()
    return ref.checksum(), pot


def parity_and_best_time(size):
    pre_probe = probe_cells_per_s(size)
    ref_cs, ref_pot = reference(size)  # host-side; GPU idles here
    r = ramp(size)                     # ramp AFTER the host gap, before GPU work
    post_probe = probe_cells_per_s(size)

    # Parity run (untimed): fresh instance, inject -> 10 flows -> entropy.
    q = cupy_quilt.CupySoaQuilt(size, THRESHOLD)
    for rr, cc, pp in INJECT:
        q.inject_force(rr, cc, pp)
    q.run(STEPS)
    gpu_cs = q.checksum()
    gpu_pot = cp.asnumpy(q.pot)
    parity_diff = float(abs(gpu_cs - ref_cs))
    max_dpot = float(np.max(np.abs(gpu_pot - ref_pot)))
    ref_checksum = float(ref_cs)
    del q

    # Timing: best-of-3; sync lands inside the window (their bench.py).
    best = None
    for _ in range(REPEAT):
        t = cupy_quilt.CupySoaQuilt(size, THRESHOLD)
        for rr, cc, pp in INJECT:
            t.inject_force(rr, cc, pp)
        t0 = time.perf_counter_ns()
        for _ in range(STEPS):
            t.step_flow()
        t.flow_sync()
        t1 = time.perf_counter_ns()
        t.step_entropy()
        best = (t1 - t0) if best is None else min(best, t1 - t0)
        del t
    cells_per_s = round(size * size * STEPS / (best / 1e9), 1)

    row = {
        "size": size,
        "steps": STEPS,
        "parity_diff": parity_diff,
        "max_abs_dpot": max_dpot,
        "cells_per_s": cells_per_s,
        "best_flow_window_ns": best,
        "ref_checksum": ref_checksum,
        "ramp": r,
        "probe_cells_per_s_pre_ramp": pre_probe,
        "probe_cells_per_s_post_ramp": post_probe,
    }
    print(f"[size {size}] parity_diff={parity_diff} max|dpot|={max_dpot} "
          f"cells/s={cells_per_s} probe pre/post ramp: {pre_probe} / {post_probe}",
          flush=True)
    return row


def main():
    started = datetime.datetime.now(datetime.timezone.utc)
    # Deliberate idle gap so the pre-ramp probe can demonstrate the
    # idle-poisoned state that INSTRUMENT-01 exists to defeat.
    time.sleep(IDLE_GAP_S)

    sizes_rows = []
    for s in SIZES:
        sizes_rows.append(parity_and_best_time(s))

    name_csv = subprocess.run(
        ["/usr/lib/wsl/lib/nvidia-smi", "--query-gpu=name,driver_version",
         "--format=csv,noheader"], capture_output=True, text=True, check=True)
    props = cp.cuda.runtime.getDeviceProperties(0)
    ended = datetime.datetime.now(datetime.timezone.utc)
    receipt = {
        "job": "a5_parity — reproduce quilt-mojo-lab wave-73 runtime #9 CuPy receipt",
        "device": f"{name_csv.stdout.strip()} (WSL2)",
        "device_detail": {
            "nvidia_smi": name_csv.stdout.strip(),
            "cupy_device_name": props["name"].decode()
                              if isinstance(props["name"], bytes) else str(props["name"]),
        },
        "cupy_version": cp.__version__,
        "protocol": {
            "source_runtime": "quilt-mojo-lab/python/cupy_quilt.py (imported read-only)",
            "reference": "quilt-mojo-lab/python/flat_quilt.py (FlatQuilt, their Python canon)",
            "inject": INJECT, "threshold": THRESHOLD, "steps": STEPS,
            "repeat": REPEAT, "timing": "best_of_3; flow passes only; "
            "flow_sync inside the timed window; cells/s = size^2*steps/best_ns",
            "parity": "|gpu_checksum - ref_checksum| and max|gpu_pot - ref_pot| "
                      "after run(10), host-side float64 sequential accumulation",
            "deltas_vs_their_harness": [
                "D1: deliberate 12s idle gap once at start + pre/post-ramp probes "
                "to receipt the INSTRUMENT-01 ramp law on this box",
                "D2: per-size pre-ramp probes + this JSON receipt",
                "no kernel/gate/tolerance changes; kernels and timing window identical",
            ],
        },
        "ramp_receipt": {
            "law": "INSTRUMENT-01: idle >= ~10s -> short GPU bursts measure 2-10x "
                   "slow on this box; 0.6s sustained synced load restores full "
                   "speed; ramp runs on a throwaway instance before any timing",
            "idle_gap_before_first_probe_s": IDLE_GAP_S,
            "per_size": {str(r["size"]): {
                "probe_cells_per_s_pre_ramp": r["probe_cells_per_s_pre_ramp"],
                "probe_cells_per_s_post_ramp": r["probe_cells_per_s_post_ramp"],
                **r["ramp"],
            } for r in sizes_rows},
        },
        "sizes": [{k: v for k, v in r.items() if k != "ramp"} for r in sizes_rows],
        "timestamp": ended.isoformat(),
        "started_at": started.isoformat(),
    }
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "a5_parity_receipt.json")
    with open(path, "w") as f:
        json.dump(receipt, f, indent=1)
    print(f"receipt written: {path}", flush=True)


if __name__ == "__main__":
    main()
