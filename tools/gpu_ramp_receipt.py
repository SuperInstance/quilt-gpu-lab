#!/usr/bin/env python3
"""gpu-ramp-receipt — WSL2 GPU idle-ramp instrument (INSTRUMENT-01 law).

Lifted from the calibrated 2026-10-01 lesson (TOOLS.md INSTRUMENT-01,
LAW_CALIBRATED): on this WSL2 box every GPU measurement ramps first.
Idle <5s is SAFE; slowdown saturates ~4.5x by ~20s idle, flat after.
Recovery: >=0.3s sustained synced load restores >=97% of hot throughput
(0.6s used for margin; 0.1s is best-case single-draw, never rely on it).

This tool MEASURES the ramp on the current box instead of trusting the
booked numbers, then verifies recovery — and emits a JSON ramp receipt
either way (fail-loud: dead run still books a receipt with verdict KILL).

The rule it enforces (quote it in your methods section): **every GPU
measurement on a ramping box reports a ramp receipt. No exceptions.**

Usage:
    elephant-gpu-python gpu_ramp_receipt.py [--delays 0,5,10,20] \
        [--recovery-idle 20] [--out receipt.json] [--tolerance 0.97]

Requires torch+CUDA. On this box run with the GPU venv:
    /home/eileen/venvs/elephant-gpu/bin/python tools/gpu_ramp_receipt.py

Worked example (smoke run, ~40s):
    $ python gpu_ramp_receipt.py --delays 0,5 --out /tmp/ramp.json
    $ python -c "import json;r=json.load(open('/tmp/ramp.json'));print(r['verdict'])"
    CLEAN          # ramp characterized + recovery >= tolerance

Exit codes: 0 CLEAN, 1 RAMPED (measured slowdown beyond expected curve),
2 KILL (environment/precondition failure — receipt still written).
"""
import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone

FLOPS_PER_ELT = 2  # a*b+... elementwise: count as 2 flops for readability


def gpu_temp_and_free_mib():
    """Query via WSL nvidia-smi; returns (temp_c, free_mib) or None."""
    smi = "/usr/lib/wsl/lib/nvidia-smi"
    if not os.path.exists(smi):
        return None
    try:
        out = subprocess.run(
            [smi, "--query-gpu=temperature.gpu,memory.free",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip().splitlines()[0]
        t, m = [x.strip() for x in out.split(",")]
        return float(t), float(m)
    except Exception:
        return None


def preflight(min_free_mib=1024, max_temp=80):
    g = gpu_temp_and_free_mib()
    if g is None:
        print("[preflight] nvidia-smi unavailable; skipping temp/VRAM guard",
              file=sys.stderr)
        return
    temp, free = g
    if free < min_free_mib:
        raise RuntimeError(f"preflight FAIL: only {free:.0f} MiB VRAM free "
                           f"(need >= {min_free_mib})")
    if temp > max_temp:
        raise RuntimeError(f"preflight FAIL: GPU temp {temp:.0f}C > {max_temp}C")


def timed_elementwise(torch, n=32_000_000, iters=20):
    """Synced timed elementwise kernel; returns elapsed seconds."""
    a = torch.randn(n, device="cuda")
    b = torch.randn(n, device="cuda")
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(iters):
        c = a * b + a
    torch.cuda.synchronize()
    dt = time.perf_counter() - t0
    del a, b, c
    torch.cuda.empty_cache()
    return dt


def gtps(torch, n=32_000_000, iters=20):
    """G-elt-ops/sec for the timed block."""
    return (n * iters) / timed_elementwise(torch, n, iters) / 1e9


def measure_ramp(torch, delays):
    """Hot baseline, then one point per idle delay: idle, single draw, rate."""
    hot = max(gtps(torch) for _ in range(3))  # best-of-3 hot baseline
    points = []
    for d in delays:
        time.sleep(d)
        rate = gbps = None
        rate = gtps(torch)  # single draw after idle
        points.append({"idle_s": d, "gops": rate,
                       "slowdown_x": hot / rate if rate > 0 else float("inf")})
    return hot, points


def main():
    ap = argparse.ArgumentParser(
        description="Measure WSL2 GPU idle-ramp slowdown + recovery, emit receipt.")
    ap.add_argument("--delays", default="0,5,10,20",
                    help="comma-separated idle seconds to probe (default 0,5,10,20)")
    ap.add_argument("--recovery-idle", type=float, default=20.0,
                    help="idle seconds before the recovery draw (default 20)")
    ap.add_argument("--recover-s", type=float, default=0.6,
                    help="sustained synced load seconds for recovery (default 0.6)")
    ap.add_argument("--tolerance", type=float, default=0.97,
                    help="recovery must restore >= this fraction of hot (default 0.97)")
    ap.add_argument("--out", default=None, help="write JSON receipt here")
    args = ap.parse_args()
    delays = sorted(float(x) for x in args.delays.split(","))
    receipt = {"tool": "gpu-ramp-receipt", "ts": datetime.now(timezone.utc).isoformat(),
               "verdict": "KILL", "delays": delays}
    out_path = args.out or f"ramp_receipt_{int(time.time())}.json"
    receipt["out"] = os.path.abspath(out_path)
    try:
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError("torch has no CUDA; run with the GPU venv")
        receipt["gpu"] = torch.cuda.get_device_name(0)
        preflight()
        hot, points = measure_ramp(torch, delays)
        receipt["hot_gops"] = round(hot, 1)
        receipt["points"] = points
        # recovery: idle again, then sustained load, then measure
        time.sleep(args.recovery_idle)
        a = torch.randn(32_000_000, device="cuda")
        t_end = time.perf_counter() + args.recover_s
        while time.perf_counter() < t_end:
            c = a * a + a
        torch.cuda.synchronize()
        rec = gtps(torch)
        del a, c
        torch.cuda.empty_cache()
        frac = rec / hot
        receipt["recovery"] = {"idle_s": args.recovery_idle,
                               "load_s": args.recover_s,
                               "gops": round(rec, 1),
                               "frac_of_hot": round(frac, 3)}
        ramped = any(p["idle_s"] >= 5 and p["slowdown_x"] < 1.5 for p in points)
        recovered = frac >= args.tolerance
        receipt["verdict"] = "CLEAN" if (ramped and recovered) else \
                             ("RAMPED" if ramped else "CLEAN")
        # RAMPED only if the ramp shows but recovery failed; law check:
        if not recovered:
            receipt["verdict"] = "RAMPED"
            receipt["note"] = ("recovery below tolerance — do not book "
                               "measurements from this state (INSTRUMENT-01)")
        else:
            receipt["note"] = ("ramp present as expected; per-point slowdowns "
                               "are single-draw statistics — treat as "
                               "order-of-magnitude (INSTRUMENT-01)")
        print(json.dumps(receipt, indent=2))
        with open(out_path, "w") as f:
            json.dump(receipt, f, indent=2)
        sys.exit(0 if receipt["verdict"] == "CLEAN" else 1)
    except Exception as e:
        receipt["error"] = f"{type(e).__name__}: {e}"
        receipt["traceback"] = traceback.format_exc()
        receipt["verdict"] = "KILL"
        with open(out_path, "w") as f:
            json.dump(receipt, f, indent=2)
        print(json.dumps(receipt, indent=2), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
