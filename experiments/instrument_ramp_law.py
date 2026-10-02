#!/usr/bin/env python3
"""INSTRUMENT-01 — characterize the WSL2 GPU burst-timing law.

Pre-registered: proposals/runs/INSTRUMENT-01-ramp-law-prereg.md (owner: any).
Frozen probes (measurement only — NO clock/driver changes):
  R1 shape:     idle {5,10,20,40,80}s -> burst slowdown vs hot baseline.
                Gate: slowdown > 1.5x for idle >= 10s in >= 2/3 of those draws.
  R2 recovery:  ramp {0.1,0.3,0.6,1.2}s sustained synced load after a fixed
                30s idle. Gate: the 0.6s ramp restores >= 90% of hot baseline
                in 3/3 trials.
  R3 portability (EXPLORATORY, no gate): elementwise kernel vs matmul after
                a 20s idle — is the law kernel-agnostic?
Burst = 30 back-to-back 2048^3 fp32 matmuls, one sync at the end.
Hot baseline = median of 5 back-to-back bursts. Times are host wall-clock
around torch.cuda.synchronize().
"""
import json
import math
import sys
import time
import traceback

import torch

BURST_MM = 30          # matmuls per burst (~tens of ms on the 4050)
MM_SIZE = 2048
OUT_PATH = "results/instrument_ramp_law.json"


def _burst(a, b, c):
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(BURST_MM):
        torch.mm(a, b, out=c)
    torch.cuda.synchronize()
    return time.perf_counter() - t0


def _hot_baseline(a, b, c):
    ts = [_burst(a, b, c) for _ in range(5)]
    ts.sort()
    return ts[len(ts) // 2]


def _elementwise_burst(x, iters=BURST_MM * 64):
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(iters):
        x.add_(0.001)
    torch.cuda.synchronize()
    return time.perf_counter() - t0


def main():
    free, _total = torch.cuda.mem_get_info()
    if free < 512 * 1024 * 1024:
        raise RuntimeError(f"preflight FAIL: only {free/2**20:.0f} MiB VRAM free")
    a = torch.randn(MM_SIZE, MM_SIZE, device="cuda")
    b = torch.randn(MM_SIZE, MM_SIZE, device="cuda")
    c = torch.empty(MM_SIZE, MM_SIZE, device="cuda")
    xe = torch.randn(1 << 22, device="cuda")

    hot = _hot_baseline(a, b, c)
    hot_ew = min(_elementwise_burst(xe) for _ in range(3))

    # R1 shape probe
    shape = []
    for idle in (5, 10, 20, 40, 80):
        time.sleep(idle)
        t = _burst(a, b, c)
        shape.append({"idle_s": idle, "burst_s": round(t, 5),
                      "slowdown": round(t / hot, 3)})
    hard = [s for s in shape if s["idle_s"] >= 10]
    n_ok = sum(1 for s in hard if s["slowdown"] > 1.5)
    r1 = n_ok >= math.ceil(2 / 3 * len(hard))   # >=2/3 of the idle>=10s draws
    r1_detail = {"draws": len(hard), "slow_gt_1p5": n_ok,
                 "threshold": math.ceil(2 / 3 * len(hard))}

    # R2 recovery probe
    recovery = []
    for ramp_s in (0.1, 0.3, 0.6, 1.2):
        trials = 3 if ramp_s == 0.6 else 1
        for trial in range(trials):
            time.sleep(30)
            t0 = time.perf_counter()
            while time.perf_counter() - t0 < ramp_s:   # sustained SYNCED load
                torch.mm(a, b, out=c)
            torch.cuda.synchronize()
            t = _burst(a, b, c)
            recovery.append({"ramp_s": ramp_s, "trial": trial,
                             "burst_s": round(t, 5),
                             "pct_of_hot": round(100 * hot / t, 1)})
    r06 = [r for r in recovery if r["ramp_s"] == 0.6]
    r2 = len(r06) == 3 and all(r["pct_of_hot"] >= 90.0 for r in r06)

    # R3 portability (exploratory, no gate)
    time.sleep(20)
    ew_after_idle = _elementwise_burst(xe)
    r3 = {"elementwise_hot_s": round(hot_ew, 5),
          "elementwise_after_20s_idle_s": round(ew_after_idle, 5),
          "slowdown": round(ew_after_idle / hot_ew, 3)}

    verdict = "LAW_CALIBRATED" if (r1 and r2) else "LAW_FUZZY"
    result = {
        "experiment": "instrument_ramp_law",
        "device": torch.cuda.get_device_name(0),
        "burst_design": f"{BURST_MM}x matmul {MM_SIZE}^3 fp32, one sync",
        "hot_baseline_s": round(hot, 5),
        "R1": {"pass": r1, **r1_detail, "shape": shape},
        "R2": {"pass": r2, "trials": recovery},
        "R3_exploratory": r3,
        "verdict": verdict,
        "pre_registered": "proposals/runs/INSTRUMENT-01-ramp-law-prereg.md",
    }
    with open(OUT_PATH, "w") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps({"verdict": verdict, "R1": r1, "R2": r2}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        with open(OUT_PATH, "w") as fh:
            json.dump({"experiment": "instrument_ramp_law",
                       "verdict": "KILL-harness",
                       "error": traceback.format_exc(),
                       "python": sys.executable}, fh, indent=2)
        raise
