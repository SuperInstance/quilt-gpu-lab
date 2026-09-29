#!/usr/bin/env python3
"""chip_probe.py — one-shot silicon inventory for the PX13 (WSL2 view).

Ground truth 2026-09-28 19:15: GPU 6141MiB (nvidia-smi), 24 CPU threads,
15GB visible RAM. NPU (XDNA2) and iGPU (890M) are NOT passed through to
WSL2 — no /dev/xdna, no /dev/dri, empty lspci. They live Windows-side;
reaching them is a Windows/driver project, not this one.

Output: JSON on stdout. Consumers: chip_route.py (the policy), the fire
chains, the CPU lanes (renders/readers/correlators) that need a thread
budget that doesn't starve the GPU's data pipeline.
"""
import json, os, re, subprocess, sys

NSMI = "/usr/lib/wsl/lib/nvidia-smi"

def probe():
    out = {"ts": subprocess.run(["date", "-Is"], capture_output=True, text=True).stdout.strip(),
           "cpu_threads": os.cpu_count(),
           "ram_total_gb": None, "ram_free_gb": None,
           "gpu_total_mb": None, "gpu_used_mb": None, "gpu_util_pct": None,
           "load1": None, "threads_busy_est": None, "gpu_locked_by": None}
    # RAM
    with open("/proc/meminfo") as f:
        mi = {}
        for line in f:
            k, v = line.split(":", 1)
            mi[k] = int(v.strip().split()[0]) // 1024  # MiB
    out["ram_total_gb"] = round(mi.get("MemTotal", 0) / 1024, 1)
    out["ram_free_gb"] = round((mi.get("MemAvailable", 0)) / 1024, 1)
    # load
    with open("/proc/loadavg") as f:
        out["load1"] = float(f.read().split()[0])
    out["threads_busy_est"] = min(out["cpu_threads"], int(round(out["load1"])))
    # GPU
    try:
        r = subprocess.run([NSMI, "--query-gpu=memory.total,memory.used,utilization.gpu",
                            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10)
        t, u, g = [x.strip() for x in r.stdout.strip().split(",")]
        out["gpu_total_mb"], out["gpu_used_mb"] = int(t), int(u)
        out["gpu_util_pct"] = int(g)
    except Exception as e:
        out["gpu_error"] = str(e)
    # sibling lock (the serial-GPU rule: one training fire at a time)
    lock = os.path.join(os.path.dirname(__file__), "..", ".gpu.lock")
    if os.path.exists(lock):
        pid = open(lock).read().strip()
        if pid and os.path.exists(f"/proc/{pid}"):
            out["gpu_locked_by"] = int(pid)
        else:
            out["gpu_locked_by"] = "stale"
    return out

if __name__ == "__main__":
    print(json.dumps(probe(), indent=2))
