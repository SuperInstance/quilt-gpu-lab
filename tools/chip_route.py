#!/usr/bin/env python3
"""chip_route.py — the distribution policy. Ask for a device class, get a
device + env + thread budget. This is the 'seamless' part: callers ask for
COMPUTE, not for a device.

Classes:
  tensor   heavy training/inference (torch)          -> GPU if free, else QUEUE
  render   cv2/frame pipelines (glyph datasets)       -> CPU, budgeted threads
  reader   ridge/MLP readers, correlators             -> CPU, small budget
  control  quick scripts                              -> CPU, 1-2 threads

Policy (honest, built on tonight's walls):
  - GPU work SERIALIZES (the sibling rule — the 6GB wall, learned in the G9 saga)
  - CPU work always runs; thread budget shrinks when a GPU fire is feeding
    (its dataloader wants threads) — reserve 6 threads for the GPU lane then.
  - GPU acceptance: >=3500 MiB free AND no live lock AND util < 95%.

Exit codes: 0 = run now (env on stdout as KEY=VAL lines + ROUTE=<device>);
            3 = do not fire now (reason on stderr). Wrap in your fire chain:
              eval "$(python3 tools/chip_route.py --class tensor)" || skip
"""
import json, os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(__file__))
from chip_probe import probe

def route(cls):
    s = probe()
    threads = s["cpu_threads"] or 24
    gpu_busy = s["gpu_locked_by"] not in (None, "stale")
    if cls == "tensor":
        free = (s["gpu_total_mb"] or 0) - (s["gpu_used_mb"] or 0)
        if gpu_busy:
            return None, f"GPU locked by {s['gpu_locked_by']} (sibling rule — serialize)"
        if free < 3500:
            return None, f"only {free} MiB free (<3500)"
        env = {"ROUTE": "gpu", "CUDA_VISIBLE_DEVICES": "0", "OMP_NUM_THREADS": "6",
               "CHIP_THREADS": str(max(2, threads - 6))}
        return env, None
    # CPU classes
    if gpu_busy:
        budget = max(2, threads - 6)   # the GPU lane's dataloader eats ~6
    else:
        budget = threads - 2           # keep the shell alive
    if cls == "render":
        n = min(budget, 12)
    elif cls == "reader":
        n = min(budget, 6)
    else:
        n = 2
    env = {"ROUTE": "cpu", "CUDA_VISIBLE_DEVICES": "", "OMP_NUM_THREADS": str(n),
           "MKL_NUM_THREADS": str(n), "CHIP_THREADS": str(n)}
    return env, None

if __name__ == "__main__":
    cls = sys.argv[sys.argv.index("--class") + 1] if "--class" in sys.argv else "control"
    env, why_not = route(cls)
    if env is None:
        print(why_not, file=sys.stderr)
        sys.exit(3)
    for k, v in env.items():
        print(f"{k}={v}")
