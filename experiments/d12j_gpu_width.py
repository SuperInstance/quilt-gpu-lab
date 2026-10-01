#!/usr/bin/env python3
"""D12j — GPU-scale width: does the W·T product rule survive W=64/128?

Pre-registered in proposals/runs/D12j-gpu-width-plan.md (commit 0b2df86,
BEFORE fire). D12i (KEEP) found the partner-discovery floor is governed by
the bandwidth-time product W·T (~400 at p=0.3) but only reached W<=16 on
CPU. This opens the GPU lane at W in {32, 64, 128}.

Model = D12i semantics, vectorized in torch on the 4050:
- Pairing: seeded shuffle, consecutive pairing (D12i make_pairs).
- Streams: per pair/channel/timestep, correlated with prob p_corr (shared
  +-1 base), else independent +-1 draws (D12i streams_for).
- corr(a,b) = |sum products| / (W*T); discovery = argmax over others with
  FIRST-index tie-break (torch argmax returns the first max, matching
  D12i's max(others, key=corr) semantics); self excluded.
- Streams RE-DRAWN per (W,N,p,T,draw) with torch CUDA generator seeded
  SEED*100000 + w*10000 + n*1000 + int(p*100)*10 + t*2 + draw, SEED=2718.
  NOT bit-matched to D12i; claims are about the floor RULES.

Frozen gates (see plan): J1 monotone non-increasing T_floor in W at every
(N,p) through W=128; J2 T_floor(128) <= 3 at (N=128, p=0.3);
J3 (kill clause) T_floor(128) == T_floor(32) at (N=128, p=0.3) => PLATEAU.
Verdict mapping mechanical, in _verdict().
"""
from __future__ import annotations

import json
import shutil
import sys
import traceback

import torch

SEED = 2718
W_VALUES = (32, 64, 128)
N_VALUES = (32, 64, 128)
P_VALUES = (0.3, 0.5, 0.7)
T_VALUES = (1, 2, 3, 5, 10, 25, 50, 100)
DRAWS = 3
ACC_BAR = 0.9
OUT_PATH = "results/d12j_gpu_width.json"


def preflight():
    free, _total = torch.cuda.mem_get_info()
    if free < 1024 * 1024 * 1024:
        raise RuntimeError(f"preflight FAIL: only {free/2**20:.0f} MiB VRAM free (< 1024)")
    try:
        temp = torch.cuda.temperature()
        if temp is not None and temp > 80:
            raise RuntimeError(f"preflight FAIL: GPU temp {temp}C > 80")
    except (RuntimeError, TypeError):
        pass  # temp readout unsupported on this driver; VRAM gate is the hard one


def run_cell(n, p, t, w, draw, dev):
    g = torch.Generator(device=dev)
    g.manual_seed(SEED * 100000 + w * 10000 + n * 1000 + int(p * 100) * 10 + t * 2 + draw)
    perm = torch.randperm(n, generator=g, device=dev)
    partner = torch.empty(n, dtype=torch.long, device=dev)
    partner[perm[0::2]] = perm[1::2]
    partner[perm[1::2]] = perm[0::2]

    P = n // 2
    pa, pb = perm[0::2], perm[1::2]                     # (P,)
    shape = (P, w, t)
    corr_mask = torch.rand(shape, generator=g, device=dev) < p
    base = torch.where(torch.rand(shape, generator=g, device=dev) < 0.5, 1.0, -1.0)
    indep_a = torch.where(torch.rand(shape, generator=g, device=dev) < 0.5, 1.0, -1.0)
    indep_b = torch.where(torch.rand(shape, generator=g, device=dev) < 0.5, 1.0, -1.0)
    sa = torch.where(corr_mask, base, indep_a)          # (P, w, t)
    sb = torch.where(corr_mask, base, indep_b)

    cells = torch.empty(n, w * t, device=dev)
    cells[pa] = sa.reshape(P, -1)
    cells[pb] = sb.reshape(P, -1)

    sim = cells @ cells.T / (w * t)                     # (n, n)
    sim.fill_diagonal_(-1.0)
    disc = sim.argmax(dim=1)                            # first-index tie-break
    return (disc == partner).float().mean().item()


def _verdict(floors, inversions):
    def f(w, n, p):
        return floors[f"W{w}_N{n}_p{p}"]

    j1 = not inversions
    hard_n, hard_p = 128, 0.3
    f128, f32 = f(128, hard_n, hard_p), f(32, hard_n, hard_p)
    j2 = f128 is not None and f128 <= 3
    j3 = f128 is not None and f32 is not None and f128 == f32
    if not j1:
        return "KILL-monotonicity", {"J1": "FAIL", "J2": j2, "J3": j3}
    if j3:
        return "KILL-product-rule/PLATEAU", {"J1": "PASS", "J2": j2, "J3": "TRIGGERED"}
    if j2:
        return "KEEP", {"J1": "PASS", "J2": "PASS", "J3": j3}
    return "PARTIAL", {"J1": "PASS", "J2": "FAIL", "J3": j3}


def main():
    preflight()
    dev = "cuda"
    grid = []
    for w in W_VALUES:
        for n in N_VALUES:
            for p in P_VALUES:
                for t in T_VALUES:
                    accs = [run_cell(n, p, t, w, d, dev) for d in range(DRAWS)]
                    grid.append({
                        "W": w, "N": n, "p_corr": p, "T": t,
                        "partner_id_acc": round(sum(accs) / len(accs), 4),
                        "chance": round(1 / (n - 1), 4),
                    })

    def floor(w, n, p):
        rows = sorted((r for r in grid if r["W"] == w and r["N"] == n and r["p_corr"] == p),
                      key=lambda r: r["T"])
        for r in rows:
            if r["partner_id_acc"] >= ACC_BAR:
                return r["T"]
        return None

    floors = {f"W{w}_N{n}_p{p}": floor(w, n, p)
              for w in W_VALUES for n in N_VALUES for p in P_VALUES}

    inversions = []
    for n in N_VALUES:
        for p in P_VALUES:
            seq = [floors[f"W{w}_N{n}_p{p}"] for w in W_VALUES]
            for i in range(1, len(seq)):
                if seq[i] is not None and seq[i - 1] is not None and seq[i] > seq[i - 1]:
                    inversions.append({"N": n, "p": p, "w_prev": W_VALUES[i - 1],
                                       "w": W_VALUES[i], "t_prev": seq[i - 1], "t": seq[i]})

    verdict, gates = _verdict(floors, inversions)
    result = {
        "experiment": "d12j_gpu_width",
        "device": torch.cuda.get_device_name(0),
        "seed": SEED, "draws": DRAWS, "acc_bar": ACC_BAR,
        "pre_registered": "proposals/runs/D12j-gpu-width-plan.md (commit 0b2df86)",
        "gates": gates,
        "verdict": verdict,
        "floors": floors,
        "monotonicity_inversions": inversions,
        "grid": grid,
    }
    with open(OUT_PATH, "w") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps({"verdict": verdict, "gates": gates, "floors": floors}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        receipt = {
            "experiment": "d12j_gpu_width",
            "verdict": "KILL-harness",
            "error": traceback.format_exc(),
            "python": sys.executable,
        }
        with open(OUT_PATH, "w") as fh:
            json.dump(receipt, fh, indent=2)
        print(json.dumps(receipt, indent=2))
        raise
